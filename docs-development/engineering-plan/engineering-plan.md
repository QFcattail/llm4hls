# 工程计划 (Engineering Plan)

> 本文档是项目进度的**唯一真相来源（Single Source of Truth）**。任何人想知道“现在做到哪一步了、接下来做什么”，只需要看这一份文档。
>
> 更新规则：每完成一个原子任务，立刻把对应行的状态改掉，并在“变更记录”里追加一行。不要等到一天结束才批量更新。
>
> 每进入一个阶段先细化原子任务，原子任务一定要细，不要一个任务需要一周的量。

最后更新时间 (Last Updated)：2026-07-11（补充手册路线图、汇合点、P1/P2/P3 检查清单细化）

---

## 1. 里程碑总览 (Milestone Overview)

| 阶段 | 名称 (Phase) | 时间 | 状态 | 核心目标 |
|---|---|---|---|---|
| P0 | 项目基础设施搭建 (Infra Scaffold) | 第 0 周 | 🟢 已完成 | 仓库、目录结构、文档中心、SSH/密钥、分工与计划基线 |
| P1 | 认知 + 环境 (Cognition & Environment) | 第 1 周 | 🟡 进行中 | 两人各自补底子；装好 Vitis HLS / API 通路；产出日志样例包 |
| P2 | 最小正确性 Agent (Minimal Correctness Agent) | 第 2-3 周 | ⚪ 未开始 | mock 闭环：读代码→调 csim→解析→出 patch→再跑，攻编译错+csim bug |
| P3 | 接真接口 + cosim + 里程碑 (Real Interface & First Run) | 第 4-5 周 | ⚪ 未开始 | 接真评估接口/本地 Vitis HLS，扩 cosim 协议错，加预算止损；达成 DoD |
| P4 | PPA 优化冲分 (PPA Optimization) | 第 6 周起 | ⚪ 未开始 | 读综合报告优化 PPA，冲隐藏题集分数 |

状态图例：⚪ 未开始　🟡 进行中　🟢 已完成　🔴 阻塞

## 里程碑 DoD（Definition of Done）

**P3 结束时必须达成：**
- Agent 在 5-10 道覆盖“编译错 / 功能 bug / cosim 协议错”的题上跑完整流程
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

## 2. 当前阶段详情 (Current Phase Detail)

**当前所处阶段：P1 认知 + 环境**

P0 已完成：仓库与文档骨架就位、SSH 已推送、赛题已入库、手册已归入 internal-notes、工程计划已细化。

P1 进行中：两人并行补底子。Agent 主读 ReAct/SWE-agent/Anthropic agents + 通 API；HLS 域主读 Kastner/UG1399 + 装好 Vitis HLS + 跑通官方 example。参见下方 P1 任务清单。

---

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
| P0-06 | 赛题原文入库 | Agent 主 | 🟢 已完成 | contest/选题要求.md |
| P0-07 | 备赛手册入库 | Agent 主 | 🟢 已完成 | internal-notes/备赛学习手册.docx |
| P0-08 | 工程计划细化（手册路线图+汇合点） | Agent 主 | 🟢 已完成 | 本次更新 |

---

### P1：认知 + 环境（第 1 周）

#### Agent 主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P1-01 | 通读备赛手册第一、六、七章，建立全景 | ⚪ | 能用一段话向队友讲清“赛道要干什么、agent 要做什么循环” |
| P1-02 | 读 ReAct 论文 + Anthropic《Building effective agents》 | ⚪ | 能画出 observe→think→act 循环，说清 workflow 与 agent 的区别 |
| P1-03 | 读 SWE-agent 仓库 README + 论文 | ⚪ | 列出 3 条可迁移到 HLS 的设计（预算化运行、工具反馈、失败模式分析） |
| P1-04 | 装好开发环境 + 选定商用 LLM API | ⚪ | 跑通一个最小“调 API → 拿结构化 JSON 输出”的脚本 |
| P1-05 | 向队友要到“Vitis HLS 日志样例包”（依赖 P1-12） | ⚪ | 拿到至少 1 份真实日志，能指出错误行/II/资源字段在哪 |

#### HLS 域主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P1-06 | 刷新数电基础：组合/时序逻辑、触发器、FSM、时序（建立/保持）、流水线 | ⚪ | 能讲清“流水线为什么提高吞吐、寄存器干啥” |
| P1-07 | 读 Kastner《Parallel Programming for FPGAs》前几章 + UG1399 的 csim/csynth/cosim 章节 | ⚪ | 能用一段话讲清 csim/synth/cosim 各验什么、报告里 II/latency/资源在哪 |
| P1-08 | 装好 Vitis HLS（或用学校/云端） | ⚪ | 本地跑通 1 个官方 example 的 csim+csynth+cosim |
| P1-09 | 产出“日志样例包”给 Agent 主：编译错/csim 失败/cosim 失败/synth 成功各 1 份 | ⚪ | **汇合点 1 交付物** |

