# 工程计划 (Engineering Plan)

> 本文档是项目进度的**唯一真相来源（Single Source of Truth）**。任何人想知道"现在做到哪一步了、接下来做什么"，只需要看这一份文档。
>
> 更新规则：每完成一个原子任务，立刻把对应行的状态改掉，并在"变更记录"里追加一行。不要等到一天结束才批量更新。
>
> 每进入一个阶段先细化原子任务，原子任务一定要细，不要一个任务需要一周的量。

最后更新时间 (Last Updated)：2026-07-22（**v0.7.4 Docker 打包实测通过（P4-05 转 🟢）**：QFS-STATION 上 build 镜像成功，容器内跑通 projection_bugfix（SCORE 1.400）+ dotProduct_optimize（SCORE 3.000 满分），csim/synth 真跑非 mock，SCORE 与宿主机一致。关键发现：Vitis settings64.sh 硬编码兄弟目录绝对路径，必须挂载整个 Xilinx 树到容器内相同路径。剩 P4-06 报告 + P4-07 视频剪辑。今天 7/22，截止 8/7，剩 16 天。）

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
| P1 | 认知 + 环境 | 第 1 周 | 🟢 实质完成（程千和侧） | 读背景资料、解压 harness、跑通离线链路、架构定稿。方欣语侧（数电基础+Vitis 环境）进行中 |
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

| 汇合点 | 时间 | 程千和交付 | 方欣语交付 | 对齐动作 |
|---|---|---|---|---|
| 1 | 第一周末 | API 通路 | 日志样例包 | 程千和据此设计日志解析器 |
| 2 | 第三周末 | 知识库注入接口 + 评测脚本 | 知识库初版 + 3-5 道小题 | 跑首次本地评测，看 success rate |
| 3 | 第五周末 | 里程碑版 agent | 端到端测试题集 | 一起跑里程碑演示，达成 DoD |

---

## 3. 原子任务清单 (Atomic Task Backlog)

> 任务编号规则：`P<阶段号>-<序号>`。状态变更时同步更新本表，并在下方"变更记录"追加一行。

### P0：项目基础设施搭建

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P0-01 | 创建 Gitee 仓库 + SSH 专用密钥 | 程千和 | 🟢 已完成 | 密钥 id_ed25519_gitee |
| P0-02 | 定义目录结构 | 程千和 | 🟢 已完成 | docs-development 模式 |
| P0-03 | 写工程计划 + dev-log 规范 | 程千和 | 🟢 已完成 | |
| P0-04 | 写顶层 README + .gitignore | 程千和 | 🟢 已完成 | |
| P0-05 | 首篇开发日志 | 程千和 | 🟢 已完成 | 2026-07-10-01 |
| P0-06 | 赛题原文入库 | 程千和 | 🟢 已完成 | contest/ 目录 |
| P0-07 | 备赛手册入库 | 程千和 | 🟢 已完成 | internal-notes/ |
| P0-08 | 工程计划细化 | 程千和 | 🟢 已完成 | |

---

### P1：认知 + 环境（第 1 周）

#### 程千和

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

#### 方欣语

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P1-09 | 刷新数电基础：组合/时序逻辑、触发器、FSM、时序、流水线 | ⚪ | 能讲清"流水线为什么提高吞吐、寄存器干啥" |
| P1-10 | 读 Kastner《Parallel Programming for FPGAs》前几章 + UG1399 的 csim/csynth/cosim 章节 | ⚪ | 能讲清 csim/synth/cosim 各验什么、报告里 II/latency/资源在哪 |
| P1-11 | 租云服务器 + 装 Vitis 2025.2（Ubuntu 22.04） | 🟢 | **完成。服务器 QFS-STATION：8核/14G/466G 数据盘，Vitis 2025.2 装于 /home/admin/Xilinx（92G），vitis-run 验证可用** |
| P1-12 | 读 AMD LLM4HLS SHA-256 案例文章 | 🟢 | 用户已代读完（dev-log 2026-07-11-03），四阶段工作流已写入 |

