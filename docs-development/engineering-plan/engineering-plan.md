# 工程计划 (Engineering Plan)

> 本文档是项目进度的**唯一真相来源（Single Source of Truth）**。任何人想知道"现在做到哪一步了、接下来做什么"，只需要看这一份文档。
>
> 更新规则：每完成一个原子任务，立刻把对应行的状态改掉，并在"变更记录"里追加一行。不要等到一天结束才批量更新。
>
> 每进入一个阶段先细化原子任务，原子任务一定要细，不要一个任务需要一周的量。

最后更新时间 (Last Updated)：2026-07-14（官方 harness 解压是决定性发现，P2/P3 大量任务（mock/日志解析/接真接口/预算止损）被官方实现解决。P1 Agent 主侧实质完成，P2 重写为"搭骨架 + 最小闭环"。架构定稿见 agent-architecture.md v2.2。）

---

## 1. 参赛概况 (Competition Overview)

**竞赛**：FPT'26 Design Competition — Track A: LLM4HLS Agent

**核心任务**：开发一个自主 AI Agent，在有限的工具调用预算内，自动生成/调试/优化 AMD Vitis HLS C/C++ 代码。先保障功能正确性（correctness），再优化 PPA。

**已确认规则**（来源：Submission_Guidelines_Track-A.docx + 选题要求.md + AMD 案例文章）：
- FPGA 平台：Alveo U55C（co-simulation 用）
- 软件版本：Vitis 2025.2
- 必须通过 csim、cosim、synth，并提供实验报告
- HLS 生成硬件频率至少 100MHz
- **Token 消耗是终评重要指标**
- 推荐模型（三选一或多个对比）：
  - DeepSeek V4 Pro（deepseek-ai/DeepSeek-V4-Pro，MoE 1.6T/49B active，100万上下文，FP8）
  - Qwen3.5 122B A10B（cyankiwi/Qwen3.5-122B-A10B-AWQ-4bit，MoE 122B/10B active，262K上下文）
  - Qwen3.6 27B（Qwen/Qwen3.6-27B-FP8，Dense 27B，262K上下文）
- 鼓励额外评测其他开源模型，写入技术报告
- 存在隐藏测试集用于终评
- Docker 环境提交（参考：https://anonymous.4open.science/r/fpt26-harness）
- 提交物：源码 + testbench + 补充材料（.zip）+ 演示视频（≤5分钟）
- **赛道明确要求 correctness 优先于 PPA**

---

## 2. 里程碑总览 (Milestone Overview)

| 阶段 | 名称 | 时间 | 状态 | 核心目标 |
|---|---|---|---|---|
| P0 | 项目基础设施搭建 | 第 0 周 | 🟢 已完成 | 仓库、目录结构、文档中心、分工与计划基线 |
| P1 | 认知 + 环境 | 第 1 周 | 🟢 实质完成（Agent 主侧） | 读背景资料、解压 harness、跑通离线链路、架构定稿。HLS 域主侧（数电基础+Vitis 环境）进行中 |
| P2 | 搭骨架 + 最小正确性闭环 | 第 2 周 | 🟡 进行中 | 按 agent-architecture.md 搭 agent/ 模块，在 ScriptedClient 上跑通 projection 题闭环 |
| P3 | 接真 Vitis + cosim + 里程碑 | 第 3-4 周 | ⚪ 未开始 | 云服务器跑真 csim/synth/cosim，扩 structural 路径，端到端跑 milestone |
| P4 | PPA 优化冲分 + 提交物 | 第 5 周起 | ⚪ 未开始 | optimize 阶段 + token 优化（第二次迭代）+ Docker/报告/视频 |

状态图例：⚪ 未开始 🟡 进行中 🟢 已完成 🔴 阻塞

## 里程碑 DoD（Definition of Done）

**P3 结束时必须达成：**
- Agent 在 5-10 道覆盖"编译错 / 功能 bug / cosim 协议错"的题上跑完整流程
- ≥60% 题目 correctness 全绿（编译 + csim + cosim 全过）
- Agent 有预算计数与止损：超限优雅终止并交当前最佳代码
- 至少 1 次，知识库条目被检索命中并实际生效
- 有可复现脚本 + 一段演示（录屏或日志）

## 两人并行汇合点 (Convergence Points)

