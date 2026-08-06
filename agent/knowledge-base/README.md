# 知识库 spec (Knowledge Base Spec)

HLS “bug->修法”知识库的**规格文档**目录。HLS 域主维护条目内容，Agent 主的检索器消费。

> **注意**：本目录（`knowledge-base/`，连字符）只有 spec 文档，无 Python 代码。实际的检索器实现在 `agent/knowledge_base/`（下划线，Python 包），包含 `retriever.py`（`KnowledgeBase` 类 + `KBEntry` dataclass）。
>
> 命名差异源于：文档目录用连字符（kebab-case），Python 包用下划线（合法标识符）。两者都活跃，不要删任何一个。

## 条目 schema

每个条目是一个结构化对象，字段见 `docs-development/design/knowledge-base-schema.md`（待写），核心字段：

| 字段 | 说明 |
|---|---|
| id | KB-NNN |
| 症状关键词 | 用于检索匹配的词 |
| 错误签名 | 正则/grep 模式，匹配日志 |
| 根因 | 为什么出这个错 |
| 修法策略 | 怎么修 |
| 代码示例 | pragma / 代码片段 |
| 涉及pragma | pipeline/unroll/array_partition/dataflow/stream 等 |
| PPA影响 | 修复对 PPA 的影响 |
| 阶段 | correctness / ppa |

## 状态
- 待 P2 阶段 HLS 域主整理首批 ≥10 条（编译错 + csim 功能 bug）。
- 草案 schema 见备赛学习手册附录 B。
