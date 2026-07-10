# FPGA Agent — 2026 FPGA 竞赛创新赛道 AMD Track A 备赛工程

> Budgeted End-to-End LLM4HLS Agent：在有限的工具调用预算内，自动修复并优化 AMD Vitis HLS 的 C/C++ 代码（先修正确性，再优化 PPA）。

本仓库是参赛工程的统一工作区，包含：agent 本体代码、HLS 领域知识库、竞赛交付物、以及完整的工程过程文档（需求/设计/工程计划/开发日志）。

## 目录结构 (Directory Structure)

| 目录 | 职责 | 谁负责 |
|---|---|---|
| [`agent/`](agent/) | Agent 本体代码（Python）：控制循环、日志解析、prompt、预算调度、知识注入 | Agent 主 |
| [`agent/knowledge-base/`](agent/knowledge-base/) | HLS “bug→修法”知识库（按 schema 检索注入） | HLS 域主 |
| [`contest/`](contest/) | 竞赛交付物：技术报告、演示脚本、图示 | 双方 |
| [`tools/`](tools/) | 辅助脚本：日志解析器、评估接口 mock、本地题集生成器 | Agent 主 |
| [`docs-development/`](docs-development/) | 工程过程文档中心（见该目录 README） | 双方 |
| `tmp/` | 本地调试产物（已 gitignore，不入库） | — |

## 文档中心 (Documentation Hub)

所有“现在做到哪一步、为什么这么设计、接下来做什么”的信息都在 [`docs-development/`](docs-development/)：

- [`engineering-plan/engineering-plan.md`](docs-development/engineering-plan/engineering-plan.md) — **项目进度唯一真相来源**（里程碑 + 原子任务清单）
- [`dev-log/`](docs-development/dev-log/) — 每次开发会话的日志（`YYYY-MM-DD-NN.md`）
- [`design/`](docs-development/design/) — 详细设计（agent 架构、知识库 schema）
- [`requirements/`](docs-development/requirements/) — 需求分析（赛道要求拆解）
- [`test-plan/`](docs-development/test-plan/) — 测试用例与策略
- [`reviews/`](docs-development/reviews/) — 需求/设计评审记录
- [`internal-notes/`](docs-development/internal-notes/) — 探索性笔记、踩坑记录

## 快速开始 (Quick Start)

1. 看一遍 [`docs-development/engineering-plan/engineering-plan.md`](docs-development/engineering-plan/engineering-plan.md)，了解当前阶段与原子任务。
2. 看最近一篇 [`dev-log/`](docs-development/dev-log/) 日志，了解上次做到哪、卡在哪。
3. 按工程计划认领一个原子任务，开发前先在 `dev-log/` 起一篇当日日志。

## 分工 (Team)

- **Agent 主**（机器人 / 大模型 Agent 落地经验）：负责 `agent/`、`tools/`、评测接口对接。
- **HLS 域主**（信息工程 / 射频芯片 / 时间充裕）：负责 `agent/knowledge-base/`、本地题集、correctness/PPA 验证。

详见工程计划文档与备赛学习手册。
