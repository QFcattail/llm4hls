> [中文](README.cn.md)

# Docker Deployment Guide (Docker 部署指南)

> This is the complete Docker guide for the FPGA Agent: building the image, running the agent, and configuring the model endpoint, model ID, and API key.

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Prerequisites](#2-prerequisites)
- [3. Build the Image](#3-build-the-image)
- [4. Configure the Model Endpoint, ID, and API Key](#4-configure-the-model-endpoint-id-and-api-key)
- [5. Run the Agent](#5-run-the-agent)
- [6. Image Internal Structure](#6-image-internal-structure)
- [7. FAQ](#7-faq)

---

## 1. Overview

FPT'26 Track A requires that the submission can be built and run in a Docker environment. This image contains:

| Component | Description |
|------|------|
| Ubuntu 22.04 | Base system |
| Vitis HLS runtime dependencies | Dependency layer from the official `vitis.dockerfile` |
| Python 3.12 + textual/rich | agent runtime environment + TUI dashboard |
| Agent source code + official harness | `/opt/fpga-agent/` |

**Vitis 2025.2 itself is not baked into the image** (~92 GB, license-bound); instead it is bind-mounted read-only from the host -- this is exactly the model of the official `run-vitis.sh`.

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
│  /home/<user>/Xilinx/  ← host Vitis tree    │
└─────────────────────────────────────────────┘
        │
        ▼  HTTPS
   LLM API endpoint (DeepSeek / Qwen / ...)
```

---

## 2. Prerequisites

### 2.1 Host requirements

| Item | Requirement |
|------|------|
| Operating system | Linux (Ubuntu 22.04 recommended) |
| Docker | Installed and running (`docker info` works) |
| Vitis HLS | 2025.2 installed (default path below) |
| Disk space | Image ~3 GB + run artifacts |
| API Key | At least one LLM service API key (see Section 4) |

### 2.2 Vitis path

The directory containing `settings64.sh` for Vitis 2025.2. Default:

```
/home/admin/Xilinx/2025.2/Vitis
```

If your Vitis is installed elsewhere, override it with the `VITIS_ROOT` environment variable.

### 2.3 API Key

Running real LLM repair (`--backend deepseek`) requires an API key. How to obtain one:

- **DeepSeek**: Register at https://platform.deepseek.com and create an API key (`sk-...` format)
- **Alibaba Cloud MaaS (Qwen)**: Activate the service at https://dashscope.aliyun.com and create an API key
- **Other OpenAI-compatible endpoints**: Any service compatible with the OpenAI chat completions format

---

## 3. Build the Image

```bash
cd fpga-agent
docker build -t fpga-agent:0.8.1 .
```

The build process takes about 5-10 minutes (depending on network speed, mainly the apt dependency installation).

> **Mirror source note**: The Dockerfile uses the Tsinghua PyPI mirror to accelerate pip installation. If your network environment cannot access the Tsinghua mirror, change the `-i` argument on lines 86-90 of the Dockerfile to the official source or another mirror.

Verify the build succeeded:

```bash
docker run --rm fpga-agent:0.8.1 --help
```

It should print the help information for `run_agent.py`.

---

## 4. Configure the Model Endpoint, ID, and API Key

This is the most important configuration step. The FPGA Agent's LLM client (`agent/deepseek_client.py`) reads all model configuration via **environment variables** and supports any OpenAI-compatible endpoint.

### 4.1 Environment variable overview

| Environment variable | Required | Default | Description |
|----------|------|--------|------|
| `DEEPSEEK_API_KEY` | yes* | - | API key (native DeepSeek key) |
| `LLM_API_KEY` | yes* | - | Generic API key (takes precedence over `DEEPSEEK_API_KEY`) |
| `LLM_BASE_URL` | no | `https://api.deepseek.com/v1/chat/completions` | Model endpoint URL |
| `LLM_MODEL` | no | `deepseek-v4-pro` | Model ID |
| `LLM_THINKING` | no | `deepseek` | Thinking mode: `deepseek` / `enable_thinking` / `none` |
| `LLM_TEMPERATURE` | no | `0.2` | Sampling temperature |
| `LLM_TIMEOUT` | no | `300` | Request timeout (seconds); `600` recommended for large models |
| `LLM_MAX_RETRIES` | no | `3` | Number of retries on transient failures |
| `VITIS_ROOT` | no | `/home/admin/Xilinx/2025.2/Vitis` | Host Vitis installation path |

> \* Choose one of `DEEPSEEK_API_KEY` or `LLM_API_KEY`. The client checks `LLM_API_KEY` first; if unset, it falls back to `DEEPSEEK_API_KEY`.

### 4.2 Configuration method 1: .env file (recommended)

Create a `.env` file in the repo root (already gitignored, won't be committed):

```bash
cp .env.example .env
# Then edit .env and fill in your key
```

Example `.env` file (DeepSeek V4 Pro):

```bash
export DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

`docker-run.sh` automatically reads `.env` and passes it to the container via `-e`.

### 4.3 Configuration method 2: pass environment variables directly

Without using a `.env` file, set them directly on the command line:

```bash
# DeepSeek V4 Pro
DEEPSEEK_API_KEY=sk-your-key ./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

### 4.4 Complete configuration examples for each model

#### DeepSeek V4 Pro (native endpoint, minimal config)

`.env`:
```bash
export DEEPSEEK_API_KEY=sk-your-deepseek-key
```

Just one key; everything else uses defaults:
- Endpoint: `https://api.deepseek.com/v1/chat/completions` (built-in default)
- Model ID: `deepseek-v4-pro` (built-in default)
- Thinking mode: `deepseek` (built-in default)

#### Qwen3.5 122B (Alibaba Cloud MaaS)

`.env`:
```bash
export LLM_API_KEY=sk-your-aliyun-key
export LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
export LLM_MODEL=qwen3.5-122b-a10b
export LLM_THINKING=enable_thinking
export LLM_TIMEOUT=600
```

#### Qwen3.6 27B (Alibaba Cloud MaaS)

`.env`:
```bash
export LLM_API_KEY=sk-your-aliyun-key
export LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
export LLM_MODEL=qwen3.6-27b
export LLM_THINKING=enable_thinking
```

#### Other OpenAI-compatible endpoints (vLLM / Ollama / OpenRouter, etc.)

```bash
export LLM_API_KEY=your-key-or-dummy
export LLM_BASE_URL=http://your-server:8000/v1/chat/completions
export LLM_MODEL=your-model-name
export LLM_THINKING=none
```

> `LLM_THINKING=none` applies to endpoints that don't support the `thinking` field (some MaaS gateways reject unknown fields).

### 4.5 How environment variables are passed in Docker

`docker-run.sh` does the following:

1. If the `DEEPSEEK_API_KEY` environment variable is set -> pass it directly to the container
2. Otherwise, if the `.env` file exists -> source it to extract the key -> pass it to the container
3. The API key is passed in via `docker run -e` and is **never baked into the image**

If you need to pass additional `LLM_*` environment variables (e.g. switching to Qwen), you can `docker run` manually:

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

## 5. Run the Agent

### 5.1 CLI mode (no TUI, most common)

```bash
# Scripted backend (no token cost, verify the toolchain)
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix

# Real LLM repair (costs tokens, requires API key)
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# Limit budget (small-budget test)
./docker-run.sh contest/fpt26-harness/tasks/dotProduct_optimize --backend deepseek --budget 10

# Specify token-saving mode
./docker-run.sh contest/fpt26-harness/tasks/vecadd_optimize --backend deepseek --token-mode balanced
```

`docker-run.sh` automatically:
1. Mounts the host's Xilinx directory tree to the same path inside the container (read-only)
2. Passes `DEEPSEEK_API_KEY` (or reads it from `.env`)
3. Mounts the `runs/` output directory (persisted to the host)
4. Invokes `scripts/run_agent.py`

### 5.2 TUI mode (interactive dashboard)

```bash
./docker-run.sh --tui contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

TUI requires a terminal (`-it`); `docker-run.sh --tui` handles this automatically.

### 5.3 Available task list

```bash
ls contest/fpt26-harness/tasks/
# projection_bugfix   dotProduct_optimize   residual_stream_deadlock
```

### 5.4 Run output

Each run produces:

| Output | Location | Description |
|------|------|------|
| Real-time log | stderr | Event stream (route/tool_result/review/checkpoint) |
| Transcript | stdout | Tool call sequence + credit consumption |
| Scorecard | stdout | SCORE + correctness/synth/PPA |
| JSONL log | `runs/<task_id>/<task_id>.jsonl` | Structured events, analyzable with `jq` |
| Final code | `runs/<task_id>/final_<kernel>.cpp` | The final submitted kernel |
| Score history | `runs/<task_id>/scores.jsonl` | SCORE trend across runs |

### 5.5 Full run_agent.py options

```bash
python3 scripts/run_agent.py <task_dir> [options]

Options:
  --backend {scripted,deepseek,openrouter}   LLM backend (default scripted)
  --budget N                                 Override the credit budget
  --work DIR                                 Working directory (default runs/<task_id>)
  --force                                    Force run without Vitis (csim will fail)
  --token-mode {full,balanced,aggressive}    Token-saving mode (default full)
```

---

## 6. Image Internal Structure

| Path (inside container) | Description |
|----------------|------|
| `/opt/fpga-agent/` | Project root (agent/ + tui/ + scripts/ + contest/) |
| `/opt/venv/` | Python 3.12 virtual environment (textual + rich) |
| `/home/admin/Xilinx/` | Host Xilinx tree mount point (read-only, injected at runtime) |
| `/opt/fpga-agent/runs/` | Run artifact output (mounted to host, persisted) |

Key environment variables (set inside the Dockerfile):

| Variable | Value | Description |
|------|----|------|
| `LLM4HLS_VITIS_HLS_ROOT` | `/home/admin/Xilinx/2025.2/Vitis` | harness locates Vitis |
| `LLM4HLS_TASKS_ROOT` | `/opt/fpga-agent/contest/fpt26-harness/tasks` | Task directory |
| `PATH` | `/opt/venv/bin:$PATH` | Python 3.12 takes priority |

The runtime user is the non-root user `agent` (uid 1000), with passwordless sudo.

---

## 7. FAQ

### Q: Error "Vitis root not found at /home/admin/Xilinx/2025.2/Vitis"

A: The Vitis installation path is not the default. Set the `VITIS_ROOT` environment variable:

```bash
VITIS_ROOT=/your/path/to/Vitis ./docker-run.sh ...
```

### Q: Error "API key missing. Set LLM_API_KEY or DEEPSEEK_API_KEY"

A: No API key is configured. Choose one:
1. Create a `.env` file in the repo root (see `.env.example`)
2. Pass it directly on the command line: `DEEPSEEK_API_KEY=sk-... ./docker-run.sh ...`

### Q: Error "vitis-run not found"

A: Vitis cannot be found inside the container. Confirm:
1. Vitis 2025.2 is installed on the host
2. The `VITIS_ROOT` path is correct (pointing to the directory containing `settings64.sh`)
3. The `settings64.sh` file exists at that path

### Q: LLM returns empty content

A: The reasoning model's reasoning may have consumed all of max_tokens. Keep `max_tokens` unset (default None, unlimited). If problems persist, try increasing `LLM_TIMEOUT`.

### Q: How to switch to the Qwen model?

A: Set the `LLM_*` environment variables (see Section 4.4). Note that although the `--backend deepseek` parameter is named deepseek, it actually instantiates `DeepSeekClient`, which fully supports switching to any OpenAI-compatible endpoint via environment variables.

### Q: How to check whether the LLM configuration inside the container is correct?

A: Enter the container to check:

```bash
docker run --rm -it \
    -e DEEPSEEK_API_KEY=sk-your-key \
    fpga-agent:0.8.1 \
    bash -c 'echo "API_KEY set: ${DEEPSEEK_API_KEY:+yes}" && echo "BASE_URL: ${LLM_BASE_URL:-default(deepseek)}" && echo "MODEL: ${LLM_MODEL:-default(deepseek-v4-pro)}"'
```

### Q: Where is the runs/ directory?

A: `docker-run.sh` automatically mounts the host's `./runs/` to the container's `/opt/fpga-agent/runs/`. Run artifacts appear directly in the host's `runs/` directory and are retained even after the container is deleted.
