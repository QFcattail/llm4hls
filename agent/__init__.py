"""Budgeted End-to-End LLM4HLS Agent.

Forks the official harness (contest/fpt26-harness/llm4hls/) for the metered
tool surface (ToolServer / Budget / Task) and replaces the reference agent
loop with our own: router -> checkpoint-gated correctness -> synth -> optimize.

Architecture reference: docs-development/design/agent-architecture.md

Modules:
    router        task.toml -> RunPlan (which stages to pass, whether to optimize)
    checkpoint    checkpoint level comparison + the three archive rules
    main_loop     the linear-with-backtracking main loop
    feedback      build LLM-friendly feedback from ToolResult
    llm_client    HLS-domain LLM wrappers (repair / propose_strategies / ...)
    observability structured logging + heartbeat + timeout tiers
    knowledge_base error-signature + pattern retrieval (RAG)
"""

from .router import RunPlan, route
from .checkpoint import Checkpoint, Level

__all__ = ["RunPlan", "route", "Checkpoint", "Level"]
