> [中文](getting-started.cn.md)

# Getting Started Guide (快速入门指南)

> Aimed at newly onboarded developers (or your future self). Read in 5 minutes to know how to install, how to run, and how to read the code.

---

## 1. Environment Requirements

| Item | Requirement |
|---|---|
| OS | Linux (Ubuntu 22.04 recommended). Windows does not support the acceleration flow |
| Python | 3.11+ (requires the tomllib standard library). 3.12 recommended |
| Vitis | 2025.2 (only required for real csim/synth/cosim; not needed for offline development) |
| LLM API | DeepSeek V4 Pro (or OpenRouter open-source models) |

**Things you don't need**: GPU, database, message queue, web server.

---

## 2. Installation

The project uses two machines: **local machine** (development, no Vitis installed) and **server QFS-STATION** (Vitis installed).

### 2.1 Local machine: framework testing (no Vitis, csim will fail)

```bash
# Local machine operations
git clone git@gitee.com:QFcattail/fpga-agent.git
cd fpga-agent

# Create venv (requires Python 3.11+)
python3.12 -m venv .venv
source .venv/bin/activate    # After activation, python points to 3.12 in the venv

# No pip install needed -- both harness and agent use only the Python standard library

# Without Vitis installed, running will exit with an error (driver detects vitis-run is not in PATH)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix
# -> ERROR: vitis-run not found

# If you just want to test the framework pipeline (csim will compile_error), add --force
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force
```

### 2.2 Server: real Vitis + real LLM (full end-to-end)

Server QFS-STATION already has Vitis 2025.2 and venv installed; this is **where the agent actually runs**.

```bash
# SSH into the server from the local machine
ssh QFS-STATION
cd /home/admin/fpga-agent

# Do these three steps every time you open a new terminal:
source /home/admin/Xilinx/2025.2/Vitis/settings64.sh   # Vitis toolchain
source .env                                              # DeepSeek API key
source /home/admin/venv-fpga/bin/activate               # Python 3.12 venv

# Now you can run (csim actually compiles and runs, ~10 seconds)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# Use DeepSeek for LLM repair (full end-to-end)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

> **Tip**: You must source these three lines every time you open a new terminal. If it's annoying, you can write them into `~/.bashrc`,
> but Vitis's settings64.sh modifies PATH; putting it in bashrc may affect other programs.

---

## 3. CLI Usage

### 3.1 Command format

```bash
python3 scripts/run_agent.py <task_dir> [options]
```

### 3.2 Options

| Option | Default | Description |
|---|---|---|
| `--backend` | `scripted` | LLM backend: `scripted` (preset answers) / `deepseek` (real LLM) / `openrouter` (official) |
| `--budget` | Task default | Override credit budget (e.g. `--budget 10`) |
| `--work` | `runs/<task_id>` | Working directory (stores build artifacts + logs) |
| `--force` | off | Force run without Vitis installed (csim will compile_error; only for framework testing) |

### 3.3 Common commands

The following commands run on **server QFS-STATION** (Vitis + .env + venv already sourced):

```bash
# Real Vitis + ScriptedClient (verify the toolchain, no token cost)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# Real Vitis + DeepSeek (full end-to-end, costs tokens)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# Limit budget (small-budget test)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/dotProduct_optimize --backend deepseek --budget 10

# Run all three tasks
for t in projection_bugfix dotProduct_optimize residual_stream_deadlock; do
    python3 scripts/run_agent.py contest/fpt26-harness/tasks/$t --backend deepseek
