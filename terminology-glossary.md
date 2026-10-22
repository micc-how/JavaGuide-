# JavaGuide Terminology Glossary

Pilot scope: `docs/java/concurrent` and `docs/java/jvm`.

Chinese explanations stay in Simplified Chinese. The terms below are replaced with the English form used in Java documentation, JVM specifications, and backend interviews.

Acronyms are expanded on the first standalone occurrence in each article (`Garbage Collection (GC)`, `Java Memory Model (JMM)`, `Compare-And-Swap (CAS)`, `AbstractQueuedSynchronizer (AQS)`, and the same pattern for TLAB, SATB, JNI, JIT, STW, OOM, and JVM).

Site `tag:` values are left unchanged so article tags stay shared with the rest of the site.

## Java concurrency and locks

| Chinese | English |
| --- | --- |
| 线程池 | Thread Pool |
| 核心线程数 | Core Pool Size |
| 最大线程数 | Maximum Pool Size |
| 非核心线程 | Non-core Thread |
| 核心线程 | Core Thread |
| 空闲线程 | Idle Thread |
| 工作线程 | Worker Thread |
| 活跃线程 | Active Thread |
| 调用者线程 | Caller Thread |
| 当前线程 | Current Thread |
| 守护线程 | Daemon Thread |
| 用户线程 | User Thread |
| 虚拟线程 | Virtual Thread |
| 平台线程 | Platform Thread |
| 载体线程 | Carrier Thread |
| 主线程 | Main Thread |
| 子线程 | Child Thread |
| 父线程 | Parent Thread |
| 业务线程 | Business Thread |
| 线程安全性 | Thread Safety |
| 线程不安全 | Not Thread-safe |
| 非线程安全 | Non-thread-safe |
| 线程安全 | Thread-safe |
| 线程本地变量 | Thread-Local Variable |
| 线程本地 | Thread-local |
| 线程快照 | Thread Dump |
| 线程转储 | Thread Dump |
| 线程堆栈 | Thread Stack |
| 线程状态 | Thread State |
| 线程调度 | Thread Scheduling |
| 线程复用 | Thread Reuse |
| 线程同步 | Thread Synchronization |
| 线程通信 | Inter-thread Communication |
| 线程中断 | Thread Interrupt |
| 线程饥饿 | Thread Starvation |
| 线程数量 | Thread Count |
| 线程数 | Thread Count |
| 线程组 | Thread Group |
| 线程工厂 | Thread Factory |
| 默认线程工厂 | Default Thread Factory |
| 多线程编程 | Multithreaded Programming |
| 多线程 | Multithreading |
| 单线程 | Single Thread |
| 线程 | Thread |
| 多进程 | Multi-process |
| 进程 | Process |
| 死锁 | Deadlock |
| 活锁 | Livelock |
| 饥饿 | Starvation |
| 竞态条件 | Race Condition |
| 竞争条件 | Race Condition |
| 临界区 | Critical Section |
| 上下文切换 | Context Switch |
| 上下文 | Context |
| 用户态 | User Mode |
| 内核态 | Kernel Mode |
| 时间片轮转 | Round-Robin |
| 时间片 | Time Slice |
| 抢占式调度 | Preemptive Scheduling |
| 协同式调度 | Cooperative Scheduling |
| 调度器 | Scheduler |
| 操作系统 | Operating System |
| 不可中断 | Uninterruptible |
| 可中断 | Interruptible |
| 中断状态 | Interrupt Status |
| 中断标记 | Interrupt Flag |
| 中断 | Interrupt |
| 非阻塞队列 | Non-blocking Queue |
| 阻塞队列 | Blocking Queue |
| 非阻塞 | Non-blocking |
| 阻塞锁 | Blocking Lock |
| 阻塞 | Blocking |
| 异步编排 | Asynchronous Orchestration |
| 异步 | Asynchronous |
| 自旋等待 | Spin-Wait |
| 自适应自旋 | Adaptive Spinning |
| 自旋锁 | Spin Lock |
| 自旋 | Spin |
| 原子性 | Atomicity |
| 原子操作 | Atomic Operation |
| 原子更新 | Atomic Update |
| Atomic 原子类 | Atomic Class |
| 原子类 | Atomic Class |
| 原子 | Atomic |
| 比较并交换（CAS） | CAS (expanded on first use) |
| 比较并交换(CAS) | CAS (expanded on first use) |
| 比较并交换 | CAS (expanded on first use) |
| 乐观读 | Optimistic Read |
| 悲观读 | Pessimistic Read |
| 乐观锁 | Optimistic Lock |
| 悲观锁 | Pessimistic Lock |
| 非公平锁 | Nonfair Lock |
| 公平锁 | Fair Lock |
| 非公平 | Nonfair |
| 不公平 | Unfair |
| 公平性 | Fairness |
| 公平 | Fair |
| 可重入性 | Reentrancy |
| 可重入锁 | Reentrant Lock |
| 可重入 | Reentrant |
| 读写锁 | Read-Write Lock |
| 读锁 | Read Lock |
| 写锁 | Write Lock |
| 互斥锁 | Mutex |
| 不互斥 | Non-exclusive |
| 互斥 | Mutual Exclusion |
| 分段锁 | Segmented Lock |
| 排他锁 | Exclusive Lock |
| 独占锁 | Exclusive Lock |
| 共享锁 | Shared Lock |
| 偏向锁 | Biased Lock |
| 轻量级锁 | Lightweight Lock |
| 重量级锁 | Heavyweight Lock |
| 同步锁 | Intrinsic Lock |
| 对象锁 | Object Lock |
| 类锁 | Class Lock |
| 行锁 | Row Lock |
| 表锁 | Table Lock |
| 锁升级 | Lock Inflation |
| 锁消除 | Lock Elimination |
| 锁粗化 | Lock Coarsening |
| 锁竞争 | Lock Contention |
| 无锁 | Lock-Free |
| 无 Lock | Lock-Free |
| 锁机制 | Locking Mechanism |
| 尝试获取锁 | Try Acquire |
| 获取锁 | Acquire Lock |
| 释放锁 | Release Lock |
| 持有锁 | Hold Lock |
| 加锁 | Locking |
| 解锁（unlock） | unlock |
| 解锁 | Unlock |
| 锁定（lock） | lock |
| 锁定 | Lock |
| 锁 | Lock |
| 独占模式 | Exclusive Mode |
| 共享模式 | Shared Mode |
| 共享资源 | Shared Resource |
| 共享变量 | Shared Variable |
| 共享 | Shared |
| 独占 | Exclusive |
| 管程 | Monitor |
| 监视器锁 | Monitor Lock |
| 对象监视器 | Object Monitor |
| 监视器 | Monitor |
| 同步方法 | Synchronized Method |
| 同步代码块 | Synchronized Block |
| 同步块 | Synchronized Block |
| 同步器 | Synchronizer |
| 同步状态 | Synchronization State |
| 同步操作 | Synchronization Action |
| 同步机制 | Synchronization Mechanism |
| 条件队列 | Condition Queue |
| 等待队列 | Wait Queue |
| 任务队列 | Task Queue |
| 工作队列 | Work Queue |
| 延迟队列 | Delay Queue |
| 优先队列 | Priority Queue |
| 双端队列 | Deque |
| 变体队列 | Variant Queue |
| 队列 | Queue |
| 拒绝策略 | Rejection Policy |
| 默认拒绝策略 | Default Rejection Policy |
| 饱和策略 | Saturation Policy |
| 反压 | Backpressure |
| 优雅关闭 | Graceful Shutdown |
| 入队 | Enqueue |
| 出队 | Dequeue |
| 重入次数 | Reentrancy Count |
| 重入 | Reentrant |
| 许可数量 | Permit Count |
| 许可证 | Permit |
| 许可数 | Permit Count |
| 内存栅栏 | Memory Fence |
| 循环栅栏 | CyclicBarrier |
| 栅栏 | Barrier |
| 倒计时器 | CountDownLatch |
| 生产者-消费者 | Producer-Consumer |
| 生产者 | Producer |
| 消费者 | Consumer |
| 回调方法 | Callback Method |
| 回调 | Callback |
| 版本号 | Version |
| 时间戳 | Timestamp |
| 复合操作 | Compound Operation |
| 唯一约束 | Unique Constraint |
| 忙等 | Busy-Waiting |
| 死循环 | Infinite Loop |
| 循环引用 | Circular Reference |
| 循环 | Loop |
| 超时 | Timeout |
| 重试 | Retry |

