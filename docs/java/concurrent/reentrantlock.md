---
title: 从ReentrantLock的实现看AbstractQueuedSynchronizer (AQS)的原理及应用
description: ReentrantLock与AQS原理深度解析：详解ReentrantLock Reentrant Lock 实现、Fair Lock 与 Nonfair Lock 区别、基于AQS的 Locking Unlock 流程、与synchronized Performance 对比。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: ReentrantLock,AQS,Fair Lock,Nonfair Lock,Reentrant Lock,lock unlock,ReentrantLock原理,synchronized对比
---

> 本文转载自：<https://tech.meituan.com/2019/12/05/aqs-theory-and-apply.html>
>
> 作者：美团技术团队

Java 中的大部分同步 Class（Semaphore、ReentrantLock 等）都是基于 AbstractQueuedSynchronizer（简称为 AQS）实现的。AQS 是一种提供了 Atomic 式管理 Synchronization State、Blocking 和唤醒 Thread 功能以及 Queue 模型的简单框架。

本文会从应用层逐渐深入到原理层，并通过 ReentrantLock 的基本特性和 ReentrantLock 与 AQS 的关联，来深入解读 AQS 相关 Exclusive Lock 的知识点，同时采取问答的模式来帮助大家理解 AQS。由于篇幅原因，本篇文章主要阐述 AQS 中 Exclusive Lock 的逻辑和 Sync Queue，不讲述包含 Shared Lock 和 Condition Queue 的部分（本篇文章核心为 AQS 原理剖析，只是简单介绍了 ReentrantLock，感兴趣同学可以阅读一下 ReentrantLock 的源码）。

> 本文的源码分析基于 JDK 8。AQS 的内部实现后来持续演进：JDK 11 中仍能看到本文涉及的主要 Field 和 Method，JDK 17 及当前版本的 Node Field 和 Enqueue、等待实现则已有较大变化。 Synchronization State、Wait Queue 以及获取/释放资源的核心思路仍可作为理解基础。

## 1 ReentrantLock

### 1.1 ReentrantLock 特性概览

ReentrantLock 意思为 Reentrant Lock，指的是一个 Thread 能够对一个临界资源重复 Locking。为了帮助大家更好地理解 ReentrantLock 的特性，我们先将 ReentrantLock 跟常用的 Synchronized 进行比较，其特性如下（蓝色部分为本篇文章主要剖析的点）：

