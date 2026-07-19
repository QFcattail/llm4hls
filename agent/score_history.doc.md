# agent/score_history.py 说明文档

## 中文说明

### 用途
每题一份的跨运行得分历史（tui-design §3.6）。每次评分（CLI driver 或 TUI agent 线程）向 `runs/<task_id>/scores.jsonl` 追加一行 JSON，让用户既能看到最新得分，也能看到多次重跑的收敛趋势。文件只增不删（每行一次运行），暂不做轮转。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `record_score(path, *, score, latency=None, credits=None, tokens=None)` | function | 追加一条得分记录（ts/score/latency/credits/tokens），自动建父目录 |
| `recent_scores(path, n=5) -> list[dict]` | function | 读最新 n 条（最旧在前）；文件不存在返回 []；坏行跳过不致命 |
| `format_history(records, task_id) -> str` | function | 渲染为纯文本表（`recent scores (<task>):` 头 + 每行时间/SCORE/lat/credits/tokens）；空历史显示 `(none yet)` |

### 导出
无 `__all__`；由 `scripts/run_agent.py` 与 `tui/app.py` 直接 import。

### 依赖
- 内部依赖：无
- 外部依赖：标准库 `json`/`time`/`pathlib`

### 关键设计点
1. **双入口互通**：CLI（run_agent.py grade 后）与 TUI（agent 线程 grade 后）写同一文件，命令行跑的和仪表盘跑的历史不分裂。
2. **容错读**：`recent_scores` 对 JSON 解析失败的行静默跳过——历史文件可被手工编辑，坏行不崩 UI。
3. **与 grade() 解耦**：本模块只管历史读写；评分本身由 harness `grade()` 完成，调用方负责把 Scorecard 字段传进来。

---

## English

### Purpose
Per-task cross-run score history (tui-design §3.6). Every grading (from the CLI driver or the TUI agent thread) appends one JSON line to `runs/<task_id>/scores.jsonl`, so users see both the latest score and the convergence trend across repeated runs. Append-only (one line per run); no rotation for now.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `record_score(path, *, score, latency=None, credits=None, tokens=None)` | function | Appends one score record (ts/score/latency/credits/tokens); creates parent dirs |
| `recent_scores(path, n=5) -> list[dict]` | function | Reads the newest n records (oldest first); [] when missing; malformed lines skipped safely |
| `format_history(records, task_id) -> str` | function | Renders a plain-text table (`recent scores (<task>):` header + per-line time/SCORE/lat/credits/tokens); `(none yet)` when empty |

### Exports
No `__all__`; imported directly by `scripts/run_agent.py` and `tui/app.py`.

### Dependencies
- Internal: none
- External: stdlib `json`/`time`/`pathlib`

### Key Design Points
1. **Shared across entry points**: the CLI (run_agent.py after grade) and the TUI (agent thread after grade) write the same file, so command-line and dashboard runs share one history.
2. **Fault-tolerant reads**: `recent_scores` silently skips unparseable lines — the history file may be hand-edited; a bad line never crashes the UI.
3. **Decoupled from grade()**: this module only handles history I/O; grading itself is done by the harness `grade()`, whose Scorecard fields the caller passes in.
