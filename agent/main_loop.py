"""Main loop — linear-with-backtracking correctness/synth/optimize flow.

Implements agent-architecture.md §4. The loop is linear in order
(correct -> synth -> optimize) but every edit triggers re-verification of
already-passed stages, because editing for a later bug can break an earlier
one (see §5). The checkpoint (§2) gives rollback for free.

First iteration scope: correctness stage fully wired (ScriptedClient-ready).
synth + optimize stages are structured but their inner detail (AMD Phase 2
strategy selection) is fleshed out in P4.
"""
from __future__ import annotations

from pathlib import Path

from .checkpoint import Checkpoint, Level
from .feedback import build_feedback
from .llm_client import HLSLLMClient
from .mechanical_checks import mechanical_review
from .observability import Heartbeat, Logger
from .router import RunPlan, route

# Harness types (imported at call time to keep this module importable without
# the harness on the path during partial development).
from llm4hls.budget import BudgetExceeded  # noqa: E402


class Agent:
    """Our agent. Replaces llm4hls.ReferenceAgent with the §4 architecture."""

    def __init__(
        self,
        task,
        server,                 # llm4hls.ToolServer
        llm: HLSLLMClient,
        kb=None,                # knowledge_base retriever or None
        max_rounds: int = 6,
        run_dir: Path | str = "runs",
    ) -> None:
        self.task = task
        self.server = server
        self.llm = llm
        self.kb = kb
        self.max_rounds = max_rounds
        self.log = Logger(task.id, run_dir)
        self.hb = Heartbeat(self.log)

    # -- entry point ------------------------------------------------------
    def run(self) -> str:
        plan = route(self.task)
        ckpt = Checkpoint(code=self.task.kernel_code, level=plan.initial_level)
        self.log.event("route", task_type=plan.task_type,
                       correctness_stages=plan.correctness_stages,
                       initial_level=plan.initial_level,
                       budget=self.server.budget.total)
        self.hb.start()
        try:
            return self._run_plan(plan, ckpt)
        except BudgetExceeded as e:
            self.log.event("budget_exhausted", error=str(e),
                           best_level=ckpt.level, best_latency=ckpt.latency)
            return ckpt.code
        finally:
            self.hb.stop()
            self.log.event("submit", final_level=ckpt.level,
                           final_latency=ckpt.latency,
                           credit_spent=self.server.budget.spent)

    def _run_plan(self, plan: RunPlan, ckpt: Checkpoint) -> str:
        # Stage 1: correctness
        ok = self._reach_correctness(plan, ckpt)
        if not ok:
            self.log.event("phase_exit", phase="correctness", result="failed",
                           best_level=ckpt.level)
            return ckpt.code
        self.log.event("phase_exit", phase="correctness", result="ok",
                       best_level=ckpt.level)

        # Stage 2: synth (baseline PPA + synth points)
        best_latency = self._do_synth(plan, ckpt)
        if best_latency is None and ckpt.level < Level.SYNTH:
            return ckpt.code   # couldn't synth; keep correct version

        # Stage 3: optimize
        if plan.needs_optimize and ckpt.level >= Level.SYNTH:
            self._optimize(plan, ckpt)
            if plan.task_type == "structural":
                self._post_opt_cosim_recheck(ckpt)

        return ckpt.code

    # -- stage 1: correctness --------------------------------------------
    def _reach_correctness(self, plan: RunPlan, ckpt: Checkpoint) -> bool:
        """Repair loop until csim (+cosim if structural) pass. Returns ok."""
        for attempt in range(1, self.max_rounds + 1):
            if not self.server.budget.can_afford("csim"):
                self.log.event("budget_exhausted", where="correctness-csim",
                               best_level=ckpt.level)
                return ckpt.level >= Level.CORRECT

            self.hb.set_stage("csim", self.server.budget.remaining())
            csim_r = self.server.csim(ckpt.code)
            self.log.event("tool_result", kind="csim", phase=csim_r.phase,
                           ok=csim_r.ok, rc=csim_r.return_code,
                           elapsed_s=round(csim_r.elapsed_s, 1),
                           credit_spent=self.server.budget.spent)

            cosim_r = None
            if csim_r.ok and "cosim" in plan.correctness_stages:
                if not self.server.budget.can_afford("cosim"):
                    self.log.event("budget_exhausted", where="correctness-cosim",
                                   best_level=ckpt.level)
                    return False
                self.hb.set_stage("cosim", self.server.budget.remaining())
                cosim_r = self.server.cosim(ckpt.code)
                self.log.event("tool_result", kind="cosim", phase=cosim_r.phase,
                               ok=cosim_r.ok, rc=cosim_r.return_code,
                               elapsed_s=round(cosim_r.elapsed_s, 1),
                               credit_spent=self.server.budget.spent)

            passed = csim_r.ok and (cosim_r is None or cosim_r.ok)
            if passed:
                # correctness gate reached -> archive advances to CORRECT
                if ckpt.should_accept(Level.CORRECT, None):
                    ckpt.accept(ckpt.code, Level.CORRECT, None,
                                cosim_ok=(cosim_r.ok if cosim_r else None))
                    self.log.event("checkpoint", old=Level.NONE, new=Level.CORRECT,
                                   reason="correctness_gate")
                return True

            # failed -> diagnose, retrieve KB, edit, review, retry
            fb = build_feedback(csim_r, cosim_r)
            kb_text = self._kb_lookup(fb)
            new_code = self._repair_with_review(ckpt.code, fb.as_prompt_block(), kb_text)
            if new_code is None:
                self.log.event("repair_failed", attempt=attempt, reason="no_code")
                break
            ckpt.code = new_code   # candidate becomes next input (level unchanged)

        return ckpt.level >= Level.CORRECT

    def _repair_with_review(self, code: str, feedback_text: str, kb_text: str) -> str | None:
        """Generate a repair, then cross-check before returning it.

        Two gates: (1) mechanical checks (deterministic, catches signature/
        header changes the LLM misses), (2) LLM review (catches semantic bugs).
        """
        for retry in range(self.llm.max_review_retries + 1):
            self.hb.set_stage("llm", self.server.budget.remaining())
            new_code = self.llm.repair(self.task, code, feedback_text, kb_text)
            if new_code is None:
                return None

            # Gate 1: mechanical (hard) checks
            mech_ok, mech_issues = mechanical_review(code, new_code, self.task)
            self.log.event("mechanical_review", passed=mech_ok,
                           issues=mech_issues if not mech_ok else [])
            if not mech_ok:
                # feed the mechanical issues back into the next repair attempt
                feedback_text = feedback_text + "\n\nMUST FIX: " + "; ".join(mech_issues)
                continue

            # Gate 2: LLM review (self-check)
            passed, issues = self.llm.review(
                self.task, new_code,
                focus="signature/interface unchanged; no new bugs; pragma hazards",
            )
            self.log.event("review", verdict="pass" if passed else "reject",
                           retry=retry, issues=issues[:200])
            if passed:
                return new_code
        return new_code   # exhausted retries; return last attempt anyway

    # -- stage 2: synth ---------------------------------------------------
    def _do_synth(self, plan: RunPlan, ckpt: Checkpoint) -> int | None:
        if not self.server.budget.can_afford("synth"):
            self.log.event("skip", phase="synth", reason="no_budget")
            return None
        self.hb.set_stage("synth", self.server.budget.remaining())
        r = self.server.synth(ckpt.code)
        self.log.event("tool_result", kind="synth", phase=r.phase, ok=r.ok,
                       elapsed_s=round(r.elapsed_s, 1),
                       credit_spent=self.server.budget.spent)
        if r.ok and r.report is not None:
            lat = r.report.latency_worst or r.report.latency_avg
            if ckpt.should_accept(Level.SYNTH, lat):
                ckpt.accept(ckpt.code, Level.SYNTH, lat, cosim_ok=ckpt.cosim_ok)
                self.log.event("checkpoint", old=Level.CORRECT, new=Level.SYNTH,
                               latency=lat, reason="synth_ok")
            return lat
        return None

    # -- stage 3: optimize (P4 flesh-out) --------------------------------
    def _optimize(self, plan: RunPlan, ckpt: Checkpoint) -> None:
        # Stub: P4 will implement AMD Phase 1+2 here. For now, no-op so the
        # correctness-only first iteration still runs end to end.
        self.log.event("phase_enter", phase="optimize", best_level=ckpt.level,
                       note="stub_P4")

    def _post_opt_cosim_recheck(self, ckpt: Checkpoint) -> None:
        """structural: re-verify cosim after optimization (architecture §4.5)."""
        if not self.server.budget.can_afford("cosim"):
            return
        self.hb.set_stage("cosim", self.server.budget.remaining())
        r = self.server.cosim(ckpt.code)
        self.log.event("tool_result", kind="cosim_recheck", phase=r.phase,
                       ok=r.ok, credit_spent=self.server.budget.spent)
        if not r.ok:
            self.log.event("rollback", reason="optimization_reintroduced_hazard")

    # -- knowledge base ---------------------------------------------------
    def _kb_lookup(self, fb) -> str:
        if self.kb is None:
            return ""
        hits = self.kb.search(fb.signatures)
        self.log.event("kb_search", query=fb.signatures, hits=len(hits))
        return "\n\n".join(h.summary() for h in hits) if hits else ""
