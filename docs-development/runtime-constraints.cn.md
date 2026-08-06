> [English](runtime-constraints.md)

# 运行约束 (Runtime Constraints)

记录影响 agent 设计与运行的硬约束。**2026-07-14 第四次更新**：官方 harness（contest/fpt26-harness/）解压后，原"待确认事项"全部解决。评估接口、credit 预算、评分公式、Docker 规范均已明确，详见下文。

---

## 一、赛题规则（FPT'26 Track A: LLM4HLS Agent）

**竞赛**：FPT'26 Design Competition — Track A（fpt2026.uark.edu）

**已确认规则**（来源：Submission_Guidelines_Track-A.docx + 选题要求.md + 官方 harness + AMD 案例文章）：
- FPGA 平台：Alveo U55C `xcu55c-fsvh2892-2L-e`
- 软件版本：Vitis **2025.2**（HLS 通过 `vitis-run --mode hls` 调用，2025.2 已弃用独立 `vitis_hls`）
- 目标频率：**200 MHz（5 ns clock）**
- 必须通过 csim、cosim、synth
- **Token 消耗是终评重要指标**
- LLM 必须用**开源模型**（harness 强制，经 OpenRouter）。推荐三选一对比：
  - DeepSeek V4 Pro / Qwen3.5 122B A10B / Qwen3.6 27B（详见原计划）
- 隐藏测试集用于终评
- **Docker 环境**提交（harness 提供 `vitis.dockerfile`）
- 提交物：源码 + testbench + 补充材料（.zip）+ 演示视频（≤5分钟，需在目标平台运行）
- **correctness 优先于 PPA**

**Agent 需完成的端到端流程**（来源：选题要求.md）：
1. Interpretation：解读任务规格和初始代码
2. Generation/modification：生成或修改 HLS C/C++ 代码（含 pragma）
3. Invocation：调用工具反馈接口
4. Parsing：解析日志和报告，诊断问题
5. Prioritization：correctness 优先，再做 PPA
6. Termination：在预算内终止

---

## 二、官方 Harness（已解压，权威来源）

**位置**：`contest/fpt26-harness/`

官方 harness 是参考实现 + 评估工具，**全 Python 标准库**（requirements.txt 为空，无第三方依赖）。它一次性回答了原"待确认事项"的全部问题。

### 2.1 评估接口（原待确认项 1，已解决）

**进程内 Python 函数调用**，不是 MCP / HTTP / 命令行接口。agent 通过 `ToolServer` 调用三个工具：

```python
server.csim(kernel_code)  -> ToolResult   # costs 1 credit
server.synth(kernel_code) -> ToolResult   # costs 4 credits, .report 有 PPA
server.cosim(kernel_code) -> ToolResult   # costs 20 credits, .cosim 有 measured latency
```

agent 只提供 kernel 源码；headers 和 testbench 由 harness 固定。每次调用计入 budget 并写入审计 transcript。

**底层实现**（`vitis.py`）：`source /opt/xilinx/2025.2/Vitis/settings64.sh && vitis-run --mode hls --tcl run_hls.tcl`，用 subprocess 跑，工具崩了不拖垮 agent（进程隔离已满足）。

### 2.2 Credit 预算（原待确认项 2，已解决）

| 工具 | credit 成本 | 超时 |
|---|---|---|
| csim | 1 | 180s |
| synth | 4 | 600s |
| cosim | 20 | 900s |

每题 budget 在 `task.toml` 的 `budget` 字段定义。示例题：projection=20、dotProduct=40、residual=80。超 budget 抛 `BudgetExceeded`，agent 强制停。

**关键：credit 不跨题累积，单题内省下 credit 无奖励（分数只取决于达到哪关）。** 真正影响评分的"省"是 token，不是 credit。

### 2.3 评分公式（原待确认项，已解决）

`scoring.py:144-149`，correctness 是硬门槛：

