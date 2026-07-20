"""Seed knowledge-base entries (first iteration, architecture §6.2 P2 scope).

These seed the retriever so the error-signature retrieval path is exercised
end to end. Sources are strictly traceable — no invented error-code meanings:

  * AMD LLM4HLS SHA-256 case study (dev-log 2026-07-11-03): error codes
    [XFORM 203-313] / [RTGEN 206-102] observed during a function-merge
    refactor (dataflow conflict / illegal connection), and the named LLM
    weaknesses (pragma interaction rules, dead streams after merging).
  * The harness task descriptions (contest/fpt26-harness/tasks/*/task.toml),
    e.g. the residual_stream_deadlock burst-write pattern.
  * Generic csim failure classes distilled from the P2 projection run.

P2-12 (HLS domain owner) extends this to >=10 entries; the format may then
move to entries/*.yaml per architecture §9. Keep signatures lowercase
keywords/codes — the retriever does case-insensitive substring matching.

2026-07-20 expansion (P2-12 / P2-13 / P3-08): 7 -> 22 entries.
  * P2-12 additions source real machine logs: residual run [HLS 207-6969]
    (pragma at file scope, dev-log 2026-07-19-03), DATA_PACK-on-type misuse
    caught by the review gate (dev-log 2026-07-19-01), and the new
    vecadd/fir/matmul task classes.
  * P3-08 adds the cosim protocol class: FIFO depth, TLAST/TREADY/TVALID
    handshake, ap_ctrl, and synth-vs-cosim latency mismatch.
  * P2-13 distills repair patterns from HLS Repair (arXiv 2407.03889),
    RTLFixer (arXiv 2311.16543) and AutoChip (arXiv 2311.04887).
"""
from __future__ import annotations

from .retriever import KBEntry


