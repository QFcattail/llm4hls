# fpga-agent.py 说明文档

## 中文说明

### 用途
FPGA Agent 的一行启动入口：解析命令行参数、自动配置 Vitis 环境，然后进入交互式选题器或直接启动 TUI 仪表盘（也可用 `--no-tui` 走纯 CLI 模式）。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `_pick_task_interactive() -> str \| None` | function | 扫描 `contest/fpt26-harness/tasks/` 下含 `task.toml` 的目录，用纯 print+input 列出任务供用户编号选择，或接受自定义路径；返回任务目录路径或 None |
| `main() -> int` | function | argparse 解析参数，自动 source Vitis settings64.sh，按 `--no-tui` 委托给 `scripts/run_agent.py` 或调用 `tui.app.run_tui()` |

### 导出
无 `__all__`；作为脚本直接运行（`if __name__ == "__main__": raise SystemExit(main())`）。

### 依赖
- 内部依赖：`tui.app.run_tui`（TUI 模式）、`scripts/run_agent.py`（`--no-tui` 模式经 subprocess 调用）
- 外部依赖：标准库 `argparse`/`os`/`sys`/`pathlib`/`shutil`/`subprocess`/`tomllib`；harness 路径 `contest/fpt26-harness` 加入 `sys.path`

### 关键设计点
1. **避免双 Textual 实例**：选题器刻意用纯 `print`+`input` 而非 Textual，因为同一进程跑两个 Textual App 会导致黑屏。
2. **Vitis 自动 source**：若 `vitis-run` 不在 PATH，尝试候选路径 `settings64.sh`，源入后设置 `PATH` 与 `LLM4HLS_VITIS_HLS_ROOT`；失败则报错退出（除非 `--force`）。
3. **两种执行路径**：`--task` 跳过选题器直进 TUI；`--no-tui` 则用 `subprocess.call` 启动 `run_agent.py`。
4. **--token-mode（v0.7.0）**：`{full,balanced,aggressive}`，默认 full（不限制不优化）；TUI 路径透传 `run_tui(token_mode=...)`，`--no-tui` 路径透传给 run_agent.py。

---

## English

### Purpose
One-line entry point for FPGA Agent: parses CLI args, auto-configures the Vitis environment, then enters an interactive task picker or launches the TUI dashboard directly (or runs plain CLI mode via `--no-tui`).

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `_pick_task_interactive() -> str \| None` | function | Scans `contest/fpt26-harness/tasks/` for dirs with `task.toml`, lists them via plain print+input for numbered selection or a custom path; returns the task dir path or None |
| `main() -> int` | function | argparse parsing, auto-sources Vitis settings64.sh, delegates to `scripts/run_agent.py` in `--no-tui` mode or calls `tui.app.run_tui()` |

### Exports
No `__all__`; runs as a script (`if __name__ == "__main__": raise SystemExit(main())`).

### Dependencies
- Internal: `tui.app.run_tui` (TUI mode), `scripts/run_agent.py` (invoked via subprocess in `--no-tui` mode)
- External: stdlib `argparse`/`os`/`sys`/`pathlib`/`shutil`/`subprocess`/`tomllib`; harness path `contest/fpt26-harness` added to `sys.path`

### Key Design Points
1. **Avoid dual Textual instances**: the picker deliberately uses plain `print`+`input` instead of Textual, since running two Textual Apps in one process causes a black screen.
2. **Auto-source Vitis**: if `vitis-run` is not on PATH, candidate `settings64.sh` paths are tried; on success `PATH` and `LLM4HLS_VITIS_HLS_ROOT` are set, otherwise it errors out (unless `--force`).
3. **Two execution paths**: `--task` skips the picker and enters TUI directly; `--no-tui` launches `run_agent.py` via `subprocess.call`.
4. **--token-mode (v0.7.0)**: `{full,balanced,aggressive}`, default full (unrestricted/unoptimized); forwarded as `run_tui(token_mode=...)` on the TUI path and to run_agent.py on the `--no-tui` path.
