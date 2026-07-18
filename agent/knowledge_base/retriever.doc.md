# agent/knowledge_base/retriever.py 说明文档

## 中文说明

### 用途
实现知识库条目与第一代检索器：把编译/仿真反馈中的错误码与关键词作为签名，与条目的签名及症状/根因文本做大小写不敏感子串匹配（对应架构 §6.3）。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `KBEntry` | dataclass | 单条 bug→fix 条目；字段 `id`/`symptom`/`root_cause`/`fix`/`example`(默认"")/`signatures`(默认[])；`summary() -> str` 返回供 prompt 使用的多行摘要 |
| `KnowledgeBase` | class | 检索器；`__init__(entries=None)`、`add(entry)` 追加条目、`search(signatures) -> list[KBEntry]` 做匹配 |

### 导出
无 `__all__`；模块级定义 `KBEntry` 与 `KnowledgeBase`（由包 `__init__` 重导出）。

### 依赖
- 内部依赖：无
- 外部依赖：标准库 `dataclasses`（`dataclass`/`field`）

### 关键设计点
1. **刻意简单的检索**：`search` 把每个条目的 `signatures + [symptom, root_cause]` 拼成 haystack 并 lower-case，查询签名任一作为子串命中即算匹配；embedding 检索留待语料增长后再引入。
2. **去重与保序**：用 `seen: set[str]` 按 `entry.id` 去重，命中结果保留语料原始顺序；空签名输入直接返回空列表。
3. **prompt 友好**：`KBEntry.summary()` 输出 `[id] symptom` + root cause + fix（+ 可选 example）的多行文本，便于直接拼进 LLM 提示。

---

## English

### Purpose
Implements KB entries and the first-iteration retriever: treats error codes and keywords from compile/sim feedback as signatures and matches them case-insensitively as substrings against each entry's signatures and symptom/root_cause text (architecture §6.3).

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `KBEntry` | dataclass | A single bug->fix entry; fields `id`/`symptom`/`root_cause`/`fix`/`example`(default "")/`signatures`(default []); `summary() -> str` returns a multi-line summary for the prompt |
| `KnowledgeBase` | class | Retriever; `__init__(entries=None)`, `add(entry)` appends an entry, `search(signatures) -> list[KBEntry]` performs matching |

### Exports
No `__all__`; module-level `KBEntry` and `KnowledgeBase` (re-exported by the package `__init__`).

### Dependencies
- Internal: none
- External: stdlib `dataclasses` (`dataclass`/`field`)

### Key Design Points
1. **Deliberately simple retrieval**: `search` joins each entry's `signatures + [symptom, root_cause]` into a haystack and lower-cases it; a hit on any query signature as a substring counts as a match. Embedding retrieval is deferred until the corpus grows.
2. **Dedup and order preservation**: a `seen: set[str]` dedups by `entry.id`; hits preserve corpus order; an empty signature input returns an empty list immediately.
3. **Prompt-friendly**: `KBEntry.summary()` emits `[id] symptom` + root cause + fix (+ optional example) as multi-line text, ready to splice into an LLM prompt.
