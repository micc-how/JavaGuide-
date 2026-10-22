---
title: Virtual Thread 常见问题总结
description: Java 21 Virtual Thread 详解：梳理 Virtual Threads 的定位、调度原理、与 Platform Thread 的区别、适用场景、创建方式、Performance 边界、Spring Boot 接入方式和实践注意事项。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: Java Virtual Thread,Virtual Threads,Project Loom,Java 21新特性,轻量级 Thread,协程,Virtual Thread 原理
---

<!-- @include: @article-header.snippet.md -->

一个 Web 请求进来，代码要查 Database、调远程 Interface、读写文件。按传统的同步写法，这个请求会占住一个 Platform Thread，哪怕大部分时间都在等 I/O。

Thread Pool 能缓解 Thread 创建成本，但不能改变一个事实：Platform Thread 数量仍然受 Operating System Thread Count、内存和调度成本限制。当 Concurrency 请求继续增加时，Thread Pool 里的 Thread 会被排队 Task 占满，Throughput 很快卡住。

Virtual Thread 就是为这个问题来的。它让我们继续用简单的同步 Blocking 代码，同时让等待 I/O 的 Task 不再长期占着昂贵的 Platform Thread。

## 什么是 Virtual Thread？

Virtual Thread 是 Java 21 正式引入的一种轻量级 Thread，也是 `java.lang.Thread` 的一种实现。它由 JDK 管理和调度，而不是直接和某个 Operating System Thread 一一绑定。

Platform Thread 通常是对 Operating System Thread 的薄 Encapsulation。一个 Platform Thread 运行时，会在整个 Lifecycle 内占用一个 Operating System Thread。 Virtual Thread 不一样：它运行 Java 代码时需要 Mount 到某个 Platform Thread 上；当它执行可 Park 的 Blocking Operation 时，JDK 可以把它从 Platform Thread 上 Unmount 下来，让这个 Platform Thread 去执行别的 Virtual Thread。

因此，Virtual Thread 的数量可以远大于 Platform Thread 数量。官方文档里用虚拟内存做类比：Operating System 把大量虚拟 Address 映射到有限物理内存，Java 运行时则把大量 Virtual Thread 映射到较少的 Platform Thread。

Virtual Thread 的几个关键点：

- Virtual Thread 仍然是 `Thread`，支持 `ThreadLocal`、Interrupt、Exception Stack、调试和 JFR 观测。
- Virtual Thread 适合大量 Blocking 等待的 Task，比如 HTTP 调用、Database 查询、Message Queue 访问、文件或网络 I/O。
- Virtual Thread 不是更快的 CPU 执行单元，不会让一段纯计算代码跑得更快。
- Virtual Thread 很便宜，通常应该“每个 Task 一个 Virtual Thread”，而不是像 Platform Thread 一样池化复用。

## Virtual Thread 和 Platform Thread 有什么关系？

在 Java 里，Virtual Thread、Platform Thread 和 Operating System Thread 大致是这样的关系：

