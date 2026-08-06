> [中文](README.cn.md)

# Agent Core

The Python implementation of the Budgeted End-to-End LLM4HLS Agent. It automatically repairs and optimizes Vitis HLS C/C++ code within a limited credit budget.

For the architectural design, see [`docs-development/design/agent-architecture.md`](../docs-development/design/agent-architecture.md) (Mermaid flowcharts + archive logic + observability). This document is a **code tour** -- start here when reading the code.

---

## Quick Start

```bash
# Offline run (no Vitis, no API key; uses ScriptedClient to feed preset answers)
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# Real Vitis + real DeepSeek (full end-to-end)
export LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis
source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh
source .env   # DEEPSEEK_API_KEY
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

CLI options: `--backend {scripted,deepseek,openrouter}`, `--budget N`, `--work DIR`

---

## Module Responsibilities (in one sentence)

| File | Metaphor | Responsibility |
|---|---|---|
| `main_loop.py` | **Brain** | Main loop: correctness -> synth -> optimize, wires all modules together |
| `router.py` | **Decision** | Reads task.toml, chooses the level path (repair->[csim], structural->[csim,cosim]) |
| `checkpoint.py` | **Memory** | Archive: which version is best (three rules: higher level -> accept; same level -> compare latency; lower -> reject) |
| `feedback.py` | **Senses** | Extracts error codes + keywords from csim/synth/cosim logs, builds LLM-friendly feedback |
| `llm_client.py` | **Hand** | Calls the LLM to modify code (repair/review/propose_strategies/apply_strategy) |
| `mechanical_checks.py` | **Eye** | Hard checks: did the signature change, is the include present (the parts where the LLM is not trusted) |
| `deepseek_client.py` | **Mouth** | DeepSeek V4 Pro API integration (OpenAI-compatible, reasoning model, records tokens) |
| `observability.py` | **Diary** | JSONL structured logging + heartbeat thread (stuck-detection) |
| `score_history.py` | **Report card** | Per-task scores.jsonl: record/recent/format, shared by both CLI and TUI entry points (v0.4.0) |
| `knowledge_base/` | **Dictionary** | bug->fix knowledge base, retrieved by error code/keyword and injected into the prompt; `entries.py` contains 7 seed entries |
| `__init__.py` | | Package entry, exports route/RunPlan/Checkpoint/Level |

---

## Module Call Graph

```
run_agent.py (driver/CLI)
  │
  ├── agent.main_loop.Agent ──────────────────────────────────────┐
  │       │                                                        │
  │       ├── agent.router.route(task) -> RunPlan                   │
  │       ├── agent.checkpoint.Checkpoint (archive decisions)       │
  │       ├── agent.feedback.build_feedback(results) -> Feedback    │
│       ├── agent.llm_client.HLSLLMClient                        │
│       │       ├── .repair(task, code, feedback, kb_text)       │
│       │       ├── .review(task, code, focus)                   │
│       │       ├── .extract_design_brief(task, code)            │
│       │       ├── .propose_strategies(task, code, synth, brief)│
│       │       ├── .select_strategies(...)  [v2.4 review AI]    │
│       │       └── .apply_strategies(subset, brief) [v2.4 combo]│
  │       │       │                                                │
  │       │       └── inject backend (DeepSeekClient / ScriptedClient)│
  │       │                                                        │
  │       ├── agent.mechanical_checks.mechanical_review(...)       │
  │       ├── agent.observability.Logger + Heartbeat              │
  │       └── agent.knowledge_base.KnowledgeBase.search(...)      │
  │                                                                │
  └── llm4hls.* (harness: ToolServer/Budget/Task/grade) ◄──────────┘
          │
          └── ToolServer.csim/synth/cosim(code) -> ToolResult
