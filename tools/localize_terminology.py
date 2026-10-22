# -*- coding: utf-8 -*-
"""Localize Chinese technical terms in JavaGuide Markdown to English.

Preserves Chinese prose, code fences, inline code, URLs, and site tag metadata.
Pilot scope: docs/java/concurrent and docs/java/jvm.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_DIRS = [
    ROOT / "docs" / "java" / "concurrent",
    ROOT / "docs" / "java" / "jvm",
]
GLOSSARY_PATH = ROOT / "terminology-glossary.md"

# Kept as-is: ordinary words, or technical words whose English form is ambiguous.
KEEP_INTACT = [
    "类似",
    "类比",
    "类别",
    "分类",
    "这类",
    "那类",
    "各类",
    "之类",
    "此类",
    "某类",
    "一类",
    "二类",
    "三类",
    "四类",
    "五类",
    "多类",
    "同类",
    "值得",
    "数值",
    "价值",
    "异常情况",
    "异常实例",
    "这种方法",
    "实现方法",
    "解决方法",
    "计算方法",
    "判断方法",
    "使用方法",
    "最佳方法",
    "有效方法",
    "使用多线程的方法",
    "竞争同一个资源的方法",
    "计算的方法",
    "具体方法",
    "引用传递",
    "堆积",
    "堆叠",
    "堆砌",
]

# (source, replacement). Longer sources win, regardless of list order.
GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Java concurrency and locks",
        [
            ("线程池", "Thread Pool"),
            ("核心线程数", "Core Pool Size"),
            ("最大线程数", "Maximum Pool Size"),
            ("非核心线程", "Non-core Thread"),
            ("核心线程", "Core Thread"),
            ("空闲线程", "Idle Thread"),
            ("工作线程", "Worker Thread"),
            ("活跃线程", "Active Thread"),
            ("调用者线程", "Caller Thread"),
            ("当前线程", "Current Thread"),
            ("守护线程", "Daemon Thread"),
            ("用户线程", "User Thread"),
            ("虚拟线程", "Virtual Thread"),
            ("平台线程", "Platform Thread"),
            ("载体线程", "Carrier Thread"),
            ("主线程", "Main Thread"),
            ("子线程", "Child Thread"),
            ("父线程", "Parent Thread"),
            ("业务线程", "Business Thread"),
            ("线程安全性", "Thread Safety"),
            ("线程不安全", "Not Thread-safe"),
            ("非线程安全", "Non-thread-safe"),
            ("线程安全", "Thread-safe"),
            ("线程本地变量", "Thread-Local Variable"),
            ("线程本地", "Thread-local"),
            ("线程快照", "Thread Dump"),
            ("线程转储", "Thread Dump"),
            ("线程堆栈", "Thread Stack"),
            ("线程状态", "Thread State"),
            ("线程调度", "Thread Scheduling"),
            ("线程复用", "Thread Reuse"),
            ("线程同步", "Thread Synchronization"),
            ("线程通信", "Inter-thread Communication"),
            ("线程中断", "Thread Interrupt"),
            ("线程饥饿", "Thread Starvation"),
            ("线程数量", "Thread Count"),
            ("线程数", "Thread Count"),
            ("线程组", "Thread Group"),
            ("线程工厂", "Thread Factory"),
            ("默认线程工厂", "Default Thread Factory"),
            ("多线程编程", "Multithreaded Programming"),
            ("多线程", "Multithreading"),
            ("单线程", "Single Thread"),
            ("线程", "Thread"),
            ("多进程", "Multi-process"),
            ("进程", "Process"),
            ("死锁", "Deadlock"),
            ("活锁", "Livelock"),
            ("饥饿", "Starvation"),
            ("竞态条件", "Race Condition"),
            ("竞争条件", "Race Condition"),
            ("临界区", "Critical Section"),
            ("上下文切换", "Context Switch"),
            ("上下文", "Context"),
            ("用户态", "User Mode"),
            ("内核态", "Kernel Mode"),
            ("时间片轮转", "Round-Robin"),
            ("时间片", "Time Slice"),
            ("抢占式调度", "Preemptive Scheduling"),
            ("协同式调度", "Cooperative Scheduling"),
            ("调度器", "Scheduler"),
            ("操作系统", "Operating System"),
            ("不可中断", "Uninterruptible"),
            ("可中断", "Interruptible"),
            ("中断状态", "Interrupt Status"),
            ("中断标记", "Interrupt Flag"),
            ("中断", "Interrupt"),
            ("非阻塞队列", "Non-blocking Queue"),
            ("阻塞队列", "Blocking Queue"),
            ("非阻塞", "Non-blocking"),
            ("阻塞锁", "Blocking Lock"),
            ("阻塞", "Blocking"),
            ("异步编排", "Asynchronous Orchestration"),
            ("异步", "Asynchronous"),
            ("自旋等待", "Spin-Wait"),
            ("自适应自旋", "Adaptive Spinning"),
            ("自旋锁", "Spin Lock"),
            ("自旋", "Spin"),
            ("原子性", "Atomicity"),
            ("原子操作", "Atomic Operation"),
            ("原子更新", "Atomic Update"),
            ("Atomic 原子类", "Atomic Class"),
            ("原子类", "Atomic Class"),
            ("原子", "Atomic"),
            ("比较并交换（CAS）", "CAS"),
            ("比较并交换(CAS)", "CAS"),
            ("比较并交换", "CAS"),
            ("乐观读", "Optimistic Read"),
            ("悲观读", "Pessimistic Read"),
            ("乐观锁", "Optimistic Lock"),
            ("悲观锁", "Pessimistic Lock"),
            ("非公平锁", "Nonfair Lock"),
            ("公平锁", "Fair Lock"),
            ("非公平", "Nonfair"),
            ("不公平", "Unfair"),
            ("公平性", "Fairness"),
            ("公平", "Fair"),
            ("可重入性", "Reentrancy"),
            ("可重入锁", "Reentrant Lock"),
            ("可重入", "Reentrant"),
            ("读写锁", "Read-Write Lock"),
            ("读锁", "Read Lock"),
            ("写锁", "Write Lock"),
            ("互斥锁", "Mutex"),
            ("不互斥", "Non-exclusive"),
            ("互斥", "Mutual Exclusion"),
            ("分段锁", "Segmented Lock"),
            ("排他锁", "Exclusive Lock"),
            ("独占锁", "Exclusive Lock"),
            ("共享锁", "Shared Lock"),
            ("偏向锁", "Biased Lock"),
            ("轻量级锁", "Lightweight Lock"),
            ("重量级锁", "Heavyweight Lock"),
            ("同步锁", "Intrinsic Lock"),
            ("对象锁", "Object Lock"),
            ("类锁", "Class Lock"),
            ("行锁", "Row Lock"),
            ("表锁", "Table Lock"),
            ("锁升级", "Lock Inflation"),
            ("锁消除", "Lock Elimination"),
            ("锁粗化", "Lock Coarsening"),
            ("锁竞争", "Lock Contention"),
            ("无锁", "Lock-Free"),
            ("无 Lock", "Lock-Free"),
            ("锁机制", "Locking Mechanism"),
            ("尝试获取锁", "Try Acquire"),
            ("获取锁", "Acquire Lock"),
            ("释放锁", "Release Lock"),
            ("持有锁", "Hold Lock"),
            ("加锁", "Locking"),
            ("解锁（unlock）", "unlock"),
            ("解锁", "Unlock"),
            ("锁定（lock）", "lock"),
            ("锁定", "Lock"),
            ("锁", "Lock"),
            ("独占模式", "Exclusive Mode"),
            ("共享模式", "Shared Mode"),
            ("共享资源", "Shared Resource"),
            ("共享变量", "Shared Variable"),
            ("共享", "Shared"),
            ("独占", "Exclusive"),
            ("管程", "Monitor"),
            ("监视器锁", "Monitor Lock"),
            ("对象监视器", "Object Monitor"),
            ("监视器", "Monitor"),
            ("同步方法", "Synchronized Method"),
            ("同步代码块", "Synchronized Block"),
            ("同步块", "Synchronized Block"),
            ("同步器", "Synchronizer"),
            ("同步状态", "Synchronization State"),
            ("同步操作", "Synchronization Action"),
            ("同步机制", "Synchronization Mechanism"),
            ("条件队列", "Condition Queue"),
            ("等待队列", "Wait Queue"),
            ("任务队列", "Task Queue"),
            ("工作队列", "Work Queue"),
            ("延迟队列", "Delay Queue"),
            ("优先队列", "Priority Queue"),
            ("双端队列", "Deque"),
            ("变体队列", "Variant Queue"),
            ("队列", "Queue"),
            ("拒绝策略", "Rejection Policy"),
            ("默认拒绝策略", "Default Rejection Policy"),
            ("饱和策略", "Saturation Policy"),
            ("反压", "Backpressure"),
            ("优雅关闭", "Graceful Shutdown"),
            ("入队", "Enqueue"),
            ("出队", "Dequeue"),
            ("重入次数", "Reentrancy Count"),
            ("重入", "Reentrant"),
            ("许可数量", "Permit Count"),
            ("许可证", "Permit"),
            ("许可数", "Permit Count"),
            ("内存栅栏", "Memory Fence"),
            ("循环栅栏", "CyclicBarrier"),
            ("栅栏", "Barrier"),
            ("倒计时器", "CountDownLatch"),
            ("生产者-消费者", "Producer-Consumer"),
            ("生产者", "Producer"),
            ("消费者", "Consumer"),
            ("回调方法", "Callback Method"),
            ("回调", "Callback"),
            ("版本号", "Version"),
            ("时间戳", "Timestamp"),
            ("复合操作", "Compound Operation"),
            ("唯一约束", "Unique Constraint"),
            ("忙等", "Busy-Waiting"),
            ("死循环", "Infinite Loop"),
            ("循环引用", "Circular Reference"),
            ("循环", "Loop"),
            ("超时", "Timeout"),
            ("重试", "Retry"),
        ],
    ),
    (
        "JMM and memory ordering",
        [
            ("JMM（Java 内存模型）", "JMM"),
            ("JMM(Java 内存模型)", "JMM"),
            ("JMM（Java内存模型）", "JMM"),
            ("JMM(Java内存模型)", "JMM"),
            ("Java内存模型JMM", "JMM"),
            ("Java 内存模型JMM", "JMM"),
            ("Java内存模型 JMM", "JMM"),
            ("Java 内存模型 JMM", "JMM"),
            ("JMMJava内存模型", "JMM"),
            ("JMM Java内存模型", "JMM"),
            ("Java 内存模型（JMM）", "JMM"),
            ("Java 内存模型(JMM)", "JMM"),
            ("Java内存模型（JMM）", "JMM"),
            ("Java内存模型(JMM)", "JMM"),
            ("Java 内存模型", "JMM"),
            ("Java内存模型", "JMM"),
            ("内存可见性", "Memory Visibility"),
            ("可见性", "Visibility"),
            ("有序性", "Ordering"),
            ("指令重排序", "Instruction Reordering"),
            ("指令重排", "Instruction Reordering"),
            ("指令并行重排", "Instruction-Parallel Reordering"),
            ("编译器优化重排", "Compiler Reordering"),
            ("重排序", "Reordering"),
            ("重排", "Reordering"),
            ("内存屏障", "Memory Barrier"),
            ("读屏障", "Read Barrier"),
            ("写屏障", "Write Barrier"),
            ("伪共享", "False Sharing"),
            ("缓存行", "Cache Line"),
            ("缓存一致性协议", "Cache Coherence Protocol"),
            ("缓存一致协议", "Cache Coherence Protocol"),
            ("缓存一致性", "Cache Coherence"),
            ("高速缓存", "Cache"),
            ("CPU 缓存", "CPU Cache"),
            ("CPU缓存", "CPU Cache"),
            ("缓存模型", "Cache Model"),
            ("硬件内存模型", "Hardware Memory Model"),
            ("缓冲区", "Buffer"),
            ("主内存", "Main Memory"),
            ("主存", "Main Memory"),
            ("工作内存", "Working Memory"),
            ("内存模型", "Memory Model"),
        ],
    ),
    (
        "JVM memory and garbage collection",
        [
            ("运行时数据区域", "Runtime Data Area"),
            ("运行时数据区", "Runtime Data Area"),
            ("程序计数器", "Program Counter"),
            ("Java 虚拟机栈", "JVM Stack"),
            ("Java虚拟机栈", "JVM Stack"),
            ("虚拟机栈", "JVM Stack"),
            ("本地方法栈", "Native Method Stack"),
            ("操作数栈", "Operand Stack"),
            ("本地方法接口（Java Native Interface）", "JNI"),
            ("本地方法接口(Java Native Interface)", "JNI"),
            ("JNI（Java Native Interface）", "JNI"),
            ("JNI(Java Native Interface)", "JNI"),
            ("JNI（本地方法接口）", "JNI"),
            ("JNI(本地方法接口)", "JNI"),
            ("本地方法接口", "JNI"),
            ("本地方法", "Native Method"),
            ("方法区", "Method Area"),
            ("直接内存", "Direct Memory"),
            ("堆外内存", "Off-heap Memory"),
            ("非堆内存", "Non-heap Memory"),
            ("堆内存", "Heap Memory"),
            ("堆转储快照", "Heap Dump"),
            ("堆转储", "Heap Dump"),
            ("堆空间", "Heap Space"),
            ("堆大小", "Heap Size"),
            ("堆溢出", "Heap OOM"),
            ("栈溢出", "StackOverflow"),
            ("栈空间", "Stack Space"),
            ("线程栈", "Thread Stack"),
            ("调用堆栈", "Call Stack"),
            ("方法堆栈", "Call Stack"),
            ("堆栈信息", "Stack Trace"),
            ("堆栈", "Stack Trace"),
            ("入栈", "Push"),
            ("出栈", "Pop"),
            ("压栈", "Push"),
            ("弹栈", "Pop"),
            ("栈帧", "Stack Frame"),
            ("堆", "Heap"),
            ("栈", "Stack"),
            ("元空间", "Metaspace"),
            ("永久代", "PermGen"),
            ("年轻代", "Young Generation"),
            ("新生代", "Young Generation"),
            ("老年代", "Old Generation"),
            ("幸存区", "Survivor Space"),
            ("幸存者区", "Survivor Space"),
            ("类元数据", "Class Metadata"),
            ("元数据", "Metadata"),
            ("对象头", "Object Header"),
            ("标记字段（Mark Word）", "Mark Word"),
            ("标记字段(Mark Word)", "Mark Word"),
            ("标记字段", "Mark Word"),
            ("类型指针", "Klass Pointer"),
            ("实例数据", "Instance Data"),
            ("对齐填充", "Alignment Padding"),
            ("指针碰撞", "Bump-the-Pointer"),
            ("空闲列表", "Free List"),
            ("线程本地分配缓冲区", "TLAB"),
            ("线程本地分配缓冲", "TLAB"),
            ("本地分配缓冲", "TLAB"),
            ("逃逸分析", "Escape Analysis"),
            ("标量替换", "Scalar Replacement"),
            ("栈上分配", "Stack Allocation"),
            ("直接指针", "Direct Pointer"),
            ("句柄", "Handle"),
            ("指针", "Pointer"),
            ("空指针异常", "NullPointerException"),
            ("空指针", "Null Pointer"),
            ("安全点", "Safepoint"),
            ("安全区域", "Safe Region"),
            ("三色标记", "Tri-color Marking"),
            ("浮动垃圾", "Floating Garbage"),
            ("记忆集", "Remembered Set"),
            ("卡表", "Card Table"),
            ("增量更新", "Incremental Update"),
            ("原始快照", "SATB"),
            ("垃圾回收器", "Garbage Collector"),
            ("垃圾收集器", "Garbage Collector"),
            ("垃圾回收算法", "GC Algorithm"),
            ("垃圾收集算法", "GC Algorithm"),
            ("垃圾回收", "GC"),
            ("垃圾收集", "GC"),
            ("垃圾对象", "Garbage Object"),
            ("回收器", "Collector"),
            ("并发收集器", "Concurrent Collector"),
            ("并行收集器", "Parallel Collector"),
            ("串行收集器", "Serial Collector"),
            ("可达性分析算法", "Reachability Analysis"),
            ("可达性分析", "Reachability Analysis"),
            ("可达性", "Reachability"),
            ("不可达", "Unreachable"),
            ("可达", "Reachable"),
            ("引用计数算法", "Reference Counting"),
            ("引用计数法", "Reference Counting"),
            ("引用计数器", "Reference Counter"),
            ("引用计数", "Reference Counting"),
            ("标记-清除算法", "Mark-Sweep Algorithm"),
            ("标记清除算法", "Mark-Sweep Algorithm"),
            ("标记-清除", "Mark-Sweep"),
            ("标记清除", "Mark-Sweep"),
            ("标记-整理算法", "Mark-Compact Algorithm"),
            ("标记整理算法", "Mark-Compact Algorithm"),
            ("标记-整理", "Mark-Compact"),
            ("标记整理", "Mark-Compact"),
            ("标记-复制算法", "Mark-Copy Algorithm"),
            ("标记复制算法", "Mark-Copy Algorithm"),
            ("标记-复制", "Mark-Copy"),
            ("标记复制", "Mark-Copy"),
            ("复制算法", "Copying Algorithm"),
            ("分代收集算法", "Generational Collection"),
            ("分代收集", "Generational Collection"),
            ("分代", "Generational"),
            ("强引用", "Strong Reference"),
            ("软引用", "Soft Reference"),
            ("弱引用", "Weak Reference"),
            ("虚引用", "Phantom Reference"),
            ("引用链", "Reference Chain"),
            ("引用队列", "Reference Queue"),
            ("符号引用", "Symbolic Reference"),
            ("直接引用", "Direct Reference"),
            ("相互引用", "Mutual Reference"),
            ("方法引用", "Method Reference"),
            ("引用类型", "Reference Type"),
            ("引用", "Reference"),
            ("内存泄漏", "Memory Leak"),
            ("内存溢出", "OOM"),
            ("内存分配", "Memory Allocation"),
            ("内存区域", "Memory Area"),
            ("内存快照", "Memory Snapshot"),
            ("空间分配担保", "Allocation Guarantee"),
            ("大对象", "Large Object"),
            ("临时对象", "Temporary Object"),
            ("死亡对象", "Dead Object"),
            ("对象实例", "Object Instance"),
            ("实例对象", "Object Instance"),
            ("本地内存", "Native Memory"),
            ("初始标记", "Initial Mark"),
            ("重新标记", "Remark"),
            ("最终标记", "Final Mark"),
            ("并发标记", "Concurrent Mark"),
            ("晋升", "Promotion"),
            ("吞吐量", "Throughput"),
            ("低延迟", "Low Latency"),
            ("停顿时间", "Pause Time"),
            ("暂停时间", "Pause Time"),
            ("停顿", "Pause"),
            ("即时编译器", "Just-In-Time Compiler"),
            ("即时编译", "JIT"),
            ("编译器", "Compiler"),
            ("解释器", "Interpreter"),
            ("编译期", "Compile-time"),
            ("字节码指令", "Bytecode Instruction"),
            ("字节码验证", "Bytecode Verification"),
            ("字节码", "Bytecode"),
            ("字节", "Byte"),
            ("机器指令", "Machine Instruction"),
            ("操作码", "Opcode"),
            ("操作数", "Operand"),
            ("指令", "Instruction"),
            ("动态链接", "Dynamic Linking"),
            ("返回地址", "Return Address"),
            ("Java 虚拟机", "Java Virtual Machine"),
            ("Java虚拟机", "Java Virtual Machine"),
        ],
    ),
    (
        "Class loading and class file",
        [
            ("启动类加载器", "Bootstrap Class Loader"),
            ("扩展类加载器", "Extension Class Loader"),
            ("平台类加载器", "Platform Class Loader"),
            ("应用类加载器", "Application Class Loader"),
            ("系统类加载器", "System Class Loader"),
            ("自定义类加载器", "Custom Class Loader"),
            ("类加载器", "Class Loader"),
            ("类加载过程", "Class Loading"),
            ("类加载阶段", "Class Loading"),
            ("类加载", "Class Loading"),
            ("类卸载", "Class Unloading"),
            ("双亲委派模型", "Parent Delegation Model"),
            ("双亲委派机制", "Parent Delegation Model"),
            ("双亲委派", "Parent Delegation"),
            ("加载阶段", "Loading"),
            ("验证阶段", "Verification"),
            ("准备阶段", "Preparation"),
            ("解析阶段", "Resolution"),
            ("初始化阶段", "Initialization"),
            ("链接阶段", "Linking"),
            ("类初始化", "Class Initialization"),
            ("初始化", "Initialization"),
            ("运行时常量池", "Runtime Constant Pool"),
            ("字符串常量池", "String Constant Pool"),
            ("常量池", "Constant Pool"),
            ("字符串常量", "String Constant"),
            ("魔数", "Magic Number"),
            ("访问标志", "Access Flag"),
            ("访问修饰符", "Access Modifier"),
            ("字段表", "Field Table"),
            ("方法表", "Method Table"),
            ("属性表", "Attribute Table"),
            ("全限定名", "Fully Qualified Name"),
            ("全类名", "Fully Qualified Class Name"),
            ("二进制名称", "Binary Name"),
            ("描述符", "Descriptor"),
            ("字面量", "Literal"),
            ("父接口", "Superinterface"),
            ("子接口", "Subinterface"),
            ("当前类", "This Class"),
            ("类文件", "Class File"),
            ("类路径", "Classpath"),
            ("类名", "Class Name"),
            ("类对象", "Class Object"),
            ("类变量", "Class Variable"),
            ("类元数据", "Class Metadata"),
        ],
    ),
    (
        "Core language and data structures",
        [
            ("连接（Linking）", "Linking"),
            ("连接(Linking)", "Linking"),
            ("Object 对象", "Object"),
            ("Class 类", "Class"),
            ("面向对象", "Object-Oriented"),
            ("匿名内部类", "Anonymous Inner Class"),
            ("静态内部类", "Static Nested Class"),
            ("成员内部类", "Member Inner Class"),
            ("局部内部类", "Local Inner Class"),
            ("内部类", "Inner Class"),
            ("外部类", "Outer Class"),
            ("抽象类", "Abstract Class"),
            ("包装类", "Wrapper Class"),
            ("工具类", "Utility Class"),
            ("实现类", "Implementation Class"),
            ("测试类", "Test Class"),
            ("枚举类", "Enum"),
            ("父类", "Superclass"),
            ("子类", "Subclass"),
            ("超类", "Superclass"),
            ("函数式接口", "Functional Interface"),
            ("函数式编程", "Functional Programming"),
            ("静态工厂方法", "Static Factory Method"),
            ("工厂方法", "Factory Method"),
            ("构造方法", "Constructor"),
            ("构造函数", "Constructor"),
            ("构造器", "Constructor"),
            ("抽象方法", "Abstract Method"),
            ("静态方法", "Static Method"),
            ("实例方法", "Instance Method"),
            ("成员方法", "Member Method"),
            ("私有方法", "Private Method"),
            ("公共方法", "Public Method"),
            ("公有方法", "Public Method"),
            ("默认方法", "Default Method"),
            ("模板方法", "Template Method"),
            ("钩子方法", "Hook Method"),
            ("方法签名", "Method Signature"),
            ("方法句柄", "Method Handle"),
            ("方法调用", "Method Invocation"),
            ("方法名", "Method Name"),
            ("方法重写", "Method Overriding"),
            ("方法重载", "Method Overloading"),
            ("静态成员变量", "Static Variable"),
            ("成员变量", "Instance Variable"),
            ("实例变量", "Instance Variable"),
            ("静态变量", "Static Variable"),
            ("局部变量表", "Local Variable Table"),
            ("局部变量", "Local Variable"),
            ("临时变量", "Temporary Variable"),
            ("变量", "Variable"),
            ("实例字段", "Instance Field"),
            ("静态字段", "Static Field"),
            ("静态属性", "Static Field"),
            ("字段", "Field"),
            ("实例化", "Instantiation"),
            ("实例", "Instance"),
            ("返回值", "Return Value"),
            ("返回类型", "Return Type"),
            ("参数类型", "Parameter Type"),
            ("基本类型", "Primitive Type"),
            ("数据类型", "Data Type"),
            ("包装类型", "Wrapper Type"),
            ("类型推断", "Type Inference"),
            ("泛型类型", "Generic Type"),
            ("类型", "Type"),
            ("实参", "Argument"),
            ("形参", "Parameter"),
            ("参数", "Parameter"),
            ("重写", "Override"),
            ("重载", "Overload"),
            ("多态性", "Polymorphism"),
            ("多态", "Polymorphism"),
            ("封装性", "Encapsulation"),
            ("泛型", "Generics"),
            ("注解", "Annotation"),
            ("反射", "Reflection"),
            ("枚举", "Enum"),
            ("序列化", "Serialization"),
            ("反序列化", "Deserialization"),
            ("关键字", "Keyword"),
            ("修饰符", "Modifier"),
            ("代码块", "Code Block"),
            ("布尔类型", "Boolean"),
            ("布尔", "Boolean"),
            ("浮点数", "Floating-point Number"),
            ("整型", "Integer"),
            ("字符", "Character"),
            ("字符串", "String"),
            ("常量", "Constant"),
            ("数组", "Array"),
            ("双向链表", "Doubly Linked List"),
            ("单向链表", "Singly Linked List"),
            ("链表", "Linked List"),
            ("红黑树", "Red-Black Tree"),
            ("二叉树", "Binary Tree"),
            ("平衡树", "Balanced Tree"),
            ("跳表", "Skip List"),
            ("哈希表", "Hash Table"),
            ("散列表", "Hash Table"),
            ("哈希冲突", "Hash Collision"),
            ("哈希码", "Hash Code"),
            ("散列", "Hash"),
            ("负载因子", "Load Factor"),
            ("扩容", "Resize"),
            ("并发容器", "Concurrent Container"),
            ("并发修改异常", "ConcurrentModificationException"),
            ("并发安全", "Concurrency-safe"),
            ("并发编程", "Concurrent Programming"),
            ("高并发", "High Concurrency"),
            ("并发", "Concurrency"),
            ("指令级并行", "Instruction-Level Parallelism"),
            ("并行性", "Parallelism"),
            ("并行执行", "Parallel Execution"),
            ("并行", "Parallelism"),
            ("串行", "Serial"),
            ("集合", "Collection"),
            ("容器", "Container"),
            ("数据结构", "Data Structure"),
            ("数据库连接池", "Database Connection Pool"),
            ("数据库连接", "Database Connection"),
            ("连接池", "Connection Pool"),
            ("网络连接", "Network Connection"),
            ("数据库", "Database"),
            ("消息队列", "Message Queue"),
            ("消息积压", "Message Backlog"),
            ("慢查询", "Slow Query"),
            ("深拷贝", "Deep Copy"),
            ("浅拷贝", "Shallow Copy"),
            ("拷贝", "Copy"),
            ("异常处理", "Exception Handling"),
            ("异常释放", "Exception-safe Release"),
            ("异常", "Exception"),
            ("接口", "Interface"),
            ("函数", "Function"),
            ("对象", "Object"),
            ("类", "Class"),
            ("头结点", "Head Node"),
            ("头节点", "Head Node"),
            ("尾结点", "Tail Node"),
            ("尾节点", "Tail Node"),
            ("前驱节点", "Predecessor"),
            ("后继节点", "Successor"),
            ("前置节点", "Predecessor"),
            ("虚拟节点", "Dummy Node"),
            ("虚节点", "Dummy Node"),
            ("节点", "Node"),
            ("状态机", "State Machine"),
            ("生命周期", "Lifecycle"),
            ("性能开销", "Performance Overhead"),
            ("性能调优", "Performance Tuning"),
            ("性能优化", "Performance Optimization"),
            ("性能问题", "Performance Issue"),
            ("高性能", "High Performance"),
            ("性能", "Performance"),
            ("开销", "Overhead"),
            ("读操作", "Read Operation"),
            ("写操作", "Write Operation"),
            ("阻塞操作", "Blocking Operation"),
            ("算法", "Algorithm"),
            ("日志", "Log"),
            ("监控指标", "Monitoring Metric"),
            ("指标", "Metric"),
            ("监控", "Monitoring"),
            ("告警", "Alert"),
            ("快照", "Snapshot"),
            ("转储", "Dump"),
            ("索引", "Index"),
            ("下标", "Index"),
            ("偏移量", "Offset"),
            ("偏移", "Offset"),
            ("地址", "Address"),
            ("寄存器", "Register"),
            ("容量", "Capacity"),
            ("阈值", "Threshold"),
            ("长度", "Length"),
            ("限流", "Rate Limiting"),
            ("熔断", "Circuit Breaking"),
            ("不可降级", "不可 Downgrade"),
            ("降级为", "Downgrade 为"),
            ("降级", "Fallback"),
            ("积压", "Backlog"),
            ("计数器", "Counter"),
            ("任务", "Task"),
            ("递归", "Recursion"),
            ("迭代", "Iteration"),
            ("遍历", "Traversal"),
            ("包名", "Package Name"),
            ("单例模式", "Singleton"),
            ("设计模式", "Design Pattern"),
            ("关闭钩子", "Shutdown Hook"),
            ("钩子", "Hook"),
        ],
    ),
]

FILE_OVERRIDES: dict[str, list[tuple[str, str]]] = {
    "jmm.md": [("本地内存", "Local Memory")],
    "virtual-thread.md": [
        ("挂载", "Mount"),
        ("卸载", "Unmount"),
        ("挂起", "Park"),
        ("载体线程", "Carrier Thread"),
        ("载体", "Carrier"),
    ],
    "jvm-in-action.md": [
        ("下游接口", "Downstream API"),
        ("慢接口", "Slow API"),
        ("接口", "API"),
    ],
    "jvm-intro.md": [("堆栈", "Heap/Stack")],
}

FILE_SKIP = {
    "jvm-in-action.md": {"接口"},
}

ACRONYMS = [
    ("CAS", "Compare-And-Swap (CAS)"),
    ("JMM", "Java Memory Model (JMM)"),
    ("AQS", "AbstractQueuedSynchronizer (AQS)"),
    ("TLAB", "Thread-Local Allocation Buffer (TLAB)"),
    ("SATB", "Snapshot-At-The-Beginning (SATB)"),
    ("JNI", "Java Native Interface (JNI)"),
    ("JIT", "Just-In-Time Compilation (JIT)"),
    ("STW", "Stop-The-World (STW)"),
    ("OOM", "Out of Memory (OOM)"),
    ("JVM", "Java Virtual Machine (JVM)"),
    ("PermGen", "Permanent Generation (PermGen)"),
]

WATCH = [
    "同步",
    "方法",
    "加载",
    "验证",
    "准备",
    "解析",
    "链接",
    "卸载",
    "挂起",
    "唤醒",
    "令牌",
    "延迟",
    "竞争",
    "标记",
    "机制",
    "资源",
    "状态",
    "固定",
]


def all_global_phrases() -> list[tuple[str, str]]:
    phrases: list[tuple[str, str]] = []
    for _, group in GROUPS:
        phrases.extend(group)
    return phrases


def phrases_for(filename: str) -> list[tuple[str, str]]:
    skip = FILE_SKIP.get(filename, set())
    merged: dict[str, str] = {}
    for src, dst in all_global_phrases():
        if src not in skip:
            merged[src] = dst
    for src, dst in FILE_OVERRIDES.get(filename, []):
        merged[src] = dst
    items = list(merged.items())
    items.sort(key=lambda pair: len(pair[0]), reverse=True)
    for index, (src, _) in enumerate(items):
        for later, _ in items[index + 1 :]:
            if len(later) > len(src) and src in later:
                raise RuntimeError(f"phrase order bug: {src!r} is inside later {later!r}")
    return items


class Stash:
    def __init__(self) -> None:
        self.bucket: list[str] = []

    def put(self, value: str) -> str:
        self.bucket.append(value)
        return f"\x00{len(self.bucket) - 1}\x00"

    def restore(self, text: str) -> str:
        pattern = re.compile("\x00" + r"(\d+)" + "\x00")
        previous = None
        while previous != text:
            previous = text
            text = pattern.sub(lambda match: self.bucket[int(match.group(1))], text)
        return text


def stash_frontmatter_tags(text: str, stash: Stash) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, flags=re.S)
    if not match:
        return text
    body = match.group(1)
    lines = body.split("\n")
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("tag:"):
            block = [line]
            index += 1
            if re.match(r"^tag:\s*$", line):
                while index < len(lines) and re.match(r"^[ \t-]", lines[index]):
                    block.append(lines[index])
                    index += 1
            output.append(stash.put("\n".join(block)))
            continue
        output.append(line)
        index += 1
    return text[: match.start(1)] + "\n".join(output) + text[match.end(1) :]


def protect(text: str, stash: Stash) -> str:
    text = stash_frontmatter_tags(text, stash)
    fence_count = len(re.findall(r"```", text))
    if fence_count % 2 != 0:
        raise RuntimeError("unbalanced code fence")

    def fence(match: re.Match[str]) -> str:
        return stash.put(match.group(0))

    text = re.sub(r"```[^\n]*\n.*?```", fence, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", lambda match: stash.put(match.group(0)), text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", lambda match: stash.put(match.group(0)), text)

    def markdown_link(match: re.Match[str]) -> str:
        bang = match.group(1) or ""
        return f"{bang}[{match.group(2)}]({stash.put(match.group(3))})"

    text = re.sub(
        r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)",
        markdown_link,
        text,
    )
    text = re.sub(r"https?://[^\s)>]+", lambda match: stash.put(match.group(0)), text)
    text = re.sub(r"</?[A-Za-z][^>\n]*>", lambda match: stash.put(match.group(0)), text)
    return text


def protect_literals(text: str, stash: Stash) -> str:
    for phrase in sorted(KEEP_INTACT, key=len, reverse=True):
        if phrase in text:
            text = text.replace(phrase, stash.put(phrase))
    return text


NO_SPACE_BEFORE = set("（([<「『【《#*_`，、；：,;:")
NO_SPACE_AFTER = set("）)]>」』】》*_`，。、；：？！,.;:!?")


def is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def boundary_space(before: str, after: str) -> bool:
    if not before or not after or before.isspace() or after.isspace():
        return False
    if before in NO_SPACE_BEFORE or after in NO_SPACE_AFTER:
        return False
    before_cjk = is_cjk(before) or before == "\x00"
    after_cjk = is_cjk(after) or after == "\x00"
    before_latin = before.isascii() and before.isalnum()
    after_latin = after.isascii() and after.isalnum()
    if before in "。！？!?" and after_latin:
        return True
    if before in ")]" and after_cjk:
        return True
    if before_cjk and after in "([":
        return True
    return (before_latin and after_cjk) or (before_cjk and after_latin) or (before_latin and after_latin)


def wrap_term(dst: str, before: str, after: str) -> str:
    if not dst:
        return dst
    left = " " if boundary_space(before, dst[0]) else ""
    right = " " if boundary_space(dst[-1], after) else ""
    return f"{left}{dst}{right}"


def sub_term(text: str, src: str, dst: str) -> str:
    if src not in text:
        return text

    def repl(match: re.Match[str]) -> str:
        left_char = text[match.start() - 1] if match.start() else ""
        right_char = text[match.end()] if match.end() < len(text) else ""
        return wrap_term(dst, left_char, right_char)

    return re.sub(re.escape(src), repl, text)


def normalize_spacing(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        indent = line[: len(line) - len(line.lstrip(" "))]
        body = line[len(indent) :]
        trailing = "  " if body.endswith("  ") else ""
        core = body.rstrip(" ")
        core = re.sub(r" {2,}", " ", core)
        lines.append(indent + core + trailing)
    return "\n".join(lines)


def dedupe_repeated_terms(text: str) -> str:
    names = "JMM|CAS|AQS|OOM|JVM|GC|JIT|JNI|TLAB|Cache|Atomic|Thread|Lock|Class|Object|Method"
    text = re.sub(rf"\b({names})\b(?:\s+\1\b)+", r"\1", text)
    text = re.sub(rf"\b({names}),\1\b", r"\1", text)
    return text


def replace_sync_queue(text: str, stash: Stash) -> str:
    def visible(sentence: str) -> str:
        return re.sub(r"\x00(\d+)\x00", lambda match: stash.bucket[int(match.group(1))], sentence)

    def repl_sentence(match: re.Match[str]) -> str:
        sentence = match.group(0)
        shown = visible(sentence)
        word = (
            "Synchronous Queue"
            if "SynchronousQueue" in shown or "CachedThreadPool" in shown
            else "Sync Queue"
        )
        return sub_term(sentence, "同步队列", word)

    return re.sub(r"[^。！？\n]+[。！？\n]?", repl_sentence, text)


def apply_phrases(text: str, filename: str) -> str:
    for src, dst in phrases_for(filename):
        text = sub_term(text, src, dst)
    return text


def contextual_replace(text: str, pattern: str, dst: str) -> str:
    def repl(match: re.Match[str]) -> str:
        left_char = text[match.start() - 1] if match.start() else ""
        right_char = text[match.end()] if match.end() < len(text) else ""
        return wrap_term(dst, left_char, right_char)

    return re.sub(pattern, repl, text)


def apply_verbs(text: str) -> str:
    text = contextual_replace(text, r"继承(?=[了着过])", "Inherit")
    text = sub_term(text, "继承", "Inheritance")
    text = contextual_replace(text, r"封装(?=[了着过在成])", "Encapsulate")
    text = sub_term(text, "封装", "Encapsulation")
    return text


def package_word(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        right_char = text[match.end()] if match.end() < len(text) else ""
        return wrap_term(f"{match.group(1)} Package", "", right_char)

    text = re.sub(r"(\x00\d+\x00)[ \t]*包", repl, text)
    for src in ("包下", "包中", "包内"):
        text = sub_term(text, src, "Package " + src[-1])
    return text


def phase_headings(text: str) -> str:
    phases = {
        "加载": "Loading",
        "验证": "Verification",
        "准备": "Preparation",
        "解析": "Resolution",
        "链接": "Linking",
        "卸载": "Unloading",
    }
    for chinese, english in phases.items():
        text = re.sub(
            rf"^(#{{2,6}})[ \t]+(?:(\d+(?:\.\d+)*[ \t]+)|([①②③④⑤⑥⑦⑧⑨][ \t]*))?{chinese}[ \t]*$",
            lambda match, english=english: (
                f"{match.group(1)} {match.group(2) or match.group(3) or ''}{english}".replace("  ", " ")
            ),
            text,
            flags=re.M,
        )
    return text


def expand_acronym(text: str, acronym: str, full: str) -> str:
    if full in text:
        return text
    pattern = re.compile(rf"(?<![A-Za-z]){re.escape(acronym)}(?![A-Za-z])")
    return pattern.sub(full, text, count=1)


def expand_gc(text: str) -> str:
    if "Garbage Collection" not in text:
        pattern = re.compile(r"(?<![A-Za-z])GC(?![A-Za-z])")
        for match in pattern.finditer(text):
            before = text[max(0, match.start() - 12) : match.start()]
            after = text[match.end() : match.end() + 8]
            if after.startswith(" Roots"):
                continue
            if re.search(r"(Minor|Major|Full|Young|Mixed)\s*$", before):
                continue
            text = text[: match.start()] + "Garbage Collection (GC)" + text[match.end() :]
            break
    if "Garbage Collection" not in text and "Garbage Collector (GC)" not in text:
        text = text.replace("Garbage Collector", "Garbage Collector (GC)", 1)
    return text


def collapse_bilingual(text: str) -> str:
    pattern = re.compile(r"([A-Za-z][A-Za-z0-9.+#_/ -]{0,80})\s*[（(]\s*([A-Za-z][A-Za-z0-9.+#_/ -]{0,80})\s*[）)]")
    previous = None
    while previous != text:
        previous = text
        current = text

        def repl(match: re.Match[str], current: str = current) -> str:
            left = re.sub(r"\s+", " ", match.group(1).strip())
            right = re.sub(r"\s+", " ", match.group(2).strip())
            if left.lower() != right.lower():
                return match.group(0)
            before = current[match.start() - 1] if match.start() else ""
            after = current[match.end()] if match.end() < len(current) else ""
            return wrap_term(left, before, after)

        text = pattern.sub(repl, current)
    return text


def strip_redundant_gloss(text: str) -> str:
    names = [
        "Java Native Interface",
        "Java Memory Model",
        "Compare-And-Swap",
        "Garbage Collection",
        "Garbage Collector",
        "AbstractQueuedSynchronizer",
        "Permanent Generation",
        "Thread-Local Allocation Buffer",
        "Just-In-Time Compilation",
        "Stop-The-World",
        "Out of Memory",
        "Java Virtual Machine",
        "Snapshot-At-The-Beginning",
    ]
    for name in names:
        text = re.sub(
            rf"({re.escape(name)}(?: \([A-Z][A-Z0-9]+\))?)\s*[（(]\s*{re.escape(name)}\s*[）)]",
            r"\1",
            text,
        )
    return text


def localize(text: str, filename: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    stash = Stash()
    text = protect(text, stash)
    text = protect_literals(text, stash)
    text = replace_sync_queue(text, stash)
    text = apply_phrases(text, filename)
    text = apply_verbs(text)
    text = package_word(text)
    text = sub_term(text, "方法", "Method")
    text = phase_headings(text)
    text = expand_gc(text)
    for acronym, full in ACRONYMS:
        text = expand_acronym(text, acronym, full)
    text = collapse_bilingual(text)
    text = strip_redundant_gloss(text)
    text = dedupe_repeated_terms(text)
    text = normalize_spacing(text)
    text = stash.restore(text)
    if "\x00" in text:
        raise RuntimeError(f"placeholder leaked in {filename}")
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    return text


def render_glossary() -> str:
    lines = [
        "# JavaGuide Terminology Glossary",
        "",
        "Pilot scope: `docs/java/concurrent` and `docs/java/jvm`.",
        "",
        "Chinese explanations stay in Simplified Chinese. The terms below are replaced with the English form used in Java documentation, JVM specifications, and backend interviews.",
        "",
        "Acronyms are expanded on the first standalone occurrence in each article (`Garbage Collection (GC)`, `Java Memory Model (JMM)`, `Compare-And-Swap (CAS)`, `AbstractQueuedSynchronizer (AQS)`, and the same pattern for TLAB, SATB, JNI, JIT, STW, OOM, and JVM).",
        "",
        "Site `tag:` values are left unchanged so article tags stay shared with the rest of the site.",
        "",
    ]
    for title, pairs in GROUPS:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Chinese | English |")
        lines.append("| --- | --- |")
        seen: set[str] = set()
        for src, dst in pairs:
            if src in seen:
                continue
            seen.add(src)
            if dst in {"CAS", "JMM", "GC", "OOM", "TLAB", "SATB", "JNI", "JIT", "PermGen"}:
                dst = f"{dst} (expanded on first use)"
            lines.append(f"| {src} | {dst} |")
        lines.append("")
    lines.extend(
        [
            "## File-specific choices",
            "",
            "| File | Chinese | English | Why |",
            "| --- | --- | --- | --- |",
            "| `jmm.md` | 本地内存 | Local Memory | JMM abstract per-thread memory, not native memory |",
            "| other JVM docs | 本地内存 | Native Memory | Metaspace, direct memory, NMT |",
            "| `virtual-thread.md` | 挂载 / 卸载 / 挂起 | Mount / Unmount / Park | Virtual-thread scheduling terms |",
            "| `jvm-in-action.md` | 接口 | API | Service/HTTP API, not a Java interface |",
            "| `jvm-intro.md` | 堆栈 | Heap/Stack | Keyword lists both memory areas |",
            "| thread-pool docs near `SynchronousQueue` | 同步队列 | Synchronous Queue | The queue implementation |",
            "| AQS docs | 同步队列 | Sync Queue | CLH queue inside AQS |",
            "",
            "## Ambiguous terms left in Chinese",
            "",
            "These were not force-translated. Context decides the English term, or the word is an ordinary verb/noun rather than a named concept.",
            "",
            "| Chinese | Why it was left |",
            "| --- | --- |",
            "| 同步 (bare) | Can mean `synchronized`, synchronous, or synchronization. Compounds such as 同步方法 and 同步器 are converted. |",
            "| 加载 / 验证 / 准备 / 解析 / 链接 | Ordinary verbs, and also class-loading phases. Exact phase headings and “阶段” compounds are converted. |",
            "| 挂起 / 唤醒 | AQS uses park/unpark; `wait/notify` uses suspend/wake. Only virtual-thread 挂起 is converted to Park. |",
            "| 令牌 | Semaphore articles use it for a permit; other texts may mean a token. |",
            "| 延迟 | Latency in GC, delay in DelayQueue, or the ordinary verb. 低延迟 and 延迟队列 are converted. |",
            "| 竞争 | Verb “contend for”, not always Contention or a race. 竞态条件 and 锁竞争 are converted. |",
            "| 标记 | GC mark phase versus a stamp/flag. Named mark phases and algorithms are converted. |",
            "| 机制 / 状态 / 资源 | Ordinary Chinese in this corpus unless part of a named term (Locking Mechanism, Thread State, Shared Resource). |",
            "| 方法 when it means “approach” | 这种方法, 实现方法, 解决方法, 计算方法, 判断方法, and a few fixed phrases. |",
            "| 这类 / 类似 / 分类 / 一类 | “kind” or “similar”, not Java Class. |",
            "| 异常情况 / 异常实例 | Abnormal condition or unhealthy instance, not a Java exception. |",
            "| 固定 | Ordinary “fixed”. Virtual-thread Pinning is already written in English where the article defines it. |",
            "| 值传递 | In this pilot it means passing a ThreadLocal value or a return value, not Java pass-by-value. |",
            "| 运行时 | Often “when running”, not the noun Runtime. Compounds such as 运行时数据区 and 运行时常量池 are converted. |",
            "| 缓存 | Kept when it is the verb “to cache”. 缓存行, 缓存一致性, and CPU 缓存 are converted. |",
            "| 连接 | Network connection versus class-loading Linking. 连接池 and 数据库连接 are converted; 连接（Linking） becomes Linking. |",
            "| 降级 | Fallback in reliability text. Lock downgrade is Downgrade, not Fallback. |",
            "| 锁升级 | Lock Inflation for HotSpot biased/lightweight/heavyweight. Read-write lock upgrade is Upgrade. |",
            "",
            "## Intentional differences from the short examples",
            "",
            "- `操作` stays Chinese when it is the ordinary word “operation”. Named forms such as Atomic Operation are converted.",
            "- `数据库` is converted to Database. It is standard interview vocabulary.",
            "- `生命周期` is converted to Lifecycle.",
            "- Existing English acronyms are expanded once per article when the full name is not already present.",
            "",
        ]
    )
    return "\n".join(lines)


def run_tests() -> None:
    cases = [
        (
            "cas.md",
            "线程池可以有效地管理线程的生命周期，减少频繁创建和销毁线程带来的性能开销。",
            "Thread Pool 可以有效地管理 Thread 的 Lifecycle，减少频繁创建和销毁 Thread 带来的 Performance Overhead。",
        ),
        (
            "jvm-garbage-collection.md",
            "垃圾回收器通过可达性分析算法判断对象是否存活。",
            "Garbage Collector (GC) 通过 Reachability Analysis 判断 Object 是否存活。",
        ),
        (
            "optimistic-lock-and-pessimistic-lock.md",
            "乐观锁通常使用 CAS 操作实现，而悲观锁通常依赖数据库锁机制。",
            "Optimistic Lock 通常使用 Compare-And-Swap (CAS) 操作实现，而 Pessimistic Lock 通常依赖 Database Locking Mechanism。",
        ),
        (
            "basis.md",
            "在 Java 中，类是对象的模板。对象通过构造方法创建，可以调用类中定义的方法，并访问成员变量。",
            "在 Java 中，Class 是 Object 的模板。 Object 通过 Constructor 创建，可以调用 Class 中定义的 Method，并访问 Instance Variable。",
        ),
        (
            "java-lock.md",
            "这种方法可以解决死锁。类似的数据结构有三类实现。",
            "这种方法可以解决 Deadlock。类似的 Data Structure 有三类实现。",
        ),
        (
            "jmm.md",
            "JMM（Java 内存模型）抽象了线程和主内存、本地内存的关系。不可达对象不会出现在这里。",
            "Java Memory Model (JMM) 抽象了 Thread 和 Main Memory、Local Memory 的关系。 Unreachable Object 不会出现在这里。",
        ),
        (
            "memory-area.md",
            "元空间使用的是本地内存。锁定（lock）作用于主内存。",
            "Metaspace 使用的是 Native Memory。 lock 作用于 Main Memory。",
        ),
        (
            "aqs.md",
            "```java\n// 线程和锁不要翻译\nsynchronized (lock) {}\n```\n见 [线程](./jmm.md#线程) 和 https://example.com/线程。",
            "```java\n// 线程和锁不要翻译\nsynchronized (lock) {}\n```\n见 [Thread](./jmm.md#线程) 和 https://example.com/线程。",
        ),
        (
            "class-loading-process.md",
            "### 加载\n\n类加载阶段之后是验证。\n",
            "### Loading\n\nClass Loading 之后是验证。\n",
        ),
        (
            "jvm-in-action.md",
            "下游接口超时，慢接口需要限流。",
            "Downstream API Timeout，Slow API 需要 Rate Limiting。",
        ),
        (
            "java-thread-pool-summary.md",
            "CachedThreadPool 使用同步队列 `SynchronousQueue`。AQS 的同步队列不同。",
            "CachedThreadPool 使用 Synchronous Queue `SynchronousQueue`。AbstractQueuedSynchronizer (AQS) 的 Sync Queue 不同。",
        ),
    ]
    failed = False
    for filename, source, expected in cases:
        actual = localize(source, filename)
        if actual != expected:
            failed = True
            print(f"FAIL {filename}")
            print(f"  expected: {expected}")
            print(f"  actual:   {actual}")
    if failed:
        raise SystemExit(1)


def watch_report(files: list[Path]) -> str:
    lines = ["# Remaining ambiguous terms in the pilot", ""]
    for path in files:
        text = path.read_text(encoding="utf-8")
        hits = []
        for term in WATCH:
            count = text.count(term)
            if count:
                hits.append(f"{term}×{count}")
        if hits:
            lines.append(f"- `{path.relative_to(ROOT).as_posix()}`: {', '.join(hits)}")
    return "\n".join(lines) + "\n"


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    run_tests()
    files = sorted(path for directory in PILOT_DIRS for path in directory.glob("*.md"))
    changed = 0
    for path in files:
        original = path.read_bytes().decode("utf-8")
        updated = localize(original, path.name)
        if updated != original:
            changed += 1
            if not dry_run:
                path.write_bytes(updated.encode("utf-8"))
    glossary = render_glossary()
    if not dry_run:
        GLOSSARY_PATH.write_text(glossary, encoding="utf-8", newline="\n")
    print(f"files={len(files)} changed={changed} dry_run={dry_run}")


if __name__ == "__main__":
    main()
