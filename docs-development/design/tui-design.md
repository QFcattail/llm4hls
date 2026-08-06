> [中文](tui-design.cn.md)

# TUI Interactive Dashboard Design (TUI Design)

> Status: v5 (2026-07-19, submit scoring panel + last-5-scores history + zone-B stage-aware rules)
> Framework: Textual + Rich
> Data source: agent/observability.py Logger event stream + harness transcript + grade() Scorecard

---

## 1. Design Goals

Display the agent's running status in real time, answering four questions:
1. **Where is it now** (flow chart + highlight current stage)
2. **What did the last tool report** (a dedicated zone, showing gcc-style error line numbers + content)
3. **What is it doing now** (LLM streaming chain-of-thought + code / tool-call status)
4. **How many resources have been spent** (credit / token / call count / review opinions)

---

## 2. Layout (four zones, top to bottom)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Zone A: flow chart (top, fixed height)                              │
│  ┌──────┐    ┌────────────┐    ┌──────┐    ┌────────┐    ┌────────┐ │
│  │route │───►│ correctness │───►│ synth │───►│optimize│───►│ submit │ │
│  │ ✅ 2s │    │  ✅ 45s     │    │ 🔄 NOW│    │  ⚪    │    │  ⚪    │ │
│  └──────┘    └────────────┘    └──────┘    └────────┘    └────────┘ │
│                csim×3 2218tok        ↑ CURRENT                        │
├─────────────────────────────────────────────────────────────────────┤
│  Zone B: last tool error (fixed height, dedicated bar; from v4 reused │
│  as the strategy panel during the optimize stage)                    │
│                                                                       │
│  (non-optimize stage, on tool failure):                              │
│  📋 [csim] compile_error  (3 errors)                                  │
│    1. projection.cpp:1:2: error: invalid preprocessing directive      │
│    2. projection.cpp:4:17: error: unknown type name 'Triangle_3D'    │
│    ...and 1 more errors                                               │
│                                                                       │
│  (optimize stage: strategy panel ≤2 lines + tool area ≤3 lines coexist, §3.2)│
│  🎯 3 strategies: 1.pipeline acc  2.array partition  3.unroll x4      │
│  ▶ selector picked 1+2: confirmed compatible, biggest combined gain   │
│  ✅ [csim] pass (9.7s)                                                │
├─────────────────────────────────────────────────────────────────────┤
│  Zone C: current activity (middle, adaptive height, main visual area) │
│                                                                       │
│  ▸ repair LLM call... elapsed 8.2s                                    │
│  💭 The csim failed because z is missing the third term...           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ triangle_2d->z = triangle_3d.z0 / 3                            │ │
│  │     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  (during a tool call: ▸ [synth] running synthesis... elapsed 12.3s)   │
├─────────────────────────────────────────────────────────────────────┤
│  Zone D: resource panel (bottom, fixed 2 lines)                       │
│                                                                       │
│  credits: 6/10 left 4  ████████░░░░░░  │  tokens: 3453 (reasoning 1007) │
│  stage: tools 1, reviews 0  │  total LLM: 2 calls  │  last review: PASS │
└─────────────────────────────────────────────────────────────────────┘
```

**v2 layout change notes** (based on real usage feedback):
- **Added Zone B**: the last tool error gets its own bar. Previously it was crammed into the third line of the status bar, where there wasn't enough space and only the generic `runtime_fail` could be shown. Now, as a dedicated bar, it can show gcc-style line numbers + error content.
- **Zone D slimmed to 2 lines**: after moving "last tool error" to Zone B, the status bar no longer needs a third line. Only credit/token and call count/review are kept.
- **Zone C's thinking and code merged**: no longer two separate panels; output continuously in the same stream. Thinking refreshes in real time (token by token); code is line-buffered + syntax-highlighted.

---

## 3. The Three Zones in Detail

### 3.1 Zone A: flow chart (top)

**Displayed content**: the agent's 5 stages, arranged horizontally, annotated with status and elapsed time.

| Stage | Status symbol | Meaning |
|---|---|---|
| `⚪` | Not started | Haven't reached this step yet |
| `🔄` | In progress | Currently running (highlighted, blinking) |
| `✅` | Done | Passed; annotate with elapsed time |
| `❌` | Failed | Did not pass; annotate with failure reason |
| `⏭️` | Skipped | Skipped due to insufficient budget or other reasons |

Below each stage, annotate the **per-stage stats**:
- route: `2s` (elapsed time)
- correctness: `csim×3 2218tok` (tool-call count + LLM tokens)
- synth: `synth×1 4cr` (tool-call count + credits)
- optimize: `opt×2 1500tok`
- submit: `SCORE 1.400` (from v5 a real score, from grade(); shows `grading...` while grading)

**Stage labels**: from v3 all use English stage names (`route`/`correctness`/`synth`/`optimize`/`submit`); the current stage is marked `↑ CURRENT`.

**Interaction**: press `1`-`5` to jump to the corresponding stage's detailed log.

### 3.2 Zone B: last tool error + optimize strategy panel (fixed height, dedicated bar)

**Displayed content**: the result and error details of the most recent tool call (csim/synth/cosim); from v4 the upper space is reused during the optimize stage to show the strategy panel.

**On tool failure** (extract gcc-style error lines from the log):
```
📋 [csim] compile_error  (3 errors)
  1. projection.cpp:1:2: error: invalid preprocessing directive
  2. projection.cpp:4:17: error: unknown type name 'Triangle_3D'
  3. projection.cpp:4:42: error: unknown type name 'Triangle_2D'
  ...and 1 more errors