> **P1 收尾说明**（2026-07-14）：harness 解压是决定性发现，把原 P1-07（日志样例包）、P1-12（AMD 文章）的状态全部改写。程千和侧 P1 实质完成，进入 P2。方欣语侧 P1-09/10/11 仍待推进（数电基础 + Vitis 环境）。

---

### P2：搭骨架 + 最小正确性闭环（第 2 周）

> **重写说明**（2026-07-14）：原 P2-01（mock）、P2-02（日志解析）、P2-05（评测脚本）被官方 harness 解决（ToolServer + report.py + scoring.py + run_poc.py）。P2 重心改为：**按 agent-architecture.md 搭 agent 骨架，在 ScriptedClient 上跑通最小闭环**。

#### 程千和

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

#### 方欣语

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P2-12 | 按 schema 整理知识库条目（先覆盖编译错+csim 功能 bug+cosim 死锁） | 🟢 | **22 条入库**（7 种子 + 15 新增）：真机日志来源 [HLS 207-6969] pragma 文件作用域、DATA_PACK 打类型名、浮点重排容差、边界条件 |
| P2-13 | 读 AutoChip / RTLFixer / HLS Repair 三篇，提炼修法模式 | 🟢 | **6 条 pattern 条目**（pattern-* 前缀）：检索先行、正确性/优化分离、语法优先、错误消息配对、期望值差异反馈、有界反馈循环 |

---

### P3：接真 Vitis + cosim + 里程碑（第 3-4 周）

> **重写说明**（2026-07-14）：原 P3-01/02（接真接口）、P3-04（预算止损）被 harness 解决（接口已是进程内函数 + Budget 类）。P3 重心改为：**接到真 Vitis 环境，扩 cosim 协议错处理，端到端跑 milestone**。

#### 程千和

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P3-01 | ~~把 mock 替换为真评估接口~~ | ✅ | **官方 ToolServer 自始即是真接口，无需替换。已废弃。** |
| P3-02 | ~~本地接 Vitis HLS 命令行~~ | ✅ | **官方 vitis.py 已封装（vitis-run --mode hls）。已废弃。** |
| P3-03 | 在云服务器（SSH）上跑通真 csim/synth/cosim | 🟢 | 真机 3 题全过（v0.1.1 起多次运行）：csim/synth/cosim 均真跑非占位；cosim 实测延迟已观测（residual 97/32） |
| P3-04 | ~~加预算计数与止损~~ | ✅ | **官方 Budget + BudgetExceeded 已实现。已废弃。** |
| P3-05 | 扩 main_loop 的 structural 路径：csim+cosim 双验证 + 优化后回验 | 🟢 | **residual 真机跑通（SCORE 3.098）**：pre-csim review 一次修掉死锁（cosim 首跑即过），§4.5 回滚路径就绪（best 未变跳过回验） |
| P3-06 | 端到端测试：3 道公开题跑完整流程 + 评分 | 🟢 | **3/3 真机全过**：projection 1.400 / dotProduct 3.000（满分）/ residual 3.098，correctness 全绿 100%（DoD ≥60% 达标） |
| P3-07 | 里程碑演示：录一段 agent 自动修 HLS 的日志/录屏 | 🟡 | 录屏脚本就绪（docs-development/recording-script.md：三镜头 + 解说词要点 + 剪辑建议）；**设备约束已适配**：改 asciinema 服务器端录制 + 后期配音，待实际录制 |

#### 方欣语

| 任务ID | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| P3-08 | 扩知识库到 cosim 协议类：dataflow 死锁、AXI-Stream 握手(TLAST/TREADY/TVALID)、ap_ctrl | 🟢 | **6 条 cosim 类条目**：FIFO 深度、TLAST 缺失、TVALID/TREADY 握手、ap_ctrl 挂起、synth/cosim 延迟不一致（+原有 fifo-burst） |
| P3-09 | 整理 PPA 优化杠杆清单（pipeline/unroll/array_partition/dataflow/bind_op） | 🟢 | `agent/knowledge-base/ppa-levers.md`：6 杠杆速查 + 6 题真机延迟参考表 + 组合顺序建议 |
| P3-10 | 配合端到端测试 + 里程碑汇合 | 🟡 | kb_search 事件已补 hit_ids（架构 §12.2）；真机命中观察随新题验证进行 |

