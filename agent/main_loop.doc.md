# agent/main_loop.py 说明文档

## 中文说明

### 用途
实现 agent-architecture.md §4 的主循环：线性顺序（correctness -> synth -> optimize）但带回溯——每次编辑后重新验证已通过的阶段，因为修后段 bug 可能破坏前段（见 §5）。检查点（§2）天然提供回滚。v2.3 起三阶段全部落地：correctness 修复循环、synth 修复循环（§4.3）、optimize PPA 优化循环（§4.4）、structural 优化后 cosim 回验真回滚（§4.5）。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Agent` | class | 核心 agent，替换 llm4hls.ReferenceAgent，驱动 correctness->synth->optimize 流 |
| `Agent.__init__(task, server, llm, kb=None, max_rounds=6, max_synth_rounds=3, max_optimize_rounds=4, run_dir="runs", token_mode="full")` | method | 构造，持有 task/server/llm/kb，创建 Logger 与 Heartbeat；初始化跨阶段状态（`_synth_summary`/`_design_brief`/`_pre_opt_snapshot`）；v0.7.0 起 `token_mode` 透传给 llm 客户端（full 默认=旧行为） |
| `Agent.run() -> str` | method | 入口：route 任务后执行三阶段，捕获 BudgetExceeded 返回最佳 checkpoint 代码，最终发 submit 事件 |
| `Agent._run_plan(plan, ckpt) -> str` | method | 顺序执行三阶段，任一阶段失败时提前返回最佳正确代码；optimize 后仅当 `"cosim" in correctness_stages` 才回验 |
| `Agent._reach_correctness(plan, ckpt) -> bool` | method | 最多 max_rounds 轮修复循环：csim(+cosim)，首轮 pre-csim review，失败时蒸馏反馈+查 KB+review-gated 修复 |
| `Agent._repair_with_review(code, feedback_text, kb_text) -> str\|None` | method | 两道闸门：mechanical checks（硬）与 LLM review（语义），失败时把 mechanical 问题回灌反馈再重试 |
| `Agent._do_synth(plan, ckpt) -> int\|None` | method | synth 修复循环（§4.3）：失败时反馈蒸馏+KB 检索+修复，**先重验 csim 再花 synth**；修 csim 崩了则带 csim 反馈续修；成功记录 `_synth_summary` |
| `Agent._valid_latency(report) -> int\|None` | static method | latency 无效值防御：None 或 <=0 视为缺失（防 latency=0 解析异常污染存档） |
| `Agent._optimize(plan, ckpt)` | method | optimize 循环（§4.4，v2.4）：入口存档快照 → Phase 1 设计摘要缓存 → Phase 2a 提策略（含兼容性标注）→ **Phase 2b 评审 AI 选兼容子集（双重确认）** → Phase 3 合并生成+双闸门 → 重验 csim+synth → 同级 latency 择优；组合失败回退首策略一次（归因），单策略失败/无改进/预算尽/轮数尽则停 |
| `Agent._try_opt_candidate(ckpt, strategies, round_n) -> str` | method | 单候选完整流水线：review 闸门生成 → csim 重验 → synth 重验 → 同级择优；返回 "improved"/"no_improvement"/"failed"（接受时更新存档与 synth_summary） |
| `Agent._apply_with_review(code, strategies) -> str\|None` | method | Phase 3 生成的双闸门变体：生成器为 apply_strategies（组合子集），mechanical 失败时把问题折进首个 strategy 重试 |
| `Agent._post_opt_cosim_recheck(ckpt)` | method | §4.5：仅当 best 在优化中变过才回验 cosim；失败或 cosim 不可负担时**真回滚**到优化前快照 |
| `Agent._restore_snapshot(ckpt, snap)` | static method | 快照整体恢复（code/level/latency/cosim_ok） |
| `Agent._kb_lookup(fb) -> str` | method | 用 fb.signatures 查知识库，返回命中摘要文本（KB 关闭或无命中返回空串）；v0.7.0 起 kb_search 事件带 `hit_ids`（命中条目 id 列表，P3-10 验证前提） |
| `Agent._llm_usage_fields() -> dict` | method | v0.7.0 新增（P4-03）：读 backend 的 `last_usage`/`model`，给 llm_call 事件附 prompt_tokens/completion_tokens/reasoning_tokens/model 字段（纯观测，不改变行为；无该属性的后端返回空 dict） |

### 导出
无 `__all__`；主要导出 `Agent` 类。

### 依赖
- 内部依赖：`.checkpoint`(Checkpoint, Level)、`.feedback`(build_feedback)、`.llm_client`(HLSLLMClient, Strategy)、`.mechanical_checks`(mechanical_review)、`.observability`(Heartbeat, Logger)、`.router`(RunPlan, route)
- 外部依赖：`llm4hls.budget.BudgetExceeded`（harness，导入时即加载）；运行期使用 harness 的 `Task` / `ToolServer`

### 关键设计点
- 线性带回溯：correctness 阶段首轮 pre-csim review 可在花 csim 信用前抓 bug；每次编辑候选不提升 level，仅下次输入。v0.7.0 起 pre-csim review 的重复 description 摘要仅 full 模式保留（repair 本身已注完整 description，graded 模式砍掉省 token）。
- token-mode（v0.7.0，P4-03）：`route` 事件记录 token_mode 便于 A/B 追溯；llm_call 事件（extract_brief/propose/select/apply）统一附 per-call token 字段。
- 双闸门修复：mechanical（确定性，捕获签名/头文件变更）在前，LLM review 在后；mechanical 失败时问题回灌反馈再修（最多 max_review_retries 次额外重试）。
- synth 修复循环（§4.3）：每轮修复后先重验 csim（1 credit）再 synth（4 credits），csim 崩了的候选不浪费 synth；`max_synth_rounds=3`。
- optimize 循环（§4.4）：AMD Phase 1 三件套（官方设计文档 description+headers、extract_design_brief 设计摘要缓存、synth 报告）注入每次策略探索；v2.4 策略组合——propose 标兼容性、select 评审 AI 双重确认选子集、apply 合并应用；组合失败回退子集首策略一次（归因），仍失败才停；`max_optimize_rounds=4`（每轮最坏 2×5=10 credits）。
- 环境错误检测：csim 失败且 elapsed_s<0.5 且日志为空时判定 vitis-run 缺失，抛 RuntimeError 给出修复指引。
- latency=0 防御：`_valid_latency` 把 <=0 当缺失，防止"0 周期"在同级的 latency 比较中永远获胜、污染存档（dev-log 2026-07-17-01 记录的解析异常）。
- 真回滚（§4.5）：optimize 入口快照 Checkpoint 全字段；cosim 回验失败或不可负担时整体恢复，不只记日志。
- v2.9（v0.8.0）credit 驱动的 optimize 停止策略 + cosim 修复优先回滚：`_optimize_can_continue` 以"还能否负担 1 csim+1 synth"为主停止条件（cosim 任务额外预留 `_COSIM_RECHECK_RESERVE`=26 credits 给 §4.5 回验），`max_optimize_rounds=20` 仅作安全帽；优化后 cosim 失败先走 `_repair_optimized_cosim`（反馈+KB+双闸门修复，先重验 csim 再重验 cosim，最多 max_opt_repair 次），修复耗尽才回滚快照（`cosim_repair_exhausted`）。
- v0.8.1 基线锚定：种子已假定正确（optimize 任务，initial_level=CORRECT）时**跳过**首轮盲审——archive 与 live code 是同一对象，盲审改写 ckpt.code 会在任何工具确认前销毁已知正确基线（2026-07-25 qwen3.5-122b matmul 事故：latency 16422→32827 翻倍）。改为原样先跑 csim 验证（`pre_csim_review` 事件带 `skipped="seed_assumed_correct"`），只有真实 csim 失败才进修复循环。TC-AGENT-020 钉死此行为。
- v0.8.1 synth 超时退避：`phase == "timeout"` 不是普通代码错误（设计爆炸或工具机过载）。`_do_synth` 中第二次连续超时即提前停 stage（`synth_timeout_backoff` 事件，保留正确版本），不再烧剩余轮数（2026-07-25 qwen3.5-122b vecadd 事故：4 连续超时 ≈19 credits 只得正确性分）；`_try_opt_candidate` 同样在两次连续 synth 超时后直接弃候选而非再修。TC-AGENT-021 钉死此行为。
- 架构章节引用：§4 主循环、§4.3 synth、§4.4 optimize、§4.5 回验、§5 回溯、§2 checkpoint。

---

## English

### Purpose
Implements the agent-architecture.md §4 main loop: linear order (correctness -> synth -> optimize) with backtracking — every edit re-verifies already-passed stages because fixing a later bug can break an earlier one (see §5). The checkpoint (§2) gives rollback for free. Since v2.3 all three stages are live: the correctness repair loop, the synth repair loop (§4.3), the optimize PPA loop (§4.4), and the structural post-optimization cosim re-check with real snapshot rollback (§4.5).

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Agent` | class | Core agent replacing llm4hls.ReferenceAgent; drives correctness->synth->optimize |
| `Agent.__init__(task, server, llm, kb=None, max_rounds=6, max_synth_rounds=3, max_optimize_rounds=4, run_dir="runs", token_mode="full")` | method | Construction; holds task/server/llm/kb, creates Logger and Heartbeat, initializes cross-stage state (`_synth_summary` / `_design_brief` / `_pre_opt_snapshot`); since v0.7.0 `token_mode` is forwarded to the llm client (default "full" = legacy behavior) |
| `Agent.run() -> str` | method | Entry: routes task, runs three stages, catches BudgetExceeded to return best checkpointed code, emits final submit |
| `Agent._run_plan(plan, ckpt) -> str` | method | Runs stages in order; returns early with best correct code on stage failure; re-checks cosim after optimize only when `"cosim" in correctness_stages` |
| `Agent._reach_correctness(plan, ckpt) -> bool` | method | Up to max_rounds repair loop: csim(+cosim), pre-csim review on first attempt, distills feedback + KB + review-gated repair on failure |
| `Agent._repair_with_review(code, feedback_text, kb_text) -> str\|None` | method | Two gates: mechanical checks (hard) then LLM review (semantic); feeds mechanical issues back into the next repair retry |
| `Agent._do_synth(plan, ckpt) -> int\|None` | method | Synth repair loop (§4.3): on failure distills feedback, queries KB, repairs, and **re-verifies csim before spending another synth**; a csim-breaking repair iterates on the csim feedback; records `_synth_summary` on success |
| `Agent._valid_latency(report) -> int\|None` | static method | Invalid-latency guard: None or <=0 is treated as missing (keeps the latency=0 parse anomaly out of the archive) |
| `Agent._optimize(plan, ckpt)` | method | Optimize loop (§4.4, v2.4): snapshot at entry -> Phase 1 cached design brief -> Phase 2a proposals (with compatibility annotations) -> **Phase 2b selector review AI picks a compatible subset (dual confirmation)** -> Phase 3 combined generation with gates -> csim+synth re-verify -> same-level latency arbitration; a failed combo falls back to the first strategy once (attribution); stops on single-strategy failure / no improvement / unaffordable tools / round cap |
| `Agent._try_opt_candidate(ckpt, strategies, round_n) -> str` | method | Full per-candidate pipeline: review-gated generation -> csim re-verify -> synth re-verify -> same-level arbitration; returns "improved"/"no_improvement"/"failed" (acceptance updates the archive and synth_summary) |
| `Agent._apply_with_review(code, strategies) -> str\|None` | method | Review-gated variant for Phase 3: the generator is apply_strategies (combined subset); mechanical failures are folded into the first strategy for the retry |
| `Agent._post_opt_cosim_recheck(ckpt)` | method | §4.5: re-verifies cosim only when best changed during optimization; on failure (or unaffordable cosim) **really rolls back** to the pre-optimization snapshot |
| `Agent._restore_snapshot(ckpt, snap)` | static method | Restores all snapshot fields (code/level/latency/cosim_ok) |
| `Agent._kb_lookup(fb) -> str` | method | Queries KB with fb.signatures; returns hits summary (empty when KB disabled or no hits); since v0.7.0 the kb_search event carries `hit_ids` (ids of matched entries, prerequisite for P3-10 verification) |
| `Agent._llm_usage_fields() -> dict` | method | New in v0.7.0 (P4-03): reads the backend's `last_usage`/`model` to attach prompt_tokens/completion_tokens/reasoning_tokens/model to llm_call events (pure observability; backends without those attrs yield an empty dict) |

