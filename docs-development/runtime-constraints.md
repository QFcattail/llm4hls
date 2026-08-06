> [中文](runtime-constraints.cn.md)

# Runtime Constraints (Runtime Constraints)

Records the hard constraints that affect the agent's design and operation. **2026-07-14 fourth update**: after unzipping the official harness (contest/fpt26-harness/), all former "to-be-confirmed items" are resolved. The evaluation interface, credit budget, scoring formula, and Docker spec are all clear; see below.

---

## I. Contest Rules (FPT'26 Track A: LLM4HLS Agent)

**Contest**: FPT'26 Design Competition - Track A (fpt2026.uark.edu)

**Confirmed rules** (source: Submission_Guidelines_Track-A.docx + selection-requirements.md + official harness + AMD case article):
- FPGA platform: Alveo U55C `xcu55c-fsvh2892-2L-e`
- Software version: Vitis **2025.2** (HLS is invoked via `vitis-run --mode hls`; standalone `vitis_hls` is deprecated in 2025.2)
- Target frequency: **200 MHz (5 ns clock)**
- Must pass csim, cosim, synth
- **Token consumption is an important final-eval metric**
- The LLM must use an **open-source model** (enforced by the harness, via OpenRouter). Three candidates recommended for comparison:
  - DeepSeek V4 Pro / Qwen3.5 122B A10B / Qwen3.6 27B (see the original plan)
- A hidden test set is used for final evaluation
- Submit a **Docker environment** (the harness provides `vitis.dockerfile`)
- Deliverables: source code + testbench + supplementary materials (.zip) + a demo video (≤5 minutes, must run on the target platform)
- **Correctness takes priority over PPA**

**End-to-end flow the agent must complete** (source: selection-requirements.md):
1. Interpretation: interpret the task spec and the initial code
2. Generation/modification: generate or modify HLS C/C++ code (including pragmas)
3. Invocation: call the tool feedback interface
4. Parsing: parse logs and reports, diagnose problems
5. Prioritization: correctness first, then PPA
6. Termination: terminate within budget

---

## II. The Official Harness (unzipped, authoritative source)

**Location**: `contest/fpt26-harness/`

The official harness is a reference implementation + evaluation tool, **pure Python standard library** (requirements.txt is empty, no third-party dependencies). It answers all the former "to-be-confirmed" questions at once.

### 2.1 Evaluation interface (former to-be-confirmed item 1, resolved)

**In-process Python function calls**, not MCP / HTTP / command-line interface. The agent calls three tools via `ToolServer`:

```python
server.csim(kernel_code)  -> ToolResult   # costs 1 credit
server.synth(kernel_code) -> ToolResult   # costs 4 credits, .report has PPA
server.cosim(kernel_code) -> ToolResult   # costs 20 credits, .cosim has measured latency
```

The agent only provides the kernel source; headers and testbench are fixed by the harness. Each call is charged against the budget and written to the audit transcript.

**Underlying implementation** (`vitis.py`): `source /opt/xilinx/2025.2/Vitis/settings64.sh && vitis-run --mode hls --tcl run_hls.tcl`, run via subprocess; a tool crash does not take down the agent (process isolation is satisfied).

### 2.2 Credit budget (former to-be-confirmed item 2, resolved)

| Tool | credit cost | Timeout |
|---|---|---|
| csim | 1 | 180s |
| synth | 4 | 600s |
| cosim | 20 | 900s |

Each task's budget is defined in the `budget` field of `task.toml`. Example tasks: projection=20, dotProduct=40, residual=80. Exceeding the budget raises `BudgetExceeded` and the agent is forced to stop.

**Key: credit does not accumulate across tasks; saving credit within a single task gives no reward (the score depends only on which gate is reached).** The "saving" that truly affects scoring is tokens, not credit.

### 2.3 Scoring formula (former to-be-confirmed item, resolved)

`scoring.py:144-149`; correctness is the hard threshold:

