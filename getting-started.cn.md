> [English](getting-started.md)

# 快速入门指南 (Getting Started)

> 面向新加入的开发者（或未来的自己）。5 分钟读完，知道怎么装、怎么跑、代码怎么读。

---

## 1. 环境要求

| 项目 | 要求 |
|---|---|
| OS | Linux（Ubuntu 22.04 推荐）。Windows 不支持加速流 |
| Python | 3.11+（需要 tomllib 标准库）。推荐 3.12 |
| Vitis | 2025.2（仅真 csim/synth/cosim 需要；离线开发不需要） |
| LLM API | DeepSeek V4 Pro（或 OpenRouter 开源模型） |

**不需要的东西**：GPU、数据库、消息队列、Web 服务器。

---

## 2. 安装

项目有两台机器：**本机**（开发，没装 Vitis）和**服务器 QFS-STATION**（装了 Vitis）。

### 2.1 本机：框架测试（无 Vitis，csim 会失败）

```bash
# 本机操作
git clone git@gitee.com:QFcattail/fpga-agent.git
cd fpga-agent

# 创建 venv（需要 Python 3.11+）
python3.12 -m venv .venv
source .venv/bin/activate    # 激活后 python 指向 venv 里的 3.12

# 无需 pip install -- harness 和 agent 都只用 Python 标准库

# 不装 Vitis 时跑会报错退出（driver 检测 vitis-run 不在 PATH）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix
# -> ERROR: vitis-run not found

# 如果只想测框架链路（csim 会 compile_error），加 --force
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force
```

### 2.2 服务器：真 Vitis + 真 LLM（完整端到端）

服务器 QFS-STATION 已装好 Vitis 2025.2 和 venv，这是**实际跑 agent 的地方**。

```bash
# 本机 SSH 进服务器
ssh QFS-STATION
cd /home/admin/fpga-agent

# 每次开新终端都要做这三步：
source /home/admin/Xilinx/2025.2/Vitis/settings64.sh   # Vitis 工具链
source .env                                              # DeepSeek API key
source /home/admin/venv-fpga/bin/activate               # Python 3.12 venv

# 现在可以跑了（csim 真编译执行，约 10 秒）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# 用 DeepSeek 做 LLM 修复（完整端到端）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

> **提示**：每次开新终端都要 source 这三行。嫌麻烦可以写进 `~/.bashrc`，
> 但 Vitis 的 settings64.sh 会改 PATH，写进 bashrc 可能影响其他程序。

---

## 3. CLI 用法

### 3.1 命令格式

```bash
python3 scripts/run_agent.py <task_dir> [选项]
```

### 3.2 选项

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--backend` | `scripted` | LLM 后端：`scripted`（预设答案）/ `deepseek`（真 LLM）/ `openrouter`（官方） |
| `--budget` | 题目自带 | 覆盖 credit 预算（如 `--budget 10`） |
| `--work` | `runs/<task_id>` | 工作目录（存 build 产物 + 日志） |
| `--force` | 关 | 没装 Vitis 时强制运行（csim 会 compile_error，仅用于框架测试） |

### 3.3 常用命令

以下命令在**服务器 QFS-STATION**上跑（已 source Vitis + .env + venv）：

```bash
# 真 Vitis + ScriptedClient（验证工具链，不花 token）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# 真 Vitis + DeepSeek（完整端到端，花 token）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# 限制 budget（小预算测试）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/dotProduct_optimize --backend deepseek --budget 10

# 三道题都跑
for t in projection_bugfix dotProduct_optimize residual_stream_deadlock; do
    python3 scripts/run_agent.py contest/fpt26-harness/tasks/$t --backend deepseek
done
```

本机只有 `--force` 能跑（无 Vitis，csim 会 compile_error）：

```bash
# 本机，框架测试用
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force
```

### 3.4 输出怎么读

每次运行产出三块输出：

