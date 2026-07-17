"""Area A - flow chart showing agent stage progress (top of the dashboard).

Displays the five fixed pipeline stages horizontally with a status symbol,
elapsed time, and a short per-stage statistic. The current (running) stage
is highlighted in bold blinking yellow.

Stages (fixed order, matching agent/main_loop.py + the design doc):

    route  ->  correctness  ->  synth  ->  optimize  ->  submit

This is a pure presenter widget: callers push data in via update_stage().
It never imports the agent package.
"""
from __future__ import annotations

from textual.widgets import Static
from rich.console import Group
from rich.table import Table
from rich.text import Text

# Fixed pipeline order (mirrors agent/main_loop.py: route -> correctness ->
# synth -> optimize, then the final submit phase emitted in Agent.run).
STAGES: list[str] = ["route", "correctness", "synth", "optimize", "submit"]

# Human-readable label per stage (kept short for the horizontal layout).
_STAGE_LABELS: dict[str, str] = {
    "route": "路由",
    "correctness": "correctness",
    "synth": "synth",
    "optimize": "optimize",
    "submit": "提交",
}

# Status symbol per stage state. Matches the design doc's table in §3.1.
STAGE_SYMBOLS: dict[str, str] = {
    "pending": "⚪",   # not started yet
    "running": "🔄",   # in progress (highlighted)
    "done": "✅",      # passed
    "failed": "❌",    # did not pass
    "skipped": "⏭️",   # skipped (budget/plan)
}

# Rich style per status for the stage name. The running stage additionally
# gets `blink` so the eye is drawn to it, per the design doc.
_STATUS_STYLE: dict[str, str] = {
    "pending": "dim",
    "running": "bold yellow blink",
    "done": "green",
    "failed": "red",
    "skipped": "dim italic",
}

# Arrow glyph drawn between two stages in the connecting row.
_ARROW = "──►"

# How many seconds of elapsed time warrants showing a decimal. Under a
# second we round to one decimal; otherwise we show an integer.
_SHORT_STAGE_S = 1.0


def _format_elapsed(elapsed: float) -> str:
    """Format an elapsed-seconds value for compact display.

    Args:
        elapsed: Seconds spent in the stage so far (0 means unknown/none).

    Returns:
        A short string like ``"2s"`` or ``"0.4s"``, or ``""`` when zero.
    """
    if not elapsed or elapsed <= 0:
        return ""
    if elapsed < _SHORT_STAGE_S:
        return f"{elapsed:.1f}s"
    return f"{elapsed:.0f}s"


class FlowChart(Static):
    """Horizontal flow chart of the five pipeline stages.

    Rendered as a Rich table: one row of stage boxes (symbol + label) joined
    by arrows, and one row of per-stage stats (elapsed + short statistic).
    The running stage is highlighted in bold blinking yellow.

    Call :meth:`update_stage` to change a stage, or :meth:`mark_current` to
    advance the "current" pointer (marking earlier running stages done).
    """

    DEFAULT_CSS = """
    FlowChart {
        height: 5;
        border: round $primary;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__("[flow chart]", id="flow-chart")
        # Per-stage mutable display state, keyed by stage name.
        self._status: dict[str, str] = {s: "pending" for s in STAGES}
        self._elapsed: dict[str, float] = {s: 0.0 for s in STAGES}
        self._stat: dict[str, str] = {s: "" for s in STAGES}

    # -- public API -----------------------------------------------------

    def update_stage(
        self,
        stage_name: str,
        status: str,
        elapsed: float = 0.0,
        stat: str = "",
    ) -> None:
        """Update one stage's display state and re-render.

        Args:
            stage_name: One of the :data:`STAGES` names
                (route/correctness/synth/optimize/submit).
            status: One of pending/running/done/failed/skipped.
            elapsed: Seconds spent in this stage so far (0 = unknown).
            stat: Short statistic line shown beneath the stage
                (e.g. ``"csim×3 2218tok"``, ``"SCORE 1.400"``).

        Raises:
            ValueError: If ``stage_name`` is not a known stage or ``status``
                is not a known status.
        """
        if stage_name not in self._status:
            raise ValueError(
                f"unknown stage {stage_name!r}; expected one of {STAGES}"
            )
        if status not in STAGE_SYMBOLS:
            raise ValueError(
                f"unknown status {status!r}; expected one of "
                f"{list(STAGE_SYMBOLS)}"
            )
        self._status[stage_name] = status
        self._elapsed[stage_name] = float(elapsed or 0.0)
        self._stat[stage_name] = stat
        self._render()

    def mark_current(self, stage: str) -> None:
        """Mark ``stage`` as running and finalize any earlier running stage.

        Convenience helper used when the caller only knows "we are now in
        stage X": every earlier stage that was still ``running`` is folded
        to ``done`` (it must have finished for us to advance), and ``stage``
        is set to ``running`` unless it already has a terminal state
        (done/failed/skipped).

        Args:
            stage: Stage name that is now current.

        Raises:
            ValueError: If ``stage`` is not a known stage.
        """
        if stage not in self._status:
            raise ValueError(
                f"unknown stage {stage!r}; expected one of {STAGES}"
            )
        found = False
        for s in STAGES:
            if s == stage:
                found = True
                # Only flip pending -> running; leave terminal states alone.
                if self._status[s] == "pending":
                    self._status[s] = "running"
            elif not found:
                # An earlier stage still "running" must have completed.
                if self._status[s] == "running":
                    self._status[s] = "done"
        self._render()

    def reset(self) -> None:
        """Clear all stages back to pending with no stats."""
        for s in STAGES:
            self._status[s] = "pending"
            self._elapsed[s] = 0.0
            self._stat[s] = ""
        self._render()

    # -- rendering ------------------------------------------------------

    def _render(self) -> None:
        """Build the Rich table and push it to the Static widget."""
        # The table has one column per stage, all centered, no box edges so
        # we can draw the connecting arrows ourselves in a second row.
        table = Table(
            show_header=False,
            show_edge=False,
            show_lines=False,
            box=None,
            padding=(0, 1),
        )
        for _ in STAGES:
            table.add_column(justify="center", no_wrap=True)

        # Row 1: symbol + stage label, styled by status.
        symbol_row: list[Text] = []
        for s in STAGES:
            status = self._status[s]
            symbol = STAGE_SYMBOLS.get(status, "⚪")
            style = _STATUS_STYLE.get(status, "dim")
            label = _STAGE_LABELS.get(s, s)
            symbol_row.append(Text(f"{symbol} {label}", style=style))

        # Row 2: elapsed + stat (dim), joined visually under each stage.
        stat_row: list[Text] = []
        for s in STAGES:
            elapsed_str = _format_elapsed(self._elapsed[s])
            stat = self._stat[s]
            parts: list[str] = []
            if elapsed_str:
                parts.append(elapsed_str)
            if stat:
                parts.append(stat)
            stat_row.append(Text(" ".join(parts) if parts else "·", style="dim"))

        # Connecting arrow row: arrow sits between stage columns. We render
        # it as a thin row of arrows aligned under the gaps.
        arrow_row: list[Text] = []
        for i, _ in enumerate(STAGES):
            if i == 0:
                arrow_row.append(Text("", style="dim"))
            else:
                arrow_row.append(Text(_ARROW, style="dim"))

        table.add_row(*symbol_row)
        table.add_row(*arrow_row)
        table.add_row(*stat_row)

        self.update(Group(table, Text("↑ 当前阶段", style="bold yellow")
                          if "running" in self._status.values() else Text("")))
