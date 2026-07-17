"""Area B - current activity panel (middle, main visual region).

Shows what the agent is doing right now, in one of three modes:

  a) LLM call   - two regions: thinking (dim italic) + content/code (cpp
                  syntax highlighted). Streams tokens via append_stream().
  b) Tool call  - tool name + elapsed + tail of the tool log, appended
                  via append_log().
  c) Idle       - "等待下一步..." with the last activity hint.

The title line reads ``▸ {title}... 已耗时 {elapsed}s`` and is refreshed
on each render (the caller's tick, or on any append). Streaming output is
appended incrementally rather than re-rendered wholesale, so large LLM
outputs stay cheap.

This widget is a pure presenter: data arrives via method calls and it never
imports the agent package. The stream ``kind`` values ("thinking"/"content")
match DeepSeekClient.on_stream's delta_kind contract (see
agent/deepseek_client.py).
"""
from __future__ import annotations

import time
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, RichLog
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# Activity modes. "mechanical" is folded into the tool-ish path but kept
# distinct so callers can label mechanical-review output differently.
ActivityType = Literal["llm", "tool", "mechanical", "idle"]

# Stream kind, matching DeepSeekClient.on_stream's delta_kind.
StreamKind = Literal["thinking", "content"]

# How much of each buffer we keep for a full re-render. Streaming appends
# go to the live RichLog directly (unbounded by default), but if the whole
# panel is re-rendered we cap to these to avoid pathological memory use.
_THINKING_KEEP_CHARS = 4000
_CONTENT_KEEP_CHARS = 8000
_TOOL_KEEP_LINES = 40

# Default lexer/theme for the code region. cpp because the agent writes HLS C++.
_CODE_LEXER = "cpp"
_CODE_THEME = "monokai"


