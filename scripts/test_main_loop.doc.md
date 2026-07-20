# scripts/test_main_loop.py 说明文档

## 中文说明

### 用途
agent 主循环的离线单元测试（TC-AGENT-001 ~ TC-AGENT-016），用例编号对齐 `docs-development/test-plan/README.md` 规范。本机无 Vitis、无 LLM API 也能跑：FakeToolServer 按规则回放 ToolResult（计费走真 harness Budget），CannedBackend 按 prompt 内容分发预设答案驱动 HLSLLMClient。钉住 v2.3/v2.4/v0.5~v0.7 三阶段语义，防止回归。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `FakeTask` | dataclass | 最小 Task 替身，覆盖 agent 链路触及的字段（id/type/requires_cosim/kernel_code/top/headers/budget 等） |
| `FakeToolServer` | class | 规则化工具替身：csim 遇 `BREAK_CSIM` 标记失败；synth/cosim 委托给每测例的 handler 闭包；内部走真 `Budget.charge` |
| `CannedBackend` | class | 按 prompt 嗅探的 LLM 后端：brief/策略/review/select 固定答案（`select_pick` 控制评审 AI 选的编号）；repair 与 apply_strategies 从每测例代码队列循环取答 |
| `_KwBackend` | class | kwargs 记录后端（TC-016）：按调用点记录 complete() 收到的关键字参数，验证 token-mode 策略 |
| `tc_001` ~ `tc_016` | function | 十六个测例（见下表） |
| `main() -> int` | function | 跑全部测例，全过返回 0 |

### 测例一览（对应架构章节）
| 用例 | 验什么 | 架构 |
|---|---|---|
| TC-AGENT-001 | synth 首败 -> 修复循环（先重验 csim）-> synth 过 -> Lv2，且 synth 错误签名命中 KB | §4.3 |
| TC-AGENT-002 | optimize 接受更快候选（100->60），次轮无改进停止；strategy_select 事件字段供 TUI | §4.4 + §2 规则 2 |
| TC-AGENT-003 | optimize 候选破坏 csim -> discard，best 不动；单策略失败即停（v2.4 fail-fast） | §4.4 + §5 |
| TC-AGENT-004 | structural：优化后 cosim 回验失败 -> 真回滚快照（code+latency 全恢复） | §4.5 |
| TC-AGENT-005 | 种子 KB 检索：错误码/关键词探针命中预期条目 | §6.3 |
| TC-AGENT-006 | latency=0 防御：零 latency 候选不进存档 | §4.3 要点 |
| TC-AGENT-007 | v2.4：评审 AI 选兼容策略对（1+2）-> 组合候选接受（100->55），无 fallback | §4.4 双重确认 |
| TC-AGENT-008 | v2.4：组合失败 -> optimize_fallback -> 首策略单试接受（100->70） | §4.4 组合归因 |
| TC-AGENT-009 | v2.4 TUI：ToolErrorBar 策略面板与工具错误共存；150ms 心跳 show_running 擦不掉策略行 | tui-design §3.2 |
| TC-AGENT-010 | 真机暴露的策略解析器：markdown 标题 + 无冒号字段标签 + 非策略块过滤 | §4.4 解析 |
| TC-AGENT-011 | 得分历史：record/recent(5)/format/损坏文件安全 | §3.6 |
| TC-AGENT-012 | JSON select：pick+rejected 解析；回退行为正常 | §4.4 v0.5 |
| TC-AGENT-013 | 回退 apply 注入失败反馈（HLS 207-6969） | §4.4 v0.5 |
| TC-AGENT-014 | selector：解析失败重试一次；回退带 fallback 标记不静默 | §4.4 v0.5 |
| TC-AGENT-015 | 非 structural 题最终 RTL 体检失败 -> 快照回滚 | §4.5 v0.6 |
| TC-AGENT-016 | token-mode 策略：full 无覆盖（旧行为逐字节）/ graded 模式 effort=off / aggressive 裁 select spec 块 / 无旋钮后端 TypeError 回退 / 未知模式拒绝 | P4-03 v0.7 |

### 导出
无 `__all__`；作为脚本直接执行：`python3 scripts/test_main_loop.py`。

### 依赖
- 内部依赖：`agent.main_loop.Agent`、`agent.llm_client.HLSLLMClient`、`agent.knowledge_base`
- 外部依赖：harness `llm4hls.budget.Budget` / `llm4hls.report.SynthReport` / `llm4hls.tools.ToolResult`（仅数据结构，不调 Vitis）

### 关键设计点
1. **sys.path 注入**：与 run_agent.py 同款（ROOT + contest/fpt26-harness），本机直接可跑。
2. **真 Budget 计费**：FakeToolServer 在方法内 `charge`，与真 ToolServer 一致，BudgetExceeded 路径也被覆盖。
3. **机械检查兼容**：所有预设代码片段共享同一顶层签名且含 `#include "dotProduct.h"`，保证 `mechanical_review` 放行，测的是主循环逻辑而非闸门。
4. **日志落临时目录**：每测例 `tempfile.mkdtemp`，不污染 runs/。

