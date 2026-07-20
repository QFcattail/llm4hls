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
import os
import sys
from pathlib import Path

# Make both our agent package and the harness package importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))                              # for `agent`
sys.path.insert(0, str(ROOT / "contest" / "fpt26-harness"))  # for `llm4hls`

from llm4hls import Budget, ToolServer, grade, load_task   # noqa: E402
from llm4hls.llm import OpenRouterClient, ScriptedClient   # noqa: E402

from agent.knowledge_base import KnowledgeBase, seed_entries  # noqa: E402
from agent.llm_client import HLSLLMClient                  # noqa: E402
from agent.main_loop import Agent                          # noqa: E402


def _check_vitis_available() -> bool:
    """Check if vitis-run is on PATH (i.e. settings64.sh has been sourced).

    Without Vitis, every csim/synth/cosim call returns compile_error with
    elapsed_s≈0, producing misleading SCORE 0.000 output that looks like the
    agent failed when really the toolchain just isn't installed.
    """
    import shutil
    return shutil.which("vitis-run") is not None


def _auto_source_vitis() -> bool:
    """Try to auto-source Vitis settings64.sh if vitis-run is not on PATH.

    Checks known locations. If found, sources it and updates os.environ PATH.
    Returns True if vitis-run is available after this call.
    """
    if _check_vitis_available():
        return True
    candidates = [
        "/home/admin/Xilinx/2025.2/Vitis/settings64.sh",
        "/opt/Xilinx/2025.2/Vitis/settings64.sh",
    ]
    for settings in candidates:
        if Path(settings).exists():
            import subprocess
            result = subprocess.run(
                ["bash", "-c", f"source '{settings}' && echo $PATH"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                os.environ["PATH"] = result.stdout.strip()
                return _check_vitis_available()
    return False


def main() -> int:
    """Parse CLI args, assemble the agent, run one task, and grade it.

    Returns:
        Process exit code: 0 on success, 1 when Vitis is unavailable or
        the scripted backend has no reference code to replay.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir")
    ap.add_argument("--backend", choices=["scripted", "openrouter", "deepseek"],
                    default="scripted")
    ap.add_argument("--budget", type=int, default=None)
    ap.add_argument("--work", default=None)
    ap.add_argument("--force", action="store_true",
                    help="run even if Vitis is not detected (csim will fail)")
    ap.add_argument("--token-mode", choices=["full", "balanced", "aggressive"],
                    default="full",
                    help="token-saving level (P4-03). 'full' (default) = no "
                         "restrictions, identical to pre-P4-03 behavior; "
                         "'balanced'/'aggressive' disable LLM thinking for "
                         "cheap call sites and trim redundant prompt blocks.")
    args = ap.parse_args()

    # Guard: refuse to run without Vitis, because every csim/synth/cosim will
    # return compile_error and the SCORE 0.000 output is misleading.
    # Try auto-source first; if that fails, error out (unless --force).
    if not _check_vitis_available():
        _auto_source_vitis()
    if not _check_vitis_available() and not args.force:
        print(
            "ERROR: vitis-run not found on PATH.\n"
            "  Vitis 2025.2 is required for csim/synth/cosim. Source its\n"
            "  settings64.sh first, e.g.:\n"
            "    source /home/admin/Xilinx/2025.2/Vitis/settings64.sh\n"
            "  To run anyway (csim will fail — for framework testing only):\n"
            "    python scripts/run_agent.py ... --force",
            file=sys.stderr,
        )
        return 1

    task = load_task(args.task_dir)
    total = args.budget if args.budget is not None else task.budget
    budget = Budget(total=total)

    work_root = Path(args.work) if args.work else ROOT / "runs" / task.id
    server = ToolServer(task, budget, work_root / "agent")

    if args.backend == "openrouter":
        backend = OpenRouterClient()
    elif args.backend == "deepseek":
        from agent.deepseek_client import DeepSeekClient
        backend = DeepSeekClient()
    else:
        if task.reference_code is None:
            print("scripted backend requires a reference/ solution",
                  file=sys.stderr)
            return 1
        backend = ScriptedClient(["```cpp\n" + task.reference_code + "```"])

    llm = HLSLLMClient(backend)
    kb = KnowledgeBase(seed_entries())   # seed corpus; P2-12 extends it

    print(f"=== Task {task.id} [{task.type}, difficulty {task.difficulty}] ===")
    print(f"    budget: {total} credits | backend: {args.backend}")

    agent = Agent(task, server, llm, kb=kb, run_dir=work_root,
                  token_mode=args.token_mode)
    final = agent.run()

    # report LLM usage if the backend tracks it
    summary = getattr(backend, "usage_summary", None)
    if summary:
        print(f"\n{summary()}")

    print("\n--- metered tool transcript ---")
    for e in server.transcript:
        print(f"  #{e.n:<2} {e.detail}   [spent {e.spent}/{total}]")
    print(f"  {budget.summary()}")

    print("\n=== Grading (hidden testbench + PPA, uncharged) ===")
    card = grade(task, final, work_root / "grade")
    print(card.render())

    # Record the score so both CLI and TUI runs share one history (§3.6).
    from agent.score_history import (
        format_history, recent_scores, record_score,
    )
    scores_path = work_root / "scores.jsonl"
    tokens_total = None
    if hasattr(backend, "total_prompt"):
        tokens_total = backend.total_prompt + backend.total_completion
    record_score(scores_path, score=card.score,
                 latency=card.candidate_latency, credits=budget.spent,
                 tokens=tokens_total)
    print("\n" + format_history(recent_scores(scores_path, 5), task.id))

    out = work_root / f"final_{task.kernel_name}"
    out.write_text(final)
    print(f"\nfinal kernel -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
