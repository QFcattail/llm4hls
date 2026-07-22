"""Knowledge-base corpus loader (architecture §9 migration, 2026-07-20).

The corpus lives in ``entries.json`` next to this module — data is decoupled
from code so entries can be edited/reviewed without touching Python (and the
contest submission can show the KB as a standalone artifact). JSON is used
instead of YAML because the project is pure-stdlib (no PyYAML dependency);
the schema matches the draft in 备赛学习手册 appendix B:

    {"id", "symptom", "root_cause", "fix", "example", "signatures": [...]}

Entry sources and growth history are documented in
``agent/knowledge_base/entries.doc.md`` (bilingual companion). Keep
signatures lowercase keywords/codes — the retriever does case-insensitive
substring matching.
"""
from __future__ import annotations

import json
from pathlib import Path

from .retriever import KBEntry

_CORPUS_PATH = Path(__file__).with_name("entries.json")


def load_entries(path: Path | str | None = None) -> list[KBEntry]:
    """Load KBEntry objects from the JSON corpus.

    Args:
        path: Corpus file path (default: ``entries.json`` next to this
            module).

    Returns:
        The list of KBEntry objects, corpus order preserved.

    Raises:
        FileNotFoundError: If the corpus file is missing (broken checkout).
        ValueError: If an entry lacks the required fields.
    """
    p = Path(path) if path is not None else _CORPUS_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"KB corpus not found: {p} (entries.json must ship next to "
            f"entries.py)")
    raw = json.loads(p.read_text(encoding="utf-8"))
    entries: list[KBEntry] = []
    for i, item in enumerate(raw):
        try:
            entries.append(KBEntry(
                id=item["id"],
                symptom=item["symptom"],
                root_cause=item["root_cause"],
                fix=item["fix"],
                example=item.get("example", ""),
                signatures=list(item.get("signatures", [])),
            ))
        except KeyError as e:
            raise ValueError(f"KB corpus entry #{i} missing field {e}") from e
    return entries


def seed_entries() -> list[KBEntry]:
    """Return the KB corpus (kept name for backward compatibility).

    Historically this returned a hardcoded seed list; since the §9 migration
    it loads ``entries.json``. Callers (run_agent.py, TUI, tests) are
    unaffected.
    """
    return load_entries()
