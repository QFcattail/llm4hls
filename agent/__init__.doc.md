# agent/__init__.py 说明文档

## 中文说明

### 用途
预算化端到端 LLM4HLS Agent 包入口：fork 官方 harness（contest/fpt26-harness/llm4hls/）复用其计量工具面（ToolServer / Budget / Task），并用自有主循环替换参考 agent。整体架构参考 `docs-development/design/agent-architecture.md`。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `RunPlan` | class (dataclass) | 路由产出的运行计划（从 router 导入） |
| `route(task)` | function | 由 task.toml 元数据构建 RunPlan（从 router 导入） |
| `Checkpoint` | class (dataclass) | 当前最佳状态（code/level/latency，从 checkpoint 导入） |
| `Level` | class | 检查点级别常量 NONE/CORRECT/SYNTH（从 checkpoint 导入） |

### 导出
`__all__ = ["RunPlan", "route", "Checkpoint", "Level"]`

### 依赖
- 内部依赖：`.router`（RunPlan, route）、`.checkpoint`（Checkpoint, Level）
- 外部依赖：无（仅作包聚合入口，引用的模块本身依赖 harness）

### 关键设计点
- 仅聚合对外公开的 4 个符号；模块 docstring 列出了 router / checkpoint / main_loop / feedback / llm_client / observability / knowledge_base 各模块职责概览。
- 架构文档引用：docstring 头部显式引用 `docs-development/design/agent-architecture.md`。

---

## English

### Purpose
Package entry point for the budgeted end-to-end LLM4HLS Agent: forks the official harness (contest/fpt26-harness/llm4hls/) to reuse its metered tool surface (ToolServer / Budget / Task) and replaces the reference agent with our own main loop. Architecture reference: `docs-development/design/agent-architecture.md`.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `RunPlan` | class (dataclass) | Run plan produced by routing (re-exported from router) |
| `route(task)` | function | Builds a RunPlan from task.toml metadata (re-exported from router) |
| `Checkpoint` | class (dataclass) | Current best state code/level/latency (re-exported from checkpoint) |
| `Level` | class | Checkpoint level constants NONE/CORRECT/SYNTH (re-exported from checkpoint) |

### Exports
`__all__ = ["RunPlan", "route", "Checkpoint", "Level"]`

### Dependencies
- Internal: `.router` (RunPlan, route), `.checkpoint` (Checkpoint, Level)
- External: none (package aggregate only; referenced modules depend on the harness)

### Key Design Points
- Aggregates only the 4 public symbols; the module docstring summarizes the responsibilities of router / checkpoint / main_loop / feedback / llm_client / observability / knowledge_base.
- Architecture reference: the docstring header explicitly cites `docs-development/design/agent-architecture.md`.
