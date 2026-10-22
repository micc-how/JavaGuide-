---
title: Class Loading 详解
description: 拆解 Java Virtual Machine (JVM) Class Loading 的各阶段与关键细节，理解验证、准备、解析与 Initialization 的具体行为。
category: Java
tag:
  - JVM
head:
  - - meta
    - name: keywords
      content: Class Loading,加载,验证,准备,解析,Initialization,clinit,Constant Pool
---

## Class 的 Lifecycle

Class 从被加载到虚拟机内存中开始到卸载出内存为止，它的整个 Lifecycle 可以简单概括为 7 个阶段：加载（Loading）、验证（Verification）、准备（Preparation）、解析（Resolution）、Initialization、使用（Using）和卸载（Unloading）。其中，验证、准备和解析这三个阶段可以统称为 Linking。

这 7 个阶段的顺序如下图所示：

![一个 Class 的完整 Lifecycle](https://oss.javaguide.cn/github/javaguide/java/jvm/lifecycle-of-a-class.png)

## Class Loading

**Class 文件需要加载到虚拟机中之后才能运行和使用，那么虚拟机是如何加载这些 Class 文件呢？**

系统加载 Class 型的文件主要三步：**加载->连接->Initialization**。连接过程又可分为三步：**验证->准备->解析**。

![Class Loading](https://oss.javaguide.cn/github/javaguide/java/jvm/class-loading-procedure.png)

详见 [Java Virtual Machine Specification - 5.3. Creation and Loading](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html#jvms-5.3)。

### Loading

Class Loading 的第一步，主要完成下面 3 件事情：

1. 通过 Fully Qualified Class Name 获取定义此类的二进制 Byte 流。
2. 将 Byte 流所代表的静态存储结构转换为 Method Area 的运行时 Data Structure。
3. 在内存中生成一个代表该 Class 的 `Class` Object，作为 Method Area 这些数据的访问入口。

虚拟机规范上面这 3 点并不具体，因此是非常灵活的。比如：“通过 Fully Qualified Class Name 获取定义此类的二进制 Byte 流” 并没有指明具体从哪里获取（`ZIP`、 `JAR`、`EAR`、`WAR`、网络、动态代理技术运行时动态生成、其他文件生成比如 `JSP`...）、怎样获取。

加载这一步主要是通过我们后面要讲到的 **Class Loader** 完成的。 Class Loader 有很多种，当我们想要加载一个 Class 的时候，具体是哪个 Class Loader 加载由 **Parent Delegation Model** 决定（不过，我们也能打破 Parent Delegation Model）。

> Class Loader、Parent Delegation Model 也是非常重要的知识点，这部分内容在[Class Loader 详解](https://javaguide.cn/java/jvm/classloader.html “Class Loader 详解”)这篇文章中有详细介绍到。阅读本篇文章的时候，大家知道有这么个东西就可以了。

每个非 Array Class 或 Interface 都由某个 Class Loader 创建。 Array Class 不是通过 `ClassLoader` 创建的，而是 JVM 在需要时自动创建；Reference Type Array 的定义 Class Loader 与其组件 Type 的定义 Class Loader 一致，Primitive Type Array 的 `getClassLoader()` 则返回 `null`。

一个非 Array Class 的 Loading（获取 Class 的二进制 Byte 流的动作）可控性很强。通常可以 Inheritance `ClassLoader` 并 Override `findClass()` 来控制 Byte 流的获取方式，同时保留 `loadClass()` 实现的 Parent Delegation 流程；只有确实要改变委派规则时才需要 Override `loadClass()`。

Loading 与连接阶段的部分动作（如一部分 Bytecode 文件格式验证动作）是交叉进行的，Loading 尚未结束，连接阶段可能就已经开始了。

### Verification

**验证是连接阶段的第一步，这一阶段的目的是确保 Class 文件的 Byte 流中包含的信息符合《Java Virtual Machine 规范》的全部约束要求，保证这些信息被当作代码运行后不会危害虚拟机自身的安全。**

Verification 这一步在整个 Class Loading 中耗费的资源还是相对较多的，但很有必要，可以有效防止恶意代码的执行。任何时候，程序安全都是第一位。

HotSpot 曾提供 `-Xverify:none` 和 `-noverify` 来关闭大部分类验证，但这会削弱 Bytecode 安全检查，不应作为生产环境的通用优化手段。这两个选项已在 JDK 13 中被弃用，现代 JDK 还可能忽略或移除它们。

Verification 主要由四个检验阶段组成：

1. 文件格式验证（Class 文件格式检查）
2. Metadata 验证（Bytecode 语义检查）
3. Bytecode Verification（程序语义检查）
4. Symbolic Reference 验证（Class 的正确性检查）

![Verification 示意图](https://oss.javaguide.cn/github/javaguide/java/jvm/class-loading-process-verification.png)

文件格式验证这一阶段是基于该 Class 的二进制 Byte 流进行的，主要目的是保证输入的 Byte 流能正确地解析并存储于 Method Area 之内，格式上符合描述一个 Java Type 信息的要求。除了这一阶段之外，其余三个 Verification 都是基于 Method Area 的存储结构上进行的，不会再直接读取、操作 Byte 流了。

> Method Area 属于是 JVM Runtime Data Area 的一块逻辑区域，是各个 Thread Shared 的 Memory Area。当虚拟机要使用一个 Class 时，它需要读取并解析 Class 文件获取相关信息，再将信息存入到 Method Area。 Method Area 会存储已被虚拟机加载的 **Class 信息、Field 信息、Method 信息、Constant、Static Variable、Just-In-Time Compiler 编译后的代码缓存等数据**。
>
> 关于 Method Area 的详细介绍，推荐阅读 [Java Memory Area 详解](https://javaguide.cn/java/jvm/memory-area.html “Java Memory Area 详解”) 这篇文章。

Symbolic Reference 验证发生在 Class Loading 中的 Resolution，具体点说是 JVM 将 Symbolic Reference 转化为 Direct Reference 的时候（Resolution 会介绍 Symbolic Reference 和 Direct Reference）。

Symbolic Reference 验证的主要目的是确保 Resolution 能正常执行，如果无法通过 Symbolic Reference 验证，JVM 会抛出 Exception，比如：

- `java.lang.IllegalAccessError`：当 Class 试图访问或修改它没有权限访问的 Field，或调用它没有权限访问的 Method 时，抛出该 Exception。
- `java.lang.NoSuchFieldError`：当 Class 试图访问或修改一个指定的 Object Field，而该 Object 不再包含该 Field 时，抛出该 Exception。
- `java.lang.NoSuchMethodError`：当 Class 试图访问一个指定的 Method，而该 Method 不存在时，抛出该 Exception。
- ……

### Preparation

**Preparation 是正式为 Class Variable 分配内存并设置 Class Variable 初始值的阶段**，这些内存都将在 Method Area 中分配。对于该阶段有以下几点需要注意：

1. 这时候进行 Memory Allocation 的仅包括 Class Variable（Class Variables，即 Static Variable，被 `static` Keyword 修饰的 Variable，只与 Class 相关，因此被称为 Class Variable），而不包括 Instance Variable。 Instance Variable 会在 Object Instance 化时随着 Object 一块分配在 Java Heap 中。
2. 从概念上讲，Class Variable 所使用的内存都应当在 **Method Area** 中进行分配。不过有一点需要注意的是：JDK 7 之前，HotSpot 使用 Permanent Generation (PermGen) 来实现方法区的时候，实现是完全符合这种逻辑概念的。 而在 JDK 7 及之后，HotSpot 已经把原本放在 PermGen 的 String Constant Pool、Static Variable 等移动到 Heap 中，这个时候 Class Variable 则会随着 Class Object 一起存放在 Java Heap 中。相关阅读：[《深入理解 Java Virtual Machine（第 3 版）》勘误#75](https://github.com/fenixsoft/jvm_book/issues/75 “《深入理解 Java Virtual Machine（第3版）》勘误#75”)
3. 这里所设置的初始值通常是 Data Type 的默认零值（如 0、0L、null、false 等）。比如定义 `public static int value=111`，`value` 在 Preparation 通常先得到 0，在 Initialization 才赋值为 111。特殊情况是 Field 带有 `ConstantValue` 属性时，Preparation 会直接赋为该属性指定的值；`public static final int value=111` 这样的 Compile-time Constant 就是典型例子，但并非所有 `static final` Field 都有 `ConstantValue` 属性。

**基本 Data Type 的零值**：（图片来自《深入理解 Java Virtual Machine》第 3 版 7.3.3）

![基本 Data Type 的零值](https://oss.javaguide.cn/github/javaguide/java/%E5%9F%BA%E6%9C%AC%E6%95%B0%E6%8D%AE%E7%B1%BB%E5%9E%8B%E7%9A%84%E9%9B%B6%E5%80%BC.png)

### Resolution

**Resolution 是虚拟机从 Runtime Constant Pool 中的 Symbolic Reference 动态确定具体值的过程。** 当前规范涉及 Class 或 Interface、Field、Method、Interface Method、Method Type、Method Handle、动态调用点以及动态 Constant 等 Symbolic Reference。

《深入理解 Java Virtual Machine》7.3.4 节第三版对 Symbolic Reference 和 Direct Reference 的解释如下：

![Symbolic Reference 和 Direct Reference](https://oss.javaguide.cn/github/javaguide/java/jvm/symbol-reference-and-direct-reference.png)

举个例子：程序调用 Method 时，虚拟机需要根据 Method Symbolic Reference 确定实际要调用的 Method。HotSpot 等虚拟机可以使用方法表、入口 Address 或其他内部结构加速调用，但这些表示方式属于实现细节，并非《Java Virtual Machine 规范》统一规定的 Method Table Offset。

综上，Resolution 是虚拟机根据 Runtime Constant Pool 中的 Symbolic Reference 确定 Class、Field、Method 或动态调用点等具体目标的过程；Direct Reference 的内部表示不一定是内存 Pointer 或固定 Offset。

### Initialization

**Initialization 会执行 Class 或 Interface 的 Initialization Method `<clinit>()`（如果 Compiler 生成了该 Method），这是 Class Loading 的最后一步。**

> 说明：Compiler 根据 Static Field Initialization 表达式和静态 Initialization 块生成 `<clinit>()`；如果没有需要执行的 Class Initialization 代码，Class 文件中可以不存在该 Method。

JVM 会同步 Class 或 Interface 的 Initialization 过程，确保同一时刻只有一个 Thread 执行其 Initialization Method；这并不是说 `<clinit>()` Method 本身带有 Java Lock。其他 Thread 可能在等待该 Class Initialization 完成时 Blocking。

对于 Initialization，规范列出的主要主动使用场景包括：

1. 遇到 `new`、`getstatic`、`putstatic` 或 `invokestatic` 这 4 条 Bytecode Instruction 时：
   - `new`: 创建一个 Class 的 Object Instance。
   - `getstatic`、`putstatic`: 读取或设置一个 Type 的 Static Field（被 `final` 修饰、已在 Compile-time 把结果放入 Constant Pool 的 Static Field 除外）。
   - `invokestatic`: 调用 Class 的 Static Method。
2. 使用 `java.lang.reflect` Package 的 Method 对 Class 进行 Reflection 调用时如 `Class.forName("...")`, `newInstance()` 等等。如果 Class 没 Initialization，需要触发其 Initialization。
3. Initialization 一个 Class，如果其 Superclass 还未 Initialization，则先触发该 Superclass 的 Initialization。
4. 当虚拟机启动时，用户需要定义一个要执行的主 Class (包含 `main` Method 的那个 Class)，虚拟机会先 Initialization 这个 Class。
5. 首次调用解析结果为 `REF_getStatic`、`REF_putStatic`、`REF_invokeStatic` 或 `REF_newInvokeSpecial` 的 `MethodHandle` 时，需要 Initialization 声明该目标的 Class 或 Interface。
6. **「补充，来自[issue745](https://github.com/Snailclimb/JavaGuide/issues/745)」** 当一个 Interface 中定义了 JDK8 新加入的 Default Method（被 default Keyword 修饰的 Interface Method）时，如果有这个 Interface 的 Implementation Class 发生了 Initialization，那该 Interface 要在其之前被 Initialization。

## Class Unloading

> 卸载这部分内容来自 [issue#662](https://github.com/Snailclimb/JavaGuide/issues/662)由 **[guang19](https://github.com/guang19)** 补充完善。

Class Unloading 是 JVM 回收某个 Class 或 Interface 的 Method Area 表示及其关联资源的过程。根据《Java 语言规范》，Class 或 Interface 只有在其定义 Class Loader 可被 Garbage Collection (GC) 时才可能卸载；由 Bootstrap Class Loader 定义的 Class 或 Interface 不能卸载。在常见的 HotSpot 应用中，这通常发生在可回收的 Custom Class Loader 及其定义的 Class 上。

在 HotSpot 中判断某个 Class 是否可能卸载时，通常可以从下面三个条件理解：

1. 该 Class 的所有的 Object Instance 都已被 GC，也就是说 Heap 不存在该 Class 的 Object Instance。
2. 该 Class 没有在其他任何地方被 Reference
3. 该 Class 的 Class Loader 的 Instance 已被 GC

满足这些条件只表示该 Class 具备被卸载的条件，并不保证 JVM 会立即或一定卸载它。由 Bootstrap Class Loader 创建的 Class 不会被卸载；由 Custom Class Loader 创建的 Class 则可能被卸载。

通常，JDK 自带的 Bootstrap Class Loader、Platform Class Loader 和 Application Class Loader 会随 JVM 长期存活；Custom Class Loader 的 Instance 则可以变为 Unreachable，因此由它定义的 Class 可能具备卸载条件。JDK 9 起，原来的 Extension Class Loader 已由 Platform Class Loader 取代。

**参考**

- 《深入理解 Java Virtual Machine》
- 《实战 Java Virtual Machine》
- Chapter 5. Loading, Linking, and Initializing - Java Virtual Machine Specification：<https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html#jvms-5.4>

<!-- @include: @article-footer.snippet.md -->