```

**On tool pass**:
```
✅ [csim] pass (9.7s)
```

**Error-line extraction logic**:
- Match the `file:line:col: error: ...` format (gcc/clang compile errors)
- Match Vitis error codes like `[XFORM 203-313]`, `[SIM 211-2]`
- Match lines containing `ERROR`/`error`/`fail`/`Failed`
- Show at most 5 lines (shrinks to 3 when the optimize stage has the strategy panel); beyond that show "...and N more errors"
- On runtime_fail (not a compile error), show the test-case failure message

**Why a dedicated bar**: gcc compile errors are usually long (line number + error type + context) and cannot be shown in one status-bar line. A dedicated bar lets both the LLM and the user clearly see "what the last tool reported".

#### Zone B stage-aware rules (added v5)

User-reported confusion: "when review reports a signature mismatch, the error tab only shows a waiting message, and you can't tell which stage you're in". Three rules:

1. **Review failure enters the tool area**: when mechanical_review fails (e.g. signature mismatch), the tool area immediately shows `🔍 [review] <first issue>` (yellow title), as visible as a tool error -- no longer hidden only in the status bar's last-review field. A subsequent review pass or the next tool result naturally overwrites it.
2. **Ready line follows the sub-stage**: when the optimize stage has no strategy data, the ready line no longer fixedly shows "proposing strategies..."; instead it follows the `llm_call` event's purpose: `extracting design brief...` -> `proposing strategies...` -> `selector reviewing...` -> `applying picked...`. The user always knows what the LLM is doing.
3. **Waiting line carries a stage label**: the tool-area waiting message changes from `(waiting for tool call...)` to `(<stage>) waiting for tool call...` (driven by the stage hint from `phase_enter`); even in non-optimize stages you can see the current stage at a glance.

#### Reused as the strategy panel during the optimize stage (added v4)

**Reason for reuse**: in the optimize loop, every tool call (csim/synth re-verify) is preceded by a review gate, and tool results are mostly pass -- the error bar is largely idle during the optimize stage. Meanwhile, optimize's "how many strategies were proposed, which ones the review AI picked, and why" is exactly the information that needs to be persistently displayed (Zone A's stat slot can't fit 2-4 strategy names in one line, and streaming output scrolls past and is lost).

**Coexistence layout** (total zone height unchanged at 7 lines = 5 content lines): strategy area ≤2 lines + tool area ≤3 lines.
```
🎯 3 strategies: 1.pipeline acc  2.array partition  3.unroll x4
▶ selector picked 1+2: confirmed compatible, biggest combined gain
✅ [csim] pass (9.7s)
```
- **Strategy line 1 (🎯)**: the `all` field of the `strategy_select` event (all candidate strategy names, numbered + truncated)
- **Strategy line 2 (▶)**: the same event's `picked` (the subset the review AI selected, joined with `+`) + truncated `reason`; on combo-failure fallback, the `optimize_fallback` event rewrites it to `▶ fallback: strategy 1 only (combo failed)`
- **Tool area**: as usual shows running / pass / error details; on candidate verification failure (optimize_discard) the error is shown normally -- the strategy panel does not cover real errors
- After the optimize stage ends (`phase_exit`), the strategy area is cleared and the tool area takes all 5 lines (restoring non-optimize behavior)

**State-driven rendering (v4 implementation note)**: ToolErrorBar changed from a one-shot `update()` to internal state (`_strategy_lines` + `_tool_parts`) + `_rebuild()` concatenation rendering (same render model as StatusBar). Otherwise the `show_running` heartbeat from `_refresh_ui` every 150ms would erase the strategy lines. Public method signatures unchanged (`show_result`/`show_running`/`clear_bar`); added `show_strategies(all_names, picked, reason)`.

### 3.3 Zone C: current activity (middle, adaptive height, main visual)

**This is the largest zone; it shows different content depending on what is happening:**

#### C-1. During an LLM call (repair / review / propose_strategies)

**Chain-of-thought + code output continuously in the same zone** (no longer two separate panels):
```
▸ repair LLM call... elapsed 8.2s
💭 The csim failed because z is missing the third term...    ← refreshes in real time, token by token
triangle_2d->z = triangle_3d.z0 / 3                          ← code, syntax-highlighted
     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;
