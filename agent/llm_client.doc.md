# agent/llm_client.py 说明文档

## 中文说明

### 用途
LLM 客户端——harness LLMClient Protocol 的领域封装。实现 agent-architecture.md §8：在 `complete(system, user) -> str` 后端之上增加 repair / review / propose_strategies / apply_strategy 四个领域方法；代码提取复用 harness 的 `_extract_code`。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Strategy` | class (dataclass) | AMD Phase 2 一条候选优化策略：name、rationale、expected_gain、risk |
| `HLSLLMClient` | class | 包装注入的后端（ScriptedClient/OpenRouterClient/DeepSeekClient），不自行导入后端 |
| `HLSLLMClient.__init__(backend, max_review_retries=1)` | method | 构造，持有 backend 与额外重试次数 |
| `HLSLLMClient._complete(system, user) -> str` | method | 转发原始完成调用到 backend |
| `HLSLLMClient.repair(task, code, feedback_text, kb_text) -> str\|None` | method | 求修正内核，返回提取的代码或 None |
| `HLSLLMClient.review(task, code, focus) -> (bool, str)` | method | 交叉检查候选，回复以 "PASS" 开头则通过 |
| `HLSLLMClient.propose_strategies(task, code, synth_summary) -> list[Strategy]` | method | AMD Phase 2：列出 2-4 条带权衡的优化策略 |
| `HLSLLMClient.apply_strategy(task, code, strategy) -> str\|None` | method | AMD Phase 3：对选定策略生成代码 |
| `_parse_strategies(text) -> list[Strategy]` | function | 宽松解析自由格式策略列表为 Strategy 对象 |
| `_headers(task) -> str` | function | 将 task.headers 渲染为注释分隔的组合块 |

### 导出
无 `__all__`；主要导出 `HLSLLMClient` 与 `Strategy`。

### 依赖
- 内部依赖：无（被 `.main_loop` 使用）
- 外部依赖：标准库 `re`、`dataclasses`；可选导入 `llm4hls.agent._extract_code`（失败时用内置回退提取器）

### 关键设计点
- 后端注入：HLSLLMClient 不导入任何具体后端，兼容 ScriptedClient（离线）/OpenRouterClient（真实）/DeepSeekClient，是 drop-in 适配。
- 代码提取复用 harness `_extract_code`（fenced ```cpp 块），import 失败时回退到模块内 `_CODE_RE`；保证与 harness 约定一致。
- 提示词模板模块级常量（_REPAIR_SYSTEM/_REVIEW_SYSTEM/_STRATEGY_SYSTEM）便于调优；review 以回复是否以 "PASS" 开头判定。
- 架构章节引用：§8 LLM 客户端。

---

## English

### Purpose
LLM client — domain wrappers over the harness LLMClient Protocol. Implements agent-architecture.md §8: adds repair / review / propose_strategies / apply_strategy domain methods on top of a `complete(system, user) -> str` backend; code extraction reuses the harness `_extract_code`.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Strategy` | class (dataclass) | One AMD Phase 2 candidate optimization strategy: name, rationale, expected_gain, risk |
| `HLSLLMClient` | class | Wraps an injected backend (ScriptedClient/OpenRouterClient/DeepSeekClient); never imports a backend itself |
| `HLSLLMClient.__init__(backend, max_review_retries=1)` | method | Construction; holds backend and extra retry count |
| `HLSLLMClient._complete(system, user) -> str` | method | Forwards a raw completion call to the backend |
| `HLSLLMClient.repair(task, code, feedback_text, kb_text) -> str\|None` | method | Asks for a corrected kernel; returns extracted code or None |
| `HLSLLMClient.review(task, code, focus) -> (bool, str)` | method | Cross-checks a candidate; passes when the reply starts with "PASS" |
| `HLSLLMClient.propose_strategies(task, code, synth_summary) -> list[Strategy]` | method | AMD Phase 2: lists 2-4 optimization strategies with tradeoffs |
| `HLSLLMClient.apply_strategy(task, code, strategy) -> str\|None` | method | AMD Phase 3: generates code applying a chosen strategy |
| `_parse_strategies(text) -> list[Strategy]` | function | Best-effort parse of a free-form strategy list into Strategy objects |
| `_headers(task) -> str` | function | Renders task.headers as a comment-delimited combined block |

### Exports
No `__all__`; primary exports are `HLSLLMClient` and `Strategy`.

### Dependencies
- Internal: none (consumed by `.main_loop`)
- External: standard library `re`, `dataclasses`; optional import of `llm4hls.agent._extract_code` (falls back to an inline extractor on failure)

### Key Design Points
- Backend injection: HLSLLMClient imports no concrete backend, making it a drop-in adapter for ScriptedClient (offline) / OpenRouterClient (real) / DeepSeekClient.
- Code extraction reuses harness `_extract_code` (fenced ```cpp block) with a module-level `_CODE_RE` fallback if the import fails, matching harness conventions exactly.
- Prompt templates are module-level constants (_REPAIR_SYSTEM/_REVIEW_SYSTEM/_STRATEGY_SYSTEM) for easy tuning; review verdict is decided by whether the reply starts with "PASS".
- Architecture section referenced: §8 LLM client.
