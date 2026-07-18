# 运行产物 (Run Outputs)

> 本目录存放 agent 运行产生的产物。**已 gitignore，不入库**。每次运行覆盖同名子目录。

## 目录结构

每次运行 `scripts/run_agent.py` 或 `./run.sh`，会在 `runs/<task_id>/` 下生成：

```
runs/
└── <task_id>/                  如 projection_bugfix
    ├── final_<kernel>.cpp      agent 最终输出的 kernel 代码
    ├── <task_id>.jsonl         事件日志（JSONL，每行一个事件：route/tool_result/kb_search/checkpoint 等）
    ├── agent/                  agent 工作区
    │   ├── csim_1/             第 1 次 csim 的工作目录（kernel.cpp/.h/_tb.cpp/run_hls.tcl）
    │   ├── csim_2/             第 2 次 csim（修复后重跑）
    │   └── ...                 最多到 csim_N（N=max_rounds）
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

## 事件日志字段

`<task_id>.jsonl` 每行一个 JSON 事件，常见字段：

| 事件类型 | 含义 |
|---|---|
| `route` | 路由结果（task_type -> 关卡路径） |
| `tool_result` | 工具调用结果（kind=csim/synth/cosim, phase, credit_spent） |
| `kb_search` | 知识库检索（query, hits） |
| `review` | LLM review 结果（accepted/rejected） |
| `mechanical_review` | 机械检查结果 |
| `checkpoint` | 存档变更（level, latency） |
| `submit` | 最终提交 |

## 状态

- `runs/projection_bugfix/`：projection 题端到端真修复的运行产物（DeepSeek + 真 Vitis，SCORE 1.400）。
