# agent/main_loop.py 说明文档

## 中文说明

### 用途
实现 agent-architecture.md §4 的主循环：线性顺序（correctness -> synth -> optimize）但带回溯——每次编辑后重新验证已通过的阶段，因为修后段 bug 可能破坏前段（见 §5）。检查点（§2）天然提供回滚。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `Agent` | class | 核心 agent，替换 llm4hls.ReferenceAgent，驱动 correctness->synth->optimize 流 |
| `Agent.__init__(task, server, llm, kb=None, max_rounds=6, run_dir="runs")` | method | 构造，持有 task/server/llm/kb，创建 Logger 与 Heartbeat |
| `Agent.run() -> str` | method | 入口：route 任务后执行三阶段，捕获 BudgetExceeded 返回最佳 checkpoint 代码，最终发 submit 事件 |
| `Agent._run_plan(plan, ckpt) -> str` | method | 顺序执行三阶段，任一阶段失败时提前返回最佳正确代码 |
| `Agent._reach_correctness(plan, ckpt) -> bool` | method | 最多 max_rounds 轮修复循环：csim(+cosim)，首轮 pre-csim review，失败时蒸馏反馈+查 KB+review-gated 修复 |
| `Agent._repair_with_review(code, feedback_text, kb_text) -> str\|None` | method | 两道闸门：mechanical checks（硬）与 LLM review（语义），失败时把 mechanical 问题回灌反馈再重试 |
| `Agent._do_synth(plan, ckpt) -> int\|None` | method | 跑综合，成功则按归档规则提升到 SYNTH 级并记录 latency |
| `Agent._optimize(plan, ckpt)` | method | Stage 3 PPA 优化（P4 占位 stub，当前 no-op） |
| `Agent._post_opt_cosim_recheck(ckpt)` | method | structural 任务优化后重验 cosim（§4.5），失败发 rollback 事件 |
| `Agent._kb_lookup(fb) -> str` | method | 用 fb.signatures 查知识库，返回命中摘要文本（KB 关闭或无命中返回空串） |

### 导出
无 `__all__`；主要导出 `Agent` 类。

### 依赖
- 内部依赖：`.checkpoint`(Checkpoint, Level)、`.feedback`(build_feedback)、`.llm_client`(HLSLLMClient)、`.mechanical_checks`(mechanical_review)、`.observability`(Heartbeat, Logger)、`.router`(RunPlan, route)
- 外部依赖：`llm4hls.budget.BudgetExceeded`（harness，导入时即加载）；运行期使用 harness 的 `Task` / `ToolServer`

### 关键设计点
- 线性带回溯：correctness 阶段首轮 pre-csim review 可在花 csim 信用前抓 bug；每次编辑候选不提升 level，仅下次输入。
- 双闸门修复：mechanical（确定性，捕获签名/头文件变更）在前，LLM review 在后；mechanical 失败时问题回灌反馈再修（最多 max_review_retries 次额外重试）。
- 环境错误检测：csim 失败且 elapsed_s<0.5 且日志为空时判定 vitis-run 缺失，抛 RuntimeError 给出修复指引。
- 架构章节引用：§4 主循环、§5 回溯、§2 checkpoint、§4.5 优化后 cosim 重验。

---

## English

### Purpose
Implements the agent-architecture.md §4 main loop: linear order (correctness -> synth -> optimize) with backtracking — every edit re-verifies already-passed stages because fixing a later bug can break an earlier one (see §5). The checkpoint (§2) gives rollback for free.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `Agent` | class | Core agent replacing llm4hls.ReferenceAgent; drives correctness->synth->optimize |
| `Agent.__init__(task, server, llm, kb=None, max_rounds=6, run_dir="runs")` | method | Construction; holds task/server/llm/kb, creates Logger and Heartbeat |
| `Agent.run() -> str` | method | Entry: routes task, runs three stages, catches BudgetExceeded to return best checkpointed code, emits final submit |
| `Agent._run_plan(plan, ckpt) -> str` | method | Runs stages in order; returns early with best correct code on stage failure |
| `Agent._reach_correctness(plan, ckpt) -> bool` | method | Up to max_rounds repair loop: csim(+cosim), pre-csim review on first attempt, distills feedback + KB + review-gated repair on failure |
| `Agent._repair_with_review(code, feedback_text, kb_text) -> str\|None` | method | Two gates: mechanical checks (hard) then LLM review (semantic); feeds mechanical issues back into the next repair retry |
| `Agent._do_synth(plan, ckpt) -> int\|None` | method | Runs synthesis; on success advances to SYNTH level via archive rules and records latency |
| `Agent._optimize(plan, ckpt)` | method | Stage 3 PPA optimization (P4 stub, currently no-op) |
| `Agent._post_opt_cosim_recheck(ckpt)` | method | Structural tasks re-verify cosim after optimization (§4.5); emits rollback on failure |
| `Agent._kb_lookup(fb) -> str` | method | Queries KB with fb.signatures; returns hits summary (empty when KB disabled or no hits) |

### Exports
No `__all__`; primary export is the `Agent` class.

### Dependencies
- Internal: `.checkpoint` (Checkpoint, Level), `.feedback` (build_feedback), `.llm_client` (HLSLLMClient), `.mechanical_checks` (mechanical_review), `.observability` (Heartbeat, Logger), `.router` (RunPlan, route)
- External: `llm4hls.budget.BudgetExceeded` (harness, imported at load time); uses harness `Task` / `ToolServer` at runtime

### Key Design Points
- Linear with backtracking: the first-round pre-csim review can catch bugs before spending a csim credit; each edited candidate does not advance level, only feeds the next input.
- Two-gate repair: mechanical (deterministic, catches signature/header changes) first, LLM review second; mechanical failures are re-fed into the next repair (up to max_review_retries extra retries).
- Environment-error detection: csim failure with elapsed_s<0.5 and empty log is treated as a missing vitis-run, raising a RuntimeError with fix guidance.
- Architecture sections referenced: §4 main loop, §5 backtracking, §2 checkpoint, §4.5 post-optimization cosim recheck.
