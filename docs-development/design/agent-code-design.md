# Agent 代码详细设计 (Code Design)

> 状态：v1（2026-07-15）
> 对应代码版本：P2 里程碑
> 架构设计依据：[agent-architecture.md](./agent-architecture.md)

本文档是 agent 代码的详细设计说明——模块职责、函数清单、模块间耦合、数据流。供细读代码时参考。

---

## 1. 目录结构

```
agent/
  __init__.py              包入口，导出 route/RunPlan/Checkpoint/Level
  router.py                路由器：task.toml → RunPlan
  checkpoint.py            存档逻辑：关卡等级 + 三条存档规则
  feedback.py              反馈构建：ToolResult → 错误签名 + LLM 友好文本
  llm_client.py            LLM 调用封装：repair/review/propose_strategies/apply_strategy
  deepseek_client.py       DeepSeek V4 Pro 后端（OpenAI 兼容）
  mechanical_checks.py     硬性检查：签名/include（不依赖 LLM）
  observability.py         可观测性：JSONL 日志 + 心跳
  main_loop.py             主循环：correctness → synth → optimize
  knowledge_base/
    __init__.py            包入口
    retriever.py           KBEntry + 关键词/错误码检索器

scripts/
  run_agent.py             driver/CLI 入口，串起 harness + agent

contest/fpt26-harness/llm4hls/  ← 官方 harness（复用，不改）
  harness.py               ToolServer（agent 调的工具接口）
  budget.py                Budget（credit 计费）
  task.py                  Task + load_task（题目加载）
  tools.py                 CSimTool/SynthTool/CoSimTool + ToolResult
  report.py                csynth.xml/cosim.rpt 解析器
  vitis.py                 vitis-run 命令行封装
  scoring.py                评分（hidden testbench + PPA）
  llm.py                   ScriptedClient/OpenRouterClient（官方后端）
  agent.py                 ReferenceAgent（官方参考 agent，我们不用）
```

---

## 2. 模块职责与依赖关系

### 2.1 依赖图（箭头 = import）

```
                    run_agent.py (driver)
                    │
                    ├── agent.main_loop.Agent
                    │       ├── agent.router (route, RunPlan)
                    │       ├── agent.checkpoint (Checkpoint, Level)
                    │       ├── agent.feedback (build_feedback, Feedback)
                    │       ├── agent.llm_client (HLSLLMClient, Strategy)
                    │       ├── agent.mechanical_checks (mechanical_review)
                    │       ├── agent.observability (Logger, Heartbeat)
                    │       └── agent.knowledge_base (KnowledgeBase)
                    │
                    ├── agent.deepseek_client.DeepSeekClient   (注入为 backend)
                    │
                    └── llm4hls.* (harness: Task/Budget/ToolServer/grade/load_task)
```

### 2.2 分层

| 层 | 模块 | 职责 | 依赖 |
|---|---|---|---|
| **驱动层** | run_agent.py | CLI 入口，解析参数，组装 agent | agent + harness |
| **核心层** | main_loop.py | 主循环：correctness/synth/optimize | router, checkpoint, feedback, llm_client, mechanical_checks, observability, knowledge_base |
| **策略层** | router.py | 按 task_type 选关卡路径 | 无（纯数据） |
| **数据结构** | checkpoint.py | 存档判定 | 无（纯数据） |
| **适配层** | feedback.py, llm_client.py, mechanical_checks.py, deepseek_client.py | 格式转换 / 接口适配 | harness ToolResult |
| **基建层** | observability.py, knowledge_base/ | 日志 / RAG | 无（独立） |
| **外部** | harness (llm4hls.*) | 工具调用 / 计费 / 评分 | vitis-run |

---

## 3. 模块详解

### 3.1 router.py — 路由器

**职责**：读题目的 task.toml 元数据，决定 correctness 需要过哪几关、是否优化。不花 credit，不调工具。

**核心函数**：

| 函数 | 签名 | 说明 |
|---|---|---|
| `route(task)` | `Task -> RunPlan` | 根据 task.type 和 task.requires_cosim 产出运行计划 |

**数据结构**：

```python
@dataclass
class RunPlan:
    task_type: str                  # repair/optimize/structural/generate
    correctness_stages: list[str]    # ["csim"] 或 ["csim", "cosim"]
    needs_optimize: bool             # 是否进入 PPA 优化
    initial_level: int               # 起始存档等级（optimize=1, 其余=0）
```

**路由逻辑**：
- repair/optimize → stages=[csim]
- structural → stages=[csim, cosim]（requires_cosim=true）
- optimize 题初始 level=1（假设 csim 已过，循环里确认）

**耦合**：被 main_loop.py 的 `Agent.__init__` 调用一次。无下游依赖。

---

### 3.2 checkpoint.py — 存档逻辑