## JMM and memory ordering

| Chinese | English |
| --- | --- |
| JMM（Java 内存模型） | JMM (expanded on first use) |
| JMM(Java 内存模型) | JMM (expanded on first use) |
| JMM（Java内存模型） | JMM (expanded on first use) |
| JMM(Java内存模型) | JMM (expanded on first use) |
| Java内存模型JMM | JMM (expanded on first use) |
| Java 内存模型JMM | JMM (expanded on first use) |
| Java内存模型 JMM | JMM (expanded on first use) |
| Java 内存模型 JMM | JMM (expanded on first use) |
| JMMJava内存模型 | JMM (expanded on first use) |
| JMM Java内存模型 | JMM (expanded on first use) |
| Java 内存模型（JMM） | JMM (expanded on first use) |
| Java 内存模型(JMM) | JMM (expanded on first use) |
| Java内存模型（JMM） | JMM (expanded on first use) |
| Java内存模型(JMM) | JMM (expanded on first use) |
| Java 内存模型 | JMM (expanded on first use) |
| Java内存模型 | JMM (expanded on first use) |
| 内存可见性 | Memory Visibility |
| 可见性 | Visibility |
| 有序性 | Ordering |
| 指令重排序 | Instruction Reordering |
| 指令重排 | Instruction Reordering |
| 指令并行重排 | Instruction-Parallel Reordering |
| 编译器优化重排 | Compiler Reordering |
| 重排序 | Reordering |
| 重排 | Reordering |
| 内存屏障 | Memory Barrier |
| 读屏障 | Read Barrier |
| 写屏障 | Write Barrier |
| 伪共享 | False Sharing |
| 缓存行 | Cache Line |
| 缓存一致性协议 | Cache Coherence Protocol |
| 缓存一致协议 | Cache Coherence Protocol |
| 缓存一致性 | Cache Coherence |
| 高速缓存 | Cache |
| CPU 缓存 | CPU Cache |
| CPU缓存 | CPU Cache |
| 缓存模型 | Cache Model |
| 硬件内存模型 | Hardware Memory Model |
| 缓冲区 | Buffer |
| 主内存 | Main Memory |
| 主存 | Main Memory |
| 工作内存 | Working Memory |
| 内存模型 | Memory Model |