def seed_entries() -> list[KBEntry]:
    """Return the seed KBEntry list (synth-heavy, plus cosim and csim classes).

    Returns:
        A fresh list of KBEntry objects; callers may extend it freely.
    """
    return [
        # -- synth class ----------------------------------------------------
        KBEntry(
            id="synth-xform-dataflow-conflict",
            symptom=("synth_error with [XFORM 203-313] / [RTGEN 206-102] after "
                     "merging functions or restructuring DATAFLOW regions"),
            root_cause=("AMD SHA-256 case study: after a function merge, a stream "
                        "is left with no consumer (dead code) or a DATAFLOW stage "
                        "is illegally connected, so synthesis rejects the region."),
            fix=("Audit every hls::stream in the DATAFLOW region: exactly one "
                 "producer and one consumer each; delete streams nobody reads; "
                 "do not place PIPELINE and DATAFLOW at the same level."),
            signatures=["[XFORM 203-313]", "[RTGEN 206-102]", "dataflow",
                        "illegal connection", "dead stream"],
        ),
        KBEntry(
            id="synth-ii-scheduling-fail",
            symptom=("synth reports an II violation or 'cannot be scheduled' "
                     "for a loop"),
            root_cause=("Loop-carried dependence (e.g. sequential accumulation "
                        "into one variable) or too few memory ports for the "
                        "requested initiation interval."),
            fix=("For accumulation: unroll partially and reduce pairwise, or "
                 "accept II>1. For port limits: add ARRAY_PARTITION (complete "
                 "for small arrays, cyclic with a factor for larger ones)."),
            signatures=["ii violation", "cannot be scheduled", "scheduling",
                        "ii="],
        ),
        KBEntry(
            id="synth-array-port-conflict",
            symptom=("synth fails or serializes accesses on an array: port / "
                     "memory conflict"),
            root_cause=("A loop reads/writes more array elements per iteration "
                        "than the default dual-port BRAM provides."),
            fix=("Partition the array: #pragma HLS ARRAY_PARTITION "
                 "variable=<a> complete (small, unrolled loops) or cyclic "
                 "factor=<unroll factor> (larger arrays)."),
            signatures=["array port", "memory conflict", "ported",
                        "array_partition"],
        ),
        KBEntry(
            id="synth-pragma-same-level-conflict",
            symptom=("synth error or warning about conflicting pragmas "
                     "PIPELINE and DATAFLOW"),
            root_cause=("AMD-named LLM weakness: PIPELINE and DATAFLOW applied "
                        "at the same hierarchy level, which Vitis rejects."),
            fix=("Put PIPELINE on the innermost loop body; put DATAFLOW only "
                 "on a function/region whose body is a sequence of "
                 "producer-consumer stages. Never both at one level."),
            signatures=["pipeline", "dataflow", "pragma", "conflict"],
        ),
        # -- cosim class ----------------------------------------------------
        KBEntry(
            id="cosim-deadlock-fifo-burst",
            symptom=("cosim hangs/deadlocks while csim passes (deadlock, FIFO, "
                     "TVALID/TREADY stall in the log)"),
            root_cause=("A DATAFLOW stage writes its entire main stream before "
                        "any of its skip/secondary stream. C-sim FIFOs are "
                        "unbounded and hide this; RTL FIFOs (default depth 2) "
                        "cannot buffer the burst, so the pipeline deadlocks "
                        "(residual_stream_deadlock pattern)."),
            fix=("Rate-balance producers and consumers: interleave writes to "
                 "the streams in the same loop, or raise the FIFO depth with "
                 "#pragma HLS STREAM depth=<n> sized to the burst."),
            signatures=["deadlock", "deadlocked", "fifo", "stream", "tvalid",
                        "tready", "hung", "stall"],
        ),
        # -- csim class -----------------------------------------------------
        KBEntry(
            id="csim-test-case-failed",
            symptom=("csim runtime_fail: 'Test Case N Failed' with a compiled "
                     "binary"),
            root_cause=("Functional bug: a branch drops or miscomputes a term "
                        "vs the interface contract (e.g. the projection "
                        "angle==0 branch averaging two vertices instead of "
                        "three)."),
            fix=("Diff the kernel against task.description's input/output "
                 "contract; check every conditional branch for dropped terms "
                 "and off-by-one loop bounds before re-running csim."),
            signatures=["test case", "failed", "runtime_fail"],
        ),
        KBEntry(
            id="csim-compile-error",
            symptom="csim compile_error with gcc-style 'file:line: error:' lines",
            root_cause=("Syntax error, undeclared identifier, missing include, "
                        "or a signature drift from the fixed header."),
            fix=("Fix the first reported error line first (later ones are "
                 "often cascades); confirm the top-level signature matches "
                 "the read-only header exactly and all includes are present."),
            signatures=["compile_error", "error:", "undeclared", "expected"],
        ),
        # -- P2-12 additions (real machine logs + new task classes) ----------
        KBEntry(
            id="synth-pragma-file-scope",
            symptom=("synth_error [HLS 207-6969]: '#pragma HLS' is only allowed "
                     "inside a function/loop body"),
            root_cause=("Real residual run (dev-log 2026-07-19-03): an LLM "
                        "placed a pragma at file scope (outside any function) "
                        "while merging a strategy combo."),
            fix=("Move every #pragma HLS inside the function body, directly "
                 "above the loop or variable it targets; pragmas at namespace "
                 "or file scope are rejected by Vitis."),
            signatures=["[hls 207-6969]", "only allowed", "file scope",
                        "pragma"],
        ),
        KBEntry(
            id="synth-datapack-interface-misuse",
            symptom=("reviewer/synth rejects DATA_PACK applied to a type name, "
                     "or the top-level interface changes after a DATA_PACK "
                     "strategy"),
            root_cause=("Real residual run (dev-log 2026-07-19-01): DATA_PACK "
                        "was placed on a struct type instead of a specific "
                        "interface argument, silently changing the kernel's "
                        "port contract — the AMD-named LLM pragma weakness."),
            fix=("DATA_PACK goes on a function argument (variable=), never on "
                 "a type definition; after any interface pragma, re-check the "
                 "top-level signature against the read-only header."),
            signatures=["data_pack", "data pack", "struct", "interface"],
        ),
        KBEntry(
            id="csim-numeric-reorder-tolerance",
            symptom=("csim runtime_fail where results are close but outside "
                     "tolerance (e.g. 1e-3), often after an optimization "
                     "round"),
            root_cause=("Float accumulation was reordered (adder tree, partial "
                        "unroll with pairwise reduction), changing rounding "
                        "vs the sequential float reference."),
            fix=("Check the testbench tolerance before 'fixing': if the error "
                 "is marginal, keep the accumulation order closer to the "
                 "reference (e.g. per-tile sequential sums); never change the "
                 "public testbench to pass."),
            signatures=["tolerance", "1e-3", "1e-2", "abs err", "expected"],
        ),
        KBEntry(
            id="csim-boundary-condition",
            symptom=("csim runtime_fail with first outputs wrong and later "
                     "ones correct (warm-up region), or off-by-one on loop "
                     "bounds"),
            root_cause=("Boundary handling mismatch vs the contract: e.g. FIR "
                        "zero-history for i < tap, guard conditions (i >= j) "
                        "dropped during optimization."),
            fix=("Re-read the description's boundary semantics; verify the "
                 "first TAPS/N outputs separately; ensure index guards survive "
                 "loop restructuring."),
            signatures=["boundary", "off-by-one", "index", "bounds",
                        "test case"],
        ),
        # -- P3-08 additions: cosim protocol class ---------------------------
        KBEntry(
            id="cosim-fifo-depth-too-shallow",
            symptom=("cosim deadlocks or stalls after a few elements while "
                     "csim passes; FIFO full/empty in the waveform log"),
            root_cause=("Default RTL stream FIFO depth is 2; any producer "
                        "burst larger than 2 elements ahead of its consumer "
                        "blocks (C-sim FIFOs are unbounded and hide this)."),
            fix=("#pragma HLS STREAM depth=<n> variable=<s> sized to the "
                 "maximum burst skew between producer and consumer; or "
                 "restructure so writes are rate-balanced."),
            signatures=["fifo", "depth", "stream", "full", "empty"],
        ),
        KBEntry(
            id="cosim-tlast-missing",
            symptom=("cosim hangs with the consumer waiting for end-of-packet "
                     "on an AXI-Stream interface"),
            root_cause=("TLAST is never asserted (or asserted on the wrong "
                        "beat), so the downstream IP keeps waiting for the "
                        "packet terminator."),
            fix=("Drive TLAST on the final element of each logical packet "
                 "(e.g. tlast = (i == N-1)); verify it in the csim-visible "
                 "side data before spending a cosim run."),
            signatures=["tlast", "packet", "axis", "end of packet"],
        ),
        KBEntry(
            id="cosim-tvalid-tready-handshake",
            symptom=("cosim data mismatch or stall on an AXI-Stream interface "
                     "even though no deadlock is reported"),
            root_cause=("Handshake violation: payload changed while TVALID "
                        "was high and TREADY low, or the producer dropped "
                        "TVALID early; csim's idealized streams do not model "
                        "this."),
            fix=("Once TVALID is raised, hold both TVALID and the payload "
                 "stable until TREADY; only advance data on a TVALID&&TREADY "
                 "beat."),
            signatures=["tvalid", "tready", "handshake", "axis", "stall"],
        ),
        KBEntry(
            id="cosim-apctrl-hang",
            symptom=("cosim hangs immediately at start; the kernel never "
                     "begins or never reports done"),
            root_cause=("ap_ctrl protocol issue: ap_start never raised by the "
                        "testbench wrapper, or the kernel never reaches its "
                        "return so ap_done/ap_idle stay low (e.g. an inner "
                        "loop with a data-dependent exit that never fires)."),
            fix=("Check loop exit conditions are reachable with the real "
                 "testbench data; avoid while-loops waiting on stream states "
                 "that require a different stage to run first."),
            signatures=["ap_ctrl", "ap_start", "ap_done", "ap_idle", "hang"],
        ),
        KBEntry(
            id="cosim-latency-vs-synth-mismatch",
            symptom=("cosim passes but measured RTL latency is much higher "
                     "than the csynth estimate"),
            root_cause=("Stall cycles invisible to synthesis: FIFO back-"
                        "pressure, II violations at runtime, or memory "
                        "contention; e.g. residual run measured 68 cyc in "
                        "cosim vs a lower synth estimate (dev-log 2026-07-20-01)."),
            fix=("Trust cosim latency over the synth estimate; look for "
                 "back-pressure points (deepen FIFOs, rebalance stages) "
                 "rather than adding more pragmas."),
            signatures=["latency", "cosim", "mismatch", "estimate", "stall"],
        ),
        # -- P2-13 additions: repair patterns from papers --------------------
        KBEntry(
            id="pattern-retrieve-before-repair",
            symptom=("meta-pattern: an LLM repair attempt invents a fix that "
                     "does not match the actual error (HLS Repair, arXiv "
                     "2407.03889)"),
            root_cause=("Without retrieval grounding, LLMs hallucinate fixes; "
                        "HLS Repair shows RAG-guided repair beats direct LLM "
                        "repair on pass rate across 24 real applications."),
            fix=("Always pair the concrete error signature with a KB entry "
                 "before rewriting code; repair the diagnosed cause, not a "
                 "plausible-looking one."),
            signatures=["hallucination", "rag", "retrieval", "repair"],
        ),
        KBEntry(
            id="pattern-correctness-before-optimization",
            symptom=("meta-pattern: a fix mixes functional repair and "
                     "performance pragmas in one edit and breaks both"),
            root_cause=("HLS Repair separates repair stages: HLS-C "
                        "correctness first, bit-width/pragma optimization as "
                        "a later, separate program — coupling them makes "
                        "failures unattributable."),
            fix=("One concern per iteration: get csim green with minimal "
                 "edits; only then add pragmas, re-verifying csim after each "
                 "optimization."),
            signatures=["stage", "separation", "correctness", "optimization"],
        ),
        KBEntry(
            id="pattern-syntax-first",
            symptom=("meta-pattern: many errors at once, mostly syntax-class "
                     "(RTLFixer, arXiv 2311.16543: ~55% of LLM codegen errors "
                     "are syntax-related)"),
            root_cause=("Cascaded diagnostics: one syntax error produces "
                        "pages of downstream errors; fixing later lines first "
                        "wastes iterations."),
            fix=("Fix the FIRST reported error line, then re-run: RTLFixer "
                 "corrected ~98.5% of compilation errors with retrieval + "
                 "ReAct iteration on first-errors."),
            signatures=["syntax", "cascade", "first error", "compile"],
        ),
        KBEntry(
            id="pattern-error-message-pairing",
            symptom=("meta-pattern: repair prompt lacks the exact tool "
                     "message, so the model guesses (RTLFixer ReAct design)"),
            root_cause=("ReAct loop: observe the exact tool output, reason "
                        "over it, act with a targeted patch; dropping the "
                        "verbatim message degrades to blind editing."),
            fix=("Quote the exact error code + log tail in the repair "
                 "context, state the hypothesis, then patch minimally."),
            signatures=["react", "observe", "tool feedback", "patch"],
        ),
        KBEntry(
            id="pattern-mismatch-diff-feedback",
            symptom=("meta-pattern: functional repair stalls without knowing "
                     "WHAT differs (AutoChip, arXiv 2311.04887)"),
            root_cause=("AutoChip feeds expected-vs-actual output mismatches "
                        "back into the loop; tool context yielded 24.2% more "
                        "functionally correct results."),
            fix=("When a testbench reports a mismatch, carry the expected vs "
                 "actual values (and index) into the repair prompt instead of "
                 "just 'test failed'."),
            signatures=["mismatch", "expected", "actual", "diff"],
        ),
        KBEntry(
            id="pattern-bounded-feedback-loop",
            symptom=("meta-pattern: repair loops that never converge burn the "
                     "whole budget (AutoChip interactive loop)"),
            root_cause=("Iterative tool-feedback repair works but must be "
                        "bounded; unbounded loops cost more than they fix."),
            fix=("Cap repair rounds (this agent: 6 correctness / 3 synth / "
                 "4 optimize), keep the best checkpoint, and submit the best "
                 "known-good version on exhaustion."),
            signatures=["iteration", "budget", "loop", "converge"],
        ),
    ]
