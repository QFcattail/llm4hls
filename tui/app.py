"""TUI App - main dashboard assembling the three regions.

Region A (top): flow chart showing stage progress
Region B (middle): current activity (LLM streaming / tool call / idle)
Region C (bottom): resource panel (credits / tokens / last feedback)

The app runs the agent in a background thread and consumes events from
a queue to update the UI.
"""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import Label, Button
from textual.containers import Horizontal

from .flow_chart import FlowChart
from .activity_panel import ActivityPanel
from .status_bar import StatusBar
from .tool_error_bar import ToolErrorBar
from .task_picker import TaskPickerScreen, scan_tasks

# Version is shown in the TUI title bar (PROJECT-CONVENTIONS.md section 11).
try:
    from agent._version import __version__ as APP_VERSION
except ImportError:  # pragma: no cover - fallback if agent package not on path
    APP_VERSION = "unknown"


# Custom light theme, spec in docs-development/design/tui-design.md section 3.5:
#   primary    #587559  sage green - title bar, dialog border, headings
#   accent     #FDD100  gold       - accent + decoration (region borders)
#   background #FFFFFF  white, normal text black, CoT thinking stays gray
FPGA_LIGHT_THEME = Theme(
    name="fpga-light",
    primary="#587559",
    secondary="#3F5741",
    accent="#FDD100",
    warning="#FDD100",
    error="#B00020",
    success="#587559",
    foreground="#000000",
    background="#FFFFFF",
    surface="#FFFFFF",
    panel="#F2F2F2",
    dark=False,
    variables={
        "footer-key-foreground": "#587559",
    },
)


