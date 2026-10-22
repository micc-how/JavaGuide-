---
title: CompletableFuture 详解
description: CompletableFuture Asynchronous 编程详解：全面讲解CompletableFuture核心API、Asynchronous Task 编排、thenCompose/thenCombine组合、allOf/anyOf聚合、Thread Pool 配置与最佳实践。
category: Java
tag:
  - Java并发
head:
  - - meta
    - name: keywords
      content: CompletableFuture,Asynchronous 编程,Asynchronous Orchestration,Future,thenCompose,thenCombine,allOf,Parallelism Task
---

实际项目中，一个 Interface 可能需要同时获取多种不同的数据，然后再汇总返回，这种场景还是挺常见的。举个例子：用户请求获取订单信息，可能需要同时获取用户信息、商品详情、物流信息、商品推荐等数据。

如果是 Serial（按顺序依次执行每个 Task）执行的话，Interface 的响应速度会非常慢。考虑到这些 Task 之间有大部分都是 **无前后顺序关联** 的，可以 **Parallel Execution**，就比如说调用获取商品详情的时候，可以同时调用获取物流信息。通过 Parallel Execution 多个 Task 的方式，Interface 的响应速度会得到大幅优化。

![](https://oss.javaguide.cn/github/javaguide/high-performance/serial-to-parallel.png)

对于存在前后调用顺序关系的 Task，可以进行 Task 编排。

![](https://oss.javaguide.cn/github/javaguide/high-performance/serial-to-parallel2.png)

1. 获取用户信息之后，才能调用商品详情和物流信息 Interface。
2. 成功获取商品详情和物流信息之后，才能调用商品推荐 Interface。

可能会用到 Multithreading Asynchronous Task 编排的场景（这里只是举例，数据不一定是一次返回，可能会对 Interface 进行拆分）：

1. 首页：例如技术社区的首页可能需要同时获取文章推荐列表、广告栏、文章排行榜、热门话题等信息。
2. 详情页：例如技术社区的文章详情页可能需要同时获取作者信息、文章详情、文章评论等信息。
3. 统计模块：例如技术社区的后台统计模块可能需要同时获取粉丝数汇总、文章数据（阅读量、评论量、收藏量）汇总等信息。

对于 Java 程序来说，Java 8 才被引入的 `CompletableFuture` 可以帮助我们来做多个 Task 的编排，功能非常强大。

这篇文章是 `CompletableFuture` 的简单入门，带大家看看 `CompletableFuture` 常用的 API。

## Future 介绍

`Future` Interface 是 Asynchronous 思想的典型运用，主要用在一些需要执行耗时 Task 的场景，避免程序一直原地等待耗时 Task 执行完成，执行效率太低。具体来说是这样的：当我们执行某一耗时的 Task 时，可以将这个耗时 Task 交给一个 Child Thread 去 Asynchronous 执行，同时我们可以干点其他事情，不用傻傻等待耗时 Task 执行完成。等我们的事情干完后，我们再通过 `Future` 获取到耗时 Task 的执行结果。这样一来，程序的执行效率就明显提高了。

这其实就是 Multithreading 中经典的 **Future 模式**，你可以将其看作是一种 Design Pattern，核心思想是 Asynchronous 调用，主要用在 Multithreading 领域，并非 Java 语言独有。

在 Java 中，`Future` 是一个 Generics Interface，位于 `java.util.concurrent` Package 下。它有 5 个经典 Abstract Method，主要包括下面 4 Class 功能；JDK 19 起又增加了 `resultNow()`、`exceptionNow()` 和 `state()` 三个默认查询 Method。

- 取消 Task；
- 判断 Task 是否被取消;
- 判断 Task 是否已经执行完成;
- 获取 Task 执行结果。

```java
// V 代表了Future执行的任务返回值的类型
public interface Future<V> {
    // 取消任务执行
    // 成功取消返回 true，否则返回 false
    boolean cancel(boolean mayInterruptIfRunning);
    // 判断任务是否被取消
    boolean isCancelled();
    // 判断任务是否已经执行完成
    boolean isDone();
    // 获取任务执行结果
    V get() throws InterruptedException, ExecutionException;
    // 指定时间内没有返回计算结果就抛出 TimeoutException 异常
    V get(long timeout, TimeUnit unit)
        throws InterruptedException, ExecutionException, TimeoutException;
}
```

简单理解就是：我有一个 Task，提交给了 `Future` 来处理。 Task 执行期间我自己可以去做任何想做的事情。并且，在这期间我还可以取消 Task 以及获取 Task 的执行状态。一段时间之后，我就可以 `Future` 那里直接取出 Task 执行结果。

## CompletableFuture 介绍

`Future` 在实际使用过程中存在一些局限性，比如不支持 Asynchronous Task 的编排组合、获取计算结果的 `get()` Method 为 Blocking 调用。

Java 8 才被引入 `CompletableFuture` Class 可以解决 `Future` 的这些缺陷。`CompletableFuture` 除了提供了更为好用和强大的 `Future` 特性之外，还提供了 Functional Programming、Asynchronous Task 编排组合（可以将多个 Asynchronous Task 串联起来，组成一个完整的链式调用）等能力。

下面我们来简单看看 `CompletableFuture` Class 的定义。

```java
public class CompletableFuture<T> implements Future<T>, CompletionStage<T> {
}
```

可以看到，`CompletableFuture` 同时实现了 `Future` 和 `CompletionStage` Interface。

![](https://oss.javaguide.cn/github/javaguide/java/concurrent/completablefuture-class-diagram.jpg)

`CompletableFuture` 除了提供了更为好用和强大的 `Future` 特性之外，还提供了 Functional Programming 的能力。

![](https://oss.javaguide.cn/javaguide/image-20210902092441434.png)

`Future` Interface 有 5 个 Method：

- `boolean cancel(boolean mayInterruptIfRunning)`：尝试取消执行 Task。
- `boolean isCancelled()`：判断 Task 是否被取消。
- `boolean isDone()`：判断 Task 是否已经被执行完成。
- `get()`：等待 Task 执行完成并获取运算结果。
- `get(long timeout, TimeUnit unit)`：多了一个 Timeout 时间。

`CompletionStage` Interface 描述了一个 Asynchronous 计算的阶段。很多计算可以分成多个阶段或步骤，此时可以通过它将所有步骤组合起来，形成 Asynchronous 计算的流水线。

`CompletionStage` Interface 中的 Method 比较多，`CompletableFuture` 的 Function 式能力就是这个 Interface 赋予的。从这个 Interface 的 Method Parameter 你就可以发现其大量使用了 Java8 引入的 Functional Programming。

![](https://oss.javaguide.cn/javaguide/image-20210902093026059.png)

由于 Method 众多，所以这里不能一一讲解，下文中我会介绍大部分常见 Method 的使用。

## CompletableFuture 常见操作

### 创建 CompletableFuture

常见的创建 `CompletableFuture` Object 的 Method 如下：

1. 通过 new Keyword。
2. 基于 `CompletableFuture` 自带的 Static Factory Method：`runAsync()`、`supplyAsync()`。

#### new Keyword

通过 new Keyword 创建 `CompletableFuture` Object 这种使用方式可以看作是将 `CompletableFuture` 当做 `Future` 来使用。

我在我的开源项目 [guide-rpc-framework](https://github.com/Snailclimb/guide-rpc-framework) 中就是这种方式创建的 `CompletableFuture` Object。

下面咱们来看一个简单的案例。

我们通过创建了一个结果值 Type 为 `RpcResponse<Object>` 的 `CompletableFuture`，你可以把 `resultFuture` 看作是 Asynchronous 运算结果的载体。

```java
CompletableFuture<RpcResponse<Object>> resultFuture = new CompletableFuture<>();
```

假设在未来的某个时刻，我们得到了最终的结果。这时，我们可以调用 `complete()` Method 为其传入结果，这表示 `resultFuture` 已经被完成了。

```java
// complete() 方法只能调用一次，后续调用将被忽略。
resultFuture.complete(rpcResponse);
```

你可以通过 `isDone()` Method 来检查是否已经完成。

```java
public boolean isDone() {
    return result != null;
}
```

获取 Asynchronous 计算的结果也非常简单，直接调用 `get()` Method 即可。调用 `get()` Method 的 Thread 会 Blocking 直到 `CompletableFuture` 完成运算。

```java
rpcResponse = completableFuture.get();
```

如果你已经知道计算的结果的话，可以使用 Static Method `completedFuture()` 来创建 `CompletableFuture`。

```java
CompletableFuture<String> future = CompletableFuture.completedFuture("hello!");
assertEquals("hello!", future.get());
```

`completedFuture()` Method 底层调用的是带 Parameter 的 new Method，只不过，这个 Method 不对外暴露。

```java
public static <U> CompletableFuture<U> completedFuture(U value) {
    return new CompletableFuture<U>((value == null) ? NIL : value);
}
```

#### Static Factory Method

这两个 Method 可以帮助我们 Encapsulation 计算逻辑。

```java
static <U> CompletableFuture<U> supplyAsync(Supplier<U> supplier);
// 使用自定义线程池(推荐)
static <U> CompletableFuture<U> supplyAsync(Supplier<U> supplier, Executor executor);
static CompletableFuture<Void> runAsync(Runnable runnable);
// 使用自定义线程池(推荐)
static CompletableFuture<Void> runAsync(Runnable runnable, Executor executor);
```

`runAsync()` Method 接受的 Parameter 是 `Runnable`，这是一个 Functional Interface，不允许 Return Value。当你需要 Asynchronous 操作且不关心返回结果的时候可以使用 `runAsync()` Method。

```java
@FunctionalInterface
public interface Runnable {
    public abstract void run();
}
```

`supplyAsync()` Method 接受的 Parameter 是 `Supplier<U>`，这也是一个 Functional Interface，`U` 是返回结果值的 Type。

```java
@FunctionalInterface
public interface Supplier<T> {

    /**
     * Gets a result.
     *
     * @return a result
     */
    T get();
}
```

当你需要 Asynchronous 操作且关心返回结果的时候，可以使用 `supplyAsync()` Method。

```java
CompletableFuture<Void> future = CompletableFuture.runAsync(() -> System.out.println("hello!"));
future.get();// 输出 "hello!"
CompletableFuture<String> future2 = CompletableFuture.supplyAsync(() -> "hello!");
assertEquals("hello!", future2.get());
```

### 处理 Asynchronous 结算的结果

当我们获取到 Asynchronous 计算的结果之后，还可以对其进行进一步的处理，比较常用的 Method 有下面几个：

- `thenApply()`
- `thenAccept()`
- `thenRun()`
- `whenComplete()`

`thenApply()` Method 接受一个 `Function` Instance，用它来处理结果。

```java
// 非异步回调：可能由完成上一个阶段的线程执行；如果阶段已经完成，也可能由当前调用线程执行
public <U> CompletableFuture<U> thenApply(
    Function<? super T,? extends U> fn) {
    return uniApplyStage(null, fn);
}

//使用默认的 ForkJoinPool 线程池（不推荐）
public <U> CompletableFuture<U> thenApplyAsync(
    Function<? super T,? extends U> fn) {
    return uniApplyStage(defaultExecutor(), fn);
}
// 使用自定义线程池(推荐)
public <U> CompletableFuture<U> thenApplyAsync(
    Function<? super T,? extends U> fn, Executor executor) {
    return uniApplyStage(screenExecutor(executor), fn);
}
```

`thenApply()` Method 使用示例如下：

```java
CompletableFuture<String> future = CompletableFuture.completedFuture("hello!")
        .thenApply(s -> s + "world!");
assertEquals("hello!world!", future.get());
// 这次调用将被忽略。
future.thenApply(s -> s + "nice!");
assertEquals("hello!world!", future.get());
```

你还可以进行 **流式调用**：

```java
CompletableFuture<String> future = CompletableFuture.completedFuture("hello!")
        .thenApply(s -> s + "world!").thenApply(s -> s + "nice!");
assertEquals("hello!world!nice!", future.get());
```

**如果你不需要从 Callback Function 中获取返回结果，可以使用 `thenAccept()` 或者 `thenRun()`。这两个 Method 的区别在于 `thenRun()` 不能访问 Asynchronous 计算的结果。**

`thenAccept()` Method 的 Parameter 是 `Consumer<? super T>`。

```java
public CompletableFuture<Void> thenAccept(Consumer<? super T> action) {
    return uniAcceptStage(null, action);
}

public CompletableFuture<Void> thenAcceptAsync(Consumer<? super T> action) {
    return uniAcceptStage(defaultExecutor(), action);
}

public CompletableFuture<Void> thenAcceptAsync(Consumer<? super T> action,
                                               Executor executor) {
    return uniAcceptStage(screenExecutor(executor), action);
}
```

顾名思义，`Consumer` 属于消费型 Interface，它可以接收 1 个输入 Object 然后进行“消费”。

```java
@FunctionalInterface
public interface Consumer<T> {

    void accept(T t);

    default Consumer<T> andThen(Consumer<? super T> after) {
        Objects.requireNonNull(after);
        return (T t) -> { accept(t); after.accept(t); };
    }
}
```

`thenRun()` 的 Method 是的 Parameter 是 `Runnable`。

```java
public CompletableFuture<Void> thenRun(Runnable action) {
    return uniRunStage(null, action);
}

public CompletableFuture<Void> thenRunAsync(Runnable action) {
    return uniRunStage(defaultExecutor(), action);
}

public CompletableFuture<Void> thenRunAsync(Runnable action,
                                            Executor executor) {
    return uniRunStage(screenExecutor(executor), action);
}
```

`thenAccept()` 和 `thenRun()` 使用示例如下：

```java
CompletableFuture.completedFuture("hello!")
        .thenApply(s -> s + "world!").thenApply(s -> s + "nice!").thenAccept(System.out::println);//hello!world!nice!

CompletableFuture.completedFuture("hello!")
        .thenApply(s -> s + "world!").thenApply(s -> s + "nice!").thenRun(() -> System.out.println("hello!"));//hello!
```

`whenComplete()` 的 Method 的 Parameter 是 `BiConsumer<? super T, ? super Throwable>`。

```java
public CompletableFuture<T> whenComplete(
    BiConsumer<? super T, ? super Throwable> action) {
    return uniWhenCompleteStage(null, action);
}


public CompletableFuture<T> whenCompleteAsync(
    BiConsumer<? super T, ? super Throwable> action) {
    return uniWhenCompleteStage(defaultExecutor(), action);
}
// 使用自定义线程池(推荐)
public CompletableFuture<T> whenCompleteAsync(
    BiConsumer<? super T, ? super Throwable> action, Executor executor) {
    return uniWhenCompleteStage(screenExecutor(executor), action);
}
```

相对于 `Consumer`， `BiConsumer` 可以接收 2 个输入 Object 然后进行“消费”。

```java
@FunctionalInterface
public interface BiConsumer<T, U> {
    void accept(T t, U u);

    default BiConsumer<T, U> andThen(BiConsumer<? super T, ? super U> after) {
        Objects.requireNonNull(after);

        return (l, r) -> {
            accept(l, r);
            after.accept(l, r);
        };
    }
}
```

`whenComplete()` 使用示例如下：

```java
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> "hello!")
        .whenComplete((res, ex) -> {
            // res 代表返回的结果
            // ex 的类型为 Throwable ，代表抛出的异常
            System.out.println(res);
            // 这里没有抛出异常所有为 null
            assertNull(ex);
        });
assertEquals("hello!", future.get());
```

### Exception Handling

你可以通过 `handle()` Method 来处理 Task 执行过程中可能出现的抛出 Exception 的情况。

```java
public <U> CompletableFuture<U> handle(
    BiFunction<? super T, Throwable, ? extends U> fn) {
    return uniHandleStage(null, fn);
}

public <U> CompletableFuture<U> handleAsync(
    BiFunction<? super T, Throwable, ? extends U> fn) {
    return uniHandleStage(defaultExecutor(), fn);
}

public <U> CompletableFuture<U> handleAsync(
    BiFunction<? super T, Throwable, ? extends U> fn, Executor executor) {
    return uniHandleStage(screenExecutor(executor), fn);
}
```

示例代码如下：

```java
CompletableFuture<String> future
        = CompletableFuture.supplyAsync(() -> {
    if (true) {
        throw new RuntimeException("Computation error!");
    }
    return "hello!";
}).handle((res, ex) -> {
    // res 代表返回的结果
    // ex 的类型为 Throwable ，代表抛出的异常
    return res != null ? res : "world!";
});
assertEquals("world!", future.get());
```

你还可以通过 `exceptionally()` Method 来处理异常情况。

```java
CompletableFuture<String> future
        = CompletableFuture.supplyAsync(() -> {
    if (true) {
        throw new RuntimeException("Computation error!");
    }
    return "hello!";
}).exceptionally(ex -> {
    System.out.println(ex.toString());// CompletionException
    return "world!";
});
assertEquals("world!", future.get());
```

如果你想让 `CompletableFuture` 的结果就是 Exception 的话，可以使用 `completeExceptionally()` Method 为其赋值。

```java
CompletableFuture<String> completableFuture = new CompletableFuture<>();
// ...
completableFuture.completeExceptionally(
  new RuntimeException("Calculation failed!"));
// ...
completableFuture.get(); // ExecutionException
```

### 组合 CompletableFuture

你可以使用 `thenCompose()` 按顺序链接两个 `CompletableFuture` Object，实现 Asynchronous 的 Task 链。它的作用是将前一个 Task 的返回结果作为下一个 Task 的输入 Parameter，从而形成一个依赖关系。

```java
public <U> CompletableFuture<U> thenCompose(
    Function<? super T, ? extends CompletionStage<U>> fn) {
    return uniComposeStage(null, fn);
}

public <U> CompletableFuture<U> thenComposeAsync(
    Function<? super T, ? extends CompletionStage<U>> fn) {
    return uniComposeStage(defaultExecutor(), fn);
}

public <U> CompletableFuture<U> thenComposeAsync(
    Function<? super T, ? extends CompletionStage<U>> fn,
    Executor executor) {
    return uniComposeStage(screenExecutor(executor), fn);
}
```

`thenCompose()` Method 会使用示例如下：

```java
CompletableFuture<String> future
        = CompletableFuture.supplyAsync(() -> "hello!")
        .thenCompose(s -> CompletableFuture.supplyAsync(() -> s + "world!"));
assertEquals("hello!world!", future.get());
```

在实际开发中，这个 Method 还是非常有用的。比如说，task1 和 task2 都是 Asynchronous 执行的，但 task1 必须执行完成后才能开始执行 task2（task2 依赖 task1 的执行结果）。

和 `thenCompose()` Method 类似的还有 `thenCombine()` Method， 它同样可以组合两个 `CompletableFuture` Object。

```java
CompletableFuture<String> completableFuture
        = CompletableFuture.supplyAsync(() -> "hello!")
        .thenCombine(CompletableFuture.supplyAsync(
                () -> "world!"), (s1, s2) -> s1 + s2)
        .thenCompose(s -> CompletableFuture.supplyAsync(() -> s + "nice!"));
assertEquals("hello!world!nice!", completableFuture.get());
```

**那 `thenCompose()` 和 `thenCombine()` 有什么区别呢？**

- `thenCompose()` 可以链接两个 `CompletableFuture` Object，并将前一个 Task 的返回结果作为下一个 Task 的 Parameter，它们之间存在着先后顺序。
- `thenCombine()` 会在两个阶段都正常完成后，把它们的结果合并。这两个阶段可以彼此独立，但是否 Parallel Execution 取决于它们的创建方式和所用执行器，`thenCombine()` 本身不负责启动 Task。

除了 `thenCompose()` 和 `thenCombine()` 之外， 还有一些其他的组合 `CompletableFuture` 的 Method 用于实现不同的效果，满足不同的业务需求。

例如，在 task1 和 task2 都正常完成的场景中，可以使用 `acceptEither()`，让 task3 接收其中一个先完成 Task 的结果。需要注意，它不能作为可靠的“第一个成功结果”选择器：只要其中一个阶段 Exception 完成，返回阶段的结果就要遵循 `CompletionStage` 对 either 组合的 Exception 规则。

```java
public CompletableFuture<Void> acceptEither(
    CompletionStage<? extends T> other, Consumer<? super T> action) {
    return orAcceptStage(null, other, action);
}

public CompletableFuture<Void> acceptEitherAsync(
    CompletionStage<? extends T> other, Consumer<? super T> action) {
    return orAcceptStage(asyncPool, other, action);
}
```

简单举一个例子：

```java
CompletableFuture<String> task = CompletableFuture.supplyAsync(() -> {
    System.out.println("任务1开始执行，当前时间：" + System.currentTimeMillis());
    try {
        Thread.sleep(500);
    } catch (InterruptedException e) {
        e.printStackTrace();
    }
    System.out.println("任务1执行完毕，当前时间：" + System.currentTimeMillis());
    return "task1";
});

CompletableFuture<String> task2 = CompletableFuture.supplyAsync(() -> {
    System.out.println("任务2开始执行，当前时间：" + System.currentTimeMillis());
    try {
        Thread.sleep(1000);
    } catch (InterruptedException e) {
        e.printStackTrace();
    }
    System.out.println("任务2执行完毕，当前时间：" + System.currentTimeMillis());
    return "task2";
});

task.acceptEitherAsync(task2, (res) -> {
    System.out.println("任务3开始执行，当前时间：" + System.currentTimeMillis());
    System.out.println("上一个任务的结果为：" + res);
});

// 增加一些延迟时间，确保异步任务有足够的时间完成
try {
    Thread.sleep(2000);
} catch (InterruptedException e) {
    e.printStackTrace();
}
```

输出：

```plain
任务1开始执行，当前时间：1695088058520
任务2开始执行，当前时间：1695088058521
任务1执行完毕，当前时间：1695088059023
任务3开始执行，当前时间：1695088059023
上一个任务的结果为：task1
任务2执行完毕，当前时间：1695088059523
```

当两个阶段都正常完成时，`acceptEitherAsync()` 会使用其中一个已完成阶段的结果 Asynchronous 执行 Task 3，通常是先完成者的结果。不过，如果其中一个阶段 Exception 完成，而另一个尚未完成或正常完成，规范并不保证返回阶段最终一定正常完成还是 Exception 完成。因此，不能依赖该 Method 忽略先发生的 Exception 并继续等待另一个成功结果。

### 等待多个 CompletableFuture 完成

你可以通过 `CompletableFuture` 的 `allOf()` Static Method 等待多个 `CompletableFuture` 全部完成。`allOf()` 只组合已有阶段的完成状态，不负责启动这些 Task；Task 是否 Parallelism 取决于它们的创建方式和执行器。

实际项目中，我们经常需要 Parallelism 运行多个互不相关的 Task，这些 Task 之间没有依赖关系，可以互相独立地运行。

比说我们要读取处理 6 个文件，这 6 个 Task 都是没有执行顺序依赖的 Task，但是我们需要返回给用户的时候将这几个文件的处理的结果进行统计整理。像这种情况我们就可以使用 Parallelism 运行多个 `CompletableFuture` 来处理。

示例代码如下：

```java
CompletableFuture<Void> task1 =
  CompletableFuture.supplyAsync(()->{
    //自定义业务操作
  });
......
CompletableFuture<Void> task6 =
  CompletableFuture.supplyAsync(()->{
    //自定义业务操作
  });
......
 CompletableFuture<Void> headerFuture=CompletableFuture.allOf(task1,.....,task6);

  try {
    headerFuture.join();
  } catch (Exception ex) {
    ......
  }
System.out.println("all done. ");
```

经常和 `allOf()` Method 拿来对比的是 `anyOf()` Method。

**`allOf()` Method 会等到所有的 `CompletableFuture` 都运行完成之后再返回**

```java
Random rand = new Random();
CompletableFuture<String> future1 = CompletableFuture.supplyAsync(() -> {
    try {
        Thread.sleep(1000 + rand.nextInt(1000));
    } catch (InterruptedException e) {
        e.printStackTrace();
    } finally {
        System.out.println("future1 done...");
    }
    return "abc";
});
CompletableFuture<String> future2 = CompletableFuture.supplyAsync(() -> {
    try {
        Thread.sleep(1000 + rand.nextInt(1000));
    } catch (InterruptedException e) {
        e.printStackTrace();
    } finally {
        System.out.println("future2 done...");
    }
    return "efg";
});
```

调用 `join()` 可以让程序等 `future1` 和 `future2` 都运行完了之后再继续执行。

```java
CompletableFuture<Void> completableFuture = CompletableFuture.allOf(future1, future2);
completableFuture.join();
assertTrue(completableFuture.isDone());
System.out.println("all futures done...");
```

输出：

```plain
future1 done...
future2 done...
all futures done...
```

**`anyOf()` Method 不会等待所有的 `CompletableFuture` 都运行完成之后再返回，只要有一个执行完成即可！**

```java
CompletableFuture<Object> f = CompletableFuture.anyOf(future1, future2);
System.out.println(f.get());
```

输出结果可能是：

```plain
future2 done...
efg
```

也可能是：

```plain
future1 done...
abc
```

## CompletableFuture 使用建议

### 使用自定义 Thread Pool

我们上面的代码示例中，为了方便，都没有选择自定义 Thread Pool。实际项目中，这是不可取的。

在 `CompletableFuture` 的默认实现中，没有显式传入 `Executor` 的 Asynchronous Method 通常使用全局 Shared 的 `ForkJoinPool.commonPool()`；Subclass 可以通过 Override `defaultExecutor()` 改变非静态 Asynchronous Method 的默认执行器。这意味着应用程序、多个库或框架若都使用默认实现，相关 Asynchronous Task 通常会 Shared 同一个 Thread Pool。

虽然 `ForkJoinPool` 效率很高，但当同时提交大量 Task 时，可能会导致资源竞争和 Thread Starvation，进而影响系统 Performance。

为避免这些问题，建议为 `CompletableFuture` 提供自定义 Thread Pool，带来以下优势：

- **隔离性**：为不同 Task 分配独立的 Thread Pool，避免全局 Thread Pool 资源争夺。
- **资源控制**：根据 Task 特性调整 Thread Pool 大小和 Queue Type，优化 Performance 表现。
- **Exception Handling**：通过自定义 `ThreadFactory` 更好地处理 Thread 中的异常情况。

```java
private ThreadPoolExecutor executor = new ThreadPoolExecutor(10, 10,
        0L, TimeUnit.MILLISECONDS,
        new LinkedBlockingQueue<Runnable>());

CompletableFuture.runAsync(() -> {
     //...
}, executor);
```

### 尽量避免使用 get()

`CompletableFuture` 的 `get()` Method 是 Blocking 的，尽量避免使用。如果必须要使用的话，需要添加 Timeout 时间，否则可能会导致 Main Thread 一直等待，无法执行其他 Task。

```java
    CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
        try {
            Thread.sleep(10_000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        return "Hello, world!";
    });

    // 获取异步任务的返回值，设置超时时间为 5 秒
    try {
        String result = future.get(5, TimeUnit.SECONDS);
        System.out.println(result);
    } catch (InterruptedException | ExecutionException | TimeoutException e) {
        // 处理异常
        e.printStackTrace();
    }
}
```

上面这段代码在调用 `get()` 时抛出了 `TimeoutException` Exception。这样我们就可以在 Exception Handling 中进行相应的操作，比如取消 Task、Retry Task、记录 Log 等。

### 正确进行 Exception Handling

使用 `CompletableFuture` 的时候一定要以正确的方式进行 Exception Handling，避免 Exception 丢失或者出现不可控问题。

下面是一些建议：

- `whenComplete` 会在阶段正常或 Exception 完成时执行 Callback，适合观察结果和记录 Exception；它默认保留原阶段的结果或 Exception，不用于把 Exception 转换为正常结果。
- `exceptionally` 只在阶段 Exception 完成时执行，并用 Callback 的 Return Value 恢复为正常结果；如果需要继续传播 Exception，可以在 Callback 中显式抛出 Exception。
- `handle` 无论阶段正常还是 Exception 完成都会执行，并根据结果和 Exception 生成一个新的结果。
- `CompletableFuture.allOf` 可以等待多个阶段全部完成；只要其中一个阶段 Exception 完成，返回的 `CompletableFuture` 也会 Exception 完成，但仍需分别检查各阶段才能获得每个 Task 的结果或 Exception。
- ……

### 合理组合多个 Asynchronous Task

正确使用 `thenCompose()`、 `thenCombine()`、`acceptEither()`、`allOf()`、`anyOf()` 等 Method 来组合多个 Asynchronous Task，以满足实际业务的需求，提高程序执行效率。

实际使用中，我们还可以利用或者参考现成的 Asynchronous Task 编排框架，比如京东的 [asyncTool](https://gitee.com/jd-platform-opensource/asyncTool)。

![asyncTool README 文档](https://oss.javaguide.cn/github/javaguide/java/concurrent/asyncTool-readme.png)

## 后记

这篇文章只是简单介绍了 `CompletableFuture` 的核心概念和比较常用的一些 API。如果想要深入学习的话，还可以多找一些书籍和博客看，比如下面几篇文章就挺不错：

- [CompletableFuture 原理与实践-外卖商家端 API 的 Asynchronous 化 - 美团技术团队](https://tech.meituan.com/2022/05/12/principles-and-practices-of-completablefuture.html)：这篇文章详细介绍了 `CompletableFuture` 在实际项目中的运用。参考这篇文章，可以对项目中类似的场景进行优化，也算是一个小亮点了。这种 Performance Optimization 方式比较简单且效果还不错！
- [读 RocketMQ 源码，学习 Concurrent Programming 三大神器 - 勇哥 java 实战分享](https://mp.weixin.qq.com/s/32Ak-WFLynQfpn0Cg0N-0A)：这篇文章介绍了 RocketMQ 对 `CompletableFuture` 的应用。具体来说，从 RocketMQ 4.7 开始，RocketMQ 引入了 `CompletableFuture` 来实现 Asynchronous 消息处理。

另外，建议 G 友们可以看看京东的 [asyncTool](https://gitee.com/jd-platform-opensource/asyncTool) 这个 Concurrency 框架，里面大量使用到了 `CompletableFuture`。

<!-- @include: @article-footer.snippet.md -->
