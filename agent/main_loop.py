"""Main loop — linear-with-backtracking correctness/synth/optimize flow.

Implements agent-architecture.md §4. The loop is linear in order
(correct -> synth -> optimize) but every edit triggers re-verification of
already-passed stages, because editing for a later bug can break an earlier
one (see §5). The checkpoint (§2) gives rollback for free.

Stage semantics (v2.3):
  1. correctness: csim (+cosim) repair loop with KB retrieval + review gates.
  2. synth: repair loop (§4.3) — RAG retrieval on synth errors, and every
     edit re-verifies csim before another synth attempt is spent.
  3. optimize (§4.4): AMD Phase 1 context loading (design document +
     extract_design_brief + synth report) -> Phase 2 strategy exploration ->
     Phase 3 apply_strategy -> review gates -> csim/synth re-verify ->
     same-level latency arbitration. Structural tasks get a post-optimization
     cosim re-check with real snapshot rollback (§4.5).
"""
from __future__ import annotations

from pathlib import Path

from .checkpoint import Checkpoint, Level
from .feedback import build_feedback
from .llm_client import HLSLLMClient, Strategy
from .mechanical_checks import mechanical_review
from .observability import Heartbeat, Logger
from .router import RunPlan, route

# Harness types (imported at call time to keep this module importable without
# the harness on the path during partial development).
from llm4hls.budget import BudgetExceeded  # noqa: E402