```python
if not functional_pass:                    # hidden testbench 没过
    score = 0.0
else:
    ppa_norm = min(acceleration, 8) / 8
    quality = 0.5 * correct + 0.2 * synth_pass + 0.3 * ppa_norm
    score = difficulty * quality
```

`functional_pass = hidden_csim.ok and (cosim_pass is not False)`。

**评分用 hidden testbench，在 agent budget 之外运行（不花 agent credit）。** 详见 `docs-development/design/agent-architecture.md` §1。

### 2.4 Task 包格式

```
<task>/
  task.toml            # spec: task_type, difficulty, budget, target, top fn
  description.md       # 接口契约 + 初始状态描述（官方设计文档）
  <kernel>.cpp         # agent 唯一能编辑的文件（起始代码，broken 或 slow）
  <kernel>.h           # header，fixed，agent 不能改
  <kernel>_tb.cpp      # PUBLIC testbench（agent 可 csim，metered）
  hidden/<kernel>_tb.cpp   # HIDDEN testbench（评分用，agent 不可见）
  reference/<kernel>.cpp   # golden solution（offline scripted agent baseline）
```

`task_type` ∈ `generate | repair | optimize | synth_fix`。另可设 `requires_cosim = true`（structural 题必须过 cosim 才算 correct）。

### 2.5 三道示例题

| 题 | task_type | difficulty | budget | bug 在哪关 |
|---|---|---|---|---|
| projection_bugfix | repair | 2 | 20 | csim（功能 bug） |
| dotProduct_optimize | optimize | 3 | 40 | 无 bug，冲 PPA |
| residual_stream_deadlock | structural | 4 | 80 | cosim（DATAFLOW 死锁） |

### 2.6 Docker 规范（原待确认项 4，已解决）

harness 提供 `vitis.dockerfile`（Vitis 2025.2 环境）和 `run-vitis.sh`（容器内运行脚本）。

---

## 三、已探明的本地环境事实

- **网络出口**：本机 Bash 有完整网络出口（curl / python urllib / pip / npm registry 均可联网）。
  harness 内置 `WebFetch` 受域名验证限制，用自写 `tools/web_fetch.py`（Bash + requests + html2text）绕过。
- **Python 运行时**：conda `python3` **3.13**（`/home/GPUclaude/miniconda3/bin/python3`）+ 系统 `python3` 3.10。
  harness 已验证可在 3.13 跑通 ScriptedClient 离线链路（task 加载、budget 计费、transcript、评分卡全正常）。
- **LLM 大脑**：开源模型（DeepSeek V4 Pro / Qwen3.5 / Qwen3.6），经 OpenRouter。
  - 本环境内置智谱 GLM（`builtin:bigmodel`）可作开发调试
  - 具体 API key 待用户提供
- **开发平台**：Linux 主机 `gpuclaude`（8 核 Xeon Platinum，14GB 内存，/ 剩 14G、/home 剩 20G）
- **Git**：remote 为 `git@gitee.com:QFcattail/fpga-agent.git`，SSH 已生效

---

## 四、Vitis 2025.2 环境需求与部署

本机**磁盘不足**（两盘合计可用 34GB，Vitis 完整安装需 100-200GB），**无法本地安装 Vitis**。

### 4.1 系统要求（来源：UG1742 + 官方支持论坛）

| 项目 | 要求 |
|---|---|
| OS | **Linux**（Ubuntu 22.04 LTS 官方指定 / RHEL 9.x）。**Windows 不支持加速流**（Alveo U55C + Docker 提交必须 Linux）|
| 安装体积 | 完整 Vitis ~100-200GB；最小嵌入式/SDK ~15-35GB（但无独立 HLS 安装包，HLS 随 Vitis/Vivado 绑定装）|
| 内存 | 32GB 最低，64GB 推荐（我们的 kernel 是小设计，16GB 勉强可用）|
| CPU | 多核收益有限，4-8 核够 |
| GPU | **不需要**（cosim 是 CPU 跑的 RTL 仿真）|
| License | **HLS C 综合/仿真免 license**（UG1399 明确）；只有硬件实现需 Vivado license |