| 汇合点 | 时间 | Agent 主交付 | HLS 域主交付 | 对齐动作 |
|---|---|---|---|---|
| 1 | 第一周末 | API 通路 | 日志样例包 | Agent 主据此设计日志解析器 |
| 2 | 第三周末 | 知识库注入接口 + 评测脚本 | 知识库初版 + 3-5 道小题 | 跑首次本地评测，看 success rate |
| 3 | 第五周末 | 里程碑版 agent | 端到端测试题集 | 一起跑里程碑演示，达成 DoD |

---

## 3. 原子任务清单 (Atomic Task Backlog)

> 任务编号规则：`P<阶段号>-<序号>`。状态变更时同步更新本表，并在下方"变更记录"追加一行。

### P0：项目基础设施搭建

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P0-01 | 创建 Gitee 仓库 + SSH 专用密钥 | Agent 主 | 🟢 已完成 | 密钥 id_ed25519_gitee |
| P0-02 | 定义目录结构 | Agent 主 | 🟢 已完成 | docs-development 模式 |
| P0-03 | 写工程计划 + dev-log 规范 | Agent 主 | 🟢 已完成 | |
| P0-04 | 写顶层 README + .gitignore | Agent 主 | 🟢 已完成 | |
| P0-05 | 首篇开发日志 | Agent 主 | 🟢 已完成 | 2026-07-10-01 |
| P0-06 | 赛题原文入库 | Agent 主 | 🟢 已完成 | contest/ 目录 |
| P0-07 | 备赛手册入库 | Agent 主 | 🟢 已完成 | internal-notes/ |
| P0-08 | 工程计划细化 | Agent 主 | 🟢 已完成 | |

---

### P1：认知 + 环境（第 1 周）

#### Agent 主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P1-01 | 通读赛题规则 + AMD 案例文章，建立全景 | 🟢 | 已通读全部规则，能讲清四阶段工作流 |
| P1-02 | 读 ReAct 论文 + Anthropic《Building effective agents》 | 🟢 | 已读完，理解 Thought→Action→Observation 循环和 5 种 agent 模式 |
| P1-03 | 读 SWE-agent 仓库 README + 论文 | 🟢 | 已读完，理解 ACI 设计原则 |
| P1-04 | 装 LLM API 通路（待用户给 key） | 🟡 | 环境侧完成（OpenRouterClient 已可跑），API key 待用户提供 |
| P1-05 | 读 HLS Repair 论文（arXiv 2407.03889） | 🟢 | 已读完，理解 bug 模式分类与 LLM 定向修复方法 |
| P1-06 | 读 AutoChip / RTLFixer / HLSPilot 论文 | 🟢 | 已读完摘要，理解工具反馈迭代模式 |
| P1-07 | 向队友要"Vitis HLS 日志样例包" | 🟢 | **harness 自带 3 道题（projection/dotProduct/residual），含 reference 答案，远超预期，不再需要队友单独造** |
| P1-08a | 解压官方 harness，全量分析 | 🟢 | 11 个 py 文件 + 3 道 task 逐文件读完，接口/预算/评分/Docker 全部明确（见 runtime-constraints.md §二） |
| P1-08b | 跑通 harness 离线链路（ScriptedClient） | 🟢 | `run_poc.py` 在本机 python3.13 跑通，task 加载/budget/transcript/评分卡全正常 |
| P1-08c | agent 架构定稿 | 🟢 | `docs-development/design/agent-architecture.md` v2.2（Mermaid 流程图 + 存档逻辑 + 可观测性） |
| P1-08d | 确定开发环境与部署方案 | 🟡 | 开发期用 ScriptedClient 离线（已完成）；Vitis 待云服务器（用户将给 SSH） |

#### HLS 域主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P1-09 | 刷新数电基础：组合/时序逻辑、触发器、FSM、时序、流水线 | ⚪ | 能讲清"流水线为什么提高吞吐、寄存器干啥" |
| P1-10 | 读 Kastner《Parallel Programming for FPGAs》前几章 + UG1399 的 csim/csynth/cosim 章节 | ⚪ | 能讲清 csim/synth/cosim 各验什么、报告里 II/latency/资源在哪 |
| P1-11 | 租云服务器 + 装 Vitis 2025.2（Ubuntu 22.04） | ⚪ | 能在服务器上跑通 harness 的 csim+synth（**用户给 SSH 后配置**） |
| P1-12 | 读 AMD LLM4HLS SHA-256 案例文章 | 🟢 | 用户已代读完（dev-log 2026-07-11-03），四阶段工作流已写入 |