class ActivityPanel(Static):
    """Current-activity panel with streaming LLM output and tool log tail.

    Layout (top to bottom):
      - title line: ``▸ {title}... 已耗时 {elapsed}s``
      - mode-specific body:
          * llm        -> thinking RichLog + code RichLog
          * tool/mech  -> single RichLog with the tool log tail
          * idle       -> a single dim line

    Public API:
      - set_activity(activity_type, title)
      - append_stream(kind, text)    # kind = "thinking" | "content"
      - append_log(text)             # tool output
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
    #ap-body { height: 1fr; }
    .ap-think-log { border: none; height: 1fr; }
    .ap-code-log { border: none; height: 1fr; }
    .ap-tool-log { border: none; height: 1fr; }
    """

    def __init__(self) -> None:
        super().__init__("[activity]", id="activity-panel")
        self._activity_type: ActivityType = "idle"
        self._title: str = "空闲"
        self._start_time: float = 0.0
        # Full-text buffers kept so a re-render (mode switch / tick) can
        # rebuild the body without losing what was streamed.
        self._thinking_parts: list[str] = []
        self._content_parts: list[str] = []
        self._log_lines: list[str] = []
        # Current in-progress code line for line-buffered syntax highlighting.
        self._code_line_buf: str = ""

    # ------------------------------------------------------------------
    # Textual lifecycle + compositio
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Yield the title line and the swap-in body container."""
        yield Static("", id="ap-title")
        with Vertical(id="ap-body"):
            yield RichLog(id="ap-thinking", classes="ap-think-log",
                          markup=False, wrap=True, auto_scroll=True)
            yield RichLog(id="ap-code", classes="ap-code-log",
                          markup=False, wrap=False, auto_scroll=True)
            yield RichLog(id="ap-tool", classes="ap-tool-log",
                          markup=False, wrap=True, auto_scroll=True)
            yield Static("", id="ap-idle")

    def on_mount(self) -> None:
        """Hide all body widgets until the first set_activity() call."""
        self._show_only("ap-idle")
        self._render_title()
        self._render_idle()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_activity(self, activity_type: ActivityType, title: str) -> None:
        """Switch to a new activity mode, resetting the body.

        Args:
            activity_type: One of "llm", "tool", "mechanical", "idle".
            title: Human-readable title shown after the ▸ marker
                (e.g. ``"repair 修复中"``, ``"synth 综合中"``).
        """
        self._activity_type = activity_type
        self._title = title
        self._start_time = time.monotonic()
        # Reset buffers and clear the live logs so the new mode starts clean.
        self._thinking_parts = []
        self._content_parts = []
        self._log_lines = []
        self._code_line_buf = ""
        self._clear_logs()
        # Pick which body widget(s) to show for this mode.
        if activity_type == "llm":
            self._show_only_with(["ap-thinking", "ap-code"], hide_idle=True)
        elif activity_type in ("tool", "mechanical"):
            self._show_only("ap-tool")
        else:
            self._show_only("ap-idle")
            self._render_idle()
        self._render_title()

    def append_stream(self, kind: StreamKind, text: str) -> None:
        """Append a streaming delta from the LLM.

        Used as the DeepSeek ``on_stream`` callback target. ``kind`` matches
        the client's ``delta_kind``: ``"thinking"`` for reasoning_content
        and ``"content"`` for the final answer/code.

        If the panel is not currently in LLM mode, it is switched to LLM
        mode with the existing title first (so streamed tokens are never
        dropped on the floor).

        Args:
            kind: "thinking" or "content".
            text: The delta text (may be a partial line / single token).
        """
        if self._activity_type != "llm":
            # Auto-enter LLM mode if a stream arrives out of band.
            self.set_activity("llm", self._title or "LLM 调用")
        if not text:
            return
        if kind == "thinking":
            self._thinking_parts.append(text)
            self._append_thinking(text)
        elif kind == "content":
            self._content_parts.append(text)
            self._append_content(text)
        self._render_title()

    def append_log(self, text: str) -> None:
        """Append a chunk of tool/mechanical output to the log tail.

        If the panel is in LLM or idle mode, it is switched to "tool" mode
        first so the log is visible.

        Args:
            text: Tool output text (may contain multiple lines).
        """
        if self._activity_type not in ("tool", "mechanical"):
            self.set_activity("tool", self._title or "工具调用")
        if not text:
            return
        # Track full lines for a possible re-render; flush the partial tail.
        for line in text.splitlines() or [text]:
            self._log_lines.append(line)
        # Cap the kept buffer.
        if len(self._log_lines) > _TOOL_KEEP_LINES:
            self._log_lines = self._log_lines[-_TOOL_KEEP_LINES:]
        tool_log = self._body_widget("ap-tool")
        tool_log.write(Text(text, style="white"))
        self._render_title()

    def clear_log(self) -> None:
        """Clear the tool log buffer and visible log."""
        self._log_lines = []
        self._body_widget("ap-tool").clear()

    def refresh_title(self) -> None:
        """Re-render just the title line (call from a periodic tick).

        This is what keeps the ``已耗时`` counter ticking forward without
        re-streaming or re-appending any body content.
        """
        self._render_title()

    # ------------------------------------------------------------------
    # Internals: rendering helpers
    # ------------------------------------------------------------------

    @property
    def _elapsed(self) -> float:
        """Seconds since the current activity started (0 if not started)."""
        if not self._start_time:
            return 0.0
        return time.monotonic() - self._start_time

    def _render_title(self) -> None:
        """Render the ``▸ {title}... 已耗时 {elapsed}s`` line."""
        try:
            title_w = self.query_one("#ap-title", Static)
        except Exception:
            return  # not mounted yet (e.g. constructed in a unit test)
        if self._activity_type == "idle":
            style = "dim"
        else:
            style = "bold cyan"
        title_w.update(
            Text(f"▸ {self._title}... 已耗时 {self._elapsed:.1f}s", style=style)
        )

    def _render_idle(self) -> None:
        """Render the idle body line."""
        try:
            idle_w = self.query_one("#ap-idle", Static)
        except Exception:
            return
        idle_w.update(Text("  等待下一步...", style="dim italic"))

    def _append_thinking(self, text: str) -> None:
        """Append a thinking delta to the thinking RichLog (dim italic)."""
        log = self._body_widget("ap-thinking")
        # Show a header the first time we get thinking content.
        if not self._thinking_parts or len(self._thinking_parts) == 1:
            log.write(Text("┌─ thinking ──────────────────────────────",
                           style="dim"))
        log.write(Text(text, style="dim italic"))

    def _append_content(self, text: str) -> None:
        """Append a content/code delta to the code RichLog.

        Code is line-buffered: we accumulate the current line and emit a
        Syntax-highlighted renderable on each newline, so partial lines
        are re-highlighted as they grow without re-emitting finished lines.
        """
        log = self._body_widget("ap-code")
        if not self._content_parts or len(self._content_parts) == 1:
            log.write(Text("┌─ code ───────────────────────────────────",
                           style="cyan"))
        self._code_line_buf += text
        # Flush complete lines as syntax-highlighted renderables.
        while "\n" in self._code_line_buf:
            line, self._code_line_buf = self._code_line_buf.split("\n", 1)
            self._write_code_line(log, line)
        # Re-render the in-progress partial line (replace last entry). We
        # just write it fresh; RichLog appends, which is acceptable and
        # avoids complex cursor tracking. For very long single-line outputs
        # this is still bounded by the streaming chunk size.
        if self._code_line_buf:
            self._write_code_line(log, self._code_line_buf)

    def _write_code_line(self, log: RichLog, line: str) -> None:
        """Write one code line to ``log``, syntax-highlighted when possible."""
        if not line.strip():
            log.write(Text("", style="white"))
            return
        try:
            log.write(Syntax(line, _CODE_LEXER, theme=_CODE_THEME,
                             line_numbers=False, word_wrap=False))
        except Exception:
            # If the lexer chokes (e.g. binary noise), fall back to plain.
            log.write(Text(line, style="white"))

    # ------------------------------------------------------------------
    # Internals: body widget plumbing
    # ------------------------------------------------------------------

    def _body_widget(self, widget_id: str) -> RichLog:
        """Return a mounted body RichLog by id (must be mounted)."""
        return self.query_one(f"#{widget_id}", RichLog)

    def _clear_logs(self) -> None:
        """Clear all three body RichLogs (safe if not mounted)."""
        for wid in ("ap-thinking", "ap-code", "ap-tool"):
            try:
                self.query_one(f"#{wid}", RichLog).clear()
            except Exception:
                pass

    def _show_only(self, widget_id: str) -> None:
        """Show only ``widget_id`` among the body widgets, hide the rest."""
        all_ids = ["ap-thinking", "ap-code", "ap-tool", "ap-idle"]
        for wid in all_ids:
            try:
                self.query_one(f"#{wid}").display = (wid == widget_id)
            except Exception:
                pass

    def _show_only_with(self, ids: list[str], hide_idle: bool = True) -> None:
        """Show the listed widget ids, hide the others (and idle)."""
        all_ids = ["ap-thinking", "ap-code", "ap-tool", "ap-idle"]
        for wid in all_ids:
            want = wid in ids and not (wid == "ap-idle" and hide_idle)
            try:
                self.query_one(f"#{wid}").display = want
            except Exception:
                pass


# Re-export for callers that import the type names.
__all__ = ["ActivityPanel", "ActivityType", "StreamKind"]
