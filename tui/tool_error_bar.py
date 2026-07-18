"""Region B - tool error bar (between flow chart and activity panel).

Shows the last tool call result with parsed error details:
- compile_error: gcc-style error lines (file:line:col: error: ...)
- runtime_fail: test case failure lines
- pass: green success line

This is a SEPARATE region from the status bar (which only has 2 lines now)
because gcc error lines are long and need their own space.
"""
from __future__ import annotations

import re
from textual.widgets import Static
from rich.text import Text

# gcc/clang error: file:line:col: error: message
_GCC_ERROR_RE = re.compile(r'^[^:\s]+:\d+:\d+:\s*(?:error|fatal error|warning):', re.IGNORECASE)
# Vitis error codes: [XFORM 203-313] message (but NOT [HLS 200-xxx] which are INFO)
_VITIS_ERROR_RE = re.compile(r'\[(?:XFORM|RTGEN|SIM|VPP)\s*\d+-\d+\]')
# Test case failure
_TESTCASE_RE = re.compile(r'(?:Test Case|test case).*(?:fail|Fail|FAIL)', re.IGNORECASE)
# Generic error/fail lines (but not INFO/WARNING lines)
_GENERIC_ERROR_RE = re.compile(r'(?:ERROR|error|Error)[:\s]', re.IGNORECASE)
# Lines to exclude (info/warning noise)
_NOISE_RE = re.compile(r'^(?:INFO|WARNING|Resolution|  )', re.IGNORECASE)

_MAX_ERRORS_SHOWN = 5


class ToolErrorBar(Static):
    """Fixed-height bar showing the last tool call's result and error details.

    Call show_result() with the tool kind, phase, and raw log to update.
    """

    DEFAULT_CSS = """
    ToolErrorBar {
        height: 7;
        border: round $accent;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__("[tool errors]", id="tool-error-bar")

    def show_result(self, kind: str, phase: str, ok: bool,
                    elapsed: float = 0, log: str = "") -> None:
        """Update the bar with a tool call result.

        Args:
            kind: Tool kind (csim/synth/cosim).
            phase: Result phase (pass/compile_error/runtime_fail/...).
            ok: Whether the tool passed.
            elapsed: Elapsed seconds.
            log: Raw tool log (for error extraction).
        """
        if ok:
            self.update(Text(
                f"  ✅ [{kind}] pass ({elapsed:.1f}s)", style="green"
            ))
            return

        # Parse error lines from log
        error_lines = self._extract_errors(log)

        parts: list[Text] = []
        header = f"  📋 [{kind}] {phase}"
        if error_lines:
            header += f"  ({len(error_lines)} errors)"
        parts.append(Text(header, style="bold red"))

        if error_lines:
            shown = error_lines[:_MAX_ERRORS_SHOWN]
            for i, err in enumerate(shown, 1):
                parts.append(Text(f"    {i}. {err[:120]}", style="red"))
            if len(error_lines) > _MAX_ERRORS_SHOWN:
                parts.append(Text(
                    f"    ...and {len(error_lines) - _MAX_ERRORS_SHOWN} more errors",
                    style="dim"
                ))
        elif log.strip():
            # No structured errors found, show raw log tail
            tail = log.strip().split("\n")[-3:]
            for line in tail:
                parts.append(Text(f"    {line[:120]}"))
        else:
            parts.append(Text("    (no error details - likely an environment "
                              "problem, vitis-run not found)"))

        self.update(Text("\n").join(parts))

    def _extract_errors(self, log: str) -> list[str]:
        """Extract error lines from a tool log.

        Handles:
        - gcc/clang: file:line:col: error: msg
        - Vitis codes: [XFORM 203-313] msg
        - Test case: Test Case N Failed!
        - Generic: lines containing ERROR/error

        Args:
            log: Raw tool log text.

        Returns:
            List of error line strings (deduplicated, order preserved).
        """
        if not log:
            return []
        results: list[str] = []
        seen: set[str] = set()
        for line in log.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # Skip INFO/WARNING noise lines
            if _NOISE_RE.match(stripped):
                continue
            is_error = (
                _GCC_ERROR_RE.match(stripped)
                or _VITIS_ERROR_RE.search(stripped)
                or _TESTCASE_RE.search(stripped)
                or _GENERIC_ERROR_RE.match(stripped)
            )
            if is_error and stripped not in seen:
                results.append(stripped)
                seen.add(stripped)
        return results

    def clear_bar(self) -> None:
        """Reset to empty state."""
        self.update(Text("  (waiting for tool call...)", style="dim"))

    def show_running(self, kind: str, elapsed: float = 0) -> None:
        """Show a running tool call status (before result arrives).

        Args:
            kind: Tool kind (csim/synth/cosim).
            elapsed: Seconds elapsed so far.
        """
        labels = {"csim": "C simulation", "synth": "synthesis",
                  "cosim": "co-simulation", "cosim_recheck": "co-simulation (recheck)"}
        label = labels.get(kind, kind)
        self.update(Text(
            f"  🔄 [{kind}] running {label}... elapsed {elapsed:.1f}s",
            style="bold #FDD100"
        ))
