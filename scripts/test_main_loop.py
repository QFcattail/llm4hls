#!/usr/bin/env python3
"""Offline unit tests for agent/main_loop.py (TC-AGENT-001 .. TC-AGENT-006).

No Vitis and no LLM API needed: FakeToolServer replays rule-based
ToolResults against a real harness Budget, and a prompt-sniffing canned
backend drives HLSLLMClient. The tests pin the v2.3 stage semantics
(agent-architecture.md §4.3-§4.5):

  TC-AGENT-001  synth failure -> repair loop -> csim re-verify -> synth pass,
                with a KB hit on the synth error signature
  TC-AGENT-002  optimize accepts a faster candidate, then stops on no
                improvement (same-level latency arbitration)
  TC-AGENT-003  optimize discards a candidate that breaks csim; best untouched
  TC-AGENT-004  structural: post-optimization cosim failure rolls the
                checkpoint back to the pre-optimization snapshot (§4.5)
  TC-AGENT-005  seed KB retrieval: error codes / keywords hit the right entries
  TC-AGENT-006  latency<=0 guard: a zero-latency synth report never enters
                the archive (dev-log 2026-07-17-01 known anomaly)

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
SAME100_CODE = BASE_CODE + "// SAME100 candidate\n"
BREAK_CODE = BASE_CODE + "// BREAK_CSIM\n"
FAST0_CODE = BASE_CODE + "// FAST0 zero-latency anomaly\n"

_STRATEGY_TEXT = (
    "1.\n"
    "name: pipeline accumulation loop\n"
    "rationale: add PIPELINE II=1 to the main loop\n"
    "gain: much lower cycle count\n"
    "risk: none\n"
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
        self.budget.charge("csim")
        self.csim_calls += 1
        if "BREAK_CSIM" in code:
            return ToolResult(kind="csim", ok=False, phase="runtime_fail",
                              return_code=1, log="Test Case 1 Failed!\n",
                              elapsed_s=9.7)
        return ToolResult(kind="csim", ok=True, phase="pass", return_code=0,
                          log="", elapsed_s=9.7)

    def synth(self, code: str) -> ToolResult:
        self.budget.charge("synth")
        self.synth_calls += 1
        return self.synth_handler(code)

    def cosim(self, code: str) -> ToolResult:
        self.budget.charge("cosim")
        self.cosim_calls += 1
        return self.cosim_handler(code)


class CannedBackend:
    """Prompt-sniffing LLM backend: brief / strategies / review are fixed;
    repair and apply_strategy answers cycle through per-test code queues."""

    def __init__(self, repair_codes: list[str] | None = None,
                 apply_codes: list[str] | None = None,
                 review: str = "PASS", brief: str = "sequential accumulation") -> None:
        self.repair_codes = repair_codes or []
        self.apply_codes = apply_codes or []
        self.review = review
        self.brief = brief
        self._ri = 0
        self._ai = 0

    @staticmethod
    def _cycle(queue: list[str], i: int) -> str | None:
        if not queue:
            return None
        return queue[min(i, len(queue) - 1)]

    def complete(self, system: str, user: str) -> str:
        if "Summarize this design" in user:
            return self.brief
        if "Propose 2-4 optimization strategies" in user:
            return _STRATEGY_TEXT
        if "Reply PASS or FAIL" in user:
            return self.review
        if "## Apply this strategy" in user:
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
    print("TC-AGENT-002 PASS  optimize accepted 100->60, stopped on no improvement")


def tc_003() -> None:
    """TC-AGENT-003: optimize discards a csim-breaking candidate; best kept."""
    task = FakeTask(type="optimize")
    server = FakeToolServer(total=40)
    events: list = []
    agent = _make_agent(task, server,
                        CannedBackend(repair_codes=[BASE_CODE],
                                      apply_codes=[BREAK_CODE]),
                        events, max_optimize_rounds=2)
    final = agent.run()

    assert final == BASE_CODE, "best must stay the baseline after discards"
    discards = [f for e, f in events
                if e == "optimize_discard" and f.get("reason") == "csim_broken"]
    assert len(discards) == 2, f"expected 2 csim_broken discards, got {discards}"
    submits = [f for e, f in events if e == "submit"]
    assert submits[0]["final_latency"] == 100
    print("TC-AGENT-003 PASS  csim-breaking candidates discarded, best untouched")


def tc_004() -> None:
    """TC-AGENT-004: structural rollback on post-optimization cosim failure."""
    task = FakeTask(id="fake_structural", type="structural",
                    requires_cosim=True, budget=80)
    server = FakeToolServer(total=80)

    def synth_handler(code: str) -> ToolResult:
        return _synth_result(True, code, 60 if "FAST60" in code else 100)

    def cosim_handler(code: str) -> ToolResult:
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


def main() -> int:
    """Run all TC-AGENT cases; return 0 iff every one passes."""
    cases = [tc_001, tc_002, tc_003, tc_004, tc_005, tc_006]
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
