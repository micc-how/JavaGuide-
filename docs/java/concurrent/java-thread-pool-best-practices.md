---
title: Java Thread Pool 最佳实践
description: Java Thread Pool 最佳实践总结：从业务吞吐、Task 耗时和下游 Capacity 估算 Thread Count 与 Queue Length，讲解 Queue 堆积、Rejection Policy、Task Timeout、Exception Handling、动态调参、Monitoring 和 Virtual Thread 等生产问题。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: Thread Pool 最佳实践,ThreadPoolExecutor Parameter 配置,Thread Pool Monitoring,Queue 堆积,CallerRunsPolicy,动态 Thread Pool,Task Timeout,Virtual Thread
---

看到 `corePoolSize = 8`、`maximumPoolSize = 16`、`queueCapacity = 1000` 这组配置，仅凭机器有 8 个 CPU 核心，还判断不了它是否合适。图片压缩、批量查 Database 和调用外部 Interface 的耗时构成不同，需要的 Thread Count 可能相差很大。 Task 进入多快、执行多久、允许排队多久，以及 Database 和下游能接住多少 Concurrency，都会影响最终配置。

七大 Parameter、Task 执行流程、Blocking Queue 及 Rejection Policy 的基础知识，可以先看 [Java Thread Pool 详解](./java-thread-pool-summary.md)。生产环境还要处理 Parameter 估算、过载、Task Timeout 和 Monitoring，这些问题更依赖业务 Capacity 和运行数据。

## 正确声明 Thread Pool

Business Thread 池通常需要明确指定 Thread Count、Queue Capacity、Thread 名称和 Rejection Policy。使用 `Executors` 的快捷 Method 虽然方便，但部分 Method 会创建近似无界的 Queue 或允许 Thread Count 持续增长，业务高峰期容易 Backlog 大量 Task 或创建过 Multithreading。

- `newFixedThreadPool()` 和 `newSingleThreadExecutor()` 使用无界的 `LinkedBlockingQueue`，Task 持续进入时，Queue 可能不断增长。
- `newCachedThreadPool()` 使用 `SynchronousQueue`，Maximum Pool Size 是 `Integer.MAX_VALUE`，提交速度长期高于处理速度时可能创建大量 Thread。
- `newScheduledThreadPool()` 使用无界的 `DelayedWorkQueue`，同样要考虑延迟 Task 不断堆积的问题。

因此，普通 Business Thread 池更适合直接使用 `ThreadPoolExecutor`，把 Capacity 限制写在配置里：

```java
ThreadFactory threadFactory = new NamingThreadFactory("order-query");

ThreadPoolExecutor executor = new ThreadPoolExecutor(
        8,
        16,
        60L,
        TimeUnit.SECONDS,
        new ArrayBlockingQueue<>(200),
        threadFactory,
        new ThreadPoolExecutor.AbortPolicy()
);
```

示例中的 `8`、`16` 和 `200` 只用于展示 Parameter 位置，不能直接用于生产环境。 Parameter 要结合业务 Capacity 和压测结果确定。

Thread Factory 至少应该为 Thread 设置有业务含义的名称：

```java
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

public final class NamingThreadFactory implements ThreadFactory {

    private final AtomicInteger sequence = new AtomicInteger();
    private final String prefix;

    public NamingThreadFactory(String prefix) {
        this.prefix = prefix;
    }

    @Override
    public Thread newThread(Runnable task) {
        Thread thread = new Thread(task);
        thread.setName(prefix + "-" + sequence.incrementAndGet());
        thread.setDaemon(false);
        return thread;
    }
}
```

Thread 名会出现在 Thread Dump、Log 和 Monitoring 数据中。`pool-1-thread-3` 很难判断属于哪项业务，`order-query-3` 则能直接缩小排查范围。

## Thread Pool Parameter 怎么估算？

