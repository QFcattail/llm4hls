# tui/app.py 说明文档

## 中文说明

### 用途
Textual TUI 主入口，组装三个区域 widget（流程图 / 工具错误栏 / 当前活动 / 状态栏），在后台线程运行 agent，通过内存事件队列以 150ms 轮询刷新 UI。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| FPGA_LIGHT_THEME | Theme | 自定义浅色主题 `fpga-light`（v3 新增，规格见设计文档 §3.5）：primary `#587559`、accent/装饰 `#FDD100`、白底黑字；`__init__` 里 `register_theme()` + `self.theme` 启用 |
| QuitConfirmScreen | class(ModalScreen) | 退出确认对话框，`q` 不立即退出而是弹出此屏（y/Enter 确认，n/Esc 取消） |
| AgentDashboard | class(App) | 主仪表盘 App，组装布局、启动 agent 线程、轮询事件并刷新各 widget |
| AgentDashboard.compose | method | 产出 Header + Vertical(FlowChart/ToolErrorBar/ActivityPanel/StatusBar) + Footer |
| AgentDashboard.on_mount | method | 启动 agent 后台线程 + `set_interval(0.15, _poll_events)` |
| AgentDashboard._run_agent | method | 后台线程内构造 Agent（加载 task、Budget、ToolServer、LLM backend、KnowledgeBase），劫持 `log.event` 与 `hb.set_stage` 把事件/心跳入队 |
| AgentDashboard._poll_events | method | 每 150ms 抽空事件队列并调用 `_handle_event`，随后 `_refresh_ui`；整体包了 `NoMatches` 兜底，丢弃关闭过程中最后一拍 |
| AgentDashboard._handle_event | method | 分发 init/event/stream/heartbeat/done/error 六类事件 |
| AgentDashboard._handle_agent_event | method | 处理 route/phase_enter/phase_exit/tool_result/review/mechanical_review/checkpoint/submit 等日志事件，更新各 widget |
| AgentDashboard._handle_stream | method | 处理 LLM 流式 token，注入"上次工具结果"上下文后写入 ActivityPanel |
| AgentDashboard._refresh_ui | method | 刷新 ActivityPanel 渲染、ToolErrorBar 实时计时、StatusBar 全量状态 |
| run_tui(task_path, backend, budget) | function | 入口：构造 AgentDashboard 并 `.run()` |

### 导出
- `FPGA_LIGHT_THEME`、`QuitConfirmScreen`、`AgentDashboard`（模块级 class/常量）
- `run_tui(task_path, backend="deepseek", budget=None)`（公开入口函数）

### 依赖
- 内部依赖：`.flow_chart.FlowChart`、`.activity_panel.ActivityPanel`、`.status_bar.StatusBar`、`.tool_error_bar.ToolErrorBar`、`.task_picker.TaskPickerScreen`/`scan_tasks`；运行时动态导入 `llm4hls`（Budget/ToolServer/load_task）、`agent.main_loop.Agent`、`agent.llm_client.HLSLLMClient`、`agent.knowledge_base.KnowledgeBase`、`agent.deepseek_client.DeepSeekClient`、`llm4hls.llm.OpenRouterClient`/`ScriptedClient`
- 外部依赖：标准库 `queue`/`threading`/`time`/`pathlib`；`textual`（App/ComposeResult/Vertical/Header/Footer/Binding/ModalScreen/Label/Button/Horizontal/Screen/Theme/css.query.NoMatches）

### 关键设计点
1. **agent 在后台线程、UI 在主线程**：`_run_agent` 在 daemon 线程跑 agent，通过 `queue.Queue` 把事件/心跳/流式 token 传给 UI 线程，UI 以 150ms 轮询消费，避免阻塞 Textual 事件循环。
2. **劫持而非侵入**：用 `queued_event`/`queued_hb` 包装 `agent.log.event` 和 `agent.hb.set_stage`，原方法仍被调用（保持 JSONL 日志不变），同时把副本入队——符合设计文档"TUI 是观察者，不改 agent 逻辑"的原则。
3. **多 backend 支持**：`backend` 参数支持 `deepseek`（stream 回调）、`openrouter`、`scripted`（用 reference_code 回放），状态栏的 token 统计从 backend 实例的 `total_prompt/completion/reasoning/calls` 属性读取。
4. **q 退出确认**：按 `q` 弹出 `QuitConfirmScreen`，确认后退出 TUI 但 agent 作为 daemon 线程继续在后台运行。
5. **浅色主题（v3）**：`FPGA_LIGHT_THEME` 在 `__init__` 注册并启用，四个区域边框统一用 `$accent`（金色装饰），退出对话框边框用 `$primary`；界面文案全英文。
6. **版本号显示**：Header 显示的是 `app.title`，`Header(name=...)` 只是 DOM 节点名——版本号必须通过 `self.title = f"FPGA Agent Dashboard v{APP_VERSION}"` 设置（规范 §11.3）。
7. **关闭竞态兜底**：150ms 轮询定时器可能在关闭卸载 widget 后再触发一拍，`query_one` 会抛 `NoMatches`；`_poll_events` 整体捕获后丢弃该拍，避免退出时打 traceback。

