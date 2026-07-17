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
| `knowledge_base/` | **字典** | bug→修法知识库，按错误码/关键词检索注入 prompt |
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
  │       │       ├── .propose_strategies(...)  [P4]               │
  │       │       └── .apply_strategy(...)     [P4]               │
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

## 核心数据流（projection 题实测）

```
route(task) → RunPlan{repair, [csim], init_level=0}
  │
  ▼ _reach_correctness:
  csim(code) → runtime_fail         ← Vitis 真跑出来 (9.7s)
  build_feedback(csim_r) → Feedback{runtime_fail, signatures=[]}
  _kb_lookup(fb) → ""               ← KB 空
  _repair_with_review:
    llm.repair(task, code, fb_text, "") → new_code     ← DeepSeek 修复
    mechanical_review(orig, new_code, task) → (True)    ← 签名未变
    llm.review(task, new_code, focus) → (True, "PASS")   ← LLM 审查通过
  csim(new_code) → pass             ← 修复真的过了 (9.7s)
  ckpt.should_accept(CORRECT, None) → True
  ckpt.accept(new_code, CORRECT)    ← 存档 0→1
  │
  ▼ _do_synth:
  synth(ckpt.code) → pass, latency
  ckpt.accept(ckpt.code, SYNTH, latency)  ← 存档 1→2
  │
  ▼ _optimize: (P4 实现，当前 stub)
  │
  ▼ return ckpt.code → grade() → SCORE 1.400
```

---

## 函数清单

### main_loop.Agent

| 方法 | 可见性 | 职责 |
|---|---|---|
| `__init__(task, server, llm, kb, max_rounds, run_dir)` | public | 注入依赖 |
| `run() -> str` | public | 入口：路由 → correctness → synth → optimize → 返回 best code |
| `_run_plan(plan, ckpt) -> str` | private | 按 RunPlan 执行三阶段 |
| `_reach_correctness(plan, ckpt) -> bool` | private | 阶段1：csim（+cosim）修复循环 |
| `_repair_with_review(code, feedback, kb_text) -> str\|None` | private | 生成修复 + 机械检查 + LLM review 双层验证 |
| `_do_synth(plan, ckpt) -> int\|None` | private | 阶段2：synth 拿 baseline latency |
| `_optimize(plan, ckpt)` | private | 阶段3：PPA 优化循环（P4） |
| `_post_opt_cosim_recheck(ckpt)` | private | structural 题优化后回验 cosim |
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
| `propose_strategies(task, code, synth) -> list[Strategy]` | AMD Phase 2：提优化策略 |
| `apply_strategy(task, code, strategy) -> str\|None` | AMD Phase 3：按策略生成代码 |

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