### Exports
No `__all__`; primary export is the `Agent` class.

### Dependencies
- Internal: `.checkpoint` (Checkpoint, Level), `.feedback` (build_feedback), `.llm_client` (HLSLLMClient, Strategy), `.mechanical_checks` (mechanical_review), `.observability` (Heartbeat, Logger), `.router` (RunPlan, route)
- External: `llm4hls.budget.BudgetExceeded` (harness, imported at load time); uses harness `Task` / `ToolServer` at runtime

### Key Design Points
- Linear with backtracking: the first-round pre-csim review can catch bugs before spending a csim credit; each edited candidate does not advance level, only feeds the next input. Since v0.7.0 the redundant description snippet in the pre-csim review is kept only in full mode (repair already injects the full description; graded modes drop it to save tokens).
- Token-mode (v0.7.0, P4-03): the `route` event records token_mode for A/B traceability; llm_call events (extract_brief/propose/select/apply) uniformly carry per-call token fields.
- Two-gate repair: mechanical (deterministic, catches signature/header changes) first, LLM review second; mechanical failures are re-fed into the next repair (up to max_review_retries extra retries).
- Synth repair loop (§4.3): every repair re-verifies csim (1 credit) before another synth (4 credits), so a correctness-breaking candidate never burns a synth call; `max_synth_rounds=3`.
- Optimize loop (§4.4): AMD Phase 1's three-piece context (official design document description+headers, the cached extract_design_brief summary, the synth report) is injected into every strategy exploration; v2.4 strategy combos — propose annotates compatibility, the selector review AI dually confirms and picks a subset, apply merges them; a failed combo falls back to the subset's first strategy once (attribution) and only a further failure stops the loop; `max_optimize_rounds=4` (worst case 2×5=10 credits per round).
- Environment-error detection: csim failure with elapsed_s<0.5 and empty log is treated as a missing vitis-run, raising a RuntimeError with fix guidance.
- Latency=0 guard: `_valid_latency` treats <=0 as missing so a "0-cycle" report can never win every same-level latency comparison and corrupt the archive (parse anomaly noted in dev-log 2026-07-17-01).
- Real rollback (§4.5): the optimize-entry snapshot covers all Checkpoint fields; a failed (or unaffordable) cosim re-check restores them wholesale instead of merely logging.
- v2.9 (v0.8.0) credit-driven optimize stopping + cosim repair-then-rollback: `_optimize_can_continue` makes "can we still afford 1 csim + 1 synth" the primary stopping condition (cosim-requiring tasks additionally reserve `_COSIM_RECHECK_RESERVE` = 26 credits for the §4.5 re-check); `max_optimize_rounds=20` is only a safety cap. A post-optimization cosim failure now goes through `_repair_optimized_cosim` first (feedback + KB + review-gated repair, csim re-verify before re-cosim, up to max_opt_repair attempts); only repair exhaustion rolls the snapshot back (`cosim_repair_exhausted`).
- v0.8.1 baseline anchoring: the blind pre-csim review is SKIPPED when the seed is already assumed correct (optimize tasks, initial_level=CORRECT) — the archive and the live code are the same object, so a blind rewrite of `ckpt.code` would destroy the known-good baseline before any tool confirms it (qwen3.5-122b matmul incident, 2026-07-25: latency doubled 16422->32827). The seed is csim-verified as-is instead (`pre_csim_review` event with `skipped="seed_assumed_correct"`); only a real csim failure enters the repair loop. Pinned by TC-AGENT-020.
- v0.8.1 synth-timeout backoff: a synth result with `phase == "timeout"` is not a normal code error (design explosion or an overloaded tool host). In `_do_synth`, a SECOND consecutive timeout stops the stage early (`synth_timeout_backoff` event, correct version kept) instead of burning the remaining rounds (qwen3.5-122b vecadd incident: 4 consecutive timeouts ~= 19 credits for a correctness-only score); `_try_opt_candidate` likewise discards a candidate class after two consecutive synth timeouts rather than repairing again. Pinned by TC-AGENT-021.
- Architecture sections referenced: §4 main loop, §4.3 synth, §4.4 optimize, §4.5 re-check, §5 backtracking, §2 checkpoint.
