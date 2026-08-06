> [中文](EXPERIMENT-LOG.cn.md)

# Experiment Log (EXPERIMENT-LOG)

Recorded in reverse chronological order. One section per formal test.

---

## 2026-07-25 Multi-Model Comparison Test (FPT'26 Rule 6 Compliance)

**Goal**: Competition rule 6 requires evaluating and reporting results with three recommended models. Previously only DeepSeek V4 Pro had been completed (see report Table VI); this round adds `qwen3.5-122b-a10b` (AWQ-4bit) and `qwen3.6-27b` (FP8) from Alibaba Cloud MaaS.

**Environment**:
- Server: QFS-STATION (8 cores / 32GB), Vitis 2025.2, target U55C @ 200MHz
- Endpoint: Alibaba Cloud MaaS OpenAI-compatible mode (cn-beijing)
- Integration: `agent/deepseek_client.py` via environment variable overrides (`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`/`LLM_THINKING=enable_thinking`)
- Endpoint probing conclusions (2026-07-25):
  - Both models are reasoning models that output reasoning_content by default;
  - `enable_thinking:false` is supported (can disable reasoning, used for the cheap judgment calls in token-mode);
  - usage contains `completion_tokens_details.reasoning_tokens`; token accounting is compatible.

**Configuration**: token-mode=full (consistent with the DeepSeek main experiment, to ensure comparability).

### Smoke Test: projection_bugfix × qwen3.6-27b (2026-07-25 21:37)

- Archive directory: `experiments/2026-07-25_qwen3.6-27b_projection_bugfix/`
- Result: **SCORE 1.400** (full marks 1.400), credits 5/20, tokens 13,896
- Compared with DeepSeek V4 Pro on the same task: SCORE 1.400 / credits 5 / tokens 3,629 -> same score, qwen3.6-27b uses ~3.8× the tokens (smaller model, longer reasoning)
- Timing: estimated clock 2.538 ns (target 5.0, uncertainty 1.35) -> met; conservative Fmax 257 MHz >= 100 MHz (rule 4 satisfied)
- Pitfall notes:
  1. `set -u` conflicts with Vitis settings64.sh (PYTHONPATH unbound) -> runner switched to `set -o pipefail`
  2. Passing a relative path to `--work` gets mangled by the harness (after cd into the build directory the path doubles, csim.exe No such file) -> runner switched to absolute paths `$PWD/runs/...`
  3. The first smoke run wasted ~3 credits + ~13k tokens due to bug #2; it was aborted and rerun, and the invalidated data was not archived

### Formal Matrix Results (2026-07-25 21:40 ~ early morning 2026-07-26)

token-mode=full, one run per (model, task). The two qwen matrices ran in parallel + DeepSeek vecadd rerun.

| Task | qwen3.6-27b (score/cr/tok) | qwen3.5-122b (score/cr/tok) |
|---|---|---|
| projection | 1.400 / 5 / 13,896 | 1.400 / 5 / 15,077 |
| vecadd | 0.738 / 20 / 37,699 | 0.500 / 20 / 59,725 |
| dotProduct | 2.325 / 10 / 38,458 | **3.000** / 15 / 72,763 |
| fir | 1.476 / 25 / 64,349 | **2.000** / 30 / 152,157 |
| matmul | **3.000** / 30 / 54,526 | 2.156 / 10 / 67,484 (rerun) |
| residual | 3.396 / 60 / 68,365 | 3.098 / 30 / 41,959 |
| **Total** | 12.335 / - / 277,293 | 12.154 / - / 409,165 |

DeepSeek control total: 14.091 / - / 373,451.
All three models passed the csim correctness gate 18/18; synth: DS 6/6, qwen3.6 6/6, qwen3.5 5/6. All 17 synthesizable candidates met timing (conservative Fmax 200-353 MHz).
All runs (including crash scenes) have been archived in this directory (qwen3.6-27b/, qwen3.5-122b-a10b/, deepseek-v4-pro/, deepseek-v4-pro-main/); each task directory contains transcript, event jsonl, prompts jsonl, scores, final kernel, grade/csynth.xml, ppa.json.
Report figures have all been backfilled (Table IV/V/VI/VIII/IX, compiled successfully 2026-07-26 01:15).

DeepSeek vecadd rerun (PPA data cleanup): 1.000 / 20 / 51,519, lat 262 (archived at `deepseek-v4-pro/vecadd_optimize/`).

**Key Events and Findings**:
1. **qwen3.5 vecadd only 0.5**: csim fully passed but all 4 synth runs timed out (>600s), exhausting 20 credits. The final kernel used VEC_UNROLL=8 loop partitioning; the design was legal but synth timed out. DeepSeek/qwen3.6 synth ran normally over the same period -> not a machine contention issue, but a candidate design scale issue + the agent failing to fall back to a more conservative design after the timeout. Worth a case-study analysis in the report.
2. **qwen3.6 vecadd 0.738**: correctness + synth all passed but optimization was completely ineffective (lat 4102 = baseline); the smaller model is weak at optimization.
3. **qwen3.6 matmul full marks 3.000** (lat 78, 210x): DeepSeek on the same task only reached 2.691. Optimization ability is non-monotonic with model size and is task-dependent.
4. **qwen3.5 matmul first run crashed** (00:37): LLM API read timeout (urllib read timeout, default 300s), and the agent has no HTTP-layer retry logic -> the whole run was scrapped with no scores.jsonl. This is an agent robustness defect (worth a report limitation), not an intellectual failure. Reran with LLM_TIMEOUT=600 (directory matmul_optimize_r2); the crash scene was preserved in the archive. **Rerun result 2.156**: qwen3.5's reviewer twice rejected the unmodified correct baseline at the pre_csim_review stage (with suspicious reasons like "pragma placement", "interface error"), and applied a "fix" that made matmul 2x slower (lat 32827 vs baseline 16422). The archive anchored on the contaminated code -> exposing the real design defect that "the reviewer can corrupt a good baseline before anchoring" (report §VI-C failure-mode analysis + limitation #2; fix direction: archive should anchor on the original baseline first).
5. qwen3.5 122B generates slowly: fir used 152k tokens / 30 credits; a single task took ~50 min at most.
6. Concurrency notes: at most 3 Vitis jobs ran in parallel (8-core server); synth slowed down but caused no misjudgment (DeepSeek passed over the same period). The qwen3.5 vecadd synth timeout can be rerun alone later for hard evidence if needed (low cost, ~60k tokens).

**Wrap-up**: all complete. Report v2 rewritten (report/report.tex + report.bib), adding: multi-model main table (rule 6), full PPA table (rule 4 timing evidence + resource utilization), rule-compliance self-check table (Appendix A), Related Work + 13 references, failure-mode analysis, and PPA weight discussion (proof of optimality of the latency-first scoring). TUI/version history moved out of the main text.
