"""LLM client — domain wrappers over the harness LLMClient Protocol.

Implements agent-architecture.md §8. The harness ships two backends:
ScriptedClient (offline, replays canned answers) and OpenRouterClient (real
open-source model). Both satisfy `complete(system, user) -> str`.

This module adds six domain methods used by the main loop:
    repair              -> fix a correctness/synth failure
    review              -> cross-check (v2: another agent / self-check)
    extract_design_brief-> AMD Phase 1: distill the current kernel's design
    propose_strategies  -> AMD Phase 2: list strategies + compatibility notes
    select_strategies   -> AMD Phase 2 gate: reviewer picks compatible subset
    apply_strategies    -> AMD Phase 3: generate code for a strategy subset

Per §8.1's hard requirement, every code-changing prompt (repair /
propose_strategies / apply_strategy) injects the official design document
(task.description) and the read-only headers; the optimize pair additionally
receives the synth report and the design brief.

Output parsing reuses the harness _extract_code regex (a fenced ```cpp block).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

# Reuse the harness's code extraction so we match its conventions exactly.
try:
    from llm4hls.agent import _extract_code as _harness_extract  # type: ignore
except Exception:  # fallback if import path differs
    _CODE_RE = re.compile(r"```(?:cpp|c\+\+|c)?\s*\n(.*?)```", re.DOTALL)

    def _harness_extract(text: str) -> str | None:
        """Fallback code-block extractor used when the harness import fails."""
        blocks = _CODE_RE.findall(text)
        if blocks:
            return blocks[0].strip() + "\n"
        stripped = text.strip()
        return stripped + "\n" if stripped else None


@dataclass
class Strategy:
    """One candidate optimization strategy from AMD Phase 2.

    Attributes:
        name: Short label for the strategy.
        rationale: Human-readable justification of the approach.
        expected_gain: Qualitative expected benefit, e.g. "halve latency via II=1".
        risk: Qualitative risk of the approach, e.g. "may break dataflow ordering".
        combinable_with: Proposer-declared compatibility annotation (v2.4),
            e.g. "2,3" (indexes of strategies it composes with) or
            "standalone". The selector AI re-checks this before any combo is
            allowed (dual confirmation, architecture §4.4).
    """

    name: str
    rationale: str
    expected_gain: str   # qualitative, e.g. "halve latency via II=1"
    risk: str            # e.g. "may break dataflow ordering"
    combinable_with: str = ""   # proposer-declared compatibility (v2.4)


class HLSLLMClient:
    """Wraps a harness LLMClient with HLS-domain helpers.

    The underlying client is injected (ScriptedClient for offline dev,
    OpenRouterClient for real runs). This class never imports a backend.

    Attributes:
        backend: The injected LLMClient (must implement
            ``complete(system, user) -> str``).
        max_review_retries: Number of extra repair attempts allowed when the
            mechanical or LLM review rejects a candidate.
    """

    def __init__(self, backend, max_review_retries: int = 1) -> None:
        self.backend = backend
        self.max_review_retries = max_review_retries
        # Raw text of the latest propose_strategies reply, kept so the main
        # loop can log it when parsing looks suspicious (count <= 1).
        self.last_propose_raw: str = ""

    # -- low-level --------------------------------------------------------
    def _complete(self, system: str, user: str) -> str:
        """Forward a raw (system, user) completion call to the backend."""
        return self.backend.complete(system, user)

    def _complete_json(self, system: str, user: str) -> str:
        """Call the backend with JSON structured output when supported.

        DeepSeek natively supports ``response_format: json_object`` (probed
        2026-07-19); backends without that keyword (ScriptedClient, harness
        OpenRouterClient) are called plainly and their free-text reply is
        handled by the caller's legacy fallback parser.

        Args:
            system: System prompt text.
            user: User prompt text.

        Returns:
            The assistant's content string (expected to be JSON).
        """
        try:
            return self.backend.complete(
                system, user, response_format={"type": "json_object"})
        except TypeError:
            return self.backend.complete(system, user)

    # -- domain methods ---------------------------------------------------
    def repair(self, task, code: str, feedback_text: str, kb_text: str) -> str | None:
        """Ask for a corrected kernel. Returns code or None on parse failure.

        Args:
            task: Harness Task object (used for description, headers, kernel name).
            code: The current (failing) kernel source.
            feedback_text: Distilled tool feedback block to act on.
            kb_text: Knowledge-base hits text, or empty for none.

        Returns:
            The repaired kernel source extracted from the LLM response, or
            None if no code block could be parsed.
        """
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

        Args:
            task: Harness Task object (used for kernel name).
            code: The candidate kernel source to review.
            focus: Short text describing what the review should check.

        Returns:
            A (passed, issues_text) tuple where ``passed`` is True when the
            reviewer's reply starts with "PASS", and ``issues_text`` is the
            raw reviewer output.
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

    def extract_design_brief(self, task, code: str) -> str:
        """AMD Phase 1: distill the current kernel's design into a brief.

        Called once before the optimize loop (architecture §4.4); the result
        is cached by the caller and injected into every strategy prompt so
        proposals are grounded in the actual design, not generic advice.

        Args:
            task: Harness Task object (used for description, headers, name).
            code: The current (synthesizable) kernel source.

        Returns:
            The design brief as plain text (functionality / loop structure /
            dataflow / bottleneck hypotheses). Returns "" on empty reply.
        """
        system = _BRIEF_SYSTEM
        user = (
            f"## Kernel specification\n{task.description}\n\n"
            f"## Fixed header(s) (read-only)\n```cpp\n{_headers(task)}\n```\n\n"
            f"## Current kernel: {task.kernel_name}\n```cpp\n{code}\n```\n\n"
            f"## Your task\nSummarize this design in under 200 words: "
            f"(1) what it computes, (2) loop nest structure and trip counts, "
            f"(3) dataflow / streaming between stages, (4) where the latency "
            f"bottleneck most likely is and which HLS lever (PIPELINE, UNROLL, "
            f"ARRAY_PARTITION, DATAFLOW) addresses it. Do NOT output code."
        )
        return self._complete(system, user).strip()

    def propose_strategies(self, task, code: str, synth_summary: str,
                           design_brief: str = "") -> list[Strategy]:
        """AMD Phase 2: ask for multiple optimization strategies with tradeoffs.

        Args:
            task: Harness Task object.
            code: The current synthesized kernel source.
            synth_summary: Current synthesis report summary text.
            design_brief: Cached design brief from extract_design_brief
                (empty string when unavailable).

        Returns:
            A list of parsed Strategy objects (may be empty on parse failure).
        """
        system = _STRATEGY_SYSTEM
        user = (
            f"## Kernel specification\n{task.description}\n\n"
            f"## Fixed header(s) (read-only)\n```cpp\n{_headers(task)}\n```\n\n"
            f"## Design brief (extracted from the current kernel)\n"
            f"{design_brief or '(none)'}\n\n"
            f"## Kernel\n```cpp\n{code}\n```\n\n"
            f"## Current synthesis\n{synth_summary}\n\n"
            f"## Task\nPropose 2-4 optimization strategies targeting lower "
            f"latency on the Alveo U55C @ 200 MHz, ordered by confidence "
            f"(best first). Respect the interface contract above.\n"
            f"Return STRICT JSON only (no prose outside the JSON):\n"
            f'{{"strategies": [{{"name": "short name", "rationale": "why", '
            f'"gain": "expected latency gain", "risk": "what could go wrong", '
            f'"combinable_with": "numbers of OTHER strategies it does not '
            f'interfere with, or \'standalone\'"}}]}}'
        )
        out = self._complete_json(system, user)
        self.last_propose_raw = out   # kept for parse-failure diagnostics
        return _parse_strategies(out)

    def select_strategies(self, task, code: str, strategies: list[Strategy],
                          synth_summary: str, design_brief: str = "",
                          ) -> tuple[list[int], str, list[dict], bool]:
        """Selector review AI: feasibility + compatibility review, then pick.

        A second self-check (same model, reviewer prompt). v2.7: each
        strategy first gets a feasibility verdict (interface unchanged /
        functionality unbroken / synthesizable / resources fit); poisoned
        plans are rejected with a reason. The pick is a compatible subset of
        the SURVIVING strategies (dual confirmation, architecture §4.4).

        On structured-output parse failure the selector is retried once; if
        that also fails it falls back to the first strategy and the fallback
        is FLAGGED (never silent) so the operator can see it.

        Args:
            task: Harness Task object.
            code: The current kernel source.
            strategies: The proposed Strategy list (1-based for the LLM).
            synth_summary: Current synthesis report summary text.
            design_brief: Cached design brief (empty string when unavailable).

        Returns:
            A 4-tuple ``(indices, reason, rejected, fell_back)``: 0-based
            indexes into ``strategies`` (never empty), the one-line pick
            rationale, the list of rejected strategy dicts
            (``{"id", "name", "why"}``), and True when the answer came from
            the parse-failure fallback rather than a real selection.
        """
        system = _SELECT_SYSTEM
        catalog = "\n".join(
            f"{i + 1}. {s.name}\n"
            f"   rationale: {s.rationale}\n"
            f"   expected: {s.expected_gain}; risk: {s.risk}\n"
            f"   proposer claims combinable_with: {s.combinable_with or '?'}"
            for i, s in enumerate(strategies)
        )
        user = (
            f"## Kernel specification\n{task.description}\n\n"
            f"## Design brief\n{design_brief or '(none)'}\n\n"
            f"## Current synthesis\n{synth_summary}\n\n"
            f"## Proposed strategies\n{catalog}\n\n"
            f"## Your task\nTwo steps. FIRST, feasibility review: for each "
            f"strategy, judge whether the PLAN ITSELF is sound — it must keep "
            f"the top-level signature/interface unchanged, keep functionality "
            f"correct, be synthesizable, and fit the device. Reject poisoned "
            f"plans with a reason. SECOND, pick the strategy or compatible "
            f"combination (from the SOUND ones) most likely to lower latency. "
            f"A combination is allowed only when the strategies do not "
            f"interfere (pragma rules: no PIPELINE+DATAFLOW at the same "
            f"level, no conflicting partitions, no dead streams).\n"
            f"Return STRICT JSON only:\n"
            f'{{"review": [{{"id": 1, "ok": true}}, '
            f'{{"id": 2, "ok": false, "why": "reason"}}], '
            f'"pick": [1], "reason": "one line"}}'
        )
        for attempt in range(2):   # one retry on parse failure, then fallback
            out = self._complete_json(system, user)
            parsed = _parse_select_json(out, strategies)
            if parsed is not None:
                return parsed
        # Fallback: first strategy, explicitly flagged (never silent).
        return ([0], "", [], True)

    def apply_strategies(self, task, code: str, strategies: list[Strategy],
                         design_brief: str = "",
                         failure_feedback: str = "") -> str | None:
        """AMD Phase 3: generate code applying a (compatible) strategy subset.

        The subset was dually confirmed non-interfering by the proposer and
        the selector (architecture §4.4); a single strategy is the N=1 case.

        Args:
            task: Harness Task object.
            code: The current kernel source to transform.
            strategies: The selected Strategy subset to apply together.
            design_brief: Cached design brief from extract_design_brief
                (empty string when unavailable).
            failure_feedback: Optional distilled feedback from the failed
                previous attempt (error codes + log tail, v2.7). Injected so
                the LLM avoids repeating the mistake.

        Returns:
            The optimized kernel source extracted from the LLM response, or
            None if no code block could be parsed.
        """
        system = _REPAIR_SYSTEM
        plan = "\n".join(
            f"{i + 1}. {s.name}: {s.rationale}\n"
            f"   expected: {s.expected_gain}; risk: {s.risk}"
            for i, s in enumerate(strategies)
        )
        combo_note = (
            "These strategies were confirmed non-interfering by both the "
            "proposer and an independent reviewer; apply ALL of them together."
            if len(strategies) > 1 else
            "Apply this single strategy."
        )
        feedback_block = (
            f"\n\n## Previous attempt FAILED — avoid these mistakes\n"
            f"{failure_feedback}\n" if failure_feedback else ""
        )
        user = (
            f"## Kernel specification\n{task.description}\n\n"
            f"## Fixed header(s) (read-only)\n```cpp\n{_headers(task)}\n```\n\n"
            f"## Design brief\n{design_brief or '(none)'}\n\n"
            f"## Kernel\n```cpp\n{code}\n```\n\n"
            f"## Apply these strategies\n{plan}\n\n{combo_note}"
            f"{feedback_block}\n"
            f"Output ONLY the full optimized kernel in one ```cpp block. "
            f"Keep the top-level signature and the interface contract "
            f"unchanged. Do not modify other function calls."
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
    "You are an HLS design-space explorer. Given a kernel, its design brief, "
    "and its synthesis report, propose concrete optimization strategies with "
    "honest tradeoffs. Respect the interface contract: the top-level "
    "signature and headers are read-only."
)

_BRIEF_SYSTEM = (
    "You are a senior Vitis HLS engineer. Read an HLS C++ kernel and its "
    "specification, then distill the design's structure and likely latency "
    "bottleneck. Be concrete: name loops, arrays, streams, and pragmas. "
    "Output plain prose, no code."
)

_SELECT_SYSTEM = (
    "You are a skeptical HLS design reviewer. Given a list of proposed "
    "optimization strategies, select the best one — or a combination only "
    "when the strategies genuinely do not interfere. Check pragma "
    "interaction rules strictly (no PIPELINE+DATAFLOW at the same level, no "
    "conflicting array partitions, no dead streams). Be conservative: when "
    "in doubt, pick a single strategy."
)


def _headers(task) -> str:
    """Render a task's headers as a combined comment-delimited block."""
    return "\n".join(f"// {n}\n{c}" for n, c in task.headers.items())