---

### P4：PPA 优化冲分 + 提交物（第 5 周起）

| 任务ID | 任务 | 负责人 | 状态 | 备注 |
|---|---|---|---|---|
| P4-01 | 实现 optimize 阶段：注入综合报告 + Strategy Exploration + 存档择优 | 程千和 | 🟢 | v0.2.0 完成：设计文档+设计摘要提取（extract_design_brief）+取首策略+重验+同级择优+真回滚；离线 6 用例过，真机待验。对应 agent-architecture.md §4.4 |
| P4-02 | pragma 变换优化 PPA（pipeline/unroll/partition/dataflow） | 程千和 | 🟢 | **真机实证**：dotProduct 73.36× 加速、SCORE 3.000 满分（策略组合：PIPELINE+UNROLL+ARRAY_PARTITION+加法树重构） |
| P4-03 | 第二次迭代：token 优化（第一次迭代暂不考虑） | 程千和 | 🟢 | **v0.7.0 分级开关 + 真机 A/B 验收**：`--token-mode full(默认，逐字节同旧行为)/balanced/aggressive`；A/B 三题 tokens −31.3%/−8.4%/−50.4% 且 SCORE 全不降（vecadd/dotProduct 满分保持，matmul 反升 2.270→2.691）；per-call 埋点归因 select 每次省 ~4-5k |
| P4-04 | 第二次迭代：功能 pattern 检索（agent-architecture.md §6.4） | 程千和 | ⚪ | 难度较高，先靠错误签名匹配；决策：Docker 后看时间 |
| P4-05 | Docker 镜像打包 | 程千和 | 🟢 | v0.7.4 完成：Dockerfile + .dockerignore + docker-run.sh + QFS-STATION 实测通过（projection 1.400 / dotProduct 3.000 满分，csim/synth 真跑）。Vitis 挂载整个 Xilinx 树（settings64.sh 硬编码兄弟路径） |
| P4-06 | 技术报告撰写 | 双方 | ⚪ | 含模型对比实验 |
| P4-07 | 演示视频录制（≤5分钟） | 双方 | 🟡 | 录制完成，待剪辑（asciinema 方案）；录屏发现 2 个 TUI 显示问题，记入下方待办区 |

---

## TUI 已知待办（录屏发现，非阻塞）

> 2026-07-22 录制演示视频时发现两个 TUI 显示体验问题，不影响功能正确性，记此待办，优先级低于 Docker/报告/视频交稿，留待交稿后修。

| 编号 | 现象 | 根因（初判） | 涉及代码 | 优先级 |
|---|---|---|---|---|
| TUI-01 | 优化阶段不显示最近一次 latency，用户看不到实时改进 | latency 轨迹仅在 `score` 事件（最终评分）时渲染到 ActivityPanel（`app.py:396-398`）；`checkpoint` 事件虽累积 `_latency_traj`（`app.py:471-486`）但优化进行中无实时展示 | `tui/app.py`（可考虑在 `checkpoint` 事件分支追加一行 ActivityPanel 日志，或在 status_bar 加 latency 字段） | 低 |
| TUI-02 | review 第一次 reject 后修复成功，但 reject 状态一直挂着直到下一次 review 判定才刷新，延续到编译跑完进入下一阶段 | `review` 事件按 verdict 更新 `_last_review`（`app.py:435-440`），但 reject 后的修复重试循环（`_repair_with_review`/`_apply_with_review` 内 retry）期间不发新 review 事件，导致红字持续；需确认是否真的 review 了（看日志 event 而非仅看 TUI） | `tui/app.py` + `agent/main_loop.py`（可考虑修复重试开始时置 `_last_review="(retrying...)"` 占位） | 低 |

---

## 5. 交稿路线图（2026-07-20 划定，截止 8/7 剩 18 天）

### 现状盘点（已完成）

