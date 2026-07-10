# 工程计划 (Engineering Plan)

> 本文档是项目进度的**唯一真相来源（Single Source of Truth）**。任何人想知道“现在做到哪一步了、接下来做什么”，只需要看这一份文档。
>
> 更新规则：每完成一个原子任务，立刻把对应行的状态改掉，并在“变更记录”里追加一行。不要等到一天结束才批量更新。
>
> 每进入一个阶段先细化原子任务，原子任务一定要细，不要一个任务需要一周的量。

最后更新时间 (Last Updated)：2026-07-10（P0 仓库与文档骨架搭建）

## 1. 里程碑总览 (Milestone Overview)

| 阶段 | 名称 (Phase) | 状态 | 说明 |
|---|---|---|---|
| P0 | 项目基础设施搭建 (Infra Scaffold) | 🟢 已完成 | 仓库、目录结构、文档中心、SSH/密钥、分工与计划基线 |
| P1 | 认知 + 环境 (Cognition & Environment) | 🟡 进行中 | 两人各自补底子；装好 Vitis HLS / API 通路；产出日志样例包 |
| P2 | 最小正确性 Agent (Minimal Correctness Agent) | ⚪ 未开始 | mock 闭环：读代码→调 csim→解析→出 patch→再跑，攻编译错+csim bug |
| P3 | 接真接口 + cosim + 里程碑 (Real Interface & First Run) | ⚪ 未开始 | 接真评估接口/本地 Vitis HLS，扩 cosim 协议错，加预算止损；达成 DoD |
| P4 | PPA 优化冲分 (PPA Optimization) | ⚪ 未开始 | 读综合报告优化 PPA，冲隐藏题集分数 |

状态图例：⚪ 未开始　🟡 进行中　🟢 已完成　🔴 阻塞

> 里程碑定义（DoD）：见 `design/` 下的设计文档与备赛学习手册第五章。简言之——给一道坏 HLS，agent 在预算内自动修到 csim+cosim 全绿，≥60% 题过，有可复现脚本与演示。

## 2. 当前阶段详情 (Current Phase Detail)

**当前所处阶段：P1 认知 + 环境**

P0 已完成：仓库与文档骨架搭建（目录结构参考 webusb 工程的 `docs-development` 模式）、SSH 专用密钥已生成并配置、工程计划与 dev-log 规范就位、首篇日志已写。

P1 进行中：两人并行补底子。Agent 主读 ReAct/SWE-agent/Anthropic agents + 通 API；HLS 域主读 Kastner/UG1399 + 装好 Vitis HLS + 跑通官方 example。第一周末汇合点：HLS 域主交“日志样例包”。

## 3. 原子任务清单 (Atomic Task Backlog)

> 任务编号规则：`P<阶段号>-<序号>`。状态变更时同步更新本表，并在下方“变更记录”追加一行。

### P0：项目基础设施搭建

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P0-01 | 创建 Gitee 仓库 + SSH 专用密钥 | Agent 主 | 🟢 已完成 | 密钥 id_ed25519_gitee |
| P0-02 | 定义目录结构（参考 webusb） | Agent 主 | 🟢 已完成 | docs-development 模式 |
| P0-03 | 写工程计划 + dev-log 规范 | Agent 主 | 🟢 已完成 | 本文档 + dev-log/README |
| P0-04 | 写顶层 README + .gitignore | Agent 主 | 🟢 已完成 | 含 Vitis HLS 忽略项 |
| P0-05 | 首篇开发日志 | Agent 主 | 🟢 已完成 | 2026-07-10-01 |