**职责**：维护"当前最佳版本"（best），判定新候选是否替换 best。这是整个主循环的核心数据结构。

**核心数据结构**：

```python
class Level:
    NONE = 0        # 啥都没过
    CORRECT = 1     # csim（+cosim if structural）过了
    SYNTH = 2       # synth 过了，有 latency 数据

@dataclass
class Checkpoint:
    code: str                    # 当前最佳 kernel 源码
    level: int                   # 关卡等级
    latency: int | None          # synth/cosim 的 latency（cycle 数）
    cosim_ok: bool | None        # cosim 是否通过（structural gate）
```

**核心方法**：

| 方法 | 说明 |
|---|---|
| `should_accept(cand_level, cand_latency) -> bool` | 三条存档规则判定：等级更高→接受；同级→比 latency 更低才接受；等级更低→拒绝 |
| `accept(code, level, latency, cosim_ok)` | 提交候选为新 best（仅在 should_accept=True 后调用） |

**存档三规则**（架构 §2.2）：
1. `level(C) > level(B)` → 无条件接受
2. `level(C) == level(B)` → latency 更低才接受
3. `level(C) < level(B)` → 绝不接受（correctness 倒退）

**回滚机制**：失败的候选不进 best，best 停在最后通过版本——自动回滚，无需额外逻辑。

**耦合**：被 main_loop.py 在每个阶段达标后调用。无下游依赖。

---

### 3.3 feedback.py — 反馈构建

**职责**：把 harness 的 ToolResult（原始日志）蒸馏成 (a) 错误签名（给 KB 检索用）和 (b) LLM 友好的反馈文本（给 repair prompt 用）。

**核心函数**：

| 函数 | 说明 |
|---|---|
| `build_feedback(*results) -> Feedback` | 从一个或多个 ToolResult 构建 Feedback 对象 |

**Feedback 对象**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `phases` | list[str] | 如 `["csim: runtime_fail"]` |
| `error_codes` | list[str] | 如 `["[XFORM 203-313]"]` |
| `signatures` | list[str] | KB 检索用关键词（错误码 + deadlock/streaming 等） |
| `log_tail` | str | 日志末尾 3000 字符 |
| `as_prompt_block() -> str` | 方法 | 渲染为 repair prompt 的反馈块 |

**正则提取**：
- `_ERROR_CODE_RE`：匹配 `[XFORM 203-313]`、`[RTGEN 206-102]` 等错误码
- `_DEADLOCK_RE`：匹配 deadlock/hung/stall 关键词
- `_FIFO_RE`：匹配 FIFO/stream/TVALID/TREADY/TLAST 关键词

**耦合**：被 main_loop.py 的 `_reach_correctness` 调用。输出传给 llm_client.repair 和 knowledge_base.search。

---

### 3.4 llm_client.py — LLM 调用封装

**职责**：在 harness 的 `LLMClient` Protocol（`complete(system, user) -> str`）之上，封装四个领域方法。

**核心类**：`HLSLLMClient`

**方法清单**：

| 方法 | 签名（简化） | 说明 |
|---|---|---|
| `repair(task, code, feedback_text, kb_text)` | `-> str \| None` | 给 LLM 源码+反馈+KB命中，返回修复后的代码（或 None） |
| `review(task, code, focus)` | `-> (bool, str)` | 交叉验证：检查候选代码是否破坏接口/引入 bug。返回(通过, 问题) |
| `propose_strategies(task, code, synth_summary)` | `-> list[Strategy]` | AMD Phase 2：让 LLM 提多个优化策略+权衡 |
| `apply_strategy(task, code, strategy)` | `-> str \| None` | AMD Phase 3：按选定策略生成优化代码 |

