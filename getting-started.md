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

### 2.1 不装 Vitis 也能开发（框架测试）

harness 自带 ScriptedClient，用预设答案模拟 LLM 调用。agent 代码本身（路由器、存档、反馈构建、日志）不依赖 Vitis。但 **csim/synth/cosim 调用需要 Vitis**——没装时会直接报错退出，避免输出误导性的 SCORE 0.000。

```bash
# 克隆
git clone git@gitee.com:QFcattail/fpga-agent.git
cd fpga-agent

# Python 3.12 venv
python3.12 -m venv .venv
source .venv/bin/activate

# 无需 pip install —— harness 和 agent 都只用 Python 标准库

# 不装 Vitis 时跑会报错退出（driver 检测 vitis-run 不在 PATH）
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix
# → ERROR: vitis-run not found

# 如果只想测框架链路（csim 会 compile_error），加 --force
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force
```

### 2.2 接真 Vitis（真 csim/synth/cosim）

需要 Vitis 2025.2 装在 Linux 上。配置环境变量：

```bash
export LLM4HLS_VITIS_HLS_ROOT=/path/to/Xilinx/2025.2/Vitis
source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh
```

再跑同样的命令（不加 --force），这次 csim 会真编译执行（约 10 秒）。

### 2.3 接真 LLM（DeepSeek）

API key 放在 `.env` 文件里（**已 gitignore，不入库**）：

```bash
# .env
export DEEPSEEK_API_KEY=sk-你的key

# 用法
source .env
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

---

## 3. CLI 用法

### 3.1 命令格式

```bash
python scripts/run_agent.py <task_dir> [选项]
```

### 3.2 选项

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--backend` | `scripted` | LLM 后端：`scripted`（预设答案）/ `deepseek`（真 LLM）/ `openrouter`（官方） |
| `--budget` | 题目自带 | 覆盖 credit 预算（如 `--budget 10`） |
| `--work` | `runs/<task_id>` | 工作目录（存 build 产物 + 日志） |
| `--force` | 关 | 没装 Vitis 时强制运行（csim 会 compile_error，仅用于框架测试） |

### 3.3 常用命令

```bash
# 离线跑（不花 token，不依赖 Vitis）
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# 真 Vitis + ScriptedClient（验证工具链，不花 token）
export LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis
source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# 真 Vitis + DeepSeek（完整端到端）
source .env
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# 限制 budget（小预算测试）
python scripts/run_agent.py contest/fpt26-harness/tasks/dotProduct_optimize --backend deepseek --budget 10

# 三道题都跑
for t in projection_bugfix dotProduct_optimize residual_stream_deadlock; do
    python scripts/run_agent.py contest/fpt26-harness/tasks/$t --backend deepseek
done
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

代码导览（模块职责、调用关系、阅读五遍法、函数清单）在 **[agent/README.md](agent/README.md)**，和代码放一起。

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

A: 在 `agent/knowledge_base/retriever.py` 的 KnowledgeBase 里 add KBEntry。格式见 `KBEntry` dataclass。或者创建 YAML 数据文件批量加载（待实现）。

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

### 6.2 服务器（真 Vitis）

```bash
# SSH（配好 ~/.ssh/config 后）
ssh QFS-STATION

# 环境
export LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis
source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh
cd /home/admin/fpga-agent
source .env
/home/admin/venv-fpga/bin/python scripts/run_agent.py ...
```

### 6.3 代码同步到服务器

```bash
# 从本地推到服务器（不经过 git）
rsync -az --exclude='.git' --exclude='runs/' --exclude='__pycache__' --exclude='.env' \
  agent/ scripts/ QFS-STATION:/home/admin/fpga-agent/
```

---

## 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-15 | v1 初稿。 | Agent 主 |
