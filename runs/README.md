> [中文](README.cn.md)

# Run Outputs

> This directory holds the artifacts produced by agent runs. **It is gitignored and not committed.** Each run overwrites the same-named subdirectory.

## Directory Structure

Each run of `scripts/run_agent.py` or `./run.sh` generates the following under `runs/<task_id>/`:

```
runs/
└── <task_id>/                  e.g. projection_bugfix
    ├── final_<kernel>.cpp      the kernel code the agent finally outputs
    ├── <task_id>.jsonl         event log (JSONL, one event per line: route/tool_result/kb_search/checkpoint, etc.)
    ├── <task_id>_prompts.jsonl  full LLM prompt record (v0.7.2: the purpose/system/user/response of each call)
    ├── scores.jsonl            score history (one row appended per scoring: ts/score/latency/credits/tokens)
    ├── agent/                  agent workspace
    │   ├── csim_1/             working dir for the 1st csim (kernel.cpp/.h/_tb.cpp/run_hls.tcl)
    │   ├── csim_2/             2nd csim (rerun after repair)
    │   ├── synth_3/            the 3rd tool call is synth
    │   └── ...                 ordered by tool-call number
    └── grade/                  grading area
        ├── grade_csim/         hidden testbench csim
        ├── grade_synth_base/   baseline synthesis
        └── grade_synth_cand/   candidate synthesis (PPA comparison)
```

## Distinguishing From the Harness's Own runs/

| Directory | Source | Purpose |
|---|---|---|
| `runs/` (project root) | produced by this project's `agent.main_loop.Agent` | validating our agent |
| `contest/fpt26-harness/runs/` | produced by the harness's built-in `ReferenceAgent` | baseline comparison against the official reference implementation |

