---
title: 2026 最新 Java Virtual Machine (JVM) 面试题总结：Memory Area、Class Loading、Garbage Collection (GC) 与线上排查
category: Java
description: 2026 最新 JVM 面试题总结，覆盖运行时 Memory Area、Object 创建、Class File 与 Class Loading、GC Algorithm 与收集器、JVM Parameter、JDK 诊断工具、Out of Memory (OOM)、频繁 Full GC 和 CPU 飙高等高频考点。
tag:
  - Java
  - JVM
  - 面试题
head:
  - - meta
    - name: keywords
      content: JVM面试题,Java Memory Area,Object 创建,Class Loading,Parent Delegation,GC,GC面试题,G1,ZGC,JVM Parameter,OOM,Full GC,CPU飙高,JVM调优
---

JVM 面试很少停在“Heap 和 Stack 有什么区别”。回答完 Memory Area，面试官通常会继续问 Object 怎样分配、哪些 Object 可以回收、一次 GC 为什么会 Pause，以及线上出现 OOM、频繁 Full GC 或 CPU 飙高时怎样排查。

这篇文章是 JavaGuide JVM 专题的面试复习入口，问题按内存与 Object、Class File 与 Class Loading、GC、Parameter 与诊断工具、线上问题排查五部分整理。每个问题的完整答案放在对应专题文章中。

