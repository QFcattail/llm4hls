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
    ]