**辅助**：
- `_headers(task)` — 从 task.headers 渲染 header 文本
- `_parse_strategies(text)` — 从 LLM 自由文本解析 Strategy 列表
- `_harness_extract(text)` — 复用 harness 的 ```cpp 代码块提取正则

**Prompt 模板**（模块级常量）：
- `_REPAIR_SYSTEM` — 修复角色的 system prompt
- `_REVIEW_SYSTEM` — 审查角色的 system prompt
- `_STRATEGY_SYSTEM` — 策略探索的 system prompt

**耦合**：被 main_loop.py 调用。注入一个 backend（ScriptedClient/OpenRouterClient/DeepSeekClient）。

---

### 3.5 deepseek_client.py — DeepSeek 后端

**职责**：实现 `complete(system, user) -> str` 接口，对接 DeepSeek V4 Pro 原生 API。

**关键特性**：
- DeepSeek V4 Pro 是**推理模型**——每次调用产生 reasoning_tokens（先思考后回答）
- `max_tokens` 包含 reasoning + 输出，必须设大（默认 16384）
- 内置 usage 统计（prompt/completion/reasoning 分别计数），供 token 分析

**核心方法**：

| 方法 | 说明 |
|---|---|
| `complete(system, user) -> str` | 调 DeepSeek API，返回 content（不含 reasoning） |
| `usage_summary() -> str` | 返回累计用量摘要 |

**API key 管理**：从环境变量 `DEEPSEEK_API_KEY` 读取，**绝不入库**（.env 已 gitignore）。

**耦合**：被 run_agent.py 注入 HLSLLMClient。实现和 harness OpenRouterClient 同样的接口，可互换。

---

### 3.6 mechanical_checks.py — 硬性检查

**职责**：不依赖 LLM 的确定性检查，在 LLM review 之前作为第一道硬门。抓 LLM 容易漏的签名变更/header 丢失。

**核心函数**：

| 函数 | 说明 |
|---|---|
| `check_signature_unchanged(original, candidate, top_fn) -> (bool, str)` | 比较原始/候选的 top 函数签名 |
| `check_header_included(candidate, header_names) -> (bool, str)` | 检查候选代码是否保留了 #include |
| `mechanical_review(original, candidate, task) -> (bool, list[str])` | 跑所有机械检查，返回(是否全过, 问题列表) |

**为什么需要**：实测发现 DeepSeek self-check 漏掉了签名被改坏的情况（加了参数竟判 PASS）。机械检查 100% 可靠。

**耦合**：被 main_loop.py 的 `_repair_with_review` 调用，作为 LLM review 前的第一道门。

---

### 3.7 observability.py — 可观测性

**职责**：结构化日志 + 心跳，对应架构 §12。

**两个类**：

| 类 | 职责 |
|---|---|
| `Logger` | JSONL 事件日志（写文件 + stdout），12 个日志点 |
| `Heartbeat` | 后台线程，每 10s 报一条心跳（当前阶段/距上次活动秒数/credit余量/STALE标志） |

**Logger 方法**：
- `event(event_type, **fields)` — 写一条 JSONL 事件
- `age_s() -> float` — 距上次活动的秒数（给 Heartbeat 用）

**Heartbeat 方法**：
- `set_stage(stage, credit_remaining)` — 更新当前阶段（csim/synth/cosim/llm/idle）
- `start()` / `stop()` — 启停后台线程

**卡死判定**：心跳的 `age_s` 超过当前阶段的阈值（csim=180s/synth=600s/cosim=900s/llm=180s）标 STALE。

**耦合**：被 main_loop.py 在所有决策点调用。独立，无下游依赖。

---

### 3.8 knowledge_base/ — 知识库（RAG）

**职责**：按错误签名/关键词检索 bug→修法条目，注入 repair prompt。第一次迭代：错误码匹配。

**数据结构**：

```python
@dataclass
class KBEntry:
    id: str                    # 条目 ID
    symptom: str               # 症状描述
    root_cause: str            # 根因
    fix: str                   # 修法
    example: str               # 示例
    signatures: list[str]      # 触发关键词（错误码 + 关键词）

class KnowledgeBase:
    entries: list[KBEntry]
    def search(signatures) -> list[KBEntry]   # 子串匹配
```

**检索逻辑**：把 feedback.signatures 作为 query，对每条 entry 的 signatures + symptom + root_cause 做大小写不敏感子串匹配。

**耦合**：被 main_loop.py 的 `_kb_lookup` 调用。当前 entries 为空（待 P2-12 填充）。

---

### 3.9 main_loop.py — 主循环

**职责**：整个 agent 的核心。线性流程（correct → synth → optimize）+ 回溯重验 + 存档判定。

**核心类**：`Agent`

**方法清单**（按调用顺序）：

| 方法 | 可见性 | 说明 |
|---|---|---|
| `__init__(task, server, llm, kb, max_rounds, run_dir)` | public | 注入所有依赖 |
| `run() -> str` | public | 入口：路由 → correctness → synth → optimize → 返回 best code |
| `_run_plan(plan, ckpt) -> str` | private | 按 RunPlan 执行三阶段 |
| `_reach_correctness(plan, ckpt) -> bool` | private | **阶段1**：csim（+cosim if structural）修复循环 |
| `_repair_with_review(code, feedback, kb_text) -> str\|None` | private | 生成修复 + 机械检查 + LLM review 双层验证 |
| `_do_synth(plan, ckpt) -> int\|None` | private | **阶段2**：synth 拿 baseline latency |
| `_optimize(plan, ckpt)` | private | **阶段3**：PPA 优化循环（P4 实现，当前 stub） |
| `_post_opt_cosim_recheck(ckpt)` | private | structural 题优化后回验 cosim |
| `_kb_lookup(fb) -> str` | private | 查知识库，返回命中条目文本 |

**主循环数据流**（projection 题实测）：

```
route(task) → RunPlan{repair, [csim], init_level=0}
  │
  ▼
