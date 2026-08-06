> [中文](agent-code-design.cn.md)

# Agent Code Detailed Design (Code Design)

> Status: v1 (2026-07-15)
> Corresponding code version: P2 milestone
> Architecture design basis: [agent-architecture.md](./agent-architecture.md)
>
> **The code guide (one-line module responsibilities, reading order, function-list quick reference) has been moved to [`agent/README.md`](../../agent/README.md), colocated with the code so you can read it directly while reading the code.**
>
> This document retains **design-level content**: cross-module detailed dependency analysis, data-flow diagrams, and design-decision records.

---

## 1. Dependency Graph

```
                    run_agent.py (driver)
                    │
                    ├── agent.main_loop.Agent
                    │       ├── agent.router (route, RunPlan)
                    │       ├── agent.checkpoint (Checkpoint, Level)
                    │       ├── agent.feedback (build_feedback, Feedback)
                    │       ├── agent.llm_client (HLSLLMClient, Strategy)
                    │       ├── agent.mechanical_checks (mechanical_review)
                    │       ├── agent.observability (Logger, Heartbeat)
                    │       └── agent.knowledge_base (KnowledgeBase)
                    │
                    ├── agent.deepseek_client.DeepSeekClient   (injected as backend)
                    │
                    └── llm4hls.* (harness: Task/Budget/ToolServer/grade/load_task)
```

### Layering

| Layer | Module | Responsibility | Dependencies |
|---|---|---|---|
| **Driver layer** | run_agent.py | CLI entry, parse args, assemble agent | agent + harness |
| **Core layer** | main_loop.py | Main loop: correctness/synth/optimize | router, checkpoint, feedback, llm_client, mechanical_checks, observability, knowledge_base |
| **Strategy layer** | router.py | Pick gate path by task_type | none (pure data) |
| **Data structure** | checkpoint.py | Checkpoint judgment | none (pure data) |
| **Adapter layer** | feedback.py, llm_client.py, mechanical_checks.py, deepseek_client.py | Format conversion / interface adaptation | harness ToolResult |
| **Infrastructure layer** | observability.py, knowledge_base/ | Logging / RAG | none (independent) |
| **External** | harness (llm4hls.*) | Tool calls / billing / scoring | vitis-run |

### Coupling notes

- main_loop depends on all agent modules + harness. It is the single "hub".
- Agent modules **try not to depend on each other**: checkpoint/router/feedback/observability/knowledge_base are all independent and individually testable.
- The only bidirectional coupling: llm_client consumes feedback's output format, but via parameter passing (does not directly import the feedback module).
- deepseek_client is replaceable -- it implements the same `complete(system, user) -> str` interface as ScriptedClient/OpenRouterClient.

---

## 2. Overview Data Flow

```
Task package (task.toml + .cpp + .h + _tb.cpp)
    │
    ▼ load_task()
Task object ────────────────────────────────────────────┐
    │                                                  │
    ▼ route()                    ToolServer ◄── Budget │
RunPlan                            │  csim/synth/cosim │
    │                              │  (spend credit)    │
    ▼                              ▼                    │
Agent.run() ──► _reach_correctness ──► ToolServer.csim(code)
    │                                      │
    │                                      ▼ ToolResult{kind, ok, phase, log, report}
    │                                      │
    │  ◄───────────────────────────────────┘
    │
    ├── build_feedback(result) ──► Feedback{phases, error_codes, signatures, log_tail}
    │                                  │
    ├── _kb_lookup(fb) ──► KnowledgeBase.search(signatures) ──► KBEntry[]
    │                                  │
    ├── _repair_with_review:
    │     llm.repair(task, code, feedback_text, kb_text) ──► new_code
    │     mechanical_review(orig, new_code, task) ──► (ok, issues)
    │     llm.review(task, new_code, focus) ──► (passed, issues)
    │                                  │
    ├── checkpoint.should_accept(level, latency) ──► bool
    │     ckpt.accept(code, level, latency)
    │                                  │
    ▼                                  │
  (loop back to csim until it passes)  │
    │                                  │
    ▼ (correctness met)                │
  _do_synth ──► ToolServer.synth(code)─┘
    │
    ▼ (synth passes; fix loop preserves correctness re-verification)
  _optimize ──► extract_design_brief(cached) + propose_strategies + apply_strategy
    │           + double-gate review + csim/synth re-verification + same-level latency best-pick
    ▼ (tasks needing cosim)
  _post_opt_cosim_recheck ──► on failure, real rollback to pre-optimization snapshot
    │
    ▼
  return ckpt.code ──► grade() ──► Scorecard
```

---

## 3. Key Design-Decision Records

| Decision | Rationale | Source |
|---|---|---|
| Fork harness, don't rewrite | The official ToolServer is already an in-process function call; the evaluation interface is locked; rebuilding yields no benefit | harness analysis |
| Single process, no RPC | subprocess running vitis already gives process isolation; the agent itself is serial with no concurrency need | architecture discussion |
| Double-layer review (mechanical + LLM) | Measured: DeepSeek self-check missed signature changes (adding a param was judged PASS); mechanical check is 100% reliable backstop | measured finding |
| Checkpoint level monotonically non-decreasing | The scoring formula is layered (correct gate 0.5 > synth 0.2 > PPA 0.3); the checkpoint rules map naturally | user reasoning |
| Linear + backtracking re-verification | Changing code to fix a later bug may break earlier gates; must re-verify; the checkpoint mechanism auto-rolls-back | architecture §5 |
| DeepSeek max_tokens=16384 | For reasoning models reasoning_tokens count against max_tokens; too small truncates (17×23 alone spent 59 reasoning tokens) | measured finding |
| Cross-validation does not count tokens for now | First iteration only pursues correctness; token optimization is the second iteration | user decision |
| Functional-pattern retrieval deferred to second iteration | High implementation complexity; first close the loop with error-signature matching | user decision |
| optimize extracts design brief before changing (extract_design_brief) | AMD Phase 1: without design context the LLM only gives generic advice; "extract the design doc first, then improve" | user decision 2026-07-18 |
| synth fix re-verifies csim before synth | 1 credit is cheaper than 4 credits; changing synth may break correctness (§5) | architecture v2.3 |
| Strategy selection takes the first | First iteration fixed heuristic; the LLM tends to rank the most confident first; re-propose each round | architecture v2.3 |
| Real rollback to snapshot on post-optimization cosim failure | The original implementation only logged and did not restore, would submit with deadlock; snapshot includes code/level/latency/cosim_ok | measured finding (code review) |

---

## Change Log

| Date | Change | By |
|---|---|---|
| 2026-07-18 | v1.2. Synced with v0.2.0 implementation: §2 data-flow optimize segment changed from "(P4)" to the real chain (design-brief cache + strategies + double gate + re-verification + same-level best-pick + real rollback); §3 decision record added 4 rows (design-brief extraction / synth re-verify csim first / take first strategy / real rollback). Corresponds to agent-architecture.md v2.3. | Agent lead |
| 2026-07-15 | v1.1. Code-guide section moved to agent/README.md (colocated with code). This document retains cross-module design analysis + data flow + decision records. | Agent lead |
| 2026-07-15 | v1 initial draft. Based on the P2 milestone code version; detailed all modules' function lists, coupling, and data flow. | Agent lead |
