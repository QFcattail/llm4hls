"""Router — read task metadata and decide the stage path.

Implements agent-architecture.md §3. Runs once per task at entry. Costs zero
credits: it only reads task.toml fields (task_type, requires_cosim) and the
header, never invokes a tool.

Key correction from an earlier design: the router does NOT decide "C vs HLS"
(input is always HLS C++ with a header-locked signature), does NOT skip low
stages (grading re-runs every stage anyway, and editing for a later bug can
break an earlier stage), and does NOT run a tool for diagnosis. It only picks
which stages form the correctness gate.
"""
from __future__ import annotations

from dataclasses import dataclass

# Imported lazily inside route() to avoid a hard coupling at import time;
# callers usually already hold a Task from llm4hls.load_task.


@dataclass
class RunPlan:
    """The plan handed to the main loop.

    Attributes:
        task_type: One of "generate", "repair", "optimize", "structural".
        correctness_stages: Ordered list of correctness gate stages, either
            ["csim"] or ["csim", "cosim"] (the latter when cosim is required).
        needs_optimize: Whether to enter PPA optimization after synth holds.
        initial_level: Starting checkpoint level of the seed code.
    """

    task_type: str                  # generate | repair | optimize | structural
    correctness_stages: list[str]   # ["csim"] or ["csim", "cosim"]
    needs_optimize: bool            # enter PPA optimization after synth
    initial_level: int              # starting checkpoint level of the seed code


def route(task) -> RunPlan:
    """Build a RunPlan from a llm4hls.Task.

    `task` is the harness Task dataclass (has .type and .requires_cosim).

    Args:
        task: A harness Task object exposing ``.type`` and ``.requires_cosim``.

    Returns:
        A RunPlan describing the correctness gate, optimization entry, and
        initial checkpoint level for the task.
    """
    needs_cosim = bool(getattr(task, "requires_cosim", False))
    correctness_stages = ["csim", "cosim"] if needs_cosim else ["csim"]

    # Initial level: optimize seeds usually already pass csim; everything else
    # starts at NONE and must earn CORRECT in the repair loop.
    task_type = task.type
    if task_type == "optimize":
        initial_level = 1            # assume csim-correct; the loop confirms it
    else:
        initial_level = 0

    # Every task type can benefit from optimization once correctness+synth hold.
    needs_optimize = True

    return RunPlan(
        task_type=task_type,
        correctness_stages=correctness_stages,
        needs_optimize=needs_optimize,
        initial_level=initial_level,
    )