CPU 密集型 Task 常从 CPU 核数附近起步，I/O 密集型 Task 可以配置更 Multithreading。这类经验适合做初始判断，实际配置还要回答几个更具体的问题：高峰期每秒会提交多少个 Task？一个 Task 会运行多久？其中多少时间在等待 I/O？下游能接住多少 Concurrency？ Task 最多允许排队多久？

在一段相对稳定的高峰窗口内，假设每秒提交的 Task 数为 $\lambda$，Task 平均执行时间为 $T$ 秒，执行中的 Task 数量 $L$ 可以先按下面的方式估算：

$$
L \approx \lambda \times T
$$

例如，某个 Interface 高峰期每秒产生 400 个 Asynchronous Task，每个 Task 平均执行 80 ms，对应的平均 Concurrency 需求约为 `400 × 0.08 = 32`。这只是估算起点，不能据此直接把 Thread Count 设置为 32，原因包括：

- 平均耗时会掩盖慢 Task，P95、P99 可能远高于平均值。
- Task 耗时上涨时，Concurrency 需求也会随之上涨。
- CPU、内存和 Context Switch 会限制 Platform Thread 数量。
- Database Connection Pool 或下游 Interface 可能只允许更低的 Concurrency。

《Java Concurrent Programming 实战》给出过一个包含目标 CPU 利用率的估算式。对于混合了计算和等待的 Task，可以用它辅助确定初始值：

$$
N_{threads} \approx N_{cpu} \times U_{cpu} \times \left(1 + \frac{W}{C}\right)
$$

其中，$N_{cpu}$ 是 CPU 核数，$U_{cpu}$ 是目标 CPU 利用率，$W/C$ 是 Task 等待时间与计算时间的比值。

等待时间越长，理论上可以安排越 Multithreading，让一部分 Task 等待 I/O 时，其他 Task 继续使用 CPU。不过，当等待来自 Database Connection Pool 耗尽、下游 Rate Limiting 或 Lock Contention 时，增加 Thread 只会制造更多等待。公式无法识别这种区别。

初始值确定后，还要用接近真实流量的压测逐步调整。压测时同时观察吞吐、P95/P99 延迟、CPU、Context Switch、Queue 等待时间和下游 Connection Pool，不能只看应用 QPS。

## 有界 Queue 应该设置多大？

Queue 主要用来吸收短时间的流量波动，不适合长期保存来不及处理的 Task。 Queue 过小，轻微抖动就可能触发拒绝；Queue 过大，Task 虽然被接收了，却可能在真正执行前已经超过业务 Timeout 时间，还会占用大量 Heap Memory。

可以先用突发流量估算需要的缓冲量。$\lambda_{in}$ 表示 Task 进入速率，$\lambda_{out}$ 表示完成速率，$\Delta t$ 表示突发持续时间：

$$
Q \approx (\lambda_{in} - \lambda_{out}) \times \Delta t
$$

例如，Thread Pool 每秒能完成约 500 个 Task，某次流量高峰会在 2 秒内把提交速率推到每秒 600 个，那么这段时间会多出约 200 个 Task。这个数字只能说明短时缓冲需求，最终 Capacity 还要受 Task 时效和内存限制。

Queue 等待时间也可以做一个粗略判断：Queue 中有 500 个 Task，Thread Pool 每秒完成 500 个 Task，队尾 Task 大约还要等待 1 秒。 Interface 总 Timeout 只有 800 ms 时，这批 Task 即使 Enqueue 也很难按时返回。

Worker Thread 达到 `corePoolSize` 后，新 Task 会先进入 Queue；只有 Queue 满了，Thread Pool 才会继续创建 Thread，直到 `maximumPoolSize`。 Queue 设置得很大时，Thread Count 可能长期停在 Core Pool Size，Maximum Pool Size 很少有机会生效。无界 Queue 下，`maximumPoolSize` 实际上不会参与 Resize。

确定 Queue Capacity 时，至少要做四项验证：

