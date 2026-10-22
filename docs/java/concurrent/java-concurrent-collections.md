---
title: Java 常见 Concurrent Container 总结
description: Java Concurrent Container 全面总结：详解ConcurrentHashMap/CopyOnWriteArrayList/BlockingQueue等JUC Thread-safe Container 特性、适用场景与 Performance 对比。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: Java Concurrent Container,ConcurrentHashMap,CopyOnWriteArrayList,BlockingQueue,ConcurrentLinkedQueue,Thread-safe Container
---

JDK 提供的这些 Container 大部分在 `java.util.concurrent` Package 中。

- **`ConcurrentHashMap`** : Thread-safe 的 `HashMap`
- **`CopyOnWriteArrayList`** : Thread-safe 的 `List`，在读多写少的场合 Performance 非常好，远远好于 `Vector`。
- **`ConcurrentLinkedQueue`** : 高效的 Concurrency Queue，使用 Linked List 实现。可以看做一个 Thread-safe 的 `LinkedList`，这是一个 Non-blocking Queue。
- **`BlockingQueue`** : 这是一个 Interface，JDK 内部通过 Linked List、Array 等方式实现了这个 Interface。表示 Blocking Queue，非常适合用于作为数据 Shared 的通道。
- **`ConcurrentSkipListMap`** : Skip List 的实现。这是一个 Map，使用 Skip List 的 Data Structure 进行快速查找。

## ConcurrentHashMap

我们知道，`HashMap` 是 Not Thread-safe 的，如果在 Concurrency 场景下使用，一种常见的解决方式是通过 `Collections.synchronizedMap()` Method 对 `HashMap` 进行包装，使其变为 Thread-safe。不过，这种方式是通过一个全局 Lock 来同步不同 Thread 间的 Concurrency 访问，会导致严重的 Performance 瓶颈，尤其是在 High Concurrency 场景下。

为了解决这一问题，`ConcurrentHashMap` 应运而生，作为 `HashMap` 的 Thread-safe 版本，它提供了更高效的 Concurrency 处理能力。

在 JDK1.7 的时候，`ConcurrentHashMap` 对整个桶 Array 进行了分割分段(`Segment`，Segmented Lock)，每一把 Lock 只 Lock Container 其中一部分数据（下面有示意图），Multithreading 访问 Container 里不同数据段的数据，就不会存在 Lock Contention，提 High Concurrency 访问率。