- **Agent 功能**：三阶段主循环 + 策略组合/评审 AI（可行性+兼容性双审查）+ JSON 结构化输出 + 失败感知回退 + 最终 RTL 体检 + KB 检索 + 存档快照回滚
- **真机成绩**：projection 1.400 / dotProduct 3.000 满分 / residual 最高 4.000 满分（3/3 公开题 correctness 全绿 100%）
- **工程基建**：TUI 仪表盘（策略面板+SCORE+得分历史+latency 轨迹）、16 个离线测试、文档体系、可复现脚本
- **泛化题集（2026-07-20 新增）**：vecadd/fir/matmul 三道 optimize 新题（官方格式 + hidden TB），真机 scripted 3/3 全过（0.997/2.000/3.000），DeepSeek 真机 vecadd 1.000 满分 / fir 2.000 满分 / matmul 2.270（优化候选 synth 超时，归因回退正常）——DoD 5-10 题缺口闭合至 6 题，correctness 6/6 全绿
- **知识库（2026-07-20）**：22 条（synth/csim/cosim/论文 pattern 四类）+ kb_search hit_ids 埋点
- **token 优化（2026-07-20，v0.7.0）**：分级开关 `--token-mode` 落地（full 默认 = 逐字节旧行为），per-call token 埋点

### 差距清单（除异模型评审外）

| 类别 | 任务 | 说明 |
|---|---|---|
| ✅ 已闭合 | ~~P4-05 Docker 打包~~ | **2026-07-22 完成（v0.7.4）**：QFS-STATION build + 镜像内复现验证通过（projection 1.400 / dotProduct 3.000 满分） |
| 🔴 提交硬要求 | P4-06 技术报告 | 含模型对比实验（赛题要求三选一/多模型对比 + 鼓励评测其他开源模型） |
| 🔴 提交硬要求 | P4-07 演示视频 ≤5min | 目标平台实跑 + 讲解；与 P3-07 里程碑录屏合并 |
| 🔴 提交硬要求 | 提交物打包 | 源码 + testbench + 补充材料(.zip) + 视频 |
| ✅ 已闭合 | ~~P4-03 token 优化~~ | **2026-07-20 完成（v0.7.0）**：分级开关默认 full 不限制；A/B 三题 −31.3%/−8.4%/−50.4% 且 SCORE 全不降 |
| 🟡 得分项 | P4-04 功能 pattern 检索 | 第二次迭代；压优化方差（residual 各 run latency 6~68 波动）。决策：Docker 后看时间 |
| ✅ 已闭合 | ~~造 2-3 道新题泛化验证~~ | **2026-07-20 完成**：vecadd/fir/matmul 入库，6 题达标（详见现状盘点） |
| ✅ 域主 | ~~P2-12/13、P3-08/09~~ | **2026-07-20 完成**：KB 22 条、cosim 类 6 条、PPA 速查入库；P3-10 真机命中观察中 |

### 三周排布

**第 1 周（7/20-7/26）收尾验证期**
1. 造 2-3 道新题（FIR 滤波 / 向量加 / 矩阵乘，照官方 task 格式：kernel+testbench+task.toml+reference）——同时解决 DoD 缺口和泛化风险，**本周最高优先级**
2. 域主 KB 扩充（造题真机日志正好当素材）
3. 顺手录 P3-07 演示素材

**第 2 周（7/27-8/2）指标与打包期**
1. P4-03 token 优化：先量化分析现有 JSONL 找大头（reasoning_tokens），压 30-50%（reasoning_effort 分级、砍冗余注入）
2. P4-05 Docker 打包 + 镜像内复现（官方环境与服务器可能有差异，必须实测）
3. P4-06 技术报告开写 + 模型对比实验开跑（同 3 题 × DeepSeek V4 Pro vs Qwen3.5/3.6，主要花机器时间）

**第 3 周（8/3-8/7）交稿周**
1. P4-07 视频剪辑 + 报告定稿
2. 提交物打包 + 官方 checklist 逐项过
3. **留 2 天缓冲**（隐藏测试集/环境意外保险）

### 时间紧时的砍单顺序

① 造题泛化验证 ② Docker 复现 ③ 报告+视频 ④ token 优化 ⑤ pattern 检索

---

