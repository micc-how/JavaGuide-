---
title: Java Virtual Machine (JVM) Garbage Collection (GC) 详解（重点）
description: JVM GC 详解：全面讲解GC Algorithm（Mark-Sweep、复制、Mark-Compact）、Generational 回收机制、常用 Garbage Collector（Serial、Parallel、CMS、G1、ZGC、Shenandoah）、GC调优实践。
category: Java
tag:
  - JVM
head:
  - - meta
    - name: keywords
      content: JVM GC Algorithm,Garbage Collector,Generational 回收,Mark-Sweep,Copying Algorithm,G1 GC,ZGC,Shenandoah,GC调优
---

> 如果没有特殊说明，都是针对的是 HotSpot 虚拟机。
>
> 本文基于《深入理解 Java Virtual Machine：JVM 高级特性与最佳实践》进行总结补充。
>
> 常见面试题：
>
> - 如何判断 Object 是否死亡（两种 Method）。
> - 简单的介绍一下 Strong Reference、Soft Reference、Weak Reference、Phantom Reference（Phantom Reference 与 Soft Reference 和 Weak Reference 的区别、使用 Soft Reference 能带来的好处）。
> - 如何判断一个 Constant 是废弃 Constant
> - 如何判断一个 Class 是无用的 Class
> - GC 有哪些 Algorithm，各自的特点？
> - HotSpot 为什么要分为 Young Generation 和 Old Generation？
> - 常见的 Garbage Collector 有哪些？
> - 介绍一下 CMS,G1 收集器。
> - Minor Gc 和 Full GC 有什么不同呢？

## 前言

当需要排查各种 Out of Memory (OOM) 问题、当 GC 成为系统达到更 High Concurrency 的瓶颈时，我们就需要对这些“自动化”的技术实施必要的 Monitoring 和调节。

## Heap Space 的基本结构

Java 的自动内存管理主要是针对 Object 内存的回收和 Object 内存的分配。同时，Java 自动内存管理最核心的功能是 **Heap** 内存中 Object 的分配与回收。

Java Heap 是 Garbage Collector 管理的主要区域，因此也被称作 **GC Heap（Garbage Collected Heap）**。

从 GC 的角度来说，由于现在收集器基本都采用 Generational GC Algorithm，所以 Java Heap 被划分为了几个不同的区域，这样我们就可以根据各个区域的特点选择合适的 GC Algorithm。

在 JDK 7 及更早版本的 HotSpot 中，GC 通常按下面三部分介绍，其中 Permanent Generation (PermGen) 是 Method Area 的实现，并不属于 Java Heap：

1. Young Generation 内存(Young Generation)
2. 老生代(Old Generation)
3. PermGen(Permanent Generation)

下图所示的 Eden 区、两个 Survivor 区 S0 和 S1 都属于 Young Generation，中间一层属于 Old Generation，最下面一层属于 PermGen。

