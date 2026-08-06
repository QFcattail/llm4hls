> [English](README.md)

# 详细设计 (Detailed Design)

> 本目录存放 agent 的详细设计文档。**设计文档描述"应该怎么实现"，与代码实现可能存在差异--以代码为准**。

## 文档清单

| 文档 | 内容 | 对应代码 | 状态 |
|---|---|---|---|
| `agent-architecture.md` | agent 整体架构：控制循环（线性带回溯）、存档逻辑、可观测性、路由 | `agent/` 全部 | 🟢 已完成 v2.2 |
| `agent-code-design.md` | 代码跨模块设计/数据流 | `agent/` 全部 | 🟢 已完成 |
| `tui-design.md` | TUI 仪表盘设计：四区域布局、线程模型、事件桥接 | `tui/` | 🟢 已完成 |
| `knowledge-base-schema.md` | bug->修法知识库条目 schema | `agent/knowledge-base/` | ⚪ 待编写（草案见备赛学习手册附录 B） |
| `eval-interface.md` | 评估接口契约（已被官方 harness 解决） | `contest/fpt26-harness/` | ✅ 不需要（harness ToolServer 即真接口） |

## 设计文档规范

- 设计文档**不包含代码**，用文字描述行为、状态、字段、流程。
- 详细到"细到不能再细"，让接手的人能照着重现。
- 关键术语中英对照，方便查阅英文资料。
- 每份设计文档都配有对应代码目录的 `README.md`（更新更频繁，含已知坑点）。
- 设计文档描述"应该怎么实现"，与代码实现可能存在差异--**以代码为准**，差异在此 README 或对应文档中列出。

## 阅读顺序

1. 先读 `agent-architecture.md` --理解 agent 的三阶段控制循环（correctness -> synth -> optimize）和存档逻辑。
2. 读 `agent-code-design.md` --理解跨模块数据流和函数调用关系。
3. 读 `tui-design.md` --理解 TUI 仪表盘的四区域布局和线程桥接模型。
4. 对照代码目录的 README 和 `.doc.md` 看实现细节。

## 评审

设计评审见 [`../reviews/`](../reviews/)。设计评审通过后方可进入 P3 测试用例编写。