done
```

On the local machine, only `--force` works (no Vitis, csim will compile_error):

```bash
# Local machine, for framework testing
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force
```

### 3.4 How to read the output

Each run produces three blocks of output:

**① Run log (stderr, real-time)**:
```
[log] route {'task_type': 'repair', 'correctness_stages': ['csim'], ...}
[log] tool_result {'kind': 'csim', 'phase': 'runtime_fail', 'credit_spent': 1}
[log] mechanical_review {'passed': True, 'issues': []}
[log] review {'verdict': 'pass', 'retry': 0}
[log] checkpoint {'old': 0, 'new': 1, 'reason': 'correctness_gate'}
```

**② Transcript (stdout, printed after run completes)**:
```
--- metered tool transcript ---
  #1  [csim] runtime_fail (rc=1, 9.7s)   [spent 1/10]
  #2  [csim] pass (rc=0, 9.7s)          [spent 2/10]
  #3  [synth] pass (rc=0, 23.6s)        [spent 6/10]
  budget 6/10 credits spent (csimx2, synthx1)
```

**③ Scorecard (stdout, printed after run completes)**:
```
=== Scorecard: projection_bugfix (difficulty 2) ===
  functional (hidden TB): PASS
  synthesizable         : PASS
  SCORE                 : 1.400
```

**④ JSONL log file** (`runs/<task_id>/<task_id>.jsonl`): structured events, analyzed afterward with `jq`.

---

## 4. How to read the code

The code walkthrough (module responsibilities, call relationships, the five-pass reading method, function inventory) is in **[agent/README.md](agent/README.md)**, kept together with the code.

A quick one-line understanding of each module:

| Metaphor | File | Responsibility |
|---|---|---|
| **Brain** | `agent/main_loop.py` | Main loop: correctness -> synth -> optimize |
| **Decision** | `agent/router.py` | Reads task type, selects the stage path |
| **Memory** | `agent/checkpoint.py` | Checkpointing: which version is best |
| **Perception** | `agent/feedback.py` | Extracts error info from tool logs |
| **Hands** | `agent/llm_client.py` | Calls LLM to modify code |
| **Eyes** | `agent/mechanical_checks.py` | Mechanical checks (not relying on LLM) |
| **Mouth** | `agent/deepseek_client.py` | DeepSeek API integration |
| **Diary** | `agent/observability.py` | Logging + heartbeat |
| **Dictionary** | `agent/knowledge_base/` | bug->fix knowledge base |
| **Tools** | `contest/fpt26-harness/` | Official harness (csim/synth/cosim) |
- **main_loop**: "Strings all the above modules together, repairs until csim passes, then synth, then optimize."

---

## 5. FAQ

### Q: What to do about the "vitis-run not found" error?

A: Vitis is not installed or settings64.sh was not sourced. The driver now refuses to run and gives a hint, avoiding misleading SCORE 0.000 output. Install Vitis and source it, then it works. If you just want to test the framework pipeline (csim will compile_error), add `--force`.

### Q: What to do when DeepSeek returns empty content?

A: deepseek-v4-pro is a reasoning model. max_tokens is not set by default (no limit, letting the model think enough). If you manually set max_tokens too small, reasoning will consume the entire budget and content will be empty. Keep the default (None).

### Q: What to do when review rejects everything?

A: ScriptedClient doesn't understand review semantics; the returned code doesn't start with PASS, so it's judged as reject. This is expected -- use a real LLM (deepseek backend) and it won't happen.

### Q: What to do when SCORE is 0?

A: Check: (1) Did csim pass? (2) Did the hidden testbench pass? If correctness doesn't pass, it's 0 points directly. First ensure csim passes, then check synth.

### Q: How to add a knowledge base entry?

A: Edit `agent/knowledge_base/entries.json` (JSON corpus, 22 entries, fields: id/symptom/root_cause/fix/example/signatures). Takes effect on save -- `seed_entries()` loads from this file at startup. signatures uses short lowercase error codes/keyword strings (retrieval is case-insensitive substring matching).

---

## 6. Development Environment Configuration

### 6.1 Local (development machine)

```bash
# .venv
python3.12 -m venv .venv
source .venv/bin/activate

# Environment variables (.env, already gitignored)
echo 'export DEEPSEEK_API_KEY=sk-xxx' > .env

# IDE: VS Code / PyCharm both work
# Recommended: open the Mermaid diagram in agent-architecture.md and read the code alongside it
```

### 6.2 Server QFS-STATION (real Vitis, where the agent actually runs)

```bash
# SSH into the server from the local machine
ssh QFS-STATION
cd /home/admin/fpga-agent

