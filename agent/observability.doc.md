# agent/observability.py 说明文档

## 中文说明

### 用途
可观测性——结构化 JSONL 日志 + 心跳，实现 agent-architecture.md §12。三层中的两层（harness transcript 已存在）：本模块的 agent 决策点结构化事件（-> JSONL）与心跳（停顿检测存活信号）。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Logger` | class | 追加式结构化日志，写 JSONL 到文件 + stderr |
| `Logger.__init__(task_id, run_dir="runs")` | method | 构造；建 run_dir，每运行截断 `{task_id}.jsonl`，初始化活动时间戳与锁 |
| `Logger.event(event, **fields)` | method | 发一条结构化事件行（ts/task/event/+fields），更新活动时间戳 |
| `Logger.age_s() -> float` | method | 返回距上次活动的秒数（加锁） |
| `Heartbeat` | class | 后台心跳线程做停顿检测 |
| `Heartbeat.__init__(logger, interval=10.0)` | method | 构造 daemon 线程，stage="idle" |
| `Heartbeat.set_stage(stage, credit_remaining=None)` | method | 更新当前阶段与剩余信用（换阶段计为活动） |
| `Heartbeat.start() / stop()` | method | 启动 / 通知停止并 join（超时 2s） |
| `Heartbeat._run()` | method | 周期报告存活，age 超阶段阈值则标 stale |

### 导出
无 `__all__`；主要导出 `Logger` 与 `Heartbeat`；模块常量 `_STALL_THRESHOLD`（csim 180/synth 600/cosim 900/llm 180/idle 60 秒）。

### 依赖
- 内部依赖：无（被 `.main_loop` 使用）
- 外部依赖：标准库 `json`、`sys`、`threading`、`time`、`pathlib`

### 关键设计点
- 首版写 JSONL 到 stdout+文件，用 `tail -f` 消费；次版可将同一 JSONL 渲染进 TUI/WebUI。
- 停顿阈值与 harness 超时对齐（csim 180/synth 600/cosim 900/llm 180），age 超阈值发 heartbeat 事件标 stale。
- 并发安全：event/age_s 经 `threading.Lock` 保护 `_last_activity`；心跳 daemon 线程在 run() finally 中 stop。
- 架构章节引用：§12 可观测性。

---

## English

### Purpose
Observability — structured JSONL logging + heartbeat, implementing agent-architecture.md §12. Two of three layers (the harness transcript already exists): this module's agent decision-point structured events (-> JSONL) and a heartbeat (liveness signal for stall detection).

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Logger` | class | Append-only structured logger writing JSONL to a file + stderr |
| `Logger.__init__(task_id, run_dir="runs")` | method | Construction; creates run_dir, truncates `{task_id}.jsonl` per run, initializes activity timestamp and lock |
| `Logger.event(event, **fields)` | method | Emits one structured event line (ts/task/event/+fields); updates activity timestamp |
| `Logger.age_s() -> float` | method | Returns seconds since last activity (under lock) |
| `Heartbeat` | class | Background heartbeat thread for stall detection |
| `Heartbeat.__init__(logger, interval=10.0)` | method | Construction; daemon thread, stage="idle" |
| `Heartbeat.set_stage(stage, credit_remaining=None)` | method | Updates current stage and remaining credit (stage change counts as activity) |
| `Heartbeat.start() / stop()` | method | Starts / signals stop and joins (2s timeout) |
| `Heartbeat._run()` | method | Periodically reports liveness; flags stale when age exceeds the stage threshold |

### Exports
No `__all__`; primary exports are `Logger` and `Heartbeat`; module constant `_STALL_THRESHOLD` (csim 180/synth 600/cosim 900/llm 180/idle 60 seconds).

### Dependencies
- Internal: none (consumed by `.main_loop`)
- External: standard library `json`, `sys`, `threading`, `time`, `pathlib`

### Key Design Points
- First iteration writes JSONL to stdout + file, consumed with `tail -f`; a second iteration can render the same JSONL into a TUI/WebUI.
- Stall thresholds match harness timeouts (csim 180/synth 600/cosim 900/llm 180); age exceeding the threshold emits a heartbeat event flagged stale.
- Concurrency-safe: event/age_s guard `_last_activity` with a `threading.Lock`; the heartbeat daemon thread is stopped in run()'s finally.
- Architecture section referenced: §12 observability.
