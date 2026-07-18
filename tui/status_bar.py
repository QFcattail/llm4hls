"""Area C - resource panel (bottom, fixed 3 rows).

Three stacked lines, per docs-development/design/tui-design.md §3.3:

  Line 1: credit progress bar (spent/total + remaining) | token totals
          (prompt + completion), with reasoning tokens in parentheses.
  Line 2: current-stage call counts (tool calls + reviews) | total LLM calls.
  Line 3: last tool error summary | last review verdict.

This is a pure presenter widget: all values are pushed in via :meth:`update`.
It never imports the agent package. Field names mirror the design doc and
the agent's observability fields (credits from Budget, tokens from
DeepSeekClient, last_error from tool_result, last_review from review events).
"""
from __future__ import annotations

from textual.widgets import Static
from rich.console import RenderableType
from rich.text import Text

# Width (in characters) of the credit progress bar.
_BAR_WIDTH = 20

# Sentinel shown when there is no error / no review yet. Matches the design
# doc's "(none)" placeholder so the layout stays stable.
_NONE = "(none)"

# Reviews that count as "passing" and are therefore shown in green rather
# than red. Case-insensitive match against the stored verdict.
_PASS_REVIEWS = {"pass", "ok", "accept", "accepted", "(none)"}

# Length cap for the last-error / last-review summaries so line 3 never wraps.
_SUMMARY_CAP = 40


def _truncate(text: str, cap: int = _SUMMARY_CAP) -> str:
    """Truncate ``text`` to ``cap`` characters with an ellipsis if needed."""
    if len(text) <= cap:
        return text
    return text[: cap - 1] + "…"


def _credit_bar(spent: int, total: int) -> tuple[Text, int]:
    """Build the visual credit bar and return (bar_text, remaining).

    The bar uses filled ``█`` for the spent portion and ``░`` for the
    remaining portion, sized to :data:`_BAR_WIDTH`. When ``total`` is zero
    or less the bar is rendered empty to avoid a division-by-zero.

    Args:
        spent: Credits consumed so far.
        total: Total credit budget.

    Returns:
        A tuple of (the styled bar Text, the remaining credit count).
    """
    total = max(0, total)
    spent = max(0, spent)
    remaining = max(0, total - spent)
    if total <= 0:
        filled = 0
    else:
        filled = round(_BAR_WIDTH * spent / total)
    filled = min(max(filled, 0), _BAR_WIDTH)
    bar = Text("█" * filled, style="#FDD100") + Text("░" * (_BAR_WIDTH - filled),
                                                       style="dim")
    return bar, remaining