### 4.2 部署方案

- **方案（已定）**：用户租用云 Linux 服务器（Ubuntu 22.04，8 核 / 32GB / 200GB SSD，无 GPU），由 方欣语负责 Vitis 安装。用户将提供 SSH 授权。
- **成本估算**：约 200 元/月，实际间歇使用更低。比赛周期不足一月，成本可控。
- **离线开发（现在即可）**：ScriptedClient 跑通框架层（agent 主循环、知识库、prompt）不需 Vitis。

---

## 五、比赛时间线（已确认）

来源：FPT'26 竞赛页面（fpt2026.uark.edu）

| 阶段 | 截止日期 | 说明 |
|---|---|---|
| 报名截止 | 2026-07-07 (23:59 AoE) | 团队报名 |
| 提交截止 | **2026-08-07 (23:59 AoE)** | 技术材料提交 |
| 入围公布 | 2026-08-21 | 决赛名单公布 |

- 入围者需注册 FPT 2026 会议（Full Registration）并现场演示
- 可选在 IEEE FPT 2026 会议论文集中发表 2 页短文
- 评审标准：技术价值(40%) + 创新(20%) + 实用影响(20%) + 表达与复现(20%)

---

## 六、原"待确认事项"状态

| 原待确认项 | 状态 | 解决来源 |
|---|---|---|
| 1. 评估接口形式 | ✅ 已解决 | harness ToolServer（进程内函数调用） |
| 2. 工具调用预算额度 | ✅ 已解决 | csim=1 / synth=4 / cosim=20 credits，每题 task.toml 定义 |
| 3. 隐藏测试集规模/难度 | ✅ 部分解决 | harness 给 3 道公开示例题，隐藏集结构同此 |
| 4. Docker harness 规范 | ✅ 已解决 | harness 提供 vitis.dockerfile + run-vitis.sh |

---

## 七、AI 操作约束 (AI Operating Constraints)

> 任何 AI/人在动手前必须遵守以下纪律，违反会导致返工或误操作。

- **没做之前先读**：动手前先读 `requirements/`、`design/`、本约束、最新 `dev-log/`，不要基于假设操作。
- **写日志**：每完成一段实质工作，立刻补 `dev-log/`（模板见 `dev-log/README.md`），不要攒。
- **不擅自动手前先确认**：网络端口、安全降级、设备归属、服务器配置等约束类决策，先和用户确认。
- **不擅自推进阶段**：P1 评审没过，不偷偷开始 P2。阶段推进需用户/评审确认。
- **状态变更后验证**：TUI 状态变更后截图确认实际渲染（如可用），不只靠日志推断 UI。

---

## 八、版本号与界面截图 (Versioning & UI Screenshots)

### 8.1 版本号每次发布必更新（硬约束）

- 所有带界面的子项目，每次重新构建/部署前必须 bump 版本号，否则无法辨认跑的是新版还是旧版。
- 本项目版本号定义在 `agent/_version.py` 的 `__version__`，语义化版本（SemVer）格式 `MAJOR.MINOR.PATCH`。

| 改动类型 | bump 幅度 |
|---|---|
| 修了影响运行时行为的代码 | 至少 patch +1 |
| 新功能 | minor +1 |
| 仅文档/注释 | 可不 bump |

### 8.2 界面显示版本号

本项目的 TUI 仪表盘（`tui/`）是唯一带界面的子系统，**必须**在标题栏显示版本号。当排查问题时，版本号是确认"跑的是哪个版本"的唯一可靠途径。

### 8.3 截图与读图

TUI 运行在终端，无 GUI 截图需求。如需确认 TUI 渲染状态：
- 在终端运行 `./run.sh` 或 `python3 fpga-agent.py`，直接观察终端输出。
- 如需记录：用 `script` 命令录制终端会话，或终端截图工具。
- 当前环境无 headless GUI 截图需求（Vitis csim/synth/cosim 是命令行工具，输出为日志/报告）。
