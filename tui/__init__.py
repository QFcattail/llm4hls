"""Textual + Rich TUI widgets for the LLM4HLS agent dashboard.

Three independent widgets, one per screen region described in
docs-development/design/tui-design.md:

    - FlowChart      : Area A, top - 5-stage progress (route -> correctness
                       -> synth -> optimize -> submit).
    - ActivityPanel  : Area B, middle - current activity with streaming
                       LLM output (thinking + code) or tool log tail.
    - StatusBar      : Area C, bottom 3 rows - credit/token/calls/feedback.

These widgets are pure presenters: data is pushed in through method calls,
they never import the agent package directly. See the design doc for the
layout and the per-region field semantics.
"""

from .flow_chart import FlowChart, STAGES, STAGE_SYMBOLS
from .activity_panel import ActivityPanel
from .status_bar import StatusBar

__all__ = [
    "FlowChart",
    "ActivityPanel",
    "StatusBar",
    "STAGES",
    "STAGE_SYMBOLS",
]
