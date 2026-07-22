# agent/knowledge_base/entries.py 说明文档

## 中文说明

### 用途
知识库语料**加载器**（v0.7.1 起；此前是内嵌 Python 数据）。语料单源是同目录的 **`entries.json`**（22 条）——数据与代码解耦，改条目不用动 Python，提交物里 KB 也能作为独立产物展示。用 JSON 而非架构 §9 原计划的 YAML：项目纯标准库，不引 PyYAML；schema 对齐备赛学习手册附录 B 草案（id/symptom/root_cause/fix/example/signatures）。条目来源严格可追溯（见文末"条目清单"），不编造错误码含义。

- AMD LLM4HLS SHA-256 案例文章（dev-log 2026-07-11-03）：`[XFORM 203-313]` / `[RTGEN 206-102]` 出现在函数合并重构（dataflow 冲突/非法连接）场景；AMD 点名的 LLM 短板（pragma 交互规则、合并后死 stream）。
- harness 任务描述（contest/fpt26-harness/tasks/*/task.toml）：如 residual_stream_deadlock 的突发写模式。
- P2 projection 真机运行蒸馏的 csim 通用失败类。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `load_entries(path=None) -> list[KBEntry]` | function | 从 JSON 语料加载条目（默认 `entries.json`，与本模块同目录）；文件缺失抛 FileNotFoundError，条目缺字段抛 ValueError（报序号） |
| `seed_entries() -> list[KBEntry]` | function | 兼容入口（历史名）：调用 `load_entries()`；调用方（run_agent.py / TUI / 测试）无感 |

语料 `entries.json` 共 22 条（2026-07-20 由 7 条种子扩充）：synth 类 6 条（dataflow 冲突/II 调度失败/数组端口冲突/pragma 同层冲突/**pragma 文件作用域 [HLS 207-6969]**/**DATA_PACK 打类型名**）+ csim 类 4 条（Test Case Failed/compile_error/**浮点重排容差**/**边界条件**）+ cosim 类 6 条（FIFO 突发写死锁/**FIFO 深度过浅**/**TLAST 缺失**/**TVALID/TREADY 握手**/**ap_ctrl 挂起**/**synth-cosim 延迟不一致**）+ pattern 类 6 条（P2-13 论文修法模式：检索先行/正确性优化分离/语法优先/错误消息配对/期望值差异反馈/有界反馈循环）

### 导出
无 `__all__`；由包级 `__init__.py` 重导出 `seed_entries`。

### 依赖
- 内部依赖：`.retriever.KBEntry`
- 外部依赖：无

### 关键设计点
1. **签名用小写短串**：检索器做大小写不敏感子串匹配，signatures 必须是错误码/关键词级短串（如 `"[xform 203-313]"`、`"deadlock"`），不能放整句——整句不会被命中。
2. **来源可追溯**：每条在 docstring 里注明出处（AMD 案例 / 任务描述 / 真机日志），禁止凭记忆杜撰错误码语义。
3. **扩充路径**：P2-12/P2-13/P3-08 已完成（2026-07-20，7→22 条）：真机日志来源 4 条（[HLS 207-6969] pragma 文件作用域、DATA_PACK 误用、浮点容差、边界条件）、cosim 协议类 5 条、论文修法模式 6 条（HLS Repair arXiv 2407.03889 / RTLFixer arXiv 2311.16543 / AutoChip arXiv 2311.04887）。**v0.7.1 起语料落 `entries.json`**（架构 §9 迁移，纯 stdlib 用 JSON 不用 YAML）——加条目直接编辑该文件。

---

## English

### Purpose
Knowledge-base corpus **loader** (since v0.7.1; previously embedded Python data). The single source of the corpus is **`entries.json`** next to this module (22 entries) — data is decoupled from code, so entries can be edited without touching Python and the KB ships as a standalone artifact in the submission. JSON instead of the YAML planned in architecture §9: the project is pure stdlib (no PyYAML); the schema matches the draft in 备赛学习手册 appendix B (id/symptom/root_cause/fix/example/signatures). Every entry is traceable to a real source — no invented error-code meanings:

- AMD LLM4HLS SHA-256 case study (dev-log 2026-07-11-03): `[XFORM 203-313]` / `[RTGEN 206-102]` observed during a function-merge refactor (dataflow conflict / illegal connection); the AMD-named LLM weaknesses (pragma interaction rules, dead streams after merging).
- Harness task descriptions (contest/fpt26-harness/tasks/*/task.toml), e.g. the residual_stream_deadlock burst-write pattern.
- Generic csim failure classes distilled from the real P2 projection run.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `load_entries(path=None) -> list[KBEntry]` | function | Loads entries from the JSON corpus (default `entries.json` next to this module); FileNotFoundError when the corpus is missing, ValueError (with the entry index) when a required field is absent |
| `seed_entries() -> list[KBEntry]` | function | Backward-compatible entry point (historical name): calls `load_entries()`; callers (run_agent.py / TUI / tests) are unaffected |

The corpus `entries.json` holds 22 entries (expanded from 7 seeds on 2026-07-20): 6 synth (dataflow conflict / II scheduling failure / array port conflict / same-level pragma conflict / **pragma at file scope [HLS 207-6969]** / **DATA_PACK on a type name**) + 4 csim (Test Case Failed / compile_error / **fp reorder tolerance** / **boundary conditions**) + 6 cosim (FIFO burst-write deadlock / **FIFO depth too shallow** / **missing TLAST** / **TVALID/TREADY handshake** / **ap_ctrl hang** / **synth-vs-cosim latency mismatch**) + 6 pattern (P2-13 paper repair patterns: retrieve-before-repair / correctness-before-optimization / syntax-first / error-message pairing / mismatch-diff feedback / bounded feedback loop)

### Exports
No `__all__`; `seed_entries` is re-exported by the package `__init__.py`.

### Dependencies
- Internal: `.retriever.KBEntry`
- External: none

### Key Design Points
1. **Signatures are short lowercase strings**: the retriever does case-insensitive substring matching, so signatures must be error-code/keyword-level short strings (e.g. `"[xform 203-313]"`, `"deadlock"`), never full sentences — sentences will not match.
2. **Traceable sources**: every entry cites its source in the module docstring (AMD case study / task descriptions / real run logs); never fabricate error-code semantics from memory.
3. **Growth path**: P2-12/P2-13/P3-08 completed (2026-07-20, 7->22 entries): 4 from real machine logs ([HLS 207-6969] pragma at file scope, DATA_PACK misuse, fp tolerance, boundary conditions), 5 cosim protocol entries, 6 paper repair patterns (HLS Repair arXiv 2407.03889 / RTLFixer arXiv 2311.16543 / AutoChip arXiv 2311.04887). **Since v0.7.1 the corpus lives in `entries.json`** (architecture §9 migration; JSON over YAML to stay pure stdlib) — add entries by editing that file.