def _parse_strategies(text: str) -> list[Strategy]:
    """Parse a strategy list, JSON first with a legacy free-text fallback.

    Primary path: the JSON schema requested via structured output
    (``{"strategies": [...]}``). Fallback: the free-text regex parser for
    backends without JSON mode (ScriptedClient, older prompts).
    """
    strategies = _parse_strategies_json(text)
    if strategies:
        return strategies
    return _parse_strategies_text(text)


def _parse_strategies_json(text: str) -> list[Strategy]:
    """Parse the structured-output JSON strategy list (empty list on miss)."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    items = data.get("strategies") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    strategies: list[Strategy] = []
    for it in items:
        if not isinstance(it, dict) or not it.get("name"):
            continue
        strategies.append(Strategy(
            name=str(it["name"])[:80],
            rationale=str(it.get("rationale", ""))[:200],
            expected_gain=str(it.get("gain", "?")),
            risk=str(it.get("risk", "?")),
            combinable_with=str(it.get("combinable_with", "")),
        ))
    return strategies


def _parse_select_json(text: str, strategies: list[Strategy],
                       ) -> tuple[list[int], str, list[dict], bool] | None:
    """Parse the selector's JSON reply into (indices, reason, rejected, False).

    Args:
        text: The selector AI's raw reply (expected strict JSON; the legacy
            "PICK: ... / REASON: ..." text format is accepted as fallback).
        strategies: The proposed strategies (for id validation and naming
            the rejected entries).

    Returns:
        A 4-tuple ``(indices, reason, rejected, False)`` on success — the
        trailing False marks "NOT a fallback" (the caller's fallback path
        returns True). Returns None when the reply is neither usable JSON
        nor legacy text format.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None
    if not isinstance(data, dict):
        # Legacy "PICK: 1,2 / REASON: x" text path (no review list there).
        if _PICK_RE.search(text):
            return (_parse_pick(text, len(strategies)),
                    _parse_reason(text), [], False)
        return None
    rejected: list[dict] = []
    review = data.get("review")
    if isinstance(review, list):
        for item in review:
            if not isinstance(item, dict):
                continue
            if item.get("ok") is False:
                sid = item.get("id")
                name = (strategies[sid - 1].name
                        if isinstance(sid, int) and 1 <= sid <= len(strategies)
                        else f"#{sid}")
                rejected.append({"id": sid, "name": name,
                                 "why": str(item.get("why", ""))})
    rejected_ids = {r["id"] for r in rejected if isinstance(r["id"], int)}
    picks: list[int] = []
    raw_pick = data.get("pick")
    if isinstance(raw_pick, list):
        for tok in raw_pick:
            if isinstance(tok, (int, float)):
                idx = int(tok) - 1
                if 0 <= idx < len(strategies) and idx not in picks:
                    picks.append(idx)
    if not picks:
        return None
    # A pick that names only rejected strategies is unusable.
    if all((i + 1) in rejected_ids for i in picks):
        return None
    return (picks, str(data.get("reason", ""))[:200], rejected, False)


