---
title: Java Thread Pool 详解
description: Java Thread Pool 详解：深入讲解ThreadPoolExecutor核心 Parameter 配置、Executor框架体系、Task Queue 选择、Rejection Policy、Thread Pool 工作原理及最佳实践。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: Java Thread Pool,ThreadPoolExecutor,Executor框架,Thread Pool Parameter,Rejection Policy,Task Queue,Thread Pool 原理
---

<!-- markdownlint-disable MD024 -->

池化技术想必大家已经屡见不鲜了，Thread Pool、Database Connection Pool、HTTP Connection Pool 等等都是对这个思想的应用。池化技术的思想主要是为了减少每次获取资源的消耗，提高对资源的利用率。

这篇文章我会详细介绍一下 Thread Pool 的基本概念以及核心原理。

## Thread Pool 介绍

池化技术想必大家已经屡见不鲜了，Thread Pool、Database Connection Pool、HTTP Connection Pool 等等都是对这个思想的应用。池化技术的思想主要是为了减少每次获取资源的消耗，提高对资源的利用率。

Thread Pool 提供了一种限制和管理资源（包括执行一个 Task）的方式。 每个 Thread Pool 还维护一些基本统计信息，例如已完成 Task 的数量。使用 Thread Pool 主要带来以下几个好处：

1. **降低资源消耗**：Thread Pool 里的 Thread 是可以重复利用的。一旦 Thread 完成了某个 Task，它不会立即销毁，而是回到池子里等待下一个 Task。这就避免了频繁创建和销毁 Thread 带来的 Overhead。
2. **提高响应速度**：因为 Thread Pool 里通常会维护一定数量的 Core Thread（或者说“常驻工人”），Task 来了之后，可以直接交给这些已经存在的、空闲的 Thread 去执行，省去了创建 Thread 的时间，Task 能够更快地得到处理。
3. **提高 Thread 的可管理性**：Thread Pool 允许我们统一管理池中的 Thread。我们可以配置 Thread Pool 的大小（Core Pool Size、Maximum Pool Size）、Task Queue 的 Type 和大小、Rejection Policy 等。这样就能控制 Concurrency Thread 的总量，防止资源耗尽，保证系统的稳定性。同时，Thread Pool 通常也提供了 Monitoring Interface，方便我们了解 Thread Pool 的运行状态（比如有多少 Active Thread、多少 Task 在排队等），便于调优。

## Executor 框架介绍

`Executor` 框架是 Java5 之后引进的，在 Java 5 之后，通过 `Executor` 来启动 Thread 比使用 `Thread` 的 `start` Method 更好，除了更易管理，效率更好（用 Thread Pool 实现，节约 Overhead）外，还有关键的一点：有助于避免 this 逃逸问题。

> this 逃逸是指在 Constructor 返回之前其他 Thread 就持有该 Object 的 Reference，调用尚未构造完全的 Object 的 Method 可能引发令人疑惑的错误。

`Executor` 框架不仅包括了 Thread Pool 的管理，还提供了 Thread Factory、Queue 以及 Rejection Policy 等，`Executor` 框架让 Concurrent Programming 变得更加简单。

`Executor` 框架结构主要由三大部分组成：

**1、Task(`Runnable` /`Callable`)**

执行 Task 需要实现的 **`Runnable` Interface** 或 **`Callable` Interface**。**`Runnable` Interface**或 **`Callable` Interface** Implementation Class 都可以被 **`ThreadPoolExecutor`** 或 **`ScheduledThreadPoolExecutor`** 执行。

**2、Task 的执行(`Executor`)**

如下图所示，包括 Task 执行机制的核心 Interface **`Executor`**，以及 Inheritance 自 `Executor` Interface 的 **`ExecutorService` Interface。`ThreadPoolExecutor`** 和 **`ScheduledThreadPoolExecutor`** 这两个关键 Class 实现了 **`ExecutorService`** Interface。

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/executor-class-diagram.png)

这里提了很多底层的 Class 关系，但是，实际上我们需要更多关注的是 `ThreadPoolExecutor` 这个 Class，这个 Class 在我们实际使用 Thread Pool 的过程中，使用频率还是非常高的。

**注意：** 通过查看 `ScheduledThreadPoolExecutor` 源代码我们发现 `ScheduledThreadPoolExecutor` 实际上是 Inherit 了 `ThreadPoolExecutor` 并实现了 `ScheduledExecutorService`，而 `ScheduledExecutorService` 又实现了 `ExecutorService`，正如我们上面给出的 Class 关系图显示的一样。

`ThreadPoolExecutor` Class 描述:

```java
//AbstractExecutorService实现了ExecutorService接口
public class ThreadPoolExecutor extends AbstractExecutorService
```

`ScheduledThreadPoolExecutor` Class 描述:

```java
//ScheduledExecutorService继承ExecutorService接口
public class ScheduledThreadPoolExecutor
        extends ThreadPoolExecutor
        implements ScheduledExecutorService
```

**3、Asynchronous 计算的结果(`Future`)**

**`Future`** Interface 以及 `Future` Interface 的 Implementation Class **`FutureTask`** Class 都可以代表 Asynchronous 计算的结果。

当我们把 **`Runnable` Interface** 或 **`Callable` Interface** 的 Implementation Class 提交给 **`ThreadPoolExecutor`** 或 **`ScheduledThreadPoolExecutor`** 执行时，调用 `submit()` 会返回一个实现了 `Future` Interface 的 Object。具体实现不一定是 `FutureTask`，例如定时 Thread Pool 会返回相应的 `RunnableScheduledFuture` 实现。

**`Executor` 框架的使用示意图**：

![Executor 框架的使用示意图](./images/java-thread-pool-summary/Executor框架的使用示意图.png)

1. Main Thread 首先要创建实现 `Runnable` 或者 `Callable` Interface 的 Task Object。
2. 把创建完成的实现 `Runnable`/`Callable` Interface 的 Object 直接交给 `ExecutorService` 执行: `ExecutorService.execute（Runnable command）`）或者也可以把 `Runnable` Object 或 `Callable` Object 提交给 `ExecutorService` 执行（`ExecutorService.submit（Runnable task）` 或 `ExecutorService.submit（Callable <T> task）`）。
3. 如果执行 `ExecutorService.submit(...)`，`ExecutorService` 将返回一个实现 `Future` Interface 的 Object。由于 `FutureTask` 同时实现了 `Runnable` 和 `Future`，我们也可以自行创建 `FutureTask`，然后直接交给 `ExecutorService` 执行。
4. 最后，Main Thread 可以执行 `Future.get()` Method 来等待 Task 执行完成，也可以执行 `Future.cancel(boolean mayInterruptIfRunning)` 来尝试取消 Task。

## ThreadPoolExecutor Class 介绍（重要）

Thread Pool Implementation Class `ThreadPoolExecutor` 是 `Executor` 框架最核心的 Class。

### Thread Pool Parameter 分析