```

**Implementation notes**:
- thinking uses a Static (`ap-thinking-live`) for real-time overlay display, refreshing on every token (no line break)
- complete thinking lines (on `\n`) are written to RichLog and retained
- code is line-buffered + cpp syntax-highlighted, written to the same RichLog
- thinking uses dim italic (gray, unchanged under the v3 light theme); code uses the `github-light` highlight theme (changed from monokai in v3, since monokai is a dark theme and hard to read on a white background)
- after output completes, automatically switches to "waiting for tool verification" state

#### C-2. During a tool call (csim / synth / cosim)

```
▸ [synth] running synthesis... elapsed 14.7s
  running: vitis-run --mode hls --tcl run_hls.tcl
  (waiting for result...)
```

#### C-3. Idle / waiting

```
▸ idle, waiting for next step...
  last activity: 3.2s ago (csim pass)
```

### 3.4 Zone D: resource panel (bottom, fixed 2 lines)

**Line 1: budget**
```
credits: 6/10 left 4  ████████░░░░░░  │  tokens: 3453 (reasoning 1007)
```
- Left: credit usage bar (used/total + visualized progress bar)
- Right: cumulative tokens (prompt + completion); in parentheses, reasoning tokens

**Line 2: call stats + review**
```
stage: tools 1, reviews 0  │  total LLM: 2 calls  │  last review: PASS
```
- "stage" means stats within the current stage
- The three segments are separated by `│`
- Placeholder when there is no error/no review is `(none)` (changed from a Chinese placeholder in v3)
- **On stage transition, last review / last error resets to `(none)`** (added v5): the previous stage's review result must not carry over to the next stage, or it would be misread as a current failure

---

## 3.5 Theme Colors and UI Language (added v3)

### Color spec (Theme: `fpga-light`)

| Role | Color value | Usage |
|---|---|---|
| Primary | `#587559` (gray-green) | Title bar, exit-dialog border, active-panel title text, credits text |
| Accent / decorative | `#FDD100` (golden yellow) | The four zone borders (decorative), current-stage highlight, running status, credit progress-bar fill |
| Background / surface | `#FFFFFF` (white) | Global background |
| Foreground (normal text) | `#000000` (black) | Normal text previously using white (status-bar stats, tool-log raw text) |
| CoT chain-of-thought | gray unchanged | `dim italic` / `$text-muted`, naturally gray on white |
| Semantic colors | green=pass, red=error retained | Express semantics, not decorative |

