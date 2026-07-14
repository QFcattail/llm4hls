"""LLM client — domain wrappers over the harness LLMClient Protocol.

Implements agent-architecture.md §8. The harness ships two backends:
ScriptedClient (offline, replays canned answers) and OpenRouterClient (real
open-source model). Both satisfy `complete(system, user) -> str`.

This module adds three domain methods used by the main loop:
    repair            -> fix a correctness/synth failure
    propose_strategies-> AMD Phase 2: list optimization strategies
    apply_strategy    -> AMD Phase 3: generate code for a chosen strategy
    review            -> cross-check (v2: another agent / self-check)

Output parsing reuses the harness _extract_code regex (a fenced ```cpp block).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Reuse the harness's code extraction so we match its conventions exactly.
try:
    from llm4hls.agent import _extract_code as _harness_extract  # type: ignore
except Exception:  # fallback if import path differs
    _CODE_RE = re.compile(r"```(?:cpp|c\+\+|c)?\s*\n(.*?)```", re.DOTALL)

    def _harness_extract(text: str) -> str | None:
        blocks = _CODE_RE.findall(text)
        if blocks:
            return blocks[0].strip() + "\n"
        stripped = text.strip()
        return stripped + "\n" if stripped else None


@dataclass
class Strategy:
    """One candidate optimization strategy from AMD Phase 2."""

    name: str
    rationale: str
    expected_gain: str   # qualitative, e.g. "halve latency via II=1"
    risk: str            # e.g. "may break dataflow ordering"


class HLSLLMClient:
    """Wraps a harness LLMClient with HLS-domain helpers.

    The underlying client is injected (ScriptedClient for offline dev,
    OpenRouterClient for real runs). This class never imports a backend.
    """

    def __init__(self, backend, max_review_retries: int = 1) -> None:
        self.backend = backend
        self.max_review_retries = max_review_retries

    # -- low-level --------------------------------------------------------
    def _complete(self, system: str, user: str) -> str:
        return self.backend.complete(system, user)

    # -- domain methods ---------------------------------------------------
    def repair(self, task, code: str, feedback_text: str, kb_text: str) -> str | None:
        """Ask for a corrected kernel. Returns code or None on parse failure."""
        system = _REPAIR_SYSTEM
        user = (
            f"## Kernel specification\n{task.description}\n\n"
            f"## Fixed header(s) (read-only)\n```cpp\n{_headers(task)}\n```\n\n"
            f"## Current kernel: {task.kernel_name}\n```cpp\n{code}\n```\n\n"
            f"## Knowledge-base hits\n{kb_text or '(none)'}\n\n"
            f"## Latest tool feedback\n{feedback_text}\n\n"
            f"## Your task\nReturn a corrected kernel that fixes the failure. "
            f"Do not change the top-level signature, header, or testbench. "
            f"Output ONLY the full kernel in one ```cpp block."
        )
        return _harness_extract(self._complete(system, user))

    def review(self, task, code: str, focus: str) -> tuple[bool, str]:
        """Cross-check a candidate before spending a tool call on it.

        Returns (passed, issues_text). First iteration uses the same backend
        with a reviewer prompt (self-check). Token cost is accepted per v2.
        """
        system = _REVIEW_SYSTEM
        user = (
            f"## Kernel under review: {task.kernel_name}\n```cpp\n{code}\n```\n\n"
            f"## Review focus\n{focus}\n\n"
            f"Reply PASS or FAIL. If FAIL, list concrete issues."
        )
        out = self._complete(system, user)
        passed = out.strip().upper().startswith("PASS")
        return passed, out

    def propose_strategies(self, task, code: str, synth_summary: str) -> list[Strategy]:
        """AMD Phase 2: ask for multiple optimization strategies with tradeoffs."""
        system = _STRATEGY_SYSTEM
        user = (
            f"## Kernel\n```cpp\n{code}\n```\n\n"
            f"## Current synthesis\n{synth_summary}\n\n"
            f"## Task\nPropose 2-4 optimization strategies. For each: name, "
            f"rationale, expected latency gain, and risk."
        )
        out = self._complete(system, user)
        return _parse_strategies(out)

    def apply_strategy(self, task, code: str, strategy: Strategy) -> str | None:
        """AMD Phase 3: generate code applying one strategy."""
        system = _REPAIR_SYSTEM
        user = (
            f"## Kernel\n```cpp\n{code}\n```\n\n"
            f"## Apply this strategy\n{strategy.name}: {strategy.rationale}\n"
            f"Expected: {strategy.expected_gain}; risk: {strategy.risk}\n\n"
            f"Output ONLY the full optimized kernel in one ```cpp block. "
            f"Keep the top-level signature unchanged."
        )
        return _harness_extract(self._complete(system, user))


# -- prompt templates (kept module-level so they're easy to tune) ----------
_REPAIR_SYSTEM = (
    "You are a senior Vitis 2025.2 HLS engineer targeting Alveo U55C @ 200 MHz. "
    "Keep designs functionally correct first, optimized second. Prefer general "
    "HLS techniques (PIPELINE, UNROLL, ARRAY_PARTITION, DATAFLOW) over hacks."
)

_REVIEW_SYSTEM = (
    "You are reviewing an HLS C++ kernel before it is spent on an expensive "
    "tool call. Check ONLY for: (1) top-level signature/interface unchanged, "
    "(2) obvious new bugs introduced by the edit, (3) HLS pragma hazards "
    "(e.g. mixing PIPELINE and DATAFLOW at the same level, dead streams). "
    "Be concise. Do not rewrite the code."
)

_STRATEGY_SYSTEM = (
    "You are an HLS design-space explorer. Given a kernel and its synthesis "
    "report, propose concrete optimization strategies with honest tradeoffs."
)


def _headers(task) -> str:
    return "\n".join(f"// {n}\n{c}" for n, c in task.headers.items())


def _parse_strategies(text: str) -> list[Strategy]:
    """Best-effort parse of a free-form strategy list into Strategy objects.

    The LLM is asked for a structured-ish list; we tolerate simple formats.
    """
    strategies: list[Strategy] = []
    # Split on blank-line-separated blocks or numbered headings.
    blocks = re.split(r"\n\s*(?:\d+[.)]|-{3,})\s*\n", text)
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        name_m = re.search(r"(?:name|strategy)\s*[:：]\s*(.+)", b, re.IGNORECASE)
        gain_m = re.search(r"(?:gain|expected|latency)\s*[:：]\s*(.+)", b, re.IGNORECASE)
        risk_m = re.search(r"risk\s*[:：]\s*(.+)", b, re.IGNORECASE)
        name = name_m.group(1).strip() if name_m else b.split("\n")[0][:60]
        strategies.append(Strategy(
            name=name,
            rationale=b[:200],
            expected_gain=gain_m.group(1).strip() if gain_m else "?",
            risk=risk_m.group(1).strip() if risk_m else "?",
        ))
    return strategies