## JVM memory and garbage collection

| Chinese | English |
| --- | --- |
| 运行时数据区域 | Runtime Data Area |
| 运行时数据区 | Runtime Data Area |
| 程序计数器 | Program Counter |
| Java 虚拟机栈 | JVM Stack |
| Java虚拟机栈 | JVM Stack |
| 虚拟机栈 | JVM Stack |
| 本地方法栈 | Native Method Stack |
| 操作数栈 | Operand Stack |
| 本地方法接口（Java Native Interface） | JNI (expanded on first use) |
| 本地方法接口(Java Native Interface) | JNI (expanded on first use) |
| JNI（Java Native Interface） | JNI (expanded on first use) |
| JNI(Java Native Interface) | JNI (expanded on first use) |
| JNI（本地方法接口） | JNI (expanded on first use) |
| JNI(本地方法接口) | JNI (expanded on first use) |
| 本地方法接口 | JNI (expanded on first use) |
| 本地方法 | Native Method |
| 方法区 | Method Area |
| 直接内存 | Direct Memory |
| 堆外内存 | Off-heap Memory |
| 非堆内存 | Non-heap Memory |
| 堆内存 | Heap Memory |
| 堆转储快照 | Heap Dump |
| 堆转储 | Heap Dump |
| 堆空间 | Heap Space |
| 堆大小 | Heap Size |
| 堆溢出 | Heap OOM |
| 栈溢出 | StackOverflow |
| 栈空间 | Stack Space |
| 线程栈 | Thread Stack |
| 调用堆栈 | Call Stack |
| 方法堆栈 | Call Stack |
| 堆栈信息 | Stack Trace |
| 堆栈 | Stack Trace |
| 入栈 | Push |
| 出栈 | Pop |
| 压栈 | Push |
| 弹栈 | Pop |
| 栈帧 | Stack Frame |
| 堆 | Heap |
| 栈 | Stack |
| 元空间 | Metaspace |
| 永久代 | PermGen (expanded on first use) |
| 年轻代 | Young Generation |
| 新生代 | Young Generation |
| 老年代 | Old Generation |
| 幸存区 | Survivor Space |
| 幸存者区 | Survivor Space |
| 类元数据 | Class Metadata |
| 元数据 | Metadata |
| 对象头 | Object Header |
| 标记字段（Mark Word） | Mark Word |
| 标记字段(Mark Word) | Mark Word |
| 标记字段 | Mark Word |
| 类型指针 | Klass Pointer |
| 实例数据 | Instance Data |
| 对齐填充 | Alignment Padding |
| 指针碰撞 | Bump-the-Pointer |
| 空闲列表 | Free List |
| 线程本地分配缓冲区 | TLAB (expanded on first use) |
| 线程本地分配缓冲 | TLAB (expanded on first use) |
| 本地分配缓冲 | TLAB (expanded on first use) |
| 逃逸分析 | Escape Analysis |
| 标量替换 | Scalar Replacement |
| 栈上分配 | Stack Allocation |
| 直接指针 | Direct Pointer |
| 句柄 | Handle |
| 指针 | Pointer |
| 空指针异常 | NullPointerException |
| 空指针 | Null Pointer |
| 安全点 | Safepoint |
| 安全区域 | Safe Region |
| 三色标记 | Tri-color Marking |
| 浮动垃圾 | Floating Garbage |
| 记忆集 | Remembered Set |
| 卡表 | Card Table |
| 增量更新 | Incremental Update |
| 原始快照 | SATB (expanded on first use) |
| 垃圾回收器 | Garbage Collector |
| 垃圾收集器 | Garbage Collector |
| 垃圾回收算法 | GC Algorithm |
| 垃圾收集算法 | GC Algorithm |
| 垃圾回收 | GC (expanded on first use) |
| 垃圾收集 | GC (expanded on first use) |
| 垃圾对象 | Garbage Object |
| 回收器 | Collector |
| 并发收集器 | Concurrent Collector |
| 并行收集器 | Parallel Collector |
| 串行收集器 | Serial Collector |
| 可达性分析算法 | Reachability Analysis |
| 可达性分析 | Reachability Analysis |
| 可达性 | Reachability |
| 不可达 | Unreachable |
| 可达 | Reachable |
| 引用计数算法 | Reference Counting |
| 引用计数法 | Reference Counting |
| 引用计数器 | Reference Counter |
| 引用计数 | Reference Counting |
| 标记-清除算法 | Mark-Sweep Algorithm |
| 标记清除算法 | Mark-Sweep Algorithm |
| 标记-清除 | Mark-Sweep |
| 标记清除 | Mark-Sweep |
| 标记-整理算法 | Mark-Compact Algorithm |
| 标记整理算法 | Mark-Compact Algorithm |
| 标记-整理 | Mark-Compact |
| 标记整理 | Mark-Compact |
| 标记-复制算法 | Mark-Copy Algorithm |
| 标记复制算法 | Mark-Copy Algorithm |
| 标记-复制 | Mark-Copy |
| 标记复制 | Mark-Copy |
| 复制算法 | Copying Algorithm |
| 分代收集算法 | Generational Collection |
| 分代收集 | Generational Collection |
| 分代 | Generational |
| 强引用 | Strong Reference |
| 软引用 | Soft Reference |
| 弱引用 | Weak Reference |
| 虚引用 | Phantom Reference |
| 引用链 | Reference Chain |
| 引用队列 | Reference Queue |
| 符号引用 | Symbolic Reference |
| 直接引用 | Direct Reference |
| 相互引用 | Mutual Reference |
| 方法引用 | Method Reference |
| 引用类型 | Reference Type |
| 引用 | Reference |
| 内存泄漏 | Memory Leak |
| 内存溢出 | OOM (expanded on first use) |
| 内存分配 | Memory Allocation |
| 内存区域 | Memory Area |
| 内存快照 | Memory Snapshot |
| 空间分配担保 | Allocation Guarantee |
| 大对象 | Large Object |
| 临时对象 | Temporary Object |
| 死亡对象 | Dead Object |
| 对象实例 | Object Instance |
| 实例对象 | Object Instance |
| 本地内存 | Native Memory |
| 初始标记 | Initial Mark |
| 重新标记 | Remark |
| 最终标记 | Final Mark |
| 并发标记 | Concurrent Mark |
| 晋升 | Promotion |
| 吞吐量 | Throughput |
| 低延迟 | Low Latency |
| 停顿时间 | Pause Time |
| 暂停时间 | Pause Time |
| 停顿 | Pause |
| 即时编译器 | Just-In-Time Compiler |
| 即时编译 | JIT (expanded on first use) |
| 编译器 | Compiler |
| 解释器 | Interpreter |
| 编译期 | Compile-time |
| 字节码指令 | Bytecode Instruction |
| 字节码验证 | Bytecode Verification |
| 字节码 | Bytecode |
| 字节 | Byte |
| 机器指令 | Machine Instruction |
| 操作码 | Opcode |
| 操作数 | Operand |
| 指令 | Instruction |
| 动态链接 | Dynamic Linking |
| 返回地址 | Return Address |
| Java 虚拟机 | Java Virtual Machine |
| Java虚拟机 | Java Virtual Machine |

