"""Region A - flow chart showing agent stage progress.

Displays 5 stages horizontally with status symbols and stats.
"""
from __future__ import annotations

from textual.widgets import Label
from rich.text import Text
from rich.table import Table

STAGES = ["route", "correctness", "synth", "optimize", "submit"]

# Status symbols
SYMBOLS = {
    "pending": "⚪",
    "running": "🔄",
    "done": "✅",
    "failed": "❌",
    "skipped": "⏭️",
}


class FlowChart(Label):
    """Flow chart widget showing 5 stages with status and stats.

    Call update_stage() to change a stage's display.
    """

    def __init__(self) -> None:
        super().__init__("[flow chart]", id="flow-chart")
        self._stage_status: dict[str, str] = {s: "pending" for s in STAGES}
        self._stage_stats: dict[str, str] = {s: "" for s in STAGES}
        self._stage_elapsed: dict[str, float] = {s: 0.0 for s in STAGES}

    def update_stage(self, stage: str, status: str, stat: str = "",
                     elapsed: float = 0.0) -> None:
        """Update one stage's display.

        Args:
            stage: Stage name (route/correctness/synth/optimize/submit).
            status: pending/running/done/failed/skipped.
            stat: Short stat string (e.g. "csim×3 2218tok").
            elapsed: Elapsed seconds for this stage.
        """
        if stage in self._stage_status:
            self._stage_status[stage] = status
            self._stage_stats[stage] = stat
            self._stage_elapsed[stage] = elapsed
            self._render_chart()

    def mark_current(self, stage: str) -> None:
        """Mark a stage as running, previous stages as done."""
        found = False
        for s in STAGES:
            if s == stage:
                if self._stage_status[s] == "pending":
                    self._stage_status[s] = "running"
                found = True
            elif not found and self._stage_status[s] == "running":
                self._stage_status[s] = "done"
        self._render_chart()

    def _render_chart(self) -> None:
        """Render the flow chart as a Rich table."""
        table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
        for _ in STAGES:
            table.add_column(justify="center")

        row_symbols = []
        row_stats = []
        for s in STAGES:
            sym = SYMBOLS.get(self._stage_status[s], "⚪")
            stat = self._stage_stats[s]
            elapsed = self._stage_elapsed[s]

            # Build display
            if self._stage_status[s] == "running":
                sym_text = Text(f"{sym} {s}", style="bold yellow blink")
            elif self._stage_status[s] == "done":
                sym_text = Text(f"{sym} {s}", style="green")
            elif self._stage_status[s] == "failed":
                sym_text = Text(f"{sym} {s}", style="red")
            else:
                sym_text = Text(f"{sym} {s}", style="dim")

            stat_text = stat
            if elapsed > 0:
                stat_text = f"{stat} {elapsed:.0f}s" if stat else f"{elapsed:.0f}s"

            row_symbols.append(sym_text)
            row_stats.append(Text(stat_text, style="dim"))

        table.add_row(*row_symbols)
        table.add_row(*row_stats)

        # Add arrows between stages
        from rich.console import Group
        self.update(table)
