---
title: Class Loader 详解（重点）
description: Java Class Loader 详解：深入剖析ClassLoader Class Loading 机制、Parent Delegation Model 原理、Bootstrap Class Loader/Platform Class Loader/Application Class Loader、Custom Class Loader 实现、打破 Parent Delegation 场景。
category: Java
tag:
  - JVM
head:
  - - meta
    - name: keywords
      content: Class Loader,ClassLoader,Parent Delegation Model,Class Loading,Custom Class Loader,打破 Parent Delegation
---

## 回顾一下 Class Loading

开始介绍 Class Loader 和 Parent Delegation Model 之前，简单回顾一下 Class Loading。

- Class Loading：**加载->连接->Initialization**。
- 连接过程又可分为三步：**验证->准备->解析**。

![Class Loading](https://oss.javaguide.cn/github/javaguide/java/jvm/class-loading-procedure.png)

加载是 Class Loading 的第一步，主要完成下面 3 件事情：

1. 通过 Fully Qualified Class Name 获取定义此类的二进制 Byte 流
2. 将 Byte 流所代表的静态存储结构转换为 Method Area 的运行时 Data Structure
3. 在内存中生成一个代表该 Class 的 `Class` Object，作为 Method Area 这些数据的访问入口

## Class Loader

### Class Loader 介绍

Class Loader 从 JDK 1.0 就出现了，最初只是为了满足 Java Applet（已经被淘汰） 的需要。后来，慢慢成为 Java 程序中的一个重要组成部分，赋予了 Java Class 可以被动态加载到 Java Virtual Machine (JVM) 中并执行的能力。

根据官方 API 文档的介绍：

> A class loader is an object that is responsible for loading classes. The class ClassLoader is an abstract class. Given the binary name of a class, a class loader should attempt to locate or generate data that constitutes a definition for the class. A typical strategy is to transform the name into a file name and then read a "class file" of that name from a file system.
>
> Every Class object contains a reference to the ClassLoader that defined it.
>
> Class objects for array classes are not created by class loaders, but are created automatically as required by the Java runtime. The class loader for an array class, as returned by Class.getClassLoader() is the same as the class loader for its element type; if the element type is a primitive type, then the array class has no class loader.

翻译过来大概的意思是：

> Class Loader 是一个负责加载 Class 的 Object。`ClassLoader` 是一个 Abstract Class。给定 Class 的 Binary Name，Class Loader 应尝试定位或生成构成 Class 定义的数据。典型的策略是将名称转换为文件名，然后从文件系统中读取该名称的“Class File”。
>
> 每个非 Array Class 或 Interface 都有一个 Reference 指向定义它的 `ClassLoader`。 Array Class 不是通过 `ClassLoader` 创建的，而是 JVM 在需要时自动创建；Reference Type Array 的 Class Loader 与其组件 Type 一致，Primitive Type Array 则没有 Class Loader，`getClassLoader()` 返回 `null`。

从上面的介绍可以看出:

- Class Loader 是一个负责加载 Class 的 Object，用于实现 Class Loading 中的加载这一步。
- 每个非 Array Class 或 Interface 都记录定义它的 `ClassLoader`。
- Array Class 不是通过 `ClassLoader` 创建的（Array Class 没有对应的二进制 Byte 流），而是由 JVM 直接生成；Reference Type Array 沿用组件 Type 的定义 Class Loader，Primitive Type Array 没有 Class Loader。

```java
class Class<T> {
  ...
  private final ClassLoader classLoader;
  @CallerSensitive
  public ClassLoader getClassLoader() {
     //...
  }
  ...
}
```

简单来说，**Class Loader 的主要作用就是动态加载 Java Class 的 Bytecode（`.class` 文件）到 JVM 中（在内存中生成一个代表该 Class 的 `Class` Object）。** Bytecode 可以是 Java 源程序（`.java` 文件）经过 `javac` 编译得来，也可以是通过工具动态生成或者通过网络下载得来。

其实除了加载 Class 之外，Class Loader 还可以加载 Java 应用所需的资源如文本、图像、配置文件、视频等等文件资源。本文只讨论其核心功能：加载 Class。

### Class Loader 加载规则

JVM 启动的时候，并不会一次性加载所有的 Class，而是根据需要去动态加载。也就是说，大部分类在具体用到的时候才会去加载，这样对内存更加友好。

Class Loading 时，`ClassLoader#loadClass` 会先通过 `findLoadedClass` 判断 JVM 是否已将当前 Class Loader 记录为该 Binary Name 对应 Class 的发起加载器，命中后直接返回，否则才继续委派或查找。一个 Class Loader 不能重复定义同一 Binary Name 的 Class。

```java
// 以下字段和方法来自 JDK 8 的 ClassLoader 实现，仅用于说明该版本的记录方式
public abstract class ClassLoader {
  ...
  private final ClassLoader parent;
  // 由这个类加载器加载的类。
  private final Vector<Class<?>> classes = new Vector<>();
  // 由VM调用，用此类加载器记录每个已加载类。
  void addClass(Class<?> c) {
        classes.addElement(c);
   }
  ...
}
```

### Class Loader 总结

JDK 8 中常见的三个重要 Class Loader 如下：

1. **`BootstrapClassLoader`（Bootstrap Class Loader）**：顶层的虚拟机内置加载器，在 Java API 中通常表示为 `null`，并且没有父加载器。在 JDK 8 HotSpot 中，它主要加载运行时核心 Class 库（如 `rt.jar`）以及 `-Xbootclasspath` 指定路径中的 Class。
2. **`ExtensionClassLoader`（Extension Class Loader）**：主要负责加载 `%JRE_HOME%/lib/ext` 目录下的 jar 包和 Class 以及被 `java.ext.dirs` 系统 Variable 所指定的路径下的所有 Class。
3. **`AppClassLoader`（应用程序 Class Loader）**：面向我们用户的加载器，负责加载当前应用 classpath 下的所有 jar 包和 Class。

> 🌈 拓展一下：
>
> - **`rt.jar`**：rt 代表“RunTime”，`rt.jar` 是 Java 基础 Class 库，包含 Java doc 里面看到的所有的 Class 的 Class File。也就是说，我们常用内置库 `java.xxx.*` 都在里面，比如 `java.util.*`、`java.io.*`、`java.nio.*`、`java.lang.*`、`java.sql.*`、`java.math.*`。
> - Java 9 引入模块系统后不再使用 `rt.jar` 和扩展目录机制，Extension Class Loader 由 Platform Class Loader 取代。启动、平台和 Application Class Loader 分别定义不同的运行时模块；不能简单概括为除 `java.base` 外的所有模块都由 Platform Class Loader 加载。

除了这三种 Class Loader 之外，用户还可以加入自定义的 Class Loader 来进行拓展，以满足自己的特殊需求。就比如说，我们可以对 Java Class 的 Bytecode（`.class` 文件）进行加密，加载时再利用自定义的 Class Loader 对其解密。

![Class Loader 层次关系图](https://oss.javaguide.cn/github/javaguide/java/jvm/class-loader-parents-delegation-model.png)

Bootstrap Class Loader 是虚拟机内置的，通常在 Java API 中表示为 `null`。 Platform Class Loader、Application Class Loader 以及通常的 Custom Class Loader 都是 `ClassLoader` 的 Instance。这样用户可以 Custom Class Loader，以便让应用程序决定如何获取所需的 Class。

每个 `ClassLoader` 可以通过 `getParent()` 获取其父 `ClassLoader`，如果获取到的 `ClassLoader` 为 `null` 的话，那么该 Class Loader 的父 Class Loader 是 `BootstrapClassLoader`。

```java
public abstract class ClassLoader {
  ...
  // 父加载器
  private final ClassLoader parent;
  @CallerSensitive
  public final ClassLoader getParent() {
     //...
  }
  ...
}
```

**为什么由 Bootstrap Class Loader 定义的 Class 调用 `getClassLoader()` 会得到 `null` 呢？** 因为 Bootstrap Class Loader 是 JVM 内置 Class Loader，Java API 约定通常用 `null` 表示它；具体实现语言并不是 Java 规范的一部分。

下面我们来看一个获取 `ClassLoader` 的小案例：

```java
public class PrintClassLoaderTree {

    public static void main(String[] args) {

        ClassLoader classLoader = PrintClassLoaderTree.class.getClassLoader();

        StringBuilder split = new StringBuilder("|--");
        boolean needContinue = true;
        while (needContinue){
            System.out.println(split.toString() + classLoader);
            if(classLoader == null){
                needContinue = false;
            }else{
                classLoader = classLoader.getParent();
                split.insert(0, "\t");
            }
        }
    }

}
```

输出结果(JDK 8 )：

```plain
|--sun.misc.Launcher$AppClassLoader@18b4aac2
    |--sun.misc.Launcher$ExtClassLoader@53bd815b
        |--null
```

从输出结果可以看出：

- 我们编写的 Java Class `PrintClassLoaderTree` 的 `ClassLoader` 是 `AppClassLoader`；
- `AppClassLoader` 的父 `ClassLoader` 是 `ExtClassLoader`；
- `ExtClassLoader` 的父 `ClassLoader` 是 `Bootstrap ClassLoader`，因此输出结果为 null。

### Custom Class Loader

我们前面也说了，除了 `BootstrapClassLoader` 其他 Class Loader 均由 Java 实现且全部 Inheritance 自 `java.lang.ClassLoader`。如果我们要自定义自己的 Class Loader，很明显需要 Inheritance `ClassLoader` Abstract Class。

`ClassLoader` Class 有两个关键的 Method：

- `protected Class loadClass(String name, boolean resolve)`：加载指定 Binary Name 的 Class，实现了 Parent Delegation Model。`name` 为 Class 的 Binary Name，`resolve` 如果为 true，在加载时调用 `resolveClass(Class<?> c)` Method 解析该 Class。
- `protected Class findClass(String name)`：根据 Class 的 Binary Name 查找 Class，默认实现直接抛出 `ClassNotFoundException`。

官方 API 文档中写到：

> Subclasses of `ClassLoader` are encouraged to override `findClass(String name)`, rather than this method.
>
> 建议 `ClassLoader` 的 Subclass Override `findClass(String name)` Method 而不是 `loadClass(String name, boolean resolve)` Method。

如果我们不想打破 Parent Delegation Model，就 Override `ClassLoader` Class 中的 `findClass()` Method 即可，无法被父 Class Loader 加载的 Class 最终会通过这个 Method 被加载。但是，如果想打破 Parent Delegation Model 则需要 Override `loadClass()` Method。

## Parent Delegation Model

### Parent Delegation Model 介绍

Class Loader 有很多种，当我们想要加载一个 Class 的时候，具体是哪个 Class Loader 加载呢？这就需要提到 Parent Delegation Model 了。

根据官网介绍：

> The ClassLoader class uses a delegation model to search for classes and resources. Each instance of ClassLoader has an associated parent class loader. When requested to find a class or resource, a ClassLoader instance will delegate the search for the class or resource to its parent class loader before attempting to find the class or resource itself. The virtual machine's built-in class loader, called the "bootstrap class loader", does not itself have a parent but may serve as the parent of a ClassLoader instance.

翻译过来大概的意思是：

> `ClassLoader` Class 使用委托模型来搜索 Class 和资源。每个 `ClassLoader` Instance 都有一个相关的父 Class Loader。需要查找 Class 或资源时，`ClassLoader` Instance 会在试图亲自查找 Class 或资源之前，将搜索 Class 或资源的 Task 委托给其父 Class Loader。
> 虚拟机中被称为 "bootstrap class loader"的内置 Class Loader 本身没有父 Class Loader，但是可以作为 `ClassLoader` Instance 的父 Class Loader。

从上面的介绍可以看出：

- `ClassLoader` Class 使用委托模型来搜索 Class 和资源。
- Parent Delegation Model 要求除了顶层的 Bootstrap Class Loader 外，其余的 Class Loader 都应有自己的父 Class Loader。
- `ClassLoader` Instance 会在试图亲自查找 Class 或资源之前，将搜索 Class 或资源的 Task 委托给其父 Class Loader。

下图展示的各种 Class Loader 之间的层次关系被称为 Class Loader 的“**Parent Delegation Model(Parents Delegation Model)**”。

![Class Loader 层次关系图](https://oss.javaguide.cn/github/javaguide/java/jvm/class-loader-parents-delegation-model.png)

注意 ⚠️：Parent Delegation Model 并不是一种强制性的约束，只是 JDK 官方推荐的一种方式。如果我们因为某些特殊需求想要打破 Parent Delegation Model，也是可以的，后文会介绍具体的 Method。

其实这个双亲翻译的容易让别人误解，我们一般理解的双亲都是父母，这里的双亲更多地表达的是“父母这一辈”的人而已，并不是说真的有一个 `MotherClassLoader` 和一个 `FatherClassLoader`。个人觉得翻译成单亲委派模型更好一些，不过，国内既然翻译成了 Parent Delegation Model 并流传了，按照这个来也没问题，不要被误解了就好。

另外，Class Loader 之间的父子关系一般不是以 Inheritance 的关系来实现的，而是通常使用组合关系来复用父加载器的代码。

```java
public abstract class ClassLoader {
  ...
  // 组合
  private final ClassLoader parent;
  protected ClassLoader(ClassLoader parent) {
       this(checkCreateClassLoader(), parent);
  }
  ...
}
```

在 Object-Oriented 编程中，有一条非常经典的设计原则：**组合优于 Inheritance，多用组合少用 Inheritance。**

### Parent Delegation Model 的执行流程

Parent Delegation Model 的主要逻辑集中在 `java.lang.ClassLoader` 的 `loadClass()` 中。下面展示的是 JDK 8 的相关实现片段：

```java
protected Class<?> loadClass(String name, boolean resolve)
    throws ClassNotFoundException
{
    synchronized (getClassLoadingLock(name)) {
        //首先，检查该类是否已经加载过
        Class c = findLoadedClass(name);
        if (c == null) {
            //如果 c 为 null，则说明该类没有被加载过
            long t0 = System.nanoTime();
            try {
                if (parent != null) {
                    //当父类的加载器不为空，则通过父类的loadClass来加载该类
                    c = parent.loadClass(name, false);
                } else {
                    //当父类的加载器为空，则调用启动类加载器来加载该类
                    c = findBootstrapClassOrNull(name);
                }
            } catch (ClassNotFoundException e) {
                //非空父类的类加载器无法找到相应的类，则抛出异常
            }

            if (c == null) {
                //当父类加载器无法加载时，则调用findClass方法来加载该类
                //用户可通过覆写该方法，来自定义类加载器
                long t1 = System.nanoTime();
                c = findClass(name);

                //用于统计类加载器相关的信息
                sun.misc.PerfCounter.getParentDelegationTime().addTime(t1 - t0);
                sun.misc.PerfCounter.getFindClassTime().addElapsedTimeFrom(t1);
                sun.misc.PerfCounter.getFindClasses().increment();
            }
        }
        if (resolve) {
            //对类进行link操作
            resolveClass(c);
        }
        return c;
    }
}
```

每当一个 Class Loader 接收到加载请求时，它会先将请求转发给父 Class Loader。在父 Class Loader 没有找到所请求的 Class 的情况下，该 Class Loader 才会尝试去加载。

结合上面的源码，简单总结一下 Parent Delegation Model 的执行流程：

- 在 Class Loading 的时候，系统会首先判断 This Class 是否被加载过。已经被加载的 Class 会直接返回，否则才会尝试加载（每个父 Class Loader 都会走一遍这个流程）。
- Class Loader 在进行 Class Loading 的时候，它首先不会自己去尝试加载这个 Class，而是把这个请求委派给父 Class Loader 去完成（调用父加载器 `loadClass()` Method 来加载 Class）。这样的话，所有的请求最终都会传送到顶层的 Bootstrap Class Loader `BootstrapClassLoader` 中。
- 只有当父加载器反馈自己无法完成这个加载请求（它的搜索范围中没有找到所需的 Class）时，子加载器才会尝试自己去加载（调用自己的 `findClass()` Method 来加载 Class）。
- 如果子 Class Loader 也无法加载这个 Class，那么它会抛出一个 `ClassNotFoundException` Exception。

🌈 拓展一下：

**JVM 判定两个 Java Class 是否相同的具体规则**：JVM 不仅要看 Class 的全名是否相同，还要看加载此类的 Class Loader 是否一样。只有两者都相同的情况，才认为两个 Class 是相同的。即使两个 Class 来源于同一个 `Class` 文件，被同一个虚拟机加载，只要加载它们的 Class Loader 不同，那这两个 Class 就必定不相同。

### Parent Delegation Model 的好处

Parent Delegation Model 是 Java Class Loading 机制的重要组成部分。父加载器优先有助于让同一委派链中的代码复用父加载器已经定义的 Type，并降低应用代码冒充平台 API 的风险；它并不能阻止相互独立的 Class Loader 分别定义同名 Class。

JVM 区分运行时 Type 的依据包括 Class 或 Interface 的 Binary Name 以及定义它的 Class Loader。 Parent Delegation 会让平台 Class 优先由相应的内置 Class Loader 定义，但并非所有核心或平台 API 都由 Bootstrap Class Loader 加载：JDK 9 以后还有 Platform Class Loader 负责定义平台 Class。

例如，JVM 会优先将 `java.lang.Object` 这类核心 Class 的加载请求交给 `BootstrapClassLoader` 处理；但实际上，`ClassLoader#preDefineClass` 还会在定义阶段校验 Class Name，任何以 `java.` 开头的 Class Name 都会被拒绝，因此不能通过自定义加载器去伪造核心 Class。

有很多小伙伴就要说了：“那我绕过 Parent Delegation Model 不就可以了么？”。

然而，即使攻击者绕过了 Parent Delegation Model，Java 仍然具备更底层的安全机制来保护核心 Class 库。`ClassLoader` 的 `preDefineClass` Method 会在定义 Class 之前进行 Class Name 校验。任何以 `"java."` 开头的 Class Name 都会触发 `SecurityException`，阻止恶意代码定义或加载伪造的核心 Class。

JDK 8 中 `ClassLoader#preDefineClass` Method 源码如下：

```java
private ProtectionDomain preDefineClass(String name,
                                            ProtectionDomain pd)
    {
        // 检查类名是否合法
        if (!checkName(name)) {
            throw new NoClassDefFoundError("IllegalName: " + name);
        }

        // 防止在 "java.*" 包中定义类。
        // 此检查对于安全性至关重要，因为它可以防止恶意代码替换核心 Java 类。
        // JDK 9 利用平台类加载器增强了 preDefineClass 方法的安全性
        if ((name != null) && name.startsWith("java.")) {
            throw new SecurityException
                ("禁止的包名: " +
                 name.substring(0, name.lastIndexOf('.')));
        }

         // 如果未指定 ProtectionDomain，则使用默认域（defaultDomain）。
        if (pd == null) {
            pd = defaultDomain;
        }

        if (name != null) {
            checkCerts(name, pd.getCodeSource());
        }

        return pd;
    }
```

JDK 9 引入了 Platform Class Loader，可以通过 `ClassLoader.getPlatformClassLoader()` 获取。`defineClass` 对 `java.*` Package Name 的限制仍然存在，但具体实现代码与 JDK 8 不同。

### 打破 Parent Delegation Model Method

~~为了避免双亲委托机制，我们可以自己定义一个 Class Loader，然后 Override `loadClass()` 即可。~~

**🐛 修正（参见：[issue871](https://github.com/Snailclimb/JavaGuide/issues/871)）**：自定义加载器的话，需要 Inheritance `ClassLoader`。如果我们不想打破 Parent Delegation Model，就 Override `ClassLoader` Class 中的 `findClass()` Method 即可，无法被父 Class Loader 加载的 Class 最终会通过这个 Method 被加载。但是，如果想打破 Parent Delegation Model 则需要 Override `loadClass()` Method。

为什么是 Override `loadClass()` Method 打破 Parent Delegation Model 呢？ Parent Delegation Model 的执行流程已经解释了：

> Class Loader 在进行 Class Loading 的时候，它首先不会自己去尝试加载这个 Class，而是把这个请求委派给父 Class Loader 去完成（调用父加载器 `loadClass()` Method 来加载 Class）。

Override `loadClass()` Method 之后，我们就可以改变传统 Parent Delegation Model 的执行流程。例如，子 Class Loader 可以在委派给父 Class Loader 之前，先自己尝试加载这个 Class，或者在父 Class Loader 返回之后，再尝试从其他地方加载这个 Class。具体的规则由我们自己实现，根据项目需求定制化。

我们比较熟悉的 Tomcat 服务器为了能够优先加载 Web 应用目录下的 Class，然后再加载其他目录下的 Class，就自定义了 Class Loader `WebAppClassLoader` 来打破双亲委托机制。这也是 Tomcat 下 Web 应用之间的 Class 实现隔离的具体原理。

Tomcat 的 Class Loader 的层次结构如下：

![Tomcat 的 Class Loader 的层次结构](https://oss.javaguide.cn/github/javaguide/java/jvm/tomcat-class-loader-parents-delegation-model.png)

现代 Tomcat 默认使用 `Bootstrap -> System -> Common -> WebappX` 层次。各加载器的搜索位置如下：

- `Common` 的搜索位置由 `$CATALINA_BASE/conf/catalina.properties` 中的 `common.loader` 配置，默认主要包括 `$CATALINA_BASE/lib` 和 `$CATALINA_HOME/lib`。
- 每个 `WebappX` 加载器负责相应 Web 应用的 `/WEB-INF/classes` 和 `/WEB-INF/lib/*.jar`。
- `Server` 和 `Shared` 加载器默认并未定义；只有配置 `server.loader` 或 `shared.loader` 后才会出现在更复杂的层次中。

从图中的委派关系中可以看出：

- `Common` 加载器可见的 Class 可以由 Tomcat 内部组件和所有 Web 应用 Shared。
- 如果显式配置，`Server` 只对 Tomcat 内部可见，`Shared` 则对所有 Web 应用可见。默认配置没有这两个加载器，Web 应用加载器直接以 `Common` 为父加载器。
- 每个 Web 应用都会创建一个单独的 `WebAppClassLoader`，并在启动 Web 应用的 Thread 里设置 Thread Context Class Loader 为 `WebAppClassLoader`。各个 `WebAppClassLoader` Instance 之间相互隔离，进而实现 Web 应用之间的 Class 隔。

单纯依靠 Custom Class Loader 没办法满足某些场景的要求，例如，有些情况下，高层的 Class Loader 需要加载低层的加载器才能加载的 Class。

比如，SPI 中，SPI 的 Interface（如 `java.sql.Driver`）是由 Java 核心库提供的，由 `BootstrapClassLoader` 加载。而 SPI 的实现（如 `com.mysql.cj.jdbc.Driver`）是由第三方供应商提供的，它们是由应用程序 Class Loader 或者 Custom Class Loader 来加载的。默认情况下，一个 Class 及其依赖 Class 由同一个 Class Loader 加载。所以，加载 SPI 的 Interface 的 Class Loader（`BootstrapClassLoader`）也会用来加载 SPI 的实现。按照 Parent Delegation Model，`BootstrapClassLoader` 是无法找到 SPI 的 Implementation Class 的，因为它无法委托给子 Class Loader 去尝试加载。

这里需要注意：JDK 9+ 之后引入模块化，JDBC API 被拆分到 `java.sql` 模块中，不再是 `BootstrapClassLoader` 直接加载，而是由 `PlatformClassLoader` 加载。

```java
public class ClassLoaderTest {
    public static void main(String[] args) throws ClassNotFoundException {
        Class<?> clazz = Class.forName("java.sql.Driver");
        ClassLoader loader = clazz.getClassLoader();
        System.out.println("Loader for java.sql.Driver: " + loader);

        // .jdks/corretto-1.8.0_442/bin/java 环境下为 Loader for java.sql.Driver: null

        // .jdks/jbr-17.0.12/bin/java 环境下为 Loader for java.sql.Driver: jdk.internal.loader.ClassLoaders$PlatformClassLoader@30f39991
    }
}
```

再比如，假设我们的项目中有 Spring 的 jar 包，由于其是 Web 应用之间 Shared 的，因此会由 `SharedClassLoader` 加载（Web 服务器是 Tomcat）。我们项目中有一些用到了 Spring 的业务 Class，比如实现了 Spring 提供的 Interface、用到了 Spring 提供的 Annotation。所以，加载 Spring 的 Class Loader（也就是 `SharedClassLoader`）也会用来加载这些业务 Class。但是业务 Class 在 Web 应用目录下，不在 `SharedClassLoader` 的加载路径下，所以 `SharedClassLoader` 无法找到业务 Class，也就无法加载它们。

如何解决这个问题呢？ 这个时候就需要用到 **Thread Context Class Loader（`ThreadContextClassLoader`）** 了。

拿 Spring 这个例子来说，当 Spring 需要加载业务 Class 的时候，它不是用自己的 Class Loader，而是用 Current Thread 的 Context Class Loader。还记得我上面说的吗？每个 Web 应用都会创建一个单独的 `WebAppClassLoader`，并在启动 Web 应用的 Thread 里设置 Thread Context Class Loader 为 `WebAppClassLoader`。这样就可以让高层的 Class Loader（`SharedClassLoader`）借助子 Class Loader（`WebAppClassLoader`）来加载业务 Class，破坏了 Java 的 Class Loading 委托机制，让应用逆向使用 Class Loader。

Thread Context Class Loader 的原理是将一个 Class Loader 保存在 Thread 私有数据里，跟 Thread 绑定，然后在需要的时候取出来使用。这个 Class Loader 通常是由应用程序或者 Container（如 Tomcat）设置的。

`Java.lang.Thread` 中的 `getContextClassLoader()` 和 `setContextClassLoader(ClassLoader cl)` 分别用来获取和设置 Thread 的 Context Class Loader。如果没有通过 `setContextClassLoader(ClassLoader cl)` 进行设置的话，Thread 将 Inheritance 其 Parent Thread 的 Context Class Loader。

Spring 获取 Thread Context Class Loader 的代码如下：

```java
cl = Thread.currentThread().getContextClassLoader();
```

感兴趣的小伙伴可以自行深入研究一下 Tomcat 打破 Parent Delegation Model 的原理，推荐资料：[《深入拆解 Tomcat & Jetty》](http://gk.link/a/10Egr)。

## 推荐阅读

- 《深入拆解 Java Virtual Machine》
- 深入分析 Java ClassLoader 原理：<https://blog.csdn.net/xyang81/article/details/7292380>
- Java Class Loader(ClassLoader)：<http://gityuan.com/2016/01/24/java-classloader/>
- Class Loaders in Java：<https://www.baeldung.com/java-classloaders>
- Class ClassLoader - Oracle 官方文档：<https://docs.oracle.com/javase/8/docs/api/java/lang/ClassLoader.html>
- 老大难的 Java ClassLoader 再不理解就老了：<https://zhuanlan.zhihu.com/p/51374915>

<!-- @include: @article-footer.snippet.md -->
