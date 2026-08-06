> [English](agent-code-design.md)

# Agent 代码详细设计 (Code Design)

> 状态：v1（2026-07-15）
> 对应代码版本：P2 里程碑
> 架构设计依据：[agent-architecture.md](./agent-architecture.cn.md)
>
> **代码导览（模块职责一句话、阅读顺序、函数清单速查）已移至 [`agent/README.md`](../../agent/README.cn.md)，和代码放一起，读代码时直接看。**
>
> 本文档保留**设计层内容**：跨模块的详细依赖分析、数据流图、设计决策记录。

---

## 1. 依赖关系图

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

### 分层

| 层 | 模块 | 职责 | 依赖 |
|---|---|---|---|
| **驱动层** | run_agent.py | CLI 入口，解析参数，组装 agent | agent + harness |
| **核心层** | main_loop.py | 主循环：correctness/synth/optimize | router, checkpoint, feedback, llm_client, mechanical_checks, observability, knowledge_base |
| **策略层** | router.py | 按 task_type 选关卡路径 | 无（纯数据） |
| **数据结构** | checkpoint.py | 存档判定 | 无（纯数据） |
| **适配层** | feedback.py, llm_client.py, mechanical_checks.py, deepseek_client.py | 格式转换 / 接口适配 | harness ToolResult |
| **基建层** | observability.py, knowledge_base/ | 日志 / RAG | 无（独立） |
| **外部** | harness (llm4hls.*) | 工具调用 / 计费 / 评分 | vitis-run |

### 耦合要点

- main_loop 依赖所有 agent 模块 + harness。它是唯一的"中枢"。
- agent 模块之间**尽量不互相依赖**：checkpoint/router/feedback/observability/knowledge_base 都是独立的，可单独测试。
- 唯一的双向耦合：llm_client 消费 feedback 的输出格式，但通过参数传递（不直接 import feedback 模块）。
- deepseek_client 是可替换的——实现和 ScriptedClient/OpenRouterClient 同样的 `complete(system, user) -> str` 接口。

---

## 2. 总览数据流

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
    ▼ (synth 过，修复循环保 correctness 重验)
  _optimize ──► extract_design_brief(缓存) + propose_strategies + apply_strategy
    │           + 双闸门 review + csim/synth 重验 + 同级 latency 择优
    ▼ (需要 cosim 的题)
  _post_opt_cosim_recheck ──► 失败真回滚到优化前快照
    │
    ▼
  return ckpt.code ──► grade() ──► Scorecard
```

---

## 3. 关键设计决策记录

| 决策 | 理由 | 来源 |
|---|---|---|
| fork harness 不重写 | 官方 ToolServer 已是进程内函数调用，评估接口被锁死，重造无收益 | harness 分析 |
| 单进程不做 RPC | subprocess 跑 vitis 已有进程隔离，agent 本身串行无并发需求 | 架构讨论 |
| 双层 review（机械+LLM） | 实测 DeepSeek self-check 漏掉签名变更（加参数竟判 PASS），机械检查 100% 可靠兜底 | 实测发现 |
| 存档 level 单调不减 | 评分公式分层（correct 门 0.5 > synth 0.2 > PPA 0.3），存档规则天然映射 | 用户推演 |
| 线性+回溯重验 | 改代码修后面 bug 可能破坏前面关卡，必须重验；存档机制自动回滚 | 架构 §5 |
| DeepSeek max_tokens=16384 | 推理模型 reasoning_tokens 占 max_tokens，太小会截断（17×23 就花 59 reasoning tokens） | 实测发现 |
| 交叉验证暂不计 token | 第一次迭代只追正确性，token 优化是第二次迭代 | 用户决策 |
| 功能 pattern 检索留到第二次迭代 | 实现复杂度高，先靠错误签名匹配跑通闭环 | 用户决策 |
| optimize 先提取设计摘要再改（extract_design_brief） | AMD Phase 1：不给设计上下文，LLM 只给泛泛建议；"先提取设计文档，然后改进" | 用户决策 2026-07-18 |
| synth 修复先重验 csim 再 synth | 1 credit 比 4 credits 便宜；改 synth 可能破坏 correctness（§5） | 架构 v2.3 |
| 策略选择取第一个 | 第一次迭代固定启发式，LLM 倾向把最有把握的排最前；每轮重新 propose | 架构 v2.3 |
| 优化后 cosim 失败真回滚快照 | 原实现只记日志不恢复，会带死锁提交；快照含 code/level/latency/cosim_ok | 实测发现（代码评审） |

---

## 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-18 | v1.2。同步 v0.2.0 实现：§2 数据流的 optimize 段从"(P4)"改为真实链路（设计摘要缓存+策略+双闸门+重验+同级择优+真回滚）；§3 决策记录加 4 行（设计摘要提取/synth 先重验 csim/取首策略/真回滚）。对应 agent-architecture.md v2.3。 | Agent 主 |
| 2026-07-15 | v1.1。代码导览部分移至 agent/README.md（和代码放一起）。本文档保留跨模块设计分析+数据流+决策记录。 | Agent 主 |
| 2026-07-15 | v1 初稿。基于 P2 里程碑代码版本，详述所有模块的函数清单、耦合、数据流。 | Agent 主 |