class StatusBar(Static):
    """Bottom resource panel: credits, tokens, call counts, last feedback.

    Fixed at 3 rows of content (plus the widget border). Call :meth:`update`
    to push in the latest values; only the fields you pass are changed, the
    rest retain their previous value.
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 4;
        border: round $accent;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__("[status]", id="status-bar")
        # All numeric counters default to 0; feedback fields default to the
        # "(none)" sentinel so line 3 reads cleanly before any activity.
        self._credits_spent: int = 0
        self._credits_total: int = 0
        self._tokens_prompt: int = 0
        self._tokens_completion: int = 0
        self._tokens_reasoning: int = 0
        self._stage_calls: int = 0
        self._stage_reviews: int = 0
        self._total_llm_calls: int = 0
        self._last_error: str = _NONE
        self._last_review: str = _NONE

    # -- public API -----------------------------------------------------

    def update(
        self,
        credits_spent: int | None = None,
        credits_total: int | None = None,
        tokens_prompt: int | None = None,
        tokens_completion: int | None = None,
        tokens_reasoning: int | None = None,
        stage_calls: int | None = None,
        stage_reviews: int | None = None,
        total_llm_calls: int | None = None,
        last_error: str | None = None,
        last_review: str | None = None,
    ) -> None:
        """Refresh the resource panel.

        Only the fields passed (non-None) are updated; the rest keep their
        previous value. This lets the caller refresh incrementally (e.g.
        push only ``last_error`` when a tool fails) without resending every
        counter each tick.

        Args:
            credits_spent: Credits consumed so far.
            credits_total: Total credit budget.
            tokens_prompt: Accumulated prompt tokens across LLM calls.
            tokens_completion: Accumulated completion tokens across LLM calls.
            tokens_reasoning: Accumulated reasoning tokens (subset of
                completion) across LLM calls.
            stage_calls: Tool calls made in the current stage so far.
            stage_reviews: Reviews made in the current stage so far.
            total_llm_calls: Total LLM completion calls made.
            last_error: Short summary of the last tool error, or ``_NONE``
                sentinel when there is none.
            last_review: Short summary of the last review verdict, or the
                ``_NONE`` sentinel.
        """
        if credits_spent is not None:
            self._credits_spent = int(credits_spent)
        if credits_total is not None:
            self._credits_total = int(credits_total)
        if tokens_prompt is not None:
            self._tokens_prompt = int(tokens_prompt)
        if tokens_completion is not None:
            self._tokens_completion = int(tokens_completion)
        if tokens_reasoning is not None:
            self._tokens_reasoning = int(tokens_reasoning)
        if stage_calls is not None:
            self._stage_calls = int(stage_calls)
        if stage_reviews is not None:
            self._stage_reviews = int(stage_reviews)
        if total_llm_calls is not None:
            self._total_llm_calls = int(total_llm_calls)
        if last_error is not None:
            self._last_error = last_error if last_error else _NONE
        if last_review is not None:
            self._last_review = last_review if last_review else _NONE
        self.refresh()

    def update_state(self, **kwargs) -> None:
        """Back-compat alias for :meth:`update`.

        Older callers (e.g. tui/app.py) used keyword-only ``update_state``
        with the same field names; this forwards to :meth:`update`.
        """
        # Map the older stage_tool_calls -> stage_calls name if present.
        if "stage_tool_calls" in kwargs:
            kwargs.setdefault("stage_calls", kwargs.pop("stage_tool_calls"))
        self.update(**kwargs)

    # -- rendering ------------------------------------------------------

    def render(self) -> RenderableType:
        """Render the 3-line resource panel.

        Overriding :meth:`render` (rather than calling ``Static.update``)
        lets Textual handle visualization in its own app-console context,
        which avoids the None-visual race that ``Static.update`` hits when
        called before the first layout pass. ``update`` simply mutates the
        stored fields and calls :meth:`refresh`.
        """
        return self._build_render()

    def _build_render(self) -> Text:
        """Compose the 2-line resource panel as a single Rich Text."""
        line1 = self._render_line1()
        line2 = self._render_line2()
        return Text.assemble(line1, Text("\n"), line2)

    def _render_line1(self) -> Text:
        """Line 1: credit bar + remaining | token totals (reasoning)."""
        bar, remaining = _credit_bar(self._credits_spent, self._credits_total)
        total_tokens = self._tokens_prompt + self._tokens_completion
        return Text.assemble(
            Text(f" credits: {self._credits_spent}/{self._credits_total} "
                 f"left {remaining} ", style="#587559"),
            bar,
            Text("  │  ", style="dim"),
            Text(f"tokens: {total_tokens}", style="green"),
            Text(f" (reasoning {self._tokens_reasoning})", style="dim"),
        )

    def _render_line2(self) -> Text:
        """Line 2: stage calls + reviews | total LLM calls | last review."""
        review_lower = (self._last_review or "").strip().lower()
        is_pass = review_lower in _PASS_REVIEWS or review_lower.startswith("pass")
        rev_style = "green" if is_pass else "red"
        return Text.assemble(
            Text(f" stage: tools {self._stage_calls}, "
                 f"reviews {self._stage_reviews}", style="black"),
            Text("  │  ", style="dim"),
            Text(f"total LLM: {self._total_llm_calls} calls", style="black"),
            Text("  │  ", style="dim"),
            Text(f"last review: {_truncate(self._last_review)}", style=rev_style),
        )


__all__ = ["StatusBar"]