`ThreadPoolExecutor` Class 中提供的四个 Constructor。我们来看最长的那个，其余三个都是在这个 Constructor 的基础上产生（其他几个 Constructor 说白点都是给定某些默认 Parameter 的 Constructor 比如默认制定 Rejection Policy 是什么）。

```java
    /**
     * 用给定的初始参数创建一个新的ThreadPoolExecutor。
     */
    public ThreadPoolExecutor(int corePoolSize,//线程池的核心线程数量
                              int maximumPoolSize,//线程池的最大线程数
                              long keepAliveTime,//当线程数大于核心线程数时，多余的空闲线程存活的最长时间
                              TimeUnit unit,//时间单位
                              BlockingQueue<Runnable> workQueue,//任务队列，用来储存等待执行任务的队列
                              ThreadFactory threadFactory,//线程工厂，用来创建线程，一般默认即可
                              RejectedExecutionHandler handler//拒绝策略，当提交的任务过多而不能及时处理时，我们可以定制策略来处理任务
                               ) {
        if (corePoolSize < 0 ||
            maximumPoolSize <= 0 ||
            maximumPoolSize < corePoolSize ||
            keepAliveTime < 0)
            throw new IllegalArgumentException();
        if (workQueue == null || threadFactory == null || handler == null)
            throw new NullPointerException();
        this.corePoolSize = corePoolSize;
        this.maximumPoolSize = maximumPoolSize;
        this.workQueue = workQueue;
        this.keepAliveTime = unit.toNanos(keepAliveTime);
        this.threadFactory = threadFactory;
        this.handler = handler;
    }
```

下面这些 Parameter 非常重要，在后面使用 Thread Pool 的过程中你一定会用到！所以，务必拿着小本本记清楚。

`ThreadPoolExecutor` 3 个最重要的 Parameter：

- `corePoolSize`：Thread Pool 优先维持的 Worker Thread 数量。默认情况下 Thread 按需创建；Worker Thread 数达到该值后，新 Task 通常先进入 Queue。
- `maximumPoolSize` : Task Queue 中存放的 Task 达到 Queue Capacity 的时候，当前可以同时运行的 Thread Count 变为 Maximum Pool Size。
- `workQueue`: 新 Task 来的时候会先判断当前运行的 Thread Count 是否达到 Core Pool Size，如果达到的话，新 Task 就会被存放在 Queue 中。

`ThreadPoolExecutor` 其他常见 Parameter :

- `keepAliveTime`:Thread Pool 中的 Thread Count 大于 `corePoolSize` 的时候，如果这时没有新的 Task 提交，Core Thread 外的 Thread 不会立即销毁，而是会等待，直到等待的时间超过了 `keepAliveTime` 才会被回收销毁。
- `unit` : `keepAliveTime` Parameter 的时间单位。
- `threadFactory` :executor 创建新 Thread 的时候会用到。
- `handler` :Rejection Policy（后面会单独详细介绍一下）。

下面这张图可以加深你对 Thread Pool 中各个 Parameter 的相互关系的理解（图片来源：《Java Performance Tuning 实战》）：

