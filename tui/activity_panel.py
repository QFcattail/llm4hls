"""Area B - current activity panel (middle, main visual region).

Shows what the agent is doing right now. Uses a SINGLE RichLog for all
output - thinking and code are interleaved in the same stream (not split
into separate panels), which avoids width issues and matches the user's
request to show them in the same place.

Modes:
  a) LLM call   - thinking (dim italic) then code (syntax highlighted),
                  all in one RichLog, streamed token by token.
  b) Tool call  - tool name + elapsed + parsed error details (count + top 5).
  c) Idle       - "waiting for next step..."
"""
from __future__ import annotations

import re
import time
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, RichLog
from rich.syntax import Syntax
from rich.text import Text

ActivityType = Literal["llm", "tool", "mechanical", "idle"]
StreamKind = Literal["thinking", "content"]

# Vitis error patterns for extracting tool error details
_ERROR_LINE_RE = re.compile(
    r'(?:ERROR|error|Error)[:\s].*|'
    r'\[(?:XFORM|RTGEN|SIM|HLS|VPP)\s*\d+-\d+\].*|'
    r'.*:\d+:\d+:\s*(?:error|ERROR).*'
)
_COMPILE_ERROR_RE = re.compile(r'(?:fatal error|error)[:\s].*', re.IGNORECASE)


