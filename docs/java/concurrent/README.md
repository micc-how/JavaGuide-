---
title: Java Concurrent Programming 专题：Thread、Lock、Java Memory Model (JMM)、Compare-And-Swap (CAS)、AbstractQueuedSynchronizer (AQS)、Thread Pool 与 Virtual Thread
description: Java Concurrent Programming 面试与学习路线，涵盖 Thread、Lock、synchronized、ReentrantLock、JMM、CAS、AQS、ThreadLocal、Thread Pool、CompletableFuture 和 Virtual Thread。
category: Java
tag:
  - Java
  - Java并发
  - Java面试
sitemap:
  changefreq: weekly
  priority: 0.9
head:
  - - meta
    - name: keywords
      content: Java Concurrency,Java Lock,synchronized,ReentrantLock,JMM,CAS,AQS,ThreadLocal,Thread Pool,CompletableFuture,Concurrent Container,Atomic,Virtual Thread
---

Java Concurrent Programming 是后端开发和面试中最重要、也最容易混淆的模块之一。学习 Concurrency 不能只背 API，要把 Thread Lifecycle、Locking Mechanism、Memory Model、Atomic Operation、Thread Pool 和 Concurrency Utility Class 放在同一条主线上理解。

## 适合谁看

- 想系统学习 Java Concurrent Programming 的后端开发者。
- 准备 Thread、Lock、JMM、CAS、AQS、Thread Pool 等面试题的同学。
- 已经在项目中使用 Multithreading，但对 Deadlock、Thread Pool Parameter、ThreadLocal 泄漏等问题不够熟的读者。
- 想理解 Concurrent Container、CompletableFuture、Virtual Thread 等工程实践能力的工程师。

## 学习重点

- Thread 创建、Lifecycle、Context Switch、Thread-safe 和常见 Concurrency 问题。
- `synchronized`、`volatile`、`ReentrantLock`、Mutex、Read-Write Lock、Optimistic Lock、Pessimistic Lock 的适用边界。
- JMM、happens-before、Instruction Reordering、Visibility、Atomicity 和 Ordering。
- CAS、Atomic Class、AQS、Concurrent Container 和 Blocking Queue 的底层思路。
- Thread Pool 核心 Parameter、Rejection Policy、Task Queue、Parameter 配置和生产实践。
- CompletableFuture、ThreadLocal、Virtual Thread 在真实项目中的使用方式和风险。

## 建议阅读顺序

1. [Java Concurrency 常见面试题总结（上）](./java-concurrent-questions-01.md)：先建立 Thread、Lock 和 Thread-safe 的基础问题清单。
2. [Java Concurrency 常见面试题总结（中）](./java-concurrent-questions-02.md) 和 [Java Concurrency 常见面试题总结（下）](./java-concurrent-questions-03.md)：继续补齐 JMM、CAS、AQS、Thread Pool 和 Concurrency 工具。
3. [Java Lock 详解](./java-lock.md)、[Optimistic Lock 和 Pessimistic Lock 详解](./optimistic-lock-and-pessimistic-lock.md)、[CAS 详解](./cas.md)、[JMM 详解](./jmm.md)：先建立 Lock 体系，再理解 Concurrency 控制的底层语义。
4. [AQS 详解](./aqs.md)、[从ReentrantLock的实现看AQS的原理及应用](./reentrantlock.md)：深入理解 Java Lock 和 Synchronizer。
5. [Java Thread Pool 详解](./java-thread-pool-summary.md) 和 [Java Thread Pool 最佳实践](./java-thread-pool-best-practices.md)：掌握生产中最常用的 Concurrency 基础设施。

## 核心文章

### Concurrency 面试题

- [Java Concurrency 常见面试题总结（上）](./java-concurrent-questions-01.md)：覆盖 Thread 基础、Thread-safe、Lock 和常见 Concurrency 问题。
- [Java Concurrency 常见面试题总结（中）](./java-concurrent-questions-02.md)：继续梳理 JMM、volatile、CAS、AQS 等核心知识。
- [Java Concurrency 常见面试题总结（下）](./java-concurrent-questions-03.md)：补齐 Thread Pool、Concurrency Utility Class、CompletableFuture 和 Virtual Thread 等内容。

### Lock、Memory Model 与 Synchronizer

- [Java Lock 详解](./java-lock.md)：从 Mutex、Read-Write Lock、Spin Lock 到 `synchronized`、`ReentrantLock`、AQS，建立 Java Lock 体系。
- [Optimistic Lock 和 Pessimistic Lock 详解](./optimistic-lock-and-pessimistic-lock.md)：理解不同 Concurrency 冲突处理策略。
- [CAS 详解](./cas.md)：理解 CAS、ABA 问题和 Spin Overhead。
- [JMM 详解](./jmm.md)：掌握 Visibility、Atomicity、Ordering 和 happens-before。
- [AQS 详解](./aqs.md)：理解 Sync Queue、Exclusive/Shared Mode 和常见 Synchronizer 底层。
- [从ReentrantLock的实现看AQS的原理及应用](./reentrantlock.md)：通过 ReentrantLock 深入理解 AQS。

### Concurrency 工具与工程实践

- [Java Thread Pool 详解](./java-thread-pool-summary.md)：理解核心 Parameter、Task Queue、Rejection Policy 和执行流程。
- [Java Thread Pool 最佳实践](./java-thread-pool-best-practices.md)：总结生产环境中 Thread Pool 隔离、Parameter 配置和 Monitoring 建议。
- [Java 常见 Concurrent Container 总结](./java-concurrent-collections.md)：梳理 ConcurrentHashMap、CopyOnWriteArrayList、BlockingQueue 等 Container。
- [Atomic Class 总结](./atomic-classes.md)：理解 Atomic Update Primitive Type、Array、Reference 和 Field。
- [ThreadLocal 详解](./threadlocal.md)：理解 Thread-Local Variable、ThreadLocalMap 和 Memory Leak 风险。
- [CompletableFuture 详解](./completablefuture-intro.md)：掌握 Asynchronous Orchestration、Exception Handling 和 Thread Pool 使用。
- [Virtual Thread 常见问题总结](./virtual-thread.md)：理解 Virtual Thread 的定位、适用场景和使用限制。

## 高频问题

- Thread 和 Process 有什么区别？ Thread 有哪些状态？
- 什么是 Thread-safe？如何定位 Deadlock？
- Mutex、Read-Write Lock、Spin Lock 有什么区别？
- `synchronized` 和 `ReentrantLock` 有什么区别？
- `volatile` 能保证 Atomicity 吗？它解决什么问题？
- JMM 是什么？happens-before 规则有什么用？
- CAS 有什么优缺点？ABA 问题如何解决？
- AQS 的核心思想是什么？哪些 Utility Class 基于 AQS？
- Thread Pool 核心 Parameter 如何配置？ Rejection Policy 如何选择？
- 为什么不建议直接使用 `Executors` 创建 Thread Pool？
- `ThreadLocal` 为什么可能 Memory Leak？
- CompletableFuture 默认 Thread Pool 有什么风险？
- Virtual Thread 适合 CPU 密集型 Task 吗？

## 相关专题

- [Java 知识体系](../)
- [Java Collection 专题](../collection/)
- [Java Virtual Machine (JVM) 专题](../jvm/)
- [Java IO 专题](../io/)
- [Operating System](../../cs-basics/operating-system/)

<!-- @include: @article-footer.snippet.md -->
