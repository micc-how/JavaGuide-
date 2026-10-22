---
title: Class File 结构详解
description: 介绍 Java Bytecode Class 文件结构与 Constant Pool 等核心组成，辅助理解编译产物。
category: Java
tag:
  - JVM
head:
  - - meta
    - name: keywords
      content: Class 文件,Constant Pool,Magic Number,版本,Field,Method,属性
---

## 回顾一下 Bytecode

在 Java 中，Java Virtual Machine (JVM) 可以理解的代码就叫做 `字节码`（即扩展名为 `.class` 的文件），它不面向任何特定的处理器，只面向虚拟机。Java 语言通过 Bytecode 的方式，在一定程度上解决了传统解释型语言执行效率低的问题，同时又保留了解释型语言可移植的特点。所以 Java 程序运行时比较高效，而且，由于 Bytecode 并不针对一种特定的机器，因此，Java 程序无须重新编译便可在多种不同 Operating System 的计算机上运行。

Clojure（Lisp 语言的一种方言）、Groovy、Scala、JRuby、Kotlin 等语言都是运行在 Java Virtual Machine 之上。下图展示了不同的语言被不同的 Compiler 编译成 `.class` 文件最终运行在 Java Virtual Machine 之上。`.class` 文件的二进制格式可以使用 [WinHex](https://www.x-ways.net/winhex/) 查看。

![运行在 Java Virtual Machine 之上的编程语言](https://oss.javaguide.cn/github/javaguide/java/basis/java-virtual-machine-program-language-os.png)

可以说 `.class` 文件是不同的语言在 Java Virtual Machine 之间的重要桥梁，同时也是支持 Java 跨平台很重要的一个原因。

## Class 文件结构总结

根据 Java Virtual Machine 规范，Class 文件通过 `ClassFile` 定义，有点类似 C 语言的结构体。

`ClassFile` 的结构如下：

```java
ClassFile {
    u4             magic; //Class 文件的标志
    u2             minor_version;//Class 的小版本号
    u2             major_version;//Class 的大版本号
    u2             constant_pool_count;//常量池的数量
    cp_info        constant_pool[constant_pool_count-1];//常量池
    u2             access_flags;//Class 的访问标记
    u2             this_class;//当前类
    u2             super_class;//父类
    u2             interfaces_count;//接口数量
    u2             interfaces[interfaces_count];//一个类可以实现多个接口
    u2             fields_count;//字段数量
    field_info     fields[fields_count];//一个类可以有多个字段
    u2             methods_count;//方法数量
    method_info    methods[methods_count];//一个类可以有多个方法
    u2             attributes_count;//此类的属性表中的属性数
    attribute_info attributes[attributes_count];//属性表集合
}
```

通过分析 `ClassFile` 的内容，我们便可以知道 class 文件的组成。

![ClassFile 内容分析](https://oss.javaguide.cn/java-guide-blog/16d5ec47609818fc.jpeg)

下面这张图是通过 IDEA 插件 `jclasslib` 查看的，你可以更直观看到 Class 文件结构。

![](https://oss.javaguide.cn/java-guide-blog/image-20210401170711475.png)

使用 `jclasslib` 不光可以直观地查看某个 Class 对应的 Bytecode 文件，还可以查看 Class 的基本信息、Constant Pool、Interface、属性、Function 等信息。

下面详细介绍一下 Class 文件结构涉及到的一些组件。

### Magic Number

```java
    u4             magic; //Class 文件的标志
```

每个 Class 文件的头 4 个 Byte 称为 Magic Number,它的唯一作用是**确定这个文件是否为一个能被虚拟机接收的 Class 文件**。Java 规范规定 Magic Number 为固定值：0xCAFEBABE。如果读取的文件不是以这个 Magic Number 开头，Java Virtual Machine 将拒绝加载它。

### Class 文件 Version（Minor&Major Version）

```java
    u2             minor_version;//Class 的小版本号
    u2             major_version;//Class 的大版本号
```

紧接着 Magic Number 的四个 Byte 存储的是 Class 文件的 Version：第 5 和第 6 个 Byte 是**次 Version**，第 7 和第 8 个 Byte 是**主 Version**。

每当 Java 发布大版本（比如 Java 8，Java9）的时候，主 Version 都会加 1。你可以使用 `javap -v` 命令来快速查看 Class 文件的 Version 信息。

高版本的 Java Virtual Machine 可以执行低版本 Compiler 生成的 Class 文件，但是低版本的 Java Virtual Machine 不能执行高版本 Compiler 生成的 Class 文件。所以，我们在实际开发的时候要确保开发的 JDK 版本和生产环境的 JDK 版本保持一致。

### Constant Pool

```java
    u2             constant_pool_count;//常量池的数量
    cp_info        constant_pool[constant_pool_count-1];//常量池
```

紧接着主次 Version 之后的是 Constant Pool，Constant Pool 的数量是 `constant_pool_count-1`（**Constant Pool Counter 是从 1 开始计数的，将第 0 项 Constant 空出来是有特殊考虑的，Index 值为 0 代表“不 Reference 任何一个 Constant Pool 项”**）。

Constant Pool 主要存放两大 Constant：Literal 和 Symbolic Reference。 Literal 比较接近于 Java 语言层面的 Constant 概念，如文本 String、声明为 final 的 Constant 值等。而 Symbolic Reference 则属于编译原理方面的概念。包括下面三类 Constant：

- Class 和 Interface 的 Fully Qualified Name
- Field 的名称和 Descriptor
- Method 的名称和 Descriptor

Constant Pool 中每一项 Constant 都是一个表。当前《Java Virtual Machine 规范》定义了 17 种 Constant Pool 表，它们都有一个共同特点：**开头是一个 `u1` Type 的 `tag`，用于标识当前 Constant 的 Type。**

| Type | 标志（tag） | 描述 |
| :------------------------------: | :---------: | :--------------------: |
| CONSTANT_utf8_info | 1 | UTF-8 编码的 String |
| CONSTANT_Integer_info | 3 | 整形 Literal |
| CONSTANT_Float_info | 4 | 浮点型 Literal |
| CONSTANT_Long_info | 5 | 长 Integer Literal |
| CONSTANT_Double_info | 6 | 双精度浮点型 Literal |
| CONSTANT_Class_info | 7 | Class 或 Interface 的 Symbolic Reference |
| CONSTANT_String_info | 8 | String Type Literal |
| CONSTANT_FieldRef_info | 9 | Field 的 Symbolic Reference |
| CONSTANT_MethodRef_info | 10 | Class 中 Method 的 Symbolic Reference |
| CONSTANT_InterfaceMethodRef_info | 11 | Interface 中 Method 的 Symbolic Reference |
| CONSTANT_NameAndType_info | 12 | Field 或 Method 的 Symbolic Reference |
| CONSTANT_MethodType_info | 16 | 标志 Method Type |
| CONSTANT_MethodHandle_info | 15 | 表示 Method Handle |
| CONSTANT_Dynamic_info | 17 | 表示动态计算 Constant |
| CONSTANT_InvokeDynamic_info | 18 | 表示一个动态 Method Invocation 点 |
| CONSTANT_Module_info | 19 | 表示模块 |
| CONSTANT_Package_info | 20 | 表示模块中的包 |

`.class` 文件可以通过 `javap -v class类名` Instruction 来看一下其 Constant Pool 中的信息(`javap -v class类名-> temp.txt`：将结果输出到 temp.txt 文件)。

### Access Flag(Access Flags)

```java
    u2             access_flags;//Class 的访问标记
```

在 Constant Pool 结束之后，紧接着的两个 Byte 代表 Access Flag，这个标志用于识别一些 Class 或者 Interface 层次的访问信息，包括：这个 Class 是 Class 还是 Interface，是否为 `public` 或者 `abstract` Type，如果是 Class 的话是否声明为 `final` 等等。

Class 访问和属性 Modifier:

![Class 访问和属性 Modifier](https://oss.javaguide.cn/github/javaguide/java/%E8%AE%BF%E9%97%AE%E6%A0%87%E5%BF%97.png)

我们定义了一个 `Employee` Class

```java
package top.snailclimb.bean;
public class Employee {
   ...
}
```

通过 `javap -v class类名` Instruction 来看一下 Class 的 Access Flag。

![查看 Class 的 Access Flag](https://oss.javaguide.cn/github/javaguide/java/%E6%9F%A5%E7%9C%8B%E7%B1%BB%E7%9A%84%E8%AE%BF%E9%97%AE%E6%A0%87%E5%BF%97.png)

### This Class、Superclass（Super Class）、Interface（Interfaces）Index Collection

```java
    u2             this_class;//当前类
    u2             super_class;//父类
    u2             interfaces_count;//接口数量
    u2             interfaces[interfaces_count];//一个类可以实现多个接口
```

Java Class 的 Inheritance 关系由 Class Index、Superclass Index 和 Interface Index Collection 三项确定。 Class Index、Superclass Index 和 Interface Index Collection 按照顺序排在 Access Flag 之后，

Class 索 Reference 于确定这个 Class 的 Fully Qualified Name，Superclass 索 Reference 于确定这个 Class 的 Superclass 的 Fully Qualified Name，由于 Java 语言的单 Inheritance，所以 Superclass Index 只有一个，除了 `java.lang.Object` 之外，所有的 Java Class 都有 Superclass，因此除了 `java.lang.Object` 外，所有 Java Class 的 Superclass Index 都不为 0。

Interface Index Collection 用来描述这个 Class 实现了哪些 Interface，这些被实现的 Interface 将按 `implements` (如果这个 Class 本身是 Interface 的话则是 `extends`) 后的 Interface 顺序从左到右排列在 Interface Index Collection 中。

### Field Table Collection（Fields）

```java
    u2             fields_count;//字段数量
    field_info     fields[fields_count];//一个类会可以有个字段
```

Field Table（field info）用于描述 Interface 或 Class 中声明的 Variable。 Field 包括 Class 级 Variable 以及 Instance Variable，但不包括在 Method 内部声明的 Local Variable。

**field info（Field Table） 的结构:**

![Field Table 的结构 ](https://oss.javaguide.cn/github/javaguide/java/%E5%AD%97%E6%AE%B5%E8%A1%A8%E7%9A%84%E7%BB%93%E6%9E%84.png)

- **access_flags:** Field 的作用域（`public` ,`private`,`protected` Modifier），是 Instance Variable 还是 Class Variable（`static` Modifier）,可否被 Serialization（transient Modifier）,可变性（final）,Visibility（volatile Modifier，是否强制从 Main Memory 读写）。
- **name_index:** 对 Constant Pool 的 Reference，表示的 Field 的名称；
- **descriptor_index:** 对 Constant Pool 的 Reference，表示 Field 和 Method 的 Descriptor；
- **attributes_count:** 一个 Field 还会拥有一些额外的属性，attributes_count 存放属性的个数；
- **attributes[attributes_count]:** 存放具体属性具体内容。

上述这些信息中，各个 Modifier 都是 Boolean 值，要么有某个 Modifier，要么没有，很适合使用标志位来表示。而 Field 叫什么名字、Field 被定义为什么 Data Type 这些都是无法固定的，只能 Reference Constant Pool 中 Constant 来描述。

**Field 的 access_flag 的取值:**

![Field 的 access_flag 的取值](https://oss.javaguide.cn/github/javaguide/java/jvm/class-file-fields-access_flag.png)

### Method Table Collection（Methods）

```java
    u2             methods_count;//方法数量
    method_info    methods[methods_count];//一个类可以有多个方法
```

methods_count 表示 Method 的数量，而 method_info 表示 Method Table。

Class 文件存储格式中对 Method 的描述与对 Field 的描述几乎采用了完全一致的方式。 Method Table 的结构如同 Field Table 一样，依次包括了 Access Flag、名称 Index、Descriptor Index、Attribute Table Collection 几项。

**method_info（Method Table 的） 结构:**

![Method Table 的结构](https://oss.javaguide.cn/github/javaguide/java/%E6%96%B9%E6%B3%95%E8%A1%A8%E7%9A%84%E7%BB%93%E6%9E%84.png)

**Method Table 的 access_flag 取值：**

![Method Table 的 access_flag 取值](https://oss.javaguide.cn/github/javaguide/java/jvm/class-file-methods-access_flag.png)

注意：因为 `volatile` Modifier 和 `transient` Modifier 不可以修饰 Method，所以 Method Table 的 Access Flag 中没有这两个对应的标志，但是增加了 `synchronized`、`native`、`abstract` 等 Keyword 修饰 Method，所以也就多了这些 Keyword 对应的标志。

### Attribute Table Collection（Attributes）

```java
   u2             attributes_count;//此类的属性表中的属性数
   attribute_info attributes[attributes_count];//属性表集合
```

在 Class 文件，Field Table，Method Table 中都可以携带自己的 Attribute Table Collection，以用于描述某些场景专有的信息。与 Class 文件中其它的数据项目要求的顺序、Length 和内容不同，Attribute Table Collection 的限制稍微宽松一些，不再要求各个 Attribute Table 具有严格的顺序，并且只要不与已有的属性名重复，任何人实现的 Compiler 都可以向 Attribute Table 中写 入自己定义的属性信息，Java Virtual Machine 运行时会忽略掉它不认识的属性。

## 参考

- 《实战 Java Virtual Machine》
- Chapter 4. The class File Format - Java Virtual Machine Specification: <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html>
- Instance 分析 JAVA CLASS 的文件结构：<https://coolshell.cn/articles/9229.html>
- 《Java Virtual Machine 原理图解》 1.2.2、Class 文件中的 Constant Pool 详解（上）：<https://blog.csdn.net/luanlouis/article/details/39960815>

<!-- @include: @article-footer.snippet.md -->