```

**Dependency direction**: main_loop depends on all agent modules + the harness. Agent modules avoid depending on each other where possible (checkpoint/router/feedback/observability/knowledge_base are all independent). The only bidirectional coupling is that llm_client depends on feedback's output format (but it is passed via parameters, not imported directly).

---

## Code Reading Order

Read **from the outside in, from simple to core**:

### First pass: get the big picture (30 minutes)

1. **`__init__.py`** (22 lines) - see what this package exports
2. **`router.py`** (70 lines) - the simplest module, pure data. Understand what a RunPlan is
3. **`checkpoint.py`** (68 lines) - the core data structure. Understand Level and the three rules
4. **`scripts/run_agent.py`** (82 lines) - the entry point, see how the agent is assembled
5. **`main_loop.py`'s `run()` method** (~20 lines) - the main loop skeleton, ignore the details

### Second pass: follow the data flow (40 minutes)

6. **`feedback.py`** (102 lines) - how a ToolResult becomes LLM-readable feedback
7. **`main_loop.py`'s `_reach_correctness()`** (~60 lines) - the repair loop, the core of the core
8. **`main_loop.py`'s `_repair_with_review()`** (~30 lines) - how the two-layer review works

### Third pass: the adapter layer (30 minutes)

9. **`mechanical_checks.py`** (96 lines) - signature/include checks, simple but important
10. **`llm_client.py`** (219 lines) - four domain methods + prompt templates
11. **`deepseek_client.py`** (126 lines) - API integration + token accounting

### Fourth pass: the infrastructure (15 minutes)

12. **`observability.py`** (121 lines) - logging + heartbeat
13. **`knowledge_base/retriever.py`** (61 lines) - RAG retrieval

### Fifth pass: external dependencies (as needed)

14. `contest/fpt26-harness/llm4hls/harness.py` - ToolServer (the tool interface the agent calls)
15. `contest/fpt26-harness/llm4hls/tools.py` - CSimTool/SynthTool/CoSimTool
16. `contest/fpt26-harness/llm4hls/scoring.py` - the scoring formula

---

## Core Data Flow (measured on the projection task + the synth/optimize segments completed in v0.2.0)

```
route(task) -> RunPlan{repair, [csim], init_level=0}
  │
  ▼ _reach_correctness:
  csim(code) -> runtime_fail         ← actually run by Vitis (9.7s)
  build_feedback(csim_r) -> Feedback{runtime_fail, signatures=[]}
  _kb_lookup(fb) -> ""               ← empty string if no hit
  _repair_with_review:
    llm.repair(task, code, fb_text, "") -> new_code     ← DeepSeek repairs
    mechanical_review(orig, new_code, task) -> (True)    ← signature unchanged
    llm.review(task, new_code, focus) -> (True, "PASS")   ← LLM review passes
  csim(new_code) -> pass             ← the repair actually passes (9.7s)
  ckpt.should_accept(CORRECT, None) -> True
  ckpt.accept(new_code, CORRECT)    ← archive 0->1
  │
  ▼ _do_synth (v0.2.0: repair loop):
  synth(ckpt.code) -> synth_error?
    ├─ yes -> build_feedback -> _kb_lookup(hits a seed entry) -> _repair_with_review
    │       -> re-verify csim (1 credit) -> only then synth again (4 credits)   [§4.3]
    └─ no  -> ckpt.accept(ckpt.code, SYNTH, latency)  ← archive 1->2 + record synth_summary
  │
  ▼ _optimize (v0.3.0: strategy combination + review AI):
  snapshot ckpt (§4.5 rollback point)
  extract_design_brief(task, code) -> design brief (cached once)     [AMD Phase 1]
  each round: propose_strategies(design doc + brief + latest synth report)     [AMD Phase 2a]
        -> tag each strategy with combinable_with compatibility
        -> select_strategies review AI double-checks + picks a compatible subset           [Phase 2b double confirmation]
        -> apply_strategies(merge subset) -> _apply_with_review     [AMD Phase 3]
        -> re-verify csim + synth -> should_accept(SYNTH, lat) same-level best-of
        -> combo fails -> fall back to trying the subset's first strategy alone (attribution), stop only if still fails
  │
  ▼ (tasks requiring cosim) _post_opt_cosim_recheck:
  re-verify only if best changed; cosim fails -> truly roll back to the pre-optimization snapshot            [§4.5]
  │
  ▼ return ckpt.code -> grade() -> SCORE 1.400
