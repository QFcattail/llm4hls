"""Observability — structured JSONL logging + heartbeat, per architecture §12.

Three layers:
  - harness transcript (already exists; audited, tool calls only)
  - structured events (this module): agent decision points -> JSONL
  - heartbeat (this module): liveness signal for stall detection

First iteration: write JSONL to stdout + a file; consume with `tail -f`.
Second iteration can render the same JSONL into a TUI/WebUI.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path


class Logger:
    """Append-only structured logger writing JSONL to a file + stdout.

    Attributes:
        task_id: Identifier of the task this logger tracks.
        run_dir: Directory holding the JSONL file.
        path: Path to the per-run JSONL transcript file.
    """

    def __init__(self, task_id: str, run_dir: Path | str = "runs") -> None:
        self.task_id = task_id
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / f"{task_id}.jsonl"
        # truncate per run
        self.path.write_text("")
        # Full prompt history lives beside the event log (v0.6.1): the
        # event log stays terse, this file holds every LLM call verbatim.
        self.prompt_path = self.run_dir / f"{task_id}_prompts.jsonl"
        self.prompt_path.write_text("")
        self._last_activity = time.monotonic()
        self._lock = threading.Lock()

    def _touch(self) -> None:
        """Update the last-activity timestamp under the lock."""
        with self._lock:
            self._last_activity = time.monotonic()

    def event(self, event: str, **fields) -> None:
        """Emit one structured event line.

        Args:
            event: Name of the event (e.g. "tool_result").
            **fields: Arbitrary JSON-serializable fields attached to the event.
        """
        self._touch()
        record = {"ts": time.time(), "task": self.task_id, "event": event, **fields}
        line = json.dumps(record, ensure_ascii=False, default=str)
        self.path.open("a").write(line + "\n")
        print(f"[log] {event} {fields}", file=sys.stderr, flush=True)

    def prompt(self, purpose: str, system: str, user: str, response: str) -> None:
        """Record one LLM call verbatim (purpose + system + user + response).

        Written to ``<task_id>_prompts.jsonl`` next to the event log; the
        two files join on timestamps. No truncation — prompt debugging
        needs the exact bytes.

        Args:
            purpose: The domain call type (repair/review/extract_brief/
                propose_strategies/select_strategies/apply_strategies).
            system: The system prompt sent.
            user: The user prompt sent.
            response: The assistant's raw reply.
        """
        self._touch()
        record = {"ts": time.time(), "task": self.task_id,
                  "purpose": purpose, "system": system,
                  "user": user, "response": response}
        line = json.dumps(record, ensure_ascii=False, default=str)
        self.prompt_path.open("a").write(line + "\n")

    def age_s(self) -> float:
        """Return seconds since the last recorded activity."""
        with self._lock:
            return time.monotonic() - self._last_activity


# Heartbeat: a background thread that periodically reports liveness.
# Stall thresholds match the harness timeouts (csim 180 / synth 600 / cosim 900,
# LLM 180). If age exceeds the threshold for the current stage, flag STALE.

_STALL_THRESHOLD = {
    "csim": 180,
    "synth": 600,
    "cosim": 900,
    "llm": 180,
    "idle": 60,
}


class Heartbeat:
    """Background heartbeat thread for stall detection.

    Attributes:
        logger: The Logger to emit heartbeat events to.
        interval: Seconds between heartbeat checks.
        stage: Current stage name used to pick the stall threshold.
        credit_remaining: Optional remaining credit for reporting.
    """

    def __init__(self, logger: Logger, interval: float = 10.0) -> None:
        self.logger = logger
        self.interval = interval
        self.stage = "idle"
        self.credit_remaining: int | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def set_stage(self, stage: str, credit_remaining: int | None = None) -> None:
        """Update the current stage and optional remaining credit."""
        self.stage = stage
        self.credit_remaining = credit_remaining
        self.logger._touch()  # changing stage counts as activity

    def start(self) -> None:
        """Start the background heartbeat thread."""
        self._thread.start()

    def stop(self) -> None:
        """Signal the heartbeat thread to stop and wait for it to join."""
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        """Periodically report liveness and flag stalls based on age."""
        while not self._stop.wait(self.interval):
            age = self.logger.age_s()
            threshold = _STALL_THRESHOLD.get(self.stage, 60)
            stale = age > threshold
            self.logger.event(
                "heartbeat",
                stage=self.stage,
                age_s=round(age, 1),
                stale=stale,
                credit_remaining=self.credit_remaining,
            )
