# 运行产物 (Run Outputs)

> 本目录存放 agent 运行产生的产物。**已 gitignore，不入库**。每次运行覆盖同名子目录。

## 目录结构

每次运行 `scripts/run_agent.py` 或 `./run.sh`，会在 `runs/<task_id>/` 下生成：

```
runs/
└── <task_id>/                  如 projection_bugfix
    ├── final_<kernel>.cpp      agent 最终输出的 kernel 代码
    ├── <task_id>.jsonl         事件日志（JSONL，每行一个事件：route/tool_result/kb_search/checkpoint 等）
    ├── scores.jsonl            得分历史（每次评分追加一行：ts/score/latency/credits/tokens）
    ├── agent/                  agent 工作区
    │   ├── csim_1/             第 1 次 csim 的工作目录（kernel.cpp/.h/_tb.cpp/run_hls.tcl）
    │   ├── csim_2/             第 2 次 csim（修复后重跑）
    │   ├── synth_3/            第 3 次工具调用是 synth
    │   └── ...                 按工具调用序号排列
    └── grade/                  评分区
        ├── grade_csim/         hidden testbench csim
        ├── grade_synth_base/   baseline 综合
        └── grade_synth_cand/   candidate 综合（PPA 对比）
```

## 与 harness 自带 runs/ 的区分

| 目录 | 来源 | 用途 |
|---|---|---|
| `runs/`（项目根） | 本项目的 `agent.main_loop.Agent` 跑出来 | 验证我们的 agent |
| `contest/fpt26-harness/runs/` | harness 自带的 `ReferenceAgent` 跑出来 | 官方参考实现的基线对比 |

两者结构相似（都用 harness 的 ToolServer），但 agent 实现不同。做性能对比时注意区分来源。

---

## 日志阅读指南（怎么读一次运行）

### 一、先分清三种"日志"

| 日志 | 在哪 | 记什么 | 什么时候看 |
|---|---|---|---|
| **开发日志 dev-log** | `docs-development/dev-log/` | 每次开发会话做了什么、为什么、遇到什么问题 | 想知道"项目为什么长这样" |
| **事件日志 JSONL** | `runs/<task>/<task>.jsonl` | agent 一次运行里每个决策点的事件（**读运行的主日志**） | 想知道"这次跑得好不好、卡在哪" |
| **harness transcript** | 终端输出末尾 / `server.transcript` | 每次工具调用的计费流水（csim/synth/cosim + 花了多少 credit） | 想知道"预算花哪了" |

平时说"看日志"，90% 指第二种：事件日志 JSONL。下面讲的都是它。

### 二、JSONL 怎么读：事件类型速查（v0.6.0）

每行一个 JSON：`{"ts": 时间戳, "task": 题目id, "event": 事件名, ...}`。按一次完整运行的事件顺序：

| 顺序 | 事件 | 看什么 |
|---|---|---|
| 1 | `route` | 路由判定：task_type、correctness 关卡、initial_level、budget |
| 2 | `pre_csim_review` → `mechanical_review`/`review` → `pre_csim_fix_applied` 或 `pre_csim_no_change` | 免费静态体检：LLM 有没有在花 credit 前就发现问题 |
| 3 | `tool_result` (csim) | 第一次 csim：`ok` 过没过；没过看 `phase`（compile_error/runtime_fail）和 `log`（报错原文） |
| 4 | （失败时）`kb_search` → `mechanical_review` → `review` → 回到 3 | 修复循环：KB 有没有命中（`hits>0`）、双闸门过没过 |
| 5 | `checkpoint` (reason=correctness_gate) | **存档 Lv1**：correctness 达标，correct 分到手 |
| 6 | `phase_exit` (correctness, result=ok) | 阶段 1 结束 |
| 7 | `tool_result` (synth) + `checkpoint` (reason=synth_ok) | **存档 Lv2**：synth 分到手 + baseline latency |
| 8 | `phase_enter` (optimize) → `design_brief` | 优化开始：设计摘要提取（chars 长度） |
| 9 | `llm_call` (propose_strategies, count=N) → `llm_call` (select_strategies) → `strategy_select` | **策略决策**：提了几个策略、评审选了哪几个（`indices`/`picked`）、否决了谁（`rejected`）、是不是回退（`fallback`） |
| 10 | `llm_call` (apply_strategies) → `mechanical_review` → `review` | 生成 + 双闸门；`review verdict=reject` 说明 LLM 犯了 pragma 错被拦 |
| 11 | `tool_result` (csim+synth) | 候选重验 |
| 12 | `checkpoint` (reason=optimize_improve) | **变好**：`old_latency→new_latency`；连起来就是优化轨迹 |
| 13 | `optimize_discard` / `optimize_fallback` / `optimize_stop` | 候选丢弃原因 / 组合失败回退 / 收敛停止原因 |
| 14 | `cosim_recheck` | 最终 RTL 体检（best 变过且预算够才出现） |
| 15 | `submit` | 终态：`final_level`、`final_latency`、`credit_spent` |

