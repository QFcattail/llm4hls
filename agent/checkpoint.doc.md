# agent/checkpoint.py 说明文档

## 中文说明

### 用途
检查点（归档）逻辑——主循环的核心数据结构。实现 agent-architecture.md §2：Level 0/1/2/3 的分数阶梯与三条归档规则；归档同时提供免费回滚。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Level` | class | 单调级别常量：NONE=0、CORRECT=1、SYNTH=2（越高分数阶梯上越优） |
| `Checkpoint` | class (dataclass) | 当前最佳状态：code、level、latency、cosim_ok |
| `Checkpoint.should_accept(cand_level, cand_latency) -> bool` | method | 应用三条归档规则判断候选是否替代当前最佳 |
| `Checkpoint.accept(code, level, latency, cosim_ok=None)` | method | 在 should_accept 后提交候选为新最佳 |

### 导出
无 `__all__`；主要导出 `Checkpoint` 与 `Level`（由 `agent/__init__.py` 再导出）。

### 依赖
- 内部依赖：无
- 外部依赖：标准库 `dataclasses`

### 关键设计点
- 三条归档规则（相对当前最佳 B、候选 C）：1) level(C)>level(B) 恒接受；2) 同级别仅当 latency 严格更低才接受；3) level(C)<level(B) 永不接受（正确性回退）。
- 免费回滚：打破前段的失败候选永不进入 best，故 best 停留在最后验证版本。
- 同级别比较时若任一 latency 为 None 则不接受（无可比 latency）。

---

## English

### Purpose
Checkpoint (archive) logic — the core data structure of the main loop. Implements agent-architecture.md §2: the Level 0/1/2/3 score ladder and the three archive rules; archiving also provides rollback for free.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Level` | class | Monotone level constants: NONE=0, CORRECT=1, SYNTH=2 (higher is strictly better on the score ladder) |
| `Checkpoint` | class (dataclass) | Current best state: code, level, latency, cosim_ok |
| `Checkpoint.should_accept(cand_level, cand_latency) -> bool` | method | Applies the three archive rules to decide whether a candidate replaces best |
| `Checkpoint.accept(code, level, latency, cosim_ok=None)` | method | Commits a candidate as the new best (call only after should_accept) |

### Exports
No `__all__`; primary exports are `Checkpoint` and `Level` (re-exported by `agent/__init__.py`).

### Dependencies
- Internal: none
- External: standard library `dataclasses`

### Key Design Points
- Three archive rules (vs current best B, candidate C): 1) level(C)>level(B) always accept; 2) same level accept only if latency strictly lower; 3) level(C)<level(B) never accept (correctness regression).
- Free rollback: a failed candidate that broke an earlier stage never enters best, so best stays at the last verified version.
- At the same level, if either latency is None the candidate is not accepted (no comparable latency).