## Class loading and class file

| Chinese | English |
| --- | --- |
| 启动类加载器 | Bootstrap Class Loader |
| 扩展类加载器 | Extension Class Loader |
| 平台类加载器 | Platform Class Loader |
| 应用类加载器 | Application Class Loader |
| 系统类加载器 | System Class Loader |
| 自定义类加载器 | Custom Class Loader |
| 类加载器 | Class Loader |
| 类加载过程 | Class Loading |
| 类加载阶段 | Class Loading |
| 类加载 | Class Loading |
| 类卸载 | Class Unloading |
| 双亲委派模型 | Parent Delegation Model |
| 双亲委派机制 | Parent Delegation Model |
| 双亲委派 | Parent Delegation |
| 加载阶段 | Loading |
| 验证阶段 | Verification |
| 准备阶段 | Preparation |
| 解析阶段 | Resolution |
| 初始化阶段 | Initialization |
| 链接阶段 | Linking |
| 类初始化 | Class Initialization |
| 初始化 | Initialization |
| 运行时常量池 | Runtime Constant Pool |
| 字符串常量池 | String Constant Pool |
| 常量池 | Constant Pool |
| 字符串常量 | String Constant |
| 魔数 | Magic Number |
| 访问标志 | Access Flag |
| 访问修饰符 | Access Modifier |
| 字段表 | Field Table |
| 方法表 | Method Table |
| 属性表 | Attribute Table |
| 全限定名 | Fully Qualified Name |
| 全类名 | Fully Qualified Class Name |
| 二进制名称 | Binary Name |
| 描述符 | Descriptor |
| 字面量 | Literal |
| 父接口 | Superinterface |
| 子接口 | Subinterface |
| 当前类 | This Class |
| 类文件 | Class File |
| 类路径 | Classpath |
| 类名 | Class Name |
| 类对象 | Class Object |
| 类变量 | Class Variable |
| 类元数据 | Class Metadata |

