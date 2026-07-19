# Agent 本体

Budgeted End-to-End LLM4HLS Agent 的 Python 实现。在有限 credit 预算内自动修复和优化 Vitis HLS C/C++ 代码。

架构设计见 [`docs-development/design/agent-architecture.md`](../docs-development/design/agent-architecture.md)（Mermaid 流程图 + 存档逻辑 + 可观测性）。本文档是**代码导览**——读代码时从这里开始。

---

## 快速启动

```bash
# 离线跑（不需 Vitis、不需 API key，用 ScriptedClient 喂预设答案）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# 真 Vitis + 真 DeepSeek（完整端到端）
export LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis
source $LLM4HLS_VITIS_HLS_ROOT/settings64.sh
source .env   # DEEPSEEK_API_KEY
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

CLI 选项：`--backend {scripted,deepseek,openrouter}`、`--budget N`、`--work DIR`

---

## 模块职责（一句话）

| 文件 | 比喻 | 职责 |
|---|---|---|
| `main_loop.py` | **大脑** | 主循环：correctness → synth → optimize，串起所有模块 |
| `router.py` | **决策** | 读 task.toml，选关卡路径（repair→[csim]、structural→[csim,cosim]） |
| `checkpoint.py` | **记忆** | 存档：哪个版本最好（三规则：等级更高→存；同级→比 latency；更低→拒） |
| `feedback.py` | **感知** | 从 csim/synth/cosim 日志提取错误码+关键词，构建 LLM 友好反馈 |
| `llm_client.py` | **手** | 调 LLM 改代码（repair/review/propose_strategies/apply_strategy） |
| `mechanical_checks.py` | **眼** | 硬性检查：签名变没变、include 在不在（不信任 LLM 的地方） |
| `deepseek_client.py` | **嘴** | DeepSeek V4 Pro API 对接（OpenAI 兼容，推理模型，记 token） |
| `observability.py` | **日记** | JSONL 结构化日志 + 心跳线程（卡死检测） |
| `score_history.py` | **成绩单** | 每题 scores.jsonl：record/recent/format，CLI 与 TUI 双入口共享（v0.4.0） |
| `knowledge_base/` | **字典** | bug→修法知识库，按错误码/关键词检索注入 prompt；`entries.py` 含 7 条种子条目 |
| `__init__.py` | | 包入口，导出 route/RunPlan/Checkpoint/Level |

---

## 模块调用关系

```
run_agent.py (driver/CLI)
  │
  ├── agent.main_loop.Agent ──────────────────────────────────────┐
  │       │                                                        │
  │       ├── agent.router.route(task) → RunPlan                   │
  │       ├── agent.checkpoint.Checkpoint (存档判定)                │
  │       ├── agent.feedback.build_feedback(results) → Feedback    │
│       ├── agent.llm_client.HLSLLMClient                        │
│       │       ├── .repair(task, code, feedback, kb_text)       │
│       │       ├── .review(task, code, focus)                   │
│       │       ├── .extract_design_brief(task, code)            │
│       │       ├── .propose_strategies(task, code, synth, brief)│
│       │       ├── .select_strategies(...)  [v2.4 评审 AI]      │
│       │       └── .apply_strategies(subset, brief) [v2.4 组合] │
  │       │       │                                                │
  │       │       └── 注入 backend (DeepSeekClient / ScriptedClient)│
  │       │                                                        │
  │       ├── agent.mechanical_checks.mechanical_review(...)       │
  │       ├── agent.observability.Logger + Heartbeat              │
  │       └── agent.knowledge_base.KnowledgeBase.search(...)      │
  │                                                                │
  └── llm4hls.* (harness: ToolServer/Budget/Task/grade) ◄──────────┘
          │
          └── ToolServer.csim/synth/cosim(code) → ToolResult