1. 用高峰流量和突发持续时间估算缓冲需求。
2. 检查队尾 Task 的预计等待时间是否超过业务期限。
3. 测量排队 Task 占用的内存，尤其是携带文件、请求体或大 Collection 的 Task。
4. 在 Queue 满、Task 被拒绝的情况下验证 Fallback 和 Alert 是否生效。

## Thread Count 为什么要和下游 Capacity 一起设计？

不少 I/O Task 最终会访问 Database、Redis 或外部 Interface。 Thread Pool 可以让更多 Task 同时发起调用，却不会增加下游的处理能力。

假设订单服务部署了 4 个 Instance，每个 Instance 给某项 Database Task 配置 40 个 Thread，理论上可能同时产生 160 个 Database 请求。 Database Connection Pool 每个 Instance 只有 20 个连接时，大量 Thread 会 Blocking 在获取连接的位置；Database 本身只能稳定承受 80 个 Concurrency 查询时，即便继续扩大 Connection Pool，也可能把压力转移到 Database。

配置时要从整条调用链分配 Concurrency 预算：

- Database Connection 要给 Web 请求、定时 Task 和其他 Business Thread 池预留份额，不能全部交给一个 Thread Pool。
- HTTP 客户端 Connection Pool 的每路由限制和总连接数，应该与实际调用 Concurrency 匹配。
- 下游有 Rate Limiting Threshold 时，上游所有 Instance 的 Concurrency 总和不能长期超过该 Threshold。
- 一个 Task 会 Serial 或 Parallelism 访问多个依赖时，要分别计算每个依赖的占用时间。

Thread Count 增加后，如果活跃连接、获取连接等待时间、下游 P99 和错误率同时上升，继续扩 Thread 通常没有帮助。此时应当减少无效 Concurrency，处理慢 SQL、下游 Timeout 或热点资源。

## Queue 堆积后怎么处理？

Queue 持续增长，说明 Task 进入速度已经超过完成速度。流量突然增加会造成堆积，Task 本身变慢也会造成堆积，两者的处理方式不同。

| 现象 | 需要核对的证据 | 处理方向 |
| ---------------------------------- | ---------------------------------- | ------------------------------------ |
| 提交速率上涨，Task 执行时间基本不变 | 入口 QPS、活动流量、调用方 Retry | 入口 Rate Limiting、扩 Instance 或用 MQ 削峰 |
| 提交速率稳定，Task 执行时间上涨 | Thread Stack、慢 SQL、Lock 等待、下游延迟 | 处理慢 Task 和下游故障，不急着增加 Thread |
| Active Thread 已满，CPU 长期接近上限 | CPU 使用率、运行 Queue、Context Switch | 优化计算、拆分 Task 或扩机器 |
| Thread 大量等待 Database Connection | Connection Pool 活跃数、等待数、获取连接 Timeout | 限制 Concurrency、优化 SQL，重新分配连接预算 |
| 排队时间已经超过 Task 有效期 | Queue 等待 P95/P99、业务 Timeout | 快速失败、丢弃过期 Task 或转入补偿流程 |
| Queue 和拒绝增加，下游仍有 Capacity | CPU、Connection Pool 和下游 Metric 正常 | 压测后调整 Thread Count、Queue 或 Instance 数 |

扩机器适合服务整体 Capacity 不足且 Task 可以横向拆分的情况。扩 Thread 适合单 Instance 仍有 CPU 和下游余量，但当前 Concurrency 度偏低的情况。 Task 已经失去时效时，继续排队意义不大；不能丢的 Asynchronous Task 则应先写入 MQ 或 Database，由可 Retry 的消费流程处理。

