# Agent 本体 (Agent)

Budgeted End-to-End LLM4HLS Agent 的 Python 实现。

## 计划结构
- `src/` — 源码：控制循环（ReAct）、日志解析器、预算调度器、LLM 客户端、评估接口对接。
- `knowledge-base/` — HLS bug→修法知识库（HLS 域主维护）。

## 状态
- 待 P2 阶段开始实现最小闭环。设计见 `docs-development/design/agent-architecture.md`（待写）。

## 运行
待实现后补充：`python -m agent.src.main <task_dir>` 之类。