![Thread Pool 各个 Parameter 的关系](https://oss.javaguide.cn/github/javaguide/java/concurrent/relationship-between-thread-pool-parameters.png)

### Thread Pool Lifecycle 状态

`ThreadPoolExecutor` 使用 `ctl` Variable（`AtomicInteger` Type）同时管理 Thread Pool 的运行状态和 Worker Thread 数量。 Thread Pool 共有 5 种状态：

- **运行中（`RUNNING`）**：接受新 Task，并处理 Queue 中的 Task。 Thread Pool 创建后的初始状态。
- **关闭（`SHUTDOWN`）**：不再接受新 Task，但会继续处理 Queue 中已有的 Task。调用 `shutdown()` 后进入。
- **停止（`STOP`）**：不接受新 Task，不处理 Queue 中的 Task，并尝试 Interrupt 正在执行的 Task。调用 `shutdownNow()` 后进入。
- **整理中（`TIDYING`）**：所有 Task 已终止，Worker Thread 数为 0，即将执行 `terminated()` Hook Method。
- **已终止（`TERMINATED`）**：`terminated()` Method 执行完毕，Thread Pool 彻底终结。

状态只能单向流转：运行中（`RUNNING`）→ 关闭（`SHUTDOWN`）→ 整理中（`TIDYING`）→ 已终止（`TERMINATED`），或者运行中（`RUNNING`）→ 停止（`STOP`）→ 整理中（`TIDYING`）→ 已终止（`TERMINATED`）。在关闭（`SHUTDOWN`）状态下再调用 `shutdownNow()` 也会转为停止（`STOP`）。

`shutdown()` 是“温和关闭”——Interrupt Idle Thread，但 Queue 中的 Task 仍会执行完毕。`shutdownNow()` 是“强制关闭”——尝试 Interrupt 所有正在运行的 Thread，并将 Queue 中未执行的 Task 以 `List<Runnable>` 返回。`terminated()` 是一个空的 Hook Method，可以通过 Inheritance `ThreadPoolExecutor` 来 Override 它，用于在 Thread Pool 终止后做清理工作。

### Worker Worker Thread 机制

`ThreadPoolExecutor` 将每个 Worker Thread Encapsulation 为 Inner Class `Worker`。`Worker` Inherit 了 AbstractQueuedSynchronizer (AQS) 并实现了 `Runnable` Interface。

**为什么 `Worker` 要 Inheritance AQS？** `Worker` 实现了一个**不 Reentrant 的 Exclusive Lock**，用于配合 `shutdown()` 区分 Thread 是空闲还是正在工作——正在执行 Task 的 Worker Hold Lock，`shutdown()` 对每个 Worker 尝试 `tryLock()`，失败则说明该 Thread 正在工作，不会被 Interrupt。

**Worker 的 Lifecycle：**

1. **创建**：`execute()` 判断需要新建 Thread 时，调用 `addWorker()` 创建 `Worker` Instance，内部通过 `ThreadFactory` 创建 Thread。
2. **运行**：Thread 启动后进入 `runWorker()` 的 `while` Loop，通过 `getTask()` 不断从 Queue 取 Task 执行。Worker 并不会被永久标记为“核心”或“非核心”；当允许 Core Thread Timeout，或者当前 Worker Thread 数大于 `corePoolSize` 时，`getTask()` 才会使用带 Timeout 的 `workQueue.poll(keepAliveTime, unit)`，否则使用 `workQueue.take()` Blocking 等待。
3. **退出**：`getTask()` 返回 `null` 时 Worker 退出 Loop 并清理。返回 `null` 的情况包括：Thread Pool 处于停止（`STOP`）状态、Thread Pool 处于关闭（`SHUTDOWN`）状态且 Queue 为空、Non-core Thread 等待 Timeout、或运行时缩小了 `maximumPoolSize`。如果退出后 Worker Thread 数低于核心数，会自动补充一个新 Thread。

**`ThreadPoolExecutor` Rejection Policy 定义:**

当 Thread Pool 已经关闭，或者当前 Worker Thread 数达到上限且 Queue 也无法接收新 Task 时，`ThreadPoolExecutor` 会调用 Rejection Policy：

- `ThreadPoolExecutor.AbortPolicy`：抛出 `RejectedExecutionException` 来拒绝新 Task 的处理。
- `ThreadPoolExecutor.CallerRunsPolicy`：调用执行自己的 Thread 运行 Task，也就是直接在调用 `execute` Method 的 Thread 中运行(`run`)被拒绝的 Task，如果执行程序已关闭，则会丢弃该 Task。因此这种策略会降低对于新 Task 提交速度，影响程序的整体 Performance。如果您的应用程序可以承受此延迟并且你要求任何一个 Task 请求都要被执行的话，你可以选择这个策略。
- `ThreadPoolExecutor.DiscardPolicy`：不处理新 Task，直接丢弃掉。
- `ThreadPoolExecutor.DiscardOldestPolicy`：此策略将丢弃最早的未处理的 Task 请求。

举个例子：

举个例子：Spring 通过 `ThreadPoolTaskExecutor` 或者我们直接通过 `ThreadPoolExecutor` 的 Constructor 创建 Thread Pool 的时候，当我们不指定 `RejectedExecutionHandler` Rejection Policy 来配置 Thread Pool 的时候，默认使用的是 `AbortPolicy`。在这种 Rejection Policy 下，如果 Queue 满了，`ThreadPoolExecutor` 将抛出 `RejectedExecutionException` Exception 来拒绝新来的 Task，这代表你将丢失对这个 Task 的处理。在 Thread Pool 仍处于运行状态时，`CallerRunsPolicy` 会将被拒绝的 Task 交给 Caller Thread 执行；Thread Pool 已经关闭时，该策略会直接丢弃 Task。

```java
public static class CallerRunsPolicy implements RejectedExecutionHandler {

        public CallerRunsPolicy() { }

        public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
            if (!e.isShutdown()) {
                // 直接主线程执行，而不是线程池中的线程执行
                r.run();
            }
        }
    }
```

### 4 种 Rejection Policy 的实际应用场景

上面介绍了 4 种内置 Rejection Policy 的基本行为，下面结合实际生产经验，说明它们各自适合什么场景：

**`AbortPolicy`**：适用于对 Task 丢失零容忍的核心业务（如支付、转账）。 Task 被拒绝时调用方会收到 `RejectedExecutionException`，必须在业务代码中捕获并做补偿（如 Retry 或持久化到 Database 后补偿执行）。《阿里巴巴 Java 开发手册》指出，如果不做任何配置，Queue 满时会直接抛 Exception，开发者必须显式处理。

**`CallerRunsPolicy`**：适用于不允许丢弃 Task、且允许降低提交速度的场景。由于 Task 在 Caller Thread 中执行，调用者在此期间无法提交新 Task，形成了一种天然的**Backpressure（back-pressure）**机制。美团技术团队在《Java Thread Pool 实现原理及其在美团业务中的实践》中提到，这是他们线上业务中较常使用的 Rejection Policy。但需要注意：如果提交 Task 的 Thread 是 Web Container 的请求处理 Thread（如 Tomcat 的 Worker Thread），会导致该请求响应时间显著增加，在延迟敏感的场景中需谨慎。

**`DiscardPolicy`**：适用于 Task 允许丢失的非关键路径，如 Log Asynchronous 写入、Monitoring Metric 上报。该策略完全静默（空实现），被拒绝的 Task 不会留下任何痕迹，排查问题时可能难以发现 Task 丢失。

**`DiscardOldestPolicy`**：适用于只关心最新数据、旧 Task 可被覆盖的场景，如实时行情推送、传感器数据采集。需要注意：如果使用了 `PriorityBlockingQueue`，`poll()` 弹出的是优先级最高的 Task 而非最旧的 Task，可能导致重要 Task 被误丢。

**生产环境中的常见做法**：以上 4 种内置策略往往不能完全满足需求。Dubbo 框架自定义了 `AbortPolicyWithReport` 策略，在抛 Exception 之外还会将被拒绝的 Task 信息 dump 到本地文件，方便事后排查。美团技术团队建议对 Thread Pool 的拒绝次数进行 Monitoring 和 Alert。常见的自定义策略思路包括：将被拒绝的 Task 写入 Database 或 Message Queue 后续补偿消费、递增 Monitoring Counter 上报 Prometheus、或者调用 `workQueue.put(r)` Blocking Wait Queue 有空位（Netty 中有类似实现）。

### Thread Pool 创建的两种方式

在 Java 中，创建 Thread Pool 主要有两种方式：

**方式一：通过 `ThreadPoolExecutor` Constructor 直接创建（推荐）**

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/threadpoolexecutor-construtors.png)

图中的“Default Thread Factory”和“Default Rejection Policy”，指的是当前 Constructor 没有显式传入对应 Parameter 时，`ThreadPoolExecutor` 会使用默认实现，并不是 Method 和说明错位。

这是最推荐的方式，因为它允许开发者明确指定 Thread Pool 的核心 Parameter，对 Thread Pool 的运行行为有更精细的控制，从而避免资源耗尽的风险。

**方式二：通过 `Executors` Utility Class 创建（不推荐用于生产环境）**

`Executors` Utility Class 提供的创建 Thread Pool 的 Method 如下图所示：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/executors-new-thread-pool-methods.png)

可以看出，通过 `Executors` Utility Class 可以创建多种 Type 的 Thread Pool，包括：

- `FixedThreadPool`：正常运行时最多使用固定数量的 Worker Thread。 Thread 可以因 Exception 终止后被替换，Thread Pool 关闭时也会退出，因此并非在整个 Lifecycle 中数量始终不变。当有一个新的 Task 提交时，Thread Pool 中若有 Idle Thread，则立即执行。若没有，则新的 Task 会被暂存在一个 Task Queue 中，待有 Thread 空闲时，便处理在 Task Queue 中的 Task。
- `SingleThreadExecutor`： 只有一个 Thread 的 Thread Pool。若多余一个 Task 被提交到该 Thread Pool，Task 会被保存在一个 Task Queue 中，待 Thread 空闲，按先入先出的顺序执行 Queue 中的 Task。
- `CachedThreadPool`： 可根据实际情况调整 Thread Count 的 Thread Pool。 Thread Pool 的 Thread Count 不确定，但若有 Idle Thread 可以复用，则会优先使用可复用的 Thread。若所有 Thread 均在工作，又有新的 Task 提交，则会创建新的 Thread 处理 Task。所有 Thread 在当前 Task 执行完毕后，将返回 Thread Pool 进行复用。
- `ScheduledThreadPool`：给定的延迟后运行 Task 或者定期执行 Task 的 Thread Pool。

《阿里巴巴 Java 开发手册》强制 Thread Pool 不允许使用 `Executors` 去创建，而是通过 `ThreadPoolExecutor` Constructor 的方式，这样的处理方式让写的同学更加明确 Thread Pool 的运行规则，规避资源耗尽的风险

