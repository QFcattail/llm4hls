# 脚本 (Scripts)

CLI 入口与驱动脚本。非 TUI 模式的命令行 driver。

## 文件结构

| 文件 | 职责 |
|---|---|
| `run_agent.py` | CLI driver：组装 agent 并跑端到端，输出转录 + 评分卡 |
| `test_main_loop.py` | 主循环离线单元测试（TC-AGENT-001~015），无 Vitis/LLM 可跑 |

## run_agent.py

模仿 harness 自带的 `contest/fpt26-harness/scripts/run_poc.py`，但用项目自己的 `agent.main_loop.Agent` 替代 `ReferenceAgent`。无 TUI，直接 print 转录 + 评分卡。

### 命令行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `task_dir`（位置必填） | - | 任务包目录 |
| `--backend` | `scripted` | LLM 后端：`scripted`（预设答案）/ `deepseek`（真 LLM）/ `openrouter`（官方） |
| `--budget` | 题目自带 | 覆盖 credit 预算（如 `--budget 10`） |
| `--work` | `runs/<task_id>` | 工作目录（存 build 产物 + 日志） |
| `--force` | 关 | 没装 Vitis 时强制运行（csim 会 compile_error，仅用于框架测试） |

### 组装 agent 的步骤

1. Vitis 守卫：检测 `vitis-run` 是否在 PATH，不在则尝试 source settings64.sh；仍不在且无 `--force` 则报错退出。
2. `load_task(task_dir)` -> `Budget(total)` -> `ToolServer(task, budget, work_root)`
3. backend 选择：`OpenRouterClient` / `DeepSeekClient` / `ScriptedClient`
4. `HLSLLMClient(backend)` + `KnowledgeBase(seed_entries())`（7 条种子条目，P2-12 扩充）
5. `Agent(task, server, llm, kb, run_dir=work_root)` -> `final = agent.run()`
6. 输出：`usage_summary()` -> transcript -> `budget.summary()` -> `grade(task, final)` 评分卡 -> 写 `final_<kernel_name>` 文件

### sys.path 注入

`ROOT`（项目根，for `agent`）+ `ROOT/contest/fpt26-harness`（for `llm4hls`）。

## 构建方法

```bash
# 真 Vitis + ScriptedClient（验证工具链，不花 token）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix

# 真 Vitis + DeepSeek（完整端到端，花 token）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek

# 离线框架测试（csim 会 compile_error）
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --force

# 主循环离线单元测试（不需要 Vitis / LLM API，改主循环后必跑）
python3 scripts/test_main_loop.py
```

## 已知坑点

- **无 Vitis 时 SCORE 恒 0.000**：没有 Vitis 时所有 csim/synth/cosim 返回 `compile_error`，SCORE 0.000，输出有误导性。driver 会检测并建议加 `--force`。
- **与 TUI 共享组装逻辑**：`run_agent.py` 和 `tui/app.py` 的 agent 组装步骤几乎相同（load_task->Budget->ToolServer->backend->HLSLLMClient->KnowledgeBase->Agent），差异仅在 TUI 用后台线程+事件队列，CLI 同步 print。
