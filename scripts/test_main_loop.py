#!/usr/bin/env python3
"""Offline unit tests for agent/main_loop.py (TC-AGENT-001 .. TC-AGENT-019).

No Vitis and no LLM API needed: FakeToolServer replays rule-based
ToolResults against a real harness Budget, and a prompt-sniffing canned
backend drives HLSLLMClient. The tests pin the v2.3/v2.4/v2.8 stage
semantics (agent-architecture.md §4.3-§4.5):

  TC-AGENT-001  synth failure -> repair loop -> csim re-verify -> synth pass,
                with a KB hit on the synth error signature
  TC-AGENT-002  optimize accepts a faster candidate, then stops on no
                improvement (same-level latency arbitration)
  TC-AGENT-003  optimize csim failure -> repair loop (v2.8) -> exhausted,
                best untouched
  TC-AGENT-004  structural: post-optimization cosim failure rolls the
                checkpoint back to the pre-optimization snapshot (§4.5)
  TC-AGENT-005  seed KB retrieval: error codes / keywords hit the right entries
  TC-AGENT-006  latency<=0 guard: a zero-latency synth report never enters
                the archive (dev-log 2026-07-17-01 known anomaly)
  TC-AGENT-007  v2.4: selector picks a compatible PAIR -> combined candidate
                accepted (strategy combo, dual confirmation)
  TC-AGENT-008  v2.4: combo fails -> optimize_fallback -> first strategy
                alone accepted (combo attribution)
  TC-AGENT-009  v2.4 TUI: ToolErrorBar strategy panel coexists with tool
                errors; the 150ms show_running heartbeat cannot wipe it
  TC-AGENT-018  v2.8: latency unreachable (lat=0) -> optimize skipped,
                no token spent
  TC-AGENT-019  v2.8: optimize csim failure -> repair (feedback+KB) -> success

Usage:
    python3 scripts/test_main_loop.py
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))                                # for `agent`
sys.path.insert(0, str(ROOT / "contest" / "fpt26-harness"))  # for `llm4hls`

from llm4hls.budget import Budget                            # noqa: E402
from llm4hls.report import SynthReport                       # noqa: E402
from llm4hls.tools import ToolResult                         # noqa: E402

from agent.knowledge_base import KnowledgeBase, seed_entries  # noqa: E402
from agent.llm_client import HLSLLMClient                    # noqa: E402
from agent.main_loop import Agent                            # noqa: E402


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------

BASE_CODE = (
    '#include "dotProduct.h"\n'
    "int dotProduct(int a[16], int b[16]) {\n"
    "  int r = 0;\n"
    "  for (int i = 0; i < 16; i++) r += a[i] * b[i];\n"
    "  return r;\n"
    "}\n"
)
FIXED_CODE = BASE_CODE + "// FIXED\n"
FAST60_CODE = BASE_CODE + "// FAST60 optimized\n"
FAST55_CODE = BASE_CODE + "// FAST55 combo optimized\n"
FAST70_CODE = BASE_CODE + "// FAST70 fallback optimized\n"
SAME100_CODE = BASE_CODE + "// SAME100 candidate\n"
BREAK_CODE = BASE_CODE + "// BREAK_CSIM\n"
FAST0_CODE = BASE_CODE + "// FAST0 zero-latency anomaly\n"

_STRATEGY_TEXT = (
    "1.\n"
    "name: pipeline accumulation loop\n"
    "rationale: add PIPELINE II=1 to the main loop\n"
    "gain: much lower cycle count\n"
    "risk: none\n"
    "combinable_with: 2\n"
    "2.\n"
    "name: array partition\n"
    "rationale: partition both input arrays for parallel reads\n"
    "gain: fewer memory stalls\n"
    "risk: more LUTs\n"
    "combinable_with: 1\n"
)


@dataclass
class FakeTask:
    """Minimal Task stand-in covering what the agent stack touches."""

    id: str = "fake_task"
    type: str = "optimize"
    requires_cosim: bool = False
    kernel_code: str = BASE_CODE
    kernel_name: str = "dotProduct.cpp"
    top: str = "dotProduct"
    description: str = "Compute the dot product of two 16-element vectors."
    headers: dict = field(
        default_factory=lambda: {"dotProduct.h": "int dotProduct(int a[16], int b[16]);\n"}
    )
    budget: int = 40


def _synth_result(ok: bool, code: str, lat: int | None = 100,
                  log: str = "") -> ToolResult:
    """Build a synth ToolResult, optionally with a SynthReport at `lat`."""
    report = None
    if ok:
        res = {"LUT": 10, "FF": 8, "DSP": 1, "BRAM_18K": 0, "URAM": 0}
        report = SynthReport(
            clock_period_ns=5.0, latency_best=lat, latency_avg=lat,
            latency_worst=lat, interval_min=1, interval_max=1,
            resources=res, available=dict(res), utilization=dict(res),
        )
    return ToolResult(kind="synth", ok=ok, phase="pass" if ok else "synth_error",
                      return_code=0 if ok else 1, log=log, elapsed_s=42.0,
                      report=report)


class FakeToolServer:
    """Rule-based ToolServer: csim fails on BREAK_CSIM; synth/cosim delegate
    to per-test handler closures. Charges a real Budget like the harness."""

    def __init__(self, total: int = 40) -> None:
        self.budget = Budget(total=total)
        self.csim_calls = 0
        self.synth_calls = 0
        self.cosim_calls = 0
        self.synth_handler = lambda code: _synth_result(True, code, 100)
        self.cosim_handler = lambda code: ToolResult(
            kind="cosim", ok=True, phase="pass", return_code=0, log="",
            elapsed_s=120.0)

    def csim(self, code: str) -> ToolResult:
        """Charge 1 credit and pass unless the code carries BREAK_CSIM."""
        self.budget.charge("csim")
        self.csim_calls += 1
        if "BREAK_CSIM" in code:
            return ToolResult(kind="csim", ok=False, phase="runtime_fail",
                              return_code=1, log="Test Case 1 Failed!\n",
                              elapsed_s=9.7)
        return ToolResult(kind="csim", ok=True, phase="pass", return_code=0,
                          log="", elapsed_s=9.7)

    def synth(self, code: str) -> ToolResult:
        """Charge 4 credits and delegate to the per-test synth handler."""
        self.budget.charge("synth")
        self.synth_calls += 1
        return self.synth_handler(code)

    def cosim(self, code: str) -> ToolResult:
        """Charge 20 credits and delegate to the per-test cosim handler."""
        self.budget.charge("cosim")
        self.cosim_calls += 1
        return self.cosim_handler(code)


class CannedBackend:
    """Prompt-sniffing LLM backend: brief / strategies / review / select are
    fixed; repair and apply_strategies answers cycle through per-test queues."""

    def __init__(self, repair_codes: list[str] | None = None,
                 apply_codes: list[str] | None = None,
                 review: str = "PASS", brief: str = "sequential accumulation",
                 select_pick: str = "1",
                 select_reason: str = "confirmed compatible",
                 select_replies: list[str] | None = None,
                 propose_reply: str | None = None) -> None:
        self.repair_codes = repair_codes or []
        self.apply_codes = apply_codes or []
        self.review = review
        self.brief = brief
        self.select_pick = select_pick
        self.select_reason = select_reason
        # Optional full-control reply queue for the selector (overrides
        # select_pick/select_reason when non-empty; cycles on the last).
        self.select_replies = select_replies or []
        # Optional full-control propose reply (defaults to _STRATEGY_TEXT).
        self.propose_reply = propose_reply
        self.select_calls = 0
        self.last_apply_prompt = ""
        self._ri = 0
        self._ai = 0

    @staticmethod
    def _cycle(queue: list[str], i: int) -> str | None:
        if not queue:
            return None
        return queue[min(i, len(queue) - 1)]

    def complete(self, system: str, user: str) -> str:
        """Dispatch a canned reply based on the prompt's task phrase.

        Args:
            system: Ignored (kept for the harness LLMClient contract).
            user: The user prompt; sniffed for each domain method's marker.

        Returns:
            The canned response for the matched call type, or "" when no
            marker matches (which makes the caller's parser return None).
        """
        if "Summarize this design" in user:
            return self.brief
        if "## Your task\nTwo steps. FIRST, feasibility review" in user:
            self.select_calls += 1
            if self.select_replies:
                return self._cycle(self.select_replies, self.select_calls - 1)
            return f"PICK: {self.select_pick}\nREASON: {self.select_reason}"
        if "Propose 2-4 optimization strategies" in user:
            return self.propose_reply or _STRATEGY_TEXT
        if "Reply PASS or FAIL" in user:
            return self.review
        if "## Apply these strategies" in user:
            self.last_apply_prompt = user
            code = self._cycle(self.apply_codes, self._ai)
            self._ai += 1
            return f"```cpp\n{code}```" if code is not None else ""
        if "Return a corrected kernel" in user:
            code = self._cycle(self.repair_codes, self._ri)
            self._ri += 1
            return f"```cpp\n{code}```" if code is not None else ""
        return ""


def _make_agent(task: FakeTask, server: FakeToolServer, backend: CannedBackend,
                events: list, **agent_kwargs) -> Agent:
    """Assemble an Agent with seed KB and an event-capturing log wrapper."""
    run_dir = Path(tempfile.mkdtemp(prefix="agent_test_"))
    agent = Agent(task, server, HLSLLMClient(backend),
                  kb=KnowledgeBase(seed_entries()), run_dir=run_dir,
                  **agent_kwargs)
    original_event = agent.log.event

    def capture(event: str, **fields) -> None:
        """Record the event for assertions, then forward to the real log."""
        events.append((event, fields))
        original_event(event, **fields)

    agent.log.event = capture
    return agent


# --------------------------------------------------------------------------
# Test cases
# --------------------------------------------------------------------------

def tc_001() -> None:
    """TC-AGENT-001: synth repair loop + KB hit on the synth error signature."""
    task = FakeTask(type="repair")
    server = FakeToolServer(total=40)
    state = {"synths": 0}

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        state["synths"] += 1
        if state["synths"] == 1:
            return _synth_result(
                False, code,
                log="ERROR: [XFORM 203-313] cannot be scheduled: dataflow conflict\n")
        return _synth_result(True, code, 100)

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[FIXED_CODE]),
                        events, max_optimize_rounds=0)
    agent.run()

    assert server.synth_calls == 2, f"expected 2 synth calls, got {server.synth_calls}"
    hits = [f for e, f in events if e == "kb_search" and f.get("hits", 0) >= 1]
    assert hits, "expected a kb_search event with >=1 hit on the synth error"
    ckpts = [f for e, f in events if e == "checkpoint" and f.get("new") == 2]
    assert ckpts, "expected a checkpoint event archiving Level.SYNTH"
    submits = [f for e, f in events if e == "submit"]
    assert submits and submits[0]["final_level"] == 2, \
        f"final level should be SYNTH(2), got {submits}"
    assert submits[0]["final_latency"] == 100
    print("TC-AGENT-001 PASS  synth repair loop archived Level.SYNTH, KB hit recorded")


def tc_002() -> None:
    """TC-AGENT-002: optimize accepts faster, then stops on no improvement."""
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        if "FAST60" in code:
            return _synth_result(True, code, 60)
        return _synth_result(True, code, 100)

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[FAST60_CODE, SAME100_CODE]),
                        events)
    final = agent.run()

    assert final == FAST60_CODE, "best should be the 60-cycle candidate"
    assert server.synth_calls == 3, \
        f"baseline + 2 candidates = 3 synths, got {server.synth_calls}"
    stops = [f for e, f in events if e == "optimize_stop"]
    assert any(s.get("reason") == "no_improvement" for s in stops), \
        f"expected optimize_stop no_improvement, got {stops}"
    improves = [f for e, f in events
                if e == "checkpoint" and f.get("reason") == "optimize_improve"]
    assert improves and improves[0]["new_latency"] == 60
    selects = [f for e, f in events if e == "strategy_select"]
    assert selects and selects[0]["indices"] == [0], \
        f"selector should pick strategy 1 (index 0): {selects}"
    assert len(selects[0]["all"]) == 2, "both proposed strategies reach the TUI"
    print("TC-AGENT-002 PASS  optimize accepted 100->60, stopped on no improvement")


def tc_003() -> None:
    """TC-AGENT-003: optimize discards a csim-breaking candidate; best kept.

    v2.8 semantics: a single-strategy candidate that breaks csim now enters
    a repair loop (feedback + KB injection) before being discarded. With the
    backend always returning the broken code, repairs exhaust and the best
    stays the baseline.
    """
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=80)
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[BREAK_CODE]),
                        events, max_optimize_rounds=2, max_opt_repair=2)
    final = agent.run()

    assert final == BASE_CODE, "best must stay the baseline after discards"
    repairs = [f for e, f in events if e == "optimize_repair"]
    assert len(repairs) == 2, \
        f"expected 2 repair attempts (max_opt_repair=2), got {len(repairs)}"
    assert all(r.get("reason") == "csim_broken" for r in repairs), \
        f"repairs must be csim_broken: {repairs}"
    discards = [f for e, f in events
                if e == "optimize_discard" and f.get("reason") == "csim_broken"]
    assert len(discards) == 1, f"expected 1 final csim_broken discard, got {discards}"
    stops = [f for e, f in events if e == "optimize_stop"]
    assert stops and stops[0].get("reason") == "failed", \
        f"repair exhaustion must stop the loop: {stops}"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 100
    print("TC-AGENT-003 PASS  csim-breaking candidate repaired x2 then discarded, best untouched")


def tc_004() -> None:
    """TC-AGENT-004: structural rollback on post-optimization cosim failure."""
    task = FakeTask(id="fake_structural", type="structural",
                    requires_cosim=True, budget=80)
    server = FakeToolServer(total=80)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        return _synth_result(True, code, 60 if "FAST60" in code else 100)

    def cosim_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        if "FAST60" in code:   # optimization reintroduces a deadlock
            return ToolResult(kind="cosim", ok=False, phase="cosim_fail",
                              return_code=1, log="deadlock detected in RTL sim\n",
                              elapsed_s=300.0)
        return ToolResult(kind="cosim", ok=True, phase="pass", return_code=0,
                          log="", elapsed_s=300.0)

    server.synth_handler = synth_handler
    server.cosim_handler = cosim_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[FAST60_CODE]),
                        events, max_optimize_rounds=1)
    final = agent.run()

    assert final == BASE_CODE, "rollback must restore the cosim-verified code"
    assert server.cosim_calls == 2, \
        f"correctness cosim + recheck = 2, got {server.cosim_calls}"
    rollbacks = [f for e, f in events if e == "rollback"]
    assert any(r.get("reason") == "optimization_reintroduced_hazard"
               for r in rollbacks), f"missing hazard rollback: {rollbacks}"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 100, \
        "latency must roll back to the snapshot value (100), not keep 60"
    print("TC-AGENT-004 PASS  cosim hazard -> real snapshot rollback (code+latency)")


def tc_005() -> None:
    """TC-AGENT-005: seed KB retrieval hits the intended entries."""
    kb = KnowledgeBase(seed_entries())
    cases = [
        (["[XFORM 203-313]"], "synth-xform-dataflow-conflict"),
        (["cannot be scheduled"], "synth-ii-scheduling-fail"),
        (["deadlock"], "cosim-deadlock-fifo-burst"),
        (["test case"], "csim-test-case-failed"),
        (["failed"], "csim-test-case-failed"),
        (["compile_error"], "csim-compile-error"),
    ]
    for signatures, want_id in cases:
        hits = kb.search(signatures)
        ids = [h.id for h in hits]
        assert want_id in ids, f"{signatures} -> {ids}, want {want_id}"
    assert kb.search(["no-such-signature-xyz"]) == []
    assert kb.search([]) == []
    print(f"TC-AGENT-005 PASS  {len(kb.entries)} seed entries, all probes hit")


def tc_006() -> None:
    """TC-AGENT-006: latency<=0 guard — zero latency never enters the archive."""
    zero = _synth_result(True, BASE_CODE, 0).report
    assert Agent._valid_latency(zero) is None, "latency 0 must be treated as missing"
    assert Agent._valid_latency(_synth_result(True, BASE_CODE, 100).report) == 100

    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        # candidate reports the anomalous zero; baseline reports 100
        return _synth_result(True, code, 0 if "FAST0" in code else 100)

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[FAST0_CODE]),
                        events, max_optimize_rounds=1)
    final = agent.run()

    assert final == BASE_CODE, "zero-latency candidate must not be archived"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 100, \
        f"archive must keep baseline 100, got {submits[0]['final_latency']}"
    print("TC-AGENT-006 PASS  latency=0 rejected; archive keeps baseline 100")


def tc_007() -> None:
    """TC-AGENT-007: selector picks a compatible PAIR; combo candidate accepted."""
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        return _synth_result(True, code, 55 if "FAST55" in code else 100)

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[FAST55_CODE],
                                      select_pick="1,2"),
                        events, max_optimize_rounds=1)
    final = agent.run()

    assert final == FAST55_CODE, "combined candidate should be archived"
    selects = [f for e, f in events if e == "strategy_select"]
    assert selects and selects[0]["indices"] == [0, 1], \
        f"selector picked the pair: {selects}"
    assert len(selects[0]["picked"]) == 2
    assert not [f for e, f in events if e == "optimize_fallback"], \
        "combo succeeded on first try; no fallback expected"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 55
    print("TC-AGENT-007 PASS  selector combo (1+2) applied and accepted 100->55")


def tc_008() -> None:
    """TC-AGENT-008: combo fails -> optimize_fallback -> first strategy accepted."""
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        return _synth_result(True, code, 70 if "FAST70" in code else 100)

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(
        task, server,
        CannedBackend(repair_codes=[BASE_CODE],
                      # combo candidate breaks csim; fallback candidate wins
                      apply_codes=[BREAK_CODE, FAST70_CODE],
                      select_pick="1,2"),
        events, max_optimize_rounds=1)
    final = agent.run()

    assert final == FAST70_CODE, "fallback candidate should be archived"
    fallbacks = [f for e, f in events if e == "optimize_fallback"]
    assert len(fallbacks) == 1 and len(fallbacks[0]["picked"]) == 1, \
        f"exactly one fallback to the first strategy: {fallbacks}"
    stops = [f for e, f in events if e == "optimize_stop"]
    assert not stops, f"fallback succeeded; no optimize_stop expected: {stops}"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 70
    print("TC-AGENT-008 PASS  combo failed -> fallback accepted 100->70")


def tc_009() -> None:
    """TC-AGENT-009: ToolErrorBar strategy panel + tool zone coexistence."""
    from tui.tool_error_bar import ToolErrorBar

    bar = ToolErrorBar()
    bar.update = lambda *a, **k: None   # headless: we assert on _build_render()
    err_log = "\n".join(f"kernel.cpp:{i}:{i}: error: boom{i}" for i in range(1, 8))

    # 1) no strategy panel: 3 error rows + header + "and N more" (5 rows max)
    bar.show_result("csim", "compile_error", False, 1.0, err_log)
    text = bar._build_render().plain
    assert text.count("boom") == 3 and "and 4 more errors" in text, text

    # 2) strategy panel shrinks the tool zone to 1 error row + more note
    bar.show_strategies(["pipeline acc", "array partition"],
                        ["pipeline acc", "array partition"],
                        "confirmed compatible")
    text = bar._build_render().plain
    lines = text.split("\n")
    assert "🎯 2 strategies" in lines[0]
    assert "▶ selector picked pipeline acc+array partition" in lines[1]
    assert text.count("boom") == 1 and "and 6 more errors" in text, text
    assert len(lines) == 5, f"strategy 2 + header 1 + err 1 + more 1 = 5: {lines}"

    # 3) heartbeat show_running must NOT wipe the strategy panel (v4 bug class)
    bar.show_running("synth", 3.0)
    text = bar._build_render().plain
    assert "🎯 2 strategies" in text and "running synthesis" in text, text

    # 4) fallback rewrites only the picked line
    bar.update_picked(["pipeline acc"], "fallback: combo failed")
    text = bar._build_render().plain
    assert "▶ selector picked pipeline acc: fallback: combo failed" in text

    # 5) clearing the panel restores the full 3-error tool zone
    bar.clear_strategies()
    bar.show_result("csim", "compile_error", False, 1.0, err_log)
    text = bar._build_render().plain
    assert "🎯" not in text and text.count("boom") == 3, text
    print("TC-AGENT-009 PASS  strategy panel coexists; heartbeat cannot wipe it")


# Real DeepSeek V4 Pro output shape captured from the 2026-07-18 dotProduct
# probe: "### Strategy N: Name" headings + bold labels on their own lines.
_MARKDOWN_STRATEGIES = """Here are three optimization strategies ordered by confidence.

---

### Strategy 1: Loop Pipelining (II = 1)

**Rationale**
Insert `#pragma HLS PIPELINE II=1` immediately before the loop.

**Expected latency gain**
~15x reduction (from ~16384 cycles to ~1030 cycles).

**Risk**
Very low. The only dependency is the running sum.

**Combinable with**
Strategy 2 and Strategy 3.

---

### Strategy 2: Full Unrolling by PAR_FACTOR with Array Partitioning

**Rationale**
Unroll factor=32 and partition both input arrays cyclic factor=32.

**Expected latency gain**
~400-500x reduction (to ~40-50 cycles).

**Risk**
Moderate to high. DSP count jumps from 1 to 32.

**Combinable with**
Strategy 1 (pipelining the unrolled loop).
"""


def tc_010() -> None:
    """TC-AGENT-010: _parse_strategies tolerates real LLM markdown output."""
    from agent.llm_client import _parse_strategies

    strategies = _parse_strategies(_MARKDOWN_STRATEGIES)
    names = [s.name for s in strategies]
    assert len(strategies) == 2, f"want exactly 2 real strategies, got {names}"
    assert names[0] == "Loop Pipelining (II = 1)", names
    assert names[1] == "Full Unrolling by PAR_FACTOR with Array Partitioning", names
    assert strategies[0].combinable_with == "Strategy 2 and Strategy 3."
    assert strategies[0].expected_gain.startswith("~15x")
    assert strategies[0].rationale.startswith("Insert `#pragma HLS PIPELINE")
    # old "1.\nname: x" label format still parses (regression guard)
    old = _parse_strategies(_STRATEGY_TEXT)
    assert len(old) == 2 and old[0].name == "pipeline accumulation loop"
    print("TC-AGENT-010 PASS  markdown strategies parsed, wrappers filtered")


def tc_011() -> None:
    """TC-AGENT-011: score history record / recent / format (tui-design §3.6)."""
    import tempfile
    from agent.score_history import (
        format_history, recent_scores, record_score,
    )

    path = Path(tempfile.mkdtemp(prefix="scores_test_")) / "scores.jsonl"
    assert recent_scores(path) == []
    assert "(none yet)" in format_history([], "dotProduct_optimize")

    for i, (score, lat) in enumerate([(1.4, None), (2.1, 100), (2.4, 60),
                                      (3.0, 22), (3.0, 14), (3.0, 45)]):
        record_score(path, score=score, latency=lat,
                     credits=10 + i, tokens=1000 * (i + 1))

    all_records = recent_scores(path, 10)
    assert len(all_records) == 6, f"expected 6 records, got {len(all_records)}"
    last5 = recent_scores(path, 5)
    assert len(last5) == 5 and last5[0]["score"] == 2.1, \
        "recent(5) must drop the oldest record"
    assert last5[-1]["latency"] == 45

    text = format_history(last5, "dotProduct_optimize")
    assert "recent scores (dotProduct_optimize):" in text
    assert "SCORE 2.100" in text and "lat=100" in text
    assert "credits=11" in text and "tokens=2000" in text
    # malformed lines are skipped, not fatal
    with path.open("a") as f:
        f.write("not-json\n")
    assert len(recent_scores(path, 6)) == 6
    print("TC-AGENT-011 PASS  score history: record/recent(5)/format/corrupt-safe")


_PROPOSE_JSON = (
    '{"strategies": ['
    '{"name": "pipeline loop", "rationale": "II=1", "gain": "big", '
    '"risk": "none", "combinable_with": "2,3"},'
    '{"name": "signature change hack", "rationale": "add an argument", '
    '"gain": "?", "risk": "breaks contract", "combinable_with": "standalone"},'
    '{"name": "array partition", "rationale": "parallel reads", "gain": "mid",'
    ' "risk": "LUTs", "combinable_with": "1"}]}'
)

_SELECT_JSON = (
    '{"review": [{"id": 1, "ok": true}, '
    '{"id": 2, "ok": false, "why": "changes top-level signature"}, '
    '{"id": 3, "ok": true}], '
    '"pick": [1, 3], "reason": "1 and 3 are compatible and sound"}'
)


def tc_012() -> None:
    """TC-AGENT-012: JSON propose/select parsing + rejected surfaced (v2.7)."""
    from agent.llm_client import _parse_select_json, _parse_strategies

    strategies = _parse_strategies(_PROPOSE_JSON)
    assert [s.name for s in strategies] == [
        "pipeline loop", "signature change hack", "array partition"]
    assert strategies[0].combinable_with == "2,3"

    indices, reason, rejected, fell_back = _parse_select_json(
        _SELECT_JSON, strategies)
    assert indices == [0, 2], indices
    assert not fell_back
    assert "compatible and sound" in reason
    assert rejected == [{"id": 2, "name": "signature change hack",
                         "why": "changes top-level signature"}]

    # pick naming ONLY rejected strategies is unusable -> None
    bad = _parse_select_json(
        '{"review": [{"id": 1, "ok": false, "why": "x"}], "pick": [1]}',
        strategies[:1])
    assert bad is None
    # garbage -> None (caller retries, then flagged fallback)
    assert _parse_select_json("not json at all", strategies) is None
    # legacy PICK/REASON text still accepted (no review list there)
    leg = _parse_select_json("PICK: 1,3\nREASON: legacy ok", strategies)
    assert leg == ([0, 2], "legacy ok", [], False)
    print("TC-AGENT-012 PASS  JSON select: pick+rejected parsed; fallbacks sane")


def tc_013() -> None:
    """TC-AGENT-013: fallback apply receives the failure feedback (v2.7)."""
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)

    def synth_handler(code: str) -> ToolResult:
        # combo candidate: synth fails with a pragma-scope error;
        # fallback candidate: passes at 70.
        if "FAST70" in code:
            return _synth_result(True, code, 70)
        if "BREAK_SYNTH" in code:
            return _synth_result(
                False, code,
                log="ERROR: [HLS 207-6969] '#pragma HLS' is only allowed "
                    "in function scope\n")
        return _synth_result(True, code, 100)

    server.synth_handler = synth_handler
    events: list = []
    backend = CannedBackend(
        repair_codes=[BASE_CODE],
        apply_codes=[BASE_CODE + "// BREAK_SYNTH\n", FAST70_CODE],
        select_replies=[
            '{"review": [{"id": 1, "ok": true}, {"id": 2, "ok": true}],'
            ' "pick": [1, 2], "reason": "compatible"}'],
    )
    agent = _make_agent(task, server, backend, events, max_optimize_rounds=1)
    final = agent.run()

    assert final == FAST70_CODE, "fallback candidate should be archived"
    assert "Previous attempt FAILED" in backend.last_apply_prompt, \
        "fallback apply must receive the failure feedback"
    assert "HLS 207-6969" in backend.last_apply_prompt, \
        "the feedback must carry the real synth error code"
    fallbacks = [f for e, f in events if e == "optimize_fallback"]
    assert len(fallbacks) == 1
    print("TC-AGENT-013 PASS  fallback apply got failure feedback (HLS 207-6969)")


def tc_014() -> None:
    """TC-AGENT-014: selector retry-once then flagged fallback (v2.7)."""
    # case A: first reply garbage, retry yields valid JSON -> real pick
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)
    server.synth_handler = lambda code: _synth_result(
        True, code, 60 if "FAST60" in code else 100)
    events: list = []
    backend = CannedBackend(
        repair_codes=[BASE_CODE],
        apply_codes=[FAST60_CODE],
        select_replies=["garbage, no json here",
                        '{"pick": [1], "reason": "retry worked"}'],
    )
    agent = _make_agent(task, server, backend, events, max_optimize_rounds=1)
    final = agent.run()
    assert final == FAST60_CODE
    assert backend.select_calls == 2, "one retry must be issued"
    selects = [f for e, f in events if e == "strategy_select"]
    assert selects and selects[0]["fallback"] is False and \
        selects[0]["indices"] == [0]

    # case B: both replies garbage -> flagged fallback to first strategy
    task2 = FakeTask(type="optimize")
    server2 = FakeToolServer(total=40)
    events2: list = []
    backend2 = CannedBackend(
        repair_codes=[BASE_CODE],
        apply_codes=[FAST60_CODE],
        select_replies=["garbage one", "garbage two"],
    )
    agent2 = _make_agent(task2, server2, backend2, events2,
                         max_optimize_rounds=1)
    agent2.run()
    selects2 = [f for e, f in events2 if e == "strategy_select"]
    assert selects2 and selects2[0]["fallback"] is True, \
        f"fallback must be flagged, got {selects2}"
    assert selects2[0]["indices"] == [0]
    print("TC-AGENT-014 PASS  selector: retry works; fallback flagged, not silent")


def tc_015() -> None:
    """TC-AGENT-015: non-structural final RTL recheck rolls back too (v2.7)."""
    task = FakeTask(type="optimize")   # requires_cosim=False
    server = FakeToolServer(total=40)

    server.synth_handler = lambda code: _synth_result(
        True, code, 60 if "FAST60" in code else 100)

    def cosim_handler(code: str) -> ToolResult:
        # the optimized candidate deadlocks at RTL level even though the
        # task's correctness gate does not require cosim
        if "FAST60" in code:
            return ToolResult(kind="cosim", ok=False, phase="cosim_fail",
                              return_code=1, log="deadlock in RTL sim\n",
                              elapsed_s=300.0)
        return ToolResult(kind="cosim", ok=True, phase="pass", return_code=0,
                          log="", elapsed_s=300.0)

    server.cosim_handler = cosim_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[FAST60_CODE]),
                        events, max_optimize_rounds=1)
    final = agent.run()

    assert final == BASE_CODE, \
        "RTL-failed optimized code must roll back even for non-structural tasks"
    assert server.cosim_calls == 1, \
        "exactly one final recheck (no cosim in correctness for this type)"
    rollbacks = [f for e, f in events if e == "rollback"]
    assert any(r.get("reason") == "optimization_reintroduced_hazard"
               for r in rollbacks)
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 100
    print("TC-AGENT-015 PASS  non-structural RTL recheck -> snapshot rollback")


class _KwBackend:
    """Kwargs-recording backend for token-mode policy assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, str]] = []  # (site, kwargs, user)

    def complete(self, system: str, user: str, **kwargs) -> str:
        if "Reply PASS or FAIL" in user:
            self.calls.append(("review", kwargs, user))
            return "PASS"
        if "Two steps. FIRST, feasibility review" in user:
            self.calls.append(("select", kwargs, user))
            return '{"pick": [1], "reason": "ok"}'
        if "Propose 2-4 optimization strategies" in user:
            self.calls.append(("propose", kwargs, user))
            return ('{"strategies": [{"name": "s1", "rationale": "r", '
                    '"gain": "g", "risk": "k"}]}')
        if "Summarize this design" in user:
            self.calls.append(("brief", kwargs, user))
            return "a brief"
        self.calls.append(("other", kwargs, user))
        return ""