> **P1 收尾说明**（2026-07-14）：harness 解压是决定性发现，把原 P1-07（日志样例包）、P1-12（AMD 文章）的状态全部改写。Agent 主侧 P1 实质完成，进入 P2。HLS 域主侧 P1-09/10/11 仍待推进（数电基础 + Vitis 环境）。

---

### P2：搭骨架 + 最小正确性闭环（第 2 周）

> **重写说明**（2026-07-14）：原 P2-01（mock）、P2-02（日志解析）、P2-05（评测脚本）被官方 harness 解决（ToolServer + report.py + scoring.py + run_poc.py）。P2 重心改为：**按 agent-architecture.md 搭 agent 骨架，在 ScriptedClient 上跑通最小闭环**。

#### Agent 主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P2-01 | ~~定义评估接口 mock~~ | ✅ | **官方 ToolServer 即真接口，不需要 mock。已废弃。** |
| P2-02 | ~~实现日志解析器~~ | ✅ | **官方 report.py 已实现（csynth.xml + cosim.rpt 解析）。已废弃。** |
| P2-03 | 搭 agent/ 目录骨架 + 模块 | ⚪ | router.py / checkpoint.py / main_loop.py / feedback.py / llm_client.py / knowledge_base/ 全部建出，能 import |
| P2-04 | 实现 router.py：task.toml → RunPlan | ⚪ | 对 3 道 task_type 各异的题产出正确 RunPlan |
| P2-05 | 实现 checkpoint.py：关卡等级 + 存档判定三条规则 | ⚪ | 单元测试覆盖 level 比较 + 三规则 |
| P2-06 | 实现 main_loop.py 主循环（correctness 阶段，先不接 LLM） | ⚪ | 在 ScriptedClient 上跑通 projection 题：router → csim 修复循环 → 存档 → 交卷 |
| P2-07 | 实现 feedback.py：从 ToolResult 构建 LLM 友好反馈 | ⚪ | 对 3 类失败（compile_error/runtime_fail/cosim_fail）抽出错误签名 |
| P2-08 | 接 LLM（先 ScriptedClient，再真 OpenRouter） | ⚪ | ScriptedClient 跑通全流程；有 API key 后切真模型 |
| P2-09 | 接知识库（哪怕先 3 条）+ 错误签名匹配检索 | ⚪ | 对已知错误码（如 cosim deadlock）能命中条目并注入 prompt |
| P2-10 | 可观测性：结构化日志 + transcript + 心跳 | ⚪ | agent-architecture.md §12 的 12 个日志点 + 心跳落地 |
| P2-11 | 交叉验证（第一次迭代）：关键决策点 self-check/agent review | ⚪ | correctness 修复 + optimize 策略选定两处接入 review |

#### HLS 域主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P2-12 | 按 schema 整理知识库条目（先覆盖编译错+csim 功能 bug+cosim 死锁） | ⚪ | ≥10 条，每条含 error_code/symptom/root_cause/fix/example。**数据源：harness 3 道题的真实日志 + AMD 案例** |
| P2-13 | 读 AutoChip / RTLFixer / HLS Repair 三篇，提炼修法模式 | ⚪ | ≥5 条修法模式补充进知识库 |

---

### P3：接真 Vitis + cosim + 里程碑（第 3-4 周）

> **重写说明**（2026-07-14）：原 P3-01/02（接真接口）、P3-04（预算止损）被 harness 解决（接口已是进程内函数 + Budget 类）。P3 重心改为：**接到真 Vitis 环境，扩 cosim 协议错处理，端到端跑 milestone**。

#### Agent 主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P3-01 | ~~把 mock 替换为真评估接口~~ | ✅ | **官方 ToolServer 自始即是真接口，无需替换。已废弃。** |
| P3-02 | ~~本地接 Vitis HLS 命令行~~ | ✅ | **官方 vitis.py 已封装（vitis-run --mode hls）。已废弃。** |
| P3-03 | 在云服务器（SSH）上跑通真 csim/synth/cosim | ⚪ | harness run_poc.py 在服务器上对 3 道题跑出真结果（非 compile_error 占位） |
| P3-04 | ~~加预算计数与止损~~ | ✅ | **官方 Budget + BudgetExceeded 已实现。已废弃。** |
| P3-05 | 扩 main_loop 的 structural 路径：csim+cosim 双验证 + 优化后回验 | ⚪ | 在 residual 题上自动修到 csim+cosim 全过（真 cosim，非 Scripted） |
| P3-06 | 端到端测试：3 道公开题跑完整流程 + 评分 | ⚪ | 输出每题 scorecard，≥60% correctness 全绿 |
| P3-07 | 里程碑演示：录一段 agent 自动修 HLS 的日志/录屏 | ⚪ | 可复现脚本 + 演示 |

