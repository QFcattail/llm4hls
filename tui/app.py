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
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Horizontal

from .flow_chart import FlowChart
from .activity_panel import ActivityPanel
from .status_bar import StatusBar
from .tool_error_bar import ToolErrorBar
from .task_picker import TaskPickerScreen, scan_tasks


class QuitConfirmScreen(ModalScreen):
    """Confirmation dialog for quitting: 'q' shows this, not instant quit."""

    BINDINGS = [
        Binding("y", "confirm", "Yes, quit"),
        Binding("n", "cancel", "No, cancel"),
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Yes, quit"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-dialog"):
            yield Label("Quit the agent? (agent continues in background)", id="quit-msg")
            with Horizontal():
                yield Button("Yes, quit (y)", id="quit-yes", variant="error")
                yield Button("Cancel (n)", id="quit-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class AgentDashboard(App):
    """Main TUI dashboard - shows agent run progress in real time."""

    CSS = """
    #dashboard { layout: vertical; }
    #flow-chart { height: 5; border: round $primary; padding: 0 1; }
    #tool-error-bar { height: 7; border: round $warning; padding: 0 1; }
    #activity-panel { height: 1fr; border: round $accent; }
    #status-bar { height: 4; border: round $success; padding: 0 1; }
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
        self._last_error: str = "(无)"
        self._last_review: str = "(无)"
        self._done: bool = False
        self._error: str | None = None
        self._backend_ref = None  # hold ref for usage stats

    def compose(self) -> ComposeResult:
        yield Header(name="FPGA Agent Dashboard")
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

        from llm4hls import Budget, ToolServer, load_task
        from agent.main_loop import Agent
        from agent.llm_client import HLSLLMClient
        from agent.knowledge_base import KnowledgeBase

        task = load_task(self.task_path)
        total = self.budget_override if self.budget_override is not None else task.budget
        budget = Budget(total=total)
        work_root = ROOT / "runs" / task.id
        server = ToolServer(task, budget, work_root / "agent")

        # choose backend
        if self.backend == "deepseek":
            from agent.deepseek_client import DeepSeekClient
            def stream_cb(kind: str, text: str) -> None:
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
        kb = KnowledgeBase()

        agent = Agent(task, server, llm, kb=kb, run_dir=work_root)
        original_event = agent.log.event

        def queued_event(event: str, **fields) -> None:
            original_event(event, **fields)
            self._event_queue.put(("event", {"name": event, **fields}))

        agent.log.event = queued_event

        original_hb_set = agent.hb.set_stage

        def queued_hb(stage: str, credit_remaining=None) -> None:
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
            self._event_queue.put(("done", {
                "summary": summary() if summary else "",
                "result": final[:200],
            }))
        except Exception as e:
            self._event_queue.put(("error", {"msg": str(e)}))

    def _poll_events(self) -> None:
        """Poll the event queue and update the UI (called every 150ms)."""
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
            # When a tool is running (csim/synth/cosim), show running status in ToolErrorBar
            if stage in ("csim", "synth", "cosim"):
                teb = self.query_one(ToolErrorBar)
                teb.show_running(stage, data.get("age", 0))
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
            fc.mark_current(phase if phase in ("correctness", "synth", "optimize") else "correctness")

        elif name == "phase_exit":
            phase = data.get("phase", "")
            result = data.get("result", "")
            status = "done" if result == "ok" else "failed"
            fc.update_stage(phase, status)

        elif name == "tool_result":
            kind_t = data.get("kind", "")
            phase = data.get("phase", "")
            ok = data.get("ok", False)
            elapsed = data.get("elapsed_s", 0)
            self._credit_spent = data.get("credit_spent", self._credit_spent)
            self._stage_tool_calls += 1
            log_text = data.get("log", "")

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
                self._last_error = "(无)"

            # Update activity panel
            ap = self.query_one(ActivityPanel)
            if ok:
                ap.set_activity("idle", f"[{kind_t}] {phase} ✅ ({elapsed:.1f}s)")
            else:
                ap.set_activity("idle", f"[{kind_t}] {phase} ❌ - 见上方错误详情")

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
            ap.set_activity("llm", f"{self._current_stage} LLM 调用")
            # Show what the LLM is fixing, before streaming starts
            if hasattr(self, "_last_error") and self._last_error != "(无)":
                ap.append_log(f"  📋 上次工具结果: {self._last_error}\n")
                # Switch back to llm mode for streaming
                ap._activity_type = "llm"
        ap.append_stream(data.get("kind", "content"), data.get("text", ""))

    def _refresh_ui(self) -> None:
        """Refresh UI with current state."""
        # Update activity panel elapsed
        ap = self.query_one(ActivityPanel)
        if not self._done and self._error is None:
            ap._render()

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
            ap.set_activity("idle", f"DONE - {getattr(self, '_done_summary', '')}")
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