# Source these three lines every time you open a new terminal:
source /home/admin/Xilinx/2025.2/Vitis/settings64.sh   # Vitis toolchain
source .env                                              # DeepSeek API key
source /home/admin/venv-fpga/bin/activate               # Python 3.12 venv

# Now you can use python directly (points to 3.12 in the venv)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

### 6.3 Syncing code to the server

```bash
# Push from local to the server (not via git)
rsync -az --exclude='.git' --exclude='runs/' --exclude='__pycache__' --exclude='.env' \
  agent/ scripts/ QFS-STATION:/home/admin/fpga-agent/
```

---

## 7. Docker Deployment (for submission/evaluation)

> The competition (FPT'26 Track A) requires that "the submission can be built and run in a Docker environment." This section explains how to build the image and run the agent inside a container. Vitis 2025.2 is not baked into the image (~92G, license-bound); instead it is bind-mounted read-only from the host -- this is exactly the model of the official `run-vitis.sh`.

### 7.1 Prerequisites

- Docker is installed on the host, and Vitis 2025.2 is installed (default path `/home/admin/Xilinx/2025.2/Vitis`, overridable with the `VITIS_ROOT` environment variable).
- DeepSeek API key (`DEEPSEEK_API_KEY` environment variable, or a `.env` file in the repo root) -- only needed for `--backend deepseek`.

### 7.2 Build the image

```bash
cd fpga-agent
docker build -t fpga-agent:0.7.4 .
```

The image contains: Ubuntu 22.04 + Vitis dependency libraries (the official `vitis.dockerfile`) + Python 3.12 + textual/rich (TUI) + agent source code + harness. It does NOT contain Vitis itself (mounted at runtime).

### 7.3 Run (CLI mode)

```bash
# Run one task (scripted backend, no token cost, verify the pipeline)
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix

# Real DeepSeek repair (costs tokens)
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

`docker-run.sh` automatically: bind-mounts the **entire Xilinx directory tree** to the same path inside the container (read-only; Vitis's settings64.sh hard-codes absolute paths to sibling directories, so the paths must stay consistent) -> passes `DEEPSEEK_API_KEY` -> mounts the `runs/` output directory -> invokes `scripts/run_agent.py`.

> **Verified in practice (2026-07-22)**: Build succeeded on QFS-STATION; inside the container, projection_bugfix (SCORE 1.400) + dotProduct_optimize (SCORE 3.000 full score) ran successfully, with csim/synth running for real (not mocked); SCORE matches the host.

### 7.4 Run (TUI mode)

```bash
./docker-run.sh --tui contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

TUI requires a terminal (`-it`); `docker-run.sh --tui` handles this.

### 7.5 Image structure

| Path (inside container) | Description |
|---|---|
| `/opt/fpga-agent/` | Project root (agent/ + tui/ + scripts/ + contest/fpt26-harness/) |
| `/home/admin/Xilinx/` | Host's entire Xilinx tree mount point (read-only, injected at runtime; host path preserved because settings64.sh hard-codes sibling directory paths) |
| `/opt/fpga-agent/runs/` | Run artifact output (mounted to the host, persisted) |
| `LLM4HLS_VITIS_HLS_ROOT` | Environment variable = `/home/admin/Xilinx/2025.2/Vitis` (harness config.py locates Vitis) |

### 7.6 Building on the QFS-STATION server

The server has Vitis + a 466G data disk; this is where the image is actually built:

```bash
ssh QFS-STATION
cd /home/admin/fpga-agent
git pull   # Pull the Dockerfile + docker-run.sh
docker build -t fpga-agent:0.7.4 .
# Server default VITIS_ROOT=/home/admin/Xilinx/2025.2/Vitis, no extra setup needed
./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

---

## Change Log

| Date | Change | Author |
|---|---|---|
| 2026-07-15 | v1 initial draft. | Qianhe Cheng |
