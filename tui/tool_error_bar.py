"""Region B - tool error bar + optimize-stage strategy panel.

Shows the last tool call result with parsed error details:
- compile_error: gcc-style error lines (file:line:col: error: ...)
- runtime_fail: test case failure lines
- pass: green success line

Since v4 (tui-design §3.2): during the optimize stage the bar is shared with
a strategy panel (<=2 lines: proposed strategies + selector pick), because
optimize-stage tool calls mostly pass and the error space would sit idle.
The strategy panel never hides real tool errors — they render below it.

Rendering is state-driven (like StatusBar): every public method only mutates
``_strategy_lines`` / the tool-zone state and calls :meth:`_rebuild`, so the
150 ms heartbeat ``show_running`` refresh cannot wipe the strategy lines.
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

# Error rows available when the whole bar belongs to the tool zone.
_MAX_ERRORS_SHOWN = 5
# Total content rows inside the widget (height 7 minus border).
_CONTENT_ROWS = 5
# Per-line character cap so long strategy names / errors never wrap.
_LINE_CAP = 130


class ToolErrorBar(Static):
    """Fixed-height bar: tool result/errors, plus the optimize strategy panel.

    Public methods keep their original signatures (``show_result`` /
    ``show_running`` / ``clear_bar``); v4 adds ``show_strategies`` /
    ``update_picked`` / ``clear_strategies`` for the optimize-stage panel.
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
        # Strategy zone (<=2 lines; empty outside the optimize stage).
        self._strategy_all: list[str] = []
        self._strategy_picked: list[str] = []
        self._strategy_reason: str = ""
        self._strategy_ready: bool = False
        # Tool zone: one header line plus extracted error lines.
        self._tool_header: Text = Text("  (waiting for tool call...)", style="dim")
        self._tool_errors: list[str] = []

    # -- strategy zone (v4) ----------------------------------------------
    def show_strategies(self, all_names: list[str], picked: list[str],
                        reason: str = "") -> None:
        """Show the optimize-stage strategy panel.

        Args:
            all_names: Every proposed strategy name (the 🎯 catalog line).
            picked: The selector AI's chosen subset (the ▶ line).
            reason: The selector's one-line rationale (appended to ▶).
        """
        self._strategy_all = list(all_names)
        self._strategy_picked = list(picked)
        self._strategy_reason = reason
        self._strategy_ready = not all_names
        self._rebuild()

    def update_picked(self, picked: list[str], reason: str = "") -> None:
        """Rewrite only the ▶ line (e.g. an optimize_fallback event).

        Args:
            picked: The fallback subset names.
            reason: Why the pick changed (e.g. "combo failed").
        """
        self._strategy_picked = list(picked)
        self._strategy_reason = reason
        self._strategy_ready = False
        self._rebuild()

    def clear_strategies(self) -> None:
        """Remove the strategy panel (optimize stage exited)."""
        self._strategy_all = []
        self._strategy_picked = []
        self._strategy_reason = ""
        self._strategy_ready = False
        self._rebuild()

    def _strategy_lines(self) -> list[Text]:
        """Render the strategy zone as at most two Text lines."""
        if self._strategy_all:
            catalog = "  ".join(
                f"{i + 1}.{n}" for i, n in enumerate(self._strategy_all))
            lines = [Text(
                f"  🎯 {len(self._strategy_all)} strategies: {catalog}"[:_LINE_CAP],
                style="#587559")]
        elif self._strategy_ready or self._strategy_picked:
            lines = [Text("  🎯 optimizing: proposing strategies...",
                          style="dim")]
        else:
            return []
        if self._strategy_picked:
            head = f"  ▶ selector picked {'+'.join(self._strategy_picked)}"
            if self._strategy_reason:
                head += f": {self._strategy_reason}"
            lines.append(Text(head[:_LINE_CAP], style="bold #587559"))
        return lines

    # -- tool zone --------------------------------------------------------
    def show_result(self, kind: str, phase: str, ok: bool,
                    elapsed: float = 0, log: str = "") -> None:
        """Update the tool zone with a tool call result.

        Args:
            kind: Tool kind (csim/synth/cosim).
            phase: Result phase (pass/compile_error/runtime_fail/...).
            ok: Whether the tool passed.
            elapsed: Elapsed seconds.
            log: Raw tool log (for error extraction).
        """
        if ok:
            self._set_tool(Text(f"  ✅ [{kind}] pass ({elapsed:.1f}s)",
                                style="green"))
            return

        error_lines = self._extract_errors(log)
        header = f"  📋 [{kind}] {phase}"
        if error_lines:
            header += f"  ({len(error_lines)} errors)"
        if error_lines:
            self._set_tool(Text(header, style="bold red"), error_lines)
        elif log.strip():
            # No structured errors found, show raw log tail
            self._set_tool(Text(header, style="bold red"),
                           [l for l in log.strip().split("\n")[-3:]])
        else:
            self._set_tool(Text(header, style="bold red"),
                           ["(no error details - likely an environment "
                            "problem, vitis-run not found)"])

    def clear_bar(self) -> None:
        """Reset the tool zone to its waiting state (strategy zone kept)."""
        self._set_tool(Text("  (waiting for tool call...)", style="dim"))

    def show_running(self, kind: str, elapsed: float = 0) -> None:
        """Show a running tool call status (before result arrives).

        Args:
            kind: Tool kind (csim/synth/cosim).
            elapsed: Seconds elapsed so far.
        """
        labels = {"csim": "C simulation", "synth": "synthesis",
                  "cosim": "co-simulation",
                  "cosim_recheck": "co-simulation (recheck)"}
        label = labels.get(kind, kind)
        self._set_tool(Text(
            f"  🔄 [{kind}] running {label}... elapsed {elapsed:.1f}s",
            style="bold #FDD100"))

    def _set_tool(self, header: Text, errors: list[str] | None = None) -> None:
        """Store the tool-zone state and re-render the bar."""
        self._tool_header = header
        self._tool_errors = errors or []
        self._rebuild()

    # -- rendering --------------------------------------------------------
    def _build_render(self) -> Text:
        """Compose strategy zone (<=2 rows) + tool zone (rest) as one Text.

        The error list shrinks to fit the remaining rows (5 without a
        strategy panel, 3 with one); truncated errors get an "...and N more
        errors" tail row, so the total never exceeds the widget's content
        height. Kept separate from :meth:`_rebuild` so headless tests can
        assert on the layout without an app context.
        """
        parts: list[Text] = list(self._strategy_lines())
        rows_left = _CONTENT_ROWS - len(parts)
        parts.append(self._tool_header)
        rows_left -= 1
        budget = max(0, min(rows_left, _MAX_ERRORS_SHOWN))
        errors = self._tool_errors
        if len(errors) > budget and budget > 0:
            shown = errors[:budget - 1] if budget > 1 else []
            more = len(errors) - len(shown)
        else:
            shown = errors[:budget]
            more = 0
        parts.extend(Text(f"    {i}. {e[:120]}", style="red")
                     for i, e in enumerate(shown, 1))
        if more:
            parts.append(Text(f"    ...and {more} more errors", style="dim"))
        return Text("\n").join(parts)

    def _rebuild(self) -> None:
        """Push the composed content into the widget."""
        self.update(self._build_render())

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