## 4. 变更记录 (Change Log)

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-22 | **v0.7.4：Docker 打包实测通过（P4-05 转 🟢）**。① 研读赛题规则确认：Dockerfile 是 recommended 非强制，Vitis 自备不需打进镜像（92G+license 绑定），官方 run-vitis.sh 即"挂载宿主机 Vitis"模型。② 新增 `Dockerfile`（Ubuntu 22.04 + 官方 vitis.dockerfile 依赖层 + Python 3.12 venv + textual/rich + agent 源码，Vitis 运行时挂载）、`.dockerignore`、`docker-run.sh`（封装挂载 + API key + 输出目录，CLI/TUI 双模式）。③ **QFS-STATION 实测**：docker build 成功（配镜像加速 + pip 清华源 + venv 解决 3.12 distutils 移除）；容器内跑通 projection_bugfix（csim 9.5s + synth 23.1s，SCORE 1.400）+ dotProduct_optimize（csim 10s + synth 25.6s + optimize 路径，SCORE 3.000 满分），csim/synth 真跑非 mock，SCORE 与宿主机一致。④ **关键发现**：Vitis settings64.sh 硬编码兄弟目录绝对路径（DocNav/Vivado/Model_Composer），必须挂载整个 Xilinx 树到容器内相同路径（非 /opt/xilinx 重映射）。⑤ 修 `_auto_source_vitis` 候选路径补小写 `/opt/xilinx/...`。⑥ getting-started.md 加 §7。⑦ 录屏发现 2 个 TUI 待办（TUI-01/02），记入代办区非阻塞。19/19 测试过。 | 程千和 |
|---|---|---|
| 2026-07-20 | **v0.7.1：KB 语料 JSON 化（清技术债）**。用户打包前指出 KB 内嵌 Python 不合理——执行架构 §9 既定迁移：22 条语料落 `entries.json` 单源（程序化导出零转录错误；JSON 而非 YAML 因纯 stdlib 约束）；entries.py 变薄加载器，调用方零改动；16/16 测试过；entries.doc.md/架构 §9/getting-started FAQ 同步。 | 程千和 |
|---|---|---|
| 2026-07-20 | **Docker ready 前任务全推进（v0.7.0）**。① 造 3 道泛化新题 vecadd/fir/matmul（官方格式 + hidden TB，本机 g++ 预检 + 真机 scripted 3/3 + DeepSeek 端到端 1.000/2.000/2.270，**DoD 5-10 题缺口闭合至 6 题**，correctness 6/6 全绿）。② KB 7→22 条（P2-12 真机日志 4 条 / P2-13 论文 pattern 6 条 / P3-08 cosim 类 5 条）+ P3-09 PPA 速查（ppa-levers.md）+ kb_search hit_ids 埋点。③ **P4-03 转 🟢**：token 分级开关 `--token-mode`（默认 full 逐字节同旧行为，用户拍板成品不限制）+ per-call token 埋点（§12.2 落地）；真机 A/B 三题 −31.3%/−8.4%/−50.4% 且 SCORE 全不降。④ P3-07 录屏脚本（asciinema 方案适配设备约束）。⑤ 双语 .doc.md ×8 同步 + runs/README v0.7.0 字段。P3-10 真机 KB 命中未自然触发（正确性/综合阶段零失败，已如实记录）。详见 dev-log 2026-07-20-03。 | 程千和 |
|---|---|---|
| 2026-07-20 | **交稿路线划定 + 日志阅读指南**。① 盘点交稿差距：功能完成 ~70%，剩提交物（Docker/报告/视频）、DoD 5-10 题泛化缺口（最大风险）、token 优化（终评指标）、KB 扩充；新增 §5 交稿三周路线图（收尾验证→指标打包→交稿缓冲）。② P3-03 转 🟢、P3 里程碑行转"收尾中"（计划卫生）。③ runs/README.md 新增「日志阅读指南」（用户首次读日志：三种日志分工/事件速查/真实片段注释/实用命令/30 秒判好坏）。详见 dev-log 2026-07-20-02。 | 程千和 |
| 2026-07-20 | **v0.6.0（验证完整性 + 轨迹可视）**。按用户三点疑问：① §4.4 图统一 LLM# 标注（消除'apply 环节被删'困惑）；② 最终 cosim 体检扩展到所有题型（synth 估计≠实测：residual 68 vs 97；best 变过且预算够则跑，失败回滚快照；非 structural 预算不够跳过记事件）；③ TUI 显示 run 内 latency 优化轨迹（38→37→22→14）。TC-AGENT-015 新增，15/15 全过。详见 dev-log 2026-07-20-01。 | 程千和 |
| 2026-07-19 | **v0.5.0（optimize 决策质量）**。按用户三点反馈：① DeepSeek `response_format: json_object` 结构化输出（propose/select 改 JSON schema，正则降级兜底）；② 评审 AI 扩展为可行性+兼容性双审查——带毒策略（如改接口/破坏功能）进 rejected 并级联否决，真 API 验证拦下"Unroll+Cyclic Partitioning 改接口"类策略；③ 盲回退改失败感知回退——fallback apply 注入失败工具反馈（错误码+日志尾）。select 解析失败重试一次再回退且 `fallback=true` 不再静默。TC-012/013/014 新增，14/14 全过。详见 dev-log 2026-07-19-03。 | 程千和 |
| 2026-07-19 | **三类题真机全部验证 + v0.4.1**。residual(structural) 真机首跑 SCORE **3.098**（baseline 135→68 cyc，1.99×）：pre-csim review 一次修掉死锁（cosim 首跑即过，省 20 credits+15min 超时）；优化轮评审 AI 拦下 DATA_PACK 误用（retry 后过）；组合候选 synth 失败（pragma 写在文件作用域）→ 回退首策略单试（v2.4 归因回退真机首验）→ 无改进收敛。P3-05/P3-06 转 🟢（3/3 全过，correctness 全绿 100%）。另修阶段切换 last review/error 残留（v0.4.1）。 | 程千和 |
| 2026-07-19 | **v0.4.0（TUI 得分区 + error tab 阶段感知）**。按用户实测反馈：① TUI agent 线程补 grade() 调用——submit stat 显示 SCORE、区域 C 打印 Scorecard + 最近 5 次得分历史（新模块 agent/score_history.py，runs/<task>/scores.jsonl，CLI/TUI 双入口互通）；② error tab 三规则（tui-design v5）——mechanical review 失败进工具区、就绪行跟 llm_call 子阶段（补 extract_brief/apply_strategies 事件）、等待行带阶段标签；③ 修 TUI 启动崩溃（_compose 撞名 Textual 内部方法 → _build_render + 真挂载冒烟）；④ 修策略解析发散（严格 prompt + 宽容解析 + raw_head 诊断）；⑤ DONE 行加总耗时。TC-AGENT-011 新增，11/11 全过。详见 dev-log 2026-07-19-01。 | 程千和 |
| 2026-07-18 | **真机 e2e 验证（QFS-STATION）**。rsync 同步后服务器离线 10/10 过。projection 回归 SCORE 1.400 持平；**dotProduct optimize 循环 SCORE 3.000 满分**（baseline 1027→14 cyc，73.36× 加速；4 轮优化：R1 三组合 38→37、R2 排他二组合 37→22、R3 保守单选 22→14、R4 无改进收敛）。修复真机暴露的策略解析器问题两轮（markdown 标题 + 无冒号字段标签 + 非策略块过滤），TC-AGENT-010 新增。P3-06 转 🟡（2/3）、P4-02 转 🟢。详见 dev-log 2026-07-18-05。 | 程千和 |
| 2026-07-18 | **v0.3.0 / 架构 v2.4 落地**。按用户三决策升级 optimize：① 策略从单选改组合——propose 逐策略标 `combinable_with`，新增评审 AI `select_strategies`（同模型换 prompt）复核兼容性选子集，**双重确认才允许组合**，`apply_strategies` 合并应用为一份候选；② 组合失败归因回退：组合候选失败/无改进 → 回退子集首策略单试一次 → 仍失败才停（单策略失败 fail-fast）；③ TUI error tab 在 optimize 阶段复用为策略面板（策略区≤2行+工具区≤3行共存），ToolErrorBar 改状态驱动渲染（防 150ms 心跳 show_running 擦掉策略行）。tui-design v4 同步。验证：TC-AGENT-007/008/009 新增 + 002/003 语义更新，离线 9 用例 ×3 全过。详见 dev-log 2026-07-18-04。 | 程千和 |
| 2026-07-18 | **v0.2.0 / 架构 v2.3 落地**。按用户指出的三处设计-实现差距补齐：① synth 报错检索增强修复循环（§4.3：失败→反馈蒸馏→KB 检索→修复→先重验 csim 再 synth，max_synth_rounds=3）；② optimize PPA 优化循环（§4.4：AMD Phase 1 设计文档 description+headers + extract_design_brief 设计摘要 + synth 报告 → Phase 2 取首策略 → Phase 3 双闸门 → 重验 csim+synth → 同级 latency 择优，max_optimize_rounds=4）；③ §4.5 真回滚修复（原实现只记日志不恢复快照）。另加 latency=0 防御、KB 种子条目 7 条（P2-09 转 🟢）、P4-01 转 🟢。验证：scripts/test_main_loop.py 离线 6 用例（TC-AGENT-001~006）×3 全过；真机 dotProduct/residual e2e 待服务器。详见 dev-log 2026-07-18-03。 | 程千和 |
| 2026-07-15 | **P2 里程碑达成**。Vitis 2025.2 装好（服务器 QFS-STATION），projection 题端到端真修复跑通：DeepSeek 自主诊断 csim runtime_fail → 修复 → csim pass → synth pass → hidden testbench PASS，SCORE 1.400。P2-03~P2-08/P2-10/P2-11 全部标记完成。P1-11（Vitis 安装）标记完成。P2 整体标记"里程碑达成"，剩 dotProduct/residual 验证 + 知识库填充。详见 dev-log 2026-07-15-01。 | 程千和 |
| 2026-07-14 | **P2/P3 大重写**：harness 解压是决定性发现。废弃 P2-01（mock）/P2-02（日志解析）/P3-01（接真接口）/P3-02（Vitis 命令行）/P3-04（预算止损）—— 全被官方实现解决。P2 重写为"搭 agent 骨架 + 最小闭环"（P2-03~P2-11），P3 重写为"接真 Vitis + cosim + milestone"（P3-03~P3-07）。新增 P1-08a~d（harness 分析/离线跑通/架构定稿/部署方案）标记完成。架构定稿见 agent-architecture.md v2.2。里程碑总览时间表压缩（P2→第2周、P3→第3-4周、P4→第5周起），因 harness 省去大量基础工作。 | 程千和 |
| 2026-07-11 | P1-02/03/05/06 全部完成：用户读完所有背景论文（ReAct、Anthropic agents、SWE-agent、HLS Repair、AutoChip、RTLFixer、HLSPilot、AMD案例）。AMD四阶段工作流与LLM优缺点已写入 dev-log 2026-07-11-03。用户确认已报名，只做Track A。明天开始规划agent架构。 | 程千和 |
| 2026-07-11 | **工程计划收回聚焦 Track A**：用户明确只做 FPT'26 Track A LLM4HLS。删除 FPL'26/Track B 相关内容，恢复 P0-P4 五阶段结构。补充 AMD 案例文章的四阶段工作流作为方法论参考。 | 程千和 |
| 2026-07-11 | 工程计划据实重写（涉及两个竞赛三条赛道），现已因用户决策收回。赛题规则已全部回填至 runtime-constraints.md。 | 程千和 |
| 2026-07-11 | P1-01 完成（手册全文通读）；P1-04 环境侧完成（web_fetch.py + Playwright MCP + 双 python）；tech-debt 全量废弃 | 程千和 |
| 2026-07-11 | 补充手册路线图、汇合点表、P1/P2/P3 按人细化检查清单、P0-06~P0-08 完成 | 程千和 |
| 2026-07-10 | 初始工程计划建立；P0 全部完成；P1 开始 | 程千和 |