"""Knowledge base — error-signature retrieval (RAG).

First iteration: error-code / keyword matching (architecture §6.3).
Second iteration: functional-pattern / worked-example retrieval (§6.4).
"""
from .entries import seed_entries
from .retriever import KnowledgeBase, KBEntry

__all__ = ["KnowledgeBase", "KBEntry", "seed_entries"]
