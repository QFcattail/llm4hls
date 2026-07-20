# agent/llm_client.py 说明文档

## 中文说明

### 用途
LLM 客户端——harness LLMClient Protocol 的领域封装。实现 agent-architecture.md §8：在 `complete(system, user) -> str` 后端之上增加 repair / review / extract_design_brief / propose_strategies / select_strategies / apply_strategies 六个领域方法；代码提取复用 harness 的 `_extract_code`。按 §8.1 硬要求，所有改代码类 prompt 必注官方设计文档（task.description）与只读 headers；optimize 类方法另加 synth 报告与设计摘要。v2.4 起策略支持组合：propose 标注兼容性、select 评审 AI 复核选子集、apply 合并应用（双重确认）。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Strategy` | class (dataclass) | AMD Phase 2 一条候选优化策略：name、rationale、expected_gain、risk、`combinable_with`（v2.4 兼容性标注） |
| `HLSLLMClient` | class | 包装注入的后端（ScriptedClient/OpenRouterClient/DeepSeekClient），不自行导入后端 |
| `HLSLLMClient.__init__(backend, max_review_retries=1, token_mode="full")` | method | 构造，持有 backend 与额外重试次数；v0.7.0 起 `token_mode` 选择 token 节省级别（full 默认=逐字节旧行为，未知值抛 ValueError） |
| `HLSLLMClient._effort(site) -> str\|None` | method | 查 `_EFFORT_POLICY`：当前 token_mode 下该调用点的 reasoning_effort 覆盖（None=用后端默认） |
| `HLSLLMClient._complete(system, user, effort=None) -> str` | method | 转发原始完成调用到 backend；effort 非空时尝试带 reasoning_effort 调用，后端不支持则 TypeError 回退普通调用 |
| `HLSLLMClient._complete_json(system, user, effort=None) -> str` | method | JSON 结构化输出调用（DeepSeek `response_format: json_object`），同样支持 effort 覆盖与回退 |
| `HLSLLMClient.repair(task, code, feedback_text, kb_text) -> str\|None` | method | 求修正内核，返回提取的代码或 None |
| `HLSLLMClient.review(task, code, focus) -> (bool, str)` | method | 交叉检查候选，回复以 "PASS" 开头则通过 |
| `HLSLLMClient.extract_design_brief(task, code) -> str` | method | AMD Phase 1：从当前内核提炼设计摘要（功能/循环结构/数据流/瓶颈猜想），optimize 循环前调一次缓存 |
| `HLSLLMClient.propose_strategies(task, code, synth_summary, design_brief="") -> list[Strategy]` | method | AMD Phase 2a：注入设计文档+摘要+synth 报告；**v0.5.0 起 JSON 结构化输出**（`_complete_json` 走 `response_format: json_object`，正则仅作非 JSON 后端兜底） |
| `HLSLLMClient.select_strategies(task, code, strategies, synth_summary, design_brief="") -> (list[int], str, list[dict], bool)` | method | Phase 2b 评审 AI（JSON 模式）：**可行性+兼容性双审查**——带毒策略进 rejected（含 why），再选子集；解析失败重试一次，仍失败回退 `[0]` 且 fallback=True（不静默） |
| `HLSLLMClient.apply_strategies(task, code, strategies, design_brief="", failure_feedback="") -> str\|None` | method | AMD Phase 3：子集**合并应用**；带 failure_feedback 时注入上次失败反馈（避开错误） |
| `_parse_strategies(text) -> list[Strategy]` | function | 宽松解析自由格式策略列表（含 combinable_with 行） |
| `_parse_pick(text, n) -> list[int]` | function | 解析评审 AI 的 `PICK:` 行为合法 0 基索引（失败回退 `[0]`） |
| `_parse_reason(text) -> str` | function | 解析 `REASON:` 一行（截断 200 字符） |
| `_headers(task) -> str` | function | 将 task.headers 渲染为注释分隔的组合块 |

### 导出
无 `__all__`；主要导出 `HLSLLMClient` 与 `Strategy`。

### 依赖
- 内部依赖：无（被 `.main_loop` 使用）
- 外部依赖：标准库 `re`、`dataclasses`；可选导入 `llm4hls.agent._extract_code`（失败时用内置回退提取器）

### 关键设计点
- 后端注入：HLSLLMClient 不导入任何具体后端，兼容 ScriptedClient（离线）/OpenRouterClient（真实）/DeepSeekClient，是 drop-in 适配。
- **token-mode 分级开关（v0.7.0，P4-03）**：模块级 `_EFFORT_POLICY` 表——`full`（默认，成品形态）不施加任何覆盖/裁剪，行为与旧版逐字节一致；`balanced` 给 review/select 两个判定类调用点传 `reasoning_effort="off"`（关 thinking，reasoning 占 completion ~89% 是最大头）；`aggressive` 再覆盖 brief/propose，且 select 的 user prompt 去掉静态 `## Kernel specification` 块。无 effort 旋钮的后端（ScriptedClient 等）经 TypeError 回退普通调用，不崩。
- 代码提取复用 harness `_extract_code`（fenced ```cpp 块），import 失败时回退到模块内 `_CODE_RE`；保证与 harness 约定一致。
- 提示词模板模块级常量（_REPAIR_SYSTEM/_REVIEW_SYSTEM/_STRATEGY_SYSTEM/_BRIEF_SYSTEM/_SELECT_SYSTEM）便于调优；review 以回复是否以 "PASS" 开头判定。
- §8.1 硬要求落实：repair/propose_strategies/apply_strategies 的 user prompt 固定含 `## Kernel specification`（description）与 `## Fixed header(s)`；optimize 两方法另含 `## Design brief` 与（propose 侧）`## Current synthesis`——AMD Phase 1 教训：没有上下文，LLM 只给泛泛建议。
- v2.4 策略组合：propose 逐策略标 `combinable_with`；select 评审 AI（`_SELECT_SYSTEM` 持怀疑态度，"in doubt, pick a single strategy"）复核后才允许组合；`_parse_pick` 永远返回非空合法索引（评审失败不崩优化循环）。
- 架构章节引用：§8 LLM 客户端、§4.4 Phase 1/2/3。

