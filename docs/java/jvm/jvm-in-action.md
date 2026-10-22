---
title: Java 后端线上问题排查：CPU、内存、Garbage Collection (GC)、Thread Pool、Database 与 Redis
description: Java 后端线上故障排查指南，覆盖 Alert 确认、止血留证、CPU 飙高、Out of Memory (OOM)、频繁 GC、Thread Pool 与 Connection Pool 耗尽、慢 SQL、Redis Blocking、Message Backlog 和故障复盘。
category: Java
tag:
  - JVM
  - 线上排查
  - 性能调优
  - Java面试
sitemap:
  changefreq: monthly
  priority: 0.9
head:
  - - meta
    - name: keywords
      content: Java线上问题排查,Java Virtual Machine (JVM)故障排查,CPU飙高,OOM排查,Full GC,Thread Pool 耗尽,Connection Pool 耗尽,慢SQL,Redis故障,MQ Backlog
---

Alert 刚响，排查很容易被 Monitoring 页面上最显眼的那条曲线带着走。看到 CPU 高就抓 Thread Stack，看到 Full GC 就查 Heap，发布刚结束就准备回滚。可这些现象经常互相传导：慢 SQL 会占住 Database Connection，Connection Pool 等待又会拖住 Business Thread，最后可能同时看到延迟、错误率和 CPU 上升。单看其中一项，很难定根因。

故障还在扩大时，先按预案控制影响。 Instance 还有余量，确认取证不会继续压垮服务后，再保存 Log、Trace、Thread Stack 和内存信息。重启往往能暂时恢复，但也会清掉现场；为了抓取 Heap Dump 一直让异常实例承载流量，同样可能把问题拖大。现场情况决定先摘流量、回滚，还是先取证。

下面只讨论 Java 应用侧的常见问题。如果证据已经指向 Container 调度、内核、网络设备或云平台，需要转到相应平台的 Monitoring 和操作手册继续排查，这里不展开。

::: warning 生产环境操作提醒
线上执行诊断命令前，先看 Instance 是否仍在承载流量、磁盘还有多少空间，以及命令本身的 Overhead。连续抓 Thread Stack 要控制频率；Heap Dump、Class 直方图和主动 GC 可能带来明显的 CPU、I/O 或 Pause。 Instance 已经接近不可用时，先摘流量或止损，别为了留现场继续扛着业务流量。
:::

## 收到 Alert 后先确认什么？

收到 Alert 后先看用户侧有没有 Exception。单个 Instance CPU 高，但请求仍能被其他 Instance 正常承接，和整个服务的错误率一起上升不是一个级别。还要排除 Monitoring 误报、Metric 采集延迟，以及下游 Timeout 把 Thread 堵在本服务里的情况。

把 Alert 前后十几分钟的请求量、错误率、P95/P99、CPU、内存、GC、Thread Pool 和 Connection Pool 曲线放在一起看，再对照发布、配置变更、定时 Task 和流量突增的时间点。 Database、Redis、Message Queue 和外部 API 的 Alert 也要拉进来。沿着时间线确认哪些 API 和用户受到了影响、Exception 从什么时候开始、最早变化的是哪项 Metric。

平均响应时间正常，也不代表请求都正常。少量超慢请求可能正好卡在登录、下单或支付等关键链路上，这时 P95/P99、Timeout 率和业务成功率更有参考价值。

## 止血和留证怎么取舍？

故障仍在扩大时，先按预案止血。常见措施包括回滚最近版本、摘除异常实例、关闭有问题的定时 Task、Rate Limiting、Circuit Breaking、Fallback 非核心功能以及 Resize。每项措施都有副作用：Resize 可能继续压垮 Database，Retry 会放大下游流量，回滚也未必能兼容已经变更的数据。

条件允许时，在重启或回滚前保留这些信息：

- Alert 发生前后的 Monitoring 截图或时间范围。
- 应用 Log、访问 Log、GC Log 和变更记录。
- 一到三份间隔数秒的 Thread Stack，而不是只留一份。
- Trace 中的慢调用、错误调用和上下游耗时。
- Process CPU、RSS、Heap、Thread Count、文件 Descriptor 和 Network Connection 状态。
- Database Slow Query、Lock 等待、Connection Pool 状态、Redis 慢命令和 MQ 消费 Backlog。

