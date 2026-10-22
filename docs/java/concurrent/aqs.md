---
title: AbstractQueuedSynchronizer (AQS) 详解
description: AQS抽象 Queue Synchronizer 深度解析：详解AQS核心原理、CLH Queue 结构、Exclusive Lock 与 Shared Lock 实现、ReentrantLock/Semaphore等 Synchronizer 应用、Thread Blocking 唤醒机制。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: AQS,AbstractQueuedSynchronizer,Queue Synchronizer,Exclusive Lock,Shared Lock,CLH Queue,ReentrantLock实现原理
---

<!-- markdownlint-disable MD024 -->

## AQS 介绍

AQS 的全称为 `AbstractQueuedSynchronizer`，翻译过来的意思就是抽象 Queue Synchronizer。这个 Class 在 `java.util.concurrent.locks` Package 下面。

![](https://oss.javaguide.cn/github/javaguide/AQS.png)

AQS 就是一个 Abstract Class，主要用来构建 Lock 和 Synchronizer。

```java
public abstract class AbstractQueuedSynchronizer extends AbstractOwnableSynchronizer implements java.io.Serializable {
}
```

AQS 为构建 Lock 和 Synchronizer 提供了一些通用功能的实现。因此，使用 AQS 能简单且高效地构造出应用广泛的大量 Synchronizer，比如 `ReentrantLock`、`Semaphore`、`ReentrantReadWriteLock` 等。`SynchronousQueue` 虽然也使用 Wait Queue 和 Compare-And-Swap (CAS) 实现 Thread 配对，但并不基于 AQS。

## AQS 原理

> 说明：下文的 AQS 源码和 Node 状态分析主要基于 JDK 8。AQS 的内部实现后来持续演进：JDK 11 中仍能看到本文涉及的 `waitStatus`、`addWaiter()`、`acquireQueued()` 等 Field 或 Method，JDK 17 及当前版本的 Node Field 和 Enqueue、等待实现则已有较大变化。基于 Synchronization State、Wait Queue 和 Template Method 构建 Synchronizer 的整体思路没有改变。

在面试中被问到 Concurrency 知识的时候，大多都会被问到“请你说一下自己对于 AQS 原理的理解”。下面给大家一个示例供大家参考，面试不是背题，大家一定要加入自己的思想，即使加入不了自己的思想也要保证自己能够通俗的讲出来而不是背出来。

### AQS 快速了解

在真正讲解 AQS 源码之前，需要对 AQS 有一个整体层面的认识。这里会先通过几个问题，从整体层面上认识 AQS，了解 AQS 在整个 Java Concurrency 中所位于的层面，之后在学习 AQS 源码的过程中，才能更加了解 Synchronizer 和 AQS 之间的关系。

#### AQS 的作用是什么？

AQS 解决了开发者在实现 Synchronizer 时的复杂性问题。它提供了一个通用框架，用于实现各种 Synchronizer，例如 **Reentrant Lock**（`ReentrantLock`）、**信号量**（`Semaphore`）和 **CountDownLatch**（`CountDownLatch`）。通过 Encapsulation 底层的 Thread Synchronization 机制，AQS 将复杂的 Thread 管理逻辑隐藏起来，使开发者只需专注于具体的同步逻辑。

简单来说，AQS 是一个 Abstract Class，为 Synchronizer 提供了通用的 **执行框架**。它定义了 **资源获取和释放的通用流程**，而具体的资源获取逻辑则由具体 Synchronizer 通过 Override Template Method 来实现。 因此，可以将 AQS 看作是 Synchronizer 的 **基础“底座”**，而 Synchronizer 则是基于 AQS 实现的 **具体“应用”**。

#### AQS 为什么使用 CLH Lock Queue 的变体？

CLH Lock 是一种基于 **Spin Lock** 的优化实现。

先说一下 Spin Lock 存在的问题：Spin Lock 通过 Thread 不断对一个 Atomic Variable 执行 `compareAndSet`（简称 `CAS`）操作来 Try Acquire。在 High Concurrency 场景下，多个 Thread 会同时竞争同一个 Atomic Variable，容易造成某个 Thread 的 `CAS` 操作长时间失败，从而导致 **“Starvation”问题**（某些 Thread 可能永远无法 Acquire Lock）。

CLH Lock 通过引入一个 Queue 来组织 Concurrency 竞争的 Thread，对 Spin Lock 进行了改进：

- 每个 Thread 会作为一个 Node 加入到 Queue 中，并通过 Spin Monitoring 前一个 Thread Node 的状态，而不是直接竞争 Shared Variable。
- Thread 按顺序排队，确保 Fairness，从而避免了 “Starvation” 问题。

AQS（AbstractQueuedSynchronizer）在 CLH Lock 的基础上进一步优化，形成了其内部的 **CLH Queue 变体**。主要改进点有以下两方面：

1. **Spin + Blocking**： CLH Lock 使用纯 Spin 方式等待 Lock 的释放，但大量的 Spin 操作会占用过多的 CPU 资源。AQS 引入了 **Spin + Blocking** 的混合机制：
   - 如果 Thread Acquire Lock 失败，会先短暂 Spin Try Acquire；
   - 如果仍然失败，则 Thread 会进入 Blocking 状态，等待被唤醒，从而减少 CPU 的浪费。
2. **单向 Queue 改为双向 Queue**：CLH Lock 使用单向 Queue，Node 只知道 Predecessor 的状态，而当某个 Node Release Lock 时，需要通过 Queue 唤醒后续 Node。AQS 将 Queue 改为 **双向 Queue**，新增了 `next` Pointer，使得 Node 不仅知道 Predecessor，也可以直接唤醒 Successor，从而简化了 Queue 操作，提高了唤醒效率。

#### AQS 的 Performance 比较好，原因是什么？

因为 AQS 内部大量使用了 `CAS` 操作。

AQS 内部通过 Queue 来存储等待的 Thread Node。由于 Queue 是 Shared Resource，在 Multithreading 场景下，需要保证 Queue 的同步访问。

AQS 内部通过 `CAS` 操作来控制 Queue 的同步访问，`CAS` 操作主要用于控制 `队列初始化`、 `线程节点入队` 两个操作的 Concurrency-safe。虽然利用 `CAS` 控制 Concurrency-safe 可以保证比较好的 Performance，但同时会带来比较高的 **编码复杂度**。

#### AQS 中为什么 Node Node 需要不同的状态？

AQS 中的 `waitStatus` 状态类似于 **State Machine**，通过不同状态来表明 Node Node 的不同含义，并且根据不同操作，来控制状态之间的流转。

- 状态 `0`：新 Node 加入 Queue 之后，初始状态为 `0`。

- 状态 `SIGNAL`：当有新的 Node 加入 Queue，此时新 Node 的前继 Node 状态就会由 `0` 更新为 `SIGNAL`，表示前继 Node Release Lock 之后，需要对新 Node 进行唤醒操作。如果唤醒 `SIGNAL` 状态 Node 的后续 Node，就会将 `SIGNAL` 状态更新为 `0`。即通过清除 `SIGNAL` 状态，表示已经执行了唤醒操作。

- 状态 `CANCELLED`：如果一个 Node 在 Queue 中等待 Acquire Lock 时，因为某种原因失败了，该 Node 的状态就会变为 `CANCELLED`，表明取消 Acquire Lock，这种状态的 Node 是 Exception 的，无法被唤醒，也无法唤醒 Successor。

### AQS 核心思想

AQS 核心思想是，如果被请求的 Shared Resource 空闲，则将当前请求资源的 Thread 设置为有效的 Worker Thread，并且将 Shared Resource 设置为 Lock 状态。如果被请求的 Shared Resource 被占用，那么就需要一套 Thread Blocking 等待以及被唤醒时 Lock 分配的机制，这个机制 AQS 是基于 **CLH Lock**（Craig, Landin, and Hagersten locks） 进一步优化实现的。

**CLH Lock** 对 Spin Lock 进行了改进，是基于单 Linked List 的 Spin Lock。在 Multithreading 场景下，会将请求 Acquire Lock 的 Thread Group 织成一个单向 Queue，每个等待的 Thread 会通过 Spin 访问前一个 Thread Node 的状态，前一个 Node Release Lock 之后，当前 Node 才可以 Acquire Lock。**CLH Lock** 的 Queue 结构如下图所示。

![CLH Lock 的 Queue 结构](https://oss.javaguide.cn/github/javaguide/open-source-project/clh-lock-queue-structure.png)

AQS 中使用的 **Wait Queue** 是 CLH Lock Queue 的变体（接下来简称为 CLH Variant Queue）。

AQS 的 CLH Variant Queue 是一个双向 Queue，会暂时获取不到 Lock 的 Thread 将被加入到该 Queue 中，CLH Variant Queue 和原本的 CLH Lock Queue 的区别主要有两点：

- 由 **Spin** 优化为 **Spin + Blocking**：Spin 操作的 Performance 很高，但大量的 Spin 操作比较占用 CPU 资源，因此在 CLH Variant Queue 中会先通过 Spin Try Acquire，如果失败再进行 Blocking 等待。
- 由 **单向 Queue** 优化为 **双向 Queue**：在 CLH Variant Queue 中，会对等待的 Thread 进行 Blocking Operation，当 Queue 前边的 Thread Release Lock 之后，需要对后边的 Thread 进行唤醒，因此增加了 `next` Pointer，成为了双向 Queue。

AQS 将每条请求 Shared Resource 的 Thread Encapsulate 成一个 CLH Variant Queue 的一个结点（Node）来实现 Lock 的分配。在 CLH Variant Queue 中，一个 Node 表示一个 Thread，它保存着 Thread 的 Reference（thread）、 当前 Node 在 Queue 中的状态（waitStatus）、Predecessor（prev）、Successor（next）。

AQS 中的 CLH Variant Queue 结构如下图所示：

![CLH Variant Queue 结构](https://oss.javaguide.cn/github/javaguide/java/concurrent/clh-queue-structure-bianti.png)

关于 AQS 核心 Data Structure-CLH Lock 的详细解读，强烈推荐阅读 [Java AQS 核心 Data Structure-CLH Lock - Qunar 技术沙龙](https://mp.weixin.qq.com/s/jEx-4XhNGOFdCo4Nou5tqg) 这篇文章。

AQS(`AbstractQueuedSynchronizer`)的核心原理图：

![CLH Variant Queue](https://oss.javaguide.cn/github/javaguide/java/concurrent/clh-queue-state.png)

AQS 使用 **int Instance Variable `state` 表示 Synchronization State**，通过内置的 **FIFO Thread 等待/Wait Queue** 来完成获取资源 Thread 的排队工作。

`state` Variable 由 `volatile` 修饰，用于展示当前临界资源的获取情况。这里 `volatile` 的作用不仅仅是保证 Visibility，更重要的是通过 happens-before 规则（volatile Variable 的 Write Operation 先行发生于后续的 Read Operation）防止 Compiler 和处理器对 Instruction 进行 Reordering，从而保证 Lock 语义的正确性。

```java
// 共享变量，使用volatile修饰，保证线程可见性并防止指令重排序
private volatile int state;
```

另外，状态信息 `state` 可以通过 `protected` Type 的 `getState()`、`setState()` 和 `compareAndSetState()` 进行操作。并且，这几个 Method 都是 `final` 修饰的，在 Subclass 中无法被 Override。

```java
//返回同步状态的当前值
protected final int getState() {
     return state;
}
 // 设置同步状态的值
protected final void setState(int newState) {
     state = newState;
}
//原子地（CAS操作）将同步状态值设置为给定值update如果当前同步状态的值等于expect（期望值）
protected final boolean compareAndSetState(int expect, int update) {
      return unsafe.compareAndSwapInt(this, stateOffset, expect, update);
}
```

以 Reentrant 的 Mutex `ReentrantLock` 为例，它的内部维护了一个 `state` Variable，用来表示 Lock 的占用状态。`state` 的初始值为 0，表示 Lock 处于未 Lock 状态。当 Thread A 调用 `lock()` Method 时，会尝试通过 `tryAcquire()` Method Exclusive 该 Lock，并让 `state` 的值加 1。如果成功了，那么 Thread A 就获取到了 Lock。如果失败了，那么 Thread A 就会被加入到一个 Wait Queue（CLH Variant Queue）中，直到其他 Thread 释放该 Lock。假设 Thread A Acquire Lock 成功了，Release Lock 之前，A Thread 自己是可以重复获取此 Lock 的（`state` 会累加）。这就是 Reentrancy 的体现：一个 Thread 可以多次获取同一个 Lock 而不会被 Blocking。但是，这也意味着，一个 Thread 必须释放与获取的次数相同的 Lock，才能让 `state` 的值回到 0，也就是让 Lock 恢复到未 Lock 状态。只有这样，其他等待的 Thread 才能有机会获取该 Lock。

Thread A Try Acquire 的过程如下图所示（图源[从 ReentrantLock 的实现看 AQS 的原理及应用 - 美团技术团队](./reentrantlock.md)）：

![AQS Exclusive Mode Acquire Lock](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-exclusive-mode-acquire-lock.png)

再以 CountDownLatch `CountDownLatch` 为例，可以将 `state` Initialization 为 N，表示需要等待 N 次 `countDown()` 调用。N 表示事件数或计数次数，不要求与 Thread Count 一致；同一个 Thread 可以调用多次 `countDown()`，也可以由多个 Thread 分别调用。当 `state` 变为 0 时，AQS 会唤醒 Wait Queue 中因调用 `await()` 而 Blocking 的 Thread，这些 Thread 随后可以继续执行。

### Node Node waitStatus 状态含义

AQS 中的 `waitStatus` 状态类似于 **State Machine**，通过不同状态来表明 Node Node 的不同含义，并且根据不同操作，来控制状态之间的流转。

| Node Node 状态 | 值 | 含义 |
| ------------- | --- | ------------------------------------------------------------------------------------------------------------------------- |
| `CANCELLED` | 1 | 表示 Thread 已经取消 Acquire Lock。 Thread 在等待获取资源时被 Interrupt、等待资源 Timeout 会更新为该状态。 |
| `SIGNAL` | -1 | 表示 Successor 需要当前 Node 唤醒。在 Current Thread Node Release Lock 之后，需要对 Successor 进行唤醒。 |
| `CONDITION` | -2 | 表示 Node 在等待 Condition。当其他 Thread 调用了 Condition 的 `signal()` Method 后，Node 会从 Wait Queue 转移到 Sync Queue 中等待获取资源。 |
| `PROPAGATE` | -3 | 用于 Shared Mode。在 Shared Mode 下，可能会出现 Thread 在 Queue 中无法被唤醒的情况，因此引入了 `PROPAGATE` 状态来解决这个问题。 |
| | 0 | 加入 Queue 的新 Node 的初始状态。 |

在 AQS 的源码中，经常使用 `> 0`、 `< 0` 来对 `waitStatus` 进行判断。

如果 `waitStatus > 0`，表明 Node 的状态已经取消等待获取资源。

如果 `waitStatus < 0`，表明 Node 的状态处于正常的状态，即没有取消等待。

其中 `SIGNAL` 状态是最重要的，Node 状态流转以及对应操作如下：

| 状态流转 | 对应操作 |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0` | 新 Node Enqueue 时，初始状态为 `0` 。 |
| `0 -> SIGNAL` | 新 Node Enqueue 时，它的前继 Node 状态会由 `0` 更新为 `SIGNAL` 。`SIGNAL` 状态表明该 Node 的后续 Node 需要被唤醒。 |
| `SIGNAL -> 0` | 在唤醒 Successor 时，需要清除当前 Node 的状态。通常发生在 `head` Node，比如 `head` Node 的状态由 `SIGNAL` 更新为 `0` ，表示已经对 `head` Node 的 Successor 唤醒了。 |
| `0 -> PROPAGATE` | AQS 内部引入了 `PROPAGATE` 状态，为了解决 Concurrency 场景下，可能造成的 Thread Node 无法唤醒的情况。（在 AQS Shared Mode 获取资源的源码分析会讲到） |

### 自定义 Synchronizer

基于 AQS 可以实现自定义的 Synchronizer， AQS 提供了 5 个 Template Method（Template Method 模式）。如果需要自定义 Synchronizer 一般的方式是这样（Template Method 模式很经典的一个应用）：

1. 自定义的 Synchronizer Inheritance `AbstractQueuedSynchronizer`。
2. Override AQS 暴露的 Template Method。

**AQS 使用了 Template Method 模式，自定义 Synchronizer 时需要 Override 下面几个 AQS 提供的 Hook Method：**

```java
//独占方式。尝试获取资源，成功则返回true，失败则返回false。
protected boolean tryAcquire(int)
//独占方式。尝试释放资源，成功则返回true，失败则返回false。
protected boolean tryRelease(int)
//共享方式。尝试获取资源。负数表示失败；0表示成功，但没有剩余可用资源；正数表示成功，且有剩余资源。
protected int tryAcquireShared(int)
//共享方式。尝试释放资源，成功则返回true，失败则返回false。
protected boolean tryReleaseShared(int)
//该线程是否正在独占资源。只有用到condition才需要去实现它。
protected boolean isHeldExclusively()
```

**什么是 Hook Method 呢？** Hook Method 是一种被声明在 Abstract Class 中的 Method，一般使用 `protected` Keyword 修饰，它可以是空 Method（由 Subclass 实现），也可以是默认实现的 Method。模板 Design Pattern 通过 Hook Method 控制固定步骤的实现。

篇幅问题，这里就不详细介绍 Template Method 模式了，不太了解的小伙伴可以看看这篇文章：[用 Java8 改造后的 Template Method 模式真的是 yyds!](https://mp.weixin.qq.com/s/zpScSCktFpnSWHWIQem2jg)。

除了上面提到的 Hook Method 之外，AQS Class 中的其他 Method 都是 `final`，所以无法被其他 Class Override。

### AQS 资源 Shared 方式

AQS 定义两种资源 Shared 方式：`Exclusive`（Exclusive，只有一个 Thread 能执行，如 `ReentrantLock`）和 `Share`（Shared，多个 Thread 可同时执行，如 `Semaphore`/`CountDownLatch`）。

一般来说，自定义 Synchronizer 的 Shared 方式要么是 Exclusive，要么是 Shared，他们也只需实现 `tryAcquire-tryRelease`、`tryAcquireShared-tryReleaseShared` 中的一种即可。但 AQS 也支持自定义 Synchronizer 同时实现 Exclusive 和 Shared 两种方式，如 `ReentrantReadWriteLock`。

### Exclusive Mode 与 Shared Mode 的深入对比

上面简要介绍了 AQS 的两种资源 Shared 方式，下面从多个维度对 Exclusive Mode 和 Shared Mode 进行系统对比，帮助更深入地理解二者的差异。

#### 特性对比

| 对比维度 | Exclusive Mode（Exclusive） | Shared Mode（Share） |
| ---------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **Concurrency 度** | 同一时刻只有一个 Thread 能获取到资源 | 同一时刻可以有多个 Thread 同时获取到资源 |
| **获取资源入口** | `acquire(int arg)` | `acquireShared(int arg)` |
| **释放资源入口** | `release(int arg)` | `releaseShared(int arg)` |
| **需要 Override 的 Template Method** | `tryAcquire(int)` / `tryRelease(int)` | `tryAcquireShared(int)` / `tryReleaseShared(int)` |
| **tryXxx Return Value** | `boolean`，`true` 表示获取/释放成功 | `int`（获取时），负数表示失败，0 表示成功但无剩余资源，正数表示成功且有剩余资源；`boolean`（释放时） |
| **唤醒 Successor** | 释放资源时唤醒一个 Successor | 获取资源成功后，如果还有剩余资源，会继续唤醒后续 Node（传播唤醒） |
| **Node Type 标识** | `Node.EXCLUSIVE`（`null`） | `Node.SHARED`（一个静态的 `Node` Instance） |
| **典型实现** | `ReentrantLock`、`ReentrantReadWriteLock` 的 Write Lock | `Semaphore`、`CountDownLatch`、`ReentrantReadWriteLock` 的 Read Lock |

#### `state` 在不同 Synchronizer 中的语义

AQS 中的 `state` 是一个通用的 Synchronization State Variable，不同的 Synchronizer 赋予它不同的含义：

| Synchronizer | 模式 | `state` 的语义 |
| ------------------------ | ----------- | --------------------------------------------------------------------------------- |
| `ReentrantLock` | Exclusive | 表示 Lock 的 Reentrancy Count。`state == 0` 表示 Lock 空闲；`state > 0` 表示 Lock 被持有，值为 Reentrancy Count |
| `ReentrantReadWriteLock` | Exclusive + Shared | 高 16 位表示 Read Lock 的持有数量（Shared），低 16 位表示 Write Lock 的 Reentrancy Count（Exclusive） |
| `Semaphore` | Shared | 表示可用 Permit 的数量。每次 `acquire()` 减少，`release()` 增加 |
| `CountDownLatch` | Shared | 表示需要等待的计数。每次 `countDown()` 减 1，到 0 时唤醒所有等待 Thread |

下面通过一个代码示例来直观感受 Exclusive Mode 和 Shared Mode 在使用上的区别：

```java
import java.util.concurrent.Semaphore;
import java.util.concurrent.locks.ReentrantLock;

public class ExclusiveVsSharedDemo {
    public static void main(String[] args) {
        // 独占模式：同一时刻只有 1 个线程能进入临界区
        ReentrantLock lock = new ReentrantLock();

        // 共享模式：同一时刻最多 3 个线程能进入临界区
        Semaphore semaphore = new Semaphore(3);

        // 独占模式示例
        Runnable exclusiveTask = () -> {
            lock.lock();
            try {
                System.out.println(Thread.currentThread().getName()
                        + " 获取到独占锁，正在执行...");
                Thread.sleep(500);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                lock.unlock();
            }
        };

        // 共享模式示例
        Runnable sharedTask = () -> {
            boolean acquired = false;
            try {
                semaphore.acquire();
                acquired = true;
                System.out.println(Thread.currentThread().getName()
                        + " 获取到许可证，正在执行...");
                Thread.sleep(500);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                if (acquired) {
                    semaphore.release();
                }
            }
        };

        System.out.println("=== 独占模式（ReentrantLock）===");
        for (int i = 0; i < 5; i++) {
            new Thread(exclusiveTask, "独占线程-" + i).start();
        }

        try { Thread.sleep(3000); } catch (InterruptedException e) { }

        System.out.println("\n=== 共享模式（Semaphore）===");
        for (int i = 0; i < 5; i++) {
            new Thread(sharedTask, "共享线程-" + i).start();
        }
    }
}
```

运行上面的代码可以观察到：Exclusive Mode 下同一时刻只有一个 Thread 执行，但默认的 Nonfair `ReentrantLock` 不保证 Thread 严格按启动或等待顺序获得 Lock；Shared Mode 下最多有 3 个 Thread 同时执行。

### AQS 资源获取源码分析（Exclusive Mode）

AQS 中以 Exclusive Mode 获取资源的入口 Method 是 `acquire()`，如下：

```JAVA
// AQS
public final void acquire(int arg) {
    if (!tryAcquire(arg) &&
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        selfInterrupt();
}
```

在 `acquire()` 中，Thread 会先尝试获取 Shared Resource；如果获取失败，会将 Thread Encapsulation 为 Node Node 加入到 AQS 的 Wait Queue 中；加入 Queue 之后，会让 Wait Queue 中的 Thread 尝试获取资源，并且会对 Thread 进行 Blocking Operation。分别对应以下三个 Method：

- `tryAcquire()`：Try Acquire（Template Method），`AQS` 不提供具体实现，由 Subclass 实现。
- `addWaiter()`：如果 Acquire Lock 失败，会将 Current Thread Encapsulation 为 Node Node 加入到 AQS 的 CLH Variant Queue 中等待 Acquire Lock。
- `acquireQueued()`：对 Thread 进行 Blocking，并调用 `tryAcquire()` Method 让 Queue 中的 Thread Try Acquire。

#### `tryAcquire()` 分析

AQS 中对应的 `tryAcquire()` Template Method 如下：

```JAVA
// AQS
protected boolean tryAcquire(int arg) {
    throw new UnsupportedOperationException();
}
```

`tryAcquire()` Method 是 AQS 提供的 Template Method，不提供默认实现。

因此，这里分析 `tryAcquire()` Method 时，以 `ReentrantLock` 的 Nonfair Lock（Exclusive Lock）为例进行分析，`ReentrantLock` 内部实现的 `tryAcquire()` 会调用到下边的 `nonfairTryAcquire()`：

```JAVA
// ReentrantLock
final boolean nonfairTryAcquire(int acquires) {
    final Thread current = Thread.currentThread();
    // 1、获取 AQS 中的 state 状态
    int c = getState();
    // 2、如果 state 为 0，证明锁没有被其他线程占用
    if (c == 0) {
        // 2.1、通过 CAS 对 state 进行更新
        if (compareAndSetState(0, acquires)) {
            // 2.2、如果 CAS 更新成功，就将锁的持有者设置为当前线程
            setExclusiveOwnerThread(current);
            return true;
        }
    }
    // 3、如果当前线程和锁的持有线程相同，说明发生了「锁的重入」
    else if (current == getExclusiveOwnerThread()) {
        int nextc = c + acquires;
        if (nextc < 0) // overflow
            throw new Error("Maximum lock count exceeded");
        // 3.1、将锁的重入次数加 1
        setState(nextc);
        return true;
    }
    // 4、如果锁被其他线程占用，就返回 false，表示获取锁失败
    return false;
}
```

在 `nonfairTryAcquire()` Method 内部，主要通过两个核心操作去完成资源的获取：

- 通过 `CAS` 更新 `state` Variable。`state == 0` 表示资源没有被占用。`state > 0` 表示资源被占用，此时 `state` 表示 Reentrancy Count。
- 通过 `setExclusiveOwnerThread()` 设置持有资源的 Thread。

如果 Thread 更新 `state` Variable 成功，就表明获取到了资源， 因此将持有资源的 Thread 设置为 Current Thread 即可。

#### `addWaiter()` 分析

在通过 `tryAcquire()` Method 尝试获取资源失败之后，会调用 `addWaiter()` Method 将 Current Thread Encapsulation 为 Node Node 加入 `AQS` 内部的 Queue 中。`addWaite()` 代码如下：

```JAVA
// AQS
private Node addWaiter(Node mode) {
    // 1、将当前线程封装为 Node 节点。
    Node node = new Node(Thread.currentThread(), mode);
    Node pred = tail;
    // 2、如果 pred ！= null，则证明 tail 节点已经被初始化，直接将 Node 节点加入队列即可。
    if (pred != null) {
        node.prev = pred;
        // 2.1、通过 CAS 控制并发安全。
        if (compareAndSetTail(pred, node)) {
            pred.next = node;
            return node;
        }
    }
    // 3、初始化队列，并将新创建的 Node 节点加入队列。
    enq(node);
    return node;
}
```

**Node Enqueue 的 Concurrency-safe：**

在 `addWaiter()` Method 中，需要执行 Node Node **Enqueue** 的操作。由于是在 Multithreading 环境下，因此需要通过 `CAS` 操作保证 Concurrency-safe。

通过 `CAS` 操作去更新 `tail` Pointer 指向新 Enqueue 的 Node Node，`CAS` 可以保证只有一个 Thread 会成功修改 `tail` Pointer，以此来保证 Node Node Enqueue 时的 Concurrency-safe。

**AQS 内部 Queue 的 Initialization：**

在执行 `addWaiter()` 时，如果发现 `pred == null`，即 `tail` Pointer 为 null，则证明 Queue 没有 Initialization，需要调用 `enq()` Method Initialization Queue，并将 `Node` Node 加入到 Initialization 后的 Queue 中，代码如下：

```JAVA
// AQS
private Node enq(final Node node) {
    for (;;) {
        Node t = tail;
        if (t == null) {
            // 1、通过 CAS 操作保证队列初始化的并发安全
            if (compareAndSetHead(new Node()))
                tail = head;
        } else {
            // 2、与 addWaiter() 方法中节点入队的操作相同
            node.prev = t;
            if (compareAndSetTail(t, node)) {
                t.next = node;
                return t;
            }
        }
    }
}
```

在 `enq()` Method 中 Initialization Queue，在 Initialization 过程中，也需要通过 `CAS` 来保证 Concurrency-safe。

Initialization Queue 总共包含两个步骤：Initialization `head` Node、`tail` 指向 `head` Node。

**Initialization 后的 Queue 如下图所示：**

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/clh-queue-structure-init.png)

#### `acquireQueued()` 分析

为了方便阅读，这里再贴一下 `AQS` 中 `acquire()` 获取资源的代码：

```JAVA
// AQS
public final void acquire(int arg) {
    if (!tryAcquire(arg) &&
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        selfInterrupt();
}
```

在 `acquire()` Method 中，通过 `addWaiter()` Method 将 `Node` Node 加入 Queue 之后，就会调用 `acquireQueued()` Method。代码如下：

```JAVA
// AQS：令队列中的节点尝试获取锁，并且对线程进行阻塞。
final boolean acquireQueued(final Node node, int arg) {
    boolean failed = true;
    try {
        boolean interrupted = false;
        for (;;) {
            // 1、尝试获取锁。
            final Node p = node.predecessor();
            if (p == head && tryAcquire(arg)) {
                setHead(node);
                p.next = null; // help GC
                failed = false;
                return interrupted;
            }
            // 2、判断线程是否可以阻塞，如果可以，则阻塞当前线程。
            if (shouldParkAfterFailedAcquire(p, node) &&
                parkAndCheckInterrupt())
                interrupted = true;
        }
    } finally {
        // 3、如果获取锁失败，就会取消获取锁，将节点状态更新为 CANCELLED。
        if (failed)
            cancelAcquire(node);
    }
}
```

在 `acquireQueued()` Method 中，主要做两件事情：

- **尝试获取资源：** Current Thread 加入 Queue 之后，如果发现前继 Node 是 `head` Node，说明 Current Thread 是 Queue 中第一个等待的 Node，于是调用 `tryAcquire()` 尝试获取资源。

- **Blocking Current Thread**：如果尝试获取资源失败，就需要 Blocking Current Thread，等待被唤醒之后获取资源。

**1、尝试获取资源**

在 `acquireQueued()` Method 中，尝试获取资源总共有 2 个步骤：

- `p == head`：表明当前 Node 的前继 Node 为 `head` Node。此时当前 Node 为 AQS Queue 中的第一个等待 Node。
- `tryAcquire(arg) == true`：表明 Current Thread 尝试获取资源成功。

在成功获取资源之后，就需要将 Current Thread 的 Node **从 Wait Queue 中移除**。移除操作为：将当前等待的 Thread Node 设置为 `head` Node（`head` Node 是 Dummy Node，并不参与排队获取资源）。

**2、Blocking Current Thread**

在 `AQS` 中，当前 Node 的唤醒需要依赖于上一个 Node。如果上一个 Node 取消 Acquire Lock，它的状态就会变为 `CANCELLED`，`CANCELLED` 状态的 Node 没有获取到 Lock，也就无法执行 Unlock 操作对当前 Node 进行唤醒。因此在 Blocking Current Thread 之前，需要跳过 `CANCELLED` 状态的 Node。

通过 `shouldParkAfterFailedAcquire()` Method 来判断 Current Thread Node 是否可以 Blocking，如下：

```JAVA
// AQS：判断当前线程节点是否可以阻塞。
private static boolean shouldParkAfterFailedAcquire(Node pred, Node node) {
    int ws = pred.waitStatus;
    // 1、前继节点状态正常，直接返回 true 即可。
    if (ws == Node.SIGNAL)
        return true;
    // 2、ws > 0 表示前继节点的状态异常，即为 CANCELLED 状态，需要跳过异常状态的节点。
    if (ws > 0) {
        do {
            node.prev = pred = pred.prev;
        } while (pred.waitStatus > 0);
        pred.next = node;
    } else {
        // 3、如果前继节点的状态不是 SIGNAL，也不是 CANCELLED，就将状态设置为 SIGNAL。
        compareAndSetWaitStatus(pred, ws, Node.SIGNAL);
    }
    return false;
}
```

`shouldParkAfterFailedAcquire()` Method 中的判断逻辑：

- 如果发现前继 Node 的状态是 `SIGNAL`，则可以 Blocking Current Thread。
- 如果发现前继 Node 的状态是 `CANCELLED`，则需要跳过 `CANCELLED` 状态的 Node。
- 如果发现前继 Node 的状态不是 `SIGNAL` 和 `CANCELLED`，表明前继 Node 的状态处于正常等待资源的状态，因此将前继 Node 的状态设置为 `SIGNAL`，表明该前继 Node 需要对后续 Node 进行唤醒。

当判断 Current Thread 可以 Blocking 之后，通过调用 `parkAndCheckInterrupt()` Method 来 Blocking Current Thread。内部使用了 `LockSupport` 来实现 Blocking。`LockSupoprt` 底层是基于 `Unsafe` Class 来 Blocking Thread，代码如下：

```JAVA
// AQS
private final boolean parkAndCheckInterrupt() {
    // 1、线程阻塞到这里
    LockSupport.park(this);
    // 2、线程被唤醒之后，返回线程中断状态
    return Thread.interrupted();
}
```

**为什么在 Thread 被唤醒之后，要返回 Thread 的 Interrupt Status 呢？**

在 `parkAndCheckInterrupt()` Method 中，当执行完 `LockSupport.park(this)`，Thread 会被 Blocking，代码如下：

```JAVA
// AQS
private final boolean parkAndCheckInterrupt() {
    LockSupport.park(this);
    // 线程被唤醒之后，需要返回线程中断状态
    return Thread.interrupted();
}
```

当 Thread 被唤醒之后，需要执行 `Thread.interrupted()` 来返回 Thread 的 Interrupt Status，这是为什么呢？

这个和 Thread 的 Interrupt 协作机制有关系，Thread 被唤醒之后，并不确定是被 Interrupt 唤醒，还是被 `LockSupport.unpark()` 唤醒，因此需要通过 Thread 的 Interrupt Status 来判断。

**在 `acquire()` Method 中，为什么需要调用 `selfInterrupt()`？**

`acquire()` Method 代码如下：

```JAVA
// AQS
public final void acquire(int arg) {
    if (!tryAcquire(arg) &&
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        selfInterrupt();
}
```

在 `acquire()` Method 中，当 `if` 语句的条件返回 `true` 后，就会调用 `selfInterrupt()`，该 Method 会 Interrupt Current Thread，为什么需要 Interrupt Current Thread 呢？

当 `if` 判断为 `true` 时，需要 `tryAcquire()` 返回 `false`，并且 `acquireQueued()` 返回 `true`。

其中 `acquireQueued()` Method 返回的是 Thread 被唤醒之后的 **Interrupt Status**，通过执行 `Thread.interrupted()` 来返回。该 Method 在返回 Interrupt Status 的同时，会清除 Thread 的 Interrupt Status。

因此如果 `if` 判断为 `true`，表明 Thread 的 Interrupt Status 为 `true`，但是调用 `Thread.interrupted()` 之后，Thread 的 Interrupt Status 被清除为 `false`，因此需要重新执行 `selfInterrupt()` 来重新设置 Thread 的 Interrupt Status。

### AQS 资源释放源码分析（Exclusive Mode）

AQS 中以 Exclusive Mode 释放资源的入口 Method 是 `release()`，代码如下：

```JAVA
// AQS
public final boolean release(int arg) {
    // 1、尝试释放锁
    if (tryRelease(arg)) {
        Node h = head;
        // 2、唤醒后继节点
        if (h != null && h.waitStatus != 0)
            unparkSuccessor(h);
        return true;
    }
    return false;
}
```

在 `release()` Method 中，主要做两件事：尝试 Release Lock 和唤醒 Successor。对应 Method 如下：

**1、尝试 Release Lock**

通过 `tryRelease()` Method 尝试 Release Lock，该 Method 为 Template Method，由自定义 Synchronizer 实现，因此这里仍然以 `ReentrantLock` 为例来讲解。

`ReentrantLock` 中实现的 `tryRelease()` Method 如下：

```JAVA
// ReentrantLock
protected final boolean tryRelease(int releases) {
    int c = getState() - releases;
    // 1、判断持有锁的线程是否为当前线程
    if (Thread.currentThread() != getExclusiveOwnerThread())
        throw new IllegalMonitorStateException();
    boolean free = false;
    // 2、如果 state 为 0，则表明当前线程已经没有重入次数。因此将 free 更新为 true，表明该线程会释放锁。
    if (c == 0) {
        free = true;
        // 3、更新持有资源的线程为 null
        setExclusiveOwnerThread(null);
    }
    // 4、更新 state 值
    setState(c);
    return free;
}
```

在 `tryRelease()` Method 中，会先计算 Release Lock 之后的 `state` 值，判断 `state` 值是否为 0。

- 如果 `state == 0`，表明该 Thread 没有 Reentrancy Count 了，更新 `free = true`，并修改持有资源的 Thread 为 null，表明该 Thread 完全释放这把 Lock。
- 如果 `state != 0`，表明该 Thread 还存在 Reentrancy Count，因此不更新 `free` 值，`free` 值为 `false` 表明该 Thread 没有完全释放这把 Lock。

之后更新 `state` 值，并返回 `free` 值，`free` 值表明 Thread 是否完全 Release Lock。

**2、唤醒 Successor**

如果 `tryRelease()` 返回 `true`，表明 Thread 已经没有 Reentrancy Count 了，Lock 已经被完全释放，因此需要唤醒 Successor。

在唤醒 Successor 之前，需要判断是否可以唤醒 Successor，判断条件为： `h != null && h.waitStatus != 0`。这里解释一下为什么要这样判断：

- `h == null`：表明 `head` Node 还没有被 Initialization，也就是 AQS 中的 Queue 没有被 Initialization，因此无法唤醒 Queue 中的 Thread Node。
- `h != null && h.waitStatus == 0`：表明 Head Node 刚刚 Initialization 完毕（Node 的 Initialization 状态为 0），Successor Thread 还没有成功 Enqueue，因此不需要对后续 Node 进行唤醒。（当 Successor Enqueue 之后，会将前继 Node 的状态修改为 `SIGNAL`，表明需要对 Successor 进行唤醒）
- `h != null && h.waitStatus != 0`：其中 `waitStatus` 有可能大于 0，也有可能小于 0。其中 `> 0` 表明 Node 已经取消等待获取资源，`< 0` 表明 Node 处于正常等待状态。

接下来进入 `unparkSuccessor()` Method 查看如何唤醒 Successor：

```JAVA
// AQS：这里的入参 node 为队列的头节点（虚拟头节点）
private void unparkSuccessor(Node node) {
    int ws = node.waitStatus;
    // 1、将头节点的状态进行清除，为后续的唤醒做准备。
    if (ws < 0)
        compareAndSetWaitStatus(node, ws, 0);

    Node s = node.next;
    // 2、如果后继节点异常，则需要从 tail 向前遍历，找到正常状态的节点进行唤醒。
    if (s == null || s.waitStatus > 0) {
        s = null;
        for (Node t = tail; t != null && t != node; t = t.prev)
            if (t.waitStatus <= 0)
                s = t;
    }
    if (s != null)
        // 3、唤醒后继节点
        LockSupport.unpark(s.thread);
}
```

在 `unparkSuccessor()` 中，如果 Head Node 的状态 `< 0`（在正常情况下，只要有 Successor，Head Node 的状态应该为 `SIGNAL`，即 -1），表示需要对 Successor 进行唤醒，因此这里提前清除 Head Node 的状态标识，将状态修改为 0，表示已经执行了对后续 Node 唤醒的操作。

如果 `s == null` 或者 `s.waitStatus > 0`，表明 Successor Exception，此时不能唤醒 Exception Node，而是要找到正常状态的 Node 进行唤醒。

因此需要从 `tail` Pointer 向前 Traversal，来找到第一个状态正常（`waitStatus <= 0`）的 Node 进行唤醒。

**为什么要从 `tail` Pointer 向前 Traversal，而不是从 `head` Pointer 向后 Traversal，寻找正常状态的 Node 呢？**

Traversal 的方向和 **Node 的 Enqueue 操作** 有关。 Enqueue Method 如下：

```JAVA
// AQS：节点入队方法
private Node addWaiter(Node mode) {
    Node node = new Node(Thread.currentThread(), mode);
    Node pred = tail;
    if (pred != null) {
        // 1、先修改 prev 指针。
        node.prev = pred;
        if (compareAndSetTail(pred, node)) {
            // 2、再修改 next 指针。
            pred.next = node;
            return node;
        }
    }
    enq(node);
    return node;
}
```

在 `addWaiter()` Method 中，`node` Node Enqueue 需要修改 `node.prev` 和 `pred.next` 两个 Pointer，但是这两个操作并不是 **Atomic Operation**，先修改了 `node.prev` Pointer，之后才修改 `pred.next` Pointer。

在极端情况下，可能会出现 `head` Node 的下一个 Node 状态为 `CANCELLED`，此时新 Enqueue 的 Node 仅更新了 `node.prev` Pointer，还未更新 `pred.next` Pointer，如下图：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-addWaiter.png)

这样如果从 `head` Pointer 向后 Traversal，无法找到新 Enqueue 的 Node，因此需要从 `tail` Pointer 向前 Traversal 找到新 Enqueue 的 Node。

### 图解 AQS 工作原理（Exclusive Mode）

至此，AQS 中以 Exclusive Mode 获取资源、释放资源的源码就讲完了。为了对 AQS 的工作原理、Node 状态变化有一个更加清晰的认识，接下来会通过画图的方式来了解整个 AQS 的工作原理。

由于 AQS 是底层同步工具，获取和释放资源的 Method 并没有提供具体实现，因此这里基于 `ReentrantLock` 来画图进行讲解。

假设总共有 3 个 Thread Try Acquire，Thread 分别为 `T1`、 `T2` 和 `T3`。

此时，假设 Thread `T1` 先获取到 Lock，Thread `T2` 排队等待 Acquire Lock。在 Thread `T2` 进入 Queue 之前，需要对 AQS 内部 Queue 进行 Initialization。`head` Node 在 Initialization 后状态为 `0`。AQS 内部 Initialization 后的 Queue 如下图：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-acquire-and-release-process.png)

此时，Thread `T2` Try Acquire。由于 Thread `T1` Hold Lock，因此 Thread `T2` 会进入 Queue 中等待 Acquire Lock。同时会将前继 Node（`head` Node）的状态由 `0` 更新为 `SIGNAL`，表示需要对 `head` Node 的 Successor 进行唤醒。此时，AQS 内部 Queue 如下图所示：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-acquire-and-release-process-2.png)

此时，Thread `T3` Try Acquire。由于 Thread `T1` Hold Lock，因此 Thread `T3` 会进入 Queue 中等待 Acquire Lock。同时会将前继 Node（Thread `T2` Node）的状态由 `0` 更新为 `SIGNAL`，表示 Thread `T2` Node 需要对 Successor 进行唤醒。此时，AQS 内部 Queue 如下图所示：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-acquire-and-release-process-3.png)

此时，假设 Thread `T1` Release Lock，会唤醒 Successor `T2`。 Thread `T2` 被唤醒后获取到 Lock，并且会从 Wait Queue 中退出。

这里 Thread `T2` Node 退出 Wait Queue 并不是直接从 Queue 移除，而是令 Thread `T2` Node 成为新的 `head` Node，以此来退出资源获取的等待。此时 AQS 内部 Queue 如下所示：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-acquire-and-release-process-4.png)

此时，假设 Thread `T2` Release Lock，会唤醒 Successor `T3`。 Thread `T3` 获取到 Lock 之后，同样也退出 Wait Queue，即将 Thread `T3` Node 变为 `head` Node 来退出资源获取的等待。此时 AQS 内部 Queue 如下所示：

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/aqs-acquire-and-release-process-5.png)

### AQS 资源获取源码分析（Shared Mode）

AQS 中以 Shared Mode 获取资源的入口 Method 是 `acquireShared()`，如下：

```JAVA
// AQS
public final void acquireShared(int arg) {
    if (tryAcquireShared(arg) < 0)
        doAcquireShared(arg);
}
```

在 `acquireShared()` Method 中，会先尝试获取 Shared Lock，如果获取失败，则将 Current Thread 加入到 Queue 中 Blocking，等待唤醒后尝试获取 Shared Lock，分别对应一下两个 Method：`tryAcquireShared()` 和 `doAcquireShared()`。

其中 `tryAcquireShared()` Method 是 AQS 提供的 Template Method，由 Synchronizer 来实现具体逻辑。因此这里以 `Semaphore` 为例，来分析 Shared Mode 下，如何获取资源。

#### `tryAcquireShared()` 分析

`Semaphore` 中实现了 Fair Lock 和 Nonfair Lock，接下来以 Nonfair Lock 为例来分析 `tryAcquireShared()` 源码。

`Semaphore` 中 Override 的 `tryAcquireShared()` Method 会调用下边的 `nonfairTryAcquireShared()` Method：

```JAVA
// Semaphore 重写 AQS 的模板方法
protected int tryAcquireShared(int acquires) {
    return nonfairTryAcquireShared(acquires);
}

// Semaphore
final int nonfairTryAcquireShared(int acquires) {
    for (;;) {
        // 1、获取可用资源数量。
        int available = getState();
        // 2、计算剩余资源数量。
        int remaining = available - acquires;
        // 3、如果剩余资源数量 < 0，则说明资源不足，直接返回；如果 CAS 更新 state 成功，则说明当前线程获取到了共享资源，直接返回。
        if (remaining < 0 ||
            compareAndSetState(available, remaining))
            return remaining;
    }
}
```

在 Shared Mode 下，AQS 中的 `state` 值表示 Shared Resource 的数量。

在 `nonfairTryAcquireShared()` Method 中，会在 Infinite Loop 中不断尝试获取资源，如果 「剩余资源数不足」 或者 「Current Thread 成功获取资源」，就退出 Infinite Loop。 Method 返回 **剩余的资源数量**，根据 Return Value 的不同，分为 3 种情况：

- **剩余资源数量 > 0**：表示成功获取资源，并且后续的 Thread 也可以成功获取资源。
- **剩余资源数量 = 0**：表示成功获取资源，但是后续的 Thread 无法成功获取资源。
- **剩余资源数量 < 0**：表示获取资源失败。

#### `doAcquireShared()` 分析

为了方便阅读，这里再贴一下获取资源的入口 Method `acquireShared()`：

```JAVA
// AQS
public final void acquireShared(int arg) {
    if (tryAcquireShared(arg) < 0)
        doAcquireShared(arg);
}
```

在 `acquireShared()` Method 中，会先通过 `tryAcquireShared()` 尝试获取资源。

如果发现 Method 的 Return Value `< 0`，即剩余的资源数小于 0，则表明 Current Thread 获取资源失败。因此会进入 `doAcquireShared()` Method，将 Current Thread 加入到 AQS Queue 进行等待。如下：

```JAVA
// AQS
private void doAcquireShared(int arg) {
    // 1、将当前线程加入到队列中等待。
    final Node node = addWaiter(Node.SHARED);
    boolean failed = true;
    try {
        boolean interrupted = false;
        for (;;) {
            final Node p = node.predecessor();
            if (p == head) {
                // 2、如果当前线程是等待队列的第一个节点，则尝试获取资源。
                int r = tryAcquireShared(arg);
                if (r >= 0) {
					// 3、将当前线程节点移出等待队列，并唤醒后续线程节点。
                    setHeadAndPropagate(node, r);
                    p.next = null; // help GC
                    if (interrupted)
                        selfInterrupt();
                    failed = false;
                    return;
                }
            }
            if (shouldParkAfterFailedAcquire(p, node) &&
                parkAndCheckInterrupt())
                interrupted = true;
        }
    } finally {
        // 3、如果获取资源失败，就会取消获取资源，将节点状态更新为 CANCELLED。
        if (failed)
            cancelAcquire(node);
    }
}
```

由于 Current Thread 已经尝试获取资源失败了，因此在 `doAcquireShared()` Method 中，需要将 Current Thread Encapsulation 为 Node Node，加入到 Queue 中进行等待。

以 **Shared Mode** 获取资源和 **Exclusive Mode** 获取资源最大的不同之处在于：Shared Mode 下，资源的数量可能会大于 1，即可以多个 Thread 同时持有资源。

因此在 Shared Mode 下，当 Thread 被唤醒之后，获取到了资源，如果发现还存在剩余资源，就会尝试唤醒后边的 Thread 去尝试获取资源。对应的 `setHeadAndPropagate()` Method 如下：

```JAVA
// AQS
private void setHeadAndPropagate(Node node, int propagate) {
    Node h = head;
    // 1、将当前线程节点移出等待队列。
    setHead(node);
	// 2、唤醒后续等待节点。
    if (propagate > 0 || h == null || h.waitStatus < 0 ||
        (h = head) == null || h.waitStatus < 0) {
        Node s = node.next;
        if (s == null || s.isShared())
            doReleaseShared();
    }
}
```

在 `setHeadAndPropagate()` Method 中，唤醒后续 Node 需要满足一定的条件，主要需要满足 2 个条件：

- `propagate > 0`：`propagate` 代表获取资源之后剩余的资源数量，如果 `> 0`，则可以唤醒后续 Thread 去获取资源。
- `h.waitStatus < 0`：这里的 `h` Node 是执行 `setHead()` 之前的 `head` Node。判断 `head.waitStatus` 时使用 `< 0`，主要为了确定 `head` Node 的状态为 `SIGNAL` 或 `PROPAGATE`。如果 `head` Node 为 `SIGNAL`，则可以唤醒后续 Node；如果 `head` Node 状态为 `PROPAGATE`，也可以唤醒后续 Node（这是为了解决 Concurrency 场景下出现的问题，后续会细讲）。

代码中关于 **唤醒后续等待 Node** 的 `if` 判断稍微复杂一些，这里来讲一下为什么这样写：

```JAVA
if (propagate > 0 || h == null || h.waitStatus < 0 ||
    (h = head) == null || h.waitStatus < 0)
```

- `h == null || h.waitStatus < 0` ： `h == null` 用于防止 NullPointerException。正常情况下 h 不会为 `null` ，因为执行到这里之前，当前 Node 已经加入到 Queue 中了，Queue 不可能还没有 Initialization。

  `h.waitStatus < 0` 主要判断 `head` Node 的状态是否为 `SIGNAL` 或者 `PROPAGATE`，直接使用 `< 0` 来判断比较方便。

- `(h = head) == null || h.waitStatus < 0` ：如果到这里说明之前判断的 `h.waitStatus < 0` ，说明存在 Concurrency。

  同时存在其他 Thread 在唤醒后续 Node，已经将 `head` Node 的值由 `SIGNAL` 修改为 `0` 了。因此，这里重新获取新的 `head` Node，这次获取的 `head` Node 为通过 `setHead()` 设置的 Current Thread Node，之后再次判断 `waitStatus` 状态。

如果 `if` 条件判断通过，就会走到 `doReleaseShared()` Method 唤醒后续等待 Node，如下：

```JAVA
private void doReleaseShared() {
    for (;;) {
        Node h = head;
        // 1、队列中至少需要一个等待的线程节点。
        if (h != null && h != tail) {
            int ws = h.waitStatus;
            // 2、如果 head 节点的状态为 SIGNAL，则可以唤醒后继节点。
            if (ws == Node.SIGNAL) {
                // 2.1 清除 head 节点的 SIGNAL 状态，更新为 0。表示已经唤醒该节点的后继节点了。
                if (!compareAndSetWaitStatus(h, Node.SIGNAL, 0))
                    continue;
                // 2.2 唤醒后继节点
                unparkSuccessor(h);
            }
            // 3、如果 head 节点的状态为 0，则更新为 PROPAGATE。这是为了解决并发场景下存在的问题，接下来会细讲。
            else if (ws == 0 &&
                     !compareAndSetWaitStatus(h, 0, Node.PROPAGATE))
                continue;
        }
        if (h == head)
            break;
    }
}
```

在 `doReleaseShared()` Method 中，会判断 `head` Node 的 `waitStatus` 状态来决定接下来的操作，有两种情况：

- `head` Node 的状态为 `SIGNAL`：表明 `head` Node 存在 Successor 需要唤醒，因此通过 `CAS` 操作将 `head` Node 的 `SIGNAL` 状态更新为 `0`。通过清除 `SIGNAL` 状态来表示已经对 `head` Node 的 Successor 进行唤醒操作了。
- `head` Node 的状态为 `0`：表明存在 Concurrency 情况，需要将 `0` 修改为 `PROPAGATE` 来保证在 Concurrency 场景下可以正常唤醒 Thread。

#### 为什么需要 `PROPAGATE` 状态？

在 `doReleaseShared()` 释放资源时，第 3 步不太容易理解，即如果发现 `head` Node 的状态是 `0`，就将 `head` Node 的状态由 `0` 更新为 `PROPAGATE`。

AQS 中，Node Node 的 `PROPAGATE` 就是为了处理 Concurrency 场景下可能出现的无法唤醒 Thread Node 的问题。`PROPAGATE` 只在 `doReleaseShared()` Method 中用到一次。

**接下来通过案例分析，为什么需要 `PROPAGATE` 状态？**

在 Shared Mode 下，Thread 获取和释放资源的 Method Invocation 链如下：

- Thread 获取资源的 Method Invocation 链为： `acquireShared() -> tryAcquireShared() -> 线程阻塞等待唤醒 -> tryAcquireShared() -> setHeadAndPropagate() -> if (剩余资源数 > 0) || (head.waitStatus < 0) 则唤醒后续节点` 。

- Thread 释放资源的 Method Invocation 链为： `releaseShared() -> tryReleaseShared() -> doReleaseShared()`。

**如果在释放资源时，没有将 `head` Node 的状态由 `0` 改为 `PROPAGATE`：**

假设总共有 4 个 Thread 尝试以 Shared Mode 获取资源，总共有 2 个资源。初始 `T3` 和 `T4` Thread 获取到了资源，`T1` 和 `T2` Thread 没有获取到，因此在 Queue 中排队等候。

- 在时刻 1 时，Thread `T1` 和 `T2` 在 Wait Queue 中，`T3` 和 `T4` 持有资源。此时 Wait Queue 内 Node 以及对应状态为（括号内为 Node 的 `waitStatus` 状态）：

  `head(-1) -> T1(-1) -> T2(0)`。

- 在时刻 2 时，Thread `T3` 释放资源，通过 `doReleaseShared()` Method 将 `head` Node 的状态由 `SIGNAL` 更新为 `0`，并唤醒 Thread `T1`，之后 Thread `T3` 退出。

  Thread `T1` 被唤醒之后，通过 `tryAcquireShared()` 获取到资源，但是此时还未来得及执行 `setHeadAndPropagate()` 将自己设置为 `head` Node。此时 Wait Queue 内 Node 状态为：

  `head(0) -> T1(-1) -> T2(0)`。

- 在时刻 3 时，Thread `T4` 释放资源，由于此时 `head` Node 的状态为 `0`，如果 `doReleaseShared()` 中 `ws == 0` 时什么都不做（即没有 `PROPAGATE` 状态），那么 `T4` 无法唤醒 `head` 的 Successor，之后 Thread `T4` 退出。

- 在时刻 4 时，Thread `T1` 继续执行 `setHeadAndPropagate()` Method。先保存旧 `head`（`waitStatus == 0`），再执行 `setHead(T1)` 将自己设置为 `head` Node。

  此时 `propagate == 0`，旧 `head.waitStatus == 0`，前两个条件不满足。但由于 `setHead()` 不会重置 `waitStatus`，新 `head`（即原来的 `T1` Node）的 `waitStatus` 仍然是 `-1`（SIGNAL），所以第二次判断 `(h = head).waitStatus < 0` 仍然成立，会调用 `doReleaseShared()` 唤醒 `T2`。

  在这个时序下，二次 head 判断确实能兜住。那 `PROPAGATE` 解决的是什么问题呢？

- 在时刻 5（更极端的时序），考虑这样的交错：Thread `T1` 执行完 `setHead(T1)` 之后、判断新 `head.waitStatus` **之前**，Thread `T4` 的 `doReleaseShared()` 恰好执行了 `unparkSuccessor()` 唤醒了 `T2`，`T2` 快速获取资源并执行 `setHead(T2)` 将自己设为新的 `head`。由于 `T2` 原来是 Queue 尾部 Node，其 `waitStatus` 为 `0`。当 `T1` 恢复执行读取新 `head` 时，读到的是 `T2` Node（`waitStatus == 0`），此时二次判断也无法通过了。

  在这种极端 Concurrency 时序下，`propagate == 0`、旧 `head.waitStatus == 0`、新 `head.waitStatus == 0`，三个条件全部不满足，`T1` 不会调用 `doReleaseShared()`。如果此时 Queue 中还有后续等待 Node，就会导致唤醒信号丢失。

对应时刻表如下：

| 时刻 | Thread T1 | Thread T2 | Thread T3 | Thread T4 | Wait Queue |
| ------ | --------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------- | ------------------------------------------------------------- | --------------------------------- |
| 时刻 1 | Wait Queue | Wait Queue | 持有资源 | 持有资源 | `head(-1) -> T1(-1) -> T2(0)` |
| 时刻 2 | （执行）被唤醒后，获取资源，但未来得及将自己设置为 `head` Node | Wait Queue | （执行）释放资源 | 持有资源 | `head(0) -> T1(-1) -> T2(0)` |
| 时刻 3 | | Wait Queue | 已退出 | （执行）释放资源。但 `head` Node 状态为 `0` ，无法唤醒 Successor | `head(0) -> T1(-1) -> T2(0)` |
| 时刻 4 | （执行）`setHead(T1)` 完成，尚未判断新 `head.waitStatus` | Wait Queue | 已退出 | 已退出 | `head(-1，线程 T1 节点) -> T2(0)` |
| 时刻 5 | | （执行）被 T4 唤醒，获取资源，执行 `setHead(T2)` 成为新的 `head` | 已退出 | （执行）`doReleaseShared()` 唤醒 T2 | `head(0，线程 T2 节点)` |
| 时刻 6 | （执行）读取新 `head` 为 T2 Node，`waitStatus == 0`，二次判断失败，不唤醒后续 Node | 已获取资源 | 已退出 | 已退出 | `head(0，线程 T2 节点)` |

**如果在 Thread 释放资源时，将 `head` Node 的状态由 `0` 改为 `PROPAGATE`，则可以解决上边出现的 Concurrency 问题，如下：**

`PROPAGATE` 的关键在于：它修改的是**旧 `head`** 的状态，而旧 `head` 的 Reference 在 `setHeadAndPropagate()` Method 开头就已经保存到了 Local Variable `h` 中，不会被后续的 Concurrency 修改影响。

- 在时刻 1~2 时，与上述场景相同：

  时刻 1：`head(-1) -> T1(-1) -> T2(0)`。

  时刻 2：`T3` 释放资源，`head` 状态变为 `0` 并唤醒 `T1`。

- 在时刻 3 时，Thread `T4` 释放资源，由于此时 `head` Node 的状态为 `0`，`doReleaseShared()` 会将 `head` Node 的状态由 `0` 更新为 `PROPAGATE(-3)`，之后 Thread `T4` 退出。此时 Wait Queue 内 Node 状态为：

  `head(PROPAGATE) -> T1(-1) -> T2(0)`。

- 在时刻 4 时，Thread `T1` 继续执行 `setHeadAndPropagate()` Method。先保存旧 `head` 到 Local Variable `h`，此时 `h.waitStatus == PROPAGATE(-3)`。再执行 `setHead(T1)` 将自己设置为 `head` Node。

- 在时刻 5 时，即使发生了与之前相同的极端交错（`T4` 唤醒了 `T2`，`T2` 成为新 `head`），`T1` 在判断时：

  - `propagate > 0` → `0 > 0` → false
  - `h == null` → false
  - `h.waitStatus < 0` → `PROPAGATE(-3) < 0` → **true**！

  由于旧 `head` 的 Reference `h` 在 Method 开头就已保存，不受后续 `setHead()` 和 Concurrency 操作的影响，所以 `PROPAGATE` 状态确保了 `h.waitStatus < 0` 一定能通过。因此 Thread `T1` 会在 `setHeadAndPropagate()` Method 中调用 `doReleaseShared()` 唤醒后续 Node。

有了 `PROPAGATE` 状态，就可以避免极端 Concurrency 时序下唤醒信号丢失的问题。对应时刻表如下：

| 时刻 | Thread T1 | Thread T2 | Thread T3 | Thread T4 | Wait Queue |
| ------ | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------- | ------------------------------------------------------------------- | ------------------------------------ |
| 时刻 1 | Wait Queue | Wait Queue | 持有资源 | 持有资源 | `head(-1) -> T1(-1) -> T2(0)` |
| 时刻 2 | （执行）被唤醒后，获取资源，但未来得及将自己设置为 `head` Node | Wait Queue | （执行）释放资源 | 持有资源 | `head(0) -> T1(-1) -> T2(0)` |
| 时刻 3 | 未继续向下执行 | Wait Queue | 已退出 | （执行）释放资源。此时会将 `head` Node 状态由 `0` 更新为 `PROPAGATE` | `head(PROPAGATE) -> T1(-1) -> T2(0)` |
| 时刻 4 | （执行）保存旧 `head`（`waitStatus == PROPAGATE`），执行 `setHead(T1)` | Wait Queue | 已退出 | 已退出 | `head(-1，线程 T1 节点) -> T2(0)` |
| 时刻 5 | （执行）判断旧 `h.waitStatus < 0`（`PROPAGATE(-3) < 0`）成立，调用 `doReleaseShared()` 唤醒后续 Node | Wait Queue | 已退出 | 已退出 | `head(0，线程 T1 节点) -> T2(0)` |
| 时刻 6 | 已退出 | （执行）Thread `T2` 被唤醒后，获取到资源，并将自己设置为 `head` Node | 已退出 | 已退出 | `head(0，线程 T2 节点)` |

简单总结：`PROPAGATE` 状态和 `setHeadAndPropagate()` 中的二次 head 判断是 JDK 7 中同一个 bug fix（[JDK-6801020](https://bugs.openjdk.org/browse/JDK-6801020)）的**双重保险**。`PROPAGATE` 通过修改旧 `head` 的状态来提供更可靠的保障，因为旧 `head` 的 Reference 在 Method 开头就已保存到 Local Variable，不会被 Concurrency 的 `setHead()` 操作替换。

### AQS 资源释放源码分析（Shared Mode）

AQS 中以 Shared Mode 释放资源的入口 Method 是 `releaseShared()`，代码如下：

```JAVA
// AQS
public final boolean releaseShared(int arg) {
    if (tryReleaseShared(arg)) {
        doReleaseShared();
        return true;
    }
    return false;
}
```

其中 `tryReleaseShared()` Method 是 AQS 提供的 Template Method，这里同样以 `Semaphore` 来讲解，如下：

```JAVA
// Semaphore
protected final boolean tryReleaseShared(int releases) {
    for (;;) {
        int current = getState();
        int next = current + releases;
        if (next < current) // overflow
            throw new Error("Maximum permit count exceeded");
        if (compareAndSetState(current, next))
            return true;
    }
}
```

在 `Semaphore` 实现的 `tryReleaseShared()` Method 中，会在 Infinite Loop 内不断尝试释放资源，即通过 `CAS` 操作来更新 `state` 值。

如果更新成功，则证明资源释放成功，会进入到 `doReleaseShared()` Method。

`doReleaseShared()` Method 在前文获取资源（Shared Mode）的部分已进行了详细的源码分析，此处不再重复。

### Condition Condition Queue 的工作机制

前面在 `waitStatus` 状态表格中提到过 `CONDITION`（值为 -2）状态，表示 Node 在 Condition Condition Queue 中等待。这里系统讲解 Condition Condition Queue 的工作机制。

#### 什么是 Condition？

`Condition` 是 `java.util.concurrent.locks` Package 中定义的 Interface，它提供了类似于 `Object.wait()` / `Object.notify()` 的 Thread 等待/通知机制，但功能更加强大和灵活。`Condition` 必须与 `Lock` 配合使用，就像 `wait/notify` 必须与 `synchronized` 配合使用一样。

与 `Object` 的 `wait/notify` 相比，`Condition` 的主要优势在于：

- **支持多个 Wait Queue**：一个 `Lock` 可以创建多个 `Condition` Instance，不同的 Thread 可以在不同的条件上等待，实现更精细的 Thread 协作。而 `synchronized` 只有一个 Wait Queue。
- **支持不响应 Interrupt 的等待**：`Condition` 提供了 `awaitUninterruptibly()` Method。
- **支持 Timeout 等待**：`Condition` 提供了 `awaitNanos(long)` 和 `await(long, TimeUnit)` Method，可以设定等待的截止时间。

#### AQS 中的两种 Queue

在 AQS 内部实际上维护了 **两种 Queue**：

1. **Sync Queue（CLH Variant Queue）**：就是前面详细分析过的双向 Queue，用于存放获取资源失败而等待的 Thread Node。
2. **Condition Queue**：是一个 Singly Linked List，用于存放调用了 `Condition.await()` Method 而等待的 Thread Node。每个 `Condition` Instance 维护一个独立的 Condition Queue。

Condition Queue 中的 Node 使用 `Node` 的 `nextWaiter` Pointer 来链接下一个 Node，形成 Singly Linked List。 Condition Queue 的 Head Node 为 `firstWaiter`，Tail Node 为 `lastWaiter`。

#### Condition 的核心工作流程

AQS 的 Inner Class `ConditionObject` 实现了 `Condition` Interface，其核心 Method 为 `await()` 和 `signal()`。

**`await()` Method 的工作流程：**

1. 将 Current Thread Encapsulation 为 `Node` Node（`waitStatus` 设置为 `CONDITION`），加入到 Condition Queue 的尾部。
2. 完全释放 Current Thread 持有的 Lock（即将 `state` 值置为 0），并保存释放前的 `state` 值。
3. Blocking Current Thread，等待被 `signal()` 唤醒或被 Interrupt。
4. 被唤醒后，重新通过 `acquireQueued()` 进入 Sync Queue 竞争 Lock，并恢复之前保存的 `state` 值（Reentrancy Count）。

**`signal()` Method 的工作流程：**

1. 检查调用 `signal()` 的 Thread 是否 Hold Lock（不持有则抛出 `IllegalMonitorStateException`）。
2. 将 Condition Queue 中第一个等待的 Node 从 Condition Queue 移除。
3. 将该 Node 的 `waitStatus` 从 `CONDITION` 修改为 `0`，并通过 `enq()` Method 将其加入到 Sync Queue 的尾部。
4. 如果 Sync Queue 中 Predecessor 的状态 Exception（`CANCELLED`）或者 CAS 设置 Predecessor 状态为 `SIGNAL` 失败，则直接唤醒该 Thread。

`signalAll()` Method 与 `signal()` 类似，区别在于它会将 Condition Queue 中的 **所有** Node 都转移到 Sync Queue 中。

下面的代码示例展示了 `Condition` 的典型用法——实现一个简单的有界 Blocking Queue：

```java
import java.util.LinkedList;
import java.util.Queue;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

public class SimpleBlockingQueue<T> {
    private final Queue<T> queue = new LinkedList<>();
    private final int capacity;
    private final ReentrantLock lock = new ReentrantLock();
    // 两个不同的条件队列：分别用于"队列不满"和"队列不空"
    private final Condition notFull = lock.newCondition();
    private final Condition notEmpty = lock.newCondition();

    public SimpleBlockingQueue(int capacity) {
        this.capacity = capacity;
    }

    /**
     * 向队列中添加元素，如果队列已满则等待。
     */
    public void put(T item) throws InterruptedException {
        lock.lock();
        try {
            // 队列满时，在 notFull 条件上等待
            while (queue.size() == capacity) {
                notFull.await();
            }
            queue.offer(item);
            // 添加元素后，通知在 notEmpty 条件上等待的消费者线程
            notEmpty.signal();
        } finally {
            lock.unlock();
        }
    }

    /**
     * 从队列中取出元素，如果队列为空则等待。
     */
    public T take() throws InterruptedException {
        lock.lock();
        try {
            // 队列空时，在 notEmpty 条件上等待
            while (queue.isEmpty()) {
                notEmpty.await();
            }
            T item = queue.poll();
            // 取出元素后，通知在 notFull 条件上等待的生产者线程
            notFull.signal();
            return item;
        } finally {
            lock.unlock();
        }
    }

    public static void main(String[] args) {
        SimpleBlockingQueue<Integer> blockingQueue = new SimpleBlockingQueue<>(5);

        // 生产者线程
        Thread producer = new Thread(() -> {
            try {
                for (int i = 0; i < 10; i++) {
                    blockingQueue.put(i);
                    System.out.println("生产: " + i);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "Producer");

        // 消费者线程
        Thread consumer = new Thread(() -> {
            try {
                for (int i = 0; i < 10; i++) {
                    int item = blockingQueue.take();
                    System.out.println("消费: " + item);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "Consumer");

        producer.start();
        consumer.start();
    }
}
```

在上面的例子中，`notFull` 和 `notEmpty` 是两个独立的 `Condition` Instance，分别维护各自的 Condition Queue。 Producer 在 Queue 满时在 `notFull` 上等待，Consumer 在 Queue 空时在 `notEmpty` 上等待。这种分离等待条件的设计，避免了不必要的 Thread 唤醒，比 `synchronized` + `wait/notifyAll` 更加高效。

#### `await()` 核心源码分析

```java
// AQS 内部类 ConditionObject
public final void await() throws InterruptedException {
    if (Thread.interrupted())
        throw new InterruptedException();
    // 1、将当前线程封装为 Node 节点，加入条件队列
    Node node = addConditionWaiter();
    // 2、完全释放锁，并保存释放前的 state 值
    int savedState = fullyRelease(node);
    int interruptMode = 0;
    // 3、如果节点不在同步队列中，则阻塞当前线程
    while (!isOnSyncQueue(node)) {
        LockSupport.park(this);
        if ((interruptMode = checkInterruptWhileWaiting(node)) != 0)
            break;
    }
    // 4、被唤醒后，重新进入同步队列竞争锁
    if (acquireQueued(node, savedState) && interruptMode != THROW_IE)
        interruptMode = REINTERRUPT;
    if (node.nextWaiter != null)
        unlinkCancelledWaiters();
    if (interruptMode != 0)
        reportInterruptAfterWait(interruptMode);
}
```

`await()` Method 中有两个关键操作：

- `fullyRelease(node)`：完全 Release Lock（而不是只释放一次），这样即使 Thread Reentrant 了多次 Lock，也能在等待期间让其他 Thread 获取到 Lock。被唤醒后会通过 `acquireQueued(node, savedState)` 恢复之前的 Reentrancy Count。
- `isOnSyncQueue(node)`：判断 Node 是否已经被转移到 Sync Queue。当其他 Thread 调用 `signal()` 时，Node 会从 Condition Queue 转移到 Sync Queue，此时 `isOnSyncQueue()` 返回 `true`，Thread 退出 `while` Loop，开始竞争 Lock。

### Fair Lock 与 Nonfair Lock 的 Performance 差异分析

前面的源码分析中，以 `ReentrantLock` 的 Nonfair Lock 为例讲解了 `tryAcquire()` 的实现。实际上 `ReentrantLock` 同时支持 Fair Lock 和 Nonfair Lock 两种模式。这里深入分析二者的实现差异及其对 Performance 的影响。

#### 源码层面的差异

`ReentrantLock` 默认使用 Nonfair Lock，通过构造 Parameter 可以切换为 Fair Lock：

```java
// 非公平锁（默认）
ReentrantLock unfairLock = new ReentrantLock();
// 公平锁
ReentrantLock fairLock = new ReentrantLock(true);
```

二者的核心差异在于 `tryAcquire()` Method 的实现。 Nonfair Lock 的 `nonfairTryAcquire()` 前面已经分析过，下面看 Fair Lock 的实现：

```java
// ReentrantLock.FairSync
protected final boolean tryAcquire(int acquires) {
    final Thread current = Thread.currentThread();
    int c = getState();
    if (c == 0) {
        // 关键差异：先调用 hasQueuedPredecessors() 判断同步队列中是否有等待更久的线程
        if (!hasQueuedPredecessors() &&
            compareAndSetState(0, acquires)) {
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
    return false;
}
```

**唯一的区别** 就是 Fair Lock 在 CAS 修改 `state` 之前多了一个 `hasQueuedPredecessors()` 判断：

```java
// AQS
public final boolean hasQueuedPredecessors() {
    Node t = tail;
    Node h = head;
    Node s;
    return h != t &&
        ((s = h.next) == null || s.thread != Thread.currentThread());
}
```

这个 Method 用于判断 Current Thread 之前是否有其他 Thread 在排队。如果有，则 Current Thread 不能直接 Acquire Lock，必须排队等待，从而保证了 **FIFO** 的 Fairness。

而 Nonfair Lock 没有这个判断，当 Lock 刚好释放时，新来的 Thread 可以直接通过 CAS 抢到 Lock，即使 Sync Queue 中已经有其他 Thread 在等待。

#### Performance 差异对比

| 对比维度 | Nonfair Lock（默认） | Fair Lock |
| -------------- | ------------------------------------------------------------------------------ | -------------------------------------------------- |
| **Throughput** | 更高。新 Thread 有机会直接 Acquire Lock，减少了 Thread Context Switch | 较低。所有 Thread 都必须排队，增加了 Context Switch 的 Overhead |
| **Thread Starvation** | 可能发生。极端情况下某些 Thread 长时间无法 Acquire Lock | 通常更不容易发生，但 Fair Lock 不保证 Operating System 的 Thread Scheduling |
| **Context Switch** | 较少。 Hold Lock 的 Thread Release Lock 后，新到达的 Thread 可能直接 Acquire Lock，不需要唤醒 Queue 中的 Thread | 较多。每次 Release Lock 都需要唤醒 Queue 中的下一个 Thread |
| **适用场景** | 大多数场景（对响应时间和 Throughput 要求较高） | 对 Fairness 有严格要求的场景（如资源分配、Task 调度） |

**为什么 Nonfair Lock Performance 通常更好？**

关键原因在于 **减少了 Thread Context Switch 的次数**。当 Hold Lock 的 Thread A Release Lock 后：

- **Nonfair Lock**：此时如果恰好有 Thread B 正在 Try Acquire（还没有进入 Sync Queue），Thread B 可以直接通过 CAS 获取到 Lock 并立即执行，省去了唤醒 Queue 中 Thread 的 Overhead。而 Queue 中等待的 Thread 被唤醒后发现 Lock 被占用，会重新 Blocking，虽然看起来“浪费”了一次唤醒，但总体上减少了 Thread 切换次数。
- **Fair Lock**：Thread B 必须排到 Queue 尾部，然后唤醒 Queue 头部的 Thread。从 Thread 被唤醒到真正开始执行之间，存在一段 **调度延迟**（Thread State 从 Blocking 切换到运行），在这段延迟期间 Lock 处于空闲状态，降低了 Lock 的利用率。

Doug Lea 在 `ReentrantLock` 的文档中指出：使用 Fair Lock 的程序在 Multithreading 环境下的总体 Throughput 通常低于使用 Nonfair Lock 的程序（即更慢），因此 `ReentrantLock` 默认使用 Nonfair 模式。但在需要保证请求处理顺序或避免 Thread Starvation 的场景中（如 Connection Pool 分配），Fair Lock 是更好的选择。

下面通过代码示例来演示 Fair Lock 与 Nonfair Lock 在行为上的差异：

```java
import java.util.concurrent.locks.ReentrantLock;

public class FairVsUnfairLockDemo {
    // 分别测试公平锁和非公平锁
    private static void testLock(ReentrantLock lock, String lockType) {
        System.out.println("=== " + lockType + " ===");
        Runnable task = () -> {
            for (int i = 0; i < 2; i++) {
                lock.lock();
                try {
                    System.out.println(Thread.currentThread().getName() + " 获取到锁");
                } finally {
                    lock.unlock();
                }
            }
        };

        Thread[] threads = new Thread[5];
        for (int i = 0; i < 5; i++) {
            threads[i] = new Thread(task, lockType + "-线程-" + i);
        }
        for (Thread t : threads) {
            t.start();
        }
        for (Thread t : threads) {
            try { t.join(); } catch (InterruptedException e) { }
        }
        System.out.println();
    }

    public static void main(String[] args) {
        // 非公平锁：同一个线程可能连续多次获取到锁
        testLock(new ReentrantLock(false), "非公平锁");

        // 公平锁：存在竞争时倾向于让等待更久的线程先获取锁
        testLock(new ReentrantLock(true), "公平锁");
    }
}
```

运行上面的代码通常可以观察到：Nonfair Lock 模式下，同一个 Thread 更容易连续多次获取到 Lock（因为它 Release Lock 后立即又去竞争，有机会在 Queue 中的 Thread 被唤醒之前抢到 Lock）；Fair Lock 在存在等待者时倾向于按 Queue 顺序分配 Lock。不过，Fairness 不等于 Operating System 调度 Fair，如果其他 Thread 尚未运行到等待点，同一个 Thread 仍可能连续获得 Lock。

## 常见同步 Utility Class

### Semaphore（信号量）

#### 介绍

`synchronized` 和 `ReentrantLock` 都是一次只允许一个 Thread 访问某个资源，而 `Semaphore`（信号量）可以用来控制同时访问特定资源的 Thread Count。

`Semaphore` 的使用简单，我们这里假设有 `N(N>5)` 个 Thread 来获取 `Semaphore` 中的 Shared Resource，下面的代码表示同一时刻 N 个 Thread 中只有 5 个 Thread 能获取到 Shared Resource，其他 Thread 都会 Blocking，只有获取到 Shared Resource 的 Thread 才能执行。等到有 Thread 释放了 Shared Resource，其他 Blocking 的 Thread 才能获取到。

```java
// 初始共享资源数量
final Semaphore semaphore = new Semaphore(5);
// 获取1个许可
semaphore.acquire();
// 释放1个许可
semaphore.release();
```

当初始的资源个数为 1 的时候，`Semaphore` 退化为 Exclusive Lock。

`Semaphore` 有两种模式：。

- **Fair 模式：** 存在竞争时，Blocking 式 `acquire` Method 会在内部排队点按 FIFO 选择 Thread；这不等同于严格按照 Method Invocation 的墙上时间排序。另外，无参的 `tryAcquire()` 不遵守 Fair 设置，仍可能插队成功；
- **Nonfair 模式：** 抢占式的。

`Semaphore` 对应的两个 Constructor 如下：

```java
public Semaphore(int permits) {
    sync = new NonfairSync(permits);
}

public Semaphore(int permits, boolean fair) {
    sync = fair ? new FairSync(permits) : new NonfairSync(permits);
}
```

**这两个 Constructor，都必须提供许可的数量，第二个 Constructor 可以指定是 Fair 模式还是 Nonfair 模式，默认 Nonfair 模式。**

`Semaphore` 通常用于那些资源有明确访问数量限制的场景比如 Rate Limiting（仅限于单机模式，实际项目中推荐使用 Redis +Lua 来做 Rate Limiting）。

#### 原理

`Semaphore` 是 Shared Lock 的一种实现，它默认构造 AQS 的 `state` 值为 `permits`，你可以将 `permits` 的值理解为 Permit 的数量，只有拿到 Permit 的 Thread 才能执行。

以无参 `acquire` Method 为例，调用 `semaphore.acquire()`，Thread 尝试获取 Permit，如果 `state > 0` 的话，则表示可以获取成功，如果 `state <= 0` 的话，则表示 Permit 数量不足，获取失败。

如果可以获取成功的话(`state > 0` )，会尝试使用 CAS 操作去修改 `state` 的值 `state=state-1`。如果获取失败则会创建一个 Node Node 加入 Wait Queue，挂起 Current Thread。

```java
// 获取1个许可证
public void acquire() throws InterruptedException {
    sync.acquireSharedInterruptibly(1);
}

// 获取一个或者多个许可证
public void acquire(int permits) throws InterruptedException {
    if (permits < 0) throw new IllegalArgumentException();
    sync.acquireSharedInterruptibly(permits);
}
```

`acquireSharedInterruptibly` Method 是 `AbstractQueuedSynchronizer` 中的默认实现。

```java
// 共享模式下获取许可证，获取成功则返回，失败则加入等待队列，挂起线程
public final void acquireSharedInterruptibly(int arg)
    throws InterruptedException {
    if (Thread.interrupted())
      throw new InterruptedException();
        // 尝试获取许可证，arg为获取许可证个数，当获取失败时,则创建一个节点加入等待队列，挂起当前线程。
    if (tryAcquireShared(arg) < 0)
      doAcquireSharedInterruptibly(arg);
}
```

这里再以 Nonfair 模式（`NonfairSync`）的为例，看看 `tryAcquireShared` Method 的实现。

```java
// 共享模式下尝试获取资源(在Semaphore中的资源即许可证):
protected int tryAcquireShared(int acquires) {
    return nonfairTryAcquireShared(acquires);
}

// 非公平的共享模式获取许可证
final int nonfairTryAcquireShared(int acquires) {
    for (;;) {
        // 当前可用许可证数量
        int available = getState();
        /*
         * 尝试获取许可证，当前可用许可证数量小于等于0时，返回负值，表示获取失败，
         * 当前可用许可证大于0时才可能获取成功，CAS失败了会循环重新获取最新的值尝试获取
         */
        int remaining = available - acquires;
        if (remaining < 0 ||
            compareAndSetState(available, remaining))
            return remaining;
    }
}
```

以无参 `release` Method 为例，调用 `semaphore.release();`，Thread 尝试释放 Permit，并使用 CAS 操作去修改 `state` 的值 `state=state+1`。释放 Permit 成功之后，同时会唤醒 Wait Queue 中的一个 Thread。被唤醒的 Thread 会重新尝试去修改 `state` 的值 `state=state-1`，如果 `state > 0` 则获取令牌成功，否则重新进入 Wait Queue，挂起 Thread。

```java
// 释放一个许可证
public void release() {
    sync.releaseShared(1);
}

// 释放一个或者多个许可证
public void release(int permits) {
    if (permits < 0) throw new IllegalArgumentException();
    sync.releaseShared(permits);
}
```

`releaseShared` Method 是 `AbstractQueuedSynchronizer` 中的默认实现。

```java
// 释放共享锁
// 如果 tryReleaseShared 返回 true，就唤醒等待队列中的一个或多个线程。
public final boolean releaseShared(int arg) {
    //释放共享锁
    if (tryReleaseShared(arg)) {
      //释放当前节点的后置等待节点
      doReleaseShared();
      return true;
    }
    return false;
}
```

`tryReleaseShared` Method 是 `Semaphore` 的 Inner Class `Sync` Override 的一个 Method， `AbstractQueuedSynchronizer` 中的默认实现仅仅抛出 `UnsupportedOperationException` Exception。

```java
// 内部类 Sync 中重写的一个方法
// 尝试释放资源
protected final boolean tryReleaseShared(int releases) {
    for (;;) {
        int current = getState();
        // 可用许可证+1
        int next = current + releases;
        if (next < current) // overflow
            throw new Error("Maximum permit count exceeded");
         // CAS修改state的值
        if (compareAndSetState(current, next))
            return true;
    }
}
```

可以看到，上面提到的几个 Method 底层基本都是通过 Synchronizer `sync` 实现的。`Sync` 是 `CountDownLatch` 的 Inner Class , Inherit 了 `AbstractQueuedSynchronizer`，Override 了其中的某些 Method。并且，Sync 对应的还有两个 Subclass `NonfairSync`（对应 Nonfair 模式） 和 `FairSync`（对应 Fair 模式）。

```java
private static final class Sync extends AbstractQueuedSynchronizer {
  // ...
}
static final class NonfairSync extends Sync {
  // ...
}
static final class FairSync extends Sync {
  // ...
}
```

#### 实战

```java
public class SemaphoreExample {
  // 请求的数量
  private static final int threadCount = 550;

  public static void main(String[] args) throws InterruptedException {
    // 创建一个具有固定线程数量的线程池对象（如果这里线程池的线程数量给太少的话你会发现执行的很慢）
    ExecutorService threadPool = Executors.newFixedThreadPool(300);
    // 初始许可证数量
    final Semaphore semaphore = new Semaphore(20);

    for (int i = 0; i < threadCount; i++) {
      final int threadnum = i;
      threadPool.execute(() -> {// Lambda 表达式的运用
        try {
          semaphore.acquire();// 获取一个许可，所以可运行线程数量为20/1=20
          test(threadnum);
          semaphore.release();// 释放一个许可
        } catch (InterruptedException e) {
          // TODO Auto-generated catch block
          e.printStackTrace();
        }

      });
    }
    threadPool.shutdown();
    System.out.println("finish");
  }

  public static void test(int threadnum) throws InterruptedException {
    Thread.sleep(1000);// 模拟请求的耗时操作
    System.out.println("threadnum:" + threadnum);
    Thread.sleep(1000);// 模拟请求的耗时操作
  }
}
```

执行 `acquire()` Method Blocking，直到有一个 Permit 可以获得然后拿走一个 Permit；每个 `release` Method 增加一个 Permit，这可能会释放一个 Blocking 的 `acquire()` Method。然而，其实并没有实际的 Permit 这个 Object，`Semaphore` 只是维持了一个可获得 Permit 的数量。 `Semaphore` 经常用于限制获取某种资源的 Thread Count。

当然一次也可以一次拿取和释放多个许可，不过一般没有必要这样做：

```java
semaphore.acquire(5);// 获取5个许可，所以可运行线程数量为20/5=4
test(threadnum);
semaphore.release(5);// 释放5个许可
```

除了 `acquire()` Method 之外，另一个比较常用的与之对应的 Method 是 `tryAcquire()` Method，该 Method 如果获取不到许可就立即返回 false。

[issue645 补充内容](https://github.com/Snailclimb/JavaGuide/issues/645)：

> `Semaphore` 基于 AQS 实现，用于控制 Concurrency 访问的 Thread Count，但它与 Shared Lock 的概念有所不同。`Semaphore` 的 Constructor 使用 `permits` Parameter Initialization AQS 的 `state` Variable，该 Variable 表示可用的 Permit Count。当 Thread 调用 `acquire()` Method 尝试获取许可时，`state` 会 Atomicity 地减 1。如果 `state` 减 1 后大于等于 0，则 `acquire()` 成功返回，Thread 可以继续执行。如果 `state` 减 1 后小于 0，表示当前 Concurrency 访问的 Thread Count 已达到 `permits` 的限制，该 Thread 会被放入 AQS 的 Wait Queue 并 Blocking，**而不是 Spin-Wait**。当其他 Thread 完成 Task 并调用 `release()` Method 时，`state` 会 Atomicity 地加 1。`release()` 操作会唤醒 AQS Wait Queue 中的一个或多个 Blocking Thread。这些被唤醒的 Thread 将再次尝试 `acquire()` 操作，竞争获取可用的许可。因此，`Semaphore` 通过控制 Permit Count 来限制 Concurrency 访问的 Thread Count，而不是通过 Spin 和 Shared Lock 机制。

### CountDownLatch

#### 介绍

`CountDownLatch` 允许 `count` 个 Thread Blocking 在一个地方，直至所有 Thread 的 Task 都执行完毕。

`CountDownLatch` 是一次性的，Counter 的值只能在 Constructor 中 Initialization 一次，之后没有任何机制再次对其设置值，当 `CountDownLatch` 使用完毕后，它不能再次被使用。

#### 原理

`CountDownLatch` 是 Shared Lock 的一种实现，它默认构造 AQS 的 `state` 值为 `count`。这个我们通过 `CountDownLatch` 的 Constructor 即可看出。

```java
public CountDownLatch(int count) {
    if (count < 0) throw new IllegalArgumentException("count < 0");
    this.sync = new Sync(count);
}

private static final class Sync extends AbstractQueuedSynchronizer {
    Sync(int count) {
        setState(count);
    }
  //...
}
```

当 Thread 调用 `countDown()` 时，其实使用了 `tryReleaseShared` Method 以 CAS 的操作来减少 `state`，直至 `state` 为 0。当 `state` 为 0 时，表示所有的 Thread 都调用了 `countDown` Method，那么在 `CountDownLatch` 上等待的 Thread 就会被唤醒并继续执行。

```java
public void countDown() {
    // Sync 是 CountDownLatch 的内部类 , 继承了 AbstractQueuedSynchronizer
    sync.releaseShared(1);
}
```

`releaseShared` Method 是 `AbstractQueuedSynchronizer` 中的默认实现。

```java
// 释放共享锁
// 如果 tryReleaseShared 返回 true，就唤醒等待队列中的一个或多个线程。
public final boolean releaseShared(int arg) {
    //释放共享锁
    if (tryReleaseShared(arg)) {
      //释放当前节点的后置等待节点
      doReleaseShared();
      return true;
    }
    return false;
}
```

`tryReleaseShared` Method 是 `CountDownLatch` 的 Inner Class `Sync` Override 的一个 Method， `AbstractQueuedSynchronizer` 中的默认实现仅仅抛出 `UnsupportedOperationException` Exception。

```java
// 对 state 进行递减，直到 state 变成 0；
// 只有 count 递减到 0 时，countDown 才会返回 true
protected boolean tryReleaseShared(int releases) {
    // 自选检查 state 是否为 0
    for (;;) {
        int c = getState();
        // 如果 state 已经是 0 了，直接返回 false
        if (c == 0)
            return false;
        // 对 state 进行递减
        int nextc = c-1;
        // CAS 操作更新 state 的值
        if (compareAndSetState(c, nextc))
            return nextc == 0;
    }
}
```

以无参 `await` Method 为例，当调用 `await()` 的时候，如果 `state` 不为 0，那就证明 Task 还没有执行完毕，`await()` 就会一直 Blocking，也就是说 `await()` 之后的语句不会被执行（`main` Thread 被加入到 Wait Queue 也就是 变体 CLH Queue 中了）。然后，`CountDownLatch` 会 Spin CAS 判断 `state == 0`，如果 `state == 0` 的话，就会释放所有等待的 Thread，`await()` Method 之后的语句得到执行。

```java
// 等待（也可以叫做加锁）
public void await() throws InterruptedException {
    sync.acquireSharedInterruptibly(1);
}
// 带有超时时间的等待
public boolean await(long timeout, TimeUnit unit)
    throws InterruptedException {
    return sync.tryAcquireSharedNanos(1, unit.toNanos(timeout));
}
```

`acquireSharedInterruptibly` Method 是 `AbstractQueuedSynchronizer` 中的默认实现。

```java
// 尝试获取锁，获取成功则返回，失败则加入等待队列，挂起线程
public final void acquireSharedInterruptibly(int arg)
    throws InterruptedException {
    if (Thread.interrupted())
      throw new InterruptedException();
        // 尝试获得锁，获取成功则返回
    if (tryAcquireShared(arg) < 0)
      // 获取失败加入等待队列，挂起线程
      doAcquireSharedInterruptibly(arg);
}
```

`tryAcquireShared` Method 是 `CountDownLatch` 的 Inner Class `Sync` Override 的一个 Method，其作用就是判断 `state` 的值是否为 0，是的话就返回 1，否则返回 -1。

```java
protected int tryAcquireShared(int acquires) {
    return (getState() == 0) ? 1 : -1;
}
```

#### 实战

**CountDownLatch 的两种典型用法**：

1. 某一 Thread 在开始运行前等待 n 个 Thread 执行完毕 : 将 `CountDownLatch` 的 Counter Initialization 为 n（`new CountDownLatch(n)`），每当一个 Task Thread 执行完毕，就将 Counter 减 1（`countdownlatch.countDown()`），当 Counter 的值变为 0 时，在 `CountDownLatch 上 await()` 的 Thread 就会被唤醒。一个典型应用场景就是启动一个服务时，Main Thread 需要等待多个组件加载完毕，之后再继续执行。
2. 实现多个 Thread 开始执行 Task 的最大 Parallelism：注意是 Parallelism，不是 Concurrency，强调的是多个 Thread 在某一时刻同时开始执行。类似于赛跑，将多个 Thread 放到起点，等待发令枪响，然后同时开跑。做法是 Initialization 一个 Shared 的 `CountDownLatch` Object，将其 Counter Initialization 为 1（`new CountDownLatch(1)`），多个 Thread 在开始执行 Task 前首先 `coundownlatch.await()`，当 Main Thread 调用 `countDown()` 时，Counter 变为 0，多个 Thread 同时被唤醒。

**CountDownLatch 代码示例**：

```java
public class CountDownLatchExample {
  // 请求的数量
  private static final int THREAD_COUNT = 550;

  public static void main(String[] args) throws InterruptedException {
    // 创建一个具有固定线程数量的线程池对象（如果这里线程池的线程数量给太少的话你会发现执行的很慢）
    // 只是测试使用，实际场景请手动赋值线程池参数
    ExecutorService threadPool = Executors.newFixedThreadPool(300);
    final CountDownLatch countDownLatch = new CountDownLatch(THREAD_COUNT);
    for (int i = 0; i < THREAD_COUNT; i++) {
      final int threadNum = i;
      threadPool.execute(() -> {
        try {
          test(threadNum);
        } catch (InterruptedException e) {
          e.printStackTrace();
        } finally {
          // 表示一个请求已经被完成
          countDownLatch.countDown();
        }

      });
    }
    countDownLatch.await();
    threadPool.shutdown();
    System.out.println("finish");
  }

  public static void test(int threadnum) throws InterruptedException {
    Thread.sleep(1000);
    System.out.println("threadNum:" + threadnum);
    Thread.sleep(1000);
  }
}
```

上面的代码中，我们定义了请求的数量为 550，当这 550 个请求被处理完成之后，才会执行 `System.out.println("finish");`。

与 `CountDownLatch` 的第一次交互是 Main Thread 等待其他 Thread。 Main Thread 必须在启动其他 Thread 后立即调用 `CountDownLatch.await()` Method。这样 Main Thread 的操作就会在这个 Method 上 Blocking，直到其他 Thread 完成各自的 Task。

其他 N 个 Thread 必须 Reference 闭 Lock Object，因为他们需要通知 `CountDownLatch` Object，他们已经完成了各自的 Task。这种通知机制是通过 `CountDownLatch.countDown()` Method 来完成的；每调用一次这个 Method，在 Constructor 中 Initialization 的 count 值就减 1。所以当 N 个 Thread 都调 用了这个 Method，count 的值等于 0，然后 Main Thread 就能通过 `await()` Method，恢复执行自己的 Task。

再插一嘴：`CountDownLatch` 的 `await()` Method 使用不当很容易产生 Deadlock，比如我们上面代码中的 for Loop 改为：

```java
for (int i = 0; i < threadCount-1; i++) {
.......
}
```

这样就导致 `count` 的值没办法等于 0，然后就会导致一直等待。

### CyclicBarrier

#### 介绍

`CyclicBarrier` 和 `CountDownLatch` 非常类似，它也可以实现 Thread 间的技术等待，但是它的功能比 `CountDownLatch` 更加复杂和强大。主要应用场景和 `CountDownLatch` 类似。

> `CountDownLatch` 的实现是基于 AQS 的，而 `CyclicBarrier` 是基于 `ReentrantLock`(`ReentrantLock` 也属于 AQS Synchronizer)和 `Condition` 的。

`CyclicBarrier` 的字面意思是可 Loop 使用（Cyclic）的屏障（Barrier）。它要做的事情是：让一组 Thread 到达一个屏障（也可以叫同步点）时被 Blocking，直到最后一个 Thread 到达屏障时，屏障才会开门，所有被屏障拦截的 Thread 才会继续干活。

#### 原理

`CyclicBarrier` 内部通过一个 `count` Variable 作为 Counter，`count` 的初始值为 `parties` 属性的 Initialization 值，每当一个 Thread 到了 Barrier 这里了，那么就将 Counter 减 1。如果 count 值为 0 了，表示这是这一代最后一个 Thread 到达 Barrier，就尝试执行我们 Constructor 中输入的 Task。

```java
//每次拦截的线程数
private final int parties;
//计数器
private int count;
```

下面我们结合源码来简单看看。

1、`CyclicBarrier` 默认的 Constructor 是 `CyclicBarrier(int parties)`，其 Parameter 表示屏障拦截的 Thread Count，每个 Thread 调用 `await()` Method 告诉 `CyclicBarrier` 我已经到达了屏障，然后 Current Thread 被 Blocking。

```java
public CyclicBarrier(int parties) {
    this(parties, null);
}

public CyclicBarrier(int parties, Runnable barrierAction) {
    if (parties <= 0) throw new IllegalArgumentException();
    this.parties = parties;
    this.count = parties;
    this.barrierCommand = barrierAction;
}
```

其中，`parties` 就代表了有拦截的 Thread 的数量，当拦截的 Thread Count 达到这个值的时候就打开 Barrier，让所有 Thread 通过。

2、当调用 `CyclicBarrier` Object 调用 `await()` Method 时，实际上调用的是 `dowait(false, 0L)` Method。 `await()` Method 就像树立起一个 Barrier 的行为一样，将 Thread 挡住了，当拦住的 Thread Count 达到 `parties` 的值时，Barrier 才会打开，Thread 才得以通过执行。

```java
public int await() throws InterruptedException, BrokenBarrierException {
  try {
      return dowait(false, 0L);
  } catch (TimeoutException toe) {
      throw new Error(toe); // cannot happen
  }
}
```

`dowait(false, 0L)` Method 源码分析如下：

```java
    // 当线程数量或者请求数量达到 count 时 await 之后的方法才会被执行。上面的示例中 count 的值就为 5。
    private int count;
    /**
     * Main barrier code, covering the various policies.
     */
    private int dowait(boolean timed, long nanos)
        throws InterruptedException, BrokenBarrierException,
               TimeoutException {
        final ReentrantLock lock = this.lock;
        // 锁住
        lock.lock();
        try {
            final Generation g = generation;

            if (g.broken)
                throw new BrokenBarrierException();

            // 如果线程中断了，抛出异常
            if (Thread.interrupted()) {
                breakBarrier();
                throw new InterruptedException();
            }
            // count 减1
            int index = --count;
            // 当 count 数量减为 0 之后说明最后一个线程已经到达栅栏了，也就是达到了可以执行await 方法之后的条件
            if (index == 0) {  // tripped
                boolean ranAction = false;
                try {
                    final Runnable command = barrierCommand;
                    if (command != null)
                        command.run();
                    ranAction = true;
                    // 将 count 重置为 parties 属性的初始化值
                    // 唤醒之前等待的线程
                    // 下一波执行开始
                    nextGeneration();
                    return 0;
                } finally {
                    if (!ranAction)
                        breakBarrier();
                }
            }

            // loop until tripped, broken, interrupted, or timed out
            for (;;) {
                try {
                    if (!timed)
                        trip.await();
                    else if (nanos > 0L)
                        nanos = trip.awaitNanos(nanos);
                } catch (InterruptedException ie) {
                    if (g == generation && ! g.broken) {
                        breakBarrier();
                        throw ie;
                    } else {
                        // We're about to finish waiting even if we had not
                        // been interrupted, so this interrupt is deemed to
                        // "belong" to subsequent execution.
                        Thread.currentThread().interrupt();
                    }
                }

                if (g.broken)
                    throw new BrokenBarrierException();

                if (g != generation)
                    return index;

                if (timed && nanos <= 0L) {
                    breakBarrier();
                    throw new TimeoutException();
                }
            }
        } finally {
            lock.unlock();
        }
    }
```

#### 实战

示例 1：

```java
public class CyclicBarrierExample1 {
  // 请求的数量
  private static final int threadCount = 550;
  // 需要同步的线程数量
  private static final CyclicBarrier cyclicBarrier = new CyclicBarrier(5);

  public static void main(String[] args) throws InterruptedException {
    // 创建线程池
    ExecutorService threadPool = Executors.newFixedThreadPool(10);

    for (int i = 0; i < threadCount; i++) {
      final int threadNum = i;
      Thread.sleep(1000);
      threadPool.execute(() -> {
        try {
          test(threadNum);
        } catch (InterruptedException e) {
          // TODO Auto-generated catch block
          e.printStackTrace();
        } catch (BrokenBarrierException e) {
          // TODO Auto-generated catch block
          e.printStackTrace();
        }
      });
    }
    threadPool.shutdown();
  }

  public static void test(int threadnum) throws InterruptedException, BrokenBarrierException {
    System.out.println("threadnum:" + threadnum + "is ready");
    try {
      /**等待60秒，保证子线程完全执行结束*/
      cyclicBarrier.await(60, TimeUnit.SECONDS);
    } catch (Exception e) {
      System.out.println("-----CyclicBarrierException------");
    }
    System.out.println("threadnum:" + threadnum + "is finish");
  }

}
```

运行结果，如下：

```plain
threadnum:0is ready
threadnum:1is ready
threadnum:2is ready
threadnum:3is ready
threadnum:4is ready
threadnum:4is finish
threadnum:0is finish
threadnum:1is finish
threadnum:2is finish
threadnum:3is finish
threadnum:5is ready
threadnum:6is ready
threadnum:7is ready
threadnum:8is ready
threadnum:9is ready
threadnum:9is finish
threadnum:5is finish
threadnum:8is finish
threadnum:7is finish
threadnum:6is finish
......
```

可以看到当 Thread Count 也就是请求数量达到我们定义的 5 个的时候， `await()` Method 之后的 Method 才被执行。

另外，`CyclicBarrier` 还提供一个更高级的 Constructor `CyclicBarrier(int parties, Runnable barrierAction)`，用于在 Thread 到达屏障时，优先执行 `barrierAction`，方便处理更复杂的业务场景。

示例 2：

```java
public class CyclicBarrierExample2 {
  // 请求的数量
  private static final int threadCount = 550;
  // 需要同步的线程数量
  private static final CyclicBarrier cyclicBarrier = new CyclicBarrier(5, () -> {
    System.out.println("------当线程数达到之后，优先执行------");
  });

  public static void main(String[] args) throws InterruptedException {
    // 创建线程池
    ExecutorService threadPool = Executors.newFixedThreadPool(10);

    for (int i = 0; i < threadCount; i++) {
      final int threadNum = i;
      Thread.sleep(1000);
      threadPool.execute(() -> {
        try {
          test(threadNum);
        } catch (InterruptedException e) {
          // TODO Auto-generated catch block
          e.printStackTrace();
        } catch (BrokenBarrierException e) {
          // TODO Auto-generated catch block
          e.printStackTrace();
        }
      });
    }
    threadPool.shutdown();
  }

  public static void test(int threadnum) throws InterruptedException, BrokenBarrierException {
    System.out.println("threadnum:" + threadnum + "is ready");
    cyclicBarrier.await();
    System.out.println("threadnum:" + threadnum + "is finish");
  }

}
```

运行结果，如下：

```plain
threadnum:0is ready
threadnum:1is ready
threadnum:2is ready
threadnum:3is ready
threadnum:4is ready
------当线程数达到之后，优先执行------
threadnum:4is finish
threadnum:0is finish
threadnum:2is finish
threadnum:1is finish
threadnum:3is finish
threadnum:5is ready
threadnum:6is ready
threadnum:7is ready
threadnum:8is ready
threadnum:9is ready
------当线程数达到之后，优先执行------
threadnum:9is finish
threadnum:5is finish
threadnum:6is finish
threadnum:8is finish
threadnum:7is finish
......
```

## 参考

- Java Concurrency 之 AQS 详解：<https://www.cnblogs.com/waterystone/p/4920797.html>
- 从 ReentrantLock 的实现看 AQS 的原理及应用：<https://tech.meituan.com/2019/12/05/aqs-theory-and-apply.html>

<!-- @include: @article-footer.snippet.md -->

```

```
