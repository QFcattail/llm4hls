# 工程计划 (Engineering Plan)

> 本文档是项目进度的**唯一真相来源（Single Source of Truth）**。任何人想知道"现在做到哪一步了、接下来做什么"，只需要看这一份文档。
>
> 更新规则：每完成一个原子任务，立刻把对应行的状态改掉，并在"变更记录"里追加一行。不要等到一天结束才批量更新。
>
> 每进入一个阶段先细化原子任务，原子任务一定要细，不要一个任务需要一周的量。

最后更新时间 (Last Updated)：2026-07-20（**v0.6.0**：最终 cosim 体检扩展到所有题型（best 变过且预算够则跑，失败回滚）+ run 内 latency 优化轨迹显示。15/15 测试全过。此前 07-19 **v0.5.0**：DeepSeek JSON 结构化输出（propose/select）+ 评审 AI 可行性+兼容性双审查（带毒策略提前否决）+ 失败感知回退。14/14 测试全过，真 API 验证否决带毒策略。此前 **v0.4.0**：TUI 得分区——agent 线程 grade() + submit SCORE + 最近 5 次得分历史（scores.jsonl 双入口互通）+ error tab 阶段感知三规则（review 失败进工具区/就绪行跟子阶段/等待行带阶段标签）。修复 TUI 启动崩溃（_compose 撞名）与策略解析发散。本地+服务器 11/11 测试全过。）

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
| P2 | 搭骨架 + 最小正确性闭环 | 第 2 周 | 🟢 **里程碑达成** | agent 骨架搭好，projection 题端到端真修复跑通（DeepSeek + 真 Vitis），SCORE 1.400。剩 dotProduct/residual 验证 + 知识库填充 |
| P3 | 接真 Vitis + cosim + 里程碑 | 第 3-4 周 | 🟡 收尾中 | 真机 3 题全过（P3-03/05/06 🟢，correctness 全绿 100%）；剩 P3-07 录屏 + KB 扩充（域主）+ DoD 5-10 题缺口 |
| P4 | PPA 优化冲分 + 提交物 | 第 5 周起 | 🟡 提前启动 | optimize 循环已实现（P4-01 🟢，v0.2.0）；真机冲分 + token 优化（第二次迭代）+ Docker/报告/视频待做 |

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
| P1-11 | 租云服务器 + 装 Vitis 2025.2（Ubuntu 22.04） | 🟢 | **完成。服务器 QFS-STATION：8核/14G/466G 数据盘，Vitis 2025.2 装于 /home/admin/Xilinx（92G），vitis-run 验证可用** |
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
| P2-03 | 搭 agent/ 目录骨架 + 模块 | 🟢 | router/checkpoint/feedback/llm_client/observability/knowledge_base/mechanical_checks/deepseek_client/main_loop 全部建出 |
| P2-04 | 实现 router.py：task.toml → RunPlan | 🟢 | 3 道题路由正确（repair→[csim]、optimize→[csim]、structural→[csim,cosim]） |
| P2-05 | 实现 checkpoint.py：关卡等级 + 存档判定三条规则 | 🟢 | 三规则单元测试全过 |
| P2-06 | 实现 main_loop.py 主循环（correctness 阶段） | 🟢 | **真 Vitis + DeepSeek 跑通 projection 题：csim fail→修复→csim pass→synth pass，SCORE 1.400** |
| P2-07 | 实现 feedback.py：从 ToolResult 构建 LLM 友好反馈 | 🟢 | 真实 csim runtime_fail 日志验证通过 |
| P2-08 | 接 LLM（ScriptedClient + DeepSeek） | 🟢 | DeepSeek V4 Pro 端到端真修复跑通（2 次 LLM 调用，3453 tokens） |
| P2-09 | 接知识库 + 错误签名匹配检索 | 🟢 | 检索器 + 种子条目 7 条（entries.py：synth 4/cosim 1/csim 2）接入两个入口；synth/optimize 链路已调检索。≥10 条扩充仍属 P2-12 |
| P2-10 | 可观测性：结构化日志 + transcript + 心跳 | 🟢 | JSONL + heartbeat 真环境记录通过（route/tool_result/review/checkpoint 全事件） |
| P2-11 | 交叉验证：机械检查 + LLM review 双层 | 🟢 | mechanical_checks 签名/include 硬门 + DeepSeek self-check，projection 运行中两层都触发 |

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
| P3-03 | 在云服务器（SSH）上跑通真 csim/synth/cosim | 🟢 | 真机 3 题全过（v0.1.1 起多次运行）：csim/synth/cosim 均真跑非占位；cosim 实测延迟已观测（residual 97/32） |
| P3-04 | ~~加预算计数与止损~~ | ✅ | **官方 Budget + BudgetExceeded 已实现。已废弃。** |
| P3-05 | 扩 main_loop 的 structural 路径：csim+cosim 双验证 + 优化后回验 | 🟢 | **residual 真机跑通（SCORE 3.098）**：pre-csim review 一次修掉死锁（cosim 首跑即过），§4.5 回滚路径就绪（best 未变跳过回验） |
| P3-06 | 端到端测试：3 道公开题跑完整流程 + 评分 | 🟢 | **3/3 真机全过**：projection 1.400 / dotProduct 3.000（满分）/ residual 3.098，correctness 全绿 100%（DoD ≥60% 达标） |
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
| P4-01 | 实现 optimize 阶段：注入综合报告 + Strategy Exploration + 存档择优 | Agent 主 | 🟢 | v0.2.0 完成：设计文档+设计摘要提取（extract_design_brief）+取首策略+重验+同级择优+真回滚；离线 6 用例过，真机待验。对应 agent-architecture.md §4.4 |
| P4-02 | pragma 变换优化 PPA（pipeline/unroll/partition/dataflow） | Agent 主 | 🟢 | **真机实证**：dotProduct 73.36× 加速、SCORE 3.000 满分（策略组合：PIPELINE+UNROLL+ARRAY_PARTITION+加法树重构） |
| P4-03 | 第二次迭代：token 优化（第一次迭代暂不考虑） | Agent 主 | ⚪ | 第一次迭代跑稳后，分析日志压 token |
| P4-04 | 第二次迭代：功能 pattern 检索（agent-architecture.md §6.4） | Agent 主 | ⚪ | 难度较高，先靠错误签名匹配 |
| P4-05 | Docker 镜像打包 | Agent 主 | ⚪ | 复用官方 vitis.dockerfile |
| P4-06 | 技术报告撰写 | 双方 | ⚪ | 含模型对比实验 |
| P4-07 | 演示视频录制（≤5分钟） | 双方 | ⚪ | 在目标平台运行 + 清晰讲解 |

