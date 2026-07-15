"""Feedback builder — turn a ToolResult into LLM-friendly text + error signatures.

Implements the feedback arm of agent-architecture.md §4.2. The harness already
parses csynth.xml / cosim.rpt (report.py); this module is about *distilling*
that into (a) short error signatures for knowledge-base retrieval and (b) a
concise feedback block for the repair prompt.

AMD's key lesson: feed back specific error codes (e.g. [XFORM 203-313]), not
vague descriptions. SWE-agent's ACI lesson: tool output must be structured
enough for the LLM to act on directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Harness ToolResult has: kind, ok, phase, return_code, log, elapsed_s,
# report (SynthReport|None), cosim (CoSimResult|None).

# Vitis error codes look like [XFORM 203-313], [RTGEN 206-102], [SIM ...].
_ERROR_CODE_RE = re.compile(r"\[(?:XFORM|RTGEN|SIM|HLS|VPP)\s*\d+-\d+\]")
# Deadlock / streaming keywords surfaced in cosim logs.
_DEADLOCK_RE = re.compile(r"\b(deadlock|deadlocked|hung|stall)\b", re.IGNORECASE)
_FIFO_RE = re.compile(r"\b(FIFO|stream|TVALID|TREADY|TLAST)\b", re.IGNORECASE)

_LOG_TAIL_CHARS = 3000   # mirror ReferenceAgent._feedback truncation


@dataclass
class Feedback:
    """Structured feedback distilled from one or more ToolResults.

    Attributes:
        phases: Human-readable per-result phase summaries, e.g.
            ["csim: runtime_fail"].
        error_codes: Vitis error codes found in logs, e.g.
            ["[XFORM 203-313]"].
        signatures: Knowledge-base retrieval keys (error codes + keywords).
        log_tail: Truncated tail of the most recent log output.
    """

    phases: list[str] = field(default_factory=list)            # e.g. ["csim: runtime_fail"]
    error_codes: list[str] = field(default_factory=list)       # e.g. ["[XFORM 203-313]"]
    signatures: list[str] = field(default_factory=list)        # KB-retrieval keys (codes + keywords)
    log_tail: str = ""

    def is_empty(self) -> bool:
        """Return True if no phases or error codes were collected."""
        return not self.phases and not self.error_codes

    def as_prompt_block(self) -> str:
        """Render the feedback as a concise block for the repair prompt.

        Returns:
            A multi-line string combining tool results, error codes, and the
            log tail, or "(no feedback)" when nothing was collected.
        """
        parts = []
        if self.phases:
            parts.append("Tool results: " + "; ".join(self.phases))
        if self.error_codes:
            parts.append("Error codes: " + ", ".join(self.error_codes))
        if self.log_tail:
            parts.append("--- log (tail) ---\n" + self.log_tail)
        return "\n".join(parts) if parts else "(no feedback)"


def build_feedback(*results) -> Feedback:
    """Build Feedback from one or more harness ToolResult objects.

    Pass csim result, and (for structural tasks) the cosim result.

    Args:
        *results: Harness ToolResult objects (or None values to skip). Each
            is expected to expose ``kind``, ``phase``, ``log``, and ``ok``
            attributes.

    Returns:
        A Feedback object with distilled phases, error codes, keyword
        signatures, and a log tail.
    """
    fb = Feedback()
    for r in results:
        if r is None:
            continue
        kind = getattr(r, "kind", "?")
        phase = getattr(r, "phase", "?")
        fb.phases.append(f"{kind}: {phase}")
        log = getattr(r, "log", "") or ""
        codes = _ERROR_CODE_RE.findall(log)
        fb.error_codes.extend(codes)
        # keyword signatures help when no code is present
        if _DEADLOCK_RE.search(log):
            fb.signatures.append("deadlock")
        if _FIFO_RE.search(log):
            fb.signatures.append("streaming")
        if not fb.log_tail and log:
            fb.log_tail = log[-_LOG_TAIL_CHARS:]
    # dedup while preserving order
    fb.error_codes = list(dict.fromkeys(fb.error_codes))
    fb.signatures = list(dict.fromkeys(fb.signatures + fb.error_codes))
    return fb