`Executors` 返回 Thread Pool Object 的弊端如下（后文会详细介绍到）：

- `FixedThreadPool` 和 `SingleThreadExecutor`:使用的是 Blocking Queue `LinkedBlockingQueue`，Task Queue 最大 Length 为 `Integer.MAX_VALUE`，可以看作是无界的，可能堆积大量的请求，从而导致 Out of Memory (OOM)。
- `CachedThreadPool`:使用的是 Synchronous Queue `SynchronousQueue`, 允许创建的 Thread Count 为 `Integer.MAX_VALUE`，如果 Task 数量过多且执行速度较慢，可能会创建大量的 Thread，从而导致 OOM。
- `ScheduledThreadPool` 和 `SingleThreadScheduledExecutor`:使用的无界的延迟 Blocking Queue `DelayedWorkQueue`，Task Queue 最大 Length 为 `Integer.MAX_VALUE`,可能堆积大量的请求，从而导致 OOM。

```java
public static ExecutorService newFixedThreadPool(int nThreads) {
    // LinkedBlockingQueue 的默认长度为 Integer.MAX_VALUE，可以看作是无界的
    return new ThreadPoolExecutor(nThreads, nThreads,0L, TimeUnit.MILLISECONDS,new LinkedBlockingQueue<Runnable>());

}

public static ExecutorService newSingleThreadExecutor() {
    // LinkedBlockingQueue 的默认长度为 Integer.MAX_VALUE，可以看作是无界的
    return new FinalizableDelegatedExecutorService (new ThreadPoolExecutor(1, 1,0L, TimeUnit.MILLISECONDS,new LinkedBlockingQueue<Runnable>()));

}

// 同步队列 SynchronousQueue，没有容量，最大线程数是 Integer.MAX_VALUE`
public static ExecutorService newCachedThreadPool() {

    return new ThreadPoolExecutor(0, Integer.MAX_VALUE,60L, TimeUnit.SECONDS,new SynchronousQueue<Runnable>());

}

// DelayedWorkQueue（延迟阻塞队列）
public static ScheduledExecutorService newScheduledThreadPool(int corePoolSize) {
    return new ScheduledThreadPoolExecutor(corePoolSize);
}
public ScheduledThreadPoolExecutor(int corePoolSize) {
    super(corePoolSize, Integer.MAX_VALUE, 0, NANOSECONDS,
          new DelayedWorkQueue());
}
```

### Thread Pool 常用的 Blocking Queue 总结

新 Task 来的时候会先判断当前运行的 Thread Count 是否达到 Core Pool Size，如果达到的话，新 Task 就会被存放在 Queue 中。

不同的 Thread Pool 会选用不同的 Blocking Queue，我们可以结合内置 Thread Pool 来分析。

- Capacity 为 `Integer.MAX_VALUE` 的 `LinkedBlockingQueue`（无界 Queue）：`FixedThreadPool` 和 `SingleThreadExecutor`。`FixedThreadPool` 最多只能创建 Core Pool Size 的 Thread（Core Pool Size 和 Maximum Pool Size 相等），`SingleThreadExecutor` 只能创建一个 Thread（Core Pool Size 和 Maximum Pool Size 都是 1），二者的 Task Queue 在实际使用中几乎不会被放满。
- `SynchronousQueue`（Synchronous Queue）：`CachedThreadPool`。`SynchronousQueue` 没有 Capacity，不存储元素，目的是保证对于提交的 Task，如果有 Idle Thread，则使用 Idle Thread 来处理；否则新建一个 Thread 来处理 Task。也就是说，`CachedThreadPool` 的 Maximum Pool Size 是 `Integer.MAX_VALUE`，可以理解为 Thread Count 是可以无限扩展的，可能会创建大量 Thread，从而导致 OOM。
- `DelayedWorkQueue`（延迟 Blocking Queue）：`ScheduledThreadPool` 和 `SingleThreadScheduledExecutor`。`DelayedWorkQueue` 的内部元素并不是按照放入的时间排序，而是会按照延迟的时间长短对 Task 进行排序，内部采用的是“Heap”的 Data Structure，可以保证每次 Dequeue 的 Task 都是当前 Queue 中执行时间最靠前的。`DelayedWorkQueue` 添加元素满了之后会自动 Resize 原来 Capacity 的 1/2，即永远不会 Blocking，最大 Resize Reachable `Integer.MAX_VALUE`，所以最多只能创建 Core Pool Size 的 Thread。

## Thread Pool 原理分析（重要）

我们上面讲解了 `Executor` 框架以及 `ThreadPoolExecutor` Class，下面让我们实战一下，来通过写一个 `ThreadPoolExecutor` 的小 Demo 来回顾上面的内容。

### Thread Pool 示例代码

首先创建一个 `Runnable` Interface 的 Implementation Class（当然也可以是 `Callable` Interface，我们后面会介绍两者的区别。）

`MyRunnable.java`

```java
import java.util.Date;

/**
 * 这是一个简单的Runnable类，需要大约5秒钟来执行其任务。
 * @author shuang.kou
 */
public class MyRunnable implements Runnable {

    private String command;

    public MyRunnable(String s) {
        this.command = s;
    }

    @Override
    public void run() {
        System.out.println(Thread.currentThread().getName() + " Start. Time = " + new Date());
        processCommand();
        System.out.println(Thread.currentThread().getName() + " End. Time = " + new Date());
    }