The two have similar structures (both use the harness's ToolServer), but the agent implementations differ. When doing performance comparisons, be careful to distinguish the source.

---

## Log-Reading Guide (how to read a run)

### 1. First, tell the three kinds of "logs" apart

| Log | Where | What it records | When to look |
|---|---|---|---|
| **dev-log** | `docs-development/dev-log/` | what each dev session did, why, and what problems it hit | when you want to know "why the project is shaped this way" |
| **event log JSONL** | `runs/<task>/<task>.jsonl` | the events at each decision point during one agent run (**the main log for reading a run**) | when you want to know "how well this run went, where it got stuck" |
| **harness transcript** | end of terminal output / `server.transcript` | the billing stream for each tool call (csim/synth/cosim + how many credits spent) | when you want to know "where the budget went" |

When people say "read the log" day-to-day, 90% of the time they mean the second kind: the event-log JSONL. Everything below is about it.

### 2. How to read the JSONL: event-type quick reference (v0.7.0)

Each line is one JSON object: `{"ts": timestamp, "task": task_id, "event": event_name, ...}`. In the order of events in a complete run:

| Order | Event | What to look at |
|---|---|---|
| 1 | `route` | routing decision: task_type, correctness gate, initial_level, budget, **token_mode** (v0.7.0: full/balanced/aggressive) |
| 2 | `pre_csim_review` -> `mechanical_review`/`review` -> `pre_csim_fix_applied` or `pre_csim_no_change` | free static checkup: did the LLM spot a problem before spending any credit |
| 3 | `tool_result` (csim) | first csim: did `ok` pass; if not, look at `phase` (compile_error/runtime_fail) and `log` (the raw error) |
| 4 | (on failure) `kb_search` -> `mechanical_review` -> `review` -> back to 3 | repair loop: did the KB hit anything (`hits>0`; from v0.7.0 `hit_ids` shows exactly which entry), and did the two gates pass |
| 5 | `checkpoint` (reason=correctness_gate) | **archive Lv1**: correctness met, the correct points are secured |
| 6 | `phase_exit` (correctness, result=ok) | stage 1 ends |
| 7 | `tool_result` (synth) + `checkpoint` (reason=synth_ok) | **archive Lv2**: synth points secured + baseline latency |
| 8 | `phase_enter` (optimize) -> `design_brief` | optimization begins: design-brief extraction (chars length) |
| 9 | `llm_call` (propose_strategies, count=N) -> `llm_call` (select_strategies) -> `strategy_select` | **strategy decision**: how many strategies were proposed, which the reviewer picked (`indices`/`picked`), which it rejected (`rejected`), and whether it was a fallback (`fallback`) |
| 10 | `llm_call` (apply_strategies) -> `mechanical_review` -> `review` | generation + two gates; `review verdict=reject` means the LLM made a pragma error and was blocked |
| 11 | `tool_result` (csim+synth) | candidate re-verification |
| 12 | `checkpoint` (reason=optimize_improve) | **got better**: `old_latency->new_latency`; stringing these together gives the optimization trajectory |
| 13 | `optimize_discard` / `optimize_fallback` / `optimize_stop` | reason a candidate was discarded / combo-failed fallback / convergence-stop reason |
| 14 | `cosim_recheck` | final RTL checkup (only appears if best changed and budget allows) |
| 15 | `submit` | terminal state: `final_level`, `final_latency`, `credit_spent` |

**From v0.7.0 the `llm_call` event carries token fields** (DeepSeek backend): `model` / `prompt_tokens` / `completion_tokens` / `reasoning_tokens` -- enables per-call-site token attribution analysis (P4-03).

Others that may appear: `budget_exhausted` (budget used up), `rollback` (snapshot rollback; check `reason` for why), `repair_failed` (the LLM produced no parseable code), `env_error` (vitis-run not found), `heartbeat` (a liveness heartbeat every 10s; can be filtered out during analysis).

### 3. A real snippet (the dotProduct full-score run, annotated line by line)

```
route            task_type=optimize, budget=40          ← routing: optimization task, 40 credits
pre_csim_fix_applied                                 ← free checkup: the LLM optimized the code directly
tool_result      csim pass (10.1s)  [spent 1]         ← the 1st credit
checkpoint       0->1 correctness_gate                  ← Lv1: the 1.5 correct points secured
tool_result      synth pass latency=38 [spent 5]      ← Lv2: baseline 38 cycles
phase_enter      optimize                              ← optimization begins
design_brief     chars=1386                            ← the LLM understood the design: serial accumulation is the bottleneck
llm_call         propose_strategies count=3            ← proposed 3 strategies
strategy_select  indices=[0,1,2] picked=[all three]    ← the review AI judged the 3 strategies combinable
mechanical_review passed=True                        ← hard gate passed
review           verdict=pass                          ← LLM re-review passed
tool_result      csim pass [spent 6]
tool_result      synth pass latency=37 [spent 10]
checkpoint       38->37 optimize_improve                ← a little better, continue
strategy_select  indices=[0,2] (excluded strategy 1)   ← round 2: the review excluded a conflicting strategy
checkpoint       37->22 optimize_improve                ← big improvement
strategy_select  indices=[0] (conservative single pick)← round 3: the review judged the combo too risky
checkpoint       22->14 optimize_improve                ← better again
optimize_stop    reason=no_improvement                 ← round 4 didn't get faster, converged and stopped
submit           final_level=2 final_latency=14         ← submit the 14-cycle version
```

After reading you can retell it: the free checkup optimized one round first -> baseline 38 -> three rounds, three choices (three-combo / exclusive two-combo / conservative single) -> 38->37->22->14 -> converged.

### 4. Practical commands (on the server)

```bash
cd /home/admin/fpga-agent

# Follow a run in real time (drop the 10s heartbeats)
tail -f runs/dotProduct_optimize/dotProduct_optimize.jsonl | grep -v heartbeat

# Show only decision events (the "story line" of a run)
grep -v heartbeat runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  grep -E 'route|checkpoint|strategy_select|optimize_|rollback|submit'

# Extract the optimization trajectory (old->new latency) with jq
grep checkpoint runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  jq -r 'select(.reason=="optimize_improve") | "\(.old_latency)->\(.new_latency)"'

# See how the review AI chose each round (including rejection reasons)
grep strategy_select runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  jq -c '{round, indices, rejected: [.rejected[]?.name], fallback}'

# See what errors this run reported (including the raw tool error text)
grep tool_result runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  jq -r 'select(.ok==false) | "\(.kind) \(.phase): \(.log[:200])"'

# per-call-site token attribution (from v0.7.0, DeepSeek backend)
grep llm_call runs/<task>/<task>.jsonl | \
  jq -r '[.purpose, .prompt_tokens, .completion_tokens, .reasoning_tokens] | @tsv'

# ── See what prompts the LLM actually received (from v0.7.2, prompts.jsonl) ──

# List the purpose and time of each call in this run
jq -r '[.ts, .purpose] | @tsv' runs/<task>/<task>_prompts.jsonl

# See the full user prompt of a given call (e.g. how the review AI was asked)
jq -r 'select(.purpose=="select_strategies") | .user' \
  runs/<task>/<task>_prompts.jsonl | less -S

# See the system prompt of a given call (the role setup)
jq -r 'select(.purpose=="select_strategies") | .system' \
  runs/<task>/<task>_prompts.jsonl | head -3

# See the full response of a given call (including reasons for rejected strategies)
jq -r 'select(.purpose=="select_strategies") | .response' \
  runs/<task>/<task>_prompts.jsonl | jq .

# Cross-reference the event log: prompts.jsonl and <task>.jsonl are linked by ts (timestamp)
```

### 5. Judge whether a run went well in 30 seconds

1. **checkpoint sequence**: are 0->1->2 all present? Missing 1 = correctness didn't pass; missing 2 = synth didn't pass
2. **latency trajectory**: is the `new_latency` of `optimize_improve` events going down? Not a single one = optimization produced nothing
3. **credit spent vs budget**: `submit.credit_spent` close to the budget = a struggle; far below = smooth
4. **strategy_select fallback**: `fallback=true` means the review AI's output couldn't be parsed (investigate)
5. **rollback events**: if one appears, optimization introduced a real problem that was rolled back (the mechanism is working, but investigate why)

## Event-Log Fields (summary table; see the guide above for details)

| Event type | Meaning |
|---|---|
| `route` | routing result (task_type -> level path) |
| `tool_result` | tool-call result (kind=csim/synth/cosim, phase, credit_spent) |
| `kb_search` | knowledge-base retrieval (query, hits, **hit_ids** from v0.7.0) |
| `review` / `mechanical_review` | LLM re-review / hard mechanical gate |
| `llm_call` | LLM call (purpose=extract_brief/propose_strategies/select_strategies/apply_strategies; from v0.7.0 carries model/prompt_tokens/completion_tokens/reasoning_tokens) |
| `strategy_select` | review-AI selection (indices/picked/rejected/fallback) |
| `checkpoint` | archive change (level, latency) |
| `submit` | final submission |

## Status

- `runs/projection_bugfix/`: the projection task, a real end-to-end repair (SCORE 1.400)
- `runs/dotProduct_optimize/`: the optimize loop, full score (SCORE 3.000, 73.36x)
- `runs/residual_stream_deadlock/`: a structural task (max SCORE 4.000, lat=6)
- `runs/vecadd_optimize/`: a new task (2026-07-20), DeepSeek full score (SCORE 1.000, lat=20, 68k tokens)
- `runs/fir_optimize/`, `runs/matmul_optimize/`: new tasks (2026-07-20), full score verified with scripted (2.000/3.000)
