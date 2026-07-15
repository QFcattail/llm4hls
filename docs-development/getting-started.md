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

### 2.1 不装 Vitis 也能开发（离线模式）

harness 自带 ScriptedClient，用预设答案模拟工具调用。大部分 agent 代码（路由器、存档、反馈构建、LLM 封装、日志）不依赖 Vitis。

```bash
# 克隆
git clone git@gitee.com:QFcattail/fpga-agent.git
cd fpga-agent

# Python 3.12 venv
python3.12 -m venv .venv
source .venv/bin/activate

# 无需 pip install —— harness 和 agent 都只用 Python 标准库

# 跑离线（不需要 Vitis、不需要 API key）
python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix
```

看到 `budget 6/20 credits spent` + `SCORE 0.000`（因为没 Vitis，csim 全 compile_error）——框架跑通了。

### 2.2 接真 Vitis（真 csim/synth/cosim）

需要 Vitis 2025.2 装在 Linux 上。配置环境变量：

```bash
export LLM4HLS_VITIS_HLS_ROOT=/path/to/Xilinx/2025.2/Vitis
source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh
```

再跑同样的命令，这次 csim 会真编译执行（约 10 秒），不再 compile_error。

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
| `--backend` | `scripted` | LLM 后端：`scripted`（离线）/ `deepseek`（真 LLM）/ `openrouter`（官方） |
| `--budget` | 题目自带 | 覆盖 credit 预算（如 `--budget 10`） |
| `--work` | `runs/<task_id>` | 工作目录（存 build 产物 + 日志） |

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

### 4.1 推荐阅读顺序

按**从外到内、从简单到核心**的顺序：

```
第一遍（了解全貌）：
  1. docs-development/design/agent-architecture.md     ← 架构设计（先看 Mermaid 图）
  2. scripts/run_agent.py                              ← 入口，看怎么组装
  3. agent/main_loop.py 的 run() 方法                  ← 主循环骨架

第二遍（看数据结构）：
  4. agent/router.py                                   ← RunPlan 是什么
  5. agent/checkpoint.py                               ← Level/Checkpoint 三规则
  6. agent/feedback.py                                 ← Feedback 数据结构

第三遍（看核心逻辑）：
  7. agent/main_loop.py 的 _reach_correctness          ← 修复循环
  8. agent/main_loop.py 的 _repair_with_review         ← 双层 review
  9. agent/mechanical_checks.py                        ← 硬性检查
  10. agent/llm_client.py 的 repair/review             ← LLM 调用

第四遍（看基建）：
  11. agent/observability.py                           ← 日志+心跳
  12. agent/deepseek_client.py                         ← API 对接
  13. agent/knowledge_base/retriever.py                ← RAG 检索

第五遍（看外部依赖）：
  14. contest/fpt26-harness/llm4hls/harness.py         ← ToolServer
  15. contest/fpt26-harness/llm4hls/tools.py           ← CSimTool/SynthTool
  16. contest/fpt26-harness/llm4hls/scoring.py         ← 评分公式
```

### 4.2 代码分几个部分

| 部分 | 文件 | 一句话 |
|---|---|---|
| **入口** | `scripts/run_agent.py` | CLI 入口，组装 agent |
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

### 4.3 一句话理解每个模块

- **router**："这道题是 repair 还是 optimize？要不要 cosim？"
- **checkpoint**："这个新版本比之前的好吗？好的话存下来。"
- **feedback**："csim 跑挂了，把错误信息整理成 LLM 能看懂的。"
- **llm_client**："给 LLM 源码+反馈+知识库，让它改代码。改完再审一遍。"
- **mechanical_checks**："签名变没变？include 还在吗？"（不信任 LLM 的地方）
- **deepseek_client**："调 DeepSeek API，记 token。"
- **observability**："agent 现在在哪一步？卡死了吗？"
- **knowledge_base**："这个错误码之前见过吗？怎么修的？"
- **main_loop**："把上面所有模块串起来，修到 csim 过，再 synth，再 optimize。"

---

## 5. 常见问题

### Q: csim 全是 compile_error 怎么办？

A: 没装 Vitis 或没 source settings64.sh。离线开发时这是正常的（ScriptedClient 也会这样，因为 vitis-run 找不到）。配好 `LLM4HLS_VITIS_HLS_ROOT` + source settings 后就好。

### Q: DeepSeek 返回空 content 怎么办？

A: deepseek-v4-pro 是推理模型，max_tokens 太小会全被 reasoning 吃掉。默认 16384，如果代码长可能需要更大。

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