**① 运行日志（stderr，实时）**：
```
[log] route {'task_type': 'repair', 'correctness_stages': ['csim'], ...}
[log] tool_result {'kind': 'csim', 'phase': 'runtime_fail', 'credit_spent': 1}
[log] mechanical_review {'passed': True, 'issues': []}
[log] review {'verdict': 'pass', 'retry': 0}
[log] checkpoint {'old': 0, 'new': 1, 'reason': 'correctness_gate'}
```

**② Transcript（stdout，跑完打印）**：
```
--- metered tool transcript ---
  #1  [csim] runtime_fail (rc=1, 9.7s)   [spent 1/10]
  #2  [csim] pass (rc=0, 9.7s)          [spent 2/10]
  #3  [synth] pass (rc=0, 23.6s)        [spent 6/10]
  budget 6/10 credits spent (csimx2, synthx1)
```

**③ 评分卡（stdout，跑完打印）**：
```
=== Scorecard: projection_bugfix (difficulty 2) ===
  functional (hidden TB): PASS
  synthesizable         : PASS
  SCORE                 : 1.400
```

**④ JSONL 日志文件**（`runs/<task_id>/<task_id>.jsonl`）：结构化事件，事后用 `jq` 分析。

---

## 4. 代码怎么读

代码导览（模块职责、调用关系、阅读五遍法、函数清单）在 **[agent/README.md](agent/README.cn.md)**，和代码放一起。

快速一句话理解每个模块：

| 比喻 | 文件 | 职责 |
|---|---|---|
| **大脑** | `agent/main_loop.py` | 主循环：correctness → synth → optimize |
| **决策** | `agent/router.py` | 读题目类型，选关卡路径 |
| **记忆** | `agent/checkpoint.py` | 存档：哪个版本最好 |
| **感知** | `agent/feedback.py` | 从工具日志提取错误信息 |
| **手** | `agent/llm_client.py` | 调 LLM 改代码 |
| **眼** | `agent/mechanical_checks.py` | 机械检查（不靠 LLM） |
| **嘴** | `agent/deepseek_client.py` | DeepSeek API 对接 |
| **日记** | `agent/observability.py` | 日志 + 心跳 |
| **字典** | `agent/knowledge_base/` | bug→修法知识库 |
| **工具** | `contest/fpt26-harness/` | 官方 harness（csim/synth/cosim） |
- **main_loop**："把上面所有模块串起来，修到 csim 过，再 synth，再 optimize。"

---

## 5. 常见问题

### Q: 报错 "vitis-run not found" 怎么办？

A: 没装 Vitis 或没 source settings64.sh。driver 现在会拒绝运行并给出提示，避免输出误导性的 SCORE 0.000。装好 Vitis 并 source 后即可。如果只想测框架链路（csim 会 compile_error），加 `--force`。

### Q: DeepSeek 返回空 content 怎么办？

A: deepseek-v4-pro 是推理模型。max_tokens 默认不设（不限制，让模型想够）。如果手动设了 max_tokens 且太小，reasoning 会把预算吃光，content 为空。保持默认（None）即可。

### Q: review 全 reject 怎么办？

A: ScriptedClient 不懂 review 语义，返回的代码不以 PASS 开头，所以判 reject。这是预期的——用真 LLM（deepseek backend）就不会。

### Q: SCORE 是 0 怎么办？

A: 检查：(1) csim 过了没？(2) hidden testbench 过了没？correctness 不过直接 0 分。先确保 csim 过，再查 synth。

### Q: 怎么加知识库条目？

A: 编辑 `agent/knowledge_base/entries.json`（JSON 语料，22 条，字段：id/symptom/root_cause/fix/example/signatures）。保存即生效——`seed_entries()` 启动时从该文件加载。signatures 用小写错误码/关键词短串（检索是大小写不敏感子串匹配）。

---

## 6. 开发环境配置

### 6.1 本地（开发机）

```bash
# .venv
python3.12 -m venv .venv
source .venv/bin/activate

# 环境变量（.env，已 gitignore）
echo 'export DEEPSEEK_API_KEY=sk-xxx' > .env

# IDE：VS Code / PyCharm 均可
# 推荐：开 agent-architecture.md 的 Mermaid 图对照读代码
```