```python
if not functional_pass:                    # hidden testbench did not pass
    score = 0.0
else:
    ppa_norm = min(acceleration, 8) / 8
    quality = 0.5 * correct + 0.2 * synth_pass + 0.3 * ppa_norm
    score = difficulty * quality
```

`functional_pass = hidden_csim.ok and (cosim_pass is not False)`.

**Scoring uses the hidden testbench, run outside the agent budget (does not spend agent credit).** See `docs-development/design/agent-architecture.md` §1.

### 2.4 Task package format

```
<task>/
  task.toml            # spec: task_type, difficulty, budget, target, top fn
  description.md       # interface contract + initial-state description (official design doc)
  <kernel>.cpp         # the only file the agent may edit (starting code, broken or slow)
  <kernel>.h           # header, fixed, agent cannot change
  <kernel>_tb.cpp      # PUBLIC testbench (agent may csim, metered)
  hidden/<kernel>_tb.cpp   # HIDDEN testbench (for scoring, not visible to the agent)
  reference/<kernel>.cpp   # golden solution (offline scripted agent baseline)
```

`task_type` ∈ `generate | repair | optimize | synth_fix`. You may also set `requires_cosim = true` (structural tasks must pass cosim to count as correct).

### 2.5 Three example tasks

| Task | task_type | difficulty | budget | Which gate the bug is in |
|---|---|---|---|---|
| projection_bugfix | repair | 2 | 20 | csim (functional bug) |
| dotProduct_optimize | optimize | 3 | 40 | no bug, push PPA |
| residual_stream_deadlock | structural | 4 | 80 | cosim (DATAFLOW deadlock) |

### 2.6 Docker spec (former to-be-confirmed item 4, resolved)

The harness provides `vitis.dockerfile` (Vitis 2025.2 environment) and `run-vitis.sh` (in-container run script).

---

## III. Established Facts About the Local Environment

- **Network egress**: this machine's Bash has full network egress (curl / python urllib / pip / npm registry all can reach the internet).
  The harness's built-in `WebFetch` is limited by domain verification; bypass it with the hand-written `tools/web_fetch.py` (Bash + requests + html2text).
- **Python runtime**: conda `python3` **3.13** (`/home/GPUclaude/miniconda3/bin/python3`) + system `python3` 3.10.
  The harness is verified to run the ScriptedClient offline path on 3.13 (task loading, budget billing, transcript, scorecard all normal).
- **LLM brain**: open-source model (DeepSeek V4 Pro / Qwen3.5 / Qwen3.6), via OpenRouter.
  - This environment has a built-in Zhipu GLM (`builtin:bigmodel`) usable for dev debugging
  - Specific API key to be provided by the user
- **Dev platform**: Linux host `gpuclaude` (8-core Xeon Platinum, 14GB RAM, / has 14G free, /home has 20G free)
- **Git**: remote is `git@gitee.com:QFcattail/fpga-agent.git`, SSH is in effect

---

## IV. Vitis 2025.2 Environment Requirements and Deployment

This machine has **insufficient disk** (two drives totaling 34GB available; a full Vitis install needs 100-200GB) and **cannot install Vitis locally**.

### 4.1 System requirements (source: UG1742 + official support forum)

| Item | Requirement |
|---|---|
| OS | **Linux** (Ubuntu 22.04 LTS officially designated / RHEL 9.x). **Windows does not support the acceleration flow** (Alveo U55C + Docker submission must be Linux) |
| Install size | Full Vitis ~100-200GB; minimal embedded/SDK ~15-35GB (but there is no standalone HLS installer; HLS is bundled with Vitis/Vivado) |
| Memory | 32GB minimum, 64GB recommended (our kernel is a small design; 16GB is barely usable) |
| CPU | Multi-core gains are limited; 4-8 cores is enough |
| GPU | **Not needed** (cosim is a CPU-run RTL simulation) |
| License | **HLS C synthesis/simulation is license-free** (UG1399 is explicit); only hardware implementation needs a Vivado license |