def _parse_strategies_text(text: str) -> list[Strategy]:
    """Legacy free-text strategy parser (fallback when JSON mode is absent).

    Tolerates the shapes real LLMs emit (verified against DeepSeek samples):
    "1." alone, "#### 2. Name", "### Strategy 1: Name", "Strategy 1: Name",
    "- Strategy 1: Name", "1 — Name" (em/en dash; a plain hyphen is NOT
    accepted so lines like "128-bit accumulator" cannot cause false splits).
    Non-strategy blocks (diagnosis/recommendation/intro) are dropped by
    requiring a gain or risk field and by the name filter.
    """
    cleaned = text.replace("**", "")
    strategies: list[Strategy] = []
    # Split BEFORE each numbered heading line.
    blocks = re.split(
        r"\n(?=\s*(?:#{1,4}\s+|[-•*]\s+)?(?:strategy\s+)?\d+\s*[:.)—–])",
        cleaned, flags=re.IGNORECASE)
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        name_m = re.search(r"(?:name|strategy)\s*[:：]\s*(.+)", b, re.IGNORECASE)
        # Field labels allow "Label: value" and "Label\nvalue" (bold style).
        rat_m = re.search(r"rationale\s*[:：]?\s*\n?\s*(.+)", b, re.IGNORECASE)
        gain_m = re.search(
            r"(?:expected\s+(?:latency\s+)?gain|latency\s+gain|gain)"
            r"\s*[:：]?\s*\n?\s*(.+)", b, re.IGNORECASE)
        risk_m = re.search(r"risk\s*[:：]?\s*\n?\s*(.+)", b, re.IGNORECASE)
        comb_m = re.search(
            r"combinable(?:_with|\s+with)?\s*[:：]?\s*\n?\s*(.+)",
            b, re.IGNORECASE)
        raw_name = name_m.group(1).strip() if name_m else b.split("\n")[0]
        name = re.sub(r"^[\s#*]*(?:strategy\s+)?\d*\s*[:.)]?\s*", "",
                      raw_name, flags=re.IGNORECASE).strip("#* \t")
        if not name or _NON_STRATEGY_RE.search(name):
            continue
        # A real strategy block must quantify gain or risk; this drops the
        # diagnosis/recommendation/intro sections real LLMs wrap strategies in.
        if gain_m is None and risk_m is None:
            continue
        strategies.append(Strategy(
            name=name[:80],
            rationale=(rat_m.group(1).strip() if rat_m else b[:200])[:200],
            expected_gain=gain_m.group(1).strip() if gain_m else "?",
            risk=risk_m.group(1).strip() if risk_m else "?",
            combinable_with=comb_m.group(1).strip() if comb_m else "",
        ))
    return strategies