Instance 已经摘除流量，也不要马上假设它可以安全做 Heap Dump。 Dump 大 Heap 需要足够磁盘空间和 I/O，某些命令还可能触发较长 Pause。更稳妥的做法是在启动 Parameter 中提前配置 OOM 自动 Dump，并把 Dump 文件写到 Capacity 和权限都合适的目录。

```bash
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/path/with/enough/space
```

## 怎样快速判断问题在哪一层？

暂时没有调用链线索时，先按现象选择排查入口。表里的对应关系不能替代后续验证。

| 现象 | 优先检查 |
| ------------------------- | -------------------------------------------------------- |
| CPU 高，API 同时变慢 | 热点 Thread、Infinite Loop、Serialization、Lock Contention、频繁 GC |
| CPU 不高，Load 很高 | 磁盘 I/O、Uninterruptible 睡眠、网络存储、Container CPU 限额 |
| RSS 持续上涨，Java Heap 稳定 | Direct Memory、Thread Stack、Metaspace、Java Native Interface (JNI)、本地库和内存映射 |
| Old 区回收后仍持续上涨 | 长 Lifecycle Object、无界缓存、Collection 持有、监听器或 ThreadLocal |
| Thread Count 和 Queue Length 上涨 | 下游变慢、Lock 等待、Task 处理变慢、Thread Pool 隔离不足 |
| Database Connection Pool 等待上涨 | 慢 SQL、长事务、连接泄漏、Database Capacity 不足 |
| Redis RT 上涨 | 慢命令、大 Key、热 Key、网络抖动、Connection Pool 等待 |
| MQ Lag 持续上涨 | 消费变慢、分区不均、Exception 消息 Retry、下游 Capacity 不足 |

问题也可能跨层传播。一个慢 SQL 占住 Database Connection，Business Thread 随后 Blocking 在 Connection Pool，Thread Pool Queue 开始堆积，上游 Timeout 后 Retry，最终看到的是 CPU、延迟和错误率一起上升。排查时要按时间线确认哪个 Metric 最先变化。

## CPU 飙高怎么排查？

先确认高 CPU 来自哪个 Process，再找到 Process 内占用 CPU 的 Thread。下面是 Linux 上常见的排查方式：

```bash
# 找到 Java 进程
jps -l

# 查看进程内各线程的 CPU 使用情况
top -H -p <pid>

# 也可以按线程查看一段时间内的 CPU 使用
pidstat -t -p <pid> 1
```

`top -H` 里看到的是十进制 Thread ID，而 Thread Stack 中的 `nid` 通常使用十六进制。先转换，再到 Thread Stack 里查对应 Thread：

```bash
printf '%x\n' <tid>
jcmd <pid> Thread.print > /tmp/thread-dump.txt
```

Thread Stack 需要连续抓几份。某个 Thread 只在一份 Stack 里执行 JSON Serialization，可能只是恰好采样到；多份 Stack 都停在同一段代码，才值得继续检查。常见原因包括：

- 无法退出的 Loop 或 Recursion。
- Large Object Serialization、正则回溯和加解密等计算 Task。
- 大量 Object 分配引发频繁 GC。
- Multithreading 争用同一把 Lock，伴随 Context Switch。
- 流量上涨或 Retry 放大，CPU 只是正常做了更多工作。

CPU 已经接近打满时，不要同时启动多个高 Overhead 诊断 Task。先摘除部分流量或选择一个异常实例取证，避免诊断操作继续抢占资源。

## CPU 不高但 Load 很高怎么办？

Linux Load Average 统计运行中和 Uninterruptible 睡眠的 Task。磁盘、网络存储或某些内核 I/O 等待严重时，CPU 使用率可能不高，Load 仍会持续上升。

```bash
vmstat 1
iostat -xz 1
pidstat -d -p <pid> 1
```

重点观察 `vmstat` 中的运行 Queue、I/O 等待和 Blocking Task，以及 `iostat` 中设备利用率、等待时间和 Queue。`iostat`、`pidstat` 通常由 sysstat 软件包提供，线上环境是否可用要提前确认。

## API 很慢但 CPU 不高怎么排查？

这类问题经常发生在等待上：等 Database Connection、等下游响应、等 Lock、等 Thread Pool Task 或者等磁盘 I/O。

先从 Trace 找到耗时最长的一段。如果没有 Trace，可以结合访问 Log 里的请求耗时、Database Slow Query、客户端 Connection Pool Metric 和 Thread Stack 缩小范围。 Thread Stack 中常见的状态包括：