_reach_correctness:
  csim(code) → runtime_fail         ← 真实 Vitis 跑出来
  build_feedback(csim_result) → Feedback{runtime_fail, signatures=[]}
  _kb_lookup(fb) → ""               ← KB 空
  _repair_with_review:
    llm.repair(task, code, feedback, "") → new_code    ← DeepSeek 修复
    mechanical_review(orig, new_code, task) → (True, [])  ← 签名未变
    llm.review(task, new_code, focus) → (True, "PASS")    ← LLM 审查通过
  csim(new_code) → pass             ← 修复真的过了
  ckpt.should_accept(CORRECT, None) → True
  ckpt.accept(new_code, CORRECT)    ← 存档 0→1
  │
  ▼
_do_synth:
  synth(ckpt.code) → pass, latency=0
  ckpt.should_accept(SYNTH, 0) → True
  ckpt.accept(ckpt.code, SYNTH, 0)  ← 存档 1→2
  │
  ▼
_optimize: (stub, P4 实现)
  │
  ▼
return ckpt.code                    ← 交存档
```

**耦合**：依赖几乎所有其他 agent 模块 + harness 的 ToolServer/Budget。

---

### 3.10 run_agent.py — driver/CLI

**职责**：命令行入口，解析参数，组装 harness + agent，跑完后输出 transcript + scorecard。

**用法**：
```bash
python scripts/run_agent.py <task_dir> [--backend scripted|deepseek|openrouter] [--budget N]
```

**流程**：
1. `load_task(task_dir)` — 加载题目
2. `Budget(total)` — 创建 credit 预算
3. `ToolServer(task, budget, run_root)` — 创建工具服务器
4. 选 backend：ScriptedClient（离线）/ DeepSeekClient（真 LLM）/ OpenRouterClient
5. `HLSLLMClient(backend)` — 封装
6. `Agent(task, server, llm, kb)` — 创建 agent
7. `agent.run()` — 跑
8. 打印 transcript + grade scorecard + LLM 用量

---

## 4. 数据流总览

```
题目标 (task.toml + .cpp + .h + _tb.cpp)
    │
    ▼ load_task()
Task 对象 ────────────────────────────────────────────┐
    │                                                  │
    ▼ route()                    ToolServer ◄── Budget │
RunPlan                            │  csim/synth/cosim │
    │                              │  (花 credit)       │
    ▼                              ▼                    │
Agent.run() ──► _reach_correctness ──► ToolServer.csim(code)
    │                                      │
    │                                      ▼ ToolResult{kind, ok, phase, log, report}
    │                                      │
    │  ◄───────────────────────────────────┘
    │
    ├── build_feedback(result) ──► Feedback{phases, error_codes, signatures, log_tail}
    │                                  │
    ├── _kb_lookup(fb) ──► KnowledgeBase.search(signatures) ──► KBEntry[]
    │                                  │
    ├── _repair_with_review:
    │     llm.repair(task, code, feedback_text, kb_text) ──► new_code
    │     mechanical_review(orig, new_code, task) ──► (ok, issues)
    │     llm.review(task, new_code, focus) ──► (passed, issues)
    │                                  │
    ├── checkpoint.should_accept(level, latency) ──► bool
    │     ckpt.accept(code, level, latency)
    │                                  │
    ▼                                  │
  (循环回 csim，直到过)                │
    │                                  │
    ▼ (correctness 达标)               │
  _do_synth ──► ToolServer.synth(code)─┘
    │
    ▼ (synth 过)
  _optimize (P4) ──► propose_strategies + apply_strategy + 重验
    │
    ▼
  return ckpt.code ──► grade() ──► Scorecard
```

---

## 5. 关键设计决策记录

| 决策 | 理由 |
|---|---|
| fork harness 不重写 | 官方 ToolServer 已是进程内函数调用，评估接口被锁死，重造无收益 |
| 单进程不做 RPC | subprocess 跑 vitis 已有进程隔离，agent 本身串行无并发需求 |
| 双层 review（机械+LLM） | 实测 LLM self-check 漏掉签名变更，机械检查 100% 可靠兜底 |
| 存档 level 单调不减 | 评分公式分层（correct 门 > synth > PPA），存档规则天然映射 |
| 线性+回溯重验 | 改代码修后面 bug 可能破坏前面关卡，必须重验；存档机制自动回滚 |
| DeepSeek max_tokens=16384 | 推理模型 reasoning_tokens 占 max_tokens，太小会截断 |

---

## 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-15 | v1 初稿。基于 P2 里程碑代码版本，详述所有模块的函数清单、耦合、数据流。 | Agent 主 |
