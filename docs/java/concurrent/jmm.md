---
title: Java Memory Model (JMM) 详解
description: 深入解析 JMM：详解 CPU Cache 模型、Instruction Reordering 机制、happens-before原则、Memory Visibility 保证，理解 Multithreading Concurrent Programming 的底层规范。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: JMM,CPU Cache,Instruction Reordering,happens-before,Memory Visibility,Concurrent Programming 模型
---

对于 Java 来说，你可以把 **JMM** 看作是 Java 定义的 Concurrent Programming 相关的一组规范。除了抽象了 Thread 和 Main Memory 之间的关系之外，其还规定了从 Java 源代码到 CPU 可执行 Instruction 的转化过程要遵守哪些 Concurrency 相关的原则和规范。其主要目的是为了**简化 Multithreaded Programming**，**增强程序的可移植性**。

JMM 主要定义了对于一个 Shared Variable，当一个 Thread 执行 Write Operation 后，该 Variable 对其他 Thread 的**Visibility**。

要想透彻理解 JMM，我们需要从 **CPU Cache 模型**和**Instruction Reordering**说起。

## 从 CPU Cache 模型说起

**为什么要弄一个 CPU Cache 呢？** 类比我们开发网站后台系统使用的缓存（比如 Redis）是为了解决程序处理速度和访问常规关系型 Database 速度不对等的问题。 **CPU Cache 则是为了解决 CPU 处理速度和内存处理速度不对等的问题。**

我们甚至可以把 **内存看作外存的 Cache**，程序运行的时候我们把外存的数据复制到内存，由于内存的处理速度远远高于外存，这样提高了处理速度。

总结：**CPU Cache 缓存的是内存数据用于解决 CPU 处理速度和内存不匹配的问题，内存缓存的是硬盘数据用于解决硬盘访问速度过慢的问题。**

为了更好地理解，我画了一个简单的 CPU Cache 示意图如下所示。