_NON_STRATEGY_RE = re.compile(
    r"diagnos|recommend|conclusion|summary|overview|analysis", re.IGNORECASE)


_PICK_RE = re.compile(r"PICK\s*[:：]\s*([\d,\s]+)", re.IGNORECASE)
_REASON_RE = re.compile(r"REASON\s*[:：]\s*(.+)", re.IGNORECASE)


def _parse_pick(text: str, n_strategies: int) -> list[int]:
    """Parse the selector's ``PICK:`` line into 0-based strategy indexes.

    Falls back to [0] (first strategy) when the line is missing, empty, or
    every number is out of range — a selector failure must never crash the
    optimize loop.

    Args:
        text: The selector AI's raw reply.
        n_strategies: Number of proposed strategies (valid range bound).

    Returns:
        A non-empty list of valid 0-based indexes, de-duplicated, in the
        order the selector wrote them.
    """
    m = _PICK_RE.search(text)
    if m:
        picks: list[int] = []
        for tok in m.group(1).split(","):
            tok = tok.strip()
            if not tok.isdigit():
                continue
            idx = int(tok) - 1
            if 0 <= idx < n_strategies and idx not in picks:
                picks.append(idx)
        if picks:
            return picks
    return [0]


def _parse_reason(text: str) -> str:
    """Parse the selector's one-line ``REASON:`` field (empty on miss)."""
    m = _REASON_RE.search(text)
    return m.group(1).strip()[:200] if m else ""
