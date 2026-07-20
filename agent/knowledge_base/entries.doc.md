# agent/knowledge_base/entries.py 说明文档

## 中文说明

### 用途
知识库种子条目数据（第一次迭代，架构 §6.2 P2 覆盖范围）。让"错误签名 -> 修法"的检索增强链路开箱可用——synth/cosim/csim 失败时，`build_feedback` 蒸馏出的签名能命中真实条目并注入修复 prompt。条目来源严格可追溯，不编造错误码含义：

- AMD LLM4HLS SHA-256 案例文章（dev-log 2026-07-11-03）：`[XFORM 203-313]` / `[RTGEN 206-102]` 出现在函数合并重构（dataflow 冲突/非法连接）场景；AMD 点名的 LLM 短板（pragma 交互规则、合并后死 stream）。
- harness 任务描述（contest/fpt26-harness/tasks/*/task.toml）：如 residual_stream_deadlock 的突发写模式。
- P2 projection 真机运行蒸馏的 csim 通用失败类。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `seed_entries() -> list[KBEntry]` | function | 返回 22 条条目（v0.7.0，2026-07-20 由 7 条种子扩充）：synth 类 6 条（dataflow 冲突/II 调度失败/数组端口冲突/pragma 同层冲突/**pragma 文件作用域 [HLS 207-6969]**/**DATA_PACK 打类型名**）+ csim 类 4 条（Test Case Failed/compile_error/**浮点重排容差**/**边界条件**）+ cosim 类 6 条（FIFO 突发写死锁/**FIFO 深度过浅**/**TLAST 缺失**/**TVALID/TREADY 握手**/**ap_ctrl 挂起**/**synth-cosim 延迟不一致**）+ pattern 类 6 条（P2-13 论文修法模式：检索先行/正确性优化分离/语法优先/错误消息配对/期望值差异反馈/有界反馈循环） |

### 导出
无 `__all__`；由包级 `__init__.py` 重导出 `seed_entries`。

### 依赖
- 内部依赖：`.retriever.KBEntry`
- 外部依赖：无

### 关键设计点
1. **签名用小写短串**：检索器做大小写不敏感子串匹配，signatures 必须是错误码/关键词级短串（如 `"[xform 203-313]"`、`"deadlock"`），不能放整句——整句不会被命中。
2. **来源可追溯**：每条在 docstring 里注明出处（AMD 案例 / 任务描述 / 真机日志），禁止凭记忆杜撰错误码语义。
3. **扩充路径**：P2-12/P2-13/P3-08 已完成（2026-07-20，7→22 条）：真机日志来源 4 条（[HLS 207-6969] pragma 文件作用域、DATA_PACK 误用、浮点容差、边界条件）、cosim 协议类 5 条、论文修法模式 6 条（HLS Repair arXiv 2407.03889 / RTLFixer arXiv 2311.16543 / AutoChip arXiv 2311.04887）。量大后可按架构 §9 迁到 `entries/*.yaml`。

---

## English

### Purpose
Seed knowledge-base entry data (first iteration, architecture §6.2 P2 coverage). Makes the "error signature -> fix" retrieval-augmentation path work out of the box: when synth/cosim/csim fails, the signatures distilled by `build_feedback` hit real entries that get injected into the repair prompt. Every entry is traceable to a real source — no invented error-code meanings:

- AMD LLM4HLS SHA-256 case study (dev-log 2026-07-11-03): `[XFORM 203-313]` / `[RTGEN 206-102]` observed during a function-merge refactor (dataflow conflict / illegal connection); the AMD-named LLM weaknesses (pragma interaction rules, dead streams after merging).
- Harness task descriptions (contest/fpt26-harness/tasks/*/task.toml), e.g. the residual_stream_deadlock burst-write pattern.
- Generic csim failure classes distilled from the real P2 projection run.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `seed_entries() -> list[KBEntry]` | function | Returns 22 entries (v0.7.0, expanded from 7 seeds on 2026-07-20): 6 synth (dataflow conflict / II scheduling failure / array port conflict / same-level pragma conflict / **pragma at file scope [HLS 207-6969]** / **DATA_PACK on a type name**) + 4 csim (Test Case Failed / compile_error / **fp reorder tolerance** / **boundary conditions**) + 6 cosim (FIFO burst-write deadlock / **FIFO depth too shallow** / **missing TLAST** / **TVALID/TREADY handshake** / **ap_ctrl hang** / **synth-vs-cosim latency mismatch**) + 6 pattern (P2-13 paper repair patterns: retrieve-before-repair / correctness-before-optimization / syntax-first / error-message pairing / mismatch-diff feedback / bounded feedback loop) |

### Exports
No `__all__`; `seed_entries` is re-exported by the package `__init__.py`.

### Dependencies
- Internal: `.retriever.KBEntry`
- External: none

### Key Design Points
1. **Signatures are short lowercase strings**: the retriever does case-insensitive substring matching, so signatures must be error-code/keyword-level short strings (e.g. `"[xform 203-313]"`, `"deadlock"`), never full sentences — sentences will not match.
2. **Traceable sources**: every entry cites its source in the module docstring (AMD case study / task descriptions / real run logs); never fabricate error-code semantics from memory.
3. **Growth path**: P2-12/P2-13/P3-08 completed (2026-07-20, 7->22 entries): 4 from real machine logs ([HLS 207-6969] pragma at file scope, DATA_PACK misuse, fp tolerance, boundary conditions), 5 cosim protocol entries, 6 paper repair patterns (HLS Repair arXiv 2407.03889 / RTLFixer arXiv 2311.16543 / AutoChip arXiv 2311.04887). May migrate to `entries/*.yaml` per architecture §9 once it grows further.