## Core language and data structures

| Chinese | English |
| --- | --- |
| 连接（Linking） | Linking |
| 连接(Linking) | Linking |
| Object 对象 | Object |
| Class 类 | Class |
| 面向对象 | Object-Oriented |
| 匿名内部类 | Anonymous Inner Class |
| 静态内部类 | Static Nested Class |
| 成员内部类 | Member Inner Class |
| 局部内部类 | Local Inner Class |
| 内部类 | Inner Class |
| 外部类 | Outer Class |
| 抽象类 | Abstract Class |
| 包装类 | Wrapper Class |
| 工具类 | Utility Class |
| 实现类 | Implementation Class |
| 测试类 | Test Class |
| 枚举类 | Enum |
| 父类 | Superclass |
| 子类 | Subclass |
| 超类 | Superclass |
| 函数式接口 | Functional Interface |
| 函数式编程 | Functional Programming |
| 静态工厂方法 | Static Factory Method |
| 工厂方法 | Factory Method |
| 构造方法 | Constructor |
| 构造函数 | Constructor |
| 构造器 | Constructor |
| 抽象方法 | Abstract Method |
| 静态方法 | Static Method |
| 实例方法 | Instance Method |
| 成员方法 | Member Method |
| 私有方法 | Private Method |
| 公共方法 | Public Method |
| 公有方法 | Public Method |
| 默认方法 | Default Method |
| 模板方法 | Template Method |
| 钩子方法 | Hook Method |
| 方法签名 | Method Signature |
| 方法句柄 | Method Handle |
| 方法调用 | Method Invocation |
| 方法名 | Method Name |
| 方法重写 | Method Overriding |
| 方法重载 | Method Overloading |
| 静态成员变量 | Static Variable |
| 成员变量 | Instance Variable |
| 实例变量 | Instance Variable |
| 静态变量 | Static Variable |
| 局部变量表 | Local Variable Table |
| 局部变量 | Local Variable |
| 临时变量 | Temporary Variable |
| 变量 | Variable |
| 实例字段 | Instance Field |
| 静态字段 | Static Field |
| 静态属性 | Static Field |
| 字段 | Field |
| 实例化 | Instantiation |
| 实例 | Instance |
| 返回值 | Return Value |
| 返回类型 | Return Type |
| 参数类型 | Parameter Type |
| 基本类型 | Primitive Type |
| 数据类型 | Data Type |
| 包装类型 | Wrapper Type |
| 类型推断 | Type Inference |
| 泛型类型 | Generic Type |
| 类型 | Type |
| 实参 | Argument |
| 形参 | Parameter |
| 参数 | Parameter |
| 重写 | Override |
| 重载 | Overload |
| 多态性 | Polymorphism |
| 多态 | Polymorphism |
| 封装性 | Encapsulation |
| 泛型 | Generics |
| 注解 | Annotation |
| 反射 | Reflection |
| 枚举 | Enum |
| 序列化 | Serialization |
| 反序列化 | Deserialization |
| 关键字 | Keyword |
| 修饰符 | Modifier |
| 代码块 | Code Block |
| 布尔类型 | Boolean |
| 布尔 | Boolean |
| 浮点数 | Floating-point Number |
| 整型 | Integer |
| 字符 | Character |
| 字符串 | String |
| 常量 | Constant |
| 数组 | Array |
| 双向链表 | Doubly Linked List |
| 单向链表 | Singly Linked List |
| 链表 | Linked List |
| 红黑树 | Red-Black Tree |
| 二叉树 | Binary Tree |
| 平衡树 | Balanced Tree |
| 跳表 | Skip List |
| 哈希表 | Hash Table |
| 散列表 | Hash Table |
| 哈希冲突 | Hash Collision |
| 哈希码 | Hash Code |
| 散列 | Hash |
| 负载因子 | Load Factor |
| 扩容 | Resize |
| 并发容器 | Concurrent Container |
| 并发修改异常 | ConcurrentModificationException |
| 并发安全 | Concurrency-safe |
| 并发编程 | Concurrent Programming |
| 高并发 | High Concurrency |
| 并发 | Concurrency |
| 指令级并行 | Instruction-Level Parallelism |
| 并行性 | Parallelism |
| 并行执行 | Parallel Execution |
| 并行 | Parallelism |
| 串行 | Serial |
| 集合 | Collection |
| 容器 | Container |
| 数据结构 | Data Structure |
| 数据库连接池 | Database Connection Pool |
| 数据库连接 | Database Connection |
| 连接池 | Connection Pool |
| 网络连接 | Network Connection |
| 数据库 | Database |
| 消息队列 | Message Queue |
| 消息积压 | Message Backlog |
| 慢查询 | Slow Query |
| 深拷贝 | Deep Copy |
| 浅拷贝 | Shallow Copy |
| 拷贝 | Copy |
| 异常处理 | Exception Handling |
| 异常释放 | Exception-safe Release |
| 异常 | Exception |
| 接口 | Interface |
| 函数 | Function |
| 对象 | Object |
| 类 | Class |
| 头结点 | Head Node |
| 头节点 | Head Node |
| 尾结点 | Tail Node |
| 尾节点 | Tail Node |
| 前驱节点 | Predecessor |
| 后继节点 | Successor |
| 前置节点 | Predecessor |
| 虚拟节点 | Dummy Node |
| 虚节点 | Dummy Node |
| 节点 | Node |
| 状态机 | State Machine |
| 生命周期 | Lifecycle |
| 性能开销 | Performance Overhead |
| 性能调优 | Performance Tuning |
| 性能优化 | Performance Optimization |
| 性能问题 | Performance Issue |
| 高性能 | High Performance |
| 性能 | Performance |
| 开销 | Overhead |
| 读操作 | Read Operation |
| 写操作 | Write Operation |
| 阻塞操作 | Blocking Operation |
| 算法 | Algorithm |
| 日志 | Log |
| 监控指标 | Monitoring Metric |
| 指标 | Metric |
| 监控 | Monitoring |
| 告警 | Alert |
| 快照 | Snapshot |
| 转储 | Dump |
| 索引 | Index |
| 下标 | Index |
| 偏移量 | Offset |
| 偏移 | Offset |
| 地址 | Address |
| 寄存器 | Register |
| 容量 | Capacity |
| 阈值 | Threshold |
| 长度 | Length |
| 限流 | Rate Limiting |
| 熔断 | Circuit Breaking |
| 不可降级 | 不可 Downgrade |
| 降级为 | Downgrade 为 |
| 降级 | Fallback |
| 积压 | Backlog |
| 计数器 | Counter |
| 任务 | Task |
| 递归 | Recursion |
| 迭代 | Iteration |
| 遍历 | Traversal |
| 包名 | Package Name |
| 单例模式 | Singleton |
| 设计模式 | Design Pattern |
| 关闭钩子 | Shutdown Hook |
| 钩子 | Hook |

