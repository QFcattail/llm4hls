#!/usr/bin/env python3
"""Extract full PPA data from Vitis HLS csynth.xml reports in a run directory.

For each run dir containing grade/grade_synth_{base,cand}/.../csynth.xml,
emit a JSON object with latency, interval, resources (LUT/FF/BRAM/DSP/URAM),
and timing (estimated clock period, target, uncertainty, timing-met flag,
effective Fmax) for both baseline and candidate.

Usage:
    python3 tools/extract_ppa.py <run_dir> [<run_dir>...]

Output: one JSON object per run dir on stdout (JSONL), and a copy written to
<run_dir>/ppa.json.

Timing-met criterion (Vitis convention): estimated + uncertainty <= target.
Effective Fmax (conservative) = 1000 / (estimated + uncertainty) MHz.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RES_KEYS = ["LUT", "FF", "BRAM_18K", "DSP", "URAM"]


def _find_csynth_xml(run_dir: Path, grade_sub: str) -> Path | None:
    """Locate the csynth.xml under grade/<grade_sub>/**/syn/report/."""
    base = run_dir / "grade" / grade_sub
    if not base.is_dir():
        return None
    hits = sorted(base.glob("**/syn/report/csynth.xml"))
    return hits[0] if hits else None


def _text(root: ET.Element, path: str) -> str | None:
    el = root.find(path)
    return el.text.strip() if el is not None and el.text else None


def parse_csynth(xml_path: Path) -> dict:
    """Parse one csynth.xml into a flat PPA dict."""
    root = ET.parse(xml_path).getroot()
    target = float(_text(root, "UserAssignments/TargetClockPeriod") or "nan")
    unc = float(_text(root, "UserAssignments/ClockUncertainty") or "0")
    est = _text(root, "PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod")
    est = float(est) if est else None
    lat = "PerformanceEstimates/SummaryOfOverallLatency"
    res = "AreaEstimates/Resources"
    avail = "AreaEstimates/AvailableResources"
    timing_met = (est + unc <= target) if est is not None else None
    fmax = (1000.0 / (est + unc)) if est is not None and (est + unc) > 0 else None
    return {
        "part": _text(root, "UserAssignments/Part"),
        "top": _text(root, "UserAssignments/TopModelName"),
        "target_clock_ns": target,
        "clock_uncertainty_ns": unc,
        "estimated_clock_ns": est,
        "timing_met": timing_met,
        "fmax_conservative_mhz": round(fmax, 1) if fmax else None,
        "latency_min": _text(root, f"{lat}/Best-caseLatency"),
        "latency_avg": _text(root, f"{lat}/Average-caseLatency"),
        "latency_max": _text(root, f"{lat}/Worst-caseLatency"),
        "interval_min": _text(root, f"{lat}/Interval-min"),
        "interval_max": _text(root, f"{lat}/Interval-max"),
        "resources": {k: int(_text(root, f"{res}/{k}") or 0) for k in RES_KEYS},
        "available": {k: int(_text(root, f"{avail}/{k}") or 0) for k in RES_KEYS},
    }


def extract_run(run_dir: Path) -> dict:
    """Extract PPA for baseline and candidate of one run dir."""
    out: dict = {"run_dir": str(run_dir)}
    for sub, key in (("grade_synth_base", "baseline"),
                     ("grade_synth_cand", "candidate")):
        xml = _find_csynth_xml(run_dir, sub)
        out[key] = parse_csynth(xml) if xml else None
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    for arg in sys.argv[1:]:
        run_dir = Path(arg)
        rec = extract_run(run_dir)
        (run_dir / "ppa.json").write_text(json.dumps(rec, indent=2))
        print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
