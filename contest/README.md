# 竞赛交付物 (Contest Deliverables)

本目录存放竞赛相关材料与提交物。涉及**两个独立竞赛**，注意区分。

## 目录结构

| 目录/文件 | 内容 | 竞赛 | 本项目是否使用 |
|---|---|---|---|
| `选题要求.md` | FPT'26 Track A 赛道描述与要求（agent 端到端流程） | FPT'26 Track A | ✅ 核心 |
| `Submission_Guidelines_Track-A.docx` | Track A 提交指南（10条规则） | FPT'26 Track A | ✅ 核心 |
| `Submission_Guidelines_Track-B.docx` | Track B 提交指南（3条规则） | FPT'26 Track B | ❌ 不做 |
| `FPT26_Competition_Page.html` | FPT'26 竞赛主页存档 | FPT'26 全局 | 参考 |
| `AMD_LLM_HLS_SHA256_Article.html` | AMD LLM4HLS 参考文章（四阶段工作流） | FPT'26 Track A | ✅ 方法论参考 |
| `Vitis_HLS_User_Guide.html` | Vitis HLS 用户指南 | FPT'26 Track A | 参考 |
| `fpt26-harness/` | **官方评估 harness**（ToolServer/Budget/Task/scoring） | FPT'26 Track A | ✅ **核心，只读复用** |
| `fpl26_reference/` | FPL'26 参考实现（RapidWright + DCP 优化） | FPL'26 | ❌ 仅参考 |
| `FPL26_Agentic_FPGA_Contest_README.md` | FPL'26 参考仓库 README | FPL'26 | 参考 |
| `FPL26_optimization_example.md` | FPL'26 优化示例文档 | FPL'26 | 参考 |
| `FPL26_runtime.md` | FPL'26 运行环境说明 | FPL'26 | 参考 |

## 两套赛事的关键区别

| | FPT'26 Track A（本项目） | FPL'26（仅供参考） |
|---|---|---|
| **方法** | HLS C/C++ -> RTL（Vitis HLS） | 已布线 DCP checkpoint -> RapidWright 时序优化 |
| **输入** | HLS kernel 源码（.cpp/.h） | placed-and-routed .dcp 文件 |
| **目标器件** | Alveo U55C | UltraScale+ xcvu3p |
| **Agent 任务** | 生成/修复/优化 HLS 代码 | 优化已布线设计的时序 |
| **评分** | `difficulty * (0.5*correct + 0.2*synth + 0.3*ppa)` | `alpha - 0.1*alpha*beta - 0.1*alpha*gamma` |

> **本项目聚焦 FPT'26 Track A**。`fpl26_reference/` 是早期探索 FPL'26 时入库的参考材料，与本项目主线无关，保留供参考。

## fpt26-harness/ 说明

官方 harness 是参考实现 + 评估工具，**全 Python 标准库**（requirements.txt 为空，无第三方依赖）。它一次性回答了评估接口/credit 预算/评分公式/Docker 规范等全部问题。

- `llm4hls/` 包：`config.py`/`vitis.py`/`tools.py`/`report.py`/`budget.py`/`task.py`/`harness.py`/`scoring.py`/`llm.py`/`agent.py`
- `tasks/`：3 道公开题（projection_bugfix / dotProduct_optimize / residual_stream_deadlock）
- `scripts/run_poc.py`：harness 自带 driver（被项目 `scripts/run_agent.py` 模仿）
- `vitis.dockerfile` / `run-vitis.sh`：Docker 环境规范

详见 harness 自带 `README.md` 和 `docs-development/runtime-constraints.md` §二。

## 状态
- 赛题规则已全部入库，详见 `docs-development/runtime-constraints.md`
- 提交物待里程碑达成后整理。当前优先跑通 FPT'26 Track A 的 3 道公开题。
