# PPA 优化杠杆速查（P3-09）

> 供 P4 optimize 阶段使用：每个杠杆的**作用 → 适用条件 → 常见冲突 → PPA 影响**。
> 数据源：真机 6 题运行日志（dotProduct 73.36× / fir 15.68× / matmul 15.58× 实证）、
> AMD LLM4HLS 案例、UG1399。2026-07-20 整理。

## 速查表

| 杠杆 | 一句话作用 | 延迟收益 | 资源代价 | 典型冲突 |
|---|---|---|---|---|
| `PIPELINE` | 循环/函数重叠执行，降 II | ★★★（II→1 是优化分水岭） | FF 略增 | 与 DATAFLOW 同级冲突；被循环携带依赖卡住 |
| `UNROLL` | 复制循环体并行执行 | ★★★（×factor 并行度） | DSP/LUT ×factor | 数组端口不够时反而串行 |
| `ARRAY_PARTITION` | 拆数组增端口 | ★★（解锁 UNROLL/PIPELINE 的前提） | BRAM→FF/LUT | complete 拆太大爆寄存器；拆错维度白拆 |
| `DATAFLOW` | 函数级流水线，stage 重叠 | ★★（多阶段任务） | FIFO + 控制逻辑 | 单阶段任务无效；stream 突发会死锁（见 KB cosim 类） |
| `BIND_OP` | 指定运算实现（DSP/织物） | ★ | 换资源类型不换数量 | 收益小，优先级最低 |
| 加法树重构 | 破循环携带依赖 | ★★★（累加类必备） | 与 UNROLL 同阶 | 浮点重排影响精度（注意 tb 容差） |

## 各杠杆细节

### 1. PIPELINE（第一优先）

- **作用**：让循环 II（initiation interval）从"迭代延迟"降到 1 或接近 1。dotProduct 实证：不加 pragma 的循环是顺序执行，PIPELINE+UNROLL 组合把 1027 cyc 打到 14 cyc。
- **适用**：几乎所有循环。内层循环优先；外层 PIPELINE 会自动完全展开内层。
- **冲突/注意**：
  - 与 DATAFLOW **不能同级**（KB: `synth-pragma-same-level-conflict`）。
  - 循环携带依赖（`acc += ...`）会卡 II——先重构再加（见"加法树重构"）。
  - 数组端口不够时 II 降不下来——先 ARRAY_PARTITION（KB: `synth-ii-scheduling-fail`）。
- **PPA 影响**：延迟 ↓↓，FF 略增，时钟一般不变。

### 2. UNROLL

- **作用**：复制循环体，factor 倍并行。常与 PIPELINE 组合（外层 PIPELINE + 内层 UNROLL 是实证最强组合）。
- **适用**：循环体小、迭代间无依赖；factor 取数组 partition factor 的约数。
- **冲突/注意**：
  - **没有配套 ARRAY_PARTITION 就是白展开**——端口冲突会把并行访问串行化（KB: `synth-array-port-conflict`）。
  - 全展开（不带 factor）等价于把循环变成组合逻辑，体大时寄存器爆炸。
- **PPA 影响**：延迟 ↓↓（÷factor），DSP/LUT ↑（×factor）。

### 3. ARRAY_PARTITION

- **作用**：把数组拆成多块/寄存器，增加并发端口数。是 UNROLL/PIPELINE 生效的**前置条件**。
- **模式选择**：
  - `complete`：全拆成寄存器。小数组（≤几十元素）或要全并行的维度（matmul 实证：A 拆 dim=2、B 拆 dim=1——**拆"内层循环变化的维度"**）。
  - `cyclic factor=N`：交错拆 N 块。大数组配 UNROLL factor=N（dotProduct/vecadd 实证）。
  - `block factor=N`：连续分块，用得少。
- **常见错误**：拆错维度（matmul 里 B[k][j] 内层变 k，必须拆 dim=1 而不是 dim=2）；complete 拆 1024+ 大数组爆 FF。
- **PPA 影响**：延迟（间接）↓↓，BRAM ↓ / FF·LUT ↑。

### 4. DATAFLOW

- **作用**：任务级流水线——多个函数/循环阶段用 stream 衔接、重叠执行。
- **适用**：明显多阶段（读→算→写）且单任务延迟由阶段间串行主导时。
- **冲突/注意**：
  - **单阶段计算（纯循环）不要用**，收益为零还引入 FIFO 风险。
  - producer 突发写 > consumer 消费速率会 cosim 死锁（KB: `cosim-deadlock-fifo-burst`、`cosim-fifo-depth-too-shallow`）——csim 发现不了（C FIFO 无界）。
  - stream 只能一进一出；合并函数后留意死 stream（KB: `synth-xform-dataflow-conflict`）。
- **PPA 影响**：吞吐 ↑↑，单任务延迟 ↓，FIFO/控制逻辑 ↑。

### 5. BIND_OP（最低优先）

- **作用**：指定某个运算用 DSP 还是织物实现、几级流水。
- **适用**：DSP 预算紧张或关键路径在某个运算上时的微调。
- **现实定位**：前四板斧用完再考虑；实证 6 题都没用到。

### 6. 加法树重构（代码级，非 pragma）

- **作用**：把 `for(i) acc += a[i]*b[i]` 的顺序依赖改成部分和/配对归约，破除 II 瓶颈。
- **实证**：dotProduct 满分的关键之一（策略组合：PIPELINE+UNROLL+ARRAY_PARTITION+加法树）。
- **注意**：浮点重排改变舍入——先确认 tb 容差（KB: `csim-numeric-reorder-tolerance`）。

## 实证延迟参考（U55C @ 200MHz，5ns）

| 题 | baseline | 优化后 | 加速比 | 关键杠杆 |
|---|---|---|---|---|
| dotProduct (1024 定点) | 1027 cyc | 14 cyc | 73.36× | PIPELINE+UNROLL32+cyclic partition+加法树 |
| fir (1024×32tap 浮点) | 16529 cyc | 1054 cyc | 15.68× | 移位寄存器 complete partition+MAC 全展开+PIPELINE |
| matmul (32×32 浮点) | 16422 cyc | 1054 cyc | 15.58× | A dim2/B dim1 complete partition+内层 UNROLL+PIPELINE |
| vecadd (4096 浮点) | 4102 cyc | 518 cyc | 7.92× | cyclic partition 8+UNROLL 8+PIPELINE |

## 给 optimize 阶段的策略建议（组合顺序）

1. 先 `PIPELINE` 内层 + `ARRAY_PARTITION` 配套端口（最便宜的最大收益）。
2. 累加类必做加法树重构，否则 II 卡死。
3. 再 `UNROLL` 扩并行度（factor 对齐 partition factor）。
4. 多阶段任务才考虑 `DATAFLOW`，且必须先想 FIFO 深度。
5. 每加一步都要 csim 重验——pragma 组合出错时 Vitis 报错往往指向组合而非单个 pragma。
