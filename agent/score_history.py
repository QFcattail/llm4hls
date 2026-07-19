"""Score history — per-task record of grading outcomes across runs.

Every grading (from the CLI driver or the TUI) appends one JSON line to
``runs/<task_id>/scores.jsonl`` so users can see both the latest result and
the convergence trend across repeated runs (tui-design §3.6). The file is
append-only and small (one line per run); no rotation for now.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def record_score(path: Path | str, *, score: float,
                 latency: int | None = None, credits: int | None = None,
                 tokens: int | None = None) -> None:
    """Append one score record to the history file.

    Args:
        path: The scores.jsonl path (usually ``runs/<task_id>/scores.jsonl``).
        score: The final grade score (e.g. 3.000).
        latency: Candidate latency in cycles, when known.
        credits: Credits spent during the run, when known.
        tokens: Total LLM tokens used, when known.
    """
    record = {"ts": round(time.time(), 1), "score": round(float(score), 3),
              "latency": latency, "credits": credits, "tokens": tokens}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def recent_scores(path: Path | str, n: int = 5) -> list[dict]:
    """Read the newest ``n`` score records, oldest first.

    Args:
        path: The scores.jsonl path.
        n: Maximum number of records to return.

    Returns:
        A list of record dicts (may be empty when the file is missing).
        Malformed lines are skipped.
    """
    p = Path(path)
    if not p.exists():
        return []
    records: list[dict] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records[-n:]


def format_history(records: list[dict], task_id: str) -> str:
    """Render score records as a plain-text table for logs / panels.

    Args:
        records: Records from :func:`recent_scores` (oldest first).
        task_id: Task identifier shown in the header line.

    Returns:
        A multi-line string, or a single "no history" line when empty.
    """
    if not records:
        return f"recent scores ({task_id}): (none yet)"
    lines = [f"recent scores ({task_id}):"]
    for r in records:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("ts", 0)))
        parts = [f"SCORE {r.get('score', 0):.3f}"]
        if r.get("latency") is not None:
            parts.append(f"lat={r['latency']}")
        if r.get("credits") is not None:
            parts.append(f"credits={r['credits']}")
        if r.get("tokens") is not None:
            parts.append(f"tokens={r['tokens']}")
        lines.append(f"  {ts}  {'  '.join(parts)}")
    return "\n".join(lines)
