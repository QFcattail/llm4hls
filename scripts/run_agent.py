#!/usr/bin/env python3
"""Drive our agent on a task under a credit budget, then grade.

Mirrors the harness scripts/run_poc.py but uses OUR Agent (main_loop.Agent)
instead of ReferenceAgent. Same backends: 'scripted' (offline, replays the
task's reference/ solution) or 'openrouter' (real open-source model).

Usage:
    python scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix
    python scripts/run_agent.py contest/fpt26-harness/tasks/dotProduct_optimize --backend openrouter
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make both our agent package and the harness package importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))                              # for `agent`
sys.path.insert(0, str(ROOT / "contest" / "fpt26-harness"))  # for `llm4hls`

from llm4hls import Budget, ToolServer, grade, load_task   # noqa: E402
from llm4hls.llm import OpenRouterClient, ScriptedClient   # noqa: E402

from agent.knowledge_base import KnowledgeBase             # noqa: E402
from agent.llm_client import HLSLLMClient                  # noqa: E402
from agent.main_loop import Agent                          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir")
    ap.add_argument("--backend", choices=["scripted", "openrouter"],
                    default="scripted")
    ap.add_argument("--budget", type=int, default=None)
    ap.add_argument("--work", default=None)
    args = ap.parse_args()

    task = load_task(args.task_dir)
    total = args.budget if args.budget is not None else task.budget
    budget = Budget(total=total)

    work_root = Path(args.work) if args.work else ROOT / "runs" / task.id
    server = ToolServer(task, budget, work_root / "agent")

    if args.backend == "openrouter":
        backend = OpenRouterClient()
    else:
        if task.reference_code is None:
            print("scripted backend requires a reference/ solution",
                  file=sys.stderr)
            return 1
        backend = ScriptedClient(["```cpp\n" + task.reference_code + "```"])

    llm = HLSLLMClient(backend)
    kb = KnowledgeBase()           # empty for now; entries added in P2-12

    print(f"=== Task {task.id} [{task.type}, difficulty {task.difficulty}] ===")
    print(f"    budget: {total} credits | backend: {args.backend}")

    agent = Agent(task, server, llm, kb=kb, run_dir=work_root)
    final = agent.run()

    print("\n--- metered tool transcript ---")
    for e in server.transcript:
        print(f"  #{e.n:<2} {e.detail}   [spent {e.spent}/{total}]")
    print(f"  {budget.summary()}")

    print("\n=== Grading (hidden testbench + PPA, uncharged) ===")
    card = grade(task, final, work_root / "grade")
    print(card.render())

    out = work_root / f"final_{task.kernel_name}"
    out.write_text(final)
    print(f"\nfinal kernel -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