![Heap Memory 结构](https://oss.javaguide.cn/github/javaguide/java/jvm/hotspot-heap-structure.png)

**JDK 8 移除了 PermGen，Class Metadata 改为存放在使用 Native Memory 的 Metaspace 中**。

关于 Heap Space 结构更详细的介绍，可以回过头看看 [Java Memory Area 详解](./memory-area.md) 这篇文章。

## Memory Allocation 和回收原则

### Object 优先在 Eden 区分配

大多数情况下，Object 在 Young Generation 中 Eden 区分配。当 Eden 区没有足够空间进行分配时，虚拟机将发起一次 Minor GC。下面我们来进行实际测试一下。

测试代码：

```java
public class GCTest {
  public static void main(String[] args) {
    byte[] allocation1, allocation2;
    allocation1 = new byte[30900*1024];
  }
}
```

通过以下方式运行：
![](https://oss.javaguide.cn/github/javaguide/java/jvm/25178350.png)

添加的 Parameter：`-XX:+PrintGCDetails`
![](https://oss.javaguide.cn/github/javaguide/java/jvm/run-with-PrintGCDetails.png)

运行结果（红色字体描述有误，应该是对应于 JDK1.7 的 PermGen）：

![](https://oss.javaguide.cn/github/javaguide/java/jvm/28954286.jpg)

从上图我们可以看出 Eden 区内存几乎已经被分配完全（即使程序什么也不做，Young Generation 也会使用 2000 多 k 内存）。

假如我们再为 `allocation2` 分配内存会出现什么情况呢？

```java
allocation2 = new byte[900*1024];
```

![](https://oss.javaguide.cn/github/javaguide/java/jvm/28128785.jpg)

给 `allocation2` 分配内存的时候 Eden 区内存几乎已经被分配完了

当 Eden 区没有足够空间进行分配时，虚拟机将发起一次 Minor GC。GC 期间虚拟机又发现 `allocation1` 无法存入 Survivor 空间，所以只好通过 **分配担保机制** 把 Young Generation 的 Object 提前转移到 Old Generation 中去，Old Generation 上的空间足够存放 `allocation1`，所以不会出现 Full GC。执行 Minor GC 后，后面分配的 Object 如果能够存在 Eden 区的话，还是会在 Eden 区分配内存。可以执行如下代码验证：

```java
public class GCTest {

  public static void main(String[] args) {
    byte[] allocation1, allocation2,allocation3,allocation4,allocation5;
    allocation1 = new byte[32000*1024];
    allocation2 = new byte[1000*1024];
    allocation3 = new byte[1000*1024];
    allocation4 = new byte[1000*1024];
    allocation5 = new byte[1000*1024];
  }
}

```

### Large Object 直接进入 Old Generation

Large Object 就是需要大量连续内存空间的 Object（比如：String、Array）。

Large Object 直接进入 Old Generation 的行为是由虚拟机动态决定的，它与具体使用的 Garbage Collector 和相关 Parameter 有关。 Large Object 直接进入 Old Generation 是一种优化策略，旨在避免将 Large Object 放入 Young Generation，从而减少 Young Generation 的 GC 频率和成本。

- G1 Garbage Collector 把大小达到或超过 Region 一半的 Object 视为 Humongous Object，并直接分配到属于 Old Generation 的连续 Humongous Region 中。Region 大小可通过 `-XX:G1HeapRegionSize` 设置。
- 其他收集器是否以及在什么条件下把 Large Object 直接分配到 Old Generation，取决于具体收集器和 JDK 版本，不能用一个通用 Threshold 概括。

### 长期存活的 Object 将进入 Old Generation

既然虚拟机采用了 Generational Collection 的思想来管理内存，那么内存回收时就必须能识别哪些 Object 应放在 Young Generation，哪些 Object 应放在 Old Generation 中。为了做到这一点，虚拟机给每个 Object 一个 Object 年龄（Age）Counter。

大部分情况，Object 都会首先在 Eden 区域分配。如果 Object 在 Eden 出生并经过第一次 Minor GC 后仍然能够存活，并且能被 Survivor 容纳的话，将被移动到 Survivor 空间（s0 或者 s1）中，并将 Object 年龄设为 1（Eden 区->Survivor 区后 Object 的初始年龄变为 1）。

Object 在 Survivor 中每熬过一次 Minor GC，年龄就增加 1 岁，当它的年龄达到 Promotion Threshold 时，就会被 Promotion 到 Old Generation 中。`-XX:MaxTenuringThreshold` 用于设置 Object Promotion 年龄的最大 Threshold，默认值与 Garbage Collector 有关。例如，JDK 8 中 Parallel GC 的默认值为 15，CMS 的默认值为 6；实际 Promotion Threshold 还可能由 JVM 动态调整。

> 修正（[issue552](https://github.com/Snailclimb/JavaGuide/issues/552)）：“Hotspot Traversal 所有 Object 时，按照年龄从小到大对其所占用的大小进行累积，当累积的某个年龄大小超过了 survivor 区的 50% 时（默认值是 50%，可以通过 `-XX:TargetSurvivorRatio=percent` 来设置，参见 [issue1199](https://github.com/Snailclimb/JavaGuide/issues/1199)），取这个年龄和 MaxTenuringThreshold 中更小的一个值，作为新的 Promotion 年龄 Threshold”。
>
> jdk8 官方文档 Reference：<https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html>。
>
> ![](https://oss.javaguide.cn/java-guide-blog/image-20210523201742303.png)
>
> **动态年龄计算的代码如下：**
>
> ```c++
> uint ageTable::compute_tenuring_threshold(size_t survivor_capacity) {
> //survivor_capacity是survivor空间的大小
> size_t desired_survivor_size = (size_t)((((double)survivor_capacity)*TargetSurvivorRatio)/100);
> size_t total = 0;
> uint age = 1;
> while (age < table_size) {
> //sizes数组是每个年龄段对象大小
> total += sizes[age];
> if (total > desired_survivor_size) {
> break;
> }
> age++;
> }
> uint result = age < MaxTenuringThreshold ? age : MaxTenuringThreshold;
> ...
> }
>
> ```
>
> 额外补充说明([issue672](https://github.com/Snailclimb/JavaGuide/issues/672))：**关于默认的 Promotion 年龄是 15，这个说法的来源大部分都是《深入理解 Java Virtual Machine》这本书。**
> 如果你去 Oracle 的官网阅读[相关的虚拟机 Parameter](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html)，你会发现 `-XX:MaxTenuringThreshold=threshold` 这里有个说明
>
> **Sets the maximum tenuring threshold for use in adaptive GC sizing. The largest value is 15. The default value is 15 for the parallel (throughput) collector, and 6 for the CMS collector.默认 Promotion 年龄并不都是 15，这个是要区分 Garbage Collector 的，CMS 就是 6.**

### 主要进行 gc 的区域

周志明先生在《深入理解 Java Virtual Machine》第二版中 P92 如是写道：

> ~~_“Old Generation GC（Major GC/Full GC），指发生在 Old Generation 的 GC……”_~~

上面的说法已经在《深入理解 Java Virtual Machine》第三版中被改正过来了。感谢 R 大的回答：

![R 大的回答](https://oss.javaguide.cn/github/javaguide/java/jvm/rf-hotspot-vm-gc.png)

**总结：**

针对 HotSpot VM 的实现，它里面的 GC 其实准确分类只有两大种：

部分收集 (Partial GC)：

- Young Generation 收集（Minor GC / Young GC）：只对 Young Generation 进行 GC；
- Old Generation 收集（Major GC / Old GC）：只对 Old Generation 进行 GC。需要注意的是 Major GC 在有的语境中也用于指代整 Heap 收集；
- 混合收集（Mixed GC）：对整个 Young Generation 和部分 Old Generation 进行 GC。

整 Heap 收集 (Full GC)：对整个 Java Heap 进行收集；是否同时回收 Method Area 中的 Class Metadata 取决于收集器、JDK 版本和 Class Unloading 条件。

### Allocation Guarantee

Allocation Guarantee 是为了确保在 Minor GC 之前 Old Generation 本身还有容纳 Young Generation 所有 Object 的剩余空间。

《深入理解 Java Virtual Machine》第三章对于 Allocation Guarantee 的描述如下：

> JDK 6 Update 24 之前，在发生 Minor GC 之前，虚拟机必须先检查 Old Generation 最大可用的连续空间是否大于 Young Generation 所有 Object 总空间，如果这个条件成立，那这一次 Minor GC 可以确保是安全的。如果不成立，则虚拟机会先查看 `-XX:HandlePromotionFailure` Parameter 的设置值是否允许担保失败(Handle Promotion Failure);如果允许，那会继续检查 Old Generation 最大可用的连续空间是否大于历次 Promotion 到 Old Generation Object 的平均大小，如果大于，将尝试进行一次 Minor GC，尽管这次 Minor GC 是有风险的；如果小于，或者 `-XX: HandlePromotionFailure` 设置不允许冒险，那这时就要改为进行一次 Full GC。
>
> JDK 6 Update 24 之后的规则变为只要 Old Generation 的连续空间大于 Young Generation Object 总大小或者历次 Promotion 的平均大小，就会进行 Minor GC，否则将进行 Full GC。

## Dead Object 判断方法

Heap 中几乎放着所有的 Object Instance，对 Heap GC 前的第一步就是要判断哪些 Object 已经死亡（即不能再被任何途径使用的 Object）。

### Reference Counting

给 Object 中添加一个 Reference Counter：

- 每当有一个地方 Reference 它，Counter 就加 1；
- 当 Reference 失效，Counter 就减 1；
- 任何时候 Counter 为 0 的 Object 就是不可能再被使用的。

**这个 Method 实现简单，但是目前主流的 Java Virtual Machine 并没有选择这个 Algorithm 来管理 Object Lifecycle，其重要原因之一是它无法单独解决 Object 之间 Circular Reference 的问题。**

![Object 之间 Circular Reference](https://oss.javaguide.cn/github/javaguide/java/jvm/object-circular-reference.png)

所谓 Object 之间的 Mutual Reference 问题，如下面代码所示：除了 Object `objA` 和 `objB` Mutual Reference 着对方之外，这两个 Object 之间再无任何 Reference。但是他们因为互相 Reference 对方，导致它们的 Reference Counter 都不为 0，于是 Reference Counting 无法通知 GC Collector 回收他们。

```java
public class ReferenceCountingGc {
    Object instance = null;
    public static void main(String[] args) {
        ReferenceCountingGc objA = new ReferenceCountingGc();
        ReferenceCountingGc objB = new ReferenceCountingGc();
        objA.instance = objB;
        objB.instance = objA;
        objA = null;
        objB = null;
    }
}
```

### Reachability Analysis

这个 Algorithm 的基本思想就是通过一系列的称为 **“GC Roots”** 的 Object 作为起点，从这些 Node 开始向下搜索，Node 所走过的路径称为 Reference Chain，当一个 Object 到 GC Roots 没有任何 Reference Chain 相连的话，则证明此 Object 是不可用的，需要被回收。

下图中的 `Object 6 ~ Object 10` 之间虽有 Reference 关系，但它们到 GC Roots Unreachable，因此为需要被回收的 Object。

![Reachability Analysis](https://oss.javaguide.cn/github/javaguide/java/jvm/jvm-gc-roots.png)

**哪些 Object 可以作为 GC Roots 呢？**

- JVM Stack（Stack Frame 中的 Local Variable Table）中 Reference 的 Object
- Native Method Stack（Native Method）中 Reference 的 Object
- Method Area 中 Class Static Field Reference 的 Object
- Method Area 中 Constant Reference 的 Object
- 所有被 Intrinsic Lock 持有的 Object
- Java Native Interface (JNI) Reference 的 Object

**Object 可以被回收，就代表一定会被回收吗？**

对于 Override 了 `finalize()` Method 且该 Method 尚未执行过的 Object，HotSpot 在确认 Object Unreachable 后，可能会将对应的终结 Reference 加入待处理 Queue，由 Finalizer Thread Asynchronous 处理。如果 Object 在 `finalize()` Method 中重新与 Reference Chain 上的 Object 建立关联，它可以暂时逃过回收；否则，后续 GC 会再次确认其可回收状态。这个过程通常被概括为“两次标记”，但不代表 Garbage Collector 会同步等待 `finalize()` Method 执行，也不保证该 Method 一定会被调用。

> `Object` Class 中的 `finalize` Method 一直被认为是一个糟糕的设计，成为了 Java 语言的负担，影响了 Java 语言的安全和 GC 的 Performance。`Object.finalize()` 从 JDK 9 起被弃用，JEP 421 又在 JDK 18 中将终结机制标记为待移除。新代码不应依赖它。
>
> 参考：
>
> - [JEP 421: Deprecate Finalization for Removal](https://openjdk.java.net/jeps/421)
> - [是时候忘掉 finalize Method 了](https://mp.weixin.qq.com/s/LW-paZAMD08DP_3-XCUxmg)

### Reference Type 总结

无论是通过 Reference Counting 判断 Object Reference 数量，还是通过 Reachability Analysis 法判断 Object 的 Reference Chain 是否 Reachable，判定 Object 的存活都与“Reference”有关。

JDK1.2 之前，Java 中 Reference 的定义很传统：如果 reference Type 的数据存储的数值代表的是另一块内存的起始 Address，就称这块内存代表一个 Reference。

JDK 1.2 以后，Java 对 Reference 的概念进行了扩充，将 Reference 分为 Strong Reference、Soft Reference、Weak Reference、Phantom Reference 四种（Reference 强度逐渐减弱）。 Strong Reference 就是程序代码中普遍存在的普通 Reference 赋值，Soft Reference、Weak Reference、Phantom Reference 在 JDK 中定义的 Class 分别是 `SoftReference`、`WeakReference`、`PhantomReference`。

![Java Reference Type 总结](https://oss.javaguide.cn/github/javaguide/java/jvm/java-reference-type.png)

**1．Strong Reference（StrongReference）**

Strong Reference 实际上就是程序代码中普遍存在的 Reference 赋值，这是使用最普遍的 Reference，其代码如下

```java
String strongReference = new String("abc");
```

如果一个 Object 仍然可以通过 Strong Reference 访问，那就类似于**必不可少的生活用品**，Garbage Collector 不会回收它。当内存空间不足，Java Virtual Machine 宁愿抛出 `OutOfMemoryError` 错误，使程序 Exception 终止，也不会靠随意回收强 Reachable Object 来解决内存不足问题。

**2．Soft Reference（SoftReference）**

如果一个 Object 只具有 Soft Reference，那就类似于**可有可无的生活用品**。 Soft Reference 代码如下

```java
// --- 示例1 ---
String str = new String("abc");
SoftReference<String> softReference1 = new SoftReference<>(str);
str = null; // 去掉强引用

// --- 示例2 ---
SoftReference<String> softReference2 = new SoftReference<>(new String("def")); // 匿名对象
```

Soft Reference Object 在内存压力较大时可能会被回收，但 JVM 不保证只在内存不足时才清理。唯一强保证是：在抛出 OutOfMemoryError 之前，所有仅被 Soft Reference Reachable 的 Object 一定会被清理。只要 Garbage Collector 没有回收它，该 Object 就可以被程序使用。 Soft Reference 可用来实现内存敏感的 Cache。

Soft Reference 可以和一个 Reference Queue（ReferenceQueue）联合使用。 Garbage Collector 清除 Soft Reference 后，会在同一时间或稍后把已经注册 Reference Queue 的 Soft Reference 加入对应 Queue。 Reference Enqueue 表示 Garbage Collector 已经检测到相应的 Reachability 变化，并不用于证明 Object 占用的内存已经完成物理释放。

**3．Weak Reference（WeakReference）**

如果一个 Object 只具有 Weak Reference，那就类似于**可有可无的生活用品**。 Weak Reference 代码如下：

```java
// --- 示例1 ---
String str = new String("abc");
WeakReference<String> weakReference1 = new WeakReference<>(str);
str = null; //去除强引用

// --- 示例2 ---
WeakReference<String> weakReference2 = new WeakReference<>(new String("abc")); // 匿名对象
```

Weak Reference 与 Soft Reference 的区别在于：只具有 Weak Reference 的 Object 拥有更短暂的 Lifecycle。 Garbage Collector 确定某个 Object 仅弱 Reachable 时，会 Atomic 地清除指向该 Object 的 Weak Reference。不过，清除动作要等到 GC 发生时才会执行，因此不保证 Object 变成弱 Reachable 后会立刻被回收。

Weak Reference 可以和一个 Reference Queue（ReferenceQueue）联合使用。 Garbage Collector 清除 Weak Reference 后，会在同一时间或稍后把已经注册 Reference Queue 的 Weak Reference 加入对应 Queue。

**4．Phantom Reference（PhantomReference）**

“Phantom Reference”顾名思义，就是形同虚设，与其他几种 Reference 都不同，Phantom Reference 不会阻止 Garbage Collector 回收其指向的 Object。 Phantom Reference 代码如下：

```java
// --- 示例1 ---
String str = new String("abc");
ReferenceQueue queue = new ReferenceQueue();
// 创建虚引用，要求必须与一个引用队列关联
PhantomReference phantomReference1 = new PhantomReference(str, queue);
str = null; // 去除强引用

// --- 示例2 ---
PhantomReference phantomReference2 = new PhantomReference(new String("abc"), queue); // 匿名对象
```

**Phantom Reference 主要用于接收 Object Reachability 发生变化的通知，并配合 Reference Queue 安排清理工作**。

**Phantom Reference 与 Soft Reference 和 Weak Reference 的一个区别在于：** Phantom Reference 通常与 Reference Queue（ReferenceQueue）联合使用。 Garbage Collector 确定 Object 进入虚 Reachable 状态后，会清除相关 Phantom Reference，并在同一时间或稍后将已注册 Reference Queue 的 Phantom Reference Enqueue。`PhantomReference.get()` 始终返回 `null`，程序不能通过 Phantom Reference 重新取得 Object；它主要用于在 Object 已无法再被访问后安排清理工作。

特别注意，Soft Reference 主要用于实现内存敏感的缓存，但它不能保证应用不会发生 `OutOfMemoryError`；OOM 还可能由 Heap 以外的资源耗尽等原因引起。

### 如何判断一个 Constant 是废弃 Constant？

String Constant Pool 主要回收的是废弃的 Constant。那么，我们如何判断一个 Constant 是废弃 Constant 呢？

~~**JDK1.7 及之后版本的 JVM 已经将 Runtime Constant Pool 从 Method Area 中移了出来，在 Java Heap（Heap）中开辟了一块区域存放 Runtime Constant Pool。**~~

> **🐛 修正（参见：[issue747](https://github.com/Snailclimb/JavaGuide/issues/747)，[reference](https://blog.csdn.net/q5706503/article/details/84640762)）**：
>
> 1. **JDK1.7 之前 Runtime Constant Pool 逻辑包含 String Constant Pool 存放在 Method Area, 此时 hotspot 虚拟机对 Method Area 的实现为 PermGen**
> 2. **JDK1.7 String Constant Pool 被从 Method Area 拿到了 Heap 中, 这里没有提到 Runtime Constant Pool，也就是说 String Constant Pool 被单独拿到 Heap，Runtime Constant Pool 剩下的东西还在 Method Area, 也就是 hotspot 中的 PermGen**。
> 3. **JDK1.8 hotspot 移除了 PermGen 用 Metaspace 取而代之, 这时候 String Constant Pool 还在 Heap, Runtime Constant Pool 还在 Method Area, 只不过 Method Area 的实现从 PermGen 变成了 Metaspace**

假如在 String Constant Pool 中存在 String "abc"，如果当前没有任何 String Object Reference 该 String Constant 的话，就说明 Constant "abc" 就是废弃 Constant，如果这时发生内存回收的话而且有必要的话，"abc" 就会被系统清理出 Constant Pool 了。

### 如何判断一个 Class 是无用的 Class？

Method Area 主要回收的是无用的 Class，那么如何判断一个 Class 是无用的 Class 的呢？

判定一个 Constant 是否是“废弃 Constant”比较简单，而要判定一个 Class 是否是“无用的 Class”的条件则相对苛刻许多。 Class 需要同时满足下面 3 个条件才能算是 **“无用的 Class”**：

- 该 Class 所有的 Instance 都已经被回收，也就是 Java Heap 中不存在该 Class 的任何 Instance。
- 加载该 Class 的 `ClassLoader` 已经被回收。
- 该 Class 对应的 `java.lang.Class` Object 没有在任何地方被 Reference，无法在任何地方通过 Reflection 访问该 Class 的 Method。

> JNI 场景下要特别小心第 3 个条件：通过 `NewGlobalRef` 创建的 `jclass` 全局 Reference 同样会阻止 Class 被卸载。一个常见的坑是 JNI 层缓存了 Reflection 结果：`jmethodID`/`jfieldID` 只有在 Class 保持已加载状态时才保证有效，因此长期运行的程序通常会为 `jclass` 创建全局 Reference 来保活。这也意味着只要这个全局 Reference 没有释放，对应的 Class 就永远无法卸载（参见 [issue#2908](https://github.com/Snailclimb/JavaGuide/issues/2908)）。

虚拟机可以对满足上述 3 个条件的无用 Class 进行回收，这里说的仅仅是“可以”，而并不是和 Object 一样不使用了就会必然被回收。

## GC Algorithm

### Mark-Sweep Algorithm

Mark-Sweep（Mark-and-Sweep）Algorithm 分为“标记（Mark）”和“清除（Sweep）”阶段：首先标记出所有不需要回收的 Object，在标记完成后统一回收掉所有没有被标记的 Object。

它是最基础的收集 Algorithm，后续的 Algorithm 都是对其不足进行改进得到。这种 GC Algorithm 会带来两个明显的问题：

1. **效率问题**：标记和清除两个过程效率都不高。
2. **空间问题**：Mark-Sweep 后会产生大量不连续的内存碎片。

![Mark-Sweep Algorithm](https://oss.javaguide.cn/github/javaguide/java/jvm/mark-and-sweep-garbage-collection-algorithm.png)

关于具体是标记可回收 Object（Unreachable Object）还是不可回收 Object（Reachable Object），众说纷纭，两种说法其实都没问题，我个人更倾向于是后者。

如果按照前者的理解，整个 Mark-Sweep 过程大致是这样的：

1. 当一个 Object 被创建时，给一个标记位，假设为 0 (false)；
2. 在标记阶段，我们将所有 Reachable Object（或用户可以 Reference 的 Object）的标记位设置为 1 (true)；
3. 扫描阶段清除的就是标记位为 0 (false)的 Object。

### Copying Algorithm

为了解决 Mark-Sweep Algorithm 的效率和内存碎片问题，复制（Copying）收集 Algorithm 出现了。它可以将内存分为大小相同的两块，每次使用其中的一块。当这一块的内存使用完后，就将还存活的 Object 复制到另一块去，然后再把使用的空间一次清理掉。这样就使每次的内存回收都是对内存区间的一半进行回收。

![Copying Algorithm](https://oss.javaguide.cn/github/javaguide/java/jvm/copying-garbage-collection-algorithm.png)

虽然改进了 Mark-Sweep Algorithm，但依然存在下面这些问题：

- **可用内存变小**：可用内存缩小为原来的一半。
- **不适合 Old Generation**：如果存活 Object 数量比较大，复制 Performance 会变得很差。

### Mark-Compact Algorithm

Mark-Compact（Mark-and-Compact）Algorithm 是根据 Old Generation 的特点提出的一种标记 Algorithm，标记过程仍然与“Mark-Sweep”Algorithm 一样，但后续步骤不是直接对可回收 Object 回收，而是让所有存活的 Object 向一端移动，然后直接清理掉端边界以外的内存。

![Mark-Compact Algorithm](https://oss.javaguide.cn/github/javaguide/java/jvm/mark-and-compact-garbage-collection-algorithm.png)

由于多了整理这一步，因此效率也不高，适合 Old Generation 这种 GC 频率不是很高的场景。

### Generational Collection

经典的 Generational Garbage Collector 会根据 Object 存活周期的不同将内存分为几块。一般将 Java Heap 分为 Young Generation 和 Old Generation，这样可以根据各个年代的特点选择合适的 GC Algorithm。需要注意的是，Garbage Collector 并非始终采用 Generational 设计，例如早期的 ZGC 就是非 Generational Collection 器。

比如在 Young Generation 中，每次收集都会有大量 Object 死去，所以可以选择“复制”Algorithm，只需要付出少量 Object 的复制成本就可以完成每次 GC。而 Old Generation 的 Object 存活几率是比较高的，而且没有额外的空间对它进行分配担保，所以我们必须选择“Mark-Sweep”或“Mark-Compact”Algorithm 进行 GC。

**延伸面试问题：** HotSpot 为什么要分为 Young Generation 和 Old Generation？

根据上面的对 Generational Collection 的介绍回答。

## Garbage Collector

**如果说收集 Algorithm 是内存回收的 Method 论，那么 Garbage Collector 就是内存回收的具体实现。**

虽然我们对各个收集器进行比较，但并非要挑选出一个最好的收集器。因为直到现在为止还没有最好的 Garbage Collector 出现，更加没有万能的 Garbage Collector，**我们能做的就是根据具体应用场景选择适合自己的 Garbage Collector**。试想一下：如果有一种四海之内、任何场景下都适用的完美收集器存在，那么我们的 HotSpot 虚拟机就不会实现那么多不同的 Garbage Collector 了。

Oracle/OpenJDK HotSpot 在典型 Server VM 环境中的默认 Garbage Collector（实际选择还会受平台和运行环境影响，可使用 `java -XX:+PrintCommandLineFlags -version` 命令查看）：

- JDK 8: Parallel Scavenge（Young Generation）+ Parallel Old（Old Generation）
- JDK 9 及之后：G1

### Serial 收集器

Serial 收集器是最基本、历史最悠久的 Garbage Collector 了。大家看名字就知道这个收集器是一个 Single Thread 收集器了。它的 **“Single Thread”** 的意义不仅仅意味着它只会使用一条 GC Thread 去完成 GC 工作，更重要的是它在进行 GC 工作的时候必须暂停其他所有的 Worker Thread（**"Stop The World"**），直到它收集结束。

**Young Generation 采用 Mark-Copy Algorithm，Old Generation 采用 Mark-Compact Algorithm。**

![Serial 收集器](https://oss.javaguide.cn/github/javaguide/java/jvm/serial-garbage-collector.png)

虚拟机的设计者们当然知道 Stop The World 带来的不良用户体验，所以在后续的 Garbage Collector 设计中 Pause Time 在不断缩短（仍然还有 Pause，寻找最优秀的 Garbage Collector 的过程仍然在继续）。

但是 Serial 收集器有没有优于其他 Garbage Collector 的地方呢？当然有，它**简单而高效（与其他收集器的 Single Thread 相比）**。Serial 收集器由于没有 Thread 交互的 Overhead，自然可以获得很高的 Single Thread 收集效率。Serial 收集器对于运行在 Client 模式下的虚拟机来说是个不错的选择。

### ParNew 收集器

ParNew 收集器其实就是 Serial 收集器的 Multithreading 版本，除了使用 Multithreading 进行 GC 外，其余行为（控制 Parameter、收集 Algorithm、回收策略等等）和 Serial 收集器完全一样。

ParNew 只负责 Young Generation，采用 Mark-Copy Algorithm；它通常与负责 Old Generation 的 CMS 收集器配合使用。

![ParNew 收集器 ](https://oss.javaguide.cn/github/javaguide/java/jvm/parnew-garbage-collector.png)

在 CMS 仍受支持的 JDK 版本中，ParNew 是 CMS 的 Young Generation 搭档；CMS 已在 JDK 14 中移除，因此这组搭配只适用于旧版本 HotSpot。

**Parallelism 和 Concurrency 概念补充：**

- **Parallelism（Parallel）**：指多条 GC Thread Parallelism 工作，但此时 User Thread 仍然处于等待状态。

- **Concurrency（Concurrent）**：指 User Thread 与 GC Thread 同时执行（但不一定是 Parallelism，可能会交替执行），用户程序在继续运行，而 Garbage Collector 运行在另一个 CPU 上。

### Parallel Scavenge 收集器

Parallel Scavenge 收集器也是使用 Mark-Copy Algorithm 的 Multithreading 收集器，它看上去几乎和 ParNew 都一样。 **那么它有什么特别之处呢？**

```bash
-XX:+UseParallelGC

    使用 Parallel 收集器（JDK 8 中默认搭配 Parallel Old）

-XX:+UseParallelOldGC

    使用 Parallel 收集器+ 老年代并行
```

Parallel Scavenge 收集器关注点是 Throughput（高效率的利用 CPU）。CMS 等 Garbage Collector 的关注点更多的是 User Thread 的 Pause Time（提高用户体验）。所谓 Throughput 就是 CPU 中用于运行用户代码的时间与 CPU 总消耗时间的比值。 Parallel Scavenge 收集器提供了很多 Parameter 供用户找到最合适的 Pause Time 或最大 Throughput，如果对于收集器运作不太了解，手工优化存在困难的时候，使用 Parallel Scavenge 收集器配合自适应调节策略，把内存管理优化交给虚拟机去完成也是一个不错的选择。

**Young Generation 采用 Mark-Copy Algorithm，Old Generation 采用 Mark-Compact Algorithm。**

![Parallel Old收集器运行示意图](https://oss.javaguide.cn/github/javaguide/java/jvm/parallel-scavenge-garbage-collector.png)

**这是 JDK1.8 默认收集器**

使用 `java -XX:+PrintCommandLineFlags -version` 命令查看

```bash
-XX:InitialHeapSize=262921408 -XX:MaxHeapSize=4206742528 -XX:+PrintCommandLineFlags -XX:+UseCompressedClassPointers -XX:+UseCompressedOops -XX:+UseParallelGC
java version "1.8.0_211"
Java(TM) SE Runtime Environment (build 1.8.0_211-b12)
Java HotSpot(TM) 64-Bit Server VM (build 25.211-b12, mixed mode)
```

JDK1.8 默认使用的是 Parallel Scavenge + Parallel Old，如果指定了-XX:+UseParallelGC Parameter，则默认指定了-XX:+UseParallelOldGC，可以使用-XX:-UseParallelOldGC 来禁用该功能

### Serial Old 收集器

**Serial 收集器的 Old Generation 版本**，它同样是一个 Single Thread 收集器。它主要有两大用途：一种用途是在 JDK1.5 以及以前的版本中与 Parallel Scavenge 收集器搭配使用，另一种用途是作为 CMS 收集器的后备方案。

![Serial 收集器](https://oss.javaguide.cn/github/javaguide/java/jvm/serial-garbage-collector.png)

### Parallel Old 收集器

**Parallel Scavenge 收集器的 Old Generation 版本**。使用 Multithreading 和“Mark-Compact”Algorithm。在注重 Throughput 以及 CPU 资源的场合，都可以优先考虑 Parallel Scavenge 收集器和 Parallel Old 收集器。

![Parallel Old收集器运行示意图](https://oss.javaguide.cn/github/javaguide/java/jvm/parallel-scavenge-garbage-collector.png)

### CMS 收集器

**CMS（Concurrent Mark Sweep）收集器是一种以获取最短回收 Pause Time 为目标的收集器。它非常符合在注重用户体验的应用上使用。**

**CMS（Concurrent Mark Sweep）收集器是 HotSpot 虚拟机第一款真正意义上的 Concurrent Collector，它第一次实现了让 GC Thread 与 User Thread（基本上）同时工作。**

从名字中的**Mark Sweep**这两个词可以看出，CMS 收集器是一种 **“Mark-Sweep”Algorithm**实现的，它的运作过程相比于前面几种 Garbage Collector 来说更加复杂一些。整个过程分为四个步骤：

- **Initial Mark：** 短暂 Pause，标记直接与 root 相连的 Object（根 Object）；
- **Concurrent Mark：** 同时开启 GC 和 User Thread，用一个闭包结构去记录 Reachable Object。但在这个阶段结束，这个闭包结构并不能保证包含当前所有的 Reachable Object。因为 User Thread 可能会不断的更新 Reference 域，所以 GC Thread 无法保证 Reachability Analysis 的实时性。所以这个 Algorithm 里会跟踪记录这些发生 Reference 更新的地方。
- **Remark：** Remark 阶段就是为了修正 Concurrent Mark 期间因为用户程序继续运行而导致标记产生变动的那一部分 Object 的标记记录，这个阶段的 Pause Time 一般会比 Initial Mark 阶段的时间稍长，远远比 Concurrent Mark 阶段时间短
- **Concurrency 清除：** 开启 User Thread，同时 GC Thread 开始对未标记的区域做清扫。

![CMS 收集器](https://oss.javaguide.cn/github/javaguide/java/jvm/cms-garbage-collector.png)

从它的名字就可以看出它是一款优秀的 Garbage Collector，主要优点：**Concurrency 收集、低 Pause**。但是它有下面三个明显的缺点：

- **对 CPU 资源敏感；**
- **无法处理 Floating Garbage；**
- **它使用的回收 Algorithm-“Mark-Sweep”Algorithm 会导致收集结束时会有大量空间碎片产生。**

**CMS Garbage Collector 在 Java 9 中已经被标记为过时(deprecated)，并在 Java 14 中被移除。**

### G1 收集器

**G1 (Garbage-First) 是一款面向服务器的 Garbage Collector，主要针对配备多颗处理器及大 Capacity 内存的机器. 以极高概率满足 GC Pause Time 要求的同时，还具备高 Throughput Performance 特征。**

被视为 JDK1.7 中 HotSpot 虚拟机的一个重要进化特征。它具备以下特点：

- **Parallelism 与 Concurrency**：G1 能充分利用 CPU、多核环境下的硬件优势，使用多个 CPU（CPU 或者 CPU 核心）来缩短 Stop-The-World Pause Time。部分其他收集器原本需要 Pause Java Thread 执行的 GC 动作，G1 收集器仍然可以通过 Concurrency 的方式让 java 程序继续执行。
- **Generational Collection**：虽然 G1 可以不需要其他收集器配合就能独立管理整个 GC Heap，但是还是保留了 Generational 的概念。
- **空间整合**：与 CMS 的“Mark-Sweep”Algorithm 不同，G1 从整体来看是基于“Mark-Compact”Algorithm 实现的收集器；从局部上来看是基于“Mark-Copy”Algorithm 实现的。
- **可预测的 Pause**：这是 G1 相对于 CMS 的另一个大优势，降低 Pause Time 是 G1 和 CMS 共同的关注点。G1 会根据用户设置的 Pause Time 目标建立预测模型并选择回收 Collection，但该目标是软目标，并不保证每次 Pause 都不超过指定值。

G1 收集器的运作大致分为以下几个步骤：

- **Initial Mark**： 短暂 Pause（Stop-The-World，Stop-The-World (STW)），标记从 GC Roots 可 Direct Reference 的 Object，即标记所有直接 Reachable 的活跃 Object
- **Concurrent Mark**：与应用 Concurrency 运行，标记所有 Reachable Object。 这一阶段可能持续较长时间，取决于 Heap 的大小和 Object 的数量。
- **Final Mark**： 短暂 Pause（STW），处理 Concurrent Mark 阶段结束后残留的少量未处理的 Reference 变更。
- **筛选回收**：根据标记结果，选择回收价值高的区域，复制存活 Object 到新区域，回收旧区域内存。这一阶段包含一个或多个 Pause（STW），具体取决于回收的复杂度。

![G1 收集器](https://oss.javaguide.cn/github/javaguide/java/jvm/g1-garbage-collector.png)

**G1 收集器在后台维护了一个优先列表，每次根据允许的收集时间，优先选择回收价值最大的 Region（这也就是它的名字 Garbage-First 的由来）**。这种使用 Region 划分内存空间以及有优先级的区域回收方式，保证了 G1 收集器在有限时间内可以尽可能高的收集效率（把内存化整为零）。

**从 JDK9 开始，G1 Garbage Collector 成为了默认的 Garbage Collector。**

### ZGC 收集器

ZGC 是以 Low Latency 为目标的 Garbage Collector。它将标记、Object 转移等主要工作与应用 Thread Concurrency 执行，通过染色 Pointer 和屏障机制保证 Object 移动后仍能被正确访问。它仍然有 STW 阶段，但设计目标是让暂停保持很短，且不随 Heap Size、存活 Object 数量或 Thread Count 明显增长。

这里需要区分不同 JDK 版本。早期 ZGC 的 Thread Stack 处理仍会影响 Pause Time；JDK 16 的 [JEP 376](https://openjdk.org/jeps/376) 将 Thread Stack 处理等工作移到了 Concurrency 阶段，因此介绍 JDK 17 ZGC 时，不应继续套用早期版本的暂停模型。

#### ZGC 的版本与启用方式

| JDK 版本 | ZGC 的变化 | 启用 Parameter |
| ---------- | ------------------------------------------------------------------------- | ---------------------------------------------- |
| JDK 11～14 | 以实验特性引入（[JEP 333](https://openjdk.org/jeps/333)） | `-XX:+UnlockExperimentalVMOptions -XX:+UseZGC` |
| JDK 15～20 | 已成为正式特性，采用非 Generational 模式（[JEP 377](https://openjdk.org/jeps/377)） | `-XX:+UseZGC` |
| JDK 21、22 | 增加 Generational 模式，默认仍为非 Generational 模式 | Generational 模式使用 `-XX:+UseZGC -XX:+ZGenerational` |
| JDK 23 | 选择 ZGC 后，默认使用 Generational 模式 | `-XX:+UseZGC` |
| JDK 24 起 | 移除非 Generational 模式 | `-XX:+UseZGC` |

**ZGC 默认采用 Generational 模式，不代表 JVM 默认使用 ZGC。** 在典型 Server-class 环境下，HotSpot 默认仍选择 G1，使用 ZGC 需要显式配置。例如，在 JDK 17 上运行：

```bash
java -XX:+UseZGC -jar app.jar
```

JDK 17 不支持 `-XX:+ZGenerational`，也不能把 Generational ZGC 的调优经验直接套过来。 Generational 模式的演进可参考 [JEP 439](https://openjdk.org/jeps/439)、[JEP 474](https://openjdk.org/jeps/474) 和 [JEP 490](https://openjdk.org/jeps/490)。

#### Pause Time 很短，Interface 响应就一定更快吗？

不一定。GC 暂停只是请求耗时的一部分。如果慢请求主要来自 Database、Lock Contention、下游服务或 CPU 饱和，换成 ZGC 后，Interface 的 P99 延迟可能变化不大。 Concurrency GC 还会消耗 CPU；在 CPU 配额紧张的服务中，这部分竞争可能影响 Throughput 和请求延迟。

此外，**低 STW 暂停不等于应用 Thread 永远不会因内存不足而等待**。如果 Object 分配过快、Heap Space 不足，或者 Concurrency 回收跟不上分配速度，ZGC 可能出现 Allocation Stall（分配 Pause）。 Heap Capacity 除了容纳存活 Object，还要为 Concurrency 回收期间的新分配预留空间。

评估收集器的实际收益时，建议先在相同 JDK 上比较 G1 与 ZGC，再单独评估 JDK 升级的收益，避免把版本升级、代码变化和收集器切换的效果混在一起。灰度期间同时观察：

- **业务 Metric**：相同负载下的 Throughput、P99/P999 延迟、Timeout 率和错误率。
- **GC Metric**：暂停分布、回收周期、分配速率、回收后的存活量，以及是否出现分配 Pause。
- **资源 Metric**：CPU 使用率与 Container Rate Limiting、Process 内存、Off-heap Memory 和峰值负载下的余量。

Parameter 配置与常见误区见 [JVM Parameter 详解中的 JDK 17 ZGC Parameter](./jvm-parameters-intro.md#jdk-17-zgc-参数)。生产切换前，还应保留经过验证的原收集器配置和应用版本，明确触发回退的业务 Metric。

关于 ZGC 收集器的详细介绍推荐看看这几篇文章：

- [从历代 GC Algorithm 角度剖析 ZGC - 京东技术](https://mp.weixin.qq.com/s/ExkB40cq1_Z0ooDzXn7CVw)
- [新一代 Garbage Collector ZGC 的探索与实践 - 美团技术团队](https://tech.meituan.com/2020/08/06/ZGC-in-Meituan.html)
- [极致八股文之 JVM Garbage Collector G1&ZGC 详解 - 阿里云开发者](https://mp.weixin.qq.com/s/Ywj3XMws0IIK-kiUllN87Q)

### Shenandoah 收集器

与 ZGC 类似，Shenandoah 也是面向 Low Latency 的收集器，由 Red Hat 主导开发，在 Java 12 中通过 [JEP 189](https://openjdk.org/jeps/189) 以实验特性引入，Java 15 起成为正式特性（[JEP 379](https://openjdk.org/jeps/379)）。

Shenandoah 的核心思路是**Concurrency 整理**：大部分 Heap 整理工作与应用 Thread 同时进行，Pause Time 可以控制在亚毫秒级，且不受 Heap Size 影响。它主要通过**转发 Pointer（Brooks Pointer）**和**Read Barrier**实现 Concurrency 整理时 Object 移动对应用 Thread 的透明。

需要注意的是，早期 Shenandoah 和早期 ZGC 一样是非 Generational Collection 器，Throughput 上有一定代价。 Generational Shenandoah 仍在演进中（如 [JEP 535](https://openjdk.org/jeps/535)、[JEP 521](https://openjdk.org/jeps/521)），值得持续关注。

你可以通过下面的 Parameter 启用 Shenandoah：

```bash
java -XX:+UseShenandoahGC className
```

> 注意：Shenandoah 不在 Oracle JDK 的默认支持列表中，主要随 OpenJDK（如 Red Hat、Amazon Corretto 等发行版）提供，使用前需要确认所用 JDK 发行版是否包含并默认启用了 Shenandoah（`-XX:+PrintFlagsFinal -version | grep UseShenandoahGC`）。

## 参考

- 《深入理解 Java Virtual Machine：JVM 高级特性与最佳实践（第二版》
- The Java® Virtual Machine Specification - Java SE 8 Edition：<https://docs.oracle.com/javase/specs/jvms/se8/html/index.html>

<!-- @include: @article-footer.snippet.md -->