def tc_016() -> None:
    """Token-mode policy: full sends no overrides (legacy behavior), graded
    modes send reasoning_effort to capable backends, the aggressive select
    prompt drops the spec block, and no-knob backends fall back cleanly."""
    task = FakeTask()

    # full: byte-identical legacy behavior — no reasoning_effort anywhere.
    be = _KwBackend()
    llm = HLSLLMClient(be, token_mode="full")
    llm.review(task, "code", "focus")
    strats = llm.propose_strategies(task, "code", "synth", "brief")
    llm.select_strategies(task, "code", strats, "synth", "brief")
    llm.extract_design_brief(task, "code")
    for site, kwargs, _ in be.calls:
        assert "reasoning_effort" not in kwargs, \
            f"full mode must not override effort ({site})"

    # balanced: review + select get "off"; propose/brief stay default.
    be = _KwBackend()
    llm = HLSLLMClient(be, token_mode="balanced")
    llm.review(task, "code", "focus")
    strats = llm.propose_strategies(task, "code", "synth", "brief")
    llm.select_strategies(task, "code", strats, "synth", "brief")
    llm.extract_design_brief(task, "code")
    by_site = {s: k for s, k, _ in be.calls}
    assert by_site["review"].get("reasoning_effort") == "off"
    assert by_site["select"].get("reasoning_effort") == "off"
    assert "reasoning_effort" not in by_site["propose"]
    assert "reasoning_effort" not in by_site["brief"]
    # select still carries the spec block in balanced mode
    sel_user = next(u for s, _, u in be.calls if s == "select")
    assert "## Kernel specification" in sel_user

    # aggressive: brief + propose also off; select drops the spec block.
    be = _KwBackend()
    llm = HLSLLMClient(be, token_mode="aggressive")
    llm.review(task, "code", "focus")
    strats = llm.propose_strategies(task, "code", "synth", "brief")
    llm.select_strategies(task, "code", strats, "synth", "brief")
    llm.extract_design_brief(task, "code")
    by_site = {s: k for s, k, _ in be.calls}
    for site in ("review", "select", "propose", "brief"):
        assert by_site[site].get("reasoning_effort") == "off", site
    sel_user = next(u for s, _, u in be.calls if s == "select")
    assert "## Kernel specification" not in sel_user

    # No-knob backend (CannedBackend.complete takes no kwargs): the graded
    # modes must degrade to a plain call instead of crashing.
    llm = HLSLLMClient(CannedBackend(review="PASS"), token_mode="balanced")
    passed, _ = llm.review(task, "code", "focus")
    assert passed, "TypeError fallback broken for no-knob backend"

    # Unknown mode is rejected.
    try:
        HLSLLMClient(be, token_mode="ludicrous")
        raise AssertionError("unknown token_mode accepted")
    except ValueError:
        pass

    print("TC-AGENT-016 PASS  token-mode policy: full=legacy, graded=off, "
          "fallback sane")