class ActivityPanel(Static):
    """Current-activity panel with a single streaming output log.

    Layout:
      - title line: ``▸ {title}... elapsed {elapsed}s``
      - single RichLog body (thinking + code interleaved, or tool output)

    Public API:
      - set_activity(activity_type, title)
      - append_stream(kind, text)    # kind = "thinking" | "content"
      - append_log(text)             # tool output
      - show_tool_errors(log_text, phase)  # parsed error summary
      - clear_log()
    """

    DEFAULT_CSS = """
    ActivityPanel {
        height: 1fr;
        border: round $accent;
        padding: 0 1;
    }
    ActivityPanel > Vertical { height: 1fr; }
    #ap-title { height: 1; }
    #ap-thinking-live { height: 2; color: $text-muted; }
    #ap-log { border: none; height: 1fr; }
    """

    def __init__(self) -> None:
        super().__init__("[activity]", id="activity-panel")
        self._activity_type: ActivityType = "idle"
        self._title: str = "idle"
        self._start_time: float = 0.0
        self._code_line_buf: str = ""
        self._thinking_line_buf: str = ""

    def compose(self) -> ComposeResult:
        """Yield title + thinking-live + single log."""
        yield Static("", id="ap-title")
        with Vertical(id="ap-body"):
            yield Static("", id="ap-thinking-live")
            yield RichLog(id="ap-log", markup=False, wrap=True, auto_scroll=True)

    def on_mount(self) -> None:
        """Initialize idle state."""
        self._render_title()
        self._write_idle()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_activity(self, activity_type: ActivityType, title: str) -> None:
        """Switch to a new activity mode, resetting the body.

        Args:
            activity_type: One of "llm", "tool", "mechanical", "idle".
            title: Human-readable title (e.g. "repairing").
        """
        self._activity_type = activity_type
        self._title = title
        self._start_time = time.monotonic()
        self._code_line_buf = ""
        self._thinking_line_buf = ""
        log = self._log_widget()
        log.clear()
        if activity_type == "idle":
            self._write_idle()
        self._render_title()

    def append_stream(self, kind: StreamKind, text: str) -> None:
        """Append a streaming delta from the LLM.

        Thinking: partial line shows live in a Static (overwritten each token),
        complete lines go to the RichLog. This gives real-time per-token feedback
        without the "each token on its own line" problem.
        Content: line-buffered, syntax-highlighted, written to RichLog on \\n.

        Args:
            kind: "thinking" or "content".
            text: The delta text.
        """
        if self._activity_type != "llm":
            self.set_activity("llm", self._title or "LLM call")
        if not text:
            return
        log = self._log_widget()
        if kind == "thinking":
            self._thinking_line_buf += text
            # Show partial line live (overwrite), truncated to fit
            try:
                live = self.query_one("#ap-thinking-live", Static)
                partial = self._thinking_line_buf[-200:]  # last 200 chars
                live.update(Text(f"  💭 {partial}", style="dim italic"))
            except Exception:
                pass
            # Write complete lines to RichLog
            while "\n" in self._thinking_line_buf:
                line, self._thinking_line_buf = self._thinking_line_buf.split("\n", 1)
                if line.strip():
                    log.write(Text(line, style="dim italic"))
                # Clear the live preview since we flushed a line
                try:
                    live = self.query_one("#ap-thinking-live", Static)
                    if self._thinking_line_buf.strip():
                        live.update(Text(f"  💭 {self._thinking_line_buf[-200:]}",
                                         style="dim italic"))
                    else:
                        live.update(Text("", style="dim"))
                except Exception:
                    pass
        elif kind == "content":
            # Clear thinking live preview when code starts
            try:
                self.query_one("#ap-thinking-live", Static).update(Text("", style="dim"))
            except Exception:
                pass
            self._code_line_buf += text
            while "\n" in self._code_line_buf:
                line, self._code_line_buf = self._code_line_buf.split("\n", 1)
                self._write_code_line(log, line)
        self._render_title()

    def append_log(self, text: str) -> None:
        """Append raw tool output text to the log."""
        if self._activity_type not in ("tool", "mechanical"):
            self.set_activity("tool", self._title or "tool call")
        if not text:
            return
        log = self._log_widget()
        log.write(Text(text, style="black"))
        self._render_title()

    def show_tool_errors(self, log_text: str, phase: str) -> None:
        """Parse tool log and show a structured error summary.

        Shows: total error count + top 5 error lines.

        Args:
            log_text: The raw tool log (from ToolResult.log).
            phase: The tool phase (compile_error / runtime_fail / etc).
        """
        if self._activity_type not in ("tool", "mechanical"):
            self.set_activity("tool", self._title or "tool call")
        log = self._log_widget()

        # Extract error lines
        lines = log_text.split("\n")
        error_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _ERROR_LINE_RE.match(stripped) or _COMPILE_ERROR_RE.match(stripped):
                error_lines.append(stripped)

        if not error_lines:
            log.write(Text(f"  {phase} (no specific error lines found)"))
            return

        log.write(Text(f"  {len(error_lines)} errors total, "
                       f"showing first {min(5, len(error_lines))}:",
                       style="bold red"))
        for i, err in enumerate(error_lines[:5], 1):
            log.write(Text(f"  {i}. {err[:120]}", style="red"))
        if len(error_lines) > 5:
            log.write(Text(f"  ...and {len(error_lines) - 5} more errors",
                           style="dim"))
        self._render_title()

    def clear_log(self) -> None:
        """Clear the log."""
        self._log_widget().clear()

    def refresh_title(self) -> None:
        """Re-render just the title line (from periodic tick)."""
        self._render_title()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _elapsed(self) -> float:
        """Seconds since current activity started."""
        if not self._start_time:
            return 0.0
        return time.monotonic() - self._start_time

    def _log_widget(self) -> RichLog:
        """Return the main RichLog widget."""
        return self.query_one("#ap-log", RichLog)

    def _render_title(self) -> None:
        """Render the title line."""
        try:
            title_w = self.query_one("#ap-title", Static)
        except Exception:
            return
        style = "dim" if self._activity_type == "idle" else "bold #587559"
        title_w.update(
            Text(f"▸ {self._title}... elapsed {self._elapsed:.1f}s", style=style)
        )

    def _write_idle(self) -> None:
        """Write the idle message."""
        try:
            self._log_widget().write(
                Text("  waiting for next step...", style="dim italic")
            )
        except Exception:
            pass

    def _write_code_line(self, log: RichLog, line: str) -> None:
        """Write one code line, syntax-highlighted."""
        if not line.strip():
            log.write(Text("", style="black"))
            return
        try:
            log.write(Syntax(line, "cpp", theme="github-light",
                             line_numbers=False, word_wrap=False))
        except Exception:
            log.write(Text(line, style="black"))


__all__ = ["ActivityPanel", "ActivityType", "StreamKind"]