### P1：认知 + 环境

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P1-01 | 通读手册 1/6/7 章，建立全景 | Agent 主 | ⚪ 未开始 | |
| P1-02 | 读 ReAct + Anthropic Building effective agents | Agent 主 | ⚪ 未开始 | |
| P1-03 | 读 SWE-agent 仓库 + 论文 | Agent 主 | ⚪ 未开始 | 列 3 条可迁移设计 |
| P1-04 | 装开发环境 + 选定商用 LLM API | Agent 主 | ⚪ 未开始 | 跑通调 API 拿 JSON |
| P1-05 | 刷新数电基础 | HLS 域主 | ⚪ 未开始 | 组合/时序/FSM/流水线 |
| P1-06 | 读 Kastner 前几章 + UG1399 报告章节 | HLS 域主 | ⚪ 未开始 | 讲清 csim/synth/cosim |
| P1-07 | 装好 Vitis HLS，跑通官方 example | HLS 域主 | ⚪ 未开始 | csim+csynth+cosim |
| P1-08 | 产出“日志样例包”（编译错/csim 失败/cosim 失败各 1 份） | HLS 域主 | ⚪ 未开始 | **汇合点 1：第一周末交 Agent 主** |

### P2：最小正确性 Agent

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P2-01 | 定义评估接口 mock | Agent 主 | ⚪ 未开始 | 模拟 csim/cosim/synth |
| P2-02 | 实现日志解析器 | Agent 主 | ⚪ 未开始 | 抽错误类别+字段 |
| P2-03 | 实现 ReAct 主循环 | Agent 主 | ⚪ 未开始 | 简单题修到 csim 过 |
| P2-04 | 接入知识库注入（先 3 条） | Agent 主 | ⚪ 未开始 | 检索注入 prompt |
| P2-05 | 写本地评测脚本 | Agent 主 | ⚪ 未开始 | 跑 success rate |
| P2-06 | 整理常见 HLS 失败模式 + 修法（≥10 条） | HLS 域主 | ⚪ 未开始 | 按 schema 入库 |
| P2-07 | 造 3-5 道本地小题 | HLS 域主 | ⚪ 未开始 | 坏代码+预期修法+答案 |
| P2-08 | 验证 agent 改出的代码对不对 | HLS 域主 | ⚪ 未开始 | 跑 csim/cosim 核对 |
| P2-09 | 读 AutoChip/RTLFixer/Automated Repair for HLS | HLS 域主 | ⚪ 未开始 | 提炼 5 条修法模式 |

### P3：接真接口 + cosim + 里程碑

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P3-01 | mock 替换为真评估接口 | Agent 主 | ⚪ 未开始 | 规则一发布立刻接 |
| P3-02 | 或本地接 Vitis HLS 命令行 | Agent 主 | ⚪ 未开始 | vitis_hls -f run.tcl |
| P3-03 | 扩到 cosim 协议类错误 | Agent 主 | ⚪ 未开始 | dataflow 死锁/AXI-Stream |
| P3-04 | 加预算计数与止损 | Agent 主 | ⚪ 未开始 | 超限优雅终止 |
| P3-05 | 端到端测试 5-10 题 | 双方 | ⚪ 未开始 | ≥60% correctness 全绿 |
| P3-06 | 扩知识库到 cosim 类（≥5 条） | HLS 域主 | ⚪ 未开始 | |
| P3-07 | 整理 PPA 优化杠杆清单 | HLS 域主 | ⚪ 未开始 | 阶段 4 用，先备着 |
| P3-08 | 里程碑演示 + 可复现脚本 | 双方 | ⚪ 未开始 | **汇合点 3：里程碑** |

### P4：PPA 优化冲分（后续）

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P4-01 | 读综合报告定位瓶颈 | Agent 主 | ⚪ 未开始 | latency/II/资源 |
| P4-02 | pragma 变换优化 PPA | Agent 主 | ⚪ 未开始 | pipeline/unroll/partition |
| P4-03 | 预算内取舍策略 | Agent 主 | ⚪ 未开始 | |

## 4. 变更记录 (Change Log)

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-10 | 初始工程计划建立；P0 全部完成；P1 开始 | Agent 主 |
