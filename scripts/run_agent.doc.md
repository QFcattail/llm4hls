# scripts/run_agent.py 说明文档

## 中文说明

### 用途
CLI 驱动脚本：在给定 credit 预算下用本项目的 Agent 端到端跑一个任务，完成后对隐藏测试台与 PPA 进行评分并输出报告卡。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `_check_vitis_available() -> bool` | function | 检查 `vitis-run` 是否在 PATH 上 |
| `_auto_source_vitis() -> bool` | function | 尝试在已知路径 source `settings64.sh` 并更新 `os.environ["PATH"]`，返回此后 vitis-run 是否可用 |
| `main() -> int` | function | argparse 解析参数，校验 Vitis，加载任务、构造 Budget/ToolServer/后端/HLSLLMClient/KnowledgeBase，实例化 `Agent` 并 `run()`，打印 transcript 与评分卡 |

### 导出
无 `__all__`；作为脚本运行（`if __name__ == "__main__": raise SystemExit(main())`）。

### 依赖
- 内部依赖：`agent.knowledge_base.KnowledgeBase`、`agent.llm_client.HLSLLMClient`、`agent.main_loop.Agent`、`agent.deepseek_client.DeepSeekClient`
- 外部依赖：harness 包 `llm4hls`（`Budget`/`ToolServer`/`grade`/`load_task`、`llm4hls.llm.OpenRouterClient`/`ScriptedClient`）；标准库 `argparse`/`os`/`sys`/`pathlib`/`shutil`/`subprocess`

### 关键设计点
1. **Vitis 守卫**：无 Vitis 时所有 csim/synth/cosim 都会返回 `compile_error`，产生误导性的 SCORE 0.000；故先自动 source，仍不可用且无 `--force` 时直接报错退出。
2. **多后端选择**：`openrouter` 用 `OpenRouterClient`，`deepseek` 用 `DeepSeekClient`，`scripted` 用 `ScriptedClient`（需任务带 `reference/`，回放参考解）。
3. **`scripted` 后端**：把 `task.reference_code` 包成 ```` ```cpp ``` ```` 单条消息喂给 `ScriptedClient`，用于离线回放。

### 命令行参数
`task_dir`（位置参数）、`--backend {scripted,openrouter,deepseek}`（默认 scripted）、`--budget`、`--work`、`--force`、`--token-mode {full,balanced,aggressive}`（v0.7.0，默认 full=不限制不优化；graded 模式给判定类调用关 thinking 省 token）

---

## English

### Purpose
CLI driver script: runs the project's Agent end-to-end on a task under a credit budget, then grades against the hidden testbench and PPA and prints a report card.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `_check_vitis_available() -> bool` | function | Checks whether `vitis-run` is on PATH |
| `_auto_source_vitis() -> bool` | function | Tries sourcing `settings64.sh` at known paths and updating `os.environ["PATH"]`; returns whether vitis-run is available afterwards |
| `main() -> int` | function | argparse parsing, Vitis guard, loads task and builds Budget/ToolServer/backend/HLSLLMClient/KnowledgeBase, instantiates `Agent`, runs it, prints transcript and grading card |

### Exports
No `__all__`; runs as a script (`if __name__ == "__main__": raise SystemExit(main())`).

### Dependencies
- Internal: `agent.knowledge_base.KnowledgeBase`, `agent.llm_client.HLSLLMClient`, `agent.main_loop.Agent`, `agent.deepseek_client.DeepSeekClient`
- External: harness package `llm4hls` (`Budget`/`ToolServer`/`grade`/`load_task`, `llm4hls.llm.OpenRouterClient`/`ScriptedClient`); stdlib `argparse`/`os`/`sys`/`pathlib`/`shutil`/`subprocess`

### Key Design Points
1. **Vitis guard**: without Vitis every csim/synth/cosim returns `compile_error`, producing misleading SCORE 0.000; so it auto-sources first and errors out if still unavailable and no `--force`.
2. **Multi-backend selection**: `openrouter` uses `OpenRouterClient`, `deepseek` uses `DeepSeekClient`, `scripted` uses `ScriptedClient` (requires a `reference/` solution and replays it).
3. **`scripted` backend**: wraps `task.reference_code` as a single ```` ```cpp ``` ```` message fed to `ScriptedClient` for offline replay.

### CLI Args
`task_dir` (positional), `--backend {scripted,openrouter,deepseek}` (default scripted), `--budget`, `--work`, `--force`, `--token-mode {full,balanced,aggressive}` (v0.7.0, default full = unrestricted/unoptimized; graded modes disable thinking for verdict-class calls to save tokens)