#### HLS 域主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P3-08 | 扩知识库到 cosim 协议类：dataflow 死锁、AXI-Stream 握手(TLAST/TREADY/TVALID)、ap_ctrl | ⚪ | ≥5 条 cosim 类条目 |
| P3-09 | 整理 PPA 优化杠杆清单（pipeline/unroll/array_partition/dataflow/bind_op） | ⚪ | 1 份"PPA 优化速查"，供 P4 用 |
| P3-10 | 配合端到端测试 + 里程碑汇合 | ⚪ | 知识库条目至少被命中并生效 1 次 |

---

### P4：PPA 优化冲分 + 提交物（第 5 周起）

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P4-01 | 实现 optimize 阶段：注入综合报告 + Strategy Exploration + 存档择优 | Agent 主 | ⚪ | 对应 agent-architecture.md §4.4 |
| P4-02 | pragma 变换优化 PPA（pipeline/unroll/partition/dataflow） | Agent 主 | ⚪ | 参考 AMD 案例文章的四阶段工作流 |
| P4-03 | 第二次迭代：token 优化（第一次迭代暂不考虑） | Agent 主 | ⚪ | 第一次迭代跑稳后，分析日志压 token |
| P4-04 | 第二次迭代：功能 pattern 检索（agent-architecture.md §6.4） | Agent 主 | ⚪ | 难度较高，先靠错误签名匹配 |
| P4-05 | Docker 镜像打包 | Agent 主 | ⚪ | 复用官方 vitis.dockerfile |
| P4-06 | 技术报告撰写 | 双方 | ⚪ | 含模型对比实验 |
| P4-07 | 演示视频录制（≤5分钟） | 双方 | ⚪ | 在目标平台运行 + 清晰讲解 |

---

## 4. 变更记录 (Change Log)

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-14 | **P2/P3 大重写**：harness 解压是决定性发现。废弃 P2-01（mock）/P2-02（日志解析）/P3-01（接真接口）/P3-02（Vitis 命令行）/P3-04（预算止损）—— 全被官方实现解决。P2 重写为"搭 agent 骨架 + 最小闭环"（P2-03~P2-11），P3 重写为"接真 Vitis + cosim + milestone"（P3-03~P3-07）。新增 P1-08a~d（harness 分析/离线跑通/架构定稿/部署方案）标记完成。架构定稿见 agent-architecture.md v2.2。里程碑总览时间表压缩（P2→第2周、P3→第3-4周、P4→第5周起），因 harness 省去大量基础工作。 | Agent 主 |
| 2026-07-11 | P1-02/03/05/06 全部完成：用户读完所有背景论文（ReAct、Anthropic agents、SWE-agent、HLS Repair、AutoChip、RTLFixer、HLSPilot、AMD案例）。AMD四阶段工作流与LLM优缺点已写入 dev-log 2026-07-11-03。用户确认已报名，只做Track A。明天开始规划agent架构。 | Agent 主 |
| 2026-07-11 | **工程计划收回聚焦 Track A**：用户明确只做 FPT'26 Track A LLM4HLS。删除 FPL'26/Track B 相关内容，恢复 P0-P4 五阶段结构。补充 AMD 案例文章的四阶段工作流作为方法论参考。 | Agent 主 |
| 2026-07-11 | 工程计划据实重写（涉及两个竞赛三条赛道），现已因用户决策收回。赛题规则已全部回填至 runtime-constraints.md。 | Agent 主 |
| 2026-07-11 | P1-01 完成（手册全文通读）；P1-04 环境侧完成（web_fetch.py + Playwright MCP + 双 python）；tech-debt 全量废弃 | Agent 主 |
| 2026-07-11 | 补充手册路线图、汇合点表、P1/P2/P3 按人细化检查清单、P0-06~P0-08 完成 | Agent 主 |
| 2026-07-10 | 初始工程计划建立；P0 全部完成；P1 开始 | Agent 主 |