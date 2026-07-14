"""Knowledge base — error-signature retrieval (RAG).

First iteration: error-code / keyword matching (architecture §6.3).
Second iteration: functional-pattern / worked-example retrieval (§6.4).
"""
from .retriever import KnowledgeBase, KBEntry

__all__ = ["KnowledgeBase", "KBEntry"]
