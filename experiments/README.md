> [中文](README.cn.md)

# experiments/ - Test Data Archive (Important! Do Not Delete)

This directory archives **all test data that carries a real cost** (real LLM API calls + real Vitis tool runs).
Tests are executed on the QFS-STATION server (Vitis 2025.2 + Alveo U55C target);
the raw artifacts live in the server's `runs/` (gitignored), while this directory holds a **curated archive copy**.

## Why a Separate Directory

- `runs/` is gitignored (large in size, ephemeral), so test data would be lost whenever the server is cleaned up.
- Tests carry a real cost (API token fees + server machine time), so **the data must not just be left on the server unattended**.
- Every number in the report (`report/report.tex`) must be traceable back to the raw records in this directory.

## Directory Structure

```
experiments/
├── README.md            This file (archiving spec)
├── EXPERIMENT-LOG.md    Experiment log (reverse chronological, one section per test)
├── <date>_<model>_<task>/   One directory per formal test
│   ├── summary.json     Key metrics summary (SCORE/credits/tokens/latency/PPA)
│   ├── transcript.txt   Run transcript (stdout)
│   ├── events.jsonl     Structured event log (agent observability)
│   ├── prompts.jsonl    Per-call LLM prompt+response (keep only representative samples when large)
│   └── ppa.json         PPA data extracted from the synth report (latency/resources/timing)
└── tables/              Summary tables (CSV), for direct citation in the report
```

## Archiving Process (Mandatory After Every Test)

1. Once a test finishes on the server, immediately `rsync` the key files from the corresponding run directory back into this directory.
2. Record in `EXPERIMENT-LOG.md`: date, model, task, configuration (token-mode, etc.), results (SCORE/credits/tokens), anomalies, and the location of the raw data.
3. Any number cited in the report must come from a file in this directory; never fill in figures from memory.

## Red Lines

- **API keys must never be committed**: `.env` is already gitignored; if an archived file contains a key it must be redacted.
- prompts.jsonl can be large (a single run may reach several MB); when it exceeds ~10MB, archive only a representative sample and note the selection rationale in the log.