> **🐛 修正（参见：[issue#1848](https://github.com/Snailclimb/JavaGuide/issues/1848)）**：对 CPU Cache 模型绘图不严谨的地方进行完善。

![CPU Cache 模型示意图](https://oss.javaguide.cn/github/javaguide/java/concurrent/cpu-cache.png)

现代的 CPU Cache 通常分为三层，分别叫 L1,L2,L3 Cache。有些 CPU 可能还有 L4 Cache，这里不做讨论，并不常见

**CPU Cache 的工作方式：** 先复制一份数据到 CPU Cache 中，当 CPU 需要用到的时候就可以直接从 CPU Cache 中读取数据，当运算完成后，再将运算得到的数据写回 Main Memory 中。但是，这样存在 **内存缓存不一致性的问题**！比如我执行一个 i++ 操作的话，如果两个 Thread 同时执行的话，假设两个 Thread 从 CPU Cache 中读取的 i=1，两个 Thread 做了 i++ 运算完之后再写回 Main Memory 之后 i=2，而正确结果应该是 i=3。

**CPU 为了解决内存缓存不一致性问题可以通过制定 Cache Coherence Protocol（比如 [MESI 协议](https://zh.wikipedia.org/wiki/MESI%E5%8D%8F%E8%AE%AE)）或者其他手段来解决。** 这个 Cache Coherence Protocol 指的是在 CPU Cache 与 Main Memory 交互的时候需要遵守的原则和规范。不同的 CPU 中，使用的 Cache Coherence Protocol 通常也会有所不同。

![Cache Coherence Protocol](https://oss.javaguide.cn/github/javaguide/java/concurrent/cpu-cache-protocol.png)

CPU Cache 一致性由处理器及其内存子系统协同实现。不同处理器架构还会规定各类内存访问在其他处理器看来可以按什么顺序出现，这通常称为 Hardware Memory Model。JMM 位于更高的语言层，Java Virtual Machine (JVM) 需要把它的要求映射到具体处理器提供的 Instruction 和屏障上。

## Instruction Reordering

说完了 CPU Cache 模型，我们再来看看另外一个比较重要的概念 **Instruction Reordering**。

为了提升执行速度/Performance，计算机在执行程序代码的时候，会对 Instruction 进行 Reordering。

**什么是 Instruction Reordering？** 简单来说就是系统在执行代码的时候并不一定是按照你写的代码的顺序依次执行。

常见的 Instruction Reordering 有下面 2 种情况：

- **Compiler Reordering**：Compiler（包括 JVM、Just-In-Time Compilation (JIT) Compiler 等）在不改变 Single Thread 程序语义的前提下，重新安排语句的执行顺序。
- **Instruction-Parallel Reordering**：现代处理器采用了 Instruction-Level Parallelism 技术(Instruction-Level Parallelism，ILP)来将多条 Instruction 重叠执行。如果不存在数据依赖性，处理器可以改变语句对应 Machine Instruction 的执行顺序。

另外，内存系统也会有“Reordering”，但又不是真正意义上的 Reordering。在 JMM 里表现为 Main Memory 和 Local Memory 的内容可能不一致，进而导致程序在 Multithreading 下执行可能出现问题。

Java 源代码经过 Bytecode 编译、解释执行或 JIT 编译，最终由 JVM 在目标平台上执行相应的 Machine Instruction。 Compiler 优化、处理器乱序执行以及内存子系统的行为都可能使 Multithreading 观察到的顺序与源代码直观顺序不同，它们并不是一条固定且严格线性的“Reordering 流水线”。

**Instruction Reordering 可以保证 Serial 语义一致，但是没有义务保证 Multithreading 间的语义也一致**，所以在 Multithreading 下，Instruction Reordering 可能会导致一些问题。

对于 Compiler Reordering 和处理器的 Instruction Reordering（Instruction-Parallel Reordering 和内存系统 Reordering 都属于是处理器级别的 Instruction Reordering），处理该问题的方式不一样。

- 对于 Compiler，通过禁止特定 Type 的 Compiler Reordering 的方式来禁止 Reordering。

- 对于处理器，通过插入 Memory Barrier（Memory Barrier，或有时叫做 Memory Fence，Memory Fence）的方式来禁止特定 Type 的处理器 Reordering。

> Memory Barrier（Memory Barrier，也叫 Memory Fence，Memory Fence）用于约束特定内存访问之间的顺序和 Visibility。不同处理器架构的具体实现并不相同，不能一概理解为“把缓存刷新到物理内存”或“让缓存全部失效”；JVM 会根据目标平台选择满足 JMM 语义的 Instruction。

## JMM(Java Memory Model)

### 什么是 JMM？为什么需要 JMM？

Java 是最早尝试提供 Memory Model 的编程语言。由于早期 Memory Model 存在一些缺陷（比如非常容易削弱 Compiler 的优化能力），从 Java5 开始，Java 开始使用新的 Memory Model [《JSR-133：Java Memory Model and Thread Specification》](http://www.cs.umd.edu/~pugh/java/memoryModel/CommunityReview.pdf)。

一般来说，编程语言也可以直接复用 Operating System 层面的 Memory Model。不过，不同的 Operating System Memory Model 不同。如果直接复用 Operating System 层面的 Memory Model，就可能会导致同样一套代码换了一个 Operating System 就无法执行了。Java 语言是跨平台的，它需要自己提供一套 Memory Model 以屏蔽系统差异。

这只是 JMM 存在的其中一个原因。实际上，对于 Java 来说，你可以把 JMM 看作是 Java 定义的 Concurrent Programming 相关的一组规范，除了抽象了 Thread 和 Main Memory 之间的关系之外，其还规定了从 Java 源代码到 CPU 可执行 Instruction 的这个转化过程要遵守哪些和 Concurrency 相关的原则和规范，其主要目的是为了简化 Multithreaded Programming，增强程序可移植性的。

**为什么要遵守这些 Concurrency 相关的原则和规范呢？** 这是因为 Concurrent Programming 下，像 CPU 多级缓存和 Instruction Reordering 这类设计可能会导致程序运行出现一些问题。就比如说我们上面提到的 Instruction Reordering 就可能会让 Multithreading 程序的执行出现问题，为此，JMM 抽象了 happens-before 原则（后文会详细介绍到）来解决这个 Instruction Reordering 问题。

JMM 说白了就是定义了一些规范来解决这些问题，开发者可以利用这些规范更方便地开发 Multithreading 程序。对于 Java 开发者说，你不需要了解底层原理，直接使用 Concurrency 相关的一些 Keyword 和 Class（比如 `volatile`、`synchronized`、各种 `Lock`）即可开发出 Concurrency-safe 的程序。

### JMM 是如何抽象 Thread 和 Main Memory 之间的关系？

**JMM** 抽象了 Thread 和 Main Memory 之间的关系，就比如说 Thread 之间的 Shared Variable 必须存储在 Main Memory 中。

Java 从早期规范开始就有 Memory Model；Java 5 通过 JSR-133 对它进行了重要修订，明确并增强了 `volatile`、`final` 和 happens-before 等语义。JMM 允许 JVM 使用 Register、缓存以及 Compiler 优化来实现 Shared Variable 访问；如果程序没有建立必要的同步关系，一个 Thread 就可能看不到另一个 Thread 的最新写入。

这和我们上面讲到的 CPU Cache 模型非常相似。

**什么是 Main Memory？什么是 Local Memory？**

- **Main Memory**：JMM 用它抽象 Thread 之间可以 Shared 的 Variable，包括 Instance Field、Static Field 和 Array 元素。 Method Local Variable、Parameter 和 Exception Handling Parameter 不会在 Thread 之间 Shared，因此不属于这里所说的 Shared Variable。 Main Memory 是规范层面的抽象，不等同于某一块物理内存。
- **Local Memory**：每个 Thread 都有一个私有的 Local Memory，Local Memory 存储了该 Thread 已读 / 写 Shared Variable 的副本。每个 Thread 只能操作自己 Local Memory 中的 Variable，无法直接访问其他 Thread 的 Local Memory。如果 Thread 间需要通信，必须通过 Main Memory 来进行。 Local Memory 是 JMM 抽象出来的一个概念，并不真实存在，它涵盖了缓存、写 Buffer、Register 以及其他的硬件和 Compiler 优化。

JMM 的抽象示意图如下：

![JMM](https://oss.javaguide.cn/github/javaguide/java/concurrent/jmm.png)

从上图来看，Thread 1 与 Thread 2 之间如果要进行通信的话，必须要经历下面 2 个步骤：

1. Thread 1 把 Local Memory 中修改过的 Shared Variable 副本的值同步到 Main Memory 中去。
2. Thread 2 到 Main Memory 中读取对应的 Shared Variable 的值。

也就是说，Thread 间的 Shared 数据需要遵守 JMM 的规则进行通信；只有通过 `volatile`、Lock、Thread 启动与终止等方式建立相应的 happens-before 关系时，JMM 才为相关写入提供 Visibility 保证。

不过，Multithreading 下，对 Main Memory 中的一个 Shared Variable 进行操作有可能诱发 Thread-safe 问题。举个例子：

1. Thread 1 和 Thread 2 分别对同一个 Shared Variable 进行操作，一个执行修改，一个执行读取。
2. Thread 2 读取到的是 Thread 1 修改之前的值还是修改后的值并不确定，都有可能，因为 Thread 1 和 Thread 2 都是先将 Shared Variable 从 Main Memory Copy 到对应 Thread 的 Working Memory 中。

关于 Main Memory 与 Working Memory 直接的具体交互协议，即一个 Variable 如何从 Main Memory Copy 到 Working Memory，如何从 Working Memory 同步到 Main Memory 之间的实现细节，JMM 定义来以下八种 Synchronization Action（了解即可，无需死记硬背）：

- **lock**: 作用于 Main Memory 中的 Variable，将他标记为一个 Thread 独享 Variable。
- **unlock**: 作用于 Main Memory 中的 Variable，解除 Variable 的 Lock 状态，被解除 Lock 状态的 Variable 才能被其他 Thread Lock。
- **read（读取）**：作用于 Main Memory 的 Variable，它把一个 Variable 的值从 Main Memory 传输到 Thread 的 Working Memory 中，以便随后的 load 动作使用。
- **load（载入）**：把 read 操作从 Main Memory 中得到的 Variable 值放入 Working Memory 的 Variable 的副本中。
- **use（使用）**：把 Working Memory 中的一个 Variable 的值传给执行引擎，每当虚拟机遇到一个使用到 Variable 的 Instruction 时都会使用该 Instruction。
- **assign（赋值）**：作用于 Working Memory 的 Variable，它把一个从执行引擎接收到的值赋给 Working Memory 的 Variable，每当虚拟机遇到一个给 Variable 赋值的 Bytecode Instruction 时执行这个操作。
- **store（存储）**：作用于 Working Memory 的 Variable，它把 Working Memory 中一个 Variable 的值传送到 Main Memory 中，以便随后的 write 操作使用。
- **write（写入）**：作用于 Main Memory 的 Variable，它把 store 操作从 Working Memory 中得到的 Variable 的值放入 Main Memory 的 Variable 中。

除了这 8 种 Synchronization Action 之外，还规定了下面这些同步规则来保证这些 Synchronization Action 的正确执行（了解即可，无需死记硬背）：

- 不允许一个 Thread 无原因地（没有发生过任何 assign 操作）把数据从 Thread 的 Working Memory 同步回 Main Memory 中。
- 一个新的 Variable 只能在 Main Memory 中 “诞生”，不允许在 Working Memory 中直接使用一个未被 Initialization（load 或 assign）的 Variable，换句话说就是对一个 Variable 实施 use 和 store 操作之前，必须先执行过了 assign 和 load 操作。
- 一个 Variable 在同一个时刻只允许一条 Thread 对其进行 lock 操作，但 lock 操作可以被同一条 Thread 重复执行多次，多次执行 lock 后，只有执行相同次数的 unlock 操作，Variable 才会被 Unlock。
- 如果对一个 Variable 执行 lock 操作，将会清空 Working Memory 中此 Variable 的值，在执行引擎使用这个 Variable 前，需要重新执行 load 或 assign 操作 Initialization Variable 的值。
- 如果一个 Variable 事先没有被 lock 操作 Lock，则不允许对它执行 unlock 操作，也不允许去 unlock 一个被其他 Thread Lock 住的 Variable。
- ……

### Java Memory Area 和 JMM 有何区别？

这是一个比较常见的问题，很多初学者非常容易搞混。 **Java Memory Area 和 Memory Model 是完全不一样的两个东西**：

- JVM 内存结构和 Java Virtual Machine 的运行时区域相关，定义了 JVM 在运行时如何分区存储程序数据，就比如说 Heap 主要用于存放 Object Instance。
- JMM 和 Java 的 Concurrent Programming 相关，抽象了 Thread 和 Main Memory 之间的关系就比如说 Thread 之间的 Shared Variable 必须存储在 Main Memory 中，规定了从 Java 源代码到 CPU 可执行 Instruction 的这个转化过程要遵守哪些和 Concurrency 相关的原则和规范，其主要目的是为了简化 Multithreaded Programming，增强程序可移植性的。

### happens-before 原则是什么？

happens-before 这个概念最早诞生于 Leslie Lamport 于 1978 年发表的论文[《Time，Clocks and the Ordering of Events in a Distributed System》](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)。在这篇论文中，Leslie Lamport 提出了[逻辑时钟](https://writings.sh/post/logical-clocks)的概念，这也成了第一个逻辑时钟 Algorithm。在分布式环境中，通过一系列规则来定义逻辑时钟的变化，从而能通过逻辑时钟来对分布式系统中的事件的先后顺序进行判断。**逻辑时钟并不度量时间本身，仅区分事件发生的前后顺序，其本质就是定义了一种 happens-before 关系。**

上面提到的 happens-before 这个概念诞生的背景并不是重点，简单了解即可。

JSR 133 引入了 happens-before 这个概念来描述两个操作之间的 Memory Visibility。

**为什么需要 happens-before 原则？** happens-before 原则的诞生是为了程序员和 Compiler、处理器之间的平衡。程序员追求的是易于理解和编程的强 Memory Model，遵守既定规则编码即可。 Compiler 和处理器追求的是较少约束的弱 Memory Model，让它们尽己所能地去优化 Performance，让 Performance 最大化。happens-before 原则的设计思想其实非常简单：

- 为了对 Compiler 和处理器的约束尽可能少，只要不改变程序的执行结果（Single Thread 程序和正确执行的 Multithreading 程序），Compiler 和处理器怎么进行 Reordering 优化都行。
- 对于会改变程序执行结果的 Reordering，JMM 要求 Compiler 和处理器必须禁止这种 Reordering。

下面这张是我根据《Java Concurrent Programming 的艺术》这本书中的一张 JMM 设计思想示意图重新绘制的。

![ JMM 设计思想](https://oss.javaguide.cn/github/javaguide/java/concurrent/jmm-design-idea.png)

了解了 happens-before 原则的设计思想，我们再来看看 JSR-133 对 happens-before 原则的定义：

- 如果一个操作 happens-before 另一个操作，那么第一个操作的执行结果将对第二个操作可见，并且第一个操作的执行顺序排在第二个操作之前。
- 两个操作之间存在 happens-before 关系，并不意味着 Java 平台的具体实现必须要按照 happens-before 关系指定的顺序来执行。如果 Reordering 之后的执行结果，与按 happens-before 关系来执行的结果一致，那么 JMM 也允许这样的 Reordering。

我们看下面这段代码：

```java
int userNum = getUserNum();   // 1
int teacherNum = getTeacherNum();   // 2
int totalNum = userNum + teacherNum;  // 3
```

- 1 happens-before 2
- 2 happens-before 3
- 1 happens-before 3

虽然 1 happens-before 2，但对 1 和 2 进行 Reordering 不会影响代码的执行结果，所以 JMM 是允许 Compiler 和处理器执行这种 Reordering 的。但 1 和 2 必须是在 3 执行之前，也就是说 1,2 happens-before 3。

**happens-before 原则表达的意义其实并不是一个操作发生在另外一个操作的前面，虽然这从程序员的角度上来说也并无大碍。更准确地来说，它更想表达的意义是前一个操作的结果对于后一个操作是可见的，无论这两个操作是否在同一个 Thread 里。**

举个例子：操作 1 happens-before 操作 2，即使操作 1 和操作 2 不在同一个 Thread 内，JMM 也会保证操作 1 的结果对操作 2 是可见的。

### happens-before 常见规则有哪些？谈谈你的理解？

happens-before 有多条规则，下面列出其中最常用的 5 条：

1. **程序顺序规则**：一个 Thread 内，按照代码顺序，书写在前面的操作 happens-before 于书写在后面的操作；
2. **Monitor Lock 规则**：对一个 Monitor 的 Unlock happens-before 于随后对同一个 Monitor 的 Locking；
3. **volatile Variable 规则**：对一个 `volatile` Variable 的 Write Operation happens-before 于随后对同一个 Variable 的 Read Operation；
4. **传递规则**：如果 A happens-before B，且 B happens-before C，那么 A happens-before C；
5. **Thread 启动规则**：Thread Object 的 `start()` Method happens-before 于此 Thread 的每一个动作。

这份列表并不完整，还包括 Thread 终止、Thread Interrupt 等规则。两个冲突访问之间如果无法通过完整规则推导出 happens-before 关系，就可能构成数据竞争，其 Visibility 和顺序不能按 Single Thread 直觉来保证；这不等价于 JVM 可以无条件交换任意两条 Instruction，执行结果仍受 JMM 的一致性和因果性规则约束。

### happens-before 和 JMM 什么关系？

happens-before 与 JMM 的关系如下图所示：

![jmm-vs-happens-before](https://oss.javaguide.cn/github/javaguide/java/concurrent/jmm-vs-happens-before.png)

- JMM 向程序员提供了 **“ happens-before 规则 ”**（如程序顺序规则、`volatile` Variable 规则等）。这是一种 **“ 强 Memory Model ”** 的假象：程序员不需要关心底层复杂的 Reordering 细节，只需要按照这些规则编写代码，就能保证 Multithreading 下的 Memory Visibility。
- JVM 在执行时，会将 happens-before 规则映射到具体的实现上。为了在保证正确性的前提下不丧失 Performance，JMM 只会 **“ 禁止影响执行结果的 Reordering ”**。对于不影响 Single Thread 执行结果的 Reordering，JMM 是允许的。
- 最底层是 Compiler 和处理器真实的 **“ Reordering 规则 ”**。

总结来说，JMM 就像是一个中间层：它向上通过 happens-before 为程序员提供简单的编程模型；向下通过禁止特定 Reordering，利用底层硬件 Performance。这种设计既保证了 Multithreading 的安全性，又最大限度释放了硬件的 Performance。

## 再看 Concurrent Programming 三个重要特性

### Atomicity

一次操作或者多次操作，要么所有的操作全部都得到执行并且不会受到任何因素的干扰而 Interrupt，要么都不执行。

在 Java 中，可以借助 `synchronized`、各种 `Lock` 以及各种 Atomic Class 实现 Atomicity。

`synchronized` 和各种 `Lock` 可以保证任一时刻只有一个 Thread 访问该 Code Block，因此可以保障 Atomicity。各种 Atomic Class 是利用 Compare-And-Swap (CAS) (compare and swap) 操作（可能也会用到 `volatile` 或者 `final` Keyword）来保证 Atomic Operation。

### Visibility

当一个 Thread 对 Shared Variable 进行了修改，那么另外的 Thread 都是立即可以看到修改后的最新值。

在 Java 中，可以借助 `synchronized`、`volatile` 以及各种 `Lock` 实现 Visibility。

如果将 Variable 声明为 `volatile`，对该 Variable 的写与后续读之间会建立 happens-before 关系。JVM 必须保证相应的 Visibility 和顺序语义，但具体实现不要求每次都访问物理 Main Memory。

### Ordering

由于 Instruction Reordering 问题，代码的执行顺序未必就是编写代码时候的顺序。

我们上面讲 Reordering 的时候也提到过：

> **Instruction Reordering 可以保证 Serial 语义一致，但是没有义务保证 Multithreading 间的语义也一致**，所以在 Multithreading 下，Instruction Reordering 可能会导致一些问题。

在 Java 中，`volatile` 会约束与该 Variable 读写相关、可能破坏其内存语义的 Reordering，但并不是禁止所有 Instruction Reordering 优化。

## 总结

- Java 是最早尝试提供 Memory Model 的语言，其主要目的是为了简化 Multithreaded Programming，增强程序可移植性的。
- CPU 可以通过制定 Cache Coherence Protocol（比如 [MESI 协议](https://zh.wikipedia.org/wiki/MESI%E5%8D%8F%E8%AE%AE)）来解决内存缓存不一致性问题。
- 为了提升执行速度/Performance，计算机在执行程序代码的时候，会对 Instruction 进行 Reordering。 简单来说就是系统在执行代码的时候并不一定是按照你写的代码的顺序依次执行。**Instruction Reordering 可以保证 Serial 语义一致，但是没有义务保证 Multithreading 间的语义也一致**，所以在 Multithreading 下，Instruction Reordering 可能会导致一些问题。
- 你可以把 JMM 看作是 Java 定义的 Concurrent Programming 相关的一组规范，除了抽象了 Thread 和 Main Memory 之间的关系之外，其还规定了从 Java 源代码到 CPU 可执行 Instruction 的这个转化过程要遵守哪些和 Concurrency 相关的原则和规范，其主要目的是为了简化 Multithreaded Programming，增强程序可移植性的。
- JSR 133 引入了 happens-before 这个概念来描述两个操作之间的 Memory Visibility。

## 参考

- 《Java Concurrent Programming 的艺术》第三章 JMM
- 《深入浅出 Java Multithreading》：<http://concurrent.redspider.group/RedSpider.html>
- Java 内存访问 Reordering 的研究：<https://tech.meituan.com/2014/09/23/java-memory-reordering.html>
- 嘿，同学，你要的 JMM 来了：<https://xie.infoq.cn/article/739920a92d0d27e2053174ef2>
- JSR 133 (Java Memory Model) FAQ：<https://www.cs.umd.edu/~pugh/java/memoryModel/jsr-133-faq.html>

<!-- @include: @article-footer.snippet.md -->
