# agent/router.py 说明文档

## 中文说明

### 用途
实现 agent-architecture.md §3：读取任务元数据并决定阶段路径。每个任务入口运行一次，零信用消耗——仅读 task.toml 字段（task_type、requires_cosim）与头部，从不调用工具。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `RunPlan` | class (dataclass) | 交给主循环的计划：task_type、correctness_stages、needs_optimize、initial_level |
| `route(task) -> RunPlan` | function | 由 llm4hls.Task 构建 RunPlan：读 requires_cosim 决定正确性闸门，optimize 种子初始 level=1 其余=0 |

### 导出
无 `__all__`；主要导出 `RunPlan` 与 `route`。

### 依赖
- 内部依赖：无
- 外部依赖：`llm4hls.Task`（harness，仅在 route() 内惰性使用，import 期无硬耦合）

### 关键设计点
- 相对早期设计的关键修正：router 不决定 "C vs HLS"（输入恒为 header-locked 签名的 HLS C++）、不跳过低阶段（评分无论如何重跑每个阶段，且修后段 bug 可能破坏前段）、不跑工具做诊断；它只选择哪些阶段构成正确性闸门。
- correctness_stages 为 `["csim"]` 或 `["csim","cosim"]`（后者当 requires_cosim 为真）；needs_optimize 恒为 True（正确性+综合通过后均可受益于优化）。
- initial_level：optimize 种子假定已过 csim（=1，由循环确认），其余从 0 起需在修复循环挣得 CORRECT。

---

## English

### Purpose
Implements agent-architecture.md §3: reads task metadata and decides the stage path. Runs once per task at entry at zero credit cost — it only reads task.toml fields (task_type, requires_cosim) and the header, never invokes a tool.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `RunPlan` | class (dataclass) | Plan handed to the main loop: task_type, correctness_stages, needs_optimize, initial_level |
| `route(task) -> RunPlan` | function | Builds a RunPlan from an llm4hls.Task: reads requires_cosim to decide the correctness gate; optimize seeds start at level 1, others at 0 |

### Exports
No `__all__`; primary exports are `RunPlan` and `route`.

### Dependencies
- Internal: none
- External: `llm4hls.Task` (harness, used lazily inside route() only; no hard coupling at import time)

### Key Design Points
- Key correction from an earlier design: the router does NOT decide "C vs HLS" (input is always header-locked-signature HLS C++), does NOT skip low stages (grading re-runs every stage anyway, and editing for a later bug can break an earlier one), and does NOT run a tool for diagnosis; it only picks which stages form the correctness gate.
- correctness_stages is `["csim"]` or `["csim","cosim"]` (the latter when requires_cosim is true); needs_optimize is always True (every task can benefit from optimization once correctness+synth hold).
- initial_level: optimize seeds assume csim-correct (=1, confirmed by the loop); all others start at 0 and must earn CORRECT in the repair loop.
