# Docker 部署指南 (Docker Deployment Guide)

> 本文是 FPGA Agent 的 Docker 完整使用文档，涵盖：构建镜像、运行 agent、配置模型接入点（endpoint）、模型 ID 和 API key。
>
> This is the complete Docker guide for the FPGA Agent: building the image, running the agent, and configuring the model endpoint, model ID, and API key.

---

## 目录

- [1. 概述](#1-概述)
- [2. 前置条件](#2-前置条件)
- [3. 构建镜像](#3-构建镜像)
- [4. 配置模型接入点、ID 和 API Key](#4-配置模型接入点id-和-api-key)
- [5. 运行 Agent](#5-运行-agent)
- [6. 镜像内部结构](#6-镜像内部结构)
- [7. 常见问题](#7-常见问题)

---

## 1. 概述

FPT'26 Track A 要求提交物能在 Docker 环境中 build 和 run。本镜像包含：

| 组件 | 说明 |
|------|------|
| Ubuntu 22.04 | 基础系统 |
| Vitis HLS 运行时依赖 | 镜像官方 `vitis.dockerfile` 依赖层 |
| Python 3.12 + textual/rich | agent 运行环境 + TUI 仪表盘 |
| Agent 源码 + 官方 harness | `/opt/fpga-agent/` |

**Vitis 2025.2 本身不打进镜像**（~92 GB，license 绑定），而是从宿主机只读挂载——这正是官方 `run-vitis.sh` 的模型。

```
┌─────────────────────────────────────────────┐
│  Docker Container (fpga-agent)              │
│  ┌───────────────────────────────────────┐  │
│  │  /opt/fpga-agent/                     │  │
│  │    agent/    tui/    scripts/         │  │
│  │    contest/fpt26-harness/             │  │
│  │  Python 3.12 venv (textual + rich)    │  │
│  └───────────────────────────────────────┘  │
│         │ bind-mount (read-only)            │
│         ▼                                    │
│  /home/<user>/Xilinx/  ← 宿主机 Vitis 树    │
└─────────────────────────────────────────────┘
        │
        ▼  HTTPS
   LLM API endpoint (DeepSeek / Qwen / ...)
```

---

## 2. 前置条件

### 2.1 宿主机要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux（Ubuntu 22.04 推荐） |
| Docker | 已安装并运行（`docker info` 正常） |
| Vitis HLS | 2025.2 已安装（默认路径见下方） |
| 磁盘空间 | 镜像 ~3 GB + 运行产物 |
| API Key | 至少一个 LLM 服务的 API key（见第 4 节） |

### 2.2 Vitis 路径

Vitis 2025.2 的 `settings64.sh` 所在目录。默认：

```
/home/admin/Xilinx/2025.2/Vitis
```

如果你的 Vitis 装在别处，用 `VITIS_ROOT` 环境变量覆盖。

### 2.3 API Key

运行真 LLM 修复（`--backend deepseek`）需要 API key。获取方式：

- **DeepSeek**: 在 https://platform.deepseek.com 注册，创建 API key（`sk-...` 格式）
- **阿里云 MaaS (Qwen)**: 在 https://dashscope.aliyun.com 开通服务，创建 API key
- **其他 OpenAI 兼容端点**: 任意兼容 OpenAI chat completions 格式的服务

---

## 3. 构建镜像

```bash
cd fpga-agent
docker build -t fpga-agent:0.8.1 .
```

构建过程约 5-10 分钟（取决于网络速度，主要是 apt 依赖安装）。

> **镜像源说明**：Dockerfile 使用清华 PyPI 镜像加速 pip 安装。如果你的网络环境无法访问清华源，修改 Dockerfile 第 86-90 行的 `-i` 参数为官方源或其他镜像。

验证构建成功：

```bash
docker run --rm fpga-agent:0.8.1 --help
```

应输出 `run_agent.py` 的帮助信息。

---

## 4. 配置模型接入点、ID 和 API Key

这是最重要的配置步骤。FPGA Agent 的 LLM 客户端（`agent/deepseek_client.py`）通过**环境变量**读取所有模型配置，支持任意 OpenAI 兼容端点。

### 4.1 环境变量一览

| 环境变量 | 必填 | 默认值 | 说明 |
|----------|------|--------|------|
| `DEEPSEEK_API_KEY` | 是* | — | API key（DeepSeek 原生 key） |
| `LLM_API_KEY` | 是* | — | 通用 API key（优先于 `DEEPSEEK_API_KEY`） |
| `LLM_BASE_URL` | 否 | `https://api.deepseek.com/v1/chat/completions` | 模型接入点 URL |
| `LLM_MODEL` | 否 | `deepseek-v4-pro` | 模型 ID |
| `LLM_THINKING` | 否 | `deepseek` | 思考模式：`deepseek` / `enable_thinking` / `none` |
| `LLM_TEMPERATURE` | 否 | `0.2` | 采样温度 |
| `LLM_TIMEOUT` | 否 | `300` | 请求超时（秒），大模型建议 `600` |
| `LLM_MAX_RETRIES` | 否 | `3` | 瞬时失败重试次数 |
| `VITIS_ROOT` | 否 | `/home/admin/Xilinx/2025.2/Vitis` | 宿主机 Vitis 安装路径 |

> \* `DEEPSEEK_API_KEY` 和 `LLM_API_KEY` 二选一。客户端先查 `LLM_API_KEY`，未设置则回退到 `DEEPSEEK_API_KEY`。

### 4.2 配置方式一：.env 文件（推荐）

在仓库根目录创建 `.env` 文件（已 gitignore，不会入库）：

```bash
cp .env.example .env
# 然后编辑 .env，填入你的 key
```

`.env` 文件示例（DeepSeek V4 Pro）：

```bash
export DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

`docker-run.sh` 会自动读取 `.env` 并通过 `-e` 传递给容器。

### 4.3 配置方式二：环境变量直接传递

不使用 `.env` 文件，直接在命令行设置：

```bash
# DeepSeek V4 Pro
DEEPSEEK_API_KEY=sk-your-key ./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

### 4.4 各模型的完整配置示例

#### DeepSeek V4 Pro（原生端点，最简配置）

`.env`:
```bash
export DEEPSEEK_API_KEY=sk-your-deepseek-key
```

只需一个 key，其他都用默认值：
- 端点：`https://api.deepseek.com/v1/chat/completions`（内置默认）
- 模型 ID：`deepseek-v4-pro`（内置默认）
- 思考模式：`deepseek`（内置默认）

#### Qwen3.5 122B（阿里云 MaaS）

`.env`:
```bash
export LLM_API_KEY=sk-your-aliyun-key
export LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
export LLM_MODEL=qwen3.5-122b-a10b
export LLM_THINKING=enable_thinking
export LLM_TIMEOUT=600
```

#### Qwen3.6 27B（阿里云 MaaS）

`.env`:
```bash
export LLM_API_KEY=sk-your-aliyun-key
export LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
export LLM_MODEL=qwen3.6-27b
export LLM_THINKING=enable_thinking
```

#### 其他 OpenAI 兼容端点（vLLM / Ollama / OpenRouter 等）

```bash
export LLM_API_KEY=your-key-or-dummy
export LLM_BASE_URL=http://your-server:8000/v1/chat/completions
export LLM_MODEL=your-model-name
export LLM_THINKING=none
```

> `LLM_THINKING=none` 适用于不支持 `thinking` 字段的端点（某些 MaaS 网关会拒绝未知字段）。

### 4.5 Docker 中传递环境变量的原理

`docker-run.sh` 做了以下处理：

1. 如果 `DEEPSEEK_API_KEY` 环境变量已设置 → 直接传给容器
2. 否则如果 `.env` 文件存在 → source 它提取 key → 传给容器
3. API key 通过 `docker run -e` 传入，**绝不打入镜像**

如需传递额外的 `LLM_*` 环境变量（如切换到 Qwen），可以手动 `docker run`：

```bash
docker run --rm \
    -e LLM_API_KEY=sk-your-key \
    -e LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
    -e LLM_MODEL=qwen3.6-27b \
    -e LLM_THINKING=enable_thinking \
    -v /home/admin/Xilinx:/home/admin/Xilinx:ro \
    -e LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis \
    -v $(pwd)/runs:/opt/fpga-agent/runs \
    fpga-agent:0.8.1 \
    contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

---

## 5. 运行 Agent

### 5.1 CLI 模式（无 TUI，最常用）

```bash
# 脚本后端（不花 token，验证工具链）
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix

# 真 LLM 修复（花 token，需要 API key）
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# 限制 budget（小预算测试）
./docker-run.sh contest/fpt26-harness/tasks/dotProduct_optimize --backend deepseek --budget 10

# 指定 token 节省模式
./docker-run.sh contest/fpt26-harness/tasks/vecadd_optimize --backend deepseek --token-mode balanced
```

`docker-run.sh` 自动完成：
1. 挂载宿主机 Xilinx 目录树到容器内相同路径（只读）
2. 传递 `DEEPSEEK_API_KEY`（或从 `.env` 读取）
3. 挂载 `runs/` 输出目录（持久化到宿主机）
4. 调用 `scripts/run_agent.py`

### 5.2 TUI 模式（交互式仪表盘）

```bash
./docker-run.sh --tui contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

TUI 需要终端（`-it`），`docker-run.sh --tui` 已自动处理。

### 5.3 可用任务列表

```bash
ls contest/fpt26-harness/tasks/
# projection_bugfix   dotProduct_optimize   residual_stream_deadlock
```

### 5.4 运行输出

每次运行产出：

| 输出 | 位置 | 说明 |
|------|------|------|
| 实时日志 | stderr | 事件流（route/tool_result/review/checkpoint） |
| Transcript | stdout | 工具调用序列 + credit 消耗 |
| 评分卡 | stdout | SCORE + 正确性/synth/PPA |
| JSONL 日志 | `runs/<task_id>/<task_id>.jsonl` | 结构化事件，可用 `jq` 分析 |
| 最终代码 | `runs/<task_id>/final_<kernel>.cpp` | 提交的最终 kernel |
| 评分历史 | `runs/<task_id>/scores.jsonl` | 跨运行 SCORE 趋势 |

### 5.5 run_agent.py 完整参数

```bash
python3 scripts/run_agent.py <task_dir> [options]

选项：
  --backend {scripted,deepseek,openrouter}   LLM 后端（默认 scripted）
  --budget N                                 覆盖 credit 预算
  --work DIR                                 工作目录（默认 runs/<task_id>）
  --force                                    无 Vitis 时强制运行（csim 会失败）
  --token-mode {full,balanced,aggressive}    token 节省模式（默认 full）
```

---

## 6. 镜像内部结构

| 路径（容器内） | 说明 |
|----------------|------|
| `/opt/fpga-agent/` | 项目根（agent/ + tui/ + scripts/ + contest/） |
| `/opt/venv/` | Python 3.12 虚拟环境（textual + rich） |
| `/home/admin/Xilinx/` | 宿主机 Xilinx 树挂载点（只读，运行时注入） |
| `/opt/fpga-agent/runs/` | 运行产物输出（挂载到宿主机，持久化） |

关键环境变量（Dockerfile 内设置）：

| 变量 | 值 | 说明 |
|------|----|------|
| `LLM4HLS_VITIS_HLS_ROOT` | `/home/admin/Xilinx/2025.2/Vitis` | harness 定位 Vitis |
| `LLM4HLS_TASKS_ROOT` | `/opt/fpga-agent/contest/fpt26-harness/tasks` | 任务目录 |
| `PATH` | `/opt/venv/bin:$PATH` | Python 3.12 优先 |

运行用户为非 root 用户 `agent`（uid 1000），拥有免密 sudo。

---

## 7. 常见问题

### Q: 报错 "Vitis root not found at /home/admin/Xilinx/2025.2/Vitis"

A: Vitis 安装路径不是默认值。设置 `VITIS_ROOT` 环境变量：

```bash
VITIS_ROOT=/your/path/to/Vitis ./docker-run.sh ...
```

### Q: 报错 "API key missing. Set LLM_API_KEY or DEEPSEEK_API_KEY"

A: 没有配置 API key。二选一：
1. 在仓库根目录创建 `.env` 文件（参考 `.env.example`）
2. 在命令行直接传递：`DEEPSEEK_API_KEY=sk-... ./docker-run.sh ...`

### Q: 报错 "vitis-run not found"

A: 容器内找不到 Vitis。确认：
1. 宿主机已安装 Vitis 2025.2
2. `VITIS_ROOT` 路径正确（指向包含 `settings64.sh` 的目录）
3. 该路径下的 `settings64.sh` 文件存在

### Q: LLM 返回空 content

A: 推理模型的 reasoning 可能吃光了 max_tokens。保持 `max_tokens` 不设置（默认 None，不限制）即可。如果仍有问题，尝试增大 `LLM_TIMEOUT`。

### Q: 如何切换到 Qwen 模型？

A: 设置 `LLM_*` 环境变量（见第 4.4 节）。注意 `--backend deepseek` 参数名虽然叫 deepseek，但实际上它实例化的是 `DeepSeekClient`，该客户端完全支持通过环境变量切换到任意 OpenAI 兼容端点。

### Q: 如何查看容器内的 LLM 配置是否正确？

A: 进入容器检查：

```bash
docker run --rm -it \
    -e DEEPSEEK_API_KEY=sk-your-key \
    fpga-agent:0.8.1 \
    bash -c 'echo "API_KEY set: ${DEEPSEEK_API_KEY:+yes}" && echo "BASE_URL: ${LLM_BASE_URL:-default(deepseek)}" && echo "MODEL: ${LLM_MODEL:-default(deepseek-v4-pro)}"'
```

### Q: runs/ 目录在哪？

A: `docker-run.sh` 会自动将宿主机的 `./runs/` 挂载到容器的 `/opt/fpga-agent/runs/`。运行产物会直接出现在宿主机的 `runs/` 目录下，容器删除后依然保留。