时间比较紧的话，可以先看 [JVM 常见面试题总结](https://interview.javaguide.cn/java/java-jvm.html)，把答不完整的问题标出来，再回到本文和专题文章补细节。

## 复习 JVM 时先抓住哪些问题？

| 模块 | 需要讲清楚的内容 | 常见追问方向 |
| -------------- | ------------------------------------------------- | ------------------------------------------------------ |
| 内存与 Object | Runtime Data Area 怎样划分，Object 怎样创建、存放和访问 | Heap、Stack、Method Area、Direct Memory、Object Header、Thread-Local Allocation Buffer (TLAB)、OOM |
| Class File 与 Class Loading | `.class` 文件如何进入 JVM，Class 在什么时机完成 Initialization | Constant Pool、加载过程、Class Loader、Parent Delegation、Class 隔离 |
| GC | 怎样判断 Object 存活，内存如何回收，Pause 从哪里产生 | GC Roots、Reference Type、收集 Algorithm、CMS、G1、ZGC、Full GC |
| Parameter 与工具 | Parameter 如何跟着 JDK、收集器和运行现象选择 | `-Xms`、`-Xmx`、GC Log、Heap Dump、jstat、jstack、JFR |
| 线上排查 | 收到 Alert 后怎样保留证据、缩小范围并验证修复 | CPU、Load、OOM、Memory Leak、频繁 GC、Thread Blocking |

大多数 Object Instance 分配在 Heap 中，Active Thread、Static Field 等位置可能持有到 Object 的 Reference；GC 从 GC Roots 出发判断 Object 是否 Reachable，再由具体收集器完成回收。应用出现内存上涨或 Pause 时，还要结合 GC Log、Thread Stack、Heap Dump 和系统 Metric 判断原因，不能看到 Full GC 就直接改 Heap Size。

## JVM Memory Area 与 Object

Runtime Data Area 回答到名称还不够。每个区域由哪些 Thread Shared、存放什么、Lifecycle 怎样、可能抛出什么 Exception，都可能成为下一轮追问。 Method Area 是 JVM 规范定义的逻辑区域，Permanent Generation (PermGen) 和 Metaspace 则是 HotSpot 在不同版本中的实现，回答时不要混成同一个概念。

相关内容：[Java Memory Area 详解](./memory-area.md)

常见面试题：

- JVM Runtime Data Area 包括哪些部分？哪些区域是 Thread 私有的？
- Program Counter、JVM Stack 和 Native Method Stack 分别有什么作用？
- 一个 Java Method 从调用到返回，Stack Frame 发生了什么变化？
- `StackOverflowError` 和 `OutOfMemoryError` 分别可能怎样产生？
- Java Heap 主要存放什么？所有 Object 都一定分配在 Heap 上吗？
- Method Area、PermGen 和 Metaspace 是什么关系？为什么要移除 PermGen？
- Runtime Constant Pool 和 String Constant Pool 有什么区别？它们的位置发生过哪些变化？
- Direct Memory 属于 JVM Runtime Data Area 吗？它为什么也可能 OOM？
- HotSpot 创建一个 Object 要经过哪些步骤？
- Bump-the-Pointer 和 Free List 怎样选择？ Concurrency 分配 Object 时，Compare-And-Swap (CAS) 和 TLAB 分别解决什么问题？
- Object Header、Instance Data 和 Alignment Padding 分别存放什么？
- Handle 访问和 Direct Pointer 访问 Object 有什么区别？HotSpot 主要使用哪一种？

遇到 OOM 题时，先确认耗尽的是 Java Heap、Metaspace、Direct Memory，还是创建 Thread 所需的 Native Memory。只回答“把 `-Xmx` 调大”会漏掉无界 Collection、Class Loader 泄漏、Direct Memory 未释放和 Thread Count 失控等原因。

## Class File 与 Class Loading

Class Loading 题通常从“一个 Class 怎样被加载”开始，随后追问 Initialization 时机、Parent Delegation 以及不同类加载器之间的隔离。这里既有 JVM 规范里的 Lifecycle，也有 HotSpot 和 JDK Class Loader 的具体实现，描述版本差异时要说清使用的 JDK。

相关内容：

- [Class File 结构详解](./class-file-structure.md)
- [Class Loading 详解](./class-loading-process.md)
- [Class Loader 详解](./classloader.md)

常见面试题：

- Class 文件由哪些部分组成？ Magic Number、Version 和 Constant Pool 分别有什么作用？
- Method 的 Bytecode Instruction 保存在 Class 文件的哪个位置？
- 一个 Class 从加载到卸载要经历哪些阶段？
- 加载、验证、准备、解析和 Initialization 分别做了什么？
- Preparation 和 Initialization 给 Static Variable 赋值有什么区别？
- 哪些情况会触发 Class 的 Initialization？访问 Compile-time Constant 会触发吗？
- `<clinit>` 和 Constructor `<init>` 有什么区别？
- Bootstrap Class Loader、Platform Class Loader 和 Application Class Loader 分别加载哪些 Class？JDK 8 的 Extension Class Loader 有什么不同？
- 什么是 Parent Delegation Model？它怎样避免核心 Class 被重复加载或替换？
- Parent Delegation 是怎样执行的？父加载器无法完成加载时会发生什么？
- 哪些场景会打破 Parent Delegation？ Thread Context Class Loader 解决了什么问题？
- 两个 Class 的 Fully Qualified Name 相同，就一定是同一个 Class 吗？
- Custom Class Loader 通常要 Override `findClass()` 还是 `loadClass()`？

Parent Delegation 回答成一条固定的向上查找链还不完整。 Class 的身份由 Class 的 Fully Qualified Name 和加载它的 Class Loader 共同确定；SPI、应用服务器的 Class 隔离、热部署等场景会使用不同的加载方式，目的也不完全相同。

## GC 题要从 Object 分配和存活判断讲到具体收集器。 Throughput、Pause Time 和内存占用之间存在取舍，选择收集器时还要考虑 JDK 版本、Heap Size 和业务对延迟的要求，不能只比较 Algorithm 名称。

相关内容：[JVM GC 详解](./jvm-garbage-collection.md)

常见面试题：

- Young Generation 和 Old Generation 通常怎样划分？ Object 一般怎样分配和 Promotion？
- Large Object 和长期存活 Object 会怎样进入 Old Generation？
- 什么是 Allocation Guarantee？
- Reference Counting 为什么难以解决 Object 之间的 Circular Reference？
- Reachability Analysis 怎样判断 Object 是否存活？哪些 Object 可以作为 GC Roots？
- Strong Reference、Soft Reference、Weak Reference 和 Phantom Reference 有什么区别？
- Mark-Sweep、复制和 Mark-Compact Algorithm 各有什么优缺点？
- Generational Collection 为什么要为 Young Generation 和 Old Generation 选择不同 Algorithm？
- Minor GC、Major GC 和 Full GC 有什么区别？为什么要结合收集器和 Log 理解这些名称？
- Serial、Parallel、CMS、G1 和 ZGC 的目标和适用场景有什么不同？
- CMS 为什么会产生内存碎片和 Floating Garbage？
- G1 怎样通过 Region、回收价值预测和 Mixed GC 控制 Pause？
- ZGC 怎样降低长时间 Pause？低 Pause 收集器会付出哪些代价？
- 哪些情况可能触发 Full GC？频繁 Full GC 应该从哪些数据开始查？

GC Log 中的事件名称、内存分区和 Parameter 会随 JDK 与收集器变化。面试中可以先说明自己的运行环境，再解释一次回收的触发原因、回收范围、Pause 阶段和结果；脱离版本背固定结论，很容易在追问时互相矛盾。

## JVM Parameter 与诊断工具

Parameter 题考察的是配置依据。 Heap Size、Young Generation 比例、收集器和 Log Parameter 要跟部署内存、Object 分配速率、延迟目标及 JDK 版本一起讨论。尤其是 G1，通常不建议照搬以固定 Young Generation 大小为中心的旧配置。

相关内容：

- [JVM 常用 Parameter 总结](./jvm-parameters-intro.md)
- [JDK Monitoring 和故障处理工具总结](./jdk-monitoring-and-troubleshooting-tools.md)

常见面试题：

- `-Xms`、`-Xmx`、`-Xmn` 和 `-Xss` 分别控制什么？
- 为什么服务端应用常把 `-Xms` 和 `-Xmx` 设为相同值？
- `-XX:MetaspaceSize` 和 `-XX:MaxMetaspaceSize` 有什么区别？
- 怎样为应用选择 Garbage Collector？切换收集器前要收集哪些数据？
- JDK 8 和 JDK 9 及之后怎样配置 GC Log？
- 发生 OOM 时怎样自动生成 Heap Dump？为什么要提前确认存储空间？
- `jps`、`jstat`、`jinfo`、`jmap`、`jstack` 和 `jcmd` 分别适合查什么？
- 怎样用 `jstat` 观察 GC 频率、各区域 Capacity 和 Object Promotion 情况？
- Thread 长时间 Blocking、Deadlock 或 CPU 飙高时，Thread Dump 能提供什么信息？
- Heap Dump 和 Thread Dump 有什么区别？`kill -3` 生成的是哪一种？
- MAT 分析 Heap Dump 时，Dominator Tree 和到 GC Roots 的 Reference Chain 分别有什么用？
- JFR、JMC、VisualVM 适合观察哪些运行时信息？在线采集时要考虑什么 Overhead？

生成 Heap Dump、Class 直方图或高频采样都有可能增加线上负载，Dump 文件也可能包含业务数据。执行诊断命令前要确认影响范围、磁盘空间和文件保存位置；紧急重启前，至少保留 Alert 时间、关键 Metric、Thread Stack 和必要的 GC 信息。

## JVM 线上问题排查

线上排查通常没有“一个命令直接定位”的答案。收到 Alert 后先核对时间、影响范围、最近变更和系统资源，再决定采集 Thread Stack、GC Log 还是 Heap Dump。若服务已经影响用户，止血和留证需要同时安排，不能为了抓全量证据让故障继续扩大。

相关内容：[Java 后端线上问题排查](./jvm-in-action.md)

常见面试题：

- CPU 飙高时，怎样从 Process 定位到 Thread 和具体代码 Stack？
- CPU 不高但 Load 很高，应该检查哪些 Thread State 和系统 Metric？
- Interface 响应很慢但 CPU 使用率正常，怎样区分 Lock 等待、I/O、Connection Pool 和下游延迟？
- 内存持续上涨时，怎样判断是业务缓存增长、Object 分配过快还是 Memory Leak？
- Java Process OOM 后，怎样判断问题发生在 Heap、Metaspace、Direct Memory 还是 Native Memory？
- Young GC 很频繁，但每次回收很快，应该重点检查什么？
- Full GC 频繁时，怎样观察 Old Generation 增长、Object Promotion 和回收效果？
- Heap Dump 应该在什么时候生成？生产环境直接执行 `jmap -dump` 有什么风险？
- Thread Pool Queue 堆积与 CPU 使用率、Thread State 之间有什么关系？
- 修复 JVM 问题后，应该对比哪些 Metric 来确认改动有效？
- 面试中怎样讲一次没有亲历过的 JVM 故障排查题？

排查结果要能形成证据链。例如 CPU 飙高时，先找到高 CPU 的 Java Process 和 Thread，把 Thread ID 转成 Thread Dump 使用的格式，再核对多次 Thread Stack 是否持续落在同一段代码。内存问题则要结合 GC Log、Object 直方图、Heap Dump 和本机内存，单看 JVM Heap 使用率无法覆盖所有 OOM。

## 按准备时间安排复习

| 剩余时间 | 建议安排 | 复习目标 |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| 1～2 天 | 先过一遍 [JVM 常见面试题总结](https://interview.javaguide.cn/java/java-jvm.html)，优先补 Memory Area、Object 创建、Class Loading、Object 存活判断和主流收集器 | 能回答基础高频题，知道不同结论对应的 JDK 与收集器 |
| 3～7 天 | 补 JVM Parameter、GC Log 和 JDK 诊断工具，分别口述一次 CPU 飙高、OOM 与频繁 Full GC 的排查过程 | 能从 Alert 现象选择 Metric 和工具，并说明操作风险 |
| 1 周以上 | 阅读全部 JVM 专题文章，在本地或测试环境分析一次 GC Log、Thread Dump 或 Heap Dump；结合项目记录实际 JDK、收集器、Heap 配置和运行 Metric | 能把原理、配置、运行现象和验证 Method 连起来 |

社招和中高级岗位往往会继续追问 Parameter 依据与排查证据。没有实际处理过线上 JVM 故障，可以按测试环境观察和专题资料回答，说明自己会先采集什么、怎样缩小范围；不要把学习案例说成亲历的生产事故。

<!-- @include: @article-footer.snippet.md -->
