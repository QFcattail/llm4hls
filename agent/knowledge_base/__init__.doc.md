# agent/knowledge_base/__init__.py 说明文档

## 中文说明

### 用途
knowledge_base 包的初始化模块，对外导出知识库检索的三项核心符号 `KnowledgeBase`、`KBEntry` 与 `seed_entries`。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `KnowledgeBase` | class（从 `.retriever` 重导出） | 第一代检索器：把反馈签名与条目做大小写不敏感子串匹配 |
| `KBEntry` | dataclass（从 `.retriever` 重导出） | 单条 bug→fix 知识条目，含症状/根因/修复/示例/触发签名 |
| `seed_entries` | function（从 `.entries` 重导出） | 返回 7 条种子条目（synth 类 4 + cosim 类 1 + csim 类 2），让检索链路开箱可用 |

### 导出
`__all__ = ["KnowledgeBase", "KBEntry", "seed_entries"]`

### 依赖
- 内部依赖：`.retriever`（检索器实现）、`.entries`（种子条目数据）
- 外部依赖：无

### 关键设计点
1. **精简门面**：包级 `__init__.py` 只做重导出，使外部可直接 `from agent.knowledge_base import KnowledgeBase, seed_entries`。
2. **分阶段路线**：模块 docstring 标明迭代规划——第一代做错误码/关键词匹配（架构 §6.3），第二代做功能模式/范例检索（§6.4）。
3. **种子先行**：v0.2.0 起入口（run_agent.py / tui/app.py）默认装载 `seed_entries()`；P2-12（HLS 域主）在此基础上扩充到 >=10 条。

---

## English

### Purpose
Package initializer for `knowledge_base`, re-exporting the three core symbols of KB retrieval: `KnowledgeBase`, `KBEntry`, and `seed_entries`.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `KnowledgeBase` | class (re-exported from `.retriever`) | First-iteration retriever: case-insensitive substring matching of feedback signatures against entries |
| `KBEntry` | dataclass (re-exported from `.retriever`) | A single bug->fix knowledge entry with symptom/root_cause/fix/example/trigger signatures |
| `seed_entries` | function (re-exported from `.entries`) | Returns the 7 seed entries (4 synth + 1 cosim + 2 csim classes) so the retrieval path works out of the box |

### Exports
`__all__ = ["KnowledgeBase", "KBEntry", "seed_entries"]`

### Dependencies
- Internal: `.retriever` (retriever implementation), `.entries` (seed entry data)
- External: none

### Key Design Points
1. **Lean facade**: the package `__init__.py` only re-exports, so callers can do `from agent.knowledge_base import KnowledgeBase, seed_entries` directly.
2. **Phased roadmap**: the module docstring states the iteration plan — first iteration does error-code/keyword matching (architecture §6.3), second does functional-pattern/worked-example retrieval (§6.4).
3. **Seeds first**: since v0.2.0 the entry points (run_agent.py / tui/app.py) load `seed_entries()` by default; P2-12 (HLS domain owner) extends the corpus to >=10 entries on top.