- 大量 Thread 停在 Database Connection Pool 的 `getConnection()`，检查 Connection Pool 等待、活跃连接、慢 SQL 和长事务。
- 大量 Thread 停在 HTTP 客户端读取响应，检查下游延迟、Timeout 配置和 Retry 次数。
- 大量 Thread 处于 `BLOCKED`，检查 Lock 持有者和 Critical Section 内的慢操作。
- Business Thread 空闲但 Task Queue 堆积，检查 Consumer Thread、Task 提交方式和执行器状态。

一次慢请求的总耗时应能和各阶段对上。若 Trace 只记录了业务 Method 耗时，Connection Pool 等待、Thread Pool 排队和客户端 DNS/TLS 时间没有被记录，中间会出现一段无法解释的空白，需要补充相应 Monitoring 或埋点。

## 内存持续上涨和 OOM 怎么排查？

先分清上涨的是 Java Heap、Process RSS 还是 Container 总内存。`-Xmx` 只限制 Java Heap，Process 还会使用 Metaspace、Code Cache、Thread Stack、Direct Memory、GC 自身 Data Structure 和本地库内存。

先查看 JVM 和系统两边的数据：

```bash
jcmd <pid> GC.heap_info
jcmd <pid> VM.flags
jcmd <pid> VM.native_memory summary
```

`VM.native_memory` 依赖 Native Memory Tracking（NMT），需要在 JVM 启动时开启，例如 `-XX:NativeMemoryTracking=summary`。它会带来额外 Overhead，不能在故障发生后临时补开。

NMT 主要统计 JVM/HotSpot 自身管理的 Native Memory，无法覆盖 JNI 或第三方本地库的全部 Memory Allocation。RSS 持续上涨而 NMT 没有对应变化时，还要借助 Operating System 和 Native Memory 分析工具继续排查。

常见 OOM 信息对应不同方向：

| OOM 信息 | 常见排查方向 |
| -------------------------------- | ------------------------------------------------------ |
| `Java heap space` | Large Object、Object 持有、无界 Collection、缓存、一次查询返回过多数据 |
| `GC overhead limit exceeded` | Heap 接近耗尽，GC 花费大量时间但回收很少 |
| `Metaspace` | 动态 Class 生成、Class Loader 泄漏、Metaspace 上限过小 |
| `Direct buffer memory` | NIO Direct Memory、Netty Buffer、释放延迟或上限不合理 |
| `unable to create native thread` | Thread Count 过多、Process 限制、Container 内存不足、Single Thread Stack 过大 |

Heap Dump 可以使用 MAT、VisualVM 等工具分析。先看占用最大的 Object、Dominator Tree、到 GC Roots 的 Reference Chain 和可疑 Class Loader，不要只根据 Object 数量下结论。

需要手动 Dump 时，可以使用：

```bash
jcmd <pid> GC.heap_dump filename=/path/with/enough/space/heap.hprof
```

这个命令可能对应用产生明显影响。执行前应评估 Heap Size、磁盘余量、I/O 和 Pause 风险。生产 Instance 仍在承载流量时，优先在摘流量后的异常实例操作。`jmap -dump:live` 可能触发 Full GC，不适合当作无风险命令直接执行。

## 怎么判断是 Memory Leak 还是正常增长？

观察完整 GC 之后的 Heap 占用。如果业务流量和数据规模稳定，Old 区在多次完整回收后仍持续抬升，才需要重点怀疑 Object 无法释放。缓存预热、Class Loading 和流量增长也会让 Heap 在启动后逐步上升，它们不一定是泄漏。

分析时还要看 Object 为什么被持有。一个 `Map` 很大，只能说明它占用内存；继续沿 Reference Chain 找到无界缓存、静态 Collection、监听器、ThreadLocal 或错误的会话 Lifecycle，才能确认修复位置。

## Young GC 频繁怎么排查？

Young GC 频繁通常表示 Object 分配速度快或 Young Generation Capacity 不足。先看分配速率、每次回收后的存活量和 Pause Time，再判断是否需要改代码或调 Parameter。

```bash
jstat -gcutil <pid> 1000 10
jcmd <pid> GC.heap_info
```

常见原因包括一次查询加载大量 Object、API 返回超大结果、Log 或 Serialization 创建大量 Temporary Object、批处理没有控制批次，以及 Young Generation 设置与负载不匹配。

