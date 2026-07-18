# agent/feedback.py 说明文档

## 中文说明

### 用途
反馈构建器：把 harness ToolResult 蒸馏为 LLM 友好文本 + 错误签名。实现 agent-architecture.md §4.2 的反馈臂——harness 已解析 csynth.xml/cosim.rpt，本模块负责提炼为 (a) KB 检索用的短错误签名与 (b) 修复提示词的简洁反馈块。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Feedback` | class (dataclass) | 结构化反馈：phases、error_codes、signatures、log_tail |
| `Feedback.is_empty() -> bool` | method | 无 phases 且无 error_codes 时为真 |
| `Feedback.as_prompt_block() -> str` | method | 渲染为修复提示词的简洁块（工具结果+错误码+日志尾），空则 "(no feedback)" |
| `build_feedback(*results) -> Feedback` | function | 由若干 ToolResult 构建反馈，提取 Vitis 错误码、deadlock/streaming 关键词签名、日志尾 |

### 导出
无 `__all__`；主要导出 `Feedback` 与 `build_feedback`。

### 依赖
- 内部依赖：无
- 外部依赖：标准库 `re`、`dataclasses`；运行期消费 harness 的 ToolResult（kind/phase/log/ok 等属性）

### 关键设计点
- AMD 教训落地：反馈具体错误码（如 `[XFORM 203-313]`）而非模糊描述；正则 `_ERROR_CODE_RE` 匹配 `[XFORM|RTGEN|SIM|HLS|VPP NNN-NNN]` 格式。
- SWE-agent ACI 教训：工具输出须结构化到 LLM 可直接行动；signatures = 关键词（deadlock/streaming）+ 错误码，去重保序供 KB 检索。
- log_tail 截取最后 3000 字符（镜像 ReferenceAgent._feedback 截断）。

---

## English

### Purpose
Feedback builder: distills a harness ToolResult into LLM-friendly text + error signatures. Implements the feedback arm of agent-architecture.md §4.2 — the harness already parses csynth.xml/cosim.rpt; this module distills that into (a) short error signatures for KB retrieval and (b) a concise feedback block for the repair prompt.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Feedback` | class (dataclass) | Structured feedback: phases, error_codes, signatures, log_tail |
| `Feedback.is_empty() -> bool` | method | True when no phases and no error_codes |
| `Feedback.as_prompt_block() -> str` | method | Renders a concise block for the repair prompt (tool results + error codes + log tail); "(no feedback)" when empty |
| `build_feedback(*results) -> Feedback` | function | Builds feedback from ToolResults, extracting Vitis error codes, deadlock/streaming keyword signatures, and a log tail |

### Exports
No `__all__`; primary exports are `Feedback` and `build_feedback`.

### Dependencies
- Internal: none
- External: standard library `re`, `dataclasses`; consumes harness ToolResult at runtime (kind/phase/log/ok attributes)

### Key Design Points
- AMD lesson applied: feed back specific error codes (e.g. `[XFORM 203-313]`) rather than vague descriptions; the `_ERROR_CODE_RE` regex matches `[XFORM|RTGEN|SIM|HLS|VPP NNN-NNN]`.
- SWE-agent ACI lesson: tool output must be structured enough for the LLM to act on directly; signatures = keywords (deadlock/streaming) + error codes, deduped preserving order for KB retrieval.
- log_tail takes the last 3000 characters (mirroring ReferenceAgent._feedback truncation).
