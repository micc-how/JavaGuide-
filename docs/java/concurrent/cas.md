---
title: Compare-And-Swap (CAS) 详解
description: CAS 深度解析：详解CAS Atomic Operation 原理、Unsafe Class 实现、ABA问题及解决方案、Spin Lock 机制、与 Pessimistic Lock Performance 对比。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: CAS,Compare-And-Swap,Atomic Operation,ABA问题,Spin Lock,Optimistic Lock,Unsafe,CAS原理
---

Optimistic Lock 和 Pessimistic Lock 的介绍以及 Optimistic Lock 常见实现方式可以阅读笔者写的这篇文章：[Optimistic Lock 和 Pessimistic Lock 详解](https://javaguide.cn/java/concurrent/optimistic-lock-and-pessimistic-lock.html)。

这篇文章主要介绍：Java 中 CAS 的实现以及 CAS 存在的一些问题。

## Java 中 CAS 是如何实现的？

在 Java 中，实现 CAS（Compare-And-Swap, CAS）操作的一个关键 Class 是 `Unsafe`。

`Unsafe` Class 位于 `sun.misc` Package 下，是一个提供低级别、不安全操作的 Class。由于其强大的功能和潜在的危险性，它通常用于 Java Virtual Machine (JVM) 内部或一些需要极 High Performance 和底层访问的库中，而不推荐普通开发者在应用程序中使用。关于 `Unsafe` Class 的详细介绍，可以阅读这篇文章：📌[Java 魔法 Class Unsafe 详解](https://javaguide.cn/java/basis/unsafe.html)。

`sun.misc` Package 下的 `Unsafe` Class 提供了 `compareAndSwapObject`、`compareAndSwapInt`、`compareAndSwapLong` Method 来实现的对 `Object`、`int`、`long` Type 的 CAS 操作：

```java
/**
 * 以原子方式更新对象字段的值。
 *
 * @param o        要操作的对象
 * @param offset   对象字段的内存偏移量
 * @param expected 期望的旧值
 * @param x        要设置的新值
 * @return 如果值被成功更新，则返回 true；否则返回 false
 */
boolean compareAndSwapObject(Object o, long offset, Object expected, Object x);

/**
 * 以原子方式更新 int 类型的对象字段的值。
 */
boolean compareAndSwapInt(Object o, long offset, int expected, int x);

/**
 * 以原子方式更新 long 类型的对象字段的值。
 */
boolean compareAndSwapLong(Object o, long offset, long expected, long x);
```

`Unsafe` 在 JDK 8 中提供的这些 CAS Method 是 `native` Method。Java 代码通过它们表达 Atomic CAS 语义，HotSpot 通常会把相关调用识别为 JVM 内部 Function（intrinsic），再映射为目标处理器支持的 Atomic Instruction 或等价实现。具体实现依赖 JVM 和 CPU 架构，但不能简单概括为“通过 Java Native Interface (JNI) 调用 C++ 内联汇编”。

`java.util.concurrent.atomic` Package 提供了一些用于 Atomic Operation 的 Class。

![JUC Atomic Class 概览](https://oss.javaguide.cn/github/javaguide/java/JUC%E5%8E%9F%E5%AD%90%E7%B1%BB%E6%A6%82%E8%A7%88.png)

关于这些 Atomic Class 的介绍和使用，可以阅读这篇文章：[Atomic Class 总结](https://javaguide.cn/java/concurrent/atomic-classes.html)。

Atomic Class 依赖于 CAS Optimistic Lock 来保证其 Method 的 Atomicity，而不需要使用传统的 Locking Mechanism（如 `synchronized` 块或 `ReentrantLock`）。

`AtomicInteger` 是 Java 的 Atomic Class 之一，主要用于对 `int` Type 的 Variable 进行 Atomic Operation。下面的 JDK 8 实现利用 `Unsafe` 提供的低级别 Atomic Operation Method；在较新的 JDK 中，相关 API 和内部实现细节可能不同，应用代码也可以使用标准的 `VarHandle` 表达 Atomic 访问语义。

下面，我们通过解读 `AtomicInteger` 的核心源码（JDK1.8），来说明 Java 如何使用 `Unsafe` Class 的 Method 来实现 Atomic Operation。

`AtomicInteger` 核心源码如下：

```java
// 获取 Unsafe 实例
private static final Unsafe unsafe = Unsafe.getUnsafe();
private static final long valueOffset;

static {
    try {
        // 获取“value”字段在AtomicInteger类中的内存偏移量
        valueOffset = unsafe.objectFieldOffset
            (AtomicInteger.class.getDeclaredField("value"));
    } catch (Exception ex) { throw new Error(ex); }
}
// 确保“value”字段的可见性
private volatile int value;

// 如果当前值等于预期值，则原子地将值设置为newValue
// 使用 Unsafe#compareAndSwapInt 方法进行CAS操作
public final boolean compareAndSet(int expect, int update) {
    return unsafe.compareAndSwapInt(this, valueOffset, expect, update);
}

// 原子地将当前值加 delta 并返回旧值
public final int getAndAdd(int delta) {
    return unsafe.getAndAddInt(this, valueOffset, delta);
}

// 原子地将当前值加 1 并返回加之前的值（旧值）
// 使用 Unsafe#getAndAddInt 方法进行CAS操作。
public final int getAndIncrement() {
    return unsafe.getAndAddInt(this, valueOffset, 1);
}

// 原子地将当前值减 1 并返回减之前的值（旧值）
public final int getAndDecrement() {
    return unsafe.getAndAddInt(this, valueOffset, -1);
}
```

`Unsafe#getAndAddInt` 源码：

```java
// 原子地获取并增加整数值
public final int getAndAddInt(Object o, long offset, int delta) {
    int v;
    do {
        // 以 volatile 方式获取对象 o 在内存偏移量 offset 处的整数值
        v = getIntVolatile(o, offset);
    } while (!compareAndSwapInt(o, offset, v, v + delta));
    // 返回旧值
    return v;
}
```

可以看到，`getAndAddInt` 使用了 `do-while` Loop：在 `compareAndSwapInt` 操作失败时，会不断 Retry 直到成功。也就是说，`getAndAddInt` Method 会通过 `compareAndSwapInt` Method 来尝试更新 `value` 的值，如果更新失败（当前值在此期间被其他 Thread 修改），它会重新获取当前值并再次尝试更新，直到操作成功。

由于 CAS 操作可能会因为 Concurrency 冲突而失败，因此通常会与 `while` Loop 搭配使用，在失败后不断 Retry，直到操作成功。这就是 **Spin Lock 机制**。

## CAS Algorithm 存在哪些问题？

ABA 问题是 CAS Algorithm 最常见的问题。

### ABA 问题

如果一个 Variable V 初次读取的时候是 A 值，并且在准备赋值的时候检查到它仍然是 A 值，那我们就能说明它的值没有被其他 Thread 修改过了吗？很明显是不能的，因为在这段时间它的值可能被改为其他值，然后又改回 A，那 CAS 操作就会误认为它从来没有被修改过。这个问题被称为 CAS 操作的 **"ABA"问题。**

ABA 问题的解决思路是在 Variable 前面追加上**Version 或者 Timestamp**。JDK 1.5 以后的 `AtomicStampedReference` Class 就是用来解决 ABA 问题的，其中的 `compareAndSet()` Method 就是首先检查当前 Reference 是否等于预期 Reference，并且当前标志是否等于预期标志，如果全部相等，则以 Atomic 方式将该 Reference 和该标志的值设置为给定的更新值。

```java
public boolean compareAndSet(V   expectedReference,
                             V   newReference,
                             int expectedStamp,
                             int newStamp) {
    Pair<V> current = pair;
    return
        expectedReference == current.reference &&
        expectedStamp == current.stamp &&
        ((newReference == current.reference &&
          newStamp == current.stamp) ||
         casPair(current, Pair.of(newReference, newStamp)));
}
```

### Loop 时间长 Overhead 大

CAS 经常会用到 Spin 操作来进行 Retry，也就是不成功就一直 Loop 执行直到成功。如果长时间不成功，会给 CPU 带来非常大的执行 Overhead。

如果 JVM 能够支持处理器提供的 `pause` Instruction，那么 Spin 操作的效率将有所提升。`pause` Instruction 有两个重要作用：

1. **延迟流水线执行 Instruction**：`pause` Instruction 可以延迟 Instruction 的执行，从而减少 CPU 的资源消耗。具体的延迟时间取决于处理器的实现版本，在某些处理器上，延迟时间可能为零。
2. **避免内存顺序冲突**：在退出 Loop 时，`pause` Instruction 可以避免由于内存顺序冲突而导致的 CPU 流水线被清空，从而提高 CPU 的执行效率。

### 只能保证一个 Shared Variable 的 Atomic Operation

CAS 操作仅能对单个 Shared Variable 有效。当需要操作多个 Shared Variable 时，CAS 就显得无能为力。不过，从 JDK 1.5 开始，Java 提供了 `AtomicReference` Class，这使得我们能够保证 Reference Object 之间的 Atomicity。通过将多个 Variable Encapsulate 在一个 Object 中，我们可以使用 `AtomicReference` 来执行 CAS 操作。

除了 `AtomicReference` 这种方式之外，还可以利用 Locking 来保证。

## 总结

在 Java 中，Atomic Class、`VarHandle` 等 API 可以表达 CAS 操作；JVM 再根据目标平台将其实现为处理器支持的 Atomic Instruction 或等价机制。具体实现依赖 JVM 和 CPU 架构，并不由 Java 规范限定为 JNI 或某一种汇编写法。

CAS 虽然具有高效的 Lock-Free 特性，但也需要注意 ABA、Loop 时间长 Overhead 大等问题。