其他可能出现：`budget_exhausted`（预算尽）、`rollback`（快照回滚，reason 看原因）、`repair_failed`（LLM 没产出可解析代码）、`env_error`（vitis-run 没找到）、`heartbeat`（10s 一条活性心跳，分析时可过滤掉）。

### 三、一个真实片段（dotProduct 满分 run，逐行注释）

```
route            task_type=optimize, budget=40          ← 路由：优化题，40 credits
pre_csim_fix_applied                                 ← 免费体检：LLM 直接优化了代码
tool_result      csim pass (10.1s)  [spent 1]         ← 第 1 个 credit
checkpoint       0→1 correctness_gate                  ← Lv1：correct 1.5 分到手
tool_result      synth pass latency=38 [spent 5]      ← Lv2：baseline 38 周期
phase_enter      optimize                              ← 优化开始
design_brief     chars=1386                            ← LLM 读懂了设计：串行累加是瓶颈
llm_call         propose_strategies count=3            ← 提了 3 个策略
strategy_select  indices=[0,1,2] picked=[三个全选]      ← 评审 AI 判断三策略可组合
mechanical_review passed=True                        ← 硬门过
review           verdict=pass                          ← LLM 复审过
tool_result      csim pass [spent 6]
tool_result      synth pass latency=37 [spent 10]
checkpoint       38→37 optimize_improve                ← 变好一点点，继续
strategy_select  indices=[0,2]（排除了策略1）            ← 第 2 轮：评审排除冲突策略
checkpoint       37→22 optimize_improve                ← 大幅变好
strategy_select  indices=[0]（保守单选）                 ← 第 3 轮：评审判断组合风险大
checkpoint       22→14 optimize_improve                ← 再变好
optimize_stop    reason=no_improvement                 ← 第 4 轮没变快，收敛停止
submit           final_level=2 final_latency=14         ← 交 14 周期的版本
```

读完能复述：免费体检先优化了一轮 → 基线 38 → 三轮三种选择（三组合/排他二组合/保守单选）→ 38→37→22→14 → 收敛。

### 四、实用命令（服务器上）

```bash
cd /home/admin/fpga-agent

# 实时跟踪一次运行（去掉 10s 一条的心跳）
tail -f runs/dotProduct_optimize/dotProduct_optimize.jsonl | grep -v heartbeat

# 只看决策类事件（一次运行的"故事线"）
grep -v heartbeat runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  grep -E 'route|checkpoint|strategy_select|optimize_|rollback|submit'

# 用 jq 提取优化轨迹（old→new latency）
grep checkpoint runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  jq -r 'select(.reason=="optimize_improve") | "\(.old_latency)→\(.new_latency)"'

# 看评审 AI 每次怎么选的（含否决理由）
grep strategy_select runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  jq -c '{round, indices, rejected: [.rejected[]?.name], fallback}'

# 看这次运行报了哪些错（含工具报错原文）
grep tool_result runs/dotProduct_optimize/dotProduct_optimize.jsonl | \
  jq -r 'select(.ok==false) | "\(.kind) \(.phase): \(.log[:200])"'
```

### 五、30 秒判断一次运行好不好

1. **checkpoint 序列**：0→1→2 都有吗？缺 1 = correctness 没过；缺 2 = synth 没过
2. **latency 轨迹**：`optimize_improve` 事件的 new_latency 在降吗？一次都没有 = 优化没产出
3. **credit 花费 vs 预算**：`submit.credit_spent` 接近预算 = 挣扎；远小于 = 顺利
4. **strategy_select 的 fallback**：出现 `fallback=true` = 评审 AI 输出没解析出来（要查）
5. **rollback 事件**：出现了说明优化引入了真问题被回滚（机制在工作，但要查为什么）

## 事件日志字段（简表，详细见上方指南）

| 事件类型 | 含义 |
|---|---|
| `route` | 路由结果（task_type -> 关卡路径） |
| `tool_result` | 工具调用结果（kind=csim/synth/cosim, phase, credit_spent） |
| `kb_search` | 知识库检索（query, hits） |
| `review` / `mechanical_review` | LLM 复审 / 机械硬门 |
| `llm_call` | LLM 调用（purpose=extract_brief/propose_strategies/select_strategies/apply_strategies） |
| `strategy_select` | 评审 AI 选择（indices/picked/rejected/fallback） |
| `checkpoint` | 存档变更（level, latency） |
| `submit` | 最终提交 |

## 状态

- `runs/projection_bugfix/`：projection 题端到端真修复（SCORE 1.400）
- `runs/dotProduct_optimize/`：optimize 循环满分（SCORE 3.000，73.36×）
- `runs/residual_stream_deadlock/`：structural 题（最高 SCORE 4.000，lat=6）
