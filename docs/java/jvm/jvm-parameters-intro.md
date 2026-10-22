---
title: 最重要的Java Virtual Machine (JVM) Parameter 总结
description: 总结常用 JVM Parameter 与配置 Method，结合内存与 Garbage Collection (GC) 调优的实践建议。
category: Java
tag:
  - JVM
head:
  - - meta
    - name: keywords
      content: JVM Parameter,Heap Size,Stack 大小,GC 设置,Performance Tuning,XX Parameter
---

> 本文由 JavaGuide 翻译自 [https://www.baeldung.com/jvm-parameters](https://www.baeldung.com/jvm-parameters)，并对文章进行了大量的完善补充。
> 文档 Parameter [https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html)
>
> JDK 版本：1.8 为主，也会补充新版本常用 Parameter

在本篇文章中，我们将一起掌握 Java Virtual Machine（JVM）中最常用的一些 Parameter 配置，帮助你更好地理解和调优 Java 应用的运行环境。

## Heap Memory 相关

> Java Heap 是 JVM 所管理的内存中最大的一块区域，**所有 Thread Shared**，在虚拟机启动时创建。**此 Memory Area 的唯一目的就是存放 Object Instance，几乎所有的 Object Instance 以及 Array 都要在 Heap 上分配内存。**

![Memory Area 常见配置 Parameter](./pictures/内存区域常见配置参数.png)

### 设置 Heap Memory 大小（-Xms 和 -Xmx）

根据应用程序的实际需求设置初始和最大 Heap Memory 大小，是 Performance Tuning 中最常见的实践之一。将两者设为相同值，可以减少运行时调整 Heap Capacity 的 Overhead；如果希望低负载时归还未使用的 Heap Memory，则需要保留伸缩空间。例如，ZGC 在 `-Xms` 等于 `-Xmx` 时无法通过 Uncommit 归还 Heap Memory，应根据延迟目标和内存成本选择。

使用以下 Parameter 进行设置：

```bash
-Xms<heap size>[unit]  # 设置 JVM 初始堆大小
-Xmx<heap size>[unit]  # 设置 JVM 最大堆大小
```

- `<heap size>`: 指定内存的具体数值。
- `[unit]`: 指定内存的单位，如 g (GB)、m (MB)、k (KB)。

**示例：** 将 JVM 的初始 Heap 和最大 Heap 都设置为 4GB：

```bash
-Xms4G -Xmx4G
```

### 设置 Young Generation 内存大小 (Young Generation)

根据[Oracle 官方文档](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/sizing.html)，在 Heap 总可用内存配置完成之后，第二大影响因素是 `Young Generation` 在 Heap Memory 所占的比例。 Young Generation 的默认大小会受 JVM 实现、平台、Garbage Collector、Heap Size 和自适应策略影响，并不存在适用于所有环境的固定“最小 1310 MB”；`NewSize` 和 `MaxNewSize` 分别用于约束 Young Generation 大小的下限和上限。

对于支持固定 Young Generation 大小 Parameter 的 Generational Collection 器，可以通过以下两种方式设置 Young Generation 内存大小：

**1.通过 `-XX:NewSize` 和 `-XX:MaxNewSize` 指定**

```bash
-XX:NewSize=<young size>[unit]    # 设置新生代初始大小
-XX:MaxNewSize=<young size>[unit] # 设置新生代最大大小
```

**示例：** 设置 Young Generation 最小 512MB，最大 1024MB：

```bash
-XX:NewSize=512m -XX:MaxNewSize=1024m
```

**2.通过 `-Xmn<young size>[unit]` 指定**

**示例：** 将 Young Generation 大小固定为 512MB：

```bash
-Xmn512m
```

显式设置 Young Generation 大小会限制 Garbage Collector 的自适应调整能力。[Oracle 官方文档](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html#extra-options-for-java)明确建议不要为 G1 设置 `-Xmn`；是否需要调整以及如何调整，应结合具体收集器和 GC Log 判断。

GC 调优策略中很重要的一条经验总结是这样说的：

> 尽量让新创建的 Object 在 Young Generation 分配内存并被回收，因为 Minor GC 的成本通常远低于 Full GC。通过分析 GC Log，判断 Young Generation 空间分配是否合理。如果大量新 Object 过早进入 Old Generation（Promotion），可以适当通过 `-Xmn` 或 -`XX:NewSize/-XX:MaxNewSize` 调整 Young Generation 大小，目标是最大限度地减少 Object 直接进入 Old Generation 的情况。

另外，你还可以通过 **`-XX:NewRatio=<int>`** Parameter 来设置**Old Generation 与整个 Young Generation（包括 Eden 和两个 Survivor 区）的内存大小比例**。

例如，`-XX:NewRatio=2` 表示 Old Generation : Young Generation = 2 : 1，即 Young Generation 占整个 Heap Size 的 1/3。默认值会受 JVM、收集器和平台影响。

```bash
-XX:NewRatio=2
```

### 设置 Permanent Generation (PermGen)/Metaspace 大小 (PermGen/Metaspace)

**从 Java 8 开始，Class Metadata 改用 Native Memory。如果没有通过 `-XX:MaxMetaspaceSize` 设置上限，持续增长的 Class Metadata 可能消耗大量 Native Memory；PermGen 则受 `-XX:MaxPermSize` 上限约束。**

JDK 1.8 之前 PermGen 还没被彻底移除的时候通常通过下面这些 Parameter 来调节 Method Area 大小

```bash
-XX:PermSize=N #方法区 (永久代) 初始大小
-XX:MaxPermSize=N #方法区 (永久代) 最大大小,超过这个值将会抛出 OutOfMemoryError 异常:java.lang.OutOfMemoryError: PermGen
```

相对而言，GC 行为在这个区域是比较少出现的，但并非数据进入 Method Area 后就“永久存在”了。

**JDK 1.8 的时候，Method Area（HotSpot 的 PermGen）被彻底移除了（JDK1.7 就已经开始了），取而代之是 Metaspace，Metaspace 使用的是 Native Memory。**

下面是一些常用 Parameter：

```bash
-XX:MetaspaceSize=N #设置 Metaspace 的初始大小（是一个常见的误区，后面会解释）
-XX:MaxMetaspaceSize=N #设置 Metaspace 的最大大小
```

**🐛 修正（参见：[issue#1947](https://github.com/Snailclimb/JavaGuide/issues/1947)）**：

**1、`-XX:MetaspaceSize` 并非初始 Capacity：** Metaspace 的初始 Capacity 并不是 `-XX:MetaspaceSize` 设置，无论 `-XX:MetaspaceSize` 配置什么值，对于 64 位 JVM，Metaspace 的初始 Capacity 通常是一个固定的较小值（Oracle 文档提到约 12MB 到 20MB 之间，实际观察约 20.8MB）。

可以参考 Oracle 官方文档 [Other Considerations](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/considerations.html) 中提到的：

> Specify a higher value for the option MetaspaceSize to avoid early garbage collections induced for class metadata. The amount of class metadata allocated for an application is application-dependent and general guidelines do not exist for the selection of MetaspaceSize. The default size of MetaspaceSize is platform-dependent and ranges from 12 MB to about 20 MB.
>
> MetaspaceSize 的默认大小取决于平台，范围从 12 MB 到大约 20 MB。

另外，还可以看一下这个试验：[JVM Parameter MetaspaceSize 的误解](https://mp.weixin.qq.com/s/jqfppqqd98DfAJHZhFbmxA)。

**2、Resize 与 Metadata GC：** 当 Metaspace 的已提交空间达到 `-XX:MetaspaceSize` 对应的高水位 Threshold 时，JVM 会触发一次 GC 以尝试卸载 Class、释放 Class Metadata。在此之后，JVM 会根据释放效果动态调高或调低下一次触发 GC 的 Threshold；具体采用哪 Class 回收周期取决于 Garbage Collector 和 JDK 版本，不能一概称为 Full GC。垃圾搜集器内部是根据 Variable `_capacity_until_GC` 来判断 Metaspace 区域是否达到 Threshold 的，Initialization 代码如下所示：

```c
void MetaspaceGC::initialize() {
  // Set the high-water mark to MaxMetapaceSize during VM initialization since
  // we can't do a GC during initialization.
  _capacity_until_GC = MaxMetaspaceSize;
}
```

**3、`-XX:MaxMetaspaceSize` 的作用：**如果不显式设置 `-XX:MaxMetaspaceSize`，Metaspace 默认没有固定上限，持续增长的 Class Metadata 可能消耗大量 Native Memory。是否设置该 Parameter 以及设置多大，应结合 Class Metadata 使用情况和 Process 的 Native Memory 预算决定。上限过小会增加 Metadata GC 的频率，也可能提前触发 `OutOfMemoryError: Metaspace`，因此不存在适用于所有应用的推荐值。

相关阅读：[issue 更正：MaxMetaspaceSize 如果不指定大小的话，不会耗尽内存 #1204](https://github.com/Snailclimb/JavaGuide/issues/1204)。

## GC 相关

### 选择 Garbage Collector

选择合适的 Garbage Collector（Garbage Collector, GC）对于应用的 Throughput 和响应延迟至关重要。关于 GC Algorithm 和收集器的详细介绍，可以看笔者写的这篇：[JVM GC 详解（重点）](https://javaguide.cn/java/jvm/jvm-garbage-collection.html)。

JVM 提供了多种 GC 实现，适用于不同的场景：

- **Serial GC（Serial Garbage Collector）:** Single Thread 执行 GC，适用于客户端模式或单核 CPU 环境。 Parameter：`-XX:+UseSerialGC`。
- **Parallel GC（Parallelism Garbage Collector）:** Multithreading 执行 Young Generation 和 Old Generation GC，关注 Throughput，是 JDK 8 Server VM 的默认 GC；在 JDK 8 中启用 `-XX:+UseParallelGC` 时默认搭配 Parallel Old。 Parameter：`-XX:+UseParallelGC`。
- **CMS GC（Concurrent Mark Sweep Concurrency Mark-Sweep 收集器）:** 以获取最短回收 Pause Time 为目标，大部分 GC 阶段可与 User Thread Concurrency 执行。适用于对响应时间要求高的应用。在 JDK 9 中被标记为弃用，JDK 14 中被移除。 Parameter：`-XX:+UseConcMarkSweepGC`。
- **G1 GC (Garbage-First Garbage Collector):** JDK 9 及之后 HotSpot 在典型 Server-class 机器上的默认 GC；其他环境的默认选择可能不同。它将 Heap 划分为多个 Region，兼顾 Throughput 和 Pause Time，尝试满足用户设置的 Pause Time 目标。 Parameter：`-XX:+UseG1GC`。
- **ZGC:** Low Latency GC，需要较新版本的 JDK 支持。 Parameter：`-XX:+UseZGC`。
- **Shenandoah GC:** 另一款低 Pause 收集器，是否可用取决于具体 JDK 发行版。 Parameter：`-XX:+UseShenandoahGC`。

### JDK 17 ZGC Parameter

JDK 17 的 ZGC 是非 Generational Collection 器，使用 `-XX:+UseZGC` 启用。调优时先根据实际负载确定 Heap 和 CPU 预算，再根据 GC Log 调整 Parameter，不要直接复制其他服务的整套配置。

| Parameter | 含义与使用时需要注意的地方 |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `-Xmx`、`-Xms` | 最大 Heap 与初始/最小 Heap Capacity。 Heap 需要容纳存活 Object，并为 Concurrency 回收期间的分配预留空间；`-Xmx` 也不是整个 Java Process 的内存上限。 |
| `-XX:ConcGCThreads` | Concurrency GC Thread Count。过少可能回收不及时，过多会与 Business Thread 争抢 CPU。先使用 JVM 的自适应选择，再结合分配 Pause、CPU 配额和负载验证是否需要手动设置。 |
| `-XX:ZAllocationSpikeTolerance` | 对分配速率突增的容忍系数，JDK 17 默认值为 `2.0`，用于影响回收时机的预测。它不是 Heap Resize 比例，也不能代替足够的内存余量。 |
| `-XX:ZCollectionInterval` | GC 周期的最大间隔，单位为秒。默认值 `0` 表示不通过这个时间间隔触发 GC，**不是禁用 GC**。不要把它理解为两次 GC 之间必须等待的最短时间。 |
| `-XX:+ZUncommit`、`-XX:ZUncommitDelay` | 允许归还未使用的 Heap Memory，JDK 17 默认开启，默认延迟为 `300` 秒。归还不会使 Heap 低于 `-Xms`；设置 `-Xms` 等于 `-Xmx` 时，这项机制实际上不起作用。 |

以上语义可对照 [JDK 17 `java` 命令文档](https://docs.oracle.com/en/java/javase/17/docs/specs/man/java.html) 和 [OpenJDK 17 ZGC Parameter 定义](https://github.com/openjdk/jdk17u/blob/master/src/hotspot/share/gc/z/z_globals.hpp)。不同 JDK 版本的 Parameter 可能变化，尤其不要给 JDK 17 添加 Generational ZGC Parameter `-XX:+ZGenerational`。

例如，下面的命令同时记录 GC 与 Safepoint Log；Heap Size 需要另外按应用的资源预算设置：

```bash
java -XX:+UseZGC \
  '-Xlog:gc*,safepoint:file=gc.log:time,uptime,level,tags:filecount=5,filesize=20M' \
  -jar app.jar
```

如果 Log 中出现 Allocation Stall，应结合分配速率、存活量、可用 Heap Space 和 Concurrency GC 的 CPU 资源定位原因。单纯缩短定时回收间隔不一定有效，还可能增加 CPU Overhead。 Container 的内存预算也要覆盖 Metaspace、Thread Stack、Direct Memory 和 JVM 本地 Overhead，不能只按 `-Xmx` 设置 Container 上限。

### GC Log 记录

在生产环境或进行 GC 问题排查时，**务必开启 GC Log 记录**。详细的 GC Log 是分析和解决 GC 问题的关键依据。

以下是一些 JDK 8 的 GC Log Parameter：

```bash
# --- 推荐的基础配置 ---
# 打印详细 GC 信息
-XX:+PrintGCDetails
# 打印 GC 发生的时间戳 (相对于 JVM 启动时间)
# -XX:+PrintGCTimeStamps
# 打印 GC 发生的日期和时间 (更常用)
-XX:+PrintGCDateStamps
# 指定 GC 日志文件的输出路径，%t 可以输出日期时间戳
-Xloggc:/path/to/gc-%t.log

# --- 推荐的进阶配置 ---
# 打印对象年龄分布 (有助于判断对象晋升老年代的情况)
-XX:+PrintTenuringDistribution
# 在 GC 前后打印堆信息
-XX:+PrintHeapAtGC
# 打印各种类型引用 (强/软/弱/虚) 的处理信息
-XX:+PrintReferenceGC
# 打印应用暂停时间 (Stop-The-World, STW)
-XX:+PrintGCApplicationStoppedTime

# --- GC 日志文件滚动配置 ---
# 启用 GC 日志文件滚动
-XX:+UseGCLogFileRotation
# 设置滚动日志文件的数量 (例如，保留最近 14 个)
-XX:NumberOfGCLogFiles=14
# 设置每个日志文件的最大大小 (例如，50MB)
-XX:GCLogFileSize=50M

# --- 可选的辅助诊断配置 ---
# 打印安全点 (Safepoint) 统计信息 (有助于分析 STW 原因)
# -XX:+PrintSafepointStatistics
# -XX:PrintSafepointStatisticsCount=1
```

JDK 9 及之后应使用统一 JVM Log 框架 `-Xlog`。例如，下面的配置记录详细 GC 信息并启用按大小滚动：

```bash
-Xlog:gc*:file=/path/to/gc-%t.log:time,uptime,level,tags:filecount=14,filesize=50M
```

旧 Parameter 并非都能继续使用：部分 Parameter 会被映射、弃用或直接不再识别。例如 `PrintGCDetails` 对应 `-Xlog:gc*`，`PrintTenuringDistribution` 对应 `-Xlog:gc+age*=debug`，`PrintGCApplicationStoppedTime` 对应 `-Xlog:safepoint`。应以目标 JDK 的 `java` 命令文档和 `java -Xlog:help` 输出为准。

## 处理 Out of Memory (OOM)

对于大型应用程序来说，面对内存不足错误是非常常见的，这反过来会导致应用程序崩溃。这是一个非常关键的场景，很难通过复制来解决这个问题。

这就是为什么 JVM 提供了一些 Parameter，这些 Parameter 将 Heap Memory Dump 到一个物理文件中，以后可以用来查找泄漏:

```bash
# Java 堆耗尽并抛出 OOME 时生成堆转储文件
-XX:+HeapDumpOnOutOfMemoryError

# 指定堆转储文件或目录。若指定目录，JVM 会使用默认名称 java_pid<pid>.hprof
-XX:HeapDumpPath=/data/dumps/

# (可选) 在发生 OOM 时执行指定的命令或脚本
# 例如，发送告警通知或尝试重启服务（需谨慎使用）
# -XX:OnOutOfMemoryError="<command> <args>"
# 示例：-XX:OnOutOfMemoryError="sh /path/to/notify.sh"

# (可选) 启用 GC 开销限制检查
# 如果 GC 时间占总时间比例过高（默认 98%）且回收效果甚微（默认小于 2% 堆内存），
# 会提前抛出 OOM，防止应用长时间卡死在 GC 中。
-XX:+UseGCOverheadLimit
```

## 其他常用 Parameter

- `-server`: 明确启用 Server 模式的 HotSpot VM。（在 64 位 JVM 上通常是默认值）。
- `-XX:+UseStringDeduplication`: (JDK 8u20+) 尝试识别内容相同的 String Object 并 Shared 其底层 Character 数据 Array，以减少内存占用。JDK 8 中底层 Array 是 `char[]`，启用 Compact Strings 的现代 JDK 通常是 `byte[]`；该选项还要求使用支持 String 去重的收集器，例如 G1。
- `-XX:SurvivorRatio=<ratio>`: 设置 Eden 区与单个 Survivor 区的大小比例。例如 `-XX:SurvivorRatio=8` 表示 Eden:Survivor = 8:1。
- `-XX:MaxTenuringThreshold=<threshold>`: 设置 Object 从 Young Generation Promotion 到 Old Generation 的最大年龄 Threshold（Object 每经历一次 Minor GC 且存活，年龄加 1）。默认值与收集器和 JDK 版本有关，例如 JDK 8 文档中 Parallel GC 的默认值为 15，CMS 的默认值为 6。
- `-XX:+DisableExplicitGC`: 让 JVM 忽略 `System.gc()` 等显式 GC 请求，但 JVM 在需要时仍会自行执行 GC。显式请求并不保证触发 Full GC；是否启用该 Parameter 应结合 Direct Memory 清理、框架行为和所用收集器评估，不能一概而论。
- `-XX:+UseLargePages`:（需要 Operating System 支持） 尝试使用大内存页（如 2MB 而非 4KB），可能提升内存密集型应用的 Performance，但需谨慎测试。
- `-XX:MinHeapFreeRatio=<percent>` / `-XX:MaxHeapFreeRatio=<percent>`: 对支持这组 Parameter 的收集器，控制 GC 后期望的 Heap 空闲比例，参与 Heap Capacity 调整。具体行为取决于收集器，不能用这组 Parameter 代替 ZGC 的 Capacity 与归还策略。

**注意：** 以下 Parameter 在现代 JVM 版本中可能已**弃用、移除或默认开启且无需手动设置**：

- `-XX:+UseLWPSynchronization`: 较旧的同步策略选项，现代 JVM 通常有更优化的实现。
- `-XX:LargePageSizeInBytes`: 通常由 `-XX:+UseLargePages` 自动确定或通过 OS 配置。
- `-XX:+UseStringCache`: 已被移除。
- `-XX:+UseCompressedStrings`: 旧的实验性选项，已经被移除；JDK 9 引入的 Compact Strings 是另一套实现。
- `-XX:+OptimizeStringConcat`: 旧版 HotSpot C2 的 String 拼接优化选项；JDK 9 起 String 拼接主要通过 `invokedynamic` 和 `StringConcatFactory` 实现，不能把二者视为同一个开关。

## 总结

本文为 Java 开发者提供了一份实用的 JVM 常用 Parameter 配置指南，旨在帮助读者理解和优化 Java 应用的 Performance 与稳定性。文章重点强调了以下几个方面：

1. **Heap Memory 配置：** 根据部署环境设置初始与最大 Heap Memory（`-Xms`、`-Xmx`），权衡固定 Heap Capacity 的 Performance 收益和弹性归还内存的需求。 Young Generation 大小是否需要显式设置，应结合 Garbage Collector 和 GC Log 判断；G1 通常不建议设置 `-Xmn`，JDK 17 的非 Generational ZGC 则没有 Young Generation。
2. **Metaspace 管理（Java 8+）：** `-XX:MetaspaceSize` 用于设置触发 Metadata GC 的初始高水位 Threshold，而不是 Metaspace 的初始 Capacity。`-XX:MaxMetaspaceSize` 可以限制 Class Metadata 使用的 Native Memory，但具体上限需要根据应用实际情况确定。
3. **Garbage Collector 选择与 Log：**介绍了不同 GC Algorithm 的适用场景，并强调在生产和测试环境中开启详细 GC Log 对于问题排查的必要性；JDK 8 使用传统 GC Log Parameter，JDK 9 及之后使用 `-Xlog`。
4. **OOM 故障排查：** 说明了如何通过 `-XX:+HeapDumpOnOutOfMemoryError` 等 Parameter 在发生 OOM 时自动生成 Heap Dump 文件，以便进行后续的 Memory Leak 分析。
5. **其他 Parameter：** 简要介绍了如 String 去重等其他有用 Parameter，并指出了部分旧 Parameter 的现状。

具体的问题排查和调优案例，可以参考笔者整理的这篇文章：[JVM 线上问题排查和 Performance Tuning 案例](https://javaguide.cn/java/jvm/jvm-in-action.html)。

<!-- @include: @article-footer.snippet.md -->
