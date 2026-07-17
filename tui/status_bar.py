"""Region C - resource panel showing credits, tokens, and last feedback.

Fixed 3 lines at the bottom of the dashboard.
"""
from __future__ import annotations

from textual.widgets import Label
from rich.text import Text


class StatusBar(Label):
    """Bottom resource panel: credits, tokens, call counts, last feedback.

    Call update_state() to refresh all values.
    """

    def __init__(self) -> None:
        super().__init__("[status]", id="status-bar")
        self._credits_spent: int = 0
        self._credits_total: int = 0
        self._tokens_prompt: int = 0
        self._tokens_completion: int = 0
        self._tokens_reasoning: int = 0
        self._stage_tool_calls: int = 0
        self._stage_reviews: int = 0
        self._total_llm_calls: int = 0
        self._last_error: str = "(无)"
        self._last_review: str = "(无)"

    def update_state(
        self,
        credits_spent: int | None = None,
        credits_total: int | None = None,
        tokens_prompt: int | None = None,
        tokens_completion: int | None = None,
        tokens_reasoning: int | None = None,
        stage_tool_calls: int | None = None,
        stage_reviews: int | None = None,
        total_llm_calls: int | None = None,
        last_error: str | None = None,
        last_review: str | None = None,
    ) -> None:
        """Update any subset of the status fields. Only provided values change."""
        if credits_spent is not None:
            self._credits_spent = credits_spent
        if credits_total is not None:
            self._credits_total = credits_total
        if tokens_prompt is not None:
            self._tokens_prompt = tokens_prompt
        if tokens_completion is not None:
            self._tokens_completion = tokens_completion
        if tokens_reasoning is not None:
            self._tokens_reasoning = tokens_reasoning
        if stage_tool_calls is not None:
            self._stage_tool_calls = stage_tool_calls
        if stage_reviews is not None:
            self._stage_reviews = stage_reviews
        if total_llm_calls is not None:
            self._total_llm_calls = total_llm_calls
        if last_error is not None:
            self._last_error = last_error
        if last_review is not None:
            self._last_review = last_review
        self._render()

    def _render(self) -> None:
        """Render the 3-line status panel."""
        # Line 1: credits + tokens
        remaining = max(0, self._credits_total - self._credits_spent)
        bar_len = 20
        filled = int(bar_len * self._credits_spent / max(1, self._credits_total))
        bar = "█" * filled + "░" * (bar_len - filled)
        total_tokens = self._tokens_prompt + self._tokens_completion

        line1 = Text.assemble(
            Text(f" credits: {self._credits_spent}/{self._credits_total} 剩余{remaining} ", style="cyan"),
            Text(f"{bar}", style="yellow"),
            Text(f"  │  ", style="dim"),
            Text(f"tokens: {total_tokens}", style="green"),
            Text(f" (reasoning {self._tokens_reasoning})", style="dim"),
        )

        # Line 2: stage stats + total LLM calls
        line2 = Text.assemble(
            Text(f" 本环节: 工具调用 {self._stage_tool_calls} 次, review {self._stage_reviews} 次", style="white"),
            Text(f"  │  ", style="dim"),
            Text(f"总 LLM 调用: {self._total_llm_calls} 次", style="white"),
        )

        # Line 3: last error + last review
        err_style = "red" if self._last_error != "(无)" else "dim"
        rev_style = "red" if self._last_review not in ("(无)", "pass", "PASS") else "green"
        line3 = Text.assemble(
            Text(f" 上次工具报错: {self._last_error}", style=err_style),
            Text(f"  │  ", style="dim"),
            Text(f"上次 review: {self._last_review}", style=rev_style),
        )

        self.update(Text.assemble(line1, Text("\n"), line2, Text("\n"), line3))