### 6.2 服务器 QFS-STATION（真 Vitis，实际跑 agent 的地方）

```bash
# 本机 SSH 进服务器
ssh QFS-STATION
cd /home/admin/fpga-agent

# 每次开新终端都要 source 这三行：
source /home/admin/Xilinx/2025.2/Vitis/settings64.sh   # Vitis 工具链
source .env                                              # DeepSeek API key
source /home/admin/venv-fpga/bin/activate               # Python 3.12 venv

# 现在可以直接用 python（指向 venv 里的 3.12）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

### 6.3 代码同步到服务器

```bash
# 从本地推到服务器（不经过 git）
rsync -az --exclude='.git' --exclude='runs/' --exclude='__pycache__' --exclude='.env' \
  agent/ scripts/ QFS-STATION:/home/admin/fpga-agent/
```

---

## 7. Docker 部署（提交评测用）

> 赛题（FPT'26 Track A）要求"提交物能在 Docker 环境中 build 和 run"。本节说明如何构建镜像、在容器内跑 agent。Vitis 2025.2 不打进镜像（~92G，license 绑定），而是从宿主机只读挂载--这正是官方 `run-vitis.sh` 的模型。

### 7.1 前提

- 宿主机已装 Docker，且已装 Vitis 2025.2（默认路径 `/home/admin/Xilinx/2025.2/Vitis`，可用 `VITIS_ROOT` 环境变量覆盖）。
- DeepSeek API key（`DEEPSEEK_API_KEY` 环境变量，或仓库根 `.env` 文件）--仅 `--backend deepseek` 需要。

### 7.2 构建镜像

```bash
cd fpga-agent
docker build -t fpga-agent:0.7.4 .
```

镜像包含：Ubuntu 22.04 + Vitis 依赖库（镜像官方 `vitis.dockerfile`）+ Python 3.12 + textual/rich（TUI）+ agent 源码 + harness。不含 Vitis 本体（运行时挂载）。

### 7.3 运行（CLI 模式）

```bash
# 跑一道题（scripted 后端，不花 token，验证链路）
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix

# DeepSeek 真修复（花 token）
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

`docker-run.sh` 自动完成：挂载**整个 Xilinx 目录树**到容器内相同路径（只读，Vitis settings64.sh 硬编码兄弟目录绝对路径，必须保持路径一致）-> 传 `DEEPSEEK_API_KEY` -> 挂载 `runs/` 输出目录 -> 调用 `scripts/run_agent.py`。

> **实测验证（2026-07-22）**：QFS-STATION 上 build 成功，容器内跑通 projection_bugfix（SCORE 1.400）+ dotProduct_optimize（SCORE 3.000 满分），csim/synth 真跑非 mock，SCORE 与宿主机一致。

### 7.4 运行（TUI 模式）

```bash
./docker-run.sh --tui contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

TUI 需要终端（`-it`），`docker-run.sh --tui` 已处理。

### 7.5 镜像结构

| 路径（容器内） | 说明 |
|---|---|
| `/opt/fpga-agent/` | 项目根（agent/ + tui/ + scripts/ + contest/fpt26-harness/） |
| `/home/admin/Xilinx/` | 宿主机整个 Xilinx 树挂载点（只读，运行时注入；保持宿主机路径因 settings64.sh 硬编码兄弟目录） |
| `/opt/fpga-agent/runs/` | 运行产物输出（挂载到宿主机，持久化） |
| `LLM4HLS_VITIS_HLS_ROOT` | 环境变量 = `/home/admin/Xilinx/2025.2/Vitis`（harness config.py 定位 Vitis） |

### 7.6 在 QFS-STATION 服务器上构建

服务器有 Vitis + 466G 数据盘，是实际 build 镜像的地方：

```bash
ssh QFS-STATION
cd /home/admin/fpga-agent
git pull   # 拉取 Dockerfile + docker-run.sh
docker build -t fpga-agent:0.7.4 .
# 服务器默认 VITIS_ROOT=/home/admin/Xilinx/2025.2/Vitis，无需额外设置
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

---

## 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-15 | v1 初稿。 | Agent 主 |