---

## English

### Purpose
Main Textual TUI entry point: assembles the four region widgets (flow chart / tool error bar / activity panel / status bar), runs the agent in a background thread, and refreshes the UI by polling an in-memory event queue every 150ms.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| FPGA_LIGHT_THEME | Theme | Custom light theme `fpga-light` (added in v3, spec in design doc §3.5): primary `#587559`, accent/decoration `#FDD100`, white background with black text; enabled in `__init__` via `register_theme()` + `self.theme` |
| QuitConfirmScreen | class(ModalScreen) | Quit confirmation dialog; `q` pushes this screen rather than quitting instantly (y/Enter confirm, n/Esc cancel) |
| AgentDashboard | class(App) | Main dashboard App: assembles layout, starts agent thread, polls events and refreshes widgets |
| AgentDashboard.compose | method | Yields Header + Vertical(FlowChart/ToolErrorBar/ActivityPanel/StatusBar) + Footer |
| AgentDashboard.on_mount | method | Starts agent background thread + `set_interval(0.15, _poll_events)` |
| AgentDashboard._run_agent | method | In background thread builds the Agent (load_task, Budget, ToolServer, LLM backend, KnowledgeBase) and wraps `log.event`/`hb.set_stage` to enqueue events/heartbeats |
| AgentDashboard._poll_events | method | Every 150ms drains the queue calling `_handle_event`, then `_refresh_ui`; wrapped in a `NoMatches` guard that drops the final tick during shutdown |
| AgentDashboard._handle_event | method | Dispatches six event kinds: init/event/stream/heartbeat/done/error |
| AgentDashboard._handle_agent_event | method | Handles log events (route/phase_enter/phase_exit/tool_result/review/mechanical_review/checkpoint/submit) and updates widgets |
| AgentDashboard._handle_stream | method | Handles LLM streaming tokens, injects last tool result context, writes to ActivityPanel |
| AgentDashboard._refresh_ui | method | Refreshes ActivityPanel render, ToolErrorBar live timer, and full StatusBar state |
| run_tui(task_path, backend, budget) | function | Entry point: builds AgentDashboard and calls `.run()` |

### Exports
- `FPGA_LIGHT_THEME`, `QuitConfirmScreen`, `AgentDashboard` (module-level classes/constant)
- `run_tui(task_path, backend="deepseek", budget=None)` (public entry function)

### Dependencies
- Internal: `.flow_chart.FlowChart`, `.activity_panel.ActivityPanel`, `.status_bar.StatusBar`, `.tool_error_bar.ToolErrorBar`, `.task_picker.TaskPickerScreen`/`scan_tasks`; runtime dynamic imports of `llm4hls` (Budget/ToolServer/load_task), `agent.main_loop.Agent`, `agent.llm_client.HLSLLMClient`, `agent.knowledge_base.KnowledgeBase`, `agent.deepseek_client.DeepSeekClient`, `llm4hls.llm.OpenRouterClient`/`ScriptedClient`
- External: stdlib `queue`/`threading`/`time`/`pathlib`; `textual` (App/ComposeResult/Vertical/Header/Footer/Binding/ModalScreen/Label/Button/Horizontal/Screen/Theme/css.query.NoMatches)

### Key Design Points
1. **Agent in background thread, UI in main thread**: `_run_agent` runs the agent in a daemon thread and passes events/heartbeats/streaming tokens to the UI thread via a `queue.Queue`; the UI polls every 150ms to avoid blocking Textual's event loop.
2. **Wrapping, not intrusion**: `queued_event`/`queued_hb` wrap `agent.log.event` and `agent.hb.set_stage` - the originals are still called (JSONL logging unchanged) while a copy is enqueued, honoring the design-doc principle that the TUI is an observer that does not modify agent logic.
3. **Multi-backend support**: `backend` accepts `deepseek` (stream callback), `openrouter`, and `scripted` (replays reference_code); the status bar reads token stats from the backend instance's `total_prompt/completion/reasoning/calls` attributes.
4. **Quit confirmation**: `q` pushes `QuitConfirmScreen`; on confirm the TUI exits but the agent keeps running in the background as a daemon thread.
5. **Light theme (v3)**: `FPGA_LIGHT_THEME` is registered and enabled in `__init__`; all four region borders use `$accent` (gold decoration) and the quit-dialog border uses `$primary`; all UI text is English.
6. **Version display**: the Header renders `app.title` - `Header(name=...)` is only the DOM node name, so the version must be set via `self.title = f"FPGA Agent Dashboard v{APP_VERSION}"` (conventions §11.3).
7. **Shutdown race guard**: the 150ms poll timer can fire once more while shutdown unmounts the widgets, making `query_one` raise `NoMatches`; `_poll_events` catches it and drops that tick instead of printing a traceback on exit.