class Agent:
    """Our agent. Replaces llm4hls.ReferenceAgent with the §4 architecture.

    Drives a linear-with-backtracking correctness -> synth -> optimize flow.
    Every edit re-verifies already-passed stages (see §5) and the checkpoint
    (§2) provides rollback for free.

    Attributes:
        task: The harness Task to solve.
        server: The harness ToolServer used to run csim/synth/cosim.
        llm: The HLSLLMClient used for repair/review/optimization calls.
        kb: Optional knowledge-base retriever (None disables KB lookup).
        max_rounds: Maximum repair attempts in the correctness stage.
        max_synth_rounds: Maximum repair attempts after a synth failure (§4.3).
        max_optimize_rounds: Maximum PPA optimization rounds (§4.4).
        log: Structured event logger for this run.
        hb: Background heartbeat for stall detection.
    """

    def __init__(
        self,
        task,
        server,                 # llm4hls.ToolServer
        llm: HLSLLMClient,
        kb=None,                # knowledge_base retriever or None
        max_rounds: int = 6,
        max_synth_rounds: int = 3,
        max_optimize_rounds: int = 4,
        run_dir: Path | str = "runs",
        token_mode: str = "full",
    ) -> None:
        self.task = task
        self.server = server
        self.llm = llm
        self.kb = kb
        self.max_rounds = max_rounds
        self.max_synth_rounds = max_synth_rounds
        self.max_optimize_rounds = max_optimize_rounds
        self.log = Logger(task.id, run_dir)
        self.hb = Heartbeat(self.log)
        # Token-mode switch (P4-03): "full" (default) keeps the pre-P4-03
        # behavior everywhere; graded modes save tokens (see llm_client).
        self.token_mode = token_mode
        self.llm.token_mode = token_mode
        # Cross-stage state: filled by _do_synth / _optimize as they run.
        self._synth_summary: str | None = None   # latest passing synth report
        self._design_brief: str | None = None    # AMD Phase 1 brief (cached)
        self._pre_opt_snapshot: Checkpoint | None = None  # §4.5 rollback point
        # Verbatim prompt history (v0.7.2): every LLM call lands in
        # <task>_prompts.jsonl next to the event log.
        self.llm.prompt_recorder = self.log.prompt

    # -- entry point ------------------------------------------------------
    def run(self) -> str:
        """Run the full agent pipeline for this agent's task.

        Routes the task into a RunPlan, then executes correctness, synth, and
        optimization stages. Handles BudgetExceeded by returning the best
        checkpointed code. Always emits a final submit event.

        Returns:
            The final kernel source to submit (the best checkpointed code).
        """
        plan = route(self.task)
        ckpt = Checkpoint(code=self.task.kernel_code, level=plan.initial_level)
        self.log.event("route", task_type=plan.task_type,
                       correctness_stages=plan.correctness_stages,
                       initial_level=plan.initial_level,
                       budget=self.server.budget.total,
                       token_mode=self.token_mode)
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
        """Execute the three stages of a plan in order: correctness, synth, optimize.

        Each stage updates the checkpoint. Returns early if a stage fails in a
        way that prevents progression (keeping the best correct code).

        Args:
            plan: The RunPlan produced by the router.
            ckpt: The checkpoint tracking code/level/latency.

        Returns:
            The final kernel source from the checkpoint.
        """
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

        # Stage 3: optimize (+ final RTL sanity re-check, §4.5)
        if plan.needs_optimize and ckpt.level >= Level.SYNTH:
            self._optimize(plan, ckpt)
            self._post_opt_cosim_recheck(ckpt)

        return ckpt.code

    # -- stage 1: correctness --------------------------------------------
    def _reach_correctness(self, plan: RunPlan, ckpt: Checkpoint) -> bool:
        """Repair loop until csim (+cosim if structural) pass. Returns ok.

        For up to ``max_rounds`` attempts, runs csim (and cosim when the plan
        requires it), archives the code at CORRECT level on success, and on
        failure distills feedback, queries the KB, and repairs the candidate
        via the review-gated repair path.

        Args:
            plan: The RunPlan describing the correctness gate stages.
            ckpt: The checkpoint tracking code and level.

        Returns:
            True if the correctness gate was reached (or already held), False
            if rounds/budget were exhausted without success.
        """
        for attempt in range(1, self.max_rounds + 1):
            if not self.server.budget.can_afford("csim"):
                self.log.event("budget_exhausted", where="correctness-csim",
                               best_level=ckpt.level)
                return ckpt.level >= Level.CORRECT

            # Pre-csim LLM review: before spending a credit on csim, let the
            # LLM look at the code and fix obvious issues. On the first attempt
            # this catches bugs without needing a csim diagnostic at all; on
            # later attempts it reviews the previous repair before re-running.
            if attempt == 1:
                self.log.event("pre_csim_review", attempt=attempt)
                # Token note (P4-03): repair() already injects the FULL
                # description, so the snippet here is redundant. It is kept in
                # "full" mode (byte-identical legacy prompts) and dropped in
                # the graded token-saving modes.
                desc_snippet = (f"Description: {self.task.description[:500]}"
                                if self.token_mode == "full" else "")
                reviewed = self._repair_with_review(
                    ckpt.code,
                    feedback_text=f"Initial code for task {self.task.id}. "
                                  f"Review and fix any bugs before first csim. "
                                  f"Task type: {plan.task_type}. "
                                  f"{desc_snippet}",
                    kb_text=self._kb_lookup(build_feedback()),
                )
                if reviewed is not None and reviewed.strip() != ckpt.code.strip():
                    self.log.event("pre_csim_fix_applied",
                                   note="LLM found issues before first csim")
                    ckpt.code = reviewed
                else:
                    self.log.event("pre_csim_no_change",
                                   note="LLM found no issues, proceeding to csim")

            self.hb.set_stage("csim", self.server.budget.remaining())
            csim_r = self.server.csim(ckpt.code)
            # Detect environment failure: vitis-run not found (elapsed≈0, empty log)
            if not csim_r.ok and csim_r.elapsed_s < 0.5 and not csim_r.log.strip():
                self.log.event("env_error",
                               msg="vitis-run not found or settings64.sh not sourced. "
                                   "Set LLM4HLS_VITIS_HLS_ROOT and source settings64.sh.")
                raise RuntimeError(
                    "vitis-run not found or Vitis settings64.sh not sourced.\n"
                    "  This is an ENVIRONMENT problem, not a code bug.\n"
                    "  Fix: export LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis\n"
                    "       source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh"
                )
            self.log.event("tool_result", kind="csim", phase=csim_r.phase,
                           ok=csim_r.ok, rc=csim_r.return_code,
                           elapsed_s=round(csim_r.elapsed_s, 1),
                           credit_spent=self.server.budget.spent,
                           log=csim_r.log if not csim_r.ok else "")

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
                               credit_spent=self.server.budget.spent,
                               log=cosim_r.log if not cosim_r.ok else "")

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

        On a failed mechanical check, the issues are appended to the feedback
        text and another repair attempt is made (up to
        ``llm.max_review_retries`` extra retries).

        Args:
            code: The current kernel source to repair.
            feedback_text: Distilled tool feedback block to act on.
            kb_text: Knowledge-base hits text, or empty for none.

        Returns:
            The reviewed candidate kernel source, or None if the LLM produced
            no parseable code.
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
        """Synthesis gate with a repair loop (architecture §4.3).

        First attempts synth on the correct code. On failure, each round:
        distill feedback -> KB lookup -> review-gated repair -> re-verify
        csim (cheap, 1 credit) before spending another synth (4 credits).
        A repair that breaks csim is iterated with the csim feedback without
        burning a synth call. Gives up after ``max_synth_rounds`` repairs or
        when the budget cannot afford the next tool call.

        Args:
            plan: The RunPlan (used for budget/context; synth applies to all).
            ckpt: The checkpoint tracking code and level/latency.

        Returns:
            The worst (or average) latency from the synthesis report on
            success, or None if synth was skipped or never passed.
        """
        fb = None   # Feedback of the latest failure, drives the next repair
        for round_n in range(self.max_synth_rounds + 1):
            # 1) repair pass (skipped on the first attempt: no feedback yet)
            if fb is not None:
                if not self.server.budget.can_afford("csim"):
                    self.log.event("budget_exhausted", where="synth-fix-csim",
                                   best_level=ckpt.level)
                    return None
                new_code = self._repair_with_review(
                    ckpt.code, fb.as_prompt_block(), self._kb_lookup(fb))
                if new_code is None:
                    self.log.event("repair_failed", where="synth",
                                   round=round_n, reason="no_code")
                    return None
                # Re-verify csim before spending 4 credits on synth (§5:
                # fixing synth can break correctness).
                self.hb.set_stage("csim", self.server.budget.remaining())
                cr = self.server.csim(new_code)
                self.log.event("tool_result", kind="csim", phase=cr.phase,
                               ok=cr.ok, rc=cr.return_code,
                               elapsed_s=round(cr.elapsed_s, 1),
                               credit_spent=self.server.budget.spent,
                               log=cr.log if not cr.ok else "")
                if not cr.ok:
                    self.log.event("synth_fix_broke_csim", round=round_n)
                    fb = build_feedback(cr)   # iterate on the csim failure
                    continue
                ckpt.code = new_code   # correct candidate; synth it next

            # 2) synth attempt
            if not self.server.budget.can_afford("synth"):
                self.log.event("skip", phase="synth", reason="no_budget")
                return None
            self.hb.set_stage("synth", self.server.budget.remaining())
            r = self.server.synth(ckpt.code)
            self.log.event("tool_result", kind="synth", phase=r.phase, ok=r.ok,
                           elapsed_s=round(r.elapsed_s, 1),
                           credit_spent=self.server.budget.spent,
                           log=r.log if not r.ok else "")
            if r.ok and r.report is not None:
                lat = self._valid_latency(r.report)
                self._synth_summary = r.report.summary()
                if ckpt.should_accept(Level.SYNTH, lat):
                    ckpt.accept(ckpt.code, Level.SYNTH, lat,
                                cosim_ok=ckpt.cosim_ok)
                    self.log.event("checkpoint", old=Level.CORRECT,
                                   new=Level.SYNTH, latency=lat,
                                   reason="synth_ok")
                self.log.event("phase_exit", phase="synth", result="ok",
                               latency=lat)
                return lat
            fb = build_feedback(r)   # synth failed; next round repairs it

        self.log.event("phase_exit", phase="synth", result="failed",
                       rounds=self.max_synth_rounds, best_level=ckpt.level)
        return None

    @staticmethod
    def _valid_latency(report) -> int | None:
        """Extract a trustworthy latency from a synth report.

        Defends against the known parse anomaly where synth passes but the
        reported latency is 0 (dev-log 2026-07-17-01): a 0 would win every
        same-level comparison and corrupt the archive, so it is treated as
        missing data instead.

        Args:
            report: A harness SynthReport.

        Returns:
            latency_worst (falling back to latency_avg), or None when the
            value is missing or non-positive.
        """
        lat = report.latency_worst or report.latency_avg
        if lat is not None and lat <= 0:
            return None
        return lat

    # -- stage 3: optimize -------------------------------------------------
    def _optimize(self, plan: RunPlan, ckpt: Checkpoint) -> None:
        """Stage 3: PPA optimization loop (architecture §4.4, v2.4).

        AMD four-phase workflow per round: Phase 1 context (design document +
        cached design brief + latest synth report) -> Phase 2a strategy
        exploration with compatibility annotations -> Phase 2b selector
        review AI (dually-confirmed compatible subset) -> Phase 3 combined
        code generation with review gates -> csim/synth re-verification ->
        same-level latency arbitration (§2 rule 2). A failed multi-strategy
        candidate falls back to the subset's first strategy alone (combo
        attribution). Stops on single-strategy failure / no improvement /
        unaffordable tools / the round cap.

        Args:
            plan: The RunPlan (used for context; optimization applies to all).
            ckpt: The checkpoint holding the synth-correct code to improve.
        """
        self.log.event("phase_enter", phase="optimize",
                       best_level=ckpt.level, best_latency=ckpt.latency)
        # Snapshot for the §4.5 post-optimization cosim rollback.
        self._pre_opt_snapshot = Checkpoint(
            code=ckpt.code, level=ckpt.level, latency=ckpt.latency,
            cosim_ok=ckpt.cosim_ok)

        # AMD Phase 1: extract the design brief once and cache it (§4.4).
        if not self._design_brief:
            self.hb.set_stage("llm", self.server.budget.remaining())
            self._design_brief = self.llm.extract_design_brief(
                self.task, ckpt.code)
            self.log.event("llm_call", purpose="extract_brief",
                           chars=len(self._design_brief),
                           **self._llm_usage_fields())
            self.log.event("design_brief", chars=len(self._design_brief))

        for round_n in range(1, self.max_optimize_rounds + 1):
            if not (self.server.budget.can_afford("csim")
                    and self.server.budget.can_afford("synth")):
                self.log.event("budget_exhausted", where="optimize",
                               best_level=ckpt.level, best_latency=ckpt.latency)
                break

            # AMD Phase 2a: strategy exploration on the latest synth data.
            self.hb.set_stage("llm", self.server.budget.remaining())
            strategies = self.llm.propose_strategies(
                self.task, ckpt.code,
                self._synth_summary or "(no synthesis report available)",
                self._design_brief)
            self.log.event("llm_call", purpose="propose_strategies",
                           round=round_n, count=len(strategies),
                           raw_head=(self.llm.last_propose_raw[:800]
                                     if len(strategies) <= 1 else ""),
                           **self._llm_usage_fields())
            if not strategies:
                self.log.event("optimize_stop", reason="no_strategy")
                break

            # AMD Phase 2b: selector review AI picks a compatible subset
            # (dual confirmation: proposer + selector must both agree the
            # strategies do not interfere, §4.4; v2.7: feasibility review
            # first, poisoned plans rejected with reasons).
            self.hb.set_stage("llm", self.server.budget.remaining())
            indices, sel_reason, sel_rejected, sel_fallback = (
                self.llm.select_strategies(
                    self.task, ckpt.code, strategies,
                    self._synth_summary or "(no synthesis report available)",
                    self._design_brief))
            self.log.event("llm_call", purpose="select_strategies",
                           round=round_n, **self._llm_usage_fields())
            subset = [strategies[i] for i in indices]
            self.log.event("strategy_select", round=round_n, indices=indices,
                           picked=[s.name for s in subset],
                           all=[s.name for s in strategies],
                           reason=sel_reason,
                           rejected=sel_rejected,
                           fallback=sel_fallback)

            # AMD Phase 3: apply the subset as ONE candidate, then arbitrate.
            outcome, fail_fb = self._try_opt_candidate(ckpt, subset, round_n)
            if outcome == "improved":
                continue

            # Combo attribution fallback (§4.4): when a multi-strategy
            # candidate fails (or does not improve), we cannot tell which
            # strategy caused it — retry once with the subset's first
            # strategy alone, WITH the failure feedback so the LLM avoids
            # repeating the mistake (v2.7: was a blind retry).
            if len(subset) > 1:
                self.log.event("optimize_fallback", round=round_n,
                               picked=[subset[0].name],
                               reason="combo failed; retrying first "
                                      "strategy only (with failure feedback)")
                outcome, _ = self._try_opt_candidate(
                    ckpt, subset[:1], round_n, failure_feedback=fail_fb)
                if outcome == "improved":
                    continue

            self.log.event("optimize_stop", reason=outcome,
                           best_latency=ckpt.latency)
            break

        self.log.event("phase_exit", phase="optimize", result="ok",
                       best_level=ckpt.level, best_latency=ckpt.latency)

    def _try_opt_candidate(self, ckpt: Checkpoint,
                           strategies: list[Strategy], round_n: int,
                           failure_feedback: str = "") -> tuple[str, str]:
        """Generate, verify, and arbitrate one optimization candidate.

        The full per-candidate pipeline (§4.4): review-gated generation ->
        csim re-verify -> synth re-verify -> same-level latency arbitration
        (§2 rule 2). On acceptance the checkpoint and the cached synth
        summary are updated.

        Args:
            ckpt: The checkpoint holding the current best code.
            strategies: The selected Strategy subset to apply together.
            round_n: Current optimize round number (for logging).
            failure_feedback: Distilled feedback from a previous failed
                attempt, injected into generation so the LLM avoids
                repeating the mistake (empty for a first attempt).

        Returns:
            An ``(outcome, failure_feedback)`` tuple. ``outcome`` is
            "improved" (accepted as strictly faster), "no_improvement"
            (verified but not faster), or "failed" (generation/verification
            failed). ``failure_feedback`` is the distilled tool feedback of
            the failed attempt ("" when the candidate improved or none was
            produced) for the caller's failure-aware fallback.
        """
        cand = self._apply_with_review(ckpt.code, strategies,
                                       failure_feedback=failure_feedback)
        if cand is None or cand.strip() == ckpt.code.strip():
            self.log.event("optimize_discard", round=round_n,
                           reason="no_candidate")
            return "failed", ""

        # Re-verify already-passed stages before arbitrating (§5).
        if not self.server.budget.can_afford("csim"):
            self.log.event("budget_exhausted", where="optimize-csim",
                           best_latency=ckpt.latency)
            return "failed", ""
        self.hb.set_stage("csim", self.server.budget.remaining())
        cr = self.server.csim(cand)
        self.log.event("tool_result", kind="csim", phase=cr.phase,
                       ok=cr.ok, rc=cr.return_code,
                       elapsed_s=round(cr.elapsed_s, 1),
                       credit_spent=self.server.budget.spent,
                       log=cr.log if not cr.ok else "")
        if not cr.ok:
            self.log.event("optimize_discard", round=round_n,
                           reason="csim_broken", phase=cr.phase)
            return "failed", build_feedback(cr).as_prompt_block()
        if not self.server.budget.can_afford("synth"):
            self.log.event("budget_exhausted", where="optimize-synth",
                           best_latency=ckpt.latency)
            return "failed", ""
        self.hb.set_stage("synth", self.server.budget.remaining())
        sr = self.server.synth(cand)
        self.log.event("tool_result", kind="synth", phase=sr.phase,
                       ok=sr.ok, elapsed_s=round(sr.elapsed_s, 1),
                       credit_spent=self.server.budget.spent,
                       log=sr.log if not sr.ok else "")
        if not sr.ok or sr.report is None:
            self.log.event("optimize_discard", round=round_n,
                           reason="synth_failed", phase=sr.phase)
            return "failed", build_feedback(sr).as_prompt_block()

        # Same-level arbitration: accept only a strictly faster design.
        lat = self._valid_latency(sr.report)
        if ckpt.should_accept(Level.SYNTH, lat):
            old_lat = ckpt.latency
            # The new code has not been cosim-verified (§4.5 re-checks).
            ckpt.accept(cand, Level.SYNTH, lat, cosim_ok=None)
            self._synth_summary = sr.report.summary()
            self.log.event("checkpoint", old=Level.SYNTH, new=Level.SYNTH,
                           old_latency=old_lat, new_latency=lat,
                           reason="optimize_improve")
            return "improved", ""
        self.log.event("optimize_discard", round=round_n,
                       reason="no_improvement",
                       best_latency=ckpt.latency, cand_latency=lat)
        return "no_improvement", ""

    def _apply_with_review(self, code: str,
                           strategies: list[Strategy],
                           failure_feedback: str = "") -> str | None:
        """Generate an optimized candidate, then cross-check before returning.

        Mirrors ``_repair_with_review`` but the generator is
        ``llm.apply_strategies`` (AMD Phase 3, v2.4: a dually-confirmed
        compatible subset). Gate 1 is the deterministic mechanical review;
        gate 2 is the LLM review focused on multi-strategy pragma
        interaction hazards (AMD's named LLM weakness).

        Args:
            code: The current best kernel source.
            strategies: The Strategy subset selected this round.
            failure_feedback: Distilled feedback from a previous failed
                attempt, injected into generation (v2.7, empty by default).

        Returns:
            The reviewed candidate kernel source, or None if the LLM produced
            no parseable code.
        """
        names = "+".join(s.name for s in strategies)
        for retry in range(self.llm.max_review_retries + 1):
            self.hb.set_stage("llm", self.server.budget.remaining())
            new_code = self.llm.apply_strategies(
                self.task, code, strategies, self._design_brief,
                failure_feedback=failure_feedback)
            self.log.event("llm_call", purpose="apply_strategies",
                           strategies=names, retry=retry,
                           **self._llm_usage_fields())
            if new_code is None:
                return None

            # Gate 1: mechanical (hard) checks
            mech_ok, mech_issues = mechanical_review(code, new_code, self.task)
            self.log.event("mechanical_review", passed=mech_ok,
                           issues=mech_issues if not mech_ok else [])
            if not mech_ok:
                # Fold the issues into the first strategy for the retry.
                strategies = [Strategy(
                    name=strategies[0].name,
                    rationale=strategies[0].rationale
                    + "\nMUST FIX: " + "; ".join(mech_issues),
                    expected_gain=strategies[0].expected_gain,
                    risk=strategies[0].risk,
                    combinable_with=strategies[0].combinable_with,
                )] + strategies[1:]
                continue

            # Gate 2: LLM review (self-check)
            passed, issues = self.llm.review(
                self.task, new_code,
                focus="signature/interface unchanged; pragma interaction rules "
                      "(no PIPELINE+DATAFLOW at the same level, no dead "
                      "streams, no conflicting partitions); strategies "
                      "correctly combined: " + names,
            )
            self.log.event("review", verdict="pass" if passed else "reject",
                           retry=retry, issues=issues[:200])
            if passed:
                return new_code
        return new_code   # exhausted retries; return last attempt anyway

    def _post_opt_cosim_recheck(self, ckpt: Checkpoint) -> None:
        """Final RTL re-check after optimization, with real rollback (§4.5).

        Runs only when the best code actually changed during optimization
        (otherwise the verified correctness version still stands) and cosim
        is affordable. Since v2.7 this applies to ALL task types, not only
        structural ones: the synth report is a static estimate, not a
        measured value (e.g. the residual task estimated 68 vs measured 97
        cycles), so an optimized kernel deserves an RTL-level sanity check
        even when the rules do not require it. On cosim failure — or when
        cosim is unaffordable for a structural task — restores the
        pre-optimization snapshot in full (code/level/latency/cosim_ok).

        Args:
            ckpt: The checkpoint holding the optimized code to re-verify.
        """
        snap = self._pre_opt_snapshot
        if snap is None or ckpt.code.strip() == snap.code.strip():
            return   # best unchanged by optimization; nothing to re-verify
        if not self.server.budget.can_afford("cosim"):
            # Structural tasks must not ship RTL-unverified code; for other
            # tasks the check is best-effort, so just note the skip.
            if ckpt.cosim_ok is None and self.task_requires_cosim():
                self.log.event("rollback", reason="cosim_unaffordable",
                               note="restored pre-optimization verified version")
                self._restore_snapshot(ckpt, snap)
            else:
                self.log.event("cosim_recheck", result="skipped_no_budget")
            return
        self.hb.set_stage("cosim", self.server.budget.remaining())
        r = self.server.cosim(ckpt.code)
        self.log.event("tool_result", kind="cosim", phase=r.phase, ok=r.ok,
                       elapsed_s=round(r.elapsed_s, 1),
                       credit_spent=self.server.budget.spent,
                       log=r.log if not r.ok else "")
        if r.ok:
            ckpt.cosim_ok = True
            self.log.event("cosim_recheck", result="pass")
        else:
            self.log.event("rollback",
                           reason="optimization_reintroduced_hazard",
                           note="restored pre-optimization verified version")
            self._restore_snapshot(ckpt, snap)

    def task_requires_cosim(self) -> bool:
        """Return True when this task's correctness gate includes cosim.

        Returns:
            True for structural tasks (``requires_cosim`` set in task.toml).
        """
        return bool(getattr(self.task, "requires_cosim", False))

    @staticmethod
    def _restore_snapshot(ckpt: Checkpoint, snap: Checkpoint) -> None:
        """Restore a checkpoint in full from a snapshot (§4.5 rollback).

        Args:
            ckpt: The live checkpoint to overwrite.
            snap: The snapshot taken at optimize entry.
        """
        ckpt.code = snap.code
        ckpt.level = snap.level
        ckpt.latency = snap.latency
        ckpt.cosim_ok = snap.cosim_ok

    # -- LLM usage instrumentation (P4-03) ---------------------------------
    def _llm_usage_fields(self) -> dict:
        """Return per-call token-usage fields for an llm_call event.

        Reads the backend's last-call usage snapshot (DeepSeekClient exposes
        ``last_usage``/``model``; other backends yield an empty dict). Pure
        observability — never changes behavior (architecture §12.2).
        """
        backend = getattr(self.llm, "backend", None)
        u = getattr(backend, "last_usage", None) or {}
        fields: dict = {}
        if u:
            fields.update(prompt_tokens=u.get("prompt"),
                          completion_tokens=u.get("completion"),
                          reasoning_tokens=u.get("reasoning"))
        model = getattr(backend, "model", None)
        if model:
            fields["model"] = model
        return fields

    # -- knowledge base ---------------------------------------------------
    def _kb_lookup(self, fb) -> str:
        """Query the knowledge base for feedback signatures and return hits text.

        Args:
            fb: A Feedback object whose ``signatures`` drive the lookup.

        Returns:
            A joined summary string of matching KB hits, or "" when the KB is
            disabled or no hits were found.
        """
        if self.kb is None:
            return ""
        hits = self.kb.search(fb.signatures)
        self.log.event("kb_search", query=fb.signatures, hits=len(hits),
                       hit_ids=[h.id for h in hits])
        return "\n\n".join(h.summary() for h in hits) if hits else ""