![Java7 ConcurrentHashMap 存储结构](https://oss.javaguide.cn/github/javaguide/java/collection/java7_concurrenthashmap.png)

到了 JDK1.8 的时候，`ConcurrentHashMap` 取消了 `Segment` Segmented Lock，采用 `Node + CAS + synchronized` 来保证 Concurrency-safe。 Data Structure 跟 `HashMap` 1.8 的结构类似，Array+Linked List/红黑 Binary Tree。Java 8 在 Linked List Length 超过一定 Threshold（8）时将 Linked List（寻址时间复杂度为 O(N)）转换为 Red-Black Tree（寻址时间复杂度为 O(log(N))）。

Java 8 中，更新操作的 Lock 粒度更细：需要 Locking 时，`synchronized` Lock 的是对应桶的首 Node，不同桶上的更新通常可以 Concurrency 进行。读取操作一般不需要 Locking，也可以与更新操作 Concurrency 进行。

![Java8 ConcurrentHashMap 存储结构](https://oss.javaguide.cn/github/javaguide/java/collection/java8_concurrenthashmap.png)

关于 `ConcurrentHashMap` 的详细介绍，请看我写的这篇文章：[`ConcurrentHashMap` 源码分析](./../collection/concurrent-hash-map-source-code.md)。

## CopyOnWriteArrayList

在 JDK 1.5 引入 `CopyOnWriteArrayList` 之前，除了较早的 `Vector`，也可以通过 `Collections.synchronizedList()` Package 装普通 `List` 来获得同步访问能力。`Vector` 的增删改查等 Method 基本都加了 `synchronized`，单个 Method Invocation 具备 Thread Safety，但 Compound Operation 仍需额外同步。

JDK1.5 引入了 `Java.util.concurrent`（JUC）包，其中提供了很多 Thread-safe 且 Concurrency Performance 良好的 Container，其中唯一的 Thread-safe `List` 实现就是 `CopyOnWriteArrayList`。

对于大部分业务场景来说，读取操作往往是远大于写入操作的。由于读取操作不会对原有数据进行修改，因此，对于每次读取都进行 Locking 其实是一种资源浪费。相比之下，我们应该允许多个 Thread 同时访问 `List` 的内部数据，毕竟对于读取操作来说是安全的。

这种思路与 `ReentrantReadWriteLock` Read-Write Lock 的设计思想非常类似，即读读 Non-exclusive、读写 Mutual Exclusion、写写 Mutual Exclusion（只有读读 Non-exclusive）。`CopyOnWriteArrayList` 更进一步地实现了这一思想。为了将 Read Operation Performance 发挥到极致，`CopyOnWriteArrayList` 中的读取操作是完全无需 Locking 的。更加厉害的是，写入操作也不会 Blocking 读取操作，只有写写才会 Mutual Exclusion。这样一来，Read Operation 的 Performance 就可以大幅度提升。

`CopyOnWriteArrayList` Thread-safe 的核心在于其采用了 **写时复制（Copy-On-Write）** 的策略，从 `CopyOnWriteArrayList` 的名字就能看出了。

当需要修改（`add`，`set`、`remove` 等操作） `CopyOnWriteArrayList` 的内容时，不会直接修改原 Array，而是会先创建底层 Array 的副本，对副本 Array 进行修改，修改完之后再将修改后的 Array 赋值回去，这样就可以保证 Write Operation 不会影响 Read Operation 了。

关于 `CopyOnWriteArrayList` 的详细介绍，请看我写的这篇文章：[`CopyOnWriteArrayList` 源码分析](./../collection/copyonwritearraylist-source-code.md)。

## ConcurrentLinkedQueue

Java 提供的 Thread-safe 的 `Queue` 可以分为**Blocking Queue**和**Non-blocking Queue**，其中 Blocking Queue 的典型例子是 `BlockingQueue`，Non-blocking Queue 的典型例子是 `ConcurrentLinkedQueue`，在实际应用中要根据实际需要选用 Blocking Queue 或者 Non-blocking Queue。 **Blocking Queue 可以通过 Locking 来实现，Non-blocking Queue 可以通过 Compare-And-Swap (CAS) 操作实现。**

从名字可以看出，`ConcurrentLinkedQueue` 这个 Queue 使用 Linked List 作为其 Data Structure．`ConcurrentLinkedQueue` 应该算是在 High Concurrency 环境中 Performance 最好的 Queue 了。它之所有能有很好的 Performance，是因为其内部复杂的实现。

`ConcurrentLinkedQueue` 内部代码我们就不分析了，大家知道 `ConcurrentLinkedQueue` 主要使用 CAS Non-blocking Algorithm 来实现 Thread-safe 就好了。

`ConcurrentLinkedQueue` 适合在对 Performance 要求相对较高，同时对 Queue 的读写存在多个 Thread 同时进行的场景，即如果对 Queue Locking 的成本较高则适合使用 Lock-Free 的 `ConcurrentLinkedQueue` 来替代。

## BlockingQueue

### BlockingQueue 简介

上面我们己经提到了 `ConcurrentLinkedQueue` 作为 High Performance 的 Non-blocking Queue。下面我们要讲到的是 Blocking Queue——`BlockingQueue`。 Blocking Queue（`BlockingQueue`）被广泛使用在“Producer-Consumer”问题中，其原因是 `BlockingQueue` 提供了可 Blocking 的插入和移除的 Method。当 Queue Container 已满，Producer Thread 会被 Blocking，直到 Queue 未满；当 Queue Container 为空时，Consumer Thread 会被 Blocking，直至 Queue 非空时为止。

`BlockingQueue` 是一个 Interface，Inheritance 自 `Queue`，所以其 Implementation Class 也可以作为 `Queue` 的实现来使用，而 `Queue` 又 Inheritance 自 `Collection` Interface。下面是 `BlockingQueue` 的相关 Implementation Class：

![BlockingQueue 的 Implementation Class](https://oss.javaguide.cn/github/javaguide/java/51622268.jpg)

下面主要介绍一下 3 个常见的 `BlockingQueue` 的 Implementation Class：`ArrayBlockingQueue`、`LinkedBlockingQueue`、`PriorityBlockingQueue`。

### ArrayBlockingQueue

`ArrayBlockingQueue` 是 `BlockingQueue` Interface 的有界 Queue Implementation Class，底层采用 Array 来实现。

```java
public class ArrayBlockingQueue<E>
extends AbstractQueue<E>
implements BlockingQueue<E>, Serializable{}
```

`ArrayBlockingQueue` 一旦创建，Capacity 不能改变。其 Concurrency 控制采用 Reentrant Lock `ReentrantLock`，不管是插入操作还是读取操作，都需要获取到 Lock 才能进行操作。当 Queue Capacity 满时，尝试将元素放入 Queue 将导致操作 Blocking；尝试从一个空 Queue 中取一个元素也会同样 Blocking。

`ArrayBlockingQueue` 默认情况下不能保证等待 Thread 访问 Queue 的 Fairness。启用 Fair 策略后，Queue 在存在竞争时会按 FIFO 顺序授予等待中的 Producer 或 Consumer 访问机会；这描述的是 Queue 中的等待顺序，并不等同于 Operating System 严格按墙上时间调度 Thread。 Nonfair 模式下，长时间 Blocking 的 Thread 可能仍然无法及时访问 Queue。 Fair 策略通常会降低 Throughput，如果需要可以采用如下代码：

```java
private static ArrayBlockingQueue<Integer> blockingQueue = new ArrayBlockingQueue<Integer>(10,true);
```

### LinkedBlockingQueue

`LinkedBlockingQueue` 底层基于**Singly Linked List**实现的 Blocking Queue，可以当做无界 Queue 也可以当做有界 Queue 来使用，同样满足 FIFO 的特性，与 `ArrayBlockingQueue` 相比起来具有更高的 Throughput，为了防止 `LinkedBlockingQueue` Capacity 迅速增，损耗大量内存。通常在创建 `LinkedBlockingQueue` Object 时，会指定其大小，如果未指定，Capacity 等于 `Integer.MAX_VALUE`。

**相关 Constructor:**

```java
    /**
     *某种意义上的无界队列
     * Creates a {@code LinkedBlockingQueue} with a capacity of
     * {@link Integer#MAX_VALUE}.
     */
    public LinkedBlockingQueue() {
        this(Integer.MAX_VALUE);
    }

    /**
     *有界队列
     * Creates a {@code LinkedBlockingQueue} with the given (fixed) capacity.
     *
     * @param capacity the capacity of this queue
     * @throws IllegalArgumentException if {@code capacity} is not greater
     *         than zero
     */
    public LinkedBlockingQueue(int capacity) {
        if (capacity <= 0) throw new IllegalArgumentException();
        this.capacity = capacity;
        last = head = new Node<E>(null);
    }
```

### PriorityBlockingQueue

`PriorityBlockingQueue` 是一个支持优先级的无界 Blocking Queue。默认情况下元素采用自然顺序进行排序，也可以通过自定义 Class 实现 `compareTo()` Method 来指定元素排序规则，或者 Initialization 时通过 Constructor Parameter `Comparator` 来指定排序规则。

`PriorityBlockingQueue` Concurrency 控制采用的是 Reentrant Lock `ReentrantLock`，Queue 为无界 Queue（`ArrayBlockingQueue` 是有界 Queue，`LinkedBlockingQueue` 也可以通过在 Constructor 中传入 `capacity` 指定 Queue 最大的 Capacity，但是 `PriorityBlockingQueue` 只能指定初始的 Queue 大小，后面插入元素的时候，**如果空间不够的话会自动 Resize**）。

简单地说，它就是 `PriorityQueue` 的 Thread-safe 版本。不可以插入 null 值，同时，插入 Queue 的 Object 必须是可比较大小的（comparable），否则报 `ClassCastException` Exception。它的插入操作 put Method 不会 block，因为它是无界 Queue（take Method 在 Queue 为空的时候会 Blocking）。

**推荐文章：** [《解读 Java Concurrency Queue BlockingQueue》](https://javadoop.com/post/java-concurrent-queue)

## ConcurrentSkipListMap

> 下面这部分内容参考了极客时间专栏[《Data Structure 与 Algorithm 之美》](https://time.geekbang.org/column/intro/126?code=zl3GYeAsRI4rEJIBNu5B/km7LSZsPDlGWQEpAYw5Vu0=&utm_term=SPoster “《Data Structure 与 Algorithm 之美》”)以及《实战 Java High Concurrency 程序设计》。

为了引出 `ConcurrentSkipListMap`，先带着大家简单理解一下 Skip List。

对于一个单 Linked List，即使 Linked List 是有序的，如果我们想要在其中查找某个数据，也只能从头到尾 Traversal Linked List，这样效率自然就会很低，Skip List 就不一样了。 Skip List 是一种可以用来快速查找的 Data Structure，有点类似于 Balanced Tree。它们都可以对元素进行快速的查找。但一个重要的区别是：对 Balanced Tree 的插入和删除往往很可能导致 Balanced Tree 进行一次全局的调整。而对 Skip List 的插入和删除只需要对整个 Data Structure 的局部进行操作即可。这样带来的好处是：在 High Concurrency 的情况下，你会需要一个全局 Lock 来保证整个 Balanced Tree 的 Thread-safe。而对于 Skip List，你只需要部分 Lock 即可。这样，在 High Concurrency 环境下，你就可以拥有更好的 Performance。而就查询的 Performance 而言，Skip List 的时间复杂度也是 **O(logn)** 所以在 Concurrency Data Structure 中，JDK 使用 Skip List 来实现一个 Map。

Skip List 的本质是同时维护了多个 Linked List，并且 Linked List 是分层的，

![2级 Index Skip List](https://oss.javaguide.cn/github/javaguide/java/93666217.jpg)

最低层的 Linked List 维护了 Skip List 内所有的元素，每上面一层 Linked List 都是下面一层的子集。

Skip List 内的所有 Linked List 的元素都是排序的。查找时，可以从顶级 Linked List 开始找。一旦发现被查找的元素小于当前访问 Node 的 Successor（或 Successor 为空），就会转入下一层 Linked List 继续找。这也就是说在查找过程中，搜索是跳跃式的。如上图所示，在 Skip List 中查找元素 18。

![在 Skip List 中查找元素18](https://oss.javaguide.cn/github/javaguide/java/32005738.jpg)

查找 18 的时候原来需要 Traversal 18 次，现在只需要 7 次即可。针对 Linked List Length 比较大的时候，构建 Index 查找效率的提升就会非常明显。

从上面很容易看出，**Skip List 是一种利用空间换时间的 Algorithm。**

使用 Skip List 实现 `Map` 和使用哈希 Algorithm 实现 `Map` 的另外一个不同之处是：哈希并不会保存元素的顺序，而 Skip List 内所有的元素都是排序的。因此在对 Skip List 进行 Traversal 时，你会得到一个有序的结果。所以，如果你的应用需要 Ordering，那么 Skip List 就是你不二的选择。JDK 中实现这一 Data Structure 的 Class 是 `ConcurrentSkipListMap`。

## 参考

- 《实战 Java High Concurrency 程序设计》
- <https://javadoop.com/post/java-concurrent-queue>
- <https://juejin.im/post/5aeebd02518825672f19c546>

<!-- @include: @article-footer.snippet.md -->