调整 Young Generation 只能改变 GC 节奏，无法修复无界查询和高分配代码。先通过 GC Log、JFR、分配采样或压测确认 Object 从哪里产生。改 Parameter 后要在相同流量和数据条件下比较吞吐、P95/P99、GC 次数和总 Pause Time。

## Full GC 频繁怎么排查？

先从 GC Log 确认触发原因、回收前后占用和 Pause Time。不同收集器的 Log Field 和触发原因并不完全相同，不能把所有 Full GC 都归结为“Old Generation 满了”。

排查时重点看：

- Old 区在回收后能否明显下降。
- Large Object 和 Promotion Object 是否过多。
- Metaspace 是否接近上限。
- 是否存在显式 `System.gc()` 或诊断工具触发。
- Heap Size、Container 内存限制和收集器配置是否匹配。
- GC 之前是否先出现流量上涨、批 Task 或缓存刷新。

回收后占用仍然很高，继续分析 Object 持有；回收效果正常但很快再次填满，重点查分配速率、Promotion 速度和 Heap Capacity。修改 JVM Parameter 以前，先确认应用行为，否则加大 Heap 只会延后下一次故障，并可能增加 Pause 或 Dump 成本。

## Thread Pool Queue 堆积怎么排查？

Thread Pool 问题不能只看 Active Thread 数。至少要同时 Monitoring：

- `corePoolSize`、`maximumPoolSize` 和 Current Thread 数。
- Active Thread 数、Queue Length 和 Queue Capacity。
- Task 提交速率、完成速率、等待时间和执行时间。
- 拒绝次数以及具体 Rejection Policy。

Queue 持续上涨，表示 Task 进入速度高于完成速度。原因可能是突发流量，也可能是 Task 本身变慢，例如 Database Connection 等待、下游 Timeout 或者 Lock Contention。直接增加 Thread Count 会增加对 Database、Redis 和外部 API 的 Concurrency 访问，可能把问题推到下游。

按下面的顺序排查：

1. 确认哪些业务 Task 使用这个 Thread Pool，是否有无关 Task 混用。
2. 比较提交速率、完成速率、排队时间和执行时间。
3. 抽取正在运行 Task 的 Thread Stack，确认它们在计算还是等待。
4. 检查 Database、HTTP 和 Redis Connection Pool 是否同步耗尽。
5. 根据 Task 重要性决定 Rate Limiting、Fallback、Resize、隔离或丢弃策略。

`CallerRunsPolicy` 会让提交 Task 的 Thread 自己执行 Task，可以暂时减慢提交速度，但 Web 请求 Thread 因此被长 Task 占住后，API 延迟也会升高。它适不适合 Current Thread 池，需要结合调用方和 Task Type 判断。

## Database Connection Pool 耗尽怎么排查？

Connection Pool 耗尽时，先看活跃连接、空闲连接、等待 Thread 和获取连接耗时。 Business Thread 大量等待连接，通常继续沿三个方向检查：

- SQL 执行慢，连接长时间无法归还。
- 事务范围过大，包含远程调用、文件处理或大量计算。
- 代码没有在所有分支正确关闭连接，出现连接泄漏。

Database 侧再检查当前会话、Slow Query、Lock 等待、长事务和 Instance 资源。MySQL 可以结合 `SHOW PROCESSLIST`、Slow Query Log、Performance Schema、`EXPLAIN` 和 InnoDB 事务 Lock 信息定位。执行计划来自当前 SQL、Parameter 和数据分布，测试库里“走 Index”不能证明生产环境一定相同。

扩充 Connection Pool 之前要确认 Database 还能承受更多 Concurrency。应用 Instance 数乘以每个 Instance 的 Connection Pool 上限，才是 Database 可能面对的总连接数；服务 Resize 后，这个总数也会跟着增加。

相关内容：[MySQL 执行计划分析](../../database/mysql/mysql-query-execution-plan.md)、[SQL 优化总结](../../high-performance/sql-optimization.md)。

## Redis 变慢怎么排查？

应用访问 Redis 变慢时，先区分客户端等待和服务端执行。 Connection Pool 耗尽、网络抖动、DNS 问题都会让一次 Redis 调用变慢，即使命令本身执行很快。

Redis 服务端重点看：

- 命令延迟和慢 Log。
- CPU、内存、网络流量和连接数。
- 大 Key、热 Key、过期删除以及持久化操作。
- 主从复制延迟、集群状态和故障切换。