## File-specific choices

| File | Chinese | English | Why |
| --- | --- | --- | --- |
| `jmm.md` | 本地内存 | Local Memory | JMM abstract per-thread memory, not native memory |
| other JVM docs | 本地内存 | Native Memory | Metaspace, direct memory, NMT |
| `virtual-thread.md` | 挂载 / 卸载 / 挂起 | Mount / Unmount / Park | Virtual-thread scheduling terms |
| `jvm-in-action.md` | 接口 | API | Service/HTTP API, not a Java interface |
| `jvm-intro.md` | 堆栈 | Heap/Stack | Keyword lists both memory areas |
| thread-pool docs near `SynchronousQueue` | 同步队列 | Synchronous Queue | The queue implementation |
| AQS docs | 同步队列 | Sync Queue | CLH queue inside AQS |

## Ambiguous terms left in Chinese

These were not force-translated. Context decides the English term, or the word is an ordinary verb/noun rather than a named concept.

| Chinese | Why it was left |
| --- | --- |
| 同步 (bare) | Can mean `synchronized`, synchronous, or synchronization. Compounds such as 同步方法 and 同步器 are converted. |
| 加载 / 验证 / 准备 / 解析 / 链接 | Ordinary verbs, and also class-loading phases. Exact phase headings and “阶段” compounds are converted. |
| 挂起 / 唤醒 | AQS uses park/unpark; `wait/notify` uses suspend/wake. Only virtual-thread 挂起 is converted to Park. |
| 令牌 | Semaphore articles use it for a permit; other texts may mean a token. |
| 延迟 | Latency in GC, delay in DelayQueue, or the ordinary verb. 低延迟 and 延迟队列 are converted. |
| 竞争 | Verb “contend for”, not always Contention or a race. 竞态条件 and 锁竞争 are converted. |
| 标记 | GC mark phase versus a stamp/flag. Named mark phases and algorithms are converted. |
| 机制 / 状态 / 资源 | Ordinary Chinese in this corpus unless part of a named term (Locking Mechanism, Thread State, Shared Resource). |
| 方法 when it means “approach” | 这种方法, 实现方法, 解决方法, 计算方法, 判断方法, and a few fixed phrases. |
| 这类 / 类似 / 分类 / 一类 | “kind” or “similar”, not Java Class. |
| 异常情况 / 异常实例 | Abnormal condition or unhealthy instance, not a Java exception. |
| 固定 | Ordinary “fixed”. Virtual-thread Pinning is already written in English where the article defines it. |
| 值传递 | In this pilot it means passing a ThreadLocal value or a return value, not Java pass-by-value. |
| 运行时 | Often “when running”, not the noun Runtime. Compounds such as 运行时数据区 and 运行时常量池 are converted. |
| 缓存 | Kept when it is the verb “to cache”. 缓存行, 缓存一致性, and CPU 缓存 are converted. |
| 连接 | Network connection versus class-loading Linking. 连接池 and 数据库连接 are converted; 连接（Linking） becomes Linking. |
| 降级 | Fallback in reliability text. Lock downgrade is Downgrade, not Fallback. |
| 锁升级 | Lock Inflation for HotSpot biased/lightweight/heavyweight. Read-write lock upgrade is Upgrade. |

## Intentional differences from the short examples

- `操作` stays Chinese when it is the ordinary word “operation”. Named forms such as Atomic Operation are converted.
- `数据库` is converted to Database. It is standard interview vocabulary.
- `生命周期` is converted to Lifecycle.
- Existing English acronyms are expanded once per article when the full name is not already present.