---

## English

### Purpose
Offline unit tests for the agent main loop (TC-AGENT-001 ~ TC-AGENT-016), numbered per `docs-development/test-plan/README.md`. Runs on machines without Vitis or an LLM API: FakeToolServer replays rule-based ToolResults against a real harness Budget, and a prompt-sniffing CannedBackend drives HLSLLMClient. Pins the v2.3/v2.4/v0.5~v0.7 three-stage semantics against regressions.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `FakeTask` | dataclass | Minimal Task stand-in covering every field the agent stack touches (id/type/requires_cosim/kernel_code/top/headers/budget, etc.) |
| `FakeToolServer` | class | Rule-based tool stand-in: csim fails on the `BREAK_CSIM` marker; synth/cosim delegate to per-test handler closures; charges a real `Budget` |
| `CannedBackend` | class | Prompt-sniffing LLM backend: fixed brief/strategy/review/select answers (`select_pick` controls the selector AI's pick); repair and apply_strategies cycle through per-test code queues |
| `_KwBackend` | class | Kwargs-recording backend (TC-016): records the keyword arguments each call site receives, verifying the token-mode policy |
| `tc_001` ~ `tc_016` | function | The sixteen test cases (table below) |
| `main() -> int` | function | Runs all cases; returns 0 iff all pass |

### Test Cases (mapped to architecture sections)
| Case | What it verifies | Architecture |
|---|---|---|
| TC-AGENT-001 | Synth fails once -> repair loop (csim re-verified first) -> synth passes -> Lv2, with a KB hit on the synth error signature | §4.3 |
| TC-AGENT-002 | Optimize accepts the faster candidate (100->60), then stops on no improvement; strategy_select event fields feed the TUI | §4.4 + §2 rule 2 |
| TC-AGENT-003 | Optimize discards a candidate that breaks csim; best untouched; single-strategy failure stops the loop (v2.4 fail-fast) | §4.4 + §5 |
| TC-AGENT-004 | Structural: post-optimization cosim re-check fails -> real snapshot rollback (code+latency restored) | §4.5 |
| TC-AGENT-005 | Seed KB retrieval: error-code/keyword probes hit the intended entries | §6.3 |
| TC-AGENT-006 | Latency=0 guard: a zero-latency candidate never enters the archive | §4.3 notes |
| TC-AGENT-007 | v2.4: selector picks a compatible PAIR (1+2) -> combined candidate accepted (100->55), no fallback | §4.4 dual confirmation |
| TC-AGENT-008 | v2.4: combo fails -> optimize_fallback -> first strategy alone accepted (100->70) | §4.4 combo attribution |
| TC-AGENT-009 | v2.4 TUI: ToolErrorBar strategy panel coexists with tool errors; the 150ms show_running heartbeat cannot wipe it | tui-design §3.2 |
| TC-AGENT-010 | Real-machine strategy parser fixes: markdown headings + colon-less field labels + non-strategy block filtering | §4.4 parsing |
| TC-AGENT-011 | Score history: record/recent(5)/format/corrupt-file safety | §3.6 |
| TC-AGENT-012 | JSON select: pick+rejected parsed; fallback behaves | §4.4 v0.5 |
| TC-AGENT-013 | Fallback apply receives failure feedback (HLS 207-6969) | §4.4 v0.5 |
| TC-AGENT-014 | Selector: one retry on parse failure; fallback flagged, never silent | §4.4 v0.5 |
| TC-AGENT-015 | Non-structural final RTL re-check failure -> snapshot rollback | §4.5 v0.6 |
| TC-AGENT-016 | Token-mode policy: full sends no overrides (byte-identical legacy) / graded modes effort=off / aggressive trims the select spec block / no-knob backend TypeError fallback / unknown mode rejected | P4-03 v0.7 |

### Exports
No `__all__`; run directly: `python3 scripts/test_main_loop.py`.

### Dependencies
- Internal: `agent.main_loop.Agent`, `agent.llm_client.HLSLLMClient`, `agent.knowledge_base`
- External: harness `llm4hls.budget.Budget` / `llm4hls.report.SynthReport` / `llm4hls.tools.ToolResult` (data structures only; no Vitis invoked)

### Key Design Points
1. **sys.path injection**: same pattern as run_agent.py (ROOT + contest/fpt26-harness), runnable anywhere.
2. **Real Budget metering**: FakeToolServer charges inside its methods like the real ToolServer, so the BudgetExceeded path is covered too.
3. **Mechanical-check compatible**: every canned code snippet shares the same top-level signature and includes `dotProduct.h`, so `mechanical_review` passes and the tests exercise loop logic, not the gates.
4. **Logs to temp dirs**: each case uses `tempfile.mkdtemp`, keeping runs/ clean.
