# FPGA Agent — FPT'26 Track A LLM4HLS 备赛工程

> Budgeted End-to-End LLM4HLS Agent：在有限的工具调用预算内，自动修复并优化 AMD Vitis HLS 的 C/C++ 代码（先修正确性，再优化 PPA）。

**当前状态**：P2 里程碑达成 — projection 题端到端真修复跑通（DeepSeek + 真 Vitis），SCORE 1.400。

---

## 快速开始

**3 分钟跑通**（不需要 Vitis、不需要 API key）：

```bash
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix
```

完整安装、CLI 用法、输出解读 → [getting-started.md](getting-started.md)

---

## 目录结构

```
agent/               Agent 本体代码（Python）
  README.md            ← 读代码从这里开始（模块职责/调用关系/阅读顺序）
  main_loop.py         主循环：correctness → synth → optimize
  router.py            路由器：task.toml → 关卡路径
  checkpoint.py        存档逻辑：三规则（等级更高→存/同级比latency/更低→拒）
  feedback.py          反馈构建：ToolResult → LLM 友好文本
  llm_client.py        LLM 调用：repair/review/propose_strategies
  mechanical_checks.py 硬性检查：签名/include（不依赖 LLM）
  deepseek_client.py   DeepSeek V4 Pro API 对接
  observability.py     JSONL 日志 + 心跳（卡死检测）
  knowledge_base/      RAG 知识库（bug→修法检索）

contest/
  fpt26-harness/      官方评估 harness（复用，不改）
    llm4hls/             ToolServer/Budget/Task/scoring/CSimTool/SynthTool/CoSimTool
    tasks/               3 道公开题（projection_bugfix/dotProduct_optimize/residual_stream_deadlock）
    vitis.dockerfile     官方 Docker 环境

scripts/
  run_agent.py         CLI 入口（driver）

docs-development/     工程过程文档中心
  engineering-plan/    ← 项目进度唯一真相来源（里程碑+原子任务）
  design/              架构设计 + 代码详细设计
  dev-log/             开发日志（每次会话一篇）
  runtime-constraints.md 运行约束（赛题规则/环境/预算/评分）
  notes/              背景知识笔记（论文/工具文档）
  internal-notes/      探索性笔记
  requirements/        需求分析
  test-plan/           测试策略
  reviews/             评审记录

tools/                辅助脚本（web_fetch 等）
.env                  API key（已 gitignore，不入库）
```

---

## 文档导航

| 想知道什么 | 看哪里 |
|---|---|
| **怎么装、怎么跑** | [getting-started.md](getting-started.md) |
| **现在做到哪一步** | [engineering-plan.md](docs-development/engineering-plan/engineering-plan.md) |
| **agent 架构怎么设计的** | [agent-architecture.md](docs-development/design/agent-architecture.md) |
| **代码怎么读** | [agent/README.md](agent/README.md) |
| **赛题规则/预算/评分公式** | [runtime-constraints.md](docs-development/runtime-constraints.md) |
| **代码跨模块设计/数据流** | [agent-code-design.md](docs-development/design/agent-code-design.md) |
| **上次做到哪** | [dev-log/](docs-development/dev-log/) 最新一篇 |

---

## 分工

| 角色 | 背景 | 负责 |
|---|---|---|
| **Agent 主** | 机器人 / 大模型 Agent 落地经验 | `agent/`、`scripts/`、评估接口对接 |
| **HLS 域主** | 信息工程 / 射频芯片 | `agent/knowledge-base/`、本地题集、correctness/PPA 验证 |

---

## 技术栈

- **语言**：Python 3.11+（只用标准库，无第三方依赖）
- **LLM**：DeepSeek V4 Pro（推理模型，OpenAI 兼容 API）
- **EDA**：AMD Vitis 2025.2（`vitis-run --mode hls`）
- **目标硬件**：Alveo U55C `xcu55c-fsvh2892-2L-e` @ 200 MHz
- **Git**：`git@gitee.com:QFcattail/fpga-agent.git`
