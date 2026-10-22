---
title: Java Virtual Machine (JVM) 专题：Memory Area、Class Loading、Garbage Collection (GC)、Parameter 调优与线上排查
description: JVM 面试与 Performance Tuning 学习路线，涵盖 Java Memory Area、Class File 结构、Class Loading、GC、JVM Parameter、JDK Monitoring 工具和线上问题排查。
category: Java
tag:
  - Java
  - JVM
  - Java面试
sitemap:
  changefreq: weekly
  priority: 0.9
head:
  - - meta
    - name: keywords
      content: JVM,JVM面试题,Java Memory Area,Class Loading,Class Loader,GC,JVM Parameter,JDK Monitoring 工具,Out of Memory (OOM),Performance Tuning
---

JVM 是 Java 后端绕不开的核心基础。学习 JVM 的目标不是背概念，而是能解释 Object 如何创建和回收、Class 如何加载、GC 如何影响应用、Parameter 如何配置，以及线上 OOM、频繁 GC、CPU 飙高等问题应该如何排查。

## 适合谁看

- 想系统学习 JVM 的 Java 后端开发者。
- 准备 JVM 内存、Class Loading、GC、Parameter 调优和线上排查相关面试题的同学。
- 已经参与过线上服务维护，但对 GC Log、Heap Dump、Thread Stack 和 JDK 工具不熟的读者。
- 想继续深入 Spring、Netty、中间件或 Performance Optimization 的工程师。

## 学习重点

- JVM 运行时 Memory Area、Object 创建、Object 访问和 OOM 场景。
- Class File 结构、Class Loading、Class Loader 和 Parent Delegation Model。
- GC 基础、Object 存活判断、GC Algorithm 和主流 Garbage Collector。
- JVM Parameter、GC Log、Heap Dump、Thread Stack 和常见 JDK Monitoring 诊断工具。
- 线上问题排查的基本路径：现象观察、Metric 采集、工具分析、原因定位和优化验证。

## 建议阅读顺序

1. 准备面试时先看 [JVM 常见面试题总结](./jvm-interview-questions.md)，找出自己答不完整的模块；系统学习可以从下一步开始。
2. [大白话带你认识 JVM](./jvm-intro.md)：先建立 JVM 的整体认知。
3. [Java Memory Area 详解（重点）](./memory-area.md)：理解 Runtime Data Area 和常见 OOM 场景。
4. [Class File 结构详解](./class-file-structure.md)、[Class Loading 详解](./class-loading-process.md)、[Class Loader 详解（重点）](./classloader.md)：掌握 Class 从 `.class` 到可运行 Object 的过程。
5. [JVM GC 详解（重点）](./jvm-garbage-collection.md)：系统学习 GC 基础、Algorithm 和 Garbage Collector。
6. [最重要的 JVM Parameter 总结](./jvm-parameters-intro.md)、[JDK Monitoring 和故障处理工具总结](./jdk-monitoring-and-troubleshooting-tools.md)、[Java 后端线上问题排查](./jvm-in-action.md)：进入 Parameter 配置和线上实践。

## 核心文章

### JVM 基础与内存

- [JVM 常见面试题总结](./jvm-interview-questions.md)：按内存、Class Loading、GC、Parameter 工具和线上排查整理高频问题。
- [大白话带你认识 JVM](./jvm-intro.md)：用整体视角理解 JVM 的定位和组成。
- [Java Memory Area 详解（重点）](./memory-area.md)：讲解 Program Counter、JVM Stack、Native Method Stack、Heap、Method Area 和 Direct Memory。
- [Class File 结构详解](./class-file-structure.md)：理解 Magic Number、Version、Constant Pool、Access Flag、Field Table、Method Table 和 Attribute Table。

### Class Loading

- [Class Loading 详解](./class-loading-process.md)：梳理加载、验证、准备、解析、Initialization、使用和卸载。
- [Class Loader 详解（重点）](./classloader.md)：理解 Bootstrap Class Loader、Extension Class Loader（JDK 8）/Platform Class Loader（JDK 9+）、Application Class Loader 和 Parent Delegation Model。

### GC 与调优

- [JVM GC 详解（重点）](./jvm-garbage-collection.md)：理解 Object 存活判断、Reference Type、GC Algorithm、Generational Collection 和主流 Garbage Collector。
- [最重要的JVM Parameter 总结](./jvm-parameters-intro.md)：整理 Heap Size、GC Log、OOM Dump、Garbage Collector 和诊断相关 Parameter。
- [JDK Monitoring 和故障处理工具总结](./jdk-monitoring-and-troubleshooting-tools.md)：介绍 jps、jstat、jmap、jstack、jcmd、JConsole、VisualVM、JMC 等工具。
- [Java 后端线上问题排查](./jvm-in-action.md)：从 Alert 确认、止血留证开始，串起 CPU、内存、GC、Thread Pool、Connection Pool、慢 SQL、Redis 和 Message Backlog 的排查过程。

## 高频问题

- JVM 运行时 Memory Area 如何划分？哪些区域 Thread 私有？
- Heap 和 Method Area 分别存放什么？ Direct Memory 会不会 OOM？
- Object 是如何创建的？ Object 访问定位有哪几种方式？
- Class Loading 有哪些阶段？ Initialization 什么时候触发？
- 什么是 Parent Delegation Model？为什么需要它？
- 如何判断 Object 是否可以被回收？强软弱 Phantom Reference 有什么区别？
- Minor GC、Major GC、Full GC 有什么区别？
- G1、ZGC、Shenandoah 分别适合什么场景？
- 常用 JVM Parameter 有哪些？线上如何保留 GC Log 和 OOM dump？
- CPU 飙高、频繁 Full GC、Memory Leak 应该如何排查？

## 相关专题

- [Java 知识体系](../)
- [Java 基础专题](../basis/)
- [Java Concurrent Programming 专题](../concurrent/)
- [Java IO 专题](../io/)
- [Operating System](../../cs-basics/operating-system/)

<!-- @include: @article-footer.snippet.md -->
