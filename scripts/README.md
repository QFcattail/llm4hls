> [中文](README.cn.md)

# Scripts

CLI entry points and driver scripts. The command-line driver for non-TUI mode.

## File Structure

| File | Responsibility |
|---|---|
| `run_agent.py` | CLI driver: assembles the agent and runs it end-to-end, outputting the transcript + scorecard |
| `test_main_loop.py` | Offline unit tests for the main loop (TC-AGENT-001~015); runnable without Vitis/LLM |

## run_agent.py

Modeled on the harness's built-in `contest/fpt26-harness/scripts/run_poc.py`, but uses the project's own `agent.main_loop.Agent` in place of `ReferenceAgent`. No TUI; it prints the transcript + scorecard directly.

### Command-Line Arguments

| Argument | Default | Description |
|---|---|---|
| `task_dir` (required positional) | - | Task package directory |
| `--backend` | `scripted` | LLM backend: `scripted` (preset answers) / `deepseek` (real LLM) / `openrouter` (official) |
| `--budget` | from the task | Override the credit budget (e.g. `--budget 10`) |
| `--work` | `runs/<task_id>` | Working directory (stores build artifacts + logs) |
| `--force` | off | Force-run when Vitis is not installed (csim will return compile_error; only for framework testing) |

### Steps to Assemble the Agent

1. Vitis guard: check whether `vitis-run` is on PATH; if not, try sourcing settings64.sh; if still missing and no `--force`, error out.
2. `load_task(task_dir)` -> `Budget(total)` -> `ToolServer(task, budget, work_root)`
3. Backend selection: `OpenRouterClient` / `DeepSeekClient` / `ScriptedClient`
4. `HLSLLMClient(backend)` + `KnowledgeBase(seed_entries())` (7 seed entries; expand in P2-12)
5. `Agent(task, server, llm, kb, run_dir=work_root)` -> `final = agent.run()`
6. Output: `usage_summary()` -> transcript -> `budget.summary()` -> `grade(task, final)` scorecard -> write the `final_<kernel_name>` file

### sys.path Injection

`ROOT` (project root, for `agent`) + `ROOT/contest/fpt26-harness` (for `llm4hls`).

## Build Method

```bash
# Real Vitis + ScriptedClient (verify the toolchain, no token cost)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# Real Vitis + DeepSeek (full end-to-end, costs tokens)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# Offline framework test (csim will compile_error)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force

# Main-loop offline unit tests (no Vitis / LLM API needed; mandatory after changing the main loop)
python3 scripts/test_main_loop.py
```

## Known Pitfalls

- **SCORE is always 0.000 without Vitis**: without Vitis, all csim/synth/cosim calls return `compile_error`, SCORE is 0.000, and the output is misleading. The driver detects this and suggests adding `--force`.
- **Assembly logic shared with the TUI**: `run_agent.py` and `tui/app.py` have nearly identical agent-assembly steps (load_task->Budget->ToolServer->backend->HLSLLMClient->KnowledgeBase->Agent); the only difference is that the TUI uses a background thread + event queue, while the CLI prints synchronously.