![](https://p0.meituan.net/travelcube/412d294ff5535bbcddc0d979b2a339e6102264.png)

下面通过伪代码，进行更加直观的比较：

```java
// **************************Synchronized的使用方式**************************
// 1.用于代码块
synchronized (this) {}
// 2.用于对象
synchronized (object) {}
// 3.用于方法
public synchronized void test () {}
// 4.可重入
for (int i = 0; i < 100; i++) {
  synchronized (this) {}
}
// **************************ReentrantLock的使用方式**************************
public void test () throws Exception {
  // 1.初始化选择公平锁、非公平锁
  ReentrantLock lock = new ReentrantLock(true);
  // 2.可用于代码块
  lock.lock();
  try {
    // 3.支持多种加锁方式，比较灵活; 具有可重入特性
    if (lock.tryLock(100, TimeUnit.MILLISECONDS)) {
      try {
        // 获取第二次锁之后执行的逻辑
      } finally {
        // 每次成功加锁都要对应释放一次
        lock.unlock();
      }
    }
  } finally {
    lock.unlock();
  }
}
```

### 1.2 ReentrantLock 与 AQS 的关联

通过上文我们已经了解，ReentrantLock 支持 Fair Lock 和 Nonfair Lock（关于 Fair Lock 和 Nonfair Lock 的原理分析，可参考《[不可不说的 Java“Lock”事](https://mp.weixin.qq.com/s?__biz=MjM5NjQ5MTI5OA==&mid=2651749434&idx=3&sn=5ffa63ad47fe166f2f1a9f604ed10091&chksm=bd12a5778a652c61509d9e718ab086ff27ad8768586ea9b38c3dcf9e017a8e49bcae3df9bcc8&scene=38#wechat_redirect)》），并且 ReentrantLock 的底层就是由 AQS 来实现的。那么 ReentrantLock 是如何通过 Fair Lock 和 Nonfair Lock 与 AQS 关联起来呢？ 我们着重从这两者的 Locking 过程来理解一下它们与 AQS 之间的关系（Locking 过程中与 AQS 的关联比较明显，Unlock 流程后续会介绍）。

Nonfair Lock 源码中的 Locking 流程如下：

```java
// java.util.concurrent.locks.ReentrantLock#NonfairSync

// 非公平锁
static final class NonfairSync extends Sync {
  ...
  final void lock() {
    if (compareAndSetState(0, 1))
      setExclusiveOwnerThread(Thread.currentThread());
    else
      acquire(1);
    }
  ...
}
```

这块代码的含义为：

- 若通过 Compare-And-Swap (CAS) 设置 Variable State（Synchronization State）成功，也就是 Acquire Lock 成功，则将 Current Thread 设置为 Exclusive Thread。
- 若通过 CAS 设置 Variable State（Synchronization State）失败，也就是 Acquire Lock 失败，则进入 Acquire Method 进行后续处理。

第一步很好理解，但第二步 Acquire Lock 失败后，后续的处理策略是怎么样的呢？这块可能会有以下思考：

- 某个 Thread Acquire Lock 失败的后续流程是什么呢？有以下两种可能：

(1) 将 Current Thread 获 Lock 结果设置为失败，Acquire Lock 流程结束。这种设计会极大降低系统的 Concurrency 度，并不满足我们实际的需求。所以就需要下面这种流程，也就是 AQS 框架的处理流程。

(2) 存在某种排队等候机制，Thread 继续等待，仍然保留 Acquire Lock 的可能，Acquire Lock 流程仍在继续。

- 对于问题 1 的第二种情况，既然说到了排队等候机制，那么就一定会有某种 Queue 形成，这样的 Queue 是什么 Data Structure 呢？
- 处于排队等候机制中的 Thread，什么时候可以有机会 Acquire Lock 呢？
- 如果处于排队等候机制中的 Thread 一直无法 Acquire Lock，还是需要一直等待吗，还是有别的策略来解决这一问题？

带着 Nonfair Lock 的这些问题，再看下 Fair Lock 源码中获 Lock 的方式：

```java
// java.util.concurrent.locks.ReentrantLock#FairSync

static final class FairSync extends Sync {
  ...
  final void lock() {
    acquire(1);
  }
  ...
}
```

看到这块代码，我们可能会存在这种疑问：Lock Function 通过 Acquire Method 进行 Locking，但是具体是如何 Locking 的呢？

结合 Fair Lock 和 Nonfair Lock 的 Locking 流程，虽然流程上有一定的不同，但是都调用了 Acquire Method，而 Acquire Method 是 FairSync 和 UnfairSync 的 Superclass AQS 中的核心 Method。

对于上边提到的问题，其实在 ReentrantLock Class 源码中都无法解答，而这些问题的答案，都是位于 Acquire Method 所在的 Class AbstractQueuedSynchronizer 中，也就是本文的核心——AQS。下面我们会对 AQS 以及 ReentrantLock 和 AQS 的关联做详细介绍（相关问题答案会在 2.3.5 小节中解答）。

## 2 AQS

首先，我们通过下面的架构图来整体了解一下 AQS 框架：

![](https://p1.meituan.net/travelcube/82077ccf14127a87b77cefd1ccf562d3253591.png)

- 上图中有颜色的为 Method，无颜色的为 Attribution。
- 总的来说，AQS 框架共分为五层，自上而下由浅入深，从 AQS 对外暴露的 API 到底层基础数据。
- 当有自定义 Synchronizer 接入时，只需 Override 第一层所需要的部分 Method 即可，不需要关注底层具体的实现流程。当自定义 Synchronizer 进行 Locking 或者 Unlock 操作时，先经过第一层的 API 进入 AQS 内部 Method，然后经过第二层进 Row Lock 的获取，接着对于 Acquire Lock 失败的流程，进入第三层和第四层的 Wait Queue 处理，而这些处理方式均依赖于第五层的基础数据提供层。

下面我们会从整体到细节，从流程到 Method 逐一剖析 AQS 框架，主要分析过程如下：

![](https://p1.meituan.net/travelcube/d2f7f7fffdc30d85d17b44266c3ab05323338.png)

### 2.1 原理概览

AQS 核心思想是，如果被请求的 Shared Resource 空闲，那么就将当前请求资源的 Thread 设置为有效的 Worker Thread，将 Shared Resource 设置为 Lock 状态；如果 Shared Resource 被占用，就需要一定的 Blocking 等待唤醒机制来保证 Lock 分配。这个机制主要用的是 CLH Queue 的变体实现的，将暂时获取不到 Lock 的 Thread 加入到 Queue 中。

CLH：Craig、Landin and Hagersten Queue，是 Singly Linked List，AQS 中的 Queue 是 CLH 变体的虚拟双向 Queue（FIFO），AQS 是通过将每条请求 Shared Resource 的 Thread Encapsulate 成一个 Node 来实现 Lock 的分配。

主要原理图如下：

![](https://p0.meituan.net/travelcube/7132e4cef44c26f62835b197b239147b18062.png)

AQS 使用一个 Volatile 的 int Type 的 Instance Variable 来表示 Synchronization State，通过内置的 FIFO Queue 来完成资源获取的排队工作，通过 CAS 完成对 State 值的修改。

#### 2.1.1 AQS Data Structure

先来看下 AQS 中最基本的 Data Structure——Node，Node 即为上面 CLH Variant Queue 中的 Node。

![](https://p1.meituan.net/travelcube/960271cf2b5c8a185eed23e98b72c75538637.png)

解释一下几个 Method 和属性值的含义：

| Method 和属性值 | 含义 |
| :----------- | :----------------------------------------------------------------------------------------------- |
| waitStatus | 当前 Node 在 Queue 中的状态 |
| thread | 表示处于该 Node 的 Thread |
| prev | 前驱 Pointer |
| predecessor | 返回 Predecessor，没有的话抛出 npe |
| nextWaiter | 指向下一个处于 CONDITION 状态的 Node（由于本篇文章不讲述 Condition Queue Queue，这个 Pointer 不多介绍） |
| next | 后继 Pointer |

Thread 两种 Lock 的模式：

| 模式 | 含义 |
| :-------- | :----------------------------- |
| SHARED | 表示 Thread 以 Shared 的模式等待 Lock |
| EXCLUSIVE | 表示 Thread 正在以 Exclusive 的方式等待 Lock |

waitStatus 有下面几个 Enum 值：

| Enum | 含义 |
| :-------- | :----------------------------------------------- |
| 0 | 当一个 Node 被 Initialization 的时候的默认值 |
| CANCELLED | 为 1，表示 Thread Acquire Lock 的请求已经取消了 |
| CONDITION | 为-2，表示 Node 在 Wait Queue 中，Node Thread 等待唤醒 |
| PROPAGATE | 为-3，Current Thread 处在 SHARED 情况下，该 Field 才会使用 |
| SIGNAL | 为-1，表示 Thread 已经准备好了，就等资源释放了 |

#### 2.1.2 Synchronization State State

在了解 Data Structure 后，接下来了解一下 AQS 的 Synchronization State——State。AQS 中维护了一个名为 state 的 Field，意为 Synchronization State，是由 Volatile 修饰的，用于展示当前临界资源的获 Lock 情况。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private volatile int state;
```

下面提供了几个访问这个 Field 的 Method：

| Method Name | 描述 |
| :----------------------------------------------------------------- | :---------------------- |
| protected final int getState() | 获取 State 的值 |
| protected final void setState(int newState) | 设置 State 的值 |
| protected final boolean compareAndSetState(int expect, int update) | 使用 CAS 方式更新 State |

这几个 Method 都是 Final 修饰的，说明 Subclass 中无法 Override 它们。我们可以通过修改 State Field Table 示的 Synchronization State 来实现 Multithreading 的 Exclusive Mode 和 Shared Mode（Locking 过程）。

![](https://p0.meituan.net/travelcube/27605d483e8935da683a93be015713f331378.png)

![](https://p0.meituan.net/travelcube/3f1e1a44f5b7d77000ba4f9476189b2e32806.png)

对于我们自定义的同步工具，需要自定义获取 Synchronization State 和释放状态的方式，也就是 AQS 架构图中的第一层：API 层。

### 2.2 AQS 重要 Method 与 ReentrantLock 的关联

从架构图中可以得知，AQS 提供了大量用于自定义 Synchronizer 实现的 Protected Method。自定义 Synchronizer 实现的相关 Method 也只是为了通过修改 State Field 来实现 Multithreading 的 Exclusive Mode 或者 Shared Mode。自定义 Synchronizer 需要实现以下 Method（ReentrantLock 需要实现的 Method 如下，并不是全部）：

| Method Name | 描述 |
| :------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------- |
| protected boolean isHeldExclusively() | 该 Thread 是否正在 Exclusive 资源。只有用到 Condition 才需要去实现它。 |
| protected boolean tryAcquire(int arg) | Exclusive 方式。arg 为 Acquire Lock 的次数，尝试获取资源，成功则返回 True，失败则返回 False。 |
| protected boolean tryRelease(int arg) | Exclusive 方式。arg 为 Release Lock 的次数，尝试释放资源，成功则返回 True，失败则返回 False。 |
| protected int tryAcquireShared(int arg) | Shared 方式。arg 为 Acquire Lock 的次数，尝试获取资源。负数表示失败；0 表示成功，但没有剩余可用资源；正数表示成功，且有剩余资源。 |
| protected boolean tryReleaseShared(int arg) | Shared 方式。arg 为 Release Lock 的次数，尝试释放资源，如果释放后允许唤醒后续等待结点返回 True，否则返回 False。 |

一般来说，自定义 Synchronizer 要么是 Exclusive 方式，要么是 Shared 方式，它们也只需实现 tryAcquire-tryRelease、tryAcquireShared-tryReleaseShared 中的一种即可。AQS 也支持自定义 Synchronizer 同时实现 Exclusive 和 Shared 两种方式，如 ReentrantReadWriteLock。ReentrantLock 是 Exclusive Lock，所以实现了 tryAcquire-tryRelease。

以 Nonfair Lock 为例，这里主要阐述一下 Nonfair Lock 与 AQS 之间 Method 的关联之处，具体每一处核心 Method 的作用会在文章后面详细进行阐述。

![](https://p1.meituan.net/travelcube/b8b53a70984668bc68653efe9531573e78636.png)

> 🐛 修正（参见：[issue#1761](https://github.com/Snailclimb/JavaGuide/issues/1761)）: 图中的一处小错误，(AQS)CAS 修改 Shared Resource State 成功之后应该是 Acquire Lock 成功（Nonfair Lock）。
>
> 对应的源码如下：
>
> ```java
> final boolean nonfairTryAcquire(int acquires) {
>          final Thread current = Thread.currentThread();//获取当前线程
>          int c = getState();
>          if (c == 0) {
>              if (compareAndSetState(0, acquires)) {//CAS抢锁
>                  setExclusiveOwnerThread(current);//设置当前线程为独占线程
>                  return true;//抢锁成功
>              }
>          }
>          else if (current == getExclusiveOwnerThread()) {
>              int nextc = c + acquires;
>              if (nextc < 0) // overflow
>                  throw new Error("Maximum lock count exceeded");
>              setState(nextc);
>              return true;
>          }
>          return false;
>      }
> ```

为了帮助大家理解 ReentrantLock 和 AQS 之间 Method 的交互过程，以 Nonfair Lock 为例，我们将 Locking 和 Unlock 的交互流程单独拎出来强调一下，以便于对后续内容的理解。

![](https://p1.meituan.net/travelcube/7aadb272069d871bdee8bf3a218eed8136919.png)

Locking：

- 通过 ReentrantLock 的 Locking Method Lock 进行 Locking 操作。
- 会调用到 Inner Class Sync 的 Lock Method，由于 Sync#lock 是 Abstract Method，根据 ReentrantLock Initialization 选择的 Fair Lock 和 Nonfair Lock，执行相关 Inner Class 的 Lock Method，本质上都会执行 AQS 的 Acquire Method。
- AQS 的 Acquire Method 会执行 tryAcquire Method，但是由于 tryAcquire 需要自定义 Synchronizer 实现，因此执行了 ReentrantLock 中的 tryAcquire Method，由于 ReentrantLock 是通过 Fair Lock 和 Nonfair Lock Inner Class 实现的 tryAcquire Method，因此会根据 Lock Type 不同，执行不同的 tryAcquire。
- tryAcquire 是 Acquire Lock 逻辑，获取失败后，会执行框架 AQS 的后续逻辑，跟 ReentrantLock 自定义 Synchronizer 无关。

Unlock：

- 通过 ReentrantLock 的 Unlock Method Unlock 进行 Unlock。
- Unlock 会调用 Inner Class Sync 的 Release Method，该 Method Inheritance 于 AQS。
- Release 中会调用 tryRelease Method，tryRelease 需要自定义 Synchronizer 实现，tryRelease 只在 ReentrantLock 中的 Sync 实现，因此可以看出，Release Lock 的过程，并不区分是否为 Fair Lock。
- 释放成功后，所有处理由 AQS 框架完成，与自定义 Synchronizer 无关。

通过上面的描述，大概可以总结出 ReentrantLock Locking Unlock 时 API 层核心 Method 的映射关系。

![](https://p0.meituan.net/travelcube/f30c631c8ebbf820d3e8fcb6eee3c0ef18748.png)

## 3 通过 ReentrantLock 理解 AQS

ReentrantLock 中 Fair Lock 和 Nonfair Lock 在底层是相同的，这里以 Nonfair Lock 为例进行分析。

在 Nonfair Lock 中，有一段这样的代码：

```java
// java.util.concurrent.locks.ReentrantLock

static final class NonfairSync extends Sync {
  ...
  final void lock() {
    if (compareAndSetState(0, 1))
      setExclusiveOwnerThread(Thread.currentThread());
    else
      acquire(1);
  }
  ...
}
```

看一下这个 Acquire 是怎么写的：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

public final void acquire(int arg) {
  if (!tryAcquire(arg) && acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
    selfInterrupt();
}
```

再看一下 tryAcquire Method：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

protected boolean tryAcquire(int arg) {
  throw new UnsupportedOperationException();
}
```

可以看出，这里只是 AQS 的简单实现，具体 Acquire Lock 的实现方法是由各自的 Fair Lock 和 Nonfair Lock 单独实现的（以 ReentrantLock 为例）。如果该 Method 返回了 True，则说明 Current Thread Acquire Lock 成功，就不用往后执行了；如果获取失败，就需要加入到 Wait Queue 中。下面会详细解释 Thread 是何时以及怎样被加入进 Wait Queue 中的。

### 3.1 Thread 加入 Wait Queue

#### 3.1.1 加入 Queue 的时机

当执行 Acquire(1)时，会通过 tryAcquire Acquire Lock。在这种情况下，如果 Acquire Lock 失败，就会调用 addWaiter 加入到 Wait Queue 中去。

#### 3.1.2 如何加入 Queue

Acquire Lock 失败后，会执行 addWaiter(Node.EXCLUSIVE)加入 Wait Queue，具体实现方法如下：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private Node addWaiter(Node mode) {
  Node node = new Node(Thread.currentThread(), mode);
  // Try the fast path of enq; backup to full enq on failure
  Node pred = tail;
  if (pred != null) {
    node.prev = pred;
    if (compareAndSetTail(pred, node)) {
      pred.next = node;
      return node;
    }
  }
  enq(node);
  return node;
}
private final boolean compareAndSetTail(Node expect, Node update) {
  return unsafe.compareAndSwapObject(this, tailOffset, expect, update);
}
```

主要的流程如下：

- 通过当前的 Thread 和 Lock 模式新建一个 Node。
- Pred Pointer 指向 Tail Node Tail。
- 将 New 中 Node 的 Prev Pointer 指向 Pred。
- 通过 compareAndSetTail Method，完成 Tail Node 的设置。这个 Method 主要是对 tailOffset 和 Expect 进行比较，如果 tailOffset 的 Node 和 Expect 的 Node Address 是相同的，那么设置 Tail 的值为 Update 的值。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

static {
  try {
    stateOffset = unsafe.objectFieldOffset(AbstractQueuedSynchronizer.class.getDeclaredField("state"));
    headOffset = unsafe.objectFieldOffset(AbstractQueuedSynchronizer.class.getDeclaredField("head"));
    tailOffset = unsafe.objectFieldOffset(AbstractQueuedSynchronizer.class.getDeclaredField("tail"));
    waitStatusOffset = unsafe.objectFieldOffset(Node.class.getDeclaredField("waitStatus"));
    nextOffset = unsafe.objectFieldOffset(Node.class.getDeclaredField("next"));
  } catch (Exception ex) {
    throw new Error(ex);
  }
}
```

从 AQS 的静态 Code Block 可以看出，都是获取一个 Object 的属性相对于该 Object 在内存当中的 Offset，这样我们就可以根据这个 Offset 在 Object 内存当中找到这个属性。tailOffset 指的是 tail 对应的 Offset，所以这个时候会将 new 出来的 Node 置为当前 Queue 的 Tail Node。同时，由于是 Doubly Linked List，也需要将前一个 Node 指向 Tail Node。

- 如果 Pred Pointer 是 Null（说明 Wait Queue 中没有元素），或者当前 Pred Pointer 和 Tail 指向的位置不同（说明被别的 Thread 已经修改），就需要看一下 Enq 的 Method。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private Node enq(final Node node) {
  for (;;) {
    Node t = tail;
    if (t == null) { // Must initialize
      if (compareAndSetHead(new Node()))
        tail = head;
    } else {
      node.prev = t;
      if (compareAndSetTail(t, node)) {
        t.next = node;
        return t;
      }
    }
  }
}
```

如果没有被 Initialization，需要进行 Initialization 一个 Head Node 出来。但请注意，Initialization 的 Head Node 并不是 Current Thread Node，而是调用了无参 Constructor 的 Node。如果经历了 Initialization 或者 Concurrency 导致 Queue 中有元素，则与之前的 Method 相同。其实，addWaiter 就是一个在双端 Linked List 添加 Tail Node 的操作，需要注意的是，双端 Linked List 的 Head Node 是一个无参 Constructor 的 Head Node。

总结一下，Thread Acquire Lock 的时候，过程大体如下：

1、当没有 Thread 获取到 Lock 时，Thread 1 Acquire Lock 成功。

2、Thread 2 申请 Lock，但是 Lock 被 Thread 1 占有。

![img](https://p0.meituan.net/travelcube/e9e385c3c68f62c67c8d62ab0adb613921117.png)

3、如果再有 Thread 要 Acquire Lock，依次在 Queue 中往后排队即可。

回到上边的代码，hasQueuedPredecessors 是 Fair Lock Locking 时判断 Wait Queue 中是否存在有效 Node 的 Method。如果返回 False，说明 Current Thread 可以争取 Shared Resource；如果返回 True，说明 Queue 中存在有效 Node，Current Thread 必须加入到 Wait Queue 中。

```java
// java.util.concurrent.locks.ReentrantLock

public final boolean hasQueuedPredecessors() {
  // The correctness of this depends on head being initialized
  // before tail and on head.next being accurate if the current
  // thread is first in queue.
  Node t = tail; // Read fields in reverse initialization order
  Node h = head;
  Node s;
  return h != t && ((s = h.next) == null || s.thread != Thread.currentThread());
}
```

看到这里，我们理解一下 h != t && ((s = h.next) == null || s.thread != Thread.currentThread());为什么要判断的 Head Node 的下一个 Node？第一个 Node 储存的数据是什么？

> Doubly Linked List 中，第一个 Node 为 Dummy Node，其实并不存储任何信息，只是占位。真正的第一个有数据的 Node，是在第二个 Node 开始的。当 h != t 时：如果(s = h.next) == null，Wait Queue 正在有 Thread 进行 Initialization，但只是进行到了 Tail 指向 Head，没有将 Head 指向 Tail，此时 Queue 中有元素，需要返回 True（这块具体见下边代码分析）。 如果(s = h.next) != null，说明此时 Queue 中至少有一个有效 Node。如果此时 s.thread == Thread.currentThread()，说明 Wait Queue 的第一个有效 Node 中的 Thread 与 Current Thread 相同，那么 Current Thread 是可以获取资源的；如果 s.thread != Thread.currentThread()，说明 Wait Queue 的第一个有效 Node Thread 与 Current Thread 不同，Current Thread 必须加入进 Wait Queue。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer#enq

if (t == null) { // Must initialize
  if (compareAndSetHead(new Node()))
    tail = head;
} else {
  node.prev = t;
  if (compareAndSetTail(t, node)) {
    t.next = node;
    return t;
  }
}
```

Node Enqueue 不是 Atomic Operation，所以会出现短暂的 head != tail，此时 Tail 指向最后一个 Node，而且 Tail 指向 Head。如果 Head 没有指向 Tail（可见 5、6、7 行），这种情况下也需要将相关 Thread 加入 Queue 中。所以这块代码是为了解决极端情况下的 Concurrency 问题。

#### 3.1.3 Wait Queue 中 Thread 出 Queue 时机

回到最初的源码：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

public final void acquire(int arg) {
  if (!tryAcquire(arg) && acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
    selfInterrupt();
}
```

上文解释了 addWaiter Method，这个 Method 其实就是把对应的 Thread 以 Node 的 Data Structure 形式加入到 Deque 里，返回的是一个包含该 Thread 的 Node。而这个 Node 会作为 Parameter，进入到 acquireQueued Method 中。acquireQueued Method 可以对排队中的 Thread 进行“获 Lock”操作。

总的来说，一个 Thread Acquire Lock 失败后会被放入 Wait Queue，`acquireQueued` 会让它持续等待并 Try Acquire，直到获取成功。`acquire(int)` 是 Uninterruptible 的获取方式：等待期间发生 Interrupt 时会先记录 Interrupt Status，在成功 Acquire Lock 后再通过 `selfInterrupt()` 恢复，而不会因此取消此次获取。

下面我们从“何时出 Queue？”和“如何出 Queue？”两个方向来分析一下 acquireQueued 源码：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

final boolean acquireQueued(final Node node, int arg) {
  // 标记是否成功拿到资源
  boolean failed = true;
  try {
    // 标记等待过程中是否中断过
    boolean interrupted = false;
    // 开始自旋，要么获取锁，要么中断
    for (;;) {
      // 获取当前节点的前驱节点
      final Node p = node.predecessor();
      // 如果p是头结点，说明当前节点在真实数据队列的首部，就尝试获取锁（别忘了头结点是虚节点）
      if (p == head && tryAcquire(arg)) {
        // 获取锁成功，头指针移动到当前node
        setHead(node);
        p.next = null; // help GC
        failed = false;
        return interrupted;
      }
      // 说明p为头节点且当前没有获取到锁（可能是非公平锁被抢占了）或者是p不为头结点，这个时候就要判断当前node是否要被阻塞（被阻塞条件：前驱节点的waitStatus为-1），防止无限循环浪费资源。具体两个方法下面细细分析
      if (shouldParkAfterFailedAcquire(p, node) && parkAndCheckInterrupt())
        interrupted = true;
    }
  } finally {
    if (failed)
      cancelAcquire(node);
  }
}
```

注：setHead Method 是把当前 Node 置为 Dummy Node，但并没有修改 waitStatus，因为它是一直需要用的数据。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private void setHead(Node node) {
  head = node;
  node.thread = null;
  node.prev = null;
}

// java.util.concurrent.locks.AbstractQueuedSynchronizer

// 靠前驱节点判断当前线程是否应该被阻塞
private static boolean shouldParkAfterFailedAcquire(Node pred, Node node) {
  // 获取前驱结点的节点状态
  int ws = pred.waitStatus;
  // 说明前驱结点处于唤醒状态
  if (ws == Node.SIGNAL)
    return true;
  // 通过枚举值我们知道waitStatus>0是取消状态
  if (ws > 0) {
    do {
      // 循环向前查找取消节点，把取消节点从队列中剔除
      node.prev = pred = pred.prev;
    } while (pred.waitStatus > 0);
    pred.next = node;
  } else {
    // 设置前任节点等待状态为SIGNAL
    compareAndSetWaitStatus(pred, ws, Node.SIGNAL);
  }
  return false;
}
```

parkAndCheckInterrupt 主要用于挂起 Current Thread，Blocking 调用 Stack，返回 Current Thread 的 Interrupt Status。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private final boolean parkAndCheckInterrupt() {
    LockSupport.park(this);
    return Thread.interrupted();
}
```

上述 Method 的流程图如下：

![](https://p0.meituan.net/travelcube/c124b76dcbefb9bdc778458064703d1135485.png)

从上图可以看出，跳出当前 Loop 的条件是当“Predecessor 是 Head Node，且 Current Thread Acquire Lock 成功”。为了防止因 Infinite Loop 导致 CPU 资源被浪费，我们会判断 Predecessor 的状态来决定是否要将 Current Thread 挂起，具体挂起流程用流程图表示如下（shouldParkAfterFailedAcquire 流程）：

![](https://p0.meituan.net/travelcube/9af16e2481ad85f38ca322a225ae737535740.png)

从 Queue 中释放 Node 的疑虑打消了，那么又有新问题了：

- shouldParkAfterFailedAcquire 中取消 Node 是怎么生成的呢？什么时候会把一个 Node 的 waitStatus 设置为-1？
- 是在什么时间释放 Node 通知到被挂起的 Thread 呢？

### 3.2 CANCELLED 状态 Node 生成

acquireQueued Method 中的 Finally 代码：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

final boolean acquireQueued(final Node node, int arg) {
  boolean failed = true;
  try {
    ...
    for (;;) {
      final Node p = node.predecessor();
      if (p == head && tryAcquire(arg)) {
        ...
        failed = false;
        ...
      }
      ...
  } finally {
    if (failed)
      cancelAcquire(node);
    }
}
```

通过 cancelAcquire Method，将 Node 的状态标记为 CANCELLED。接下来，我们逐行来分析这个 Method 的原理：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private void cancelAcquire(Node node) {
  // 将无效节点过滤
  if (node == null)
    return;
  // 设置该节点不关联任何线程，也就是虚节点
  node.thread = null;
  Node pred = node.prev;
  // 通过前驱节点，跳过取消状态的node
  while (pred.waitStatus > 0)
    node.prev = pred = pred.prev;
  // 获取过滤后的前驱节点的后继节点
  Node predNext = pred.next;
  // 把当前node的状态设置为CANCELLED
  node.waitStatus = Node.CANCELLED;
  // 如果当前节点是尾节点，将从后往前的第一个非取消状态的节点设置为尾节点
  // 更新失败的话，则进入else，如果更新成功，将tail的后继节点设置为null
  if (node == tail && compareAndSetTail(node, pred)) {
    compareAndSetNext(pred, predNext, null);
  } else {
    int ws;
    // 如果当前节点不是head的后继节点，1:判断当前节点前驱节点的是否为SIGNAL，2:如果不是，则把前驱节点设置为SIGNAL看是否成功
    // 如果1和2中有一个为true，再判断当前节点的线程是否为null
    // 如果上述条件都满足，把当前节点的前驱节点的后继指针指向当前节点的后继节点
    if (pred != head && ((ws = pred.waitStatus) == Node.SIGNAL || (ws <= 0 && compareAndSetWaitStatus(pred, ws, Node.SIGNAL))) && pred.thread != null) {
      Node next = node.next;
      if (next != null && next.waitStatus <= 0)
        compareAndSetNext(pred, predNext, next);
    } else {
      // 如果当前节点是head的后继节点，或者上述条件不满足，那就唤醒当前节点的后继节点
      unparkSuccessor(node);
    }
    node.next = node; // help GC
  }
}
```

当前的流程：

- 获取当前 Node 的 Predecessor，如果 Predecessor 的状态是 CANCELLED，那就一直往前 Traversal，找到第一个 waitStatus <= 0 的 Node，将找到的 Pred Node 和当前 Node 关联，将当前 Node 设置为 CANCELLED。
- 根据当前 Node 的位置，考虑以下三种情况：

(1) 当前 Node 是 Tail Node。

(2) 当前 Node 是 Head 的 Successor。

(3) 当前 Node 不是 Head 的 Successor，也不是 Tail Node。

根据上述第二条，我们来分析每一种情况的流程。

当前 Node 是 Tail Node。

![](https://p1.meituan.net/travelcube/b845211ced57561c24f79d56194949e822049.png)

当前 Node 是 Head 的 Successor。

![](https://p1.meituan.net/travelcube/ab89bfec875846e5028a4f8fead32b7117975.png)

当前 Node 不是 Head 的 Successor，也不是 Tail Node。

![](https://p0.meituan.net/travelcube/45d0d9e4a6897eddadc4397cf53d6cd522452.png)

通过上面的流程，我们对于 CANCELLED Node 状态的产生和变化已经有了大致的了解，但是为什么所有的变化都是对 Next Pointer 进行了操作，而没有对 Prev Pointer 进行操作呢？什么情况下会对 Prev Pointer 进行操作？

> 执行 cancelAcquire 的时候，当前 Node 的 Predecessor 可能已经从 Queue 中出去了（已经执行过 Try Code Block 中的 shouldParkAfterFailedAcquire Method 了），如果此时修改 Prev Pointer，有可能会导致 Prev 指向另一个已经移除 Queue 的 Node，因此这块变化 Prev Pointer 不安全。 shouldParkAfterFailedAcquire Method 中，会执行下面的代码，其实就是在处理 Prev Pointer。shouldParkAfterFailedAcquire 是 Acquire Lock 失败的情况下才会执行，进入该 Method 后，说明 Shared Resource 已被获取，当前 Node 之前的 Node 都不会出现变化，因此这个时候变更 Prev Pointer 比较安全。
>
> ```java
> do {
>   node.prev = pred = pred.prev;
> } while (pred.waitStatus > 0);
> ```

### 3.3 如何 Unlock

我们已经剖析了 Locking 过程中的基本流程，接下来再对 Unlock 的基本流程进行分析。由于 ReentrantLock 在 Unlock 的时候，并不区分 Fair Lock 和 Nonfair Lock，所以我们直接看 Unlock 的源码：

```java
// java.util.concurrent.locks.ReentrantLock

public void unlock() {
  sync.release(1);
}
```

可以看到，本质 Release Lock 的地方，是通过框架来完成的。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

public final boolean release(int arg) {
  if (tryRelease(arg)) {
    Node h = head;
    if (h != null && h.waitStatus != 0)
      unparkSuccessor(h);
    return true;
  }
  return false;
}
```

在 ReentrantLock 里面的 Fair Lock 和 Nonfair Lock 的 Superclass Sync 定义了 Reentrant Lock 的释放 Locking Mechanism。

```java
// java.util.concurrent.locks.ReentrantLock.Sync

// 方法返回当前锁是不是没有被线程持有
protected final boolean tryRelease(int releases) {
  // 减少可重入次数
  int c = getState() - releases;
  // 当前线程不是持有锁的线程，抛出异常
  if (Thread.currentThread() != getExclusiveOwnerThread())
    throw new IllegalMonitorStateException();
  boolean free = false;
  // 如果持有线程全部释放，将当前独占锁所有线程设置为null，并更新state
  if (c == 0) {
    free = true;
    setExclusiveOwnerThread(null);
  }
  setState(c);
  return free;
}
```

我们来解释下述源码：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

public final boolean release(int arg) {
  // 上边自定义的tryRelease如果返回true，说明该锁没有被任何线程持有
  if (tryRelease(arg)) {
    // 获取头结点
    Node h = head;
    // 头结点不为空并且头结点的waitStatus不是初始化节点情况，解除线程挂起状态
    if (h != null && h.waitStatus != 0)
      unparkSuccessor(h);
    return true;
  }
  return false;
}
```

这里的判断条件为什么是 h != null && h.waitStatus != 0？

> h == null Head 还没 Initialization。初始情况下，head == null，第一个 Node Enqueue，Head 会被 Initialization 一个 Dummy Node。所以说，这里如果还没来得及 Enqueue，就会出现 head == null 的情况。
>
> h != null && waitStatus == 0 表明 Successor 对应的 Thread 仍在运行中，不需要唤醒。
>
> h != null && waitStatus < 0 表明 Successor 可能被 Blocking 了，需要唤醒。

再看一下 unparkSuccessor Method：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private void unparkSuccessor(Node node) {
  // 获取头结点waitStatus
  int ws = node.waitStatus;
  if (ws < 0)
    compareAndSetWaitStatus(node, ws, 0);
  // 获取当前节点的下一个节点
  Node s = node.next;
  // 如果下个节点是null或者下个节点被cancelled，就找到队列最开始的非cancelled的节点
  if (s == null || s.waitStatus > 0) {
    s = null;
    // 就从尾部节点开始找，到队首，找到队列第一个waitStatus<0的节点。
    for (Node t = tail; t != null && t != node; t = t.prev)
      if (t.waitStatus <= 0)
        s = t;
  }
  // 如果当前节点的下个节点不为空，而且状态<=0，就把当前节点unpark
  if (s != null)
    LockSupport.unpark(s.thread);
}
```

为什么要从后往前找第一个非 Cancelled 的 Node 呢？原因如下。

之前的 addWaiter Method：

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private Node addWaiter(Node mode) {
  Node node = new Node(Thread.currentThread(), mode);
  // Try the fast path of enq; backup to full enq on failure
  Node pred = tail;
  if (pred != null) {
    node.prev = pred;
    if (compareAndSetTail(pred, node)) {
      pred.next = node;
      return node;
    }
  }
  enq(node);
  return node;
}
```

我们从这里可以看到，Node Enqueue 并不是 Atomic Operation，也就是说，node.prev = pred; compareAndSetTail(pred, node) 这两个地方可以看作 Tail Enqueue 的 Atomic Operation，但是此时 pred.next = node;还没执行，如果这个时候执行了 unparkSuccessor Method，就没办法从前往后找了，所以需要从后往前找。还有一点原因，在产生 CANCELLED 状态 Node 的时候，先断开的是 Next Pointer，Prev Pointer 并未断开，因此也是必须要从后往前 Traversal 才能够 Traversal 完全部的 Node。

综上所述，如果是从前往后找，由于极端情况下 Enqueue 的非 Atomic Operation 和 CANCELLED Node 产生过程 Interrupt 开 Next Pointer 的操作，可能会导致无法 Traversal 所有的 Node。所以，唤醒对应的 Thread 后，对应的 Thread 就会继续往下执行。继续执行 acquireQueued Method 以后，Interrupt 如何处理？

### 3.4 Interrupt 恢复后的执行流程

唤醒后，会执行 return Thread.interrupted();，这个 Function 返回的是当前执行 Thread 的 Interrupt Status，并清除。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private final boolean parkAndCheckInterrupt() {
  LockSupport.park(this);
  return Thread.interrupted();
}
```

再回到 acquireQueued 代码，当 parkAndCheckInterrupt 返回 True 或者 False 的时候，interrupted 的值不同，但都会执行下次 Loop。如果这个时候 Acquire Lock 成功，就会把当前 interrupted 返回。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

final boolean acquireQueued(final Node node, int arg) {
  boolean failed = true;
  try {
    boolean interrupted = false;
    for (;;) {
      final Node p = node.predecessor();
      if (p == head && tryAcquire(arg)) {
        setHead(node);
        p.next = null; // help GC
        failed = false;
        return interrupted;
      }
      if (shouldParkAfterFailedAcquire(p, node) && parkAndCheckInterrupt())
        interrupted = true;
      }
  } finally {
    if (failed)
      cancelAcquire(node);
  }
}
```

如果 acquireQueued 为 True，就会执行 selfInterrupt Method。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

static void selfInterrupt() {
  Thread.currentThread().interrupt();
}
```

该 Method 其实是为了 Interrupt Thread。但为什么获取了 Lock 以后还要 Interrupt Thread 呢？这部分属于 Java 提供的协作式 Interrupt 知识内容，感兴趣同学可以查阅一下。这里简单介绍一下：

1. 当 Interrupt Thread 被唤醒时，并不知道被唤醒的原因，可能是 Current Thread 在等待中被 Interrupt，也可能是释放了 Lock 以后被唤醒。因此我们通过 Thread.interrupted()Method 检查 Interrupt Flag（该 Method 返回了 Current Thread 的 Interrupt Status，并将 Current Thread 的 Interrupt 标识设置为 False），并记录下来，如果发现该 Thread 被 Interrupt 过，就再 Interrupt 一次。
2. Thread 在等待资源的过程中被唤醒，唤醒后还是会不断地去 Try Acquire，直到抢到 Lock 为止。也就是说，在整个流程中，并不响应 Interrupt，只是记录 Interrupt 记录。最后抢到 Lock 返回了，那么如果被 Interrupt 过的话，就需要补充一次 Interrupt。

这里的处理方式主要是运用 Thread Pool 中基本运作单元 Worder 中的 runWorker，通过 Thread.interrupted()进行额外的判断处理，感兴趣的同学可以看下 ThreadPoolExecutor 源码。

### 3.5 小结

我们在 1.3 小节中提出了一些问题，现在来回答一下。

> Q：某个 Thread Acquire Lock 失败的后续流程是什么呢？
>
> A：存在某种排队等候机制，Thread 继续等待，仍然保留 Acquire Lock 的可能，Acquire Lock 流程仍在继续。
>
> Q：既然说到了排队等候机制，那么就一定会有某种 Queue 形成，这样的 Queue 是什么 Data Structure 呢？
>
> A：是 CLH 变体的 FIFO Deque。
>
> Q：处于排队等候机制中的 Thread，什么时候可以有机会 Acquire Lock 呢？
>
> A：可以详细看下 2.3.1.3 小节。
>
> Q：如果处于排队等候机制中的 Thread 一直无法 Acquire Lock，需要一直等待么？还是有别的策略来解决这一问题？
>
> A：Thread 所在 Node 的状态会变成取消状态，取消状态的 Node 会从 Queue 中释放，具体可见 2.3.2 小节。
>
> Q：Lock Function 通过 Acquire Method 进行 Locking，但是具体是如何 Locking 的呢？
>
> A：AQS 的 Acquire 会调用 tryAcquire Method，tryAcquire 由各个自定义 Synchronizer 实现，通过 tryAcquire 完成 Locking 过程。

## 4 AQS 应用

### 4.1 ReentrantLock 的 Reentrant 应用

ReentrantLock 的 Reentrancy 是 AQS 很好的应用之一，在了解完上述知识点以后，我们很容易得知 ReentrantLock 实现 Reentrant 的 Method。在 ReentrantLock 里面，不管是 Fair Lock 还是 Nonfair Lock，都有一段逻辑。

Fair Lock：

```java
// java.util.concurrent.locks.ReentrantLock.FairSync#tryAcquire

if (c == 0) {
  if (!hasQueuedPredecessors() && compareAndSetState(0, acquires)) {
    setExclusiveOwnerThread(current);
    return true;
  }
}
else if (current == getExclusiveOwnerThread()) {
  int nextc = c + acquires;
  if (nextc < 0)
    throw new Error("Maximum lock count exceeded");
  setState(nextc);
  return true;
}
```

Nonfair Lock：

```java
// java.util.concurrent.locks.ReentrantLock.Sync#nonfairTryAcquire

if (c == 0) {
  if (compareAndSetState(0, acquires)){
    setExclusiveOwnerThread(current);
    return true;
  }
}
else if (current == getExclusiveOwnerThread()) {
  int nextc = c + acquires;
  if (nextc < 0) // overflow
    throw new Error("Maximum lock count exceeded");
  setState(nextc);
  return true;
}
```

从上面这两段都可以看到，有一个 Synchronization State State 来控制整体 Reentrant 的情况。State 是 Volatile 修饰的，用于保证一定的 Visibility 和 Ordering。

```java
// java.util.concurrent.locks.AbstractQueuedSynchronizer

private volatile int state;
```

接下来看 State 这个 Field 主要的过程：

1. State Initialization 的时候为 0，表示没有任何 Thread Hold Lock。
2. 当有 Thread 持有该 Lock 时，值就会在原来的基础上+1，同一个 Thread 多次获得 Lock 是，就会多次+1，这里就是 Reentrant 的概念。
3. Unlock 也是对这个 Field-1，一直到 0，此 Thread 对 Lock 释放。

### 4.2 JUC 中的应用场景

除了上边 ReentrantLock 的 Reentrancy 的应用，AQS 作为 Concurrent Programming 的框架，为很多其他同步工具提供了良好的解决方案。下面列出了 JUC 中的几种同步工具，大体介绍一下 AQS 的应用场景：

| 同步工具 | 同步工具与 AQS 的关联 |
| :--------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ReentrantLock | 使用 AQS 保存 Lock 重复持有的次数。当一个 Thread Acquire Lock 时，ReentrantLock 记录当前获得 Lock 的 Thread 标识，用于检测是否重复获取，以及错误 Thread 试图 Unlock 操作时异常情况的处理。 |
| Semaphore | 使用 AQS Synchronization State 来保存信号量的当前计数。tryRelease 会增加计数，acquireShared 会减少计数。 |
| CountDownLatch | 使用 AQS Synchronization State 来表示计数。计数为 0 时，所有的 Acquire 操作（CountDownLatch 的 await Method）才可以通过。 |
| ReentrantReadWriteLock | 使用 AQS Synchronization State 中的 16 位保存 Write Lock 持有的次数，剩下的 16 位用于保存 Read Lock 的持有次数。 |
| ThreadPoolExecutor | Worker 利用 AQS Synchronization State 实现对 Exclusive Thread Variable 的设置（tryAcquire 和 tryRelease）。 |

### 4.3 自定义同步工具

了解 AQS 基本原理以后，按照上面所说的 AQS 知识点，自己实现一个同步工具。

```java
public class LeeLock  {

    private static class Sync extends AbstractQueuedSynchronizer {
        @Override
        protected boolean tryAcquire (int arg) {
            if (compareAndSetState(0, 1)) {
                setExclusiveOwnerThread(Thread.currentThread());
                return true;
            }
            return false;
        }

        @Override
        protected boolean tryRelease (int arg) {
            if (getState() == 0 || getExclusiveOwnerThread() != Thread.currentThread()) {
                throw new IllegalMonitorStateException();
            }
            setExclusiveOwnerThread(null);
            setState(0);
            return true;
        }

        @Override
        protected boolean isHeldExclusively () {
            return getState() == 1 && getExclusiveOwnerThread() == Thread.currentThread();
        }
    }

    private final Sync sync = new Sync();

    public void lock () {
        sync.acquire(1);
    }

    public void unlock () {
        sync.release(1);
    }
}
```

通过我们自己定义的 Lock 完成一定的同步功能。

```java
public class LeeMain {

    static int count = 0;
    static LeeLock leeLock = new LeeLock();

    public static void main (String[] args) throws InterruptedException {

        Runnable runnable = new Runnable() {
            @Override
            public void run () {
                try {
                    leeLock.lock();
                    for (int i = 0; i < 10000; i++) {
                        count++;
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    leeLock.unlock();
                }

            }
        };
        Thread thread1 = new Thread(runnable);
        Thread thread2 = new Thread(runnable);
        thread1.start();
        thread2.start();
        thread1.join();
        thread2.join();
        System.out.println(count);
    }
}
```

上述代码每次运行结果都会是 20000。通过简单的几行代码就能实现同步功能，这就是 AQS 的强大之处。

## 5 总结

我们日常开发中使用 Concurrency 的场景太多，但是对 Concurrency 内部的基本框架原理了解的人却不多。由于篇幅原因，本文仅介绍了 Reentrant Lock ReentrantLock 的原理和 AQS 原理，希望能够成为大家了解 AQS 和 ReentrantLock 等 Synchronizer 的“敲门砖”。

## 参考资料

- Lea D. The java. util. concurrent synchronizer framework\[J]. Science of Computer Programming, 2005, 58(3): 293-309.
- 《Java Concurrent Programming 实战》
- [不可不说的 Java“Lock”事](https://tech.meituan.com/2018/11/15/java-lock.html)

<!-- @include: @article-footer.snippet.md -->