`SLOWLOG GET` 记录的是命令在 Redis 服务端的执行时间，不包含排队和网络传输。应用总耗时很高而 Slow Log 正常时，继续检查 Connection Pool 等待、网络和客户端处理。

排查大 Key 时可以使用 `redis-cli --bigkeys` 等工具，但它需要扫描键空间，会增加额外负载。生产环境应选择低峰期、从 Node 或受控采样，并提前确认命令对当前版本和集群的影响。不要在线上直接执行 `KEYS *`。

热 Key 需要结合访问频率和 Node 负载确认。只看 Key 的体积找不到读取次数特别高的小 Key；可以使用代理层、客户端统计、Monitoring 平台或受控的热点 Key 分析能力获取证据。

相关内容：[Redis 常见面试题](../../database/redis/redis-questions-02.md)。

## Message Queue Backlog 怎么排查？

先比较生产速率和消费速率，并确认 Backlog 集中在哪个 Topic、Queue 或分区。随后检查 Consumer Instance 是否存活、消费 Thread 是否 Blocking、单条消息处理时间是否变化，以及下游 Database 和 API 是否变慢。

常见原因包括：

- 流量上涨，生产速度超过设计 Capacity。
- 某类消息处理变慢，拖住整个分区或 Queue。
- Exception 消息不断 Retry，形成 Retry 风暴。
- 分区分配不均或 Consumer 频繁 Rebalance。
- 消费成功后提交位点失败，造成重复消费。
- 下游 Database、Redis 或外部 API 成为瓶颈。

增加 Consumer 是否有效取决于 Message Queue 模型。Kafka 同一消费组里的有效 Parallelism 度受分区数限制；Consumer 继续增加但没有分区可分配，不会提高吞吐。即使增加分区和 Consumer，也要确认下游 Capacity，避免消费恢复后把 Backlog 流量一次性打到 Database。

处理 Backlog 期间还要保证幂等，Monitoring 消费错误和死信。需要跳过 Exception 消息时，应保留消息内容和失败原因，后续补偿，而不是直接丢弃。

相关内容：[Message Queue 常见问题](../../high-performance/message-queue/message-queue.md)。

## Downstream API Timeout 怎么排查？

先把一次调用的时间拆开：Connection Pool 等待、DNS、TCP 建连、TLS 握手、请求发送、服务端处理和响应读取。不同阶段需要不同的 Timeout 配置，只设置一个总 Timeout 不容易判断时间花在哪里。

检查调用方时重点看：

- 连接 Timeout、读取 Timeout 和调用链总预算。
- HTTP Connection Pool 的活跃连接、Wait Queue 和连接复用。
- Retry 次数、退避策略以及哪些错误会触发 Retry。
- Circuit Breaking 器状态、Fallback 结果和首次请求成功率。

下游已经变慢时，多层 Retry 会迅速放大流量。网关、业务服务和 SDK 各 Retry 三次，最坏情况下会产生远超一次调用的请求量。先限制 Retry 层级和总预算，再根据 API 是否幂等决定能不能 Retry。

## 用一条 Slow API 串起排查过程

假设订单查询 API 在一次版本发布后 P99 上升，错误率也开始增加，按下面的顺序排查。这个例子用于说明 Method，不代表真实生产事故。

1. 从 Monitoring 确认问题开始于发布后，集中在新版本 Instance 和订单查询 API。
2. 暂停继续发布，摘除部分异常实例，错误率下降，先控制影响范围。
3. 对比新旧 Instance 的 Trace，发现大部分时间消耗在获取 Database Connection 和执行查询。
4. Connection Pool Monitoring 显示等待 Thread 增加，Database Slow Query 出现同一条 SQL。
5. 使用生产 Parameter 对应的查询条件查看执行计划，发现新加的筛选条件使原联合 Index 无法有效过滤，并伴随额外排序。
6. 在接近生产数据分布的测试环境修改查询和 Index，比较扫描行数、P95/P99、CPU 和连接占用。
7. 变更经过灰度后继续观察 Slow Query、Connection Pool 等待和业务错误率，再逐步恢复流量。
8. 复盘时补充相应查询场景的 Performance 测试和发布后 Monitoring 项。

在这个假设场景中，Thread Pool 和 Connection Pool 堆积出现在慢 SQL 之后；执行计划和 Slow Query 记录把根因指向了 SQL。若第 4 步发现 SQL 很快、时间主要花在 Connection Pool 外，就要回到其他假设继续验证。