class QuitConfirmScreen(ModalScreen):
    """Confirmation dialog for quitting: 'q' shows this, not instant quit."""

    BINDINGS = [
        Binding("y", "confirm", "Yes, quit"),
        Binding("n", "cancel", "No, cancel"),
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Yes, quit"),
    ]

    def compose(self) -> ComposeResult:
        """Build the quit-confirmation dialog (message + Yes/Cancel buttons)."""
        with Vertical(id="quit-dialog"):
            yield Label("Quit the agent? (agent continues in background)", id="quit-msg")
            with Horizontal():
                yield Button("Yes, quit (y)", id="quit-yes", variant="error")
                yield Button("Cancel (n)", id="quit-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss with True (quit) or False (cancel) based on the button."""
        if event.button.id == "quit-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Keyboard 'y'/Enter binding: confirm quit."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Keyboard 'n'/Esc binding: cancel quit."""
        self.dismiss(False)


class AgentDashboard(App):
    """Main TUI dashboard - shows agent run progress in real time."""

    CSS = """
    #dashboard { layout: vertical; }
    #flow-chart { height: 5; border: round $accent; padding: 0 1; }
    #tool-error-bar { height: 7; border: round $accent; padding: 0 1; }
    #activity-panel { height: 1fr; border: round $accent; }
    #status-bar { height: 4; border: round $accent; padding: 0 1; }
    #quit-dialog {
        align: center middle;
        width: 50; height: 7;
        border: thick $primary;
        padding: 1 2;
    }
    #quit-msg { text-align: center; margin: 1 0; }
    #quit-dialog Horizontal { align: center middle; height: 3; }
    #quit-yes { margin: 0 1; }
    #quit-no { margin: 0 1; }
    """

    BINDINGS = [
        Binding("q", "request_quit", "Quit"),
    ]

    def action_request_quit(self) -> None:
        """Show quit confirmation dialog instead of quitting instantly."""
        def _on_result(result: bool) -> None:
            if result:
                self.exit()
        self.push_screen(QuitConfirmScreen(), _on_result)

    def __init__(
        self,
        task_path: str,
        backend: str = "deepseek",
        budget: int | None = None,
    ) -> None:
        super().__init__()
        # Header renders app.title; Header(name=...) is only the DOM node
        # name, so the version must go through self.title (conventions 11.3).
        self.title = f"FPGA Agent Dashboard v{APP_VERSION}"
        self.register_theme(FPGA_LIGHT_THEME)
        self.theme = FPGA_LIGHT_THEME.name
        self.task_path = task_path
        self.backend = backend
        self.budget_override = budget
        self._event_queue: queue.Queue = queue.Queue()
        self._agent_thread: threading.Thread | None = None
        self._agent_result: str | None = None
        self._start_time: float = 0
        self._task_info: dict = {}
        self._current_stage: str = "starting"
        self._stage_tool_calls: int = 0
        self._stage_reviews: int = 0
        self._credit_spent: int = 0
        self._last_error: str = "(none)"
        self._last_review: str = "(none)"
        self._done: bool = False
        self._error: str | None = None
        self._backend_ref = None  # hold ref for usage stats
        self._tool_running: str = ""  # current running tool kind ("csim"/"synth"/...)
        self._tool_start_time: float = 0  # when the tool started

    def compose(self) -> ComposeResult:
        """Build the four-region dashboard layout (A chart/B bar/C activity/D status)."""
        yield Header()
        with Vertical(id="dashboard"):
            yield FlowChart()
            yield ToolErrorBar()
            yield ActivityPanel()
            yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Start the agent in a background thread."""
        self._start_time = time.monotonic()
        self._agent_thread = threading.Thread(target=self._run_agent, daemon=True)
        self._agent_thread.start()
        self.set_interval(0.15, self._poll_events)

    def _run_agent(self) -> None:
        """Run the agent in a background thread."""
        import sys
        ROOT = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT / "contest" / "fpt26-harness"))

        from llm4hls import Budget, ToolServer, grade, load_task
        from agent.main_loop import Agent
        from agent.llm_client import HLSLLMClient
        from agent.knowledge_base import KnowledgeBase, seed_entries
        from agent.score_history import (
            format_history, recent_scores, record_score,
        )

        task = load_task(self.task_path)
        total = self.budget_override if self.budget_override is not None else task.budget
        budget = Budget(total=total)
        work_root = ROOT / "runs" / task.id
        server = ToolServer(task, budget, work_root / "agent")

        # choose backend
        if self.backend == "deepseek":
            from agent.deepseek_client import DeepSeekClient
            def stream_cb(kind: str, text: str) -> None:
                """Forward one streamed LLM token to the UI event queue."""
                self._event_queue.put(("stream", {"kind": kind, "text": text}))
            backend = DeepSeekClient(stream=True, on_stream=stream_cb)
        elif self.backend == "openrouter":
            from llm4hls.llm import OpenRouterClient
            backend = OpenRouterClient()
        else:
            from llm4hls.llm import ScriptedClient
            if task.reference_code is None:
                self._event_queue.put(("error", {"msg": "no reference code"}))
                return
            backend = ScriptedClient(["```cpp\n" + task.reference_code + "```"])

        self._backend_ref = backend
        llm = HLSLLMClient(backend)
        kb = KnowledgeBase(seed_entries())

        agent = Agent(task, server, llm, kb=kb, run_dir=work_root)
        original_event = agent.log.event

        def queued_event(event: str, **fields) -> None:
            """Write the JSONL event, then forward it to the UI event queue."""
            original_event(event, **fields)
            self._event_queue.put(("event", {"name": event, **fields}))

        agent.log.event = queued_event

        original_hb_set = agent.hb.set_stage

        def queued_hb(stage: str, credit_remaining=None) -> None:
            """Update the heartbeat stage, then forward it to the UI queue."""
            original_hb_set(stage, credit_remaining)
            self._event_queue.put(("heartbeat", {
                "stage": stage,
                "credit": credit_remaining,
                "age": agent.log.age_s(),
            }))

        agent.hb.set_stage = queued_hb

        self._event_queue.put(("init", {
            "task_id": task.id,
            "task_type": task.type,
            "difficulty": task.difficulty,
            "budget": total,
        }))

        try:
            final = agent.run()
            self._agent_result = final
            summary = getattr(backend, "usage_summary", None)
            # Grade with the hidden testbench (uncharged, ~1-2 min) before
            # declaring done, so the score + recent history land on screen.
            self._event_queue.put(("event", {"name": "grading"}))
            score_data: dict = {}
            try:
                card = grade(task, final, work_root / "grade")
                tokens_total = None
                if hasattr(backend, "total_prompt"):
                    tokens_total = backend.total_prompt + backend.total_completion
                scores_path = work_root / "scores.jsonl"
                record_score(scores_path, score=card.score,
                             latency=card.candidate_latency,
                             credits=budget.spent, tokens=tokens_total)
                score_data = {
                    "score": card.score,
                    "latency": card.candidate_latency,
                    "render": card.render(),
                    "history": format_history(
                        recent_scores(scores_path, 5), task.id),
                }
            except Exception as ge:
                score_data = {"error": str(ge)}
            self._event_queue.put(("event", {"name": "score", **score_data}))
            self._event_queue.put(("done", {
                "summary": summary() if summary else "",
                "result": final[:200],
            }))
        except Exception as e:
            self._event_queue.put(("error", {"msg": str(e)}))

    def _poll_events(self) -> None:
        """Poll the event queue and update the UI (called every 150ms)."""
        # The 150ms interval can fire once more while shutdown is
        # unmounting widgets; drop that tick instead of crashing.
        try:
            updated = False
            while True:
                try:
                    kind, data = self._event_queue.get_nowait()
                except queue.Empty:
                    break
                updated = True
                self._handle_event(kind, data)
            if updated or not self._done:
                self._refresh_ui()
        except NoMatches:
            return

    def _handle_event(self, kind: str, data: dict) -> None:
        """Handle a single event from the agent thread."""
        if kind == "init":
            self._task_info = data
            self._credit_total = data.get("budget", 0)
        elif kind == "event":
            self._handle_agent_event(data)
        elif kind == "stream":
            self._handle_stream(data)
        elif kind == "heartbeat":
            stage = data.get("stage", self._current_stage)
            self._current_stage = stage
            # When a tool starts running, record start time
            if stage in ("csim", "synth", "cosim") and self._tool_running != stage:
                self._tool_running = stage
                self._tool_start_time = time.monotonic()
        elif kind == "done":
            self._done = True
            self._done_summary = data.get("summary", "")
        elif kind == "error":
            self._error = data.get("msg", "unknown error")

    def _handle_agent_event(self, data: dict) -> None:
        """Handle an agent log event."""
        name = data.get("name", "")
        fc = self.query_one(FlowChart)

        if name == "route":
            self._current_stage = "route"
            self._stage_tool_calls = 0
            self._stage_reviews = 0
            fc.mark_current("route")
            fc.update_stage("route", "done", stat=data.get("task_type", ""))

        elif name == "phase_enter":
            phase = data.get("phase", "")
            self._current_stage = phase
            self._stage_tool_calls = 0
            self._stage_reviews = 0
            # Reset per-stage feedback fields so a previous stage's review/
            # error never lingers and reads like a current failure.
            self._last_review = "(none)"
            self._last_error = "(none)"
            fc.mark_current(phase if phase in ("correctness", "synth", "optimize") else "correctness")
            # Arm the optimize-stage strategy panel (v4); outside optimize
            # the strategy zone stays cleared. v5: stage tag in waiting line.
            teb = self.query_one(ToolErrorBar)
            if phase == "optimize":
                teb.clear_bar()
                teb.show_strategies([], [], "")
            else:
                teb.clear_strategies()
            teb.set_stage_hint(phase)

        elif name == "phase_exit":
            phase = data.get("phase", "")
            result = data.get("result", "")
            status = "done" if result == "ok" else "failed"
            fc.update_stage(phase, status)
            if phase == "optimize":
                self.query_one(ToolErrorBar).clear_strategies()

        elif name == "llm_call":
            # v5 rule 2: the strategy-zone ready line follows the optimize
            # sub-phase (these purposes only fire inside optimize).
            ready_map = {
                "extract_brief": "optimizing: extracting design brief...",
                "propose_strategies": "optimizing: proposing strategies...",
                "select_strategies": "optimizing: selector reviewing...",
                "apply_strategies": "optimizing: applying picked...",
            }
            purpose = data.get("purpose", "")
            if purpose in ready_map:
                self.query_one(ToolErrorBar).show_ready(ready_map[purpose])

        elif name == "grading":
            ap = self.query_one(ActivityPanel)
            ap.set_activity("idle",
                            "grading hidden testbench... (~1-2 min)")
            fc.mark_current("submit")

        elif name == "score":
            ap = self.query_one(ActivityPanel)
            if data.get("error"):
                ap.append_log(f"  grading failed: {data['error']}\n")
            else:
                score = data.get("score", 0.0)
                fc.update_stage("submit", "done", stat=f"SCORE {score:.3f}")
                ap.append_log("\n" + data.get("render", "") + "\n")
                ap.append_log(data.get("history", "") + "\n")
                ap.set_activity("idle", f"graded: SCORE {score:.3f}")

        elif name == "tool_result":
            kind_t = data.get("kind", "")
            phase = data.get("phase", "")
            ok = data.get("ok", False)
            elapsed = data.get("elapsed_s", 0)
            self._credit_spent = data.get("credit_spent", self._credit_spent)
            self._stage_tool_calls += 1
            log_text = data.get("log", "")
            # Tool finished - clear running state
            self._tool_running = ""

            # Update ToolErrorBar (region B) with parsed error details
            teb = self.query_one(ToolErrorBar)
            teb.show_result(kind_t, phase, ok, elapsed, log_text)

            # For status bar, keep a short summary
            if not ok:
                error_lines = [l.strip() for l in log_text.split("\n")
                               if l.strip() and ("error" in l.lower() or "fail" in l.lower())]
                if error_lines:
                    self._last_error = error_lines[0][:60]
                else:
                    self._last_error = phase
            else:
                self._last_error = "(none)"

            # Update activity panel
            ap = self.query_one(ActivityPanel)
            if ok:
                ap.set_activity("idle", f"[{kind_t}] {phase} ✅ ({elapsed:.1f}s)")
            else:
                ap.set_activity("idle", f"[{kind_t}] {phase} ❌ - see error details above")

        elif name == "review":
            verdict = data.get("verdict", "")
            self._stage_reviews += 1
            self._last_review = verdict
            if verdict == "reject":
                self._last_review = f"reject: {data.get('issues', '')[:80]}"

        elif name == "mechanical_review":
            passed = data.get("passed", False)
            if not passed:
                issues = data.get("issues", [])
                self._last_review = f"mechanical ❌: {'; '.join(issues)[:80]}"
                # v5 rule 1: review failures belong in the error bar too,
                # not only in the status-bar field.
                self.query_one(ToolErrorBar).show_review_issue(issues)

        elif name == "strategy_select":
            # optimize v2.4+: selector AI picked a (possibly combined) subset
            # v2.7: rejected strategies and parse-fallback are also shown
            teb = self.query_one(ToolErrorBar)
            reason = data.get("reason", "")
            if data.get("fallback"):
                reason = "⚠ selector output unparsed — fell back to first strategy"
            rejected = data.get("rejected") or []
            if rejected:
                reason = (reason + "  │  ✗ rejected: " + "; ".join(
                    str(r.get("name")) for r in rejected))[:120]
            teb.show_strategies(data.get("all", []), data.get("picked", []),
                                reason)

        elif name == "optimize_fallback":
            # combo failed -> retrying the first strategy alone
            teb = self.query_one(ToolErrorBar)
            teb.update_picked(data.get("picked", []),
                              "fallback: " + data.get("reason", ""))

        elif name == "checkpoint":
            old = data.get("old", 0)
            new = data.get("new", 0)
            latency = data.get("latency")
            stat = f"Lv{old}->Lv{new}"
            if latency is not None:
                stat += f" lat={latency}"

        elif name == "submit":
            fc.update_stage("submit", "done")

    def _handle_stream(self, data: dict) -> None:
        """Handle a streaming token from the LLM.

        When LLM streaming starts (first token), inject the last tool error
        into the log so the user can see what the LLM is responding to.
        """
        ap = self.query_one(ActivityPanel)
        if ap._activity_type != "llm":
            ap.set_activity("llm", f"{self._current_stage} LLM call")
            # Show what the LLM is fixing, before streaming starts
            if hasattr(self, "_last_error") and self._last_error != "(none)":
                ap.append_log(f"  📋 last tool result: {self._last_error}\n")
                # Switch back to llm mode for streaming
                ap._activity_type = "llm"
        ap.append_stream(data.get("kind", "content"), data.get("text", ""))

    def _refresh_ui(self) -> None:
        """Refresh UI with current state."""
        # Update activity panel elapsed
        ap = self.query_one(ActivityPanel)
        if not self._done and self._error is None:
            ap._render()

        # If a tool is running, refresh the ToolErrorBar with live elapsed time
        if self._tool_running:
            elapsed = time.monotonic() - self._tool_start_time
            teb = self.query_one(ToolErrorBar)
            teb.show_running(self._tool_running, elapsed)

        # Update status bar
        sb = self.query_one(StatusBar)
        total = getattr(self, "_credit_total", 0)
        prompt = 0
        completion = 0
        reasoning = 0
        llm_calls = 0
        if self._backend_ref:
            prompt = getattr(self._backend_ref, "total_prompt", 0)
            completion = getattr(self._backend_ref, "total_completion", 0)
            reasoning = getattr(self._backend_ref, "total_reasoning", 0)
            llm_calls = getattr(self._backend_ref, "calls", 0)
        sb.update_state(
            credits_spent=self._credit_spent,
            credits_total=total,
            tokens_prompt=prompt,
            tokens_completion=completion,
            tokens_reasoning=reasoning,
            stage_tool_calls=self._stage_tool_calls,
            stage_reviews=self._stage_reviews,
            total_llm_calls=llm_calls,
            last_error=self._last_error,
            last_review=self._last_review,
        )

        if self._done:
            total_s = time.monotonic() - self._start_time
            ap.set_activity(
                "idle",
                f"DONE - {getattr(self, '_done_summary', '')} "
                f"| total {total_s / 60:.1f} min")
        elif self._error:
            ap.set_activity("idle", f"ERROR: {self._error}")


def run_tui(task_path: str, backend: str = "deepseek", budget: int | None = None) -> None:
    """Entry point: start the TUI dashboard for a given task.

    Args:
        task_path: Path to the task directory.
        backend: LLM backend ("deepseek", "scripted", "openrouter").
        budget: Override credit budget (None = use task default).
    """
    app = AgentDashboard(task_path=task_path, backend=backend, budget=budget)
    app.run()