    private void processCommand() {
        try {
            Thread.sleep(5000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    @Override
    public String toString() {
        return this.command;
    }
}

```

编写测试程序，我们这里以阿里巴巴推荐的使用 `ThreadPoolExecutor` Constructor 自定义 Parameter 的方式来创建 Thread Pool。

`ThreadPoolExecutorDemo.java`

```java
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

public class ThreadPoolExecutorDemo {

    private static final int CORE_POOL_SIZE = 5;
    private static final int MAX_POOL_SIZE = 10;
    private static final int QUEUE_CAPACITY = 100;
    private static final Long KEEP_ALIVE_TIME = 1L;
    public static void main(String[] args) {

        //使用阿里巴巴推荐的创建线程池的方式
        //通过ThreadPoolExecutor构造函数自定义参数创建
        ThreadPoolExecutor executor = new ThreadPoolExecutor(
                CORE_POOL_SIZE,
                MAX_POOL_SIZE,
                KEEP_ALIVE_TIME,
                TimeUnit.SECONDS,
                new ArrayBlockingQueue<>(QUEUE_CAPACITY),
                new ThreadPoolExecutor.CallerRunsPolicy());

        for (int i = 0; i < 10; i++) {
            //创建WorkerThread对象（WorkerThread类实现了Runnable 接口）
            Runnable worker = new MyRunnable("" + i);
            //执行Runnable
            executor.execute(worker);
        }
        //终止线程池
        executor.shutdown();
        while (!executor.isTerminated()) {
        }
        System.out.println("Finished all threads");
    }
}

```

可以看到我们上面的代码指定了：

- `corePoolSize`: Core Pool Size 为 5。
- `maximumPoolSize`：Maximum Pool Size 10
- `keepAliveTime` : 等待时间为 1L。
- `unit`: 等待时间的单位为 TimeUnit.SECONDS。
- `workQueue`：Task Queue 为 `ArrayBlockingQueue`，并且 Capacity 为 100;
- `handler`:Rejection Policy 为 `CallerRunsPolicy`。

**输出结构**：

```plain
pool-1-thread-3 Start. Time = Sun Apr 12 11:14:37 CST 2020
pool-1-thread-5 Start. Time = Sun Apr 12 11:14:37 CST 2020
pool-1-thread-2 Start. Time = Sun Apr 12 11:14:37 CST 2020
pool-1-thread-1 Start. Time = Sun Apr 12 11:14:37 CST 2020
pool-1-thread-4 Start. Time = Sun Apr 12 11:14:37 CST 2020
pool-1-thread-3 End. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-4 End. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-1 End. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-5 End. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-1 Start. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-2 End. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-5 Start. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-4 Start. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-3 Start. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-2 Start. Time = Sun Apr 12 11:14:42 CST 2020
pool-1-thread-1 End. Time = Sun Apr 12 11:14:47 CST 2020
pool-1-thread-4 End. Time = Sun Apr 12 11:14:47 CST 2020
pool-1-thread-5 End. Time = Sun Apr 12 11:14:47 CST 2020
pool-1-thread-3 End. Time = Sun Apr 12 11:14:47 CST 2020
pool-1-thread-2 End. Time = Sun Apr 12 11:14:47 CST 2020
Finished all threads  // 任务全部执行完了才会跳出来，因为executor.isTerminated()判断为true了才会跳出while循环，当且仅当调用 shutdown() 方法后，并且所有提交的任务完成后返回为 true

```

### Thread Pool 原理分析

我们通过前面的代码输出结果可以看出：**Thread Pool 首先会先执行 5 个 Task，然后这些 Task 有 Task 被执行完的话，就会去拿新的 Task 执行。** 大家可以先通过上面讲解的内容，分析一下到底是咋回事？（自己独立思考一会）

现在，我们就分析上面的输出内容来简单分析一下 Thread Pool 原理。

为了搞懂 Thread Pool 的原理，我们需要首先分析一下 `execute` Method。 在示例代码中，我们使用 `executor.execute(worker)` 来提交一个 Task 到 Thread Pool 中去。

这个 Method 非常重要，下面我们来看看它的源码：

```java
   // 存放线程池的运行状态 (runState) 和线程池内有效线程的数量 (workerCount)
   private final AtomicInteger ctl = new AtomicInteger(ctlOf(RUNNING, 0));

    private static int workerCountOf(int c) {
        return c & CAPACITY;
    }
    //任务队列
    private final BlockingQueue<Runnable> workQueue;

    public void execute(Runnable command) {
        // 如果任务为null，则抛出异常。
        if (command == null)
            throw new NullPointerException();
        // ctl 中保存的线程池当前的一些状态信息
        int c = ctl.get();

        //  下面会涉及到 3 步 操作
        // 1.首先判断当前线程池中的工作线程总数是否小于 corePoolSize
        // 如果小于的话，通过addWorker(command, true)新建一个线程，并将任务(command)添加到该线程中；然后，启动该线程从而执行任务。
        if (workerCountOf(c) < corePoolSize) {
            if (addWorker(command, true))
                return;
            c = ctl.get();
        }
        // 2.如果当前工作线程总数大于等于 corePoolSize 的时候就会走到这里，表明没有走核心线程的创建分支。
        // 通过 isRunning 方法判断线程池状态，线程池处于 RUNNING 状态并且队列可以加入任务，该任务才会被加入进去
        if (isRunning(c) && workQueue.offer(command)) {
            int recheck = ctl.get();
            // 再次获取线程池状态，如果线程池状态不是 RUNNING 状态就需要从任务队列中移除任务，并尝试判断线程是否全部执行完毕。同时执行拒绝策略。
            if (!isRunning(recheck) && remove(command))
                reject(command);
                // 如果当前工作线程数量为0，新创建一个线程并执行。
            else if (workerCountOf(recheck) == 0)
                addWorker(null, false);
        }
        //3. 通过addWorker(command, false)新建一个线程，并将任务(command)添加到该线程中；然后，启动该线程从而执行任务。
        // 传入 false 代表增加线程时判断当前线程数是否少于 maxPoolSize
        //如果addWorker(command, false)执行失败，则通过reject()执行相应的拒绝策略的内容。
        else if (!addWorker(command, false))
            reject(command);
    }
```

这里简单分析一下整个流程（对整个逻辑进行了简化，方便理解）：

1. 如果当前 Worker Thread 总数小于 Core Pool Size，那么就会新建一个 Thread 来执行 Task。
2. 如果当前 Worker Thread 总数已经达到 Core Pool Size，先尝试把 Task 放入 Task Queue 中等待执行。
3. 如果向 Task Queue 投放 Task 失败（Task Queue 已经满了），并且当前 Worker Thread 总数小于 Maximum Pool Size，就新建一个 Non-core Thread 来执行 Task。
4. 如果当前 Worker Thread 总数已经等同于 Maximum Pool Size，Task Queue 也无法继续接收 Task，那么当前 Task 会被拒绝，Rejection Policy 会调用 `RejectedExecutionHandler.rejectedExecution()` Method。

> **补充说明**：很多人误以为 Non-core Thread 只在 Task Queue 满的时候才会被创建，之后就“闲着”等销毁。实际上，Non-core Thread 执行完初始 Task 后，并不会立刻销毁，而是会**主动从 Task Queue 中拉取 Task 执行**（通过 `getTask()` Method）。具体来说，Core Thread 使用 `workQueue.take()` Blocking 等待 Task，而 Non-core Thread 使用 `workQueue.poll(keepAliveTime, unit)` ——如果在存活时间内从 Queue 中取到了 Task，就会继续执行；只有 Timeout 没有取到 Task，Non-core Thread 才会被回收。这意味着，即使新 Task 被放入了 Queue，空闲的 Non-core Thread 也会抢先从 Queue 中取走 Task 来执行，而不是等 Queue 满了才被动响应。

![图解 Thread Pool 实现原理](https://oss.javaguide.cn/github/javaguide/java/concurrent/thread-pool-principle.png)

在 `execute` Method 中，多次调用 `addWorker` Method。`addWorker` 这个 Method 主要用来创建新的 Worker Thread，如果返回 true 说明创建和启动 Worker Thread 成功，否则的话返回的就是 false。

```java
    // 全局锁，并发操作必备
    private final ReentrantLock mainLock = new ReentrantLock();
    // 跟踪线程池的最大大小，只有在持有全局锁mainLock的前提下才能访问此集合
    private int largestPoolSize;
    // 工作线程集合，存放线程池中所有的（活跃的）工作线程，只有在持有全局锁mainLock的前提下才能访问此集合
    private final HashSet<Worker> workers = new HashSet<>();
    //获取线程池状态
    private static int runStateOf(int c)     { return c & ~CAPACITY; }
    //判断线程池的状态是否为 Running
    private static boolean isRunning(int c) {
        return c < SHUTDOWN;
    }


    /**
     * 添加新的工作线程到线程池
     * @param firstTask 要执行
     * @param core参数为true的话表示使用线程池的基本大小，为false使用线程池最大大小
     * @return 添加成功就返回true否则返回false
     */
   private boolean addWorker(Runnable firstTask, boolean core) {
        retry:
        for (;;) {
            //这两句用来获取线程池的状态
            int c = ctl.get();
            int rs = runStateOf(c);

            // Check if queue empty only if necessary.
            if (rs >= SHUTDOWN &&
                ! (rs == SHUTDOWN &&
                   firstTask == null &&
                   ! workQueue.isEmpty()))
                return false;

            for (;;) {
               //获取线程池中工作的线程的数量
                int wc = workerCountOf(c);
                // core参数为false的话表明队列也满了，线程池大小变为 maximumPoolSize
                if (wc >= CAPACITY ||
                    wc >= (core ? corePoolSize : maximumPoolSize))
                    return false;
               //原子操作将workcount的数量加1
                if (compareAndIncrementWorkerCount(c))
                    break retry;
                // 如果线程的状态改变了就再次执行上述操作
                c = ctl.get();
                if (runStateOf(c) != rs)
                    continue retry;
                // else CAS failed due to workerCount change; retry inner loop
            }
        }
        // 标记工作线程是否启动成功
        boolean workerStarted = false;
        // 标记工作线程是否创建成功
        boolean workerAdded = false;
        Worker w = null;
        try {

            w = new Worker(firstTask);
            final Thread t = w.thread;
            if (t != null) {
              // 加锁
                final ReentrantLock mainLock = this.mainLock;
                mainLock.lock();
                try {
                   //获取线程池状态
                    int rs = runStateOf(ctl.get());
                   //rs < SHUTDOWN 如果线程池状态依然为RUNNING,并且线程的状态是存活的话，就会将工作线程添加到工作线程集合中
                  //(rs=SHUTDOWN && firstTask == null)如果线程池状态小于STOP，也就是RUNNING或者SHUTDOWN状态下，同时传入的任务实例firstTask为null，则需要添加到工作线程集合和启动新的Worker
                   // firstTask == null证明只新建线程而不执行任务
                    if (rs < SHUTDOWN ||
                        (rs == SHUTDOWN && firstTask == null)) {
                        if (t.isAlive()) // precheck that t is startable
                            throw new IllegalThreadStateException();
                        workers.add(w);
                       //更新当前工作线程的最大容量
                        int s = workers.size();
                        if (s > largestPoolSize)
                            largestPoolSize = s;
                      // 工作线程是否启动成功
                        workerAdded = true;
                    }
                } finally {
                    // 释放锁
                    mainLock.unlock();
                }
                //// 如果成功添加工作线程，则调用Worker内部的线程实例t的Thread#start()方法启动真实的线程实例
                if (workerAdded) {
                    t.start();
                  /// 标记线程启动成功
                    workerStarted = true;
                }
            }
        } finally {
           // 线程启动失败，需要从工作线程中移除对应的Worker
            if (! workerStarted)
                addWorkerFailed(w);
        }
        return workerStarted;
    }
```

更多关于 Thread Pool 源码分析的内容推荐这篇文章：硬核干货：[4W 字从源码上分析 JUC Thread Pool ThreadPoolExecutor 的实现原理](https://www.cnblogs.com/throwable/p/13574306.html)。

现在，让我们在回到示例代码， 现在应该是不是很容易就可以搞懂它的原理了呢？

没搞懂的话，也没关系，可以看看我的分析：

> 我们在代码中模拟了 10 个 Task，我们配置的 Core Pool Size 为 5、Wait Queue Capacity 为 100，所以每次只可能存在 5 个 Task 同时执行，剩下的 5 个 Task 会被放到 Wait Queue 中去。当前的 5 个 Task 中如果有 Task 被执行完了，Thread Pool 就会去拿新的 Task 执行。

### 几个常见的对比

#### `Runnable` vs `Callable`

`Runnable` 自 Java 1.0 以来一直存在，但 `Callable` 仅在 Java 1.5 中引入，目的就是为了来处理 `Runnable` 不支持的用例。`Runnable` Interface 不会返回结果或抛出检查 Exception，但是 `Callable` Interface 可以。所以，如果 Task 不需要返回结果或抛出 Exception 推荐使用 `Runnable` Interface，这样代码看起来会更加简洁。

Utility Class `Executors` 可以实现将 `Runnable` Object 转换成 `Callable` Object。（`Executors.callable(Runnable task)` 或 `Executors.callable(Runnable task, Object result)`）。

`Runnable.java`

```java
@FunctionalInterface
public interface Runnable {
   /**
    * 被线程执行，没有返回值也无法抛出异常
    */
    public abstract void run();
}
```

`Callable.java`

```java
@FunctionalInterface
public interface Callable<V> {
    /**
     * 计算结果，或在无法这样做时抛出异常。
     * @return 计算得出的结果
     * @throws 如果无法计算结果，则抛出异常
     */
    V call() throws Exception;
}

```

#### `execute()` vs `submit()`

`execute()` 和 `submit()` 是两种提交 Task 到 Thread Pool 的 Method，有一些区别：

- **Return Value**：`execute()` Method 用于提交不需要 Return Value 的 `Runnable` Task。`submit()` 可以提交 `Runnable` 或 `Callable` Task，并返回一个 `Future` Object。`Future.isDone()` 只能说明 Task 已经以正常完成、Exception 或取消中的某种状态结束；调用 `get()` 才能取得结果，或者获知 Task 抛出的 Exception（`get(long timeout, TimeUnit unit)` 在 Timeout 前未完成时会抛出 `TimeoutException`）。
- **Exception Handling**：在使用 `submit()` Method 时，可以通过 `Future` Object 处理 Task 执行过程中抛出的 Exception；而在使用 `execute()` Method 时，Exception Handling 需要通过自定义的 `ThreadFactory`（在 Thread Factory 创建 Thread 的时候设置 `UncaughtExceptionHandler` Object 来 处理 Exception）或 `ThreadPoolExecutor` 的 `afterExecute()` Method 来处理

示例 1：使用 `get()` Method 获取 Return Value。

```java
// 这里只是为了演示使用，推荐使用 `ThreadPoolExecutor` 构造方法来创建线程池。
ExecutorService executorService = Executors.newFixedThreadPool(3);

Future<String> submit = executorService.submit(() -> {
    try {
        Thread.sleep(5000L);
    } catch (InterruptedException e) {
        e.printStackTrace();
    }
    return "abc";
});

String s = submit.get();
System.out.println(s);
executorService.shutdown();
```

输出：

```plain
abc
```

示例 2：使用 `get（long timeout，TimeUnit unit）` Method 获取 Return Value。

```java
ExecutorService executorService = Executors.newFixedThreadPool(3);

Future<String> submit = executorService.submit(() -> {
    try {
        Thread.sleep(5000L);
    } catch (InterruptedException e) {
        e.printStackTrace();
    }
    return "abc";
});

String s = submit.get(3, TimeUnit.SECONDS);
System.out.println(s);
executorService.shutdown();
```

输出：

```plain
Exception in thread "main" java.util.concurrent.TimeoutException
  at java.util.concurrent.FutureTask.get(FutureTask.java:205)
```

#### `shutdown()`VS`shutdownNow()`

- **`shutdown（）`** :关闭 Thread Pool，Thread Pool 的状态变为 `SHUTDOWN`。 Thread Pool 不再接受新 Task 了，但是 Queue 里的 Task 得执行完毕。
- **`shutdownNow()`**：关闭 Thread Pool，Thread Pool 的状态变为 `STOP`。 Thread Pool 会尝试 Interrupt 正在执行的 Task，停止处理排队的 Task 并返回尚未开始执行的 Task 列表；Task 不响应 Interrupt 时，不能保证立即终止。

#### `isTerminated()` VS `isShutdown()`

- **`isShutDown`** 当调用 `shutdown()` Method 后返回为 true。
- **`isTerminated`** 当调用 `shutdown()` Method 后，并且所有提交的 Task 完成后返回为 true

## 几种常见的内置 Thread Pool

### FixedThreadPool

#### 介绍

`FixedThreadPool` 被称为可重用固定 Thread Count 的 Thread Pool。通过 `Executors` Class 中的相关源代码来看一下相关实现：

```java
   /**
     * 创建一个可重用固定数量线程的线程池
     */
    public static ExecutorService newFixedThreadPool(int nThreads, ThreadFactory threadFactory) {
        return new ThreadPoolExecutor(nThreads, nThreads,
                                      0L, TimeUnit.MILLISECONDS,
                                      new LinkedBlockingQueue<Runnable>(),
                                      threadFactory);
    }
```

另外还有一个 `FixedThreadPool` 的实现方法，和上面的类似，所以这里不多做阐述：

```java
    public static ExecutorService newFixedThreadPool(int nThreads) {
        return new ThreadPoolExecutor(nThreads, nThreads,
                                      0L, TimeUnit.MILLISECONDS,
                                      new LinkedBlockingQueue<Runnable>());
    }
```

从上面源代码可以看出新创建的 `FixedThreadPool` 的 `corePoolSize` 和 `maximumPoolSize` 都被设置为 `nThreads`，这个 `nThreads` Parameter 是我们使用的时候自己传递的。

即使 `maximumPoolSize` 的值比 `corePoolSize` 大，也至多只会创建 `corePoolSize` 个 Thread。这是因为 `FixedThreadPool` 使用的是 Capacity 为 `Integer.MAX_VALUE` 的 `LinkedBlockingQueue`（无界 Queue），Queue 永远不会被放满。

#### 执行 Task 过程介绍

`FixedThreadPool` 的 `execute()` Method 运行示意图（该图片来源：《Java Concurrent Programming 的艺术》）：

![FixedThreadPool的execute()Method 运行示意图](./images/java-thread-pool-summary/FixedThreadPool.png)

**上图说明：**

1. 如果当前 Worker Thread 总数小于 `corePoolSize`，如果再来新 Task 的话，就创建新的 Thread 来执行 Task；
2. 当前 Worker Thread 总数达到 `corePoolSize` 后，如果再来新 Task 的话，会将 Task 加入 `LinkedBlockingQueue`；
3. Thread Pool 中的 Thread 执行完 手头的 Task 后，会在 Loop 中反复从 `LinkedBlockingQueue` 中获取 Task 来执行；

#### 为什么不推荐使用 `FixedThreadPool`？

`FixedThreadPool` 使用无界 Queue `LinkedBlockingQueue`（Queue 的 Capacity 为 Integer.MAX_VALUE）作为 Thread Pool 的 Work Queue 会对 Thread Pool 带来如下影响：

1. 当 Thread Pool 中的 Thread Count 达到 `corePoolSize` 后，新 Task 将在无界 Queue 中等待，因此 Thread Pool 中的 Thread Count 不会超过 `corePoolSize`；
2. 由于使用无界 Queue 时 `maximumPoolSize` 将是一个无效 Parameter，因为不可能存在 Task Queue 满的情况。所以，通过创建 `FixedThreadPool` 的源码可以看出创建的 `FixedThreadPool` 的 `corePoolSize` 和 `maximumPoolSize` 被设置为同一个值。
3. 由于 1 和 2，使用无界 Queue 时 `keepAliveTime` 将是一个无效 Parameter；
4. 运行中的 `FixedThreadPool`（未执行 `shutdown()` 或 `shutdownNow()`）不会拒绝 Task，在 Task 比较多的时候会导致 OOM。

### SingleThreadExecutor

#### 介绍

`SingleThreadExecutor` 是只有一个 Thread 的 Thread Pool。下面看看**SingleThreadExecutor 的实现：**

```java
   /**
     *返回只有一个线程的线程池
     */
    public static ExecutorService newSingleThreadExecutor(ThreadFactory threadFactory) {
        return new FinalizableDelegatedExecutorService
            (new ThreadPoolExecutor(1, 1,
                                    0L, TimeUnit.MILLISECONDS,
                                    new LinkedBlockingQueue<Runnable>(),
                                    threadFactory));
    }
```

```java
   public static ExecutorService newSingleThreadExecutor() {
        return new FinalizableDelegatedExecutorService
            (new ThreadPoolExecutor(1, 1,
                                    0L, TimeUnit.MILLISECONDS,
                                    new LinkedBlockingQueue<Runnable>()));
    }
```

从上面源代码可以看出新创建的 `SingleThreadExecutor` 的 `corePoolSize` 和 `maximumPoolSize` 都被设置为 1，其他 Parameter 和 `FixedThreadPool` 相同。

#### 执行 Task 过程介绍

`SingleThreadExecutor` 的运行示意图（该图片来源：《Java Concurrent Programming 的艺术》）：

![SingleThreadExecutor的运行示意图](./images/java-thread-pool-summary/SingleThreadExecutor.png)

**上图说明** :

1. 如果当前运行的 Thread Count 少于 `corePoolSize`，则创建一个新的 Thread 执行 Task；
2. Current Thread 池中有一个运行的 Thread 后，将 Task 加入 `LinkedBlockingQueue`
3. Thread 执行完当前的 Task 后，会在 Loop 中反复从 `LinkedBlockingQueue` 中获取 Task 来执行；

#### 为什么不推荐使用 `SingleThreadExecutor`？

`SingleThreadExecutor` 和 `FixedThreadPool` 一样，使用的都是 Capacity 为 `Integer.MAX_VALUE` 的 `LinkedBlockingQueue`（无界 Queue）。`SingleThreadExecutor` 使用无界 Queue 作为 Thread Pool 的 Work Queue 会对 Thread Pool 带来的影响与 `FixedThreadPool` 相同。说简单点，就是可能会导致 OOM。

### CachedThreadPool

#### 介绍

`CachedThreadPool` 是一个会根据需要创建新 Thread 的 Thread Pool。下面通过源码来看看 `CachedThreadPool` 的实现：

```java
    /**
     * 创建一个线程池，根据需要创建新线程，但会在先前构建的线程可用时重用它。
     */
    public static ExecutorService newCachedThreadPool(ThreadFactory threadFactory) {
        return new ThreadPoolExecutor(0, Integer.MAX_VALUE,
                                      60L, TimeUnit.SECONDS,
                                      new SynchronousQueue<Runnable>(),
                                      threadFactory);
    }

```

```java
    public static ExecutorService newCachedThreadPool() {
        return new ThreadPoolExecutor(0, Integer.MAX_VALUE,
                                      60L, TimeUnit.SECONDS,
                                      new SynchronousQueue<Runnable>());
    }
```

`CachedThreadPool` 的 `corePoolSize` 被设置为空（0），`maximumPoolSize` 被设置为 `Integer.MAX_VALUE`，即它是无界的，这也就意味着如果 Main Thread 提交 Task 的速度高于 `maximumPool` 中 Thread 处理 Task 的速度时，`CachedThreadPool` 会不断创建新的 Thread。极端情况下，这样会导致耗尽 cpu 和内存资源。

#### 执行 Task 过程介绍

`CachedThreadPool` 的 `execute()` Method 的执行示意图（该图片来源：《Java Concurrent Programming 的艺术》）：

![CachedThreadPool的execute()Method 的执行示意图](./images/java-thread-pool-summary/CachedThreadPool-execute.png)

**上图说明：**

1. 首先执行 `SynchronousQueue.offer(Runnable task)` 提交 Task 到 Task Queue。如果当前 `maximumPool` 中有闲 Thread 正在执行 `SynchronousQueue.poll(keepAliveTime,TimeUnit.NANOSECONDS)`，那么 Main Thread 执行 offer 操作与 Idle Thread 执行的 `poll` 操作配对成功，Main Thread 把 Task 交给 Idle Thread 执行，`execute()` Method 执行完成，否则执行下面的步骤 2；
2. 当初始 `maximumPool` 为空，或者 `maximumPool` 中没有 Idle Thread 时，将没有 Thread 执行 `SynchronousQueue.poll(keepAliveTime,TimeUnit.NANOSECONDS)`。这种情况下，步骤 1 将失败，此时 `CachedThreadPool` 会创建新 Thread 执行 Task，execute Method 执行完成；

#### 为什么不推荐使用 `CachedThreadPool`？

`CachedThreadPool` 使用的是 Synchronous Queue `SynchronousQueue`, 允许创建的 Thread Count 为 `Integer.MAX_VALUE`，可能会创建大量 Thread，从而导致 OOM。

### ScheduledThreadPool

#### 介绍

`ScheduledThreadPool` 用来在给定的延迟后运行 Task 或者定期执行 Task。这个在实际项目中基本不会被用到，也不推荐使用，大家只需要简单了解一下即可。

```java
public static ScheduledExecutorService newScheduledThreadPool(int corePoolSize) {
    return new ScheduledThreadPoolExecutor(corePoolSize);
}
public ScheduledThreadPoolExecutor(int corePoolSize) {
    super(corePoolSize, Integer.MAX_VALUE, 0, NANOSECONDS,
          new DelayedWorkQueue());
}
```

`ScheduledThreadPool` 是通过 `ScheduledThreadPoolExecutor` 创建的，使用的 `DelayedWorkQueue`（延迟 Blocking Queue）作为 Thread Pool 的 Task Queue。

`DelayedWorkQueue` 的内部元素并不是按照放入的时间排序，而是会按照延迟的时间长短对 Task 进行排序，内部采用的是“Heap”的 Data Structure，可以保证每次 Dequeue 的 Task 都是当前 Queue 中执行时间最靠前的。`DelayedWorkQueue` 添加元素满了之后会自动 Resize 原来 Capacity 的 1/2，即永远不会 Blocking，最大 Resize Reachable `Integer.MAX_VALUE`，所以最多只能创建 Core Pool Size 的 Thread。

`ScheduledThreadPoolExecutor` Inherit 了 `ThreadPoolExecutor`，所以创建 `ScheduledThreadExecutor` 本质也是创建一个 `ThreadPoolExecutor` Thread Pool，只是传入的 Parameter 不相同。

```java
public class ScheduledThreadPoolExecutor
        extends ThreadPoolExecutor
        implements ScheduledExecutorService
```

#### ScheduledThreadPoolExecutor 和 Timer 对比

- `Timer` 对系统时钟的变化敏感，`ScheduledThreadPoolExecutor` 不是；
- `Timer` 只有一个执行 Thread，因此长时间运行的 Task 可以延迟其他 Task。 `ScheduledThreadPoolExecutor` 可以配置任意数量的 Thread。 此外，如果你想（通过提供 `ThreadFactory`），你可以完全控制创建的 Thread;
- 在 `TimerTask` 中抛出的运行时 Exception 会终止 `Timer` 的唯一 Thread，后续计划 Task 也无法继续运行。`ScheduledThreadPoolExecutor` 中某个 Task 抛出 Exception 不会终止其他 Task；周期 Task 抛出 Exception 后，后续执行会被抑制。通过 `submit()` 或定时调度 Method 提交的 Task 通常会把 Exception 保存在 `Future` 中，调用方可通过 `Future.get()` 获取；若在 `afterExecute()` 中统一检查，也需要从传入的 `Future` 中读取 Exception。

关于定时 Task 的详细介绍，可以看这篇文章：[Java 定时 Task 详解](https://javaguide.cn/system-design/schedule-task.html)。

## Thread Pool 最佳实践

[Java Thread Pool 最佳实践](https://javaguide.cn/java/concurrent/java-thread-pool-best-practices.html)这篇文章总结了一些使用 Thread Pool 的时候应该注意的东西，实际项目使用 Thread Pool 之前可以看看。

## 参考

- 《Java Concurrent Programming 的艺术》
- [Java Scheduler ScheduledExecutorService ScheduledThreadPoolExecutor Example](https://www.journaldev.com/2340/java-scheduler-scheduledexecutorservice-scheduledthreadpoolexecutor-example)
- [java.util.concurrent.ScheduledThreadPoolExecutor Example](https://examples.javacodegeeks.com/core-java/util/concurrent/scheduledthreadpoolexecutor/java-util-concurrent-scheduledthreadpoolexecutor-example/)
- [ThreadPoolExecutor – Java Thread Pool Example](https://www.journaldev.com/1069/threadpoolexecutor-java-thread-pool-example-executorservice)

<!-- @include: @article-footer.snippet.md -->