def tc_017() -> None:
    """TC-AGENT-017: verbatim prompt history lands in <task>_prompts.jsonl."""
    import json
    import tempfile
    from agent.observability import Logger

    # 1) Logger.prompt writes purpose + system + user + response verbatim.
    run_dir = Path(tempfile.mkdtemp(prefix="prompt_log_test_"))
    log = Logger("fake_task", run_dir)
    log.prompt("repair", "SYS", "USER-TEXT", "RESP-TEXT")
    lines = (run_dir / "fake_task_prompts.jsonl").read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["purpose"] == "repair" and rec["system"] == "SYS"
    assert rec["user"] == "USER-TEXT" and rec["response"] == "RESP-TEXT"

    # 2) A full agent run wires the recorder: every LLM call is captured
    #    with the right purpose tags, and the JSONL stays valid.
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)
    events: list = []
    run_dir2 = Path(tempfile.mkdtemp(prefix="agent_test_"))
    agent = Agent(task, server, HLSLLMClient(CannedBackend(
        repair_codes=[BASE_CODE], apply_codes=[FAST60_CODE])),
        kb=KnowledgeBase(seed_entries()), run_dir=run_dir2,
        max_optimize_rounds=1)
    agent.run()

    prompt_file = run_dir2 / "fake_task_prompts.jsonl"
    records = [json.loads(l) for l in prompt_file.read_text().splitlines()]
    purposes = [r["purpose"] for r in records]
    assert "repair" in purposes, purposes
    assert "extract_brief" in purposes, purposes
    assert "propose_strategies" in purposes, purposes
    assert "select_strategies" in purposes, purposes
    assert "apply_strategies" in purposes, purposes
    # every record carries the full triplet, including the kernel spec
    assert all(r["system"] and r["user"] and r["response"] for r in records)
    assert any("Kernel specification" in r["user"] for r in records)
    sel = [r for r in records if r["purpose"] == "select_strategies"][0]
    assert "feasibility review" in sel["user"]
    print("TC-AGENT-017 PASS  prompts.jsonl: all 5 purposes captured verbatim")