Implementation: Textual 8.x custom `Theme` (`dark=False`); in `AgentDashboard.__init__` call `register_theme()` + `self.theme = "fpga-light"`. All Rich inline styles using `"white"` are changed to `"black"`; `"yellow"`/`"cyan"` decorative highlights are replaced with `#FDD100`/`#587559` respectively.

The code syntax-highlight theme is changed from `monokai` (dark) to `github-light` (light), to match the white background.

### UI copy language

From v3 **all UI copy is in English** (stage labels, status lines, error summaries, idle hints, etc.). Document language is unchanged (design documents remain primarily Chinese per convention).

---

## 3.6 Score and Convergence History (added v5)

**Problem**: after the agent finishes, the TUI only shows DONE and does not show the score -- the user can't see the result or the convergence across multiple runs. Root cause: the TUI only calls `agent.run()` and never calls `grade()` (scoring happens in the CLI driver).

**Design**:

1. **Scoring timing**: the agent thread, after `agent.run()` returns and before emitting the `done` event, calls the harness `grade()` (hidden testbench + PPA, does not consume budget, about 1-2 minutes). During this, Zone C shows `grading hidden testbench...`, and the flow-chart submit stage shows 🔄.
2. **Score display**: when grade completes, emit a `score` event -> the submit stage stat shows `SCORE x.xxx`; Zone C prints the full Scorecard (functional/synth/cosim, baseline vs candidate latency, acceleration, resources, SCORE).
3. **Convergence history**: each scoring appends a line to `runs/<task_id>/scores.jsonl` (ts/score/latency/credits/tokens); Zone C prints the **last-5-scores table** (including this one) after the Scorecard, making the convergence trend across multiple tuning/rerun attempts clear at a glance. The CLI driver (run_agent.py) writes to the same file after scoring; the two entry points share history.
4. **DONE line**: shows total elapsed time (`time.monotonic() - _start_time`), fixing "elapsed 0.0s".

```
=== Scorecard: dotProduct_optimize (difficulty 3) ===
  functional (hidden TB): PASS
  ...
  SCORE                 : 3.000

recent scores (dotProduct_optimize):
  2026-07-18 22:41  SCORE 3.000  lat=14  credits=25  tokens=53210
  2026-07-19 14:18  SCORE 3.000  lat=45  credits=10  tokens=22881
```

---

## 4. Data-Source Mapping

All TUI data comes from existing modules; no agent-logic changes are needed:

| TUI display | Data source | Existing/new |
|---|---|---|
| Flow-chart status + elapsed time | Logger's `phase_enter`/`phase_exit` events | ✅ existing |
| Current activity (tool call) | Logger's `tool_result` event + heartbeat's `stage` | ✅ existing |
| LLM streaming output | DeepSeek API `stream: true` + SSE parsing | 🆕 needs deepseek_client change |
| Credit usage | `Budget.spent` / `Budget.total` | ✅ existing |
| Token stats | `DeepSeekClient.total_prompt/completion/reasoning` | ✅ existing |
| Call count this stage | Filter the transcript by kind and count | ✅ existing |
| Last tool error | The most recent `tool_result`'s `phase` + `log_tail` | ✅ existing |
| Last review opinion | The most recent `review` event's `issues` | ✅ existing |
| Strategy panel (Zone B, optimize) | `strategy_select` event's `all`/`picked`/`reason` + `optimize_fallback` event | ✅ v4 existing |
| Ready-line sub-stage (Zone B) | `llm_call` event's `purpose` field | 🆕 v5 new |
| Submit score | `score` event emitted after the agent thread calls `grade()` | 🆕 v5 new |
| Last 5 scores | `runs/<task_id>/scores.jsonl` (appended by both CLI/TUI entry points) | 🆕 v5 new |

**The only thing that needs adding**: change the DeepSeek API to stream mode (`stream: true`), returning reasoning_content and content token by token. This is the prerequisite for Zone B's streaming output.

---

## 5. Interaction Design

| Key | Function |
|---|---|
| `q` / `Ctrl+C` | Quit (the agent keeps running in the background; quitting the TUI does not interrupt the agent) |
| `1`-`5` | Jump to the corresponding stage's detailed log |
| `l` | View the full JSONL log (paged) |
| `t` | View the transcript (tool-call history) |
| `r` | Refresh (manually triggered; normally auto-refreshes) |
| `↑`/`↓` | Scroll the current zone's output |

