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
    """Append-only structured logger writing JSONL to a file + stdout."""

    def __init__(self, task_id: str, run_dir: Path | str = "runs") -> None:
        self.task_id = task_id
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / f"{task_id}.jsonl"
        # truncate per run
        self.path.write_text("")
        self._last_activity = time.monotonic()
        self._lock = threading.Lock()

    def _touch(self) -> None:
        with self._lock:
            self._last_activity = time.monotonic()

    def event(self, event: str, **fields) -> None:
        """Emit one structured event line."""
        self._touch()
        record = {"ts": time.time(), "task": self.task_id, "event": event, **fields}
        line = json.dumps(record, ensure_ascii=False, default=str)
        self.path.open("a").write(line + "\n")
        print(f"[log] {event} {fields}", file=sys.stderr, flush=True)

    def age_s(self) -> float:
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
    """Background heartbeat thread for stall detection."""

    def __init__(self, logger: Logger, interval: float = 10.0) -> None:
        self.logger = logger
        self.interval = interval
        self.stage = "idle"
        self.credit_remaining: int | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def set_stage(self, stage: str, credit_remaining: int | None = None) -> None:
        self.stage = stage
        self.credit_remaining = credit_remaining
        self.logger._touch()  # changing stage counts as activity

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
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