def tc_018() -> None:
    """TC-AGENT-018: latency unreachable -> optimize skipped.

    When the synth report yields latency 0 (combinational logic / the known
    parse anomaly), `_valid_latency` returns None. The PPA slice is not
    scorable (scoring.py treats 0 as falsy), so `_run_plan` must skip the
    optimize phase entirely instead of burning token/credit for zero gain.
    """
    task = FakeTask(type="repair")
    server = FakeToolServer(total=40)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        return _synth_result(True, code, 0)   # zero-latency -> None after filter

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[FIXED_CODE]),
                        events, max_optimize_rounds=4)
    final = agent.run()

    skips = [f for e, f in events if e == "optimize_skip"]
    assert skips and skips[0]["reason"] == "latency_unreachable", \
        f"expected optimize_skip latency_unreachable, got {skips}"
    # optimize must NOT have been entered: no phase_enter / propose_strategies
    enters = [f for e, f in events if e == "phase_enter"
              and f.get("phase") == "optimize"]
    assert not enters, f"optimize must not be entered, got {enters}"
    proposes = [f for e, f in events if e == "llm_call"
                and f.get("purpose") == "propose_strategies"]
    assert not proposes, "propose_strategies must not run when skipped"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] is None, \
        f"latency None must propagate to submit, got {submits[0]}"
    print("TC-AGENT-018 PASS  latency=0 -> optimize skipped (latency_unreachable)")