---

## 6. Technical Plan

### 6.1 Framework

- **Textual**: TUI framework, providing layout (Container/Widget), event loop, CSS styling
- **Rich**: rendering engine (Textual uses Rich underneath), providing color, tables, progress bars, syntax highlighting, Markdown

### 6.2 Dependencies

```
textual>=0.40.0
rich>=13.0.0
```

Install into the server venv: `pip install textual rich`

### 6.3 Architecture

```
agent main loop (unchanged)
  │
  ├── Logger.event(...)  ──► JSONL file (unchanged, existing)
  │                    ──► TUI event bus (new, in-memory queue)
  │
  └── DeepSeekClient (switch to stream mode)
        │
        ├── per-token output ──► TUI streaming-output area (new callback)
        └── full response ──► Logger (unchanged)
```

**Key design**: the TUI does not change agent logic; it only consumes the Logger's event stream. The agent runs in the background; the TUI is an "observer".

### 6.4 Implementation Split

| Module | Responsibility | Estimated effort |
|---|---|---|
| `tui/app.py` | Textual App main entry, layout assembly | 0.5 day |
| `tui/flow_chart.py` | Zone A: flow-chart widget | 0.5 day |
| `tui/activity_panel.py` | Zone B: current activity + streaming output | 1 day |
| `tui/status_bar.py` | Zone C: resource panel | 0.5 day |
| `agent/deepseek_client.py` | Add stream mode + callback | 0.5 day |
| `agent/observability.py` | Add TUI event bus (in-memory queue) | 0.5 day |
| Integration + debugging | | 1 day |
| **Total** | | **about 4-5 days** |

---

## 7. Things Not Done

- ❌ Web version (Textual is good enough; a web version doubles dev effort)
- ❌ Remote access (the TUI runs on the server, viewed over SSH; no browser remote)
- ❌ History replay (only view the current run; view history via JSONL logs)
- ❌ Editing features (the TUI only observes; no interactive code editing)

---

## 8. Implementation Timing

**Recommended to implement at the end of P2 or the start of P3**, prerequisites:
1. Core agent functionality is stable (dotProduct + residual tasks pass)
2. The knowledge base has basic entries
3. DeepSeek stream mode is verified usable

The TUI is an experience optimization, not a functional necessity. First make do with `tail -f` on the JSONL log (already available); invest in TUI development after the agent is stable.

---

## Change Log

| Date | Change | By |
|---|---|---|
| 2026-07-15 | v1 initial draft. Designed a three-zone layout (flow chart / current activity / resource panel) based on the user's UI description. | Agent lead |
| 2026-07-17 | v2 four-zone redesign: tool error gets its own bar (Zone B), thinking+code merged streaming output, resource panel slimmed to 2 lines. | Agent lead |
| 2026-07-18 | v3 added §3.5 theme colors (`fpga-light`: primary `#587559` / accent `#FDD100` / white background black text / CoT gray unchanged); all UI copy changed to English; code-highlight theme monokai -> `github-light`. | Agent lead |
| 2026-07-18 | v4 Zone B reused as the strategy panel during the optimize stage (user decision: that stage's tools are mostly pass, the error bar is idle; Zone A's stat slot can't fit multiple strategy names): strategy area ≤2 lines + tool area ≤3 lines coexist, errors not covered; ToolErrorBar changed to state-driven rendering (to prevent the 150ms heartbeat show_running from erasing strategy lines). Data-source table added `strategy_select`/`optimize_fallback`. Pairs with agent-architecture v2.4 (strategy combination + review AI). | Agent lead |
| 2026-07-19 | v5 two items (user feedback): ① submit scoring panel -- the agent thread calls grade() after running, submit stat shows SCORE, Zone C prints the Scorecard + last-5-scores history (runs/<task>/scores.jsonl shared by both entry points), DONE line adds total elapsed time; ② Zone B three stage-aware rules -- mechanical review failure enters the tool area, the ready line follows the llm_call sub-stage, the waiting line carries a stage label. | Agent lead |
