"""Checkpoint (archive) logic — the core data structure of the main loop.

Implements agent-architecture.md §2:

    Level 0: nothing passed                          -> 0 pts
    Level 1: csim passed (and cosim passed if needed)-> correct pts (0.5*diff)
    Level 2: Level 1 + synth passed                  -> + synth pts (0.2*diff)
    Level 3: Level 2 + latency data                  -> can compete on PPA

Archive rules (vs current best B, candidate C):
    1. level(C) > level(B)      -> always accept C
    2. level(C) == level(B)     -> accept C only if latency strictly lower
    3. level(C) < level(B)      -> never accept (correctness regression)

The archive also gives rollback for free: a failed candidate that broke an
earlier stage simply never enters best, so best stays at the last verified
version.
"""
from __future__ import annotations

from dataclasses import dataclass


# Checkpoint levels — monotone: higher is strictly better on the score ladder.
class Level:
    NONE = 0        # nothing passed (or only compile-style checks)
    CORRECT = 1     # correctness gate passed (csim, + cosim if structural)
    SYNTH = 2       # synthesizable; latency available for PPA comparison


@dataclass
class Checkpoint:
    """The current best-known state of one task run.

    Attributes:
        code:        the kernel source of the current best.
        level:       Level.NONE / CORRECT / SYNTH.
        latency:     synth/cosim latency in cycles (None until Level.SYNTH).
        cosim_ok:    whether cosim has passed for this code (structural gate).
    """

    code: str
    level: int = Level.NONE
    latency: int | None = None
    cosim_ok: bool | None = None

    def should_accept(self, cand_level: int, cand_latency: int | None) -> bool:
        """Apply the three archive rules to a candidate.

        Returns True iff the candidate replaces `self` as best.
        Caller is responsible for then updating code/level/latency.
        """
        if cand_level > self.level:
            return True                     # rule 1: more stages -> always accept
        if cand_level < self.level:
            return False                    # rule 3: regression -> never accept
        # rule 2: same level -> accept only if strictly faster (when comparable)
        if cand_latency is None or self.latency is None:
            return False                    # no latency to compare at this level
        return cand_latency < self.latency

    def accept(self, code: str, level: int, latency: int | None,
               cosim_ok: bool | None = None) -> None:
        """Commit a candidate as the new best (call only after should_accept)."""
        self.code = code
        self.level = level
        self.latency = latency
        self.cosim_ok = cosim_ok