def tc_019() -> None:
    """TC-AGENT-019: optimize csim failure -> repair -> success.

    The first apply_strategies returns code that breaks csim (BREAK_CODE);
    the repair loop injects the csim feedback + KB hits and retries. The
    second apply returns FAST60_CODE, which passes csim+synth at latency 60
    and is archived. Symmetric with the correctness/synth repair loops.
    """
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=80)

    def synth_handler(code: str) -> ToolResult:
        """Per-test scripted response for this tool kind."""
        return _synth_result(True, code, 60 if "FAST60" in code else 100)

    server.synth_handler = synth_handler
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[BREAK_CODE, FAST60_CODE]),
                        events, max_optimize_rounds=1, max_opt_repair=2)
    final = agent.run()

    assert final == FAST60_CODE, \
        f"repair must recover FAST60, got {final!r}"
    repairs = [f for e, f in events if e == "optimize_repair"]
    assert len(repairs) == 1 and repairs[0]["reason"] == "csim_broken", \
        f"expected 1 csim_broken repair, got {repairs}"
    improves = [f for e, f in events
                if e == "checkpoint" and f.get("reason") == "optimize_improve"]
    assert improves and improves[0]["new_latency"] == 60, \
        f"expected optimize_improve to 60, got {improves}"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 60
    print("TC-AGENT-019 PASS  csim-broken -> repair w/ feedback+KB -> FAST60 accepted")


def main() -> int:
    """Run all TC-AGENT cases; return 0 iff every one passes."""
    cases = [tc_001, tc_002, tc_003, tc_004, tc_005, tc_006,
             tc_007, tc_008, tc_009, tc_010, tc_011, tc_012,
             tc_013, tc_014, tc_015, tc_016, tc_017, tc_018, tc_019]
    failed = 0
    for tc in cases:
        try:
            tc()
        except AssertionError as e:
            failed += 1
            print(f"{tc.__name__} FAIL  {e}")
    print(f"\n{len(cases) - failed}/{len(cases)} test cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