![Virtual Thread、Platform Thread 和系统内核 Thread 的关系](https://oss.javaguide.cn/github/javaguide/java/new-features/virtual-threads-platform-threads-kernel-threads-relationship.png)

在 Windows、Linux 等主流 Operating System 中，HotSpot Java Virtual Machine (JVM) 的 Platform Thread 通常采用一对一 Thread 模型，也就是一个 Platform Thread 对应一个 Operating System Thread。 Virtual Thread 引入后，JDK 在 Platform Thread 之上又加了一层调度：

- Virtual Thread 是 Task 的承载者，业务代码看到的 `Thread.currentThread()` 返回的是 Virtual Thread 本身。
- Platform Thread 是 Virtual Thread 的 Carrier（Carrier Thread），负责真正执行 Virtual Thread 里的 Java 代码。
- Operating System 仍然只调度 Platform Thread，不知道 Virtual Thread 的存在。

一个 Virtual Thread 开始执行时，会被 JDK Scheduler Mount（mount）到某个 Platform Thread 上。执行到 Blocking I/O、`BlockingQueue.take()`、`Future.get()` 等支持 Park 的 Blocking 点时，Virtual Thread 可以 Unmount，Platform Thread 被释放出来继续执行其他 Virtual Thread。等 Blocking Operation 就绪后，Virtual Thread 再被提交回 Scheduler，Mount 到某个 Platform Thread 上继续执行。

这个 Mount 和 Unmount 过程对业务代码是透明的。你写的仍然是普通同步代码：

```java
String body = httpClient.send(request, BodyHandlers.ofString()).body();
Result result = repository.query(body);
return service.handle(result);
```

如果这些调用内部发生 Blocking，Virtual Thread 可以 Park 自己；如果换成 Platform Thread，这个 Thread 会一直占住对应的 Operating System Thread。

## Project Loom 和 Virtual Thread 是什么关系？

Project Loom 是 OpenJDK 中改进 Java Concurrency 模型的项目，Virtual Thread 是 Loom 最重要的成果之一。 Virtual Thread 先后在 JDK 19、JDK 20 中预览，最终通过 [JEP 444](https://openjdk.org/jeps/444) 在 JDK 21 转正。

Loom 不只是加了一个轻量级 Thread API。它还推动了 JDK Blocking I/O、调试、JFR、Thread Dump 等配套能力的调整，让传统的 thread-per-request 编程风格在 High Concurrency I/O 场景下重新变得可扩展。

这也是 Virtual Thread 和普通“协程库”的一个重要区别：Virtual Thread 被纳入了 Java 平台的 Thread 模型。调试器、Profiler、JFR、Thread dump 都能以 Thread 为单位理解它，而不是把业务调用链拆成一 Heap Callback 阶段。

## Virtual Thread 解决了什么问题？

很多服务端程序天然适合“一个请求一个 Thread”的模型。它的好处很明显：代码顺序执行，Exception 可以沿着调用 Stack 抛出，调试器能一步步跟进去，Thread dump 也能看到请求卡在哪里。

问题在于 Platform Thread 太贵。

假设一个 Interface 平均耗时 50ms，系统要达到 2000 QPS，按 Little's Law 粗略估算，需要同时处理约 100 个请求。如果 Interface 平均耗时变成 500ms，同样 2000 QPS 就需要约 1000 个 Concurrency 请求。每个请求都占一个 Platform Thread 时，Thread Count 很容易先于 CPU、网络带宽、Database Connection 等资源成为瓶颈。

Asynchronous 编程、Reactive 编程可以把 Thread 从等待 I/O 中释放出来，但代价也很明显：调用链被拆成 Callback、`CompletableFuture` 链或响应式流水线，Exception Handling、调试、火焰图和 Thread Context 都会变复杂。

Virtual Thread 试图保留同步代码的可读性，同时降低 Blocking 等待时占用 Platform Thread 的成本。它提升的主要是吞吐能力和 Concurrency 承载能力，不是单个请求的执行速度。

## Virtual Thread 适合哪些场景？

Virtual Thread 最适合下面这类 Task：

- Concurrency Task 数量很多，通常是成千上万级别。
- Task 大部分时间在等待 I/O，比如 Database、Redis、HTTP/RPC、Message Queue、文件和网络读写。
- 现有代码主要是同步 Blocking 模型，不想为了扩展性改成复杂的 Asynchronous 链。
- 希望保留传统调用 Stack，方便调试、压测分析和线上排查。

典型场景包括：

- Spring MVC / Servlet Interface 中调用 Database 和外部 HTTP 服务。
- 后台 Task 批量调用第三方 Interface。
- 网关或聚合服务 Concurrency 调用多个下游服务。
- 消息消费逻辑中包含 Blocking 式 Database 写入或远程调用。

Virtual Thread 不适合把 CPU 密集型 Task“变快”。如果 Task 主要是在算哈希、压缩图片、排序大 Array、跑复杂规则引擎，Thread Count 超过 CPU 核心数之后，吞吐通常不会继续提高。CPU 密集型工作仍然应该关注 Algorithm、Data Structure、批处理、Parallelism 流、专门的计算 Thread Pool 或本地化优化。

## 如何创建 Virtual Thread？

JDK 21 中常见的创建方式有四种。

### 使用 `Thread.startVirtualThread()`

适合启动一个很简单的 Virtual Thread：

```java
public class VirtualThreadDemo {
  public static void main(String[] args) throws InterruptedException {
    Thread thread = Thread.startVirtualThread(() -> {
      System.out.println(Thread.currentThread());
    });

    thread.join();
  }
}
```

需要注意的是，Virtual Thread 是 Daemon Thread。如果 `main` Method 不等待它结束，JVM 可能直接退出，导致 Task 还没来得及执行完。

### 使用 `Thread.ofVirtual()`

`Thread.ofVirtual()` 返回一个 `Thread.Builder.OfVirtual`，可以设置 Thread 名，也可以选择创建后立即启动或先不启动：

```java
public class VirtualThreadDemo {
  public static void main(String[] args) throws InterruptedException {
    Thread unstarted = Thread.ofVirtual()
        .name("order-query")
        .unstarted(() -> System.out.println("query order"));

    unstarted.start();
    unstarted.join();

    Thread started = Thread.ofVirtual()
        .name("payment-query")
        .start(() -> System.out.println("query payment"));

    started.join();
  }
}
```

### 使用 `ThreadFactory`

如果你希望统一 Thread 命名，或者把 Thread Factory 交给框架使用，可以通过 `ThreadFactory` 创建 Virtual Thread：

```java
import java.util.concurrent.ThreadFactory;

public class VirtualThreadDemo {
  public static void main(String[] args) throws InterruptedException {
    ThreadFactory factory = Thread.ofVirtual()
        .name("worker-", 0)
        .factory();

    Thread thread = factory.newThread(() -> {
      System.out.println(Thread.currentThread().getName());
    });

    thread.start();
    thread.join();
  }
}
```

### 使用 `Executors.newVirtualThreadPerTaskExecutor()`

业务开发中最常见的是这种方式。它会为每个提交的 Task 创建一个新的 Virtual Thread：

```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class VirtualThreadDemo {
  public static void main(String[] args) throws Exception {
    try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
      Future<String> future = executor.submit(() -> {
        return "hello virtual thread";
      });

      System.out.println(future.get());
    }
  }
}
```

这里的 `ExecutorService` 不是传统意义上的 Thread Pool。它不会维护一组固定 Virtual Thread 来复用，而是每个 Task 一个新的 Virtual Thread。`try-with-resources` 结束时会调用 `close()`，等待已提交 Task 完成。

## Virtual Thread 要不要池化？

不要池化 Virtual Thread。

Thread Pool 的主要目标是复用昂贵的 Platform Thread，并顺便限制 Concurrency。 Virtual Thread 本身不是稀缺资源，池化它们通常没有意义，还会把“每个 Task 一个 Thread”的模型重新绕回旧思路。

如果你的真实目标是限制访问某个资源的 Concurrency 量，应该限制资源，而不是限制 Virtual Thread 数量。比如某个老系统最多只能承受 20 个 Concurrency 请求，可以用 `Semaphore` 控制 Concurrency：

```java
import java.util.concurrent.Semaphore;

public class OldServiceClient {
  private static final Semaphore LIMIT = new Semaphore(20);

  public String call() throws InterruptedException {
    LIMIT.acquire();
    try {
      return doCall();
    } finally {
      LIMIT.release();
    }
  }

  private String doCall() {
    return "ok";
  }
}
```

如果瓶颈是 Database Connection，那就调整 Connection Pool 大小；如果瓶颈是下游 Interface Rate Limiting，那就做 Rate Limiting、Circuit Breaking 和 Retry 退避。 Virtual Thread 能让等待变便宜，但不能让 Database Connection、下游 Capacity、CPU 和内存变无限。

## Virtual Thread 和 Platform Thread Performance 对比

先给结论：Virtual Thread 不是“跑得更快的 Thread”，而是“可以创建很多、Blocking 成本更低的 Thread”。它通常能提升 I/O 密集型服务的吞吐，但不会降低一次 Database 查询或一次 HTTP 调用本身的耗时。

下面这个例子模拟 10,000 个 Blocking 1 秒的 Task：

```java
import java.time.Duration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.IntStream;

public class VirtualThreadCompareDemo {
  public static void main(String[] args) {
    long start = System.currentTimeMillis();

    try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
      IntStream.range(0, 10_000).forEach(i -> {
        executor.submit(() -> {
          Thread.sleep(Duration.ofSeconds(1));
          return i;
        });
      });
    }

    System.out.println("cost: " + (System.currentTimeMillis() - start) + "ms");
  }
}
```

如果把它换成 `Executors.newFixedThreadPool(200)`，同一时间最多只有 200 个 Task 在执行，10,000 个 Task 会被分批处理。按每批 1 秒粗略估计，总耗时接近 50 秒。 Virtual Thread 版本可以让这 10,000 个 Task 几乎同时进入等待状态，Platform Thread 在等待期间被释放出来，总耗时更接近单个 Task 的等待时间。

这个例子只能说明 Virtual Thread 对“Blocking 等待”友好，不是严谨基准测试。真实服务要看 Database Connection Pool、HTTP 客户端 Connection Pool、下游 Rate Limiting、Garbage Collection (GC)、Object 分配、Lock Contention、Container CPU 配额等因素。

## Virtual Thread 的底层原理是什么？

可以把 Virtual Thread 的执行过程拆成三件事：调度、Mount/Unmount、Stack 管理。

### 调度

Platform Thread 依赖 Operating System 调度。 Virtual Thread 由 JDK 自己的 Scheduler 调度，再由 Platform Thread 承载执行。JEP 444 中说明，Virtual Thread Scheduler 是一个采用 FIFO 模式的 work-stealing `ForkJoinPool`，它和 Parallelism 流使用的 common pool 不是同一个池。

默认情况下，Scheduler 的 Parallelism 度和可用处理器数量相关，可以通过下面的系统属性调整：

- `jdk.virtualThreadScheduler.parallelism`：Scheduler 目标 Parallelism 度。
- `jdk.virtualThreadScheduler.maxPoolSize`：Scheduler 可扩展的 Platform Thread 上限。

大多数业务系统不需要改这两个 Parameter。优先排查 Connection Pool、Rate Limiting、Lock 和 Blocking 点，通常比调整 Scheduler Parameter 更有效。

### Mount 和 Unmount

Virtual Thread 执行 Java 代码时，会 Mount 到某个 Platform Thread 上。遇到支持 Park 的 Blocking Operation 时，Virtual Thread 可以保存当前执行状态并 Unmount，Platform Thread 继续服务其他 Virtual Thread。

常见的 JDK Blocking Operation 已经为 Virtual Thread 做了适配。例如网络 I/O、`BlockingQueue`、`Future.get()` 等，在 Virtual Thread 中 Blocking 时通常不会长期占住底层 Platform Thread。

不是所有 Blocking 都能 Unmount。JDK 21 到 JDK 23 中，Virtual Thread 在 `synchronized` Code Block 或 Method 中 Blocking，会出现 Pinning，也就是被固定在 Carrier Thread 上。JDK 24 的 [JEP 491](https://openjdk.org/jeps/491) 改进了这一点，使 Virtual Thread 在 `synchronized` 中 Blocking 时也能释放底层 Platform Thread，消除了绝大多数由 `synchronized` 带来的 Pinning 场景。调用 native Method 或 Foreign Function & Memory API 相关代码时，仍然要关注剩余的 Pinning 风险。

### Stack 管理

Platform Thread 通常使用固定大小的 Operating System Thread Stack。 Virtual Thread 的 Stack 以 Stack 块 Object 的形式存放在 Java Heap 中，可以随着执行过程增长和收缩。这也是 Virtual Thread 能够大量创建的重要原因之一。

不过，这并不代表 Virtual Thread 没有内存成本。每个 Virtual Thread 仍然是 Object，也有 Stack 块、Local Variable、`ThreadLocal` 等内存 Overhead。百万级 Virtual Thread 不是免费的，只是比百万级 Platform Thread 现实得多。

## 什么是 Pinning？

Pinning 可以理解为“Virtual Thread 暂时没法从 Carrier Thread 上 Unmount”。 Virtual Thread 被固定在某个 Platform Thread 上后，它在 Blocking 期间会连带占住底层 Operating System Thread，扩展性也会跟着变差。

在 JDK 21 到 JDK 23 中，最典型的 Pinning 场景是：Virtual Thread 在 `synchronized` Code Block 或 Method 里执行 Blocking I/O。

```java
public synchronized String load() throws IOException {
  return remoteClient.get("/config"); // JDK 21-23 中，这里阻塞时可能固定载体线程
}
```

短小、纯内存操作的 `synchronized` 问题不大。真正需要关注的是高频路径上持 Lock 执行慢 I/O，例如持有 Object Lock 时查 Database、调远程 Interface、读大文件。

如果你使用 JDK 21 到 JDK 23，可以考虑：

- 避免在 `synchronized` 内部执行慢 I/O。
- 对高频 Blocking Lock 场景使用 `ReentrantLock`，并用 `try/finally` Release Lock。
- 用 JFR 观察 `jdk.VirtualThreadPinned` 事件。
- 临时使用 `-Djdk.tracePinnedThreads=full` 定位被固定的调用 Stack。

如果你使用 JDK 24 或更高版本，`synchronized` 导致的主要 Pinning 问题已经被 JEP 491 解决。选择 `synchronized` 还是 `java.util.concurrent.locks`，可以重新回到代码语义、可维护性和 Lock 能力本身来判断。

## 使用 Virtual Thread 有哪些注意事项？

### 不要把 Virtual Thread 当作提速 CPU 的工具

Virtual Thread 提升的是等待型 Task 的 Concurrency 承载能力。CPU 密集型 Task 最终还是要抢 CPU Time Slice，Virtual Thread 数量再多也不能突破 CPU 核心数的物理限制。

### 不要用 Thread Pool 思维限制 Virtual Thread

不要创建固定数量的 Virtual Thread 池。需要限制 Concurrency 时，用 `Semaphore`、Connection Pool、Rate Limiting 器或 Queue Capacity 限制具体资源。

### 小心 `ThreadLocal` 缓存 Large Object

Java 21 正式版保证 Virtual Thread 支持 `ThreadLocal`，这有利于兼容老代码和框架。但不要用 `ThreadLocal` 给每个 Virtual Thread 缓存 Large Object。

以前在 Thread Pool 里，一个 `ThreadLocal<SimpleDateFormat>` 可能只对应几十或几百个 Platform Thread。迁移到 Virtual Thread 后，如果每个 Task 一个 Virtual Thread，同样的写法可能变成每个 Task 创建一份缓存 Object，内存和分配压力会被放大。

如果只是传递请求 Context、用户 ID、Trace ID，通常问题不大。如果是缓存 Database Connection、大 Array、复杂 formatter、客户端 Object，就要重新评估。JDK 25 通过 JEP 506 将 Scoped Values 转正，它更适合在大量 Virtual Thread 之间传递不可变 Context。

### Virtual Thread 不会消除 Thread-safe 问题

Virtual Thread 让创建 Thread 更便宜，也意味着你更容易同时跑起大量 Concurrency Task。原来因为 Thread Pool 较小而没暴露的数据竞争，切到 Virtual Thread 后可能更容易出现。

需要继续遵守 Concurrent Programming 的基本规则：Shared 可变状态要 Locking 或隔离，Database Connection、会话 Object、Non-thread-safe 客户端不要被多个 Virtual Thread 同时乱用。

### 注意 Connection Pool 和下游 Capacity

很多服务迁移到 Virtual Thread 后，第一个瓶颈不再是 Business Thread 池，而是 Database Connection Pool、HTTP Connection Pool、Redis 连接数或下游 Rate Limiting。

这不是 Virtual Thread 的问题。 Virtual Thread 只是让更多 Task 有机会同时推进，真正的 Shared Resource 仍然要按 Capacity 管理。压测时建议同时观察：

- 应用 QPS、响应时间和错误率。
- Database Connection Pool 活跃连接、Wait Queue 和 Timeout 数。
- HTTP 客户端 Connection Pool 和下游 429/5xx。
- CPU、Heap Memory、GC、Object 分配速率。
- JFR 中的 Virtual Thread 事件和 Lock Contention。

### 不要混用太多 Asynchronous 模型

Virtual Thread 最适合同步 Blocking 代码。已经用 Reactive/WebFlux/Netty 写成全链路 Asynchronous 的系统，不一定能因为打开 Virtual Thread 就获得明显收益。

更麻烦的是混用模型：外层 Virtual Thread，内层又大量使用 Asynchronous Callback 和 Thread Pool，排查时可能同时面对 Virtual Thread、事件 Loop、Business Thread 池、Connection Pool 几套 Context。迁移时最好先挑同步 Blocking 链路试点，而不是全系统一键替换。

## 如何从传统 Thread Pool 迁移到 Virtual Thread？

对于已有的同步 Blocking 代码，`submit()`、`Future.get()` 这些用法通常可以保留。迁移时要检查原来的 Thread Pool 还承担了哪些职责，比如限制下游 Concurrency、控制排队 Task 数量、拒绝过载请求。

Oracle 的[Virtual Thread 迁移指南](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)给出了对应的做法：每个 Task 创建一个 Virtual Thread，访问受限资源时用 `Semaphore` 等工具控制 Concurrency。

### 迁移前：用 Platform Thread 池执行 HTTP 调用

假设应用共用一个专门调用某个下游服务的 Thread Pool，最多使用 20 个 Platform Thread，Queue 最多放 100 个 Task。下面只展示 Task 提交和结果获取，省略导入、HTTP 客户端 Initialization、Exception Handling 以及应用关闭时的资源释放：

```java
ExecutorService executor = new ThreadPoolExecutor(
    20, 20,
    0L, TimeUnit.MILLISECONDS,
    new ArrayBlockingQueue<>(100),
    Thread.ofPlatform().name("remote-call-", 0).factory(),
    new ThreadPoolExecutor.AbortPolicy());

Future<String> future = executor.submit(() ->
    httpClient.send(request, HttpResponse.BodyHandlers.ofString()).body());

String body = future.get(3, TimeUnit.SECONDS);
```

这里的 20 个 Thread 也限制了同时执行的调用数量。 Thread 全部忙碌时，新 Task 进入 Queue；Queue 也满了，就由 `AbortPolicy` 抛出 `RejectedExecutionException`。

直接把这个 Thread Pool 替换成 `Executors.newVirtualThreadPerTaskExecutor()`，原来的 Concurrency 和排队限制就没有了。[`Executors` 的 API 文档](<https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Executors.html#newVirtualThreadPerTaskExecutor()>)说明，这个执行器不限制创建的 Virtual Thread 数量，应用仍然受 CPU、内存等资源约束。

### 迁移后：每个 Task 一个 Virtual Thread，单独限制下游 Concurrency

下面的示例使用 Java 21 正式 API，保留同步 HTTP 调用和 `Future`，用 `Semaphore` 限制本地同时执行的下游调用。20 个许可、200ms 等待时间和后面的 Timeout 时间都只是示例值，实际要按下游 Capacity 和 Interface 耗时配置。示例直接返回响应体，实际业务还需要根据 HTTP 状态码处理调用结果。

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public class RemoteServiceClient implements AutoCloseable {
  private final ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
  private final Semaphore limit = new Semaphore(20);
  private final HttpClient httpClient = HttpClient.newBuilder()
      .connectTimeout(Duration.ofSeconds(1))
      .build();

  public String fetch(URI uri)
      throws InterruptedException, ExecutionException, TimeoutException {
    Future<String> future = executor.submit(() -> {
      if (!limit.tryAcquire(200, TimeUnit.MILLISECONDS)) {
        throw new RejectedExecutionException("等待下游调用许可超时");
      }

      try {
        HttpRequest request = HttpRequest.newBuilder(uri)
            .timeout(Duration.ofSeconds(2))
            .GET()
            .build();
        return httpClient.send(request, HttpResponse.BodyHandlers.ofString()).body();
      } finally {
        limit.release();
      }
    });

    try {
      return future.get(3, TimeUnit.SECONDS);
    } catch (TimeoutException | InterruptedException e) {
      future.cancel(true);
      throw e;
    }
  }

  @Override
  public void close() {
    executor.close();
    httpClient.close();
  }
}
```

同一个下游的调用要 Shared 这个 `RemoteServiceClient` Instance，例如交给 Spring 作为单例 Bean 管理，并在应用关闭时调用 `close()`。每次请求都创建一个 Instance，会各自拿到 20 个许可，起不到统一限制 Concurrency 的作用。应用部署了多个 Instance 时，各 Instance 的许可也是独立的。

获取许可失败时，Task 里的 `RejectedExecutionException` 会被包装进 `ExecutionException`，调用方可以用 `getCause()` 判断原因。它和迁移前在提交 Task 时直接抛出的拒绝 Exception，处理位置不一样。

这个示例限制了调用 Concurrency，也给等待许可设了 Timeout，但没有保留原来最多排队 100 个 Task 的限制。短时间涌入大量请求时，仍然可能创建大量等待许可的 Virtual Thread。原来依赖有界 Queue 保护内存的系统，还需要在入口限制在途请求数量，或使用有 Capacity 上限的 Queue、快速拒绝等方式处理过载。

### Timeout 和 Task 取消还要注意什么？

[`Future.get(3, TimeUnit.SECONDS)`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Future.html)从调用 `get()` 时开始限制等待时间，Timeout 后 Task 可能还在运行。示例在等待 Timeout 或调用方被 Interrupt 时，调用 `future.cancel(true)` 尝试取消 Task，再把 Exception 抛给上层。 Platform Thread 池同样需要处理这两种情况。

这里继续抛出 `InterruptedException` 即可；如果捕获后不能继续抛出，通常需要用 `Thread.currentThread().interrupt()` 恢复 Interrupt Flag，避免上层丢失 Interrupt 信号。

示例中的几个 Timeout 有不同的起点：200ms 用于等待许可，连接 Timeout 和 HTTP 请求 Timeout 由 HTTP 客户端处理，3 秒则用于等待整个 Task 的结果，期间可能包含等待许可和 HTTP 调用。它们的时间可能重叠，不能直接相加。涉及多次下游调用时，还要按请求的剩余时间分配 Timeout 预算。

Exception 也要分清：`get()` 等待 Timeout 会直接抛出 `TimeoutException`；[`HttpRequest.Builder.timeout()`](<https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpRequest.Builder.html#timeout(java.time.Duration)>)触发的 `HttpTimeoutException` 发生在 Task 内部，调用方拿到的是包装了它的 `ExecutionException`。只捕获 `TimeoutException`，处理不到 HTTP 客户端的请求 Timeout。

`cancel(true)` 依赖 Task 响应 Interrupt，不能保证 Task 立刻停止。JDK 默认的 [`HttpClient.send()` 实现](<https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpClient.html#send(java.net.http.HttpRequest,java.net.http.HttpResponse.BodyHandler)>)在被 Interrupt 时会尝试取消 HTTP 交换，但请求可能已经发到服务端，远端业务也可能继续执行。换成 JDBC 驱动或第三方 SDK 时，需要核对它们的 Timeout 和 Interrupt 行为；涉及 Write Operation，还要考虑幂等性。

另外，[`ExecutorService.close()`](<https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html#close()>)会等待已提交 Task 结束。如果在一次请求里使用 `try-with-resources` 创建执行器，即使 `get()` 已经 Timeout，退出 Code Block 时也可能继续等。上面的示例把执行器作为客户端成员复用，在应用关闭时统一释放。`close()` 本身没有等待时限，对停机时间有要求的服务，还需要设计有 Timeout 的关闭流程。

## Spring Boot 如何开启 Virtual Thread？

Spring Boot 3.2 开始提供了比较直接的开关。使用 Java 21 或更高版本时，可以在配置中开启：

```properties
spring.threads.virtual.enabled=true
```

Spring Boot 官方文档还提到几个实践点：

- 开启 Virtual Thread 后，配置传统 Thread Pool 大小的部分属性不再按原来的方式生效，因为 Virtual Thread 调度依赖 JVM 范围内的 Platform Thread 池。
- Virtual Thread 是 Daemon Thread。如果应用依赖 `@Scheduled` 等后台 Task 保持 JVM 存活，建议设置 `spring.main.keep-alive=true`。
- Spring Boot 官方目前建议 Java 24 或更高版本获得更好的 Virtual Thread 体验，主要和 Pinning 改进有关。

一个简单配置如下：

```yaml
spring:
  threads:
    virtual:
      enabled: true
  main:
    keep-alive: true
```

开启之后，不代表所有 Interface 都会变快。它更可能改善的是同步 Blocking、I/O 等待明显、Concurrency 较高的 Interface。如果 Interface 主要耗在 CPU、Lock Contention、慢 SQL 本身或下游 Rate Limiting 上，Virtual Thread 只能让问题更早暴露。

## 如何排查 Virtual Thread 问题？

JDK 已经为 Virtual Thread 补了不少观测能力。

### 使用 `jcmd` 导出 Thread Dump

传统 `jstack` 面对成千上万个 Virtual Thread 时不太合适。JDK 提供了新的 Thread Dump 能力：

```bash
jcmd <pid> Thread.dump_to_file -format=json thread-dump.json
```

也可以导出文本格式：

```bash
jcmd <pid> Thread.dump_to_file -format=text thread-dump.txt
```

JSON 格式更适合工具分析，尤其是 Virtual Thread 数量很多时。

### 使用 JFR 观察 Virtual Thread 事件

JFR 中和 Virtual Thread 相关的事件包括：

- `jdk.VirtualThreadStart`
- `jdk.VirtualThreadEnd`
- `jdk.VirtualThreadPinned`
- `jdk.VirtualThreadSubmitFailed`

其中 `jdk.VirtualThreadPinned` 对排查 Pinning 很有用。JDK 24 以后，`synchronized` 相关 Pinning 大多被解决，但 native/FFM 等剩余场景仍然可以通过 JFR 观察。

### 临时打开 Pinning Stack 追踪

在 JDK 21 到 JDK 23 中，可以临时使用：

```bash
-Djdk.tracePinnedThreads=full
```

它会在 Virtual Thread Blocking 且被固定时打印调用 Stack，适合本地或测试环境定位问题。JDK 24 的 JEP 491 之后，`synchronized` 相关的主要 Pinning 场景已经改进；native/FFM 等剩余边界仍然建议结合 JFR 和 Thread Dump 判断。

## Virtual Thread 常见面试题

### Virtual Thread 和 Platform Thread 的区别是什么？

Platform Thread 通常和 Operating System Thread 一一对应，创建和 Context Switch 成本较高，数量有限。 Virtual Thread 由 JDK 调度，可以把大量 Virtual Thread 映射到少量 Platform Thread 上。 Virtual Thread Blocking 等待 I/O 时，通常可以从 Carrier Thread Unmount，让 Platform Thread 继续执行其他 Virtual Thread。

### Virtual Thread 为什么适合 I/O 密集型 Task？

I/O 密集型 Task 大部分时间在等待外部资源。 Platform Thread 等待时会占住 Operating System Thread；Virtual Thread 等待时可以 Park 自己并释放 Carrier Thread。这样同样数量的 Platform Thread 可以承载更多 Concurrency Task。

### Virtual Thread 适合 CPU 密集型 Task 吗？

不适合把它当作 CPU 提速工具。CPU 密集型 Task 需要真实 CPU 时间，Thread Count 超过核心数后只会增加调度竞争。 Virtual Thread 能改善 High Concurrency 等待，不会让单个计算 Task 更快。

### Virtual Thread 需要池化吗？

不需要，也不建议。 Virtual Thread 便宜，应该按 Task 创建。需要限制 Concurrency 时，限制具体资源，比如 Database Connection Pool、HTTP Connection Pool、`Semaphore`、Rate Limiting 器，而不是池化 Virtual Thread。

### Virtual Thread 和协程一样吗？

它们都属于轻量级 Concurrency 的思路，但 Java Virtual Thread 是 `java.lang.Thread` 的实现，纳入了 Java 原有 Thread 模型。业务代码不需要写 `async/await`，也不需要手动 yield。和 Go goroutine 相比，Virtual Thread 更强调兼容 Java 既有 Thread API、调试工具和 Blocking 式代码风格。对开发者来说，它更像“便宜很多的 Thread”。

### 使用 Virtual Thread 后还需要 Reactive 编程吗？

看场景。很多同步 Blocking 的服务端 Interface 可以用 Virtual Thread 获得更好的可读性和足够的吞吐，不必为了释放 Thread 写复杂 Callback 链。但 Reactive 仍然适合流式处理、背压、事件驱动、长连接和已经全链路 Asynchronous 化的系统。 Virtual Thread 不是替代所有 Asynchronous 模型的银弹。

### JDK 21 里的 `synchronized` 还能不能用？

可以用，但要注意边界。JDK 21 到 JDK 23 中，Virtual Thread 在 `synchronized` 内部执行 Blocking Operation 可能出现 Pinning。短小的内存同步问题不大，高频路径上不要持有 `synchronized` Lock 执行慢 I/O。JDK 24 通过 JEP 491 改进后，`synchronized` 相关 Pinning 已经基本解决。

## 参考资料

- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [Oracle Java 21 Documentation: Virtual Threads](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)
- [Java 21 API: Executors](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Executors.html)
- [Java 21 API: Future](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Future.html)
- [Java 21 API: ExecutorService](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html)
- [Java 21 API: HttpClient](https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpClient.html)
- [Java 21 API: HttpRequest.Builder](https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpRequest.Builder.html)
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491)
- [JEP 506: Scoped Values](https://openjdk.org/jeps/506)
- [Spring Boot Reference Documentation: Virtual threads](https://docs.spring.io/spring-boot/reference/features/spring-application.html#features.spring-application.virtual-threads)
- [Spring Blog: Embracing Virtual Threads](https://spring.io/blog/2022/10/11/embracing-virtual-threads/)
- [Inside Java: Managing Throughput with Virtual Threads](https://inside.java/2024/02/04/sip094/)
- [Quarkus Blog: When Quarkus meets Virtual Threads](https://quarkus.io/blog/virtual-thread-1/)

<!-- @include: @article-footer.snippet.md -->