---

## English

### Purpose
LLM client — domain wrappers over the harness LLMClient Protocol. Implements agent-architecture.md §8: adds repair / review / extract_design_brief / propose_strategies / select_strategies / apply_strategies domain methods on top of a `complete(system, user) -> str` backend; code extraction reuses the harness `_extract_code`. Per §8.1's hard requirement, every code-changing prompt injects the official design document (task.description) and the read-only headers; the optimize pair additionally receives the synth report and the design brief. Since v2.4 strategies are composable: propose annotates compatibility, the select reviewer AI re-checks it and picks a subset, apply merges the subset into one candidate (dual confirmation).

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Strategy` | class (dataclass) | One AMD Phase 2 candidate strategy: name, rationale, expected_gain, risk, `combinable_with` (v2.4 compatibility annotation) |
| `HLSLLMClient` | class | Wraps an injected backend (ScriptedClient/OpenRouterClient/DeepSeekClient); never imports a backend itself |
| `HLSLLMClient.__init__(backend, max_review_retries=1, token_mode="full")` | method | Construction; holds backend and extra retry count; since v0.7.0 `token_mode` selects the token-saving level (default "full" = byte-identical legacy behavior; unknown values raise ValueError) |
| `HLSLLMClient._effort(site) -> str\|None` | method | Looks up `_EFFORT_POLICY`: the reasoning_effort override for a call site under the current token_mode (None = backend default) |
| `HLSLLMClient._complete(system, user, effort=None) -> str` | method | Forwards a raw completion call to the backend; when effort is set, tries passing reasoning_effort and falls back to a plain call on TypeError |
| `HLSLLMClient._complete_json(system, user, effort=None) -> str` | method | JSON structured-output call (DeepSeek `response_format: json_object`), with the same effort override and fallback |
| `HLSLLMClient.repair(task, code, feedback_text, kb_text) -> str\|None` | method | Asks for a corrected kernel; returns extracted code or None |
| `HLSLLMClient.review(task, code, focus) -> (bool, str)` | method | Cross-checks a candidate; passes when the reply starts with "PASS" |
| `HLSLLMClient.extract_design_brief(task, code) -> str` | method | AMD Phase 1: distills the current kernel's design (functionality / loop structure / dataflow / bottleneck hypotheses); called once before the optimize loop and cached |
| `HLSLLMClient.propose_strategies(task, code, synth_summary, design_brief="") -> list[Strategy]` | method | AMD Phase 2a: injects design document + brief + synth report; **JSON structured output since v0.5.0** (`_complete_json` uses `response_format: json_object`; regex is only the non-JSON-backend fallback) |
| `HLSLLMClient.select_strategies(task, code, strategies, synth_summary, design_brief="") -> (list[int], str, list[dict], bool)` | method | Phase 2b selector review AI (JSON mode): **feasibility + compatibility review** — poisoned plans go to `rejected` (with why), then a subset is picked; one retry on parse failure, then `[0]` with fallback=True (never silent) |
| `HLSLLMClient.apply_strategies(task, code, strategies, design_brief="", failure_feedback="") -> str\|None` | method | AMD Phase 3: merges the subset into ONE candidate; injects the previous failure feedback when given (avoid repeating the mistake) |
| `_parse_strategies(text) -> list[Strategy]` | function | Best-effort parse of a free-form strategy list (incl. combinable_with lines) |
| `_parse_pick(text, n) -> list[int]` | function | Parses the selector's `PICK:` line into valid 0-based indexes (falls back to `[0]`) |
| `_parse_reason(text) -> str` | function | Parses the one-line `REASON:` field (capped at 200 chars) |
| `_headers(task) -> str` | function | Renders task.headers as a comment-delimited combined block |

### Exports
No `__all__`; primary exports are `HLSLLMClient` and `Strategy`.

### Dependencies
- Internal: none (consumed by `.main_loop`)
- External: standard library `re`, `dataclasses`; optional import of `llm4hls.agent._extract_code` (falls back to an inline extractor on failure)

### Key Design Points
- Backend injection: HLSLLMClient imports no concrete backend, making it a drop-in adapter for ScriptedClient (offline) / OpenRouterClient (real) / DeepSeekClient.
- **Token-mode graded switch (v0.7.0, P4-03)**: the module-level `_EFFORT_POLICY` table — `full` (default, shipped form) applies no overrides or trims and is byte-identical to legacy behavior; `balanced` sends `reasoning_effort="off"` (thinking disabled) for the two verdict-class call sites review/select (reasoning is ~89% of completion tokens, the dominant share); `aggressive` additionally covers brief/propose and drops the static `## Kernel specification` block from the select prompt. Backends without an effort knob (ScriptedClient etc.) fall back to a plain call via TypeError instead of crashing.
- Code extraction reuses harness `_extract_code` (fenced ```cpp block) with a module-level `_CODE_RE` fallback if the import fails, matching harness conventions exactly.
- Prompt templates are module-level constants (_REPAIR_SYSTEM/_REVIEW_SYSTEM/_STRATEGY_SYSTEM/_BRIEF_SYSTEM/_SELECT_SYSTEM) for easy tuning; review verdict is decided by whether the reply starts with "PASS".
- §8.1 hard requirement enforced: repair/propose_strategies/apply_strategies user prompts always contain `## Kernel specification` (description) and `## Fixed header(s)`; the optimize pair additionally carries `## Design brief` and (on the propose side) `## Current synthesis` — AMD Phase 1's lesson: without context the LLM only gives generic advice.
- v2.4 strategy combos: propose annotates `combinable_with` per strategy; the select reviewer AI (`_SELECT_SYSTEM` is skeptical: "in doubt, pick a single strategy") must agree before a combo is allowed; `_parse_pick` always returns a non-empty valid index list (a selector failure never crashes the optimize loop).
- Architecture sections referenced: §8 LLM client, §4.4 Phase 1/2/3.
