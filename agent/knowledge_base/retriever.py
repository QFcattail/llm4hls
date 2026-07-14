"""Knowledge base entries + first-iteration retriever.

Implements agent-architecture.md §6.3 (error-signature matching). Each entry
has error_code / symptom / root_cause / fix / example, plus a set of trigger
signatures (error codes + keywords) used for matching.

The retriever is deliberately simple (substring/keyword match). Embedding
retrieval is a later option once the corpus grows.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KBEntry:
    """One bug->fix entry."""

    id: str
    symptom: str
    root_cause: str
    fix: str
    example: str = ""
    signatures: list[str] = field(default_factory=list)  # trigger keys

    def summary(self) -> str:
        parts = [f"[{self.id}] {self.symptom}",
                 f"  root cause: {self.root_cause}",
                 f"  fix: {self.fix}"]
        if self.example:
            parts.append(f"  example: {self.example}")
        return "\n".join(parts)


class KnowledgeBase:
    """First-iteration retriever: match feedback signatures against entries."""

    def __init__(self, entries: list[KBEntry] | None = None) -> None:
        self.entries: list[KBEntry] = entries or []

    def add(self, entry: KBEntry) -> None:
        self.entries.append(entry)

    def search(self, signatures: list[str]) -> list[KBEntry]:
        """Return entries whose signatures match any of the query signatures.

        Matching is case-insensitive substring on either the entry's declared
        signatures or its symptom/root_cause text. Duplicates removed.
        """
        if not signatures:
            return []
        queries = [q.lower() for q in signatures if q]
        hits: list[KBEntry] = []
        seen: set[str] = set()
        for e in self.entries:
            haystack = " ".join(e.signatures + [e.symptom, e.root_cause]).lower()
            if any(q in haystack for q in queries):
                if e.id not in seen:
                    hits.append(e)
                    seen.add(e.id)
        return hits