---

### P2：最小正确性 Agent（第 2-3 周）

#### Agent 主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P2-01 | 定义评估接口 mock：模拟 csim/cosim/synth 的输入输出 | ⚪ | mock 能据传入代码返回“编译错/csim 过/cosim 失败”等预设结果，agent 能调它 |
| P2-02 | 实现日志解析器：从（mock 的）日志抽出错误类型与关键字段 | ⚪ | 对 3 类典型日志能正确抽出错误类别 |
| P2-03 | 实现 ReAct 主循环：读代码→调 mock→解析→LLM 出 patch→应用→再调 | ⚪ | 在一道简单编译错题上自动修到 csim 通过 |
| P2-04 | 接入队友的 bug→修法知识库（哪怕先 3 条）：按症状检索注入 prompt | ⚪ | 知识库条目能被检索并出现在 LLM 上下文里 |
| P2-05 | 写本地评测脚本：在队友造的 3-5 道小题上跑 success rate | ⚪ | 输出每题“通过/未通过/用了几次工具调用” |

#### HLS 域主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P2-06 | 按 schema 整理常见 HLS 失败模式与修法（先覆盖编译错+csim 功能 bug） | ⚪ | ≥10 条条目，每条含症状/错误签名/根因/修法/示例 |
| P2-07 | 造 3-5 道本地小题：拿官方 example 故意改坏（删 pragma、引入 bug、制造死锁） | ⚪ | 每题有“坏代码+预期修法+已知正确答案” |
| P2-08 | 验证 Agent 改出来的代码确实对：跑 csim/cosim 核对 | ⚪ | 能判定 agent 的提交是否 correctness 通过 |
| P2-09 | 读 AutoChip / RTLFixer / Automated C/C++ Repair for HLS 三篇 | ⚪ | 从中提炼 5 条“修法模式”补充进知识库 |

---

### P3：接真接口 + cosim + 里程碑（第 4-5 周）

#### Agent 主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P3-01 | 把 mock 替换为比赛真评估接口（规则一发布立刻接） | ⚪ | agent 能调真 csim/cosim/synth 拿真反馈 |
| P3-02 | 或本地接 Vitis HLS 命令行（vitis_hls -f run.tcl）跑通真 csim/synth | ⚪ | 本地能跑通 1 个真例子的 csim+synth，解析真报告 |
| P3-03 | 扩到 cosim 协议类错误：dataflow 死锁 / AXI-Stream 握手错 | ⚪ | 在一道 cosim 失败题上自动修到 cosim 通过 |
| P3-04 | 加预算计数与止损：记录已用 csim/cosim/synth 次数，超限即停 | ⚪ | agent 在预算耗尽时优雅终止并交当前最佳代码 |
| P3-05 | 端到端测试：在 5-10 道覆盖“编译错/功能 bug/cosim 协议错”的题上跑完整流程 | ⚪ | ≥60% 题目 correctness 全绿，并输出测试报告 |
| P3-06 | 里程碑演示：录一段——给一道坏 HLS，agent 自动修到 csim+cosim 通过 | ⚪ | 有可复现脚本 + 演示录屏/日志 |

#### HLS 域主

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P3-07 | 扩知识库到 cosim 协议类：dataflow 死锁规则、AXI-Stream 握手(TLAST/TREADY/TVALID)、ap_ctrl 时序 | ⚪ | ≥5 条 cosim 类条目 |
| P3-08 | 整理 PPA 优化杠杆清单（pipeline/unroll/array_partition/dataflow/bind_op）及何时用 | ⚪ | 1 份“PPA 优化速查”，供 P4 用 |
| P3-09 | 配合 Agent 主做端到端测试：提供 5-10 道覆盖各类错误的题 + 标准答案 | ⚪ | 测试题集交付，参与判定成功率 |
| P3-10 | 里程碑汇合：与 Agent 主一起完成“第一个 Agent 跑通”演示 | ⚪ | 演示中你的知识库条目至少被命中并生效 1 次 |

---

### P4：PPA 优化冲分（第 6 周起，后续）

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P4-01 | 让 agent 读综合报告定位瓶颈（latency/II/资源） | Agent 主 | ⚪ | 依赖 P3-08 弹药 |
| P4-02 | pragma 变换优化 PPA（pipeline/unroll/partition/dataflow） | Agent 主 | ⚪ | |
| P4-03 | 预算内取舍策略：便宜工具先跑、贵的省着用、置信度低就停 | Agent 主 | ⚪ | |

---

## 4. 变更记录 (Change Log)

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-11 | 补充手册路线图、汇合点表、P1/P2/P3 按人细化检查清单、P0-06~P0-08 完成 | Agent 主 |
| 2026-07-10 | 初始工程计划建立；P0 全部完成；P1 开始 | Agent 主 |