## 修复以后怎么验证？

代码或配置修复以后，还要确认用户侧 Metric 恢复、临时措施可以撤销，并且没有引入新的数据问题。

验证时对比故障前、故障中和修复后的同一组 Metric：请求量、P95/P99、错误率、业务成功率、CPU、内存、GC、Thread Pool、Connection Pool 和依赖延迟。涉及重复消费、库存、订单和资金状态时，还要做数据对账。

Performance 改动需要在相近的数据量、流量模型、机器配置和缓存状态下比较。只跑一次单 API 压测，不能代表整条业务链路已经恢复。具体可以参考：[Performance 测试和压力测试入门](../../high-availability/performance-test.md)。

## 故障复盘应该记录什么？

复盘要留下能在下次故障里直接使用的材料。文档至少保留：

- 故障时间线、影响范围和用户表现。
- 直接原因、触发条件以及故障为什么会扩大。
- 止血、定位和修复过程中使用的证据。
- 哪些 Monitoring、预案或测试没有发挥作用。
- 后续改进项、负责人和完成时间。

“开发加强代码检查”很难验证是否完成。改进项应落到具体机制，例如给 Connection Pool 等待时间增加 Alert、限制批量查询条数、为消息消费补幂等测试、给发布流程增加关键 API 对比检查。

## 面试中怎么回答线上故障排查？

面试官问“线上 CPU 飙高怎么处理”，可以先回答通用顺序，再结合自己做过的案例：

> 我会先确认影响范围、流量和最近变更，判断是否需要摘 Instance、Rate Limiting 或回滚。条件允许时保留 Monitoring、Log 和多份 Thread Stack。CPU 确实来自 Java Process 后，用 `top -H` 或 `pidstat -t` 找热点 Thread，把 Thread ID 转为十六进制后和 Thread Stack 中的 `nid` 对应。连续采样确认 Thread 长期停在哪段代码，再结合 GC、Trace 和流量判断是计算热点、Infinite Loop、Lock Contention 还是频繁 GC。修复后使用相同场景验证，并补 Monitoring 和回归测试。

如果没有处理过真实生产故障，可以说明自己在测试环境演练过哪些场景，以及参考过什么案例。不要把阅读过的文章说成亲自负责的事故。

## 常用工具速查

| 工具 | 常见用途 | 使用提醒 |
| ------------------ | ------------------------------ | ------------------------------------- |
| `top`、`pidstat` | Process 和 Thread CPU、I/O | 先确认 Container 和宿主机观察口径 |
| `vmstat`、`iostat` | 系统运行 Queue、内存和磁盘 | 需要结合一段时间趋势 |
| `jcmd` | Thread Stack、Heap 信息、JFR、Class 直方图 | 部分命令 Overhead 较高，执行前评估 |
| `jstat` | GC 和各 Memory Area 变化 | 连续采样比单点数据更有用 |
| JFR、JMC | CPU、分配、Lock、I/O 等事件分析 | 采集配置要结合线上 Overhead |
| MAT、VisualVM | Heap Dump 分析 | 重点看 Reference Chain 和 GC Roots |
| Arthas | Method 耗时、Thread、Class 和运行时诊断 | 高流量 Method 执行 Trace/Watch 要限制范围 |
| Trace/Monitoring 平台 | 请求链、错误率、延迟和依赖 | 关注采样率、脱敏和时间同步 |

## 推荐阅读

- [JDK Monitoring 和故障处理工具总结](./jdk-monitoring-and-troubleshooting-tools.md)
- [最重要的 JVM Parameter 总结](./jvm-parameters-intro.md)
- [JVM GC 详解](./jvm-garbage-collection.md)
- [Java Thread Pool 详解](../concurrent/java-thread-pool-summary.md)
- [Deadlock 详解](../../cs-basics/operating-system/dead-lock.md)
- [Oracle Java 故障排查指南：Memory Leak](https://docs.oracle.com/en/java/javase/17/troubleshoot/troubleshooting-memory-leaks.html)
- [Redis 延迟问题排查](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)
- [Redis Slow Log](https://redis.io/docs/latest/commands/slowlog/)
- [一次线上 OOM 问题分析](https://juejin.cn/post/7205141492264976445)
- [Java 中 9 种常见的 CMS GC 问题分析与解决](https://tech.meituan.com/2020/11/12/java-9-cms-gc.html)

<!-- @include: @article-footer.snippet.md -->