### 4.2 Deployment plan

- **Plan (decided)**: the user rents a cloud Linux server (Ubuntu 22.04, 8 cores / 32GB / 200GB SSD, no GPU); the HLS domain lead handles the Vitis install. The user will provide SSH authorization.
- **Cost estimate**: about 200 RMB/month, lower with intermittent actual use. The contest period is under a month, so cost is controllable.
- **Offline development (available now)**: ScriptedClient runs the framework layer (agent main loop, knowledge base, prompts) without Vitis.

---

## V. Contest Timeline (confirmed)

Source: FPT'26 contest page (fpt2026.uark.edu)

| Stage | Deadline | Notes |
|---|---|---|
| Registration closes | 2026-07-07 (23:59 AoE) | Team registration |
| Submission closes | **2026-08-07 (23:59 AoE)** | Technical materials submission |
| Finalists announced | 2026-08-21 | Finals list published |

- Finalists must register for the FPT 2026 conference (Full Registration) and demo on site
- Optional: publish a 2-page short paper in the IEEE FPT 2026 conference proceedings
- Evaluation criteria: technical value (40%) + innovation (20%) + practical impact (20%) + presentation & reproducibility (20%)

---

## VI. Status of Former "To-Be-Confirmed Items"

| Former to-be-confirmed item | Status | Resolution source |
|---|---|---|
| 1. Evaluation interface form | ✅ Resolved | harness ToolServer (in-process function call) |
| 2. Tool-call budget amount | ✅ Resolved | csim=1 / synth=4 / cosim=20 credits, defined per task in task.toml |
| 3. Hidden test-set scale/difficulty | ✅ Partially resolved | harness gives 3 public example tasks; the hidden set has the same structure |
| 4. Docker harness spec | ✅ Resolved | harness provides vitis.dockerfile + run-vitis.sh |

---

## VII. AI Operating Constraints (AI Operating Constraints)

> Any AI/person must observe the following discipline before acting; violations lead to rework or misoperation.

- **Read before doing**: before acting, first read `requirements/`, `design/`, these constraints, and the latest `dev-log/`; do not operate on assumptions.
- **Write logs**: after completing each chunk of substantive work, immediately add to `dev-log/` (template in `dev-log/README.md`); do not let it pile up.
- **Confirm before acting unilaterally**: constraint-class decisions like network ports, safety downgrades, device ownership, and server configuration must be confirmed with the user first.
- **Do not advance stages unilaterally**: if the P1 review has not passed, do not secretly start P2. Stage advancement needs user/review confirmation.
- **Verify after state changes**: after a TUI state change, screenshot to confirm the actual rendering (if available); do not rely solely on logs to infer the UI.

---

## VIII. Versioning & UI Screenshots (Versioning & UI Screenshots)

### 8.1 The version number must be bumped on every release (hard constraint)

- For all sub-projects with a UI, the version number must be bumped before every rebuild/redeploy; otherwise you cannot tell whether the running version is new or old.
- This project's version number is defined in `agent/_version.py`'s `__version__`, in semantic-versioning (SemVer) format `MAJOR.MINOR.PATCH`.

| Change type | Bump amount |
|---|---|
| Code fixing runtime behavior | at least patch +1 |
| New feature | minor +1 |
| Docs/comments only | may skip the bump |

### 8.2 Display the version number in the UI

This project's TUI dashboard (`tui/`) is the only subsystem with a UI and **must** display the version number in the title bar. When troubleshooting, the version number is the only reliable way to confirm "which version is running".

### 8.3 Screenshots and reading them

The TUI runs in a terminal and has no GUI screenshot needs. To confirm the TUI's rendering state:
- Run `./run.sh` or `python3 fpga-agent.py` in the terminal and observe the terminal output directly.
- To record: use the `script` command to record the terminal session, or a terminal screenshot tool.
- The current environment has no headless GUI screenshot needs (Vitis csim/synth/cosim are command-line tools whose output is logs/reports).