---

## 4. 变更记录 (Change Log)

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-20 | **v0.6.0（验证完整性 + 轨迹可视）**。按用户三点疑问：① §4.4 图统一 LLM# 标注（消除'apply 环节被删'困惑）；② 最终 cosim 体检扩展到所有题型（synth 估计≠实测：residual 68 vs 97；best 变过且预算够则跑，失败回滚快照；非 structural 预算不够跳过记事件）；③ TUI 显示 run 内 latency 优化轨迹（38→37→22→14）。TC-AGENT-015 新增，15/15 全过。详见 dev-log 2026-07-20-01。 | Agent 主 |
| 2026-07-19 | **v0.5.0（optimize 决策质量）**。按用户三点反馈：① DeepSeek `response_format: json_object` 结构化输出（propose/select 改 JSON schema，正则降级兜底）；② 评审 AI 扩展为可行性+兼容性双审查——带毒策略（如改接口/破坏功能）进 rejected 并级联否决，真 API 验证拦下"Unroll+Cyclic Partitioning 改接口"类策略；③ 盲回退改失败感知回退——fallback apply 注入失败工具反馈（错误码+日志尾）。select 解析失败重试一次再回退且 `fallback=true` 不再静默。TC-012/013/014 新增，14/14 全过。详见 dev-log 2026-07-19-03。 | Agent 主 |
| 2026-07-19 | **三类题真机全部验证 + v0.4.1**。residual(structural) 真机首跑 SCORE **3.098**（baseline 135→68 cyc，1.99×）：pre-csim review 一次修掉死锁（cosim 首跑即过，省 20 credits+15min 超时）；优化轮评审 AI 拦下 DATA_PACK 误用（retry 后过）；组合候选 synth 失败（pragma 写在文件作用域）→ 回退首策略单试（v2.4 归因回退真机首验）→ 无改进收敛。P3-05/P3-06 转 🟢（3/3 全过，correctness 全绿 100%）。另修阶段切换 last review/error 残留（v0.4.1）。 | Agent 主 |
| 2026-07-19 | **v0.4.0（TUI 得分区 + error tab 阶段感知）**。按用户实测反馈：① TUI agent 线程补 grade() 调用——submit stat 显示 SCORE、区域 C 打印 Scorecard + 最近 5 次得分历史（新模块 agent/score_history.py，runs/<task>/scores.jsonl，CLI/TUI 双入口互通）；② error tab 三规则（tui-design v5）——mechanical review 失败进工具区、就绪行跟 llm_call 子阶段（补 extract_brief/apply_strategies 事件）、等待行带阶段标签；③ 修 TUI 启动崩溃（_compose 撞名 Textual 内部方法 → _build_render + 真挂载冒烟）；④ 修策略解析发散（严格 prompt + 宽容解析 + raw_head 诊断）；⑤ DONE 行加总耗时。TC-AGENT-011 新增，11/11 全过。详见 dev-log 2026-07-19-01。 | Agent 主 |
| 2026-07-18 | **真机 e2e 验证（QFS-STATION）**。rsync 同步后服务器离线 10/10 过。projection 回归 SCORE 1.400 持平；**dotProduct optimize 循环 SCORE 3.000 满分**（baseline 1027→14 cyc，73.36× 加速；4 轮优化：R1 三组合 38→37、R2 排他二组合 37→22、R3 保守单选 22→14、R4 无改进收敛）。修复真机暴露的策略解析器问题两轮（markdown 标题 + 无冒号字段标签 + 非策略块过滤），TC-AGENT-010 新增。P3-06 转 🟡（2/3）、P4-02 转 🟢。详见 dev-log 2026-07-18-05。 | Agent 主 |
| 2026-07-18 | **v0.3.0 / 架构 v2.4 落地**。按用户三决策升级 optimize：① 策略从单选改组合——propose 逐策略标 `combinable_with`，新增评审 AI `select_strategies`（同模型换 prompt）复核兼容性选子集，**双重确认才允许组合**，`apply_strategies` 合并应用为一份候选；② 组合失败归因回退：组合候选失败/无改进 → 回退子集首策略单试一次 → 仍失败才停（单策略失败 fail-fast）；③ TUI error tab 在 optimize 阶段复用为策略面板（策略区≤2行+工具区≤3行共存），ToolErrorBar 改状态驱动渲染（防 150ms 心跳 show_running 擦掉策略行）。tui-design v4 同步。验证：TC-AGENT-007/008/009 新增 + 002/003 语义更新，离线 9 用例 ×3 全过。详见 dev-log 2026-07-18-04。 | Agent 主 |
| 2026-07-18 | **v0.2.0 / 架构 v2.3 落地**。按用户指出的三处设计-实现差距补齐：① synth 报错检索增强修复循环（§4.3：失败→反馈蒸馏→KB 检索→修复→先重验 csim 再 synth，max_synth_rounds=3）；② optimize PPA 优化循环（§4.4：AMD Phase 1 设计文档 description+headers + extract_design_brief 设计摘要 + synth 报告 → Phase 2 取首策略 → Phase 3 双闸门 → 重验 csim+synth → 同级 latency 择优，max_optimize_rounds=4）；③ §4.5 真回滚修复（原实现只记日志不恢复快照）。另加 latency=0 防御、KB 种子条目 7 条（P2-09 转 🟢）、P4-01 转 🟢。验证：scripts/test_main_loop.py 离线 6 用例（TC-AGENT-001~006）×3 全过；真机 dotProduct/residual e2e 待服务器。详见 dev-log 2026-07-18-03。 | Agent 主 |
| 2026-07-15 | **P2 里程碑达成**。Vitis 2025.2 装好（服务器 QFS-STATION），projection 题端到端真修复跑通：DeepSeek 自主诊断 csim runtime_fail → 修复 → csim pass → synth pass → hidden testbench PASS，SCORE 1.400。P2-03~P2-08/P2-10/P2-11 全部标记完成。P1-11（Vitis 安装）标记完成。P2 整体标记"里程碑达成"，剩 dotProduct/residual 验证 + 知识库填充。详见 dev-log 2026-07-15-01。 | Agent 主 |
| 2026-07-14 | **P2/P3 大重写**：harness 解压是决定性发现。废弃 P2-01（mock）/P2-02（日志解析）/P3-01（接真接口）/P3-02（Vitis 命令行）/P3-04（预算止损）—— 全被官方实现解决。P2 重写为"搭 agent 骨架 + 最小闭环"（P2-03~P2-11），P3 重写为"接真 Vitis + cosim + milestone"（P3-03~P3-07）。新增 P1-08a~d（harness 分析/离线跑通/架构定稿/部署方案）标记完成。架构定稿见 agent-architecture.md v2.2。里程碑总览时间表压缩（P2→第2周、P3→第3-4周、P4→第5周起），因 harness 省去大量基础工作。 | Agent 主 |
| 2026-07-11 | P1-02/03/05/06 全部完成：用户读完所有背景论文（ReAct、Anthropic agents、SWE-agent、HLS Repair、AutoChip、RTLFixer、HLSPilot、AMD案例）。AMD四阶段工作流与LLM优缺点已写入 dev-log 2026-07-11-03。用户确认已报名，只做Track A。明天开始规划agent架构。 | Agent 主 |
| 2026-07-11 | **工程计划收回聚焦 Track A**：用户明确只做 FPT'26 Track A LLM4HLS。删除 FPL'26/Track B 相关内容，恢复 P0-P4 五阶段结构。补充 AMD 案例文章的四阶段工作流作为方法论参考。 | Agent 主 |
| 2026-07-11 | 工程计划据实重写（涉及两个竞赛三条赛道），现已因用户决策收回。赛题规则已全部回填至 runtime-constraints.md。 | Agent 主 |
| 2026-07-11 | P1-01 完成（手册全文通读）；P1-04 环境侧完成（web_fetch.py + Playwright MCP + 双 python）；tech-debt 全量废弃 | Agent 主 |
| 2026-07-11 | 补充手册路线图、汇合点表、P1/P2/P3 按人细化检查清单、P0-06~P0-08 完成 | Agent 主 |
| 2026-07-10 | 初始工程计划建立；P0 全部完成；P1 开始 | Agent 主 |