```

**依赖方向**：main_loop 依赖所有 agent 模块 + harness。agent 模块之间尽量不互相依赖（checkpoint/router/feedback/observability/knowledge_base 都是独立的）。唯一的双向耦合是 llm_client 依赖 feedback 的输出格式（但通过参数传递，不直接 import）。

---

## 代码阅读顺序

按**从外到内、从简单到核心**读：

### 第一遍：了解全貌（30 分钟）

1. **`__init__.py`**（22 行）— 看这个包导出什么
2. **`router.py`**（70 行）— 最简单的模块，纯数据。理解 RunPlan 是什么
3. **`checkpoint.py`**（68 行）— 核心数据结构。理解 Level 和三规则
4. **`scripts/run_agent.py`**（82 行）— 入口，看怎么组装 agent
5. **`main_loop.py` 的 `run()` 方法**（约 20 行）— 主循环骨架，不读细节

### 第二遍：看数据流（40 分钟）

6. **`feedback.py`**（102 行）— ToolResult 怎么变成 LLM 能看懂的反馈
7. **`main_loop.py` 的 `_reach_correctness()`**（约 60 行）— 修复循环，核心中的核心
8. **`main_loop.py` 的 `_repair_with_review()`**（约 30 行）— 双层 review 怎么工作

### 第三遍：看适配层（30 分钟）

9. **`mechanical_checks.py`**（96 行）— 签名/include 检查，简单但重要
10. **`llm_client.py`**（219 行）— 四个领域方法 + prompt 模板
11. **`deepseek_client.py`**（126 行）— API 对接 + token 统计

### 第四遍：看基建（15 分钟）

12. **`observability.py`**（121 行）— 日志 + 心跳
13. **`knowledge_base/retriever.py`**（61 行）— RAG 检索

### 第五遍：看外部依赖（按需）

14. `contest/fpt26-harness/llm4hls/harness.py` — ToolServer（agent 调的工具接口）
15. `contest/fpt26-harness/llm4hls/tools.py` — CSimTool/SynthTool/CoSimTool
16. `contest/fpt26-harness/llm4hls/scoring.py` — 评分公式

---

## 核心数据流（projection 题实测 + v0.2.0 补全的 synth/optimize 段）

```
route(task) → RunPlan{repair, [csim], init_level=0}
  │
  ▼ _reach_correctness:
  csim(code) → runtime_fail         ← Vitis 真跑出来 (9.7s)
  build_feedback(csim_r) → Feedback{runtime_fail, signatures=[]}
  _kb_lookup(fb) → ""               ← 无命中则空串
  _repair_with_review:
    llm.repair(task, code, fb_text, "") → new_code     ← DeepSeek 修复
    mechanical_review(orig, new_code, task) → (True)    ← 签名未变
    llm.review(task, new_code, focus) → (True, "PASS")   ← LLM 审查通过
  csim(new_code) → pass             ← 修复真的过了 (9.7s)
  ckpt.should_accept(CORRECT, None) → True
  ckpt.accept(new_code, CORRECT)    ← 存档 0→1
  │
  ▼ _do_synth (v0.2.0: 修复循环):
  synth(ckpt.code) → synth_error?
    ├─ 是 → build_feedback → _kb_lookup(命中种子条目) → _repair_with_review
    │       → 重验 csim(1 credit) → 过才再 synth(4 credits)   [§4.3]
    └─ 否 → ckpt.accept(ckpt.code, SYNTH, latency)  ← 存档 1→2 + 记 synth_summary
  │
  ▼ _optimize (v0.3.0: 策略组合 + 评审 AI):
  快照 ckpt（§4.5 回滚点）
  extract_design_brief(task, code) → 设计摘要（一次缓存）     [AMD Phase 1]
  每轮: propose_strategies(设计文档+摘要+最新 synth 报告)     [AMD Phase 2a]
        → 每策略标 combinable_with 兼容性
        → select_strategies 评审 AI 复核+选兼容子集           [Phase 2b 双重确认]
        → apply_strategies(子集合并) → _apply_with_review     [AMD Phase 3]
        → 重验 csim + synth → should_accept(SYNTH, lat) 同级择优
        → 组合失败 → 回退子集首策略单试一次（归因），仍失败才停
  │
  ▼ (需要 cosim 的题) _post_opt_cosim_recheck:
  best 变过才回验；cosim 失败 → 真回滚到优化前快照            [§4.5]
  │
  ▼ return ckpt.code → grade() → SCORE 1.400
