# agent/mechanical_checks.py 说明文档

## 中文说明

### 用途
机械检查——花工具调用前的 LLM-free 硬闸门。LLM 自检有盲点（测试中放过了被改的签名），这些确定性检查捕获高价值、易验证且 LLM 易漏的风险：签名变更、头文件 include 丢失、禁用 token。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `_extract_signature(code, top_fn) -> str\|None` | function | 尽力从内核代码抓取顶层函数签名行 |
| `check_signature_unchanged(original, candidate, top_fn) -> (bool, str)` | function | 校验顶层函数签名未被改动 |
| `check_header_included(candidate, header_names) -> (bool, str)` | function | 校验内核仍 include 必需头文件 |
| `mechanical_review(original, candidate, task) -> (bool, list[str])` | method | 跑全部机械检查，返回 (passed, issues) |

### 导出
无 `__all__`；主要导出 `mechanical_review`（及 `check_signature_unchanged`、`check_header_included`）。

### 依赖
- 内部依赖：无（被 `.main_loop` 使用）
- 外部依赖：标准库 `re`；运行期使用 harness Task 的 `.top` 与 `.headers`

### 关键设计点
- 作为第一道闸门，LLM review 仅在机械检查通过后运行（见 main_loop._repair_with_review）。
- 签名提取用正则匹配 `<返回类型> top_fn(<参数>)`，原候选都解析不到则判失败；签名不一致时给出 was/now 对比。
- 头文件检查：`header_names` 中任一名未出现在候选源码即判缺失；mechanical_review 聚合签名与头文件两项结果为 issues 列表。

---

## English

### Purpose
Mechanical checks — LLM-free hard gates before spending a tool call. LLM self-review has blind spots (it passed a changed signature in testing); these deterministic checks catch high-value, easy-to-verify hazards an LLM tends to miss: signature changes, lost header includes, forbidden tokens.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `_extract_signature(code, top_fn) -> str\|None` | function | Best-effort grab of the top-level function signature line from kernel code |
| `check_signature_unchanged(original, candidate, top_fn) -> (bool, str)` | function | Verifies the top-level function signature was not changed |
| `check_header_included(candidate, header_names) -> (bool, str)` | function | Verifies the kernel still includes its required headers |
| `mechanical_review(original, candidate, task) -> (bool, list[str])` | method | Runs all mechanical checks; returns (passed, issues) |

### Exports
No `__all__`; primary exports are `mechanical_review` (plus `check_signature_unchanged`, `check_header_included`).

### Dependencies
- Internal: none (consumed by `.main_loop`)
- External: standard library `re`; uses harness Task `.top` and `.headers` at runtime

### Key Design Points
- Acts as the first gate; LLM review runs only after mechanical checks pass (see main_loop._repair_with_review).
- Signature extraction uses a regex matching `<return type> top_fn(<args>)`; if either side cannot be parsed it fails; on mismatch it reports a was/now comparison.
- Header check: any header name absent from the candidate source is flagged missing; mechanical_review aggregates signature and header results into the issues list.