```

---

## Function List

### main_loop.Agent

| Method | Visibility | Responsibility |
|---|---|---|
| `__init__(task, server, llm, kb, max_rounds, max_synth_rounds, max_optimize_rounds, run_dir)` | public | Inject dependencies + cross-stage state (synth_summary/design_brief/snapshots) |
| `run() -> str` | public | Entry: route -> correctness -> synth -> optimize -> return best code |
| `_run_plan(plan, ckpt) -> str` | private | Execute the three stages per the RunPlan |
| `_reach_correctness(plan, ckpt) -> bool` | private | Stage 1: csim (+cosim) repair loop |
| `_repair_with_review(code, feedback, kb_text) -> str\|None` | private | Generate a repair + mechanical check + LLM review two-layer verification |
| `_do_synth(plan, ckpt) -> int\|None` | private | Stage 2: synth repair loop (RAG + re-verify csim before synth), obtain baseline latency |
| `_valid_latency(report) -> int\|None` | private(static) | latency<=0 treated as missing (defense against latency=0 parse anomaly) |
| `_optimize(plan, ckpt)` | private | Stage 3: PPA optimization loop (Phase 1-3 + review AI selects subset + combination generation + failure fallback) |
| `_try_opt_candidate(ckpt, strategies, round_n) -> str` | private | Single-candidate pipeline: generate -> re-verify -> same-level best-of, returns improved/no_improvement/failed |
| `_apply_with_review(code, strategies) -> str\|None` | private | Phase 3 generation + two-layer verification (apply_strategies combination variant) |
| `_post_opt_cosim_recheck(ckpt)` | private | Post-optimization re-verification for cosim-requiring tasks; truly rolls back the snapshot on failure |
| `_restore_snapshot(ckpt, snap)` | private(static) | Full snapshot restore (§4.5) |
| `_kb_lookup(fb) -> str` | private | Query the knowledge base, return the matched entry text |

### router

| Function | Responsibility |
|---|---|
| `route(task) -> RunPlan` | task.type + requires_cosim -> level path |

### checkpoint.Checkpoint

| Method | Responsibility |
|---|---|
| `should_accept(cand_level, cand_latency) -> bool` | Three-rule decision |
| `accept(code, level, latency, cosim_ok)` | Commit as the new best |

### feedback

| Function/Method | Responsibility |
|---|---|
| `build_feedback(*results) -> Feedback` | Distill error signatures + feedback text from a ToolResult |
| `Feedback.as_prompt_block() -> str` | Render the feedback block for the repair prompt |

### llm_client.HLSLLMClient

| Method | Responsibility |
|---|---|
| `repair(task, code, feedback, kb_text) -> str\|None` | Have the LLM repair the code |
| `review(task, code, focus) -> (bool, str)` | Cross-validate the candidate code |
| `extract_design_brief(task, code) -> str` | AMD Phase 1: distill a design brief (functionality/loops/dataflow/bottlenecks); called once and cached before optimize |
| `propose_strategies(task, code, synth_summary, design_brief) -> list[Strategy]` | AMD Phase 2a: inject the design doc + brief + report, propose strategies (tagging combinable_with) |
| `select_strategies(task, code, strategies, synth_summary, design_brief) -> (list[int], str)` | Phase 2b review AI: double-check compatibility and pick a subset; falls back to [0] on parse failure |
| `apply_strategies(task, code, strategies, design_brief) -> str\|None` | AMD Phase 3: merge a compatible subset and generate (double confirmation) |

### mechanical_checks

| Function | Responsibility |
|---|---|
| `mechanical_review(original, candidate, task) -> (bool, list[str])` | Hard signature + include checks |

### deepseek_client.DeepSeekClient

| Method | Responsibility |
|---|---|
| `complete(system, user) -> str` | Call the DeepSeek API |
| `usage_summary() -> str` | Token usage summary |

### observability

| Class.Method | Responsibility |
|---|---|
| `Logger.event(event, **fields)` | Write one JSONL event |
| `Heartbeat.set_stage(stage, credit)` | Update the current stage (stuck-detection) |

### knowledge_base

| Method | Responsibility |
|---|---|
| `KnowledgeBase.search(signatures) -> list[KBEntry]` | Retrieve entries by error code/keyword |
| `seed_entries() -> list[KBEntry]` | 7 seed entries (synth 4 + cosim 1 + csim 2), loaded by default at the entry points |

---

## External Dependencies (harness, read-only reuse)

The agent reuses the following classes from the official harness via import, defined in `contest/fpt26-harness/llm4hls/`:

| harness class | Purpose | Where the agent uses it |
|---|---|---|
| `Task` / `load_task()` | Task loading | run_agent.py |
| `Budget` / `BudgetExceeded` | Credit billing | run_agent.py / main_loop.py |
| `ToolServer` | csim/synth/cosim tool interface | main_loop.py |
| `ToolResult` | Tool return (kind/ok/phase/log/report) | feedback.py / main_loop.py |
| `grade()` / `Scorecard` | Scoring | run_agent.py |
| `ScriptedClient` / `OpenRouterClient` | LLM backend | run_agent.py |

---

## Design Decisions Quick Reference

| Decision | Rationale |
|---|---|
| Fork the harness instead of rewriting | The evaluation interface is locked by the official spec to in-process function calls |
| Single process, no RPC | Running vitis via subprocess already provides process isolation |
| Two-layer review (mechanical + LLM) | In practice the LLM self-check misses signature changes; the mechanical check is the backstop |
| Archive level monotonically non-decreasing | Scoring is tiered (correct gate > synth > PPA), a natural mapping |
| DeepSeek max_tokens=16384 | For reasoning models, reasoning_tokens consumes the max_tokens budget |
| optimize extracts a design brief before modifying | AMD Phase 1: without design context the LLM only gives generic advice (v0.2.0) |
| Strategy combinations require double confirmation before merging | pragma interaction is a high-error area for the LLM; the proposer + reviewer must both agree the strategies don't interfere before combining (v0.3.0, user decision) |
| On combo failure, fall back to the first strategy once | A failed combo candidate can't be attributed to a single strategy, so shrink the set and retry (v0.3.0) |
| Synth repair re-verifies csim before synth | 1 credit is cheaper than 4 credits; changing for synth could break correctness (§5) |
| Truly roll back the snapshot when cosim fails after optimization | Previously it only logged without restoring, which could submit with a deadlock (§4.5, fixed in v0.2.0) |

---

## Known Pitfalls

- **`knowledge-base/` (hyphen) vs `knowledge_base/` (underscore)**: the former is the spec docs directory (only a README), the latter is the Python package (`retriever.py` + `entries.py`, importable). The naming difference stems from "doc directories use hyphens, Python packages use underscores (valid identifiers)". Both are active; do not delete either.
- **harness import path**: when agent modules import `llm4hls.*`, `contest/fpt26-harness` must be on `sys.path`. `scripts/run_agent.py`, `scripts/test_main_loop.py`, and `tui/app.py` all do `sys.path.insert`; running agent modules directly from another directory will raise ImportError.
- **DeepSeek reasoning_tokens**: the reasoning process of a reasoning model consumes the max_tokens budget; if set too small the content gets truncated. Currently set to 16384.
- **KB retrieval signatures must be short strings**: the retriever does whole-string substring matching, and `build_feedback` produces short signatures at the error-code (`[XFORM 203-313]`) + keyword (`deadlock`) level; a full-sentence query will never hit. Entry signatures likewise only hold short strings (see the comments in entries.py).
- **The seed KB is loaded by default**: both `run_agent.py` and `tui/app.py` use `KnowledgeBase(seed_entries())` (7 entries). When expanding in P2-12, just add to `entries.py`; don't modify the two entry points.
- **synth latency=0 parse anomaly**: on real hardware we've seen synth pass but latency=0. `Agent._valid_latency` treats <=0 as missing -- if you remove this defense, a "0-cycle" result would always win same-level latency comparisons and contaminate the archive. Root cause pending real-machine investigation (left over from dev-log 2026-07-17-01).