```

---

## 函数清单

### main_loop.Agent

| 方法 | 可见性 | 职责 |
|---|---|---|
| `__init__(task, server, llm, kb, max_rounds, max_synth_rounds, max_optimize_rounds, run_dir)` | public | 注入依赖 + 跨阶段状态（synth_summary/design_brief/快照） |
| `run() -> str` | public | 入口：路由 → correctness → synth → optimize → 返回 best code |
| `_run_plan(plan, ckpt) -> str` | private | 按 RunPlan 执行三阶段 |
| `_reach_correctness(plan, ckpt) -> bool` | private | 阶段1：csim（+cosim）修复循环 |
| `_repair_with_review(code, feedback, kb_text) -> str\|None` | private | 生成修复 + 机械检查 + LLM review 双层验证 |
| `_do_synth(plan, ckpt) -> int\|None` | private | 阶段2：synth 修复循环（RAG+重验 csim 再 synth），拿 baseline latency |
| `_valid_latency(report) -> int\|None` | private(static) | latency<=0 视为缺失（latency=0 解析异常防御） |
| `_optimize(plan, ckpt)` | private | 阶段3：PPA 优化循环（Phase 1-3 + 评审 AI 选子集 + 组合生成 + 失败回退） |
| `_try_opt_candidate(ckpt, strategies, round_n) -> str` | private | 单候选流水线：生成→重验→同级择优，返回 improved/no_improvement/failed |
| `_apply_with_review(code, strategies) -> str\|None` | private | Phase 3 生成 + 双层验证（apply_strategies 组合变体） |
| `_post_opt_cosim_recheck(ckpt)` | private | 需 cosim 题优化后回验，失败真回滚快照 |
| `_restore_snapshot(ckpt, snap)` | private(static) | 快照整体恢复（§4.5） |
| `_kb_lookup(fb) -> str` | private | 查知识库，返回命中条目文本 |

### router

| 函数 | 职责 |
|---|---|
| `route(task) -> RunPlan` | task.type + requires_cosim → 关卡路径 |

### checkpoint.Checkpoint

| 方法 | 职责 |
|---|---|
| `should_accept(cand_level, cand_latency) -> bool` | 三规则判定 |
| `accept(code, level, latency, cosim_ok)` | 提交为新 best |

### feedback

| 函数/方法 | 职责 |
|---|---|
| `build_feedback(*results) -> Feedback` | 从 ToolResult 蒸馏错误签名+反馈文本 |
| `Feedback.as_prompt_block() -> str` | 渲染为 repair prompt 的反馈块 |

### llm_client.HLSLLMClient

| 方法 | 职责 |
|---|---|
| `repair(task, code, feedback, kb_text) -> str\|None` | 让 LLM 修复代码 |
| `review(task, code, focus) -> (bool, str)` | 交叉验证候选代码 |
| `extract_design_brief(task, code) -> str` | AMD Phase 1：提炼设计摘要（功能/循环/数据流/瓶颈），optimize 前调一次缓存 |
| `propose_strategies(task, code, synth_summary, design_brief) -> list[Strategy]` | AMD Phase 2a：注入设计文档+摘要+报告，提策略（标 combinable_with） |
| `select_strategies(task, code, strategies, synth_summary, design_brief) -> (list[int], str)` | Phase 2b 评审 AI：复核兼容性选子集；解析失败回退 [0] |
| `apply_strategies(task, code, strategies, design_brief) -> str\|None` | AMD Phase 3：兼容子集合并生成（双重确认） |

### mechanical_checks

| 函数 | 职责 |
|---|---|
| `mechanical_review(original, candidate, task) -> (bool, list[str])` | 签名+include 硬性检查 |

### deepseek_client.DeepSeekClient

| 方法 | 职责 |
|---|---|
| `complete(system, user) -> str` | 调 DeepSeek API |
| `usage_summary() -> str` | token 用量摘要 |

### observability

| 类.方法 | 职责 |
|---|---|
| `Logger.event(event, **fields)` | 写一条 JSONL 事件 |
| `Heartbeat.set_stage(stage, credit)` | 更新当前阶段（卡死检测） |

### knowledge_base

| 方法 | 职责 |
|---|---|
| `KnowledgeBase.search(signatures) -> list[KBEntry]` | 按错误码/关键词检索条目 |
| `seed_entries() -> list[KBEntry]` | 7 条种子条目（synth 4 + cosim 1 + csim 2），入口默认装载 |

---

## 外部依赖（harness，只读复用）

agent 通过 import 复用官方 harness 的以下类，定义在 `contest/fpt26-harness/llm4hls/`：

| harness 类 | 用途 | agent 在哪用 |
|---|---|---|
| `Task` / `load_task()` | 题目加载 | run_agent.py |
| `Budget` / `BudgetExceeded` | credit 计费 | run_agent.py / main_loop.py |
| `ToolServer` | csim/synth/cosim 工具接口 | main_loop.py |
| `ToolResult` | 工具返回（kind/ok/phase/log/report） | feedback.py / main_loop.py |
| `grade()` / `Scorecard` | 评分 | run_agent.py |
| `ScriptedClient` / `OpenRouterClient` | LLM 后端 | run_agent.py |

---

## 设计决策速查

| 决策 | 理由 |
|---|---|
| fork harness 不重写 | 评估接口被官方锁死为进程内函数调用 |
| 单进程不做 RPC | subprocess 跑 vitis 已有进程隔离 |
| 双层 review（机械+LLM） | 实测 LLM self-check 漏签名变更，机械检查兜底 |
| 存档 level 单调不减 | 评分分层（correct 门 > synth > PPA），天然映射 |
| DeepSeek max_tokens=16384 | 推理模型 reasoning_tokens 占 max_tokens |
| optimize 先提取设计摘要再改 | AMD Phase 1：不给设计上下文，LLM 只给泛泛建议（v0.2.0） |
| 策略组合需双重确认才合并 | pragma 交互是 LLM 高错点；提出者+评审者都认互不干扰才组合（v0.3.0，用户决策） |
| 组合失败回退首策略一次 | 组合候选失败无法归因到单个策略，缩小集合重试（v0.3.0） |
| synth 修复先重验 csim 再 synth | 1 credit 比 4 credits 便宜；改 synth 可能破坏正确性（§5） |
| 优化后 cosim 失败真回滚快照 | 曾只记日志不恢复，会带着死锁提交（§4.5，v0.2.0 修） |

---

## 已知坑点 (Known Pitfalls)

- **`knowledge-base/`（连字符）vs `knowledge_base/`（下划线）**：前者是 spec 文档目录（只有 README），后者是 Python 包（`retriever.py` + `entries.py`，可 import）。命名差异源于"文档目录用连字符、Python 包用下划线（合法标识符）"。两者都活跃，不要删任何一个。
- **harness import 路径**：agent 模块 import `llm4hls.*` 时，需要 `contest/fpt26-harness` 在 `sys.path` 中。`scripts/run_agent.py`、`scripts/test_main_loop.py` 和 `tui/app.py` 都做了 `sys.path.insert`，直接在别的目录跑 agent 模块会 ImportError。
- **DeepSeek reasoning_tokens**：推理模型的 reasoning 过程消耗 max_tokens 额度，如果设太小会截断 content。当前设 16384。
- **KB 检索签名必须是短串**：检索器做整串子串匹配，`build_feedback` 产出的是错误码（`[XFORM 203-313]`）+ 关键词（`deadlock`）级短签名；整句查询永远不中。条目 signatures 同样只放短串（见 entries.py 注释）。
- **种子 KB 默认装载**：`run_agent.py` 与 `tui/app.py` 都用 `KnowledgeBase(seed_entries())`（7 条）。P2-12 扩充时直接往 `entries.py` 加，别改两处入口。
- **synth latency=0 解析异常**：真机出现过 synth 过但 latency=0。`Agent._valid_latency` 把 <=0 当缺失——若拿掉这层防御，"0 周期"会在同级 latency 比较中永远获胜并污染存档。根因待真机排查（dev-log 2026-07-17-01 遗留）。
