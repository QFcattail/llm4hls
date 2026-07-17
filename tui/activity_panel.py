"""Region B - current activity panel.

Shows what the agent is doing right now:
- LLM call: streaming thinking + code output (opencode style)
- Tool call: tool name + elapsed + log tail
- Mechanical check: pass/fail
- Idle: waiting for next step
"""
from __future__ import annotations

import time

from textual.widgets import RichLog
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax


class ActivityPanel(RichLog):
    """Activity panel showing current agent action.

    Use set_activity() to switch modes, append_stream() for LLM streaming,
    append_log() for tool output.
    """

    def __init__(self) -> None:
        super().__init__(id="activity-panel", markup=True, wrap=True, auto_scroll=True)
        self._activity_type: str = "idle"
        self._title: str = "idle"
        self._start_time: float = 0
        self._thinking_parts: list[str] = []
        self._content_parts: list[str] = []
        self._log_parts: list[str] = []

    def set_activity(self, activity_type: str, title: str) -> None:
        """Switch to a new activity mode.

        Args:
            activity_type: "llm" / "tool" / "mechanical" / "idle".
            title: Human-readable title (e.g. "repair 修复中").
        """
        self._activity_type = activity_type
        self._title = title
        self._start_time = time.monotonic()
        self._thinking_parts = []
        self._content_parts = []
        self._log_parts = []
        self.clear()
        self._render()

    def append_stream(self, kind: str, text: str) -> None:
        """Append a streaming token from the LLM.

        Args:
            kind: "thinking" (reasoning_content) or "content" (final answer).
            text: The token text.
        """
        if kind == "thinking":
            self._thinking_parts.append(text)
        elif kind == "content":
            self._content_parts.append(text)
        self._render()

    def append_log(self, text: str) -> None:
        """Append tool output text."""
        self._log_parts.append(text)
        self._render()

    def set_elapsed(self, elapsed: float) -> None:
        """Update elapsed time display."""
        # Called by parent on refresh tick
        self._render()

    def _render(self) -> None:
        """Render the current activity state."""
        elapsed = time.monotonic() - self._start_time if self._start_time else 0
        self.clear()

        # Title line
        title_style = "bold cyan" if self._activity_type != "idle" else "dim"
        self.write(Text(f"▸ {self._title}... {elapsed:.1f}s", style=title_style))
        self.write("")

        if self._activity_type == "llm":
            self._render_llm()
        elif self._activity_type == "tool":
            self._render_tool()
        elif self._activity_type == "mechanical":
            self._render_mechanical()
        else:
            self.write(Text("  waiting for next step...", style="dim"))

    def _render_llm(self) -> None:
        """Render LLM streaming output with thinking + code panels."""
        # Thinking panel
        thinking_text = "".join(self._thinking_parts)
        if thinking_text:
            self.write(Text("┌─ thinking ──────────────────────────────", style="dim"))
            # Truncate to last 800 chars to avoid overflow
            display = thinking_text[-800:] if len(thinking_text) > 800 else thinking_text
            self.write(Text(display, style="dim italic"))
            self.write(Text("└──────────────────────────────────────────", style="dim"))
            self.write("")

        # Content/code panel
        content_text = "".join(self._content_parts)
        if content_text:
            self.write(Text("┌─ code ───────────────────────────────────", style="cyan"))
            # Try syntax highlighting for cpp
            display = content_text[-2000:] if len(content_text) > 2000 else content_text
            try:
                syntax = Syntax(display, "cpp", theme="monokai", line_numbers=False)
                self.write(syntax)
            except Exception:
                self.write(Text(display, style="white"))
            self.write(Text("└──────────────────────────────────────────", style="cyan"))

    def _render_tool(self) -> None:
        """Render tool call status + log tail."""
        log_text = "".join(self._log_parts)
        if log_text:
            # Show last 15 lines
            lines = log_text.strip().split("\n")
            tail = "\n".join(lines[-15:])
            self.write(Text(tail, style="white"))
        else:
            self.write(Text("  (waiting for output...)", style="dim"))

    def _render_mechanical(self) -> None:
        """Render mechanical check results."""
        log_text = "".join(self._log_parts)
        if log_text:
            self.write(Text(log_text, style="green"))