线上已经出现 Thread Pool 堆积时，可以参考 [Java 后端线上问题排查](../jvm/jvm-in-action.md#线程池队列堆积怎么排查)，结合提交速率、完成速率、Thread Stack 和下游状态定位。

## CallerRunsPolicy 能形成背压吗？

`CallerRunsPolicy` 会让调用 `execute()` 的 Thread 执行被拒绝的 Task。提交 Thread 因此变慢，后续 Task 的提交速度也可能下降，所以它具备一定的反馈调节作用。

效果取决于提交者是谁。消息消费 Thread 或批处理调度 Thread 被迫执行 Task 时，上游拉取速度可能自然下降；Tomcat 请求 Thread 执行长 Task 时，请求 Thread 会被占住，Interface 延迟和请求 Thread Pool 压力也会增加。提交 Thread Hold Lock 或 Database 事务时，Task 在调用 Thread 执行还会延长 Lock 和事务的占用时间。

Thread Pool 关闭后，`CallerRunsPolicy` 不会再执行 Task，而是直接丢弃。业务不能接受丢 Task 时，需要自定义拒绝处理：记录拒绝次数，返回明确失败，或者把 Task 写入可靠存储。不要只换一个 Rejection Policy，就把 Task 可靠性问题留给调用方。

## 不同业务要不要隔离 Thread Pool？

Shared Thread Pool 会让一类慢 Task 占用其他业务的执行资源。支付 Callback、报表导出和普通通知的时效、失败处理方式、依赖资源都不同，放在同一个 Thread Pool 里很难配置统一的 Thread Count、Queue 和 Rejection Policy。

隔离也不是每个 Interface 都创建一个 Thread Pool。通常按照 Task 优先级、耗时特征和下游依赖划分：调用同一个慢服务的 Task 可以单独隔离；核心交易和非核心通知不共用 Queue；CPU 密集 Task 不要和大量 Blocking I/O Task 混在一起。 Thread Pool 过多会增加 Thread、Queue、Monitoring 和配置成本，同类 Task 可以复用一个池。

现有文章曾 Reference 过一个父子 Task 共用 Thread Pool 的事故案例（来源：[Thread Pool 运用不当的一次线上事故](https://heapdump.cn/article/646639)）：

![案例代码概览](https://oss.javaguide.cn/github/javaguide/java/concurrent/production-accident-threadpool-sharing-example.png)

假设 Thread Pool 有 $n$ 个 Worker Thread，同时运行了 $n$ 个父 Task。每个父 Task 提交子 Task 后，又同步等待子 Task 结束。子 Task 进入 Queue，却没有 Idle Thread 可以执行；父 Task 不结束，Worker Thread 也不会释放，最终形成 Thread Starvation Deadlock。

![Thread Pool 使用不当导致 Deadlock](https://oss.javaguide.cn/github/javaguide/java/concurrent/production-accident-threadpool-sharing-deadlock.png)

父 Task 和它同步等待的子 Task 不应使用这个有界 Thread Pool 形成环形等待。可以让父 Task 直接执行子逻辑、改为不 Blocking 的 Task 编排，或者为确实需要隔离的子 Task 分配独立执行资源。

## Task Timeout 后会自动停止吗？

`Future.get(timeout, unit)` 只限制调用 Thread 等待结果的时间。抛出 `TimeoutException` 时，后台 Task 可能仍在运行。调用 `cancel(true)` 可以尝试 Interrupt 执行 Thread，但 Interrupt 是协作机制，Task 不检查 Interrupt Status，或者底层调用不响应 Interrupt，Task 仍可能继续执行。

```java
Future<String> future = executor.submit(this::callRemoteService);

try {
    return future.get(200, TimeUnit.MILLISECONDS);
} catch (TimeoutException e) {
    future.cancel(true);
    throw new IllegalStateException("调用超时", e);
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    throw new IllegalStateException("等待任务时被中断", e);
} catch (ExecutionException e) {
    throw new IllegalStateException("任务执行失败", e.getCause());
}
```

这段代码还不够替代网络 Timeout。HTTP、Database 和 Redis 客户端仍要配置连接、读取和总调用 Timeout，否则 Thread 可能一直卡在不响应 Interrupt 的底层操作里。

Task 代码收到 `InterruptedException` 后，一般要结束当前工作；如果无法在当前层结束，应恢复 Interrupt Flag，让上层继续处理：

```java
try {
    blockingCall();
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    return;
}
```

`CompletableFuture.orTimeout()` 会让 `CompletableFuture` Timeout 后以 Exception 完成，但不会自动终止底层 Task。`CompletableFuture.cancel(true)` 的 Parameter 在该实现中也不会触发 Thread Interrupt。使用 `CompletableFuture` 编排 Blocking Task 时，仍要给底层调用配置 Timeout 和取消方案。

## Asynchronous Task 的 Exception 为什么容易丢？

通过 `execute()` 提交的 `Runnable` 抛出未捕获 Exception 时，Worker Thread 会 Exception 结束，可以由 Thread 的 `UncaughtExceptionHandler` 记录。通过 `submit()` 提交时，Task 通常被包装成 `FutureTask`，Exception 保存在返回的 `Future` 中；调用方既不保存 `Future`，也不调用 `get()`，Exception 就可能没有业务 Log。

`ThreadPoolExecutor.afterExecute()` 也有同样的区别。使用 `submit()` 时，传给 `afterExecute()` 的 `Throwable` 通常是 `null`，需要判断 Task 是否为已经完成的 `Future`，再通过 `get()` 取得 Exception。

Exception Handling 方式最好在项目内统一：调用方消费 `Future`，Task 入口主动捕获并记录 Exception，或者扩展 Thread Pool 集中处理。 Log 要带上 Task Type、业务 ID 和 Trace ID，不能只打印一段脱离业务的 Stack Trace。

## Thread Pool 应该 Monitoring 哪些 Metric？

`ThreadPoolExecutor` 自带的统计信息可以看到 Current Thread 数、Active Thread 数、历史 Maximum Pool Size、Task 总数、完成 Task 数和 Queue Length。这些值多数是近似值，适合 Monitoring 和趋势分析，不适合参与要求严格一致性的业务判断。

生产 Monitoring 至少应覆盖：

- **Task 流量**：提交速率、开始执行速率和完成速率。
- **Thread State**：Current Thread 数、Active Thread 数、历史 Maximum Pool Size 和活跃度。
- **Queue 状态**：当前 Length、总 Capacity、使用率和 Queue 等待时间。
- **Task 结果**：执行时间、成功数、Exception 数、Timeout 数、取消数和拒绝数。
- **关联资源**：CPU、Heap Memory、Database Connection Pool、HTTP Connection Pool 和下游延迟。

Task 总数和完成 Task 数是累计值，需要计算一段时间内的差值才能得到速率。 Queue Length 也要结合变化趋势：Queue 都是 100，一个正在从 500 降到 100，另一个从 10 涨到 100，风险并不相同。

排队时间和执行时间不能混成一个 Metric。排队时间上涨、执行时间稳定，多半是 Capacity 不足或流量突增；执行时间先上涨，随后 Queue 开始增长，应优先检查 Task 逻辑和下游。可以在提交 Task 时记录 Timestamp，在 Task 真正开始和结束时分别计算两段耗时。

Queue 在一个采集周期里突然变长，可能只是流量尖峰，很快就会回落。 Alert 除了 Threshold，还应加上持续时间，并确认 Backlog 能不能自行消化。 Queue 长时间处于高水位、完成速率连续低于提交速率，说明旧 Task 越积越多；P99 排队时间接近 Task 可等待时间时，即使 Queue 没满，也应该 Alert。拒绝次数要单独统计。核心 Task 出现拒绝立即 Alert，允许丢弃的 Task 再按拒绝比例和持续时间设置 Threshold。

## 动态调参能解决什么问题？

Task 耗时没有明显变化，CPU、Connection Pool 和下游也还有余量，只是当前 Concurrency 赶不上提交速度，这时可以调整 Thread Count。要是 Thread 都卡在 Database Connection、慢 SQL 或下游 Timeout 上，调大 Thread Count 只会多出一批等待者。

`ThreadPoolExecutor` 的部分 Parameter 可以在线修改，不过生效方式并不相同。运行期间可以修改 `corePoolSize`、`maximumPoolSize`、`keepAliveTime`、Rejection Policy 和 Thread Factory。调大 Core Pool Size 后，只要 Queue 中还有 Task，Thread Pool 就会按需创建新 Thread。 Core Pool Size 或 Maximum Pool Size 调小，不会 Interrupt 正在执行的 Task；超出的 Worker Thread 会在空闲后退出。新设置的 Thread Factory 只影响此后创建的 Thread，不会重命名已经存在的 Worker Thread。

修改 Core Pool Size 和 Maximum Pool Size 时要注意顺序：

- 新的 Core Pool Size 高于旧的 Maximum Pool Size，先调大 Maximum Pool Size，再调整 Core Pool Size。
- 新的 Maximum Pool Size 低于旧的 Core Pool Size，先调小 Core Pool Size，再调整 Maximum Pool Size。

否则，Parameter 校验会抛出 `IllegalArgumentException`。

JDK 没有提供修改现有 Blocking Queue Capacity 的通用 Method。需要调整 Queue 时，可以使用经过验证的可变 Capacity Queue 或动态 Thread Pool 框架；自行修改 `LinkedBlockingQueue` 实现要同时处理 Concurrency Visibility、Enqueue 条件和唤醒逻辑，不能只改一个 Capacity Field。

美团技术团队在[《Java Thread Pool 实现原理及其在美团业务中的实践》](https://tech.meituan.com/2020/04/02/java-pooling-pratice-in-meituan.html)中介绍过 Thread Pool Parameter 动态配置和 Monitoring Alert 的实现思路。开源方案中，[Hippo4j](https://github.com/opengoofy/hippo4j) 和 [Dynamic TP](https://github.com/dromara/dynamic-tp) 都提供了动态配置、Monitoring 和 Alert 能力。引入前仍要核对项目使用的 Thread Pool Type、配置中心、框架版本和故障 Fallback 方式。

业务高峰前预调 Parameter，最好以历史 Metric 或压测结果为依据。调整后，如果完成速率没有提高，反而出现 CPU 上涨、Connection Pool 等待或下游错误率增加，应当回滚 Parameter，继续检查 Task 本身和依赖。

线上修改时应保留 Parameter 上下限、变更记录、灰度范围和回滚值。每次尽量只改一个主要 Variable，观察 Task 完成速率、排队时间、拒绝数和下游压力，再决定是否继续调整。

## 还有哪些容易忽略的问题？

### 不要重复创建 Thread Pool

Thread Pool 用于复用 Thread，不应在每个请求或每次 Method Invocation 中重新创建。频繁创建会增加 Thread 启动和销毁 Overhead，也容易遗漏关闭逻辑。应用级 Thread Pool 通常交给 Container 统一管理 Lifecycle。

Spring 的 `@Async`、定时 Task、Web Container 和部分客户端内部也会使用 Thread Pool。项目没有显式调用 `new ThreadPoolExecutor()`，不代表不存在需要配置和 Monitoring 的 Thread Pool。

### 不要让长 Task 占满 Shared Thread Pool

长时间 Blocking 的 Task 会占用 Worker Thread，后续短 Task 只能排队。报表导出、文件处理和慢外部 Interface 适合使用独立的执行资源，或者改成 Asynchronous Task 并向用户返回 Task 状态。

`CompletableFuture` 只负责 Task 编排，不会把 Blocking 式网络请求变成非 Blocking Operation。没有显式指定 `Executor` 的 Asynchronous Method 通常使用公共 Thread Pool，公共 Thread Pool 被 Blocking 后，还可能影响应用中的其他 Asynchronous Task。

### 清理 Thread Context

Thread Pool 会复用 Thread。前一个 Task 写入 `ThreadLocal` 后没有清理，后续 Task 可能在同一 Thread 上读到旧值，还可能让 Large Object 长期被 Worker Thread Reference。

Context 传递和清理应由统一的 Task 包装器处理，在 `finally` 中恢复或删除原值。 Log MDC、登录信息和租户信息都要考虑这个问题。跨 Thread 传递场景也可以使用 [TransmittableThreadLocal](https://github.com/alibaba/transmittable-thread-local)，但仍要确认包装方式和清理时机。

### 正确关闭 Thread Pool

`shutdown()` 不再接收新 Task，会继续处理已经提交的 Task；`shutdownNow()` 会尝试 Interrupt 正在执行的 Task，并返回尚未开始执行的 Task。两者都不会等待 Thread Pool 彻底终止。

```java
executor.shutdown();
try {
    if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
        executor.shutdownNow();
        if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
            System.err.println("线程池未能正常退出");
        }
    }
} catch (InterruptedException e) {
    executor.shutdownNow();
    Thread.currentThread().interrupt();
}
```

Task 需要正确响应 Interrupt，否则 `shutdownNow()` 也不能保证立即停止。应用关闭期间还要决定 Queue 中的 Task 能否丢失；不能丢的业务 Task 不应只存在 Process 内存里。

## 使用 Virtual Thread 后还需要传统 Thread Pool 吗？

Virtual Thread 适合包含大量 Blocking 等待的 Task。它创建和切换的成本比 Platform Thread 低，通常采用每个 Task 一个 Virtual Thread 的方式，不要把 Virtual Thread 放进固定大小的池里复用。

需要限制 Database 或下游 Interface Concurrency 时，继续使用 Connection Pool、`Semaphore`、Rate Limiting 器等机制约束具体资源。 Virtual Thread 数量很多，也不会增加 Database Connection 数、CPU 核数或下游 Interface Capacity。

传统 Platform Thread 池仍适用于 CPU 密集型 Task、需要固定调度 Thread 的 Task，以及必须显式控制 Platform Thread 和 Work Queue 的组件。项目是否迁移还要看 JDK 版本、框架支持、Monitoring 工具和现有 Asynchronous 模型。详细说明可以参考 [Virtual Thread 常见问题总结](./virtual-thread.md)。

## 面试中怎么回答 Thread Pool Parameter 配置？

回答 Thread Pool Parameter 时，可以从 Task 和系统 Capacity 出发：先根据高峰 Task 提交速率和 Task 耗时估算 Concurrency 需求，再区分计算时间和 I/O 等待时间；Thread Count 还要受 CPU、Database Connection Pool、HTTP Connection Pool 及下游 Rate Limiting 约束。 Queue 只吸收短时突发，Capacity 要同时满足业务等待期限和内存限制。初始 Parameter 确定后，通过压测和线上 Monitoring 观察提交速率、完成速率、排队时间、执行时间和拒绝次数，再逐步调整。

面试官继续追问 Queue 堆积时，不要只回答扩大 Thread Pool。先比较 Task 提交速率和完成速率，再看执行时间、Thread Stack、CPU、Connection Pool 与下游延迟。流量上涨可以 Rate Limiting 或扩 Instance；Task 变慢要处理 SQL、Lock 或下游故障；Task 已经过期时应快速失败或转入补偿。动态调参只能处理 Capacity 配置不合适，不能代替 Timeout、隔离、Rate Limiting 和下游治理。

## 参考

- [ThreadPoolExecutor API 文档](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html)
- [Future API 文档](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Future.html)
- [CompletableFuture API 文档](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/CompletableFuture.html)
- [JEP 444：Virtual Threads](https://openjdk.org/jeps/444)
- [Java Thread Pool 实现原理及其在美团业务中的实践](https://tech.meituan.com/2020/04/02/java-pooling-pratice-in-meituan.html)
- 《Java Concurrent Programming 实战》

<!-- @include: @article-footer.snippet.md -->
