# tui/task_picker.py 说明文档

## 中文说明

### 用途
交互式任务选择界面（Textual Screen），扫描 harness `tasks/` 目录下的任务包并列表展示，同时接受用户手动输入的自定义任务路径。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| scan_tasks(root) | function | 扫描目录下含 `task.toml` 的子目录，返回 `[{id,type,difficulty,budget,path,requires_cosim}]`；解析失败或不存在则跳过/返回空 |
| TaskPickerScreen | class(Screen) | 任务选择屏：ListView 列出已发现任务 + Input 接受自定义路径 |
| TaskPickerScreen.selected | property | 返回选中的任务 dict，或 None（自定义路径类型时也为 None） |
| TaskPickerScreen.compose() | method | 产出 Header + Vertical(Label/ListView/Label/Input) + Footer |
| TaskPickerScreen.on_mount() | method | 调 `scan_tasks` 加载任务，逐条 `lv.append(ListItem(Label(label), name=path))`；无任务时显示提示 |
| TaskPickerScreen.on_list_view_selected(event) | method | 列表选中（Enter）时记录 `_selected` 并 `pop_screen()` |
| TaskPickerScreen.on_input_submitted(event) | method | 自定义路径提交：校验 `task.toml` 存在后解析并 `pop_screen()`，否则清空输入并显示红色错误提示 |
| TaskPickerScreen.action_request_quit() | method | `q`/Esc 直接退出 App（此时 agent 尚未启动） |

### 导出
本模块**无** `__all__`；`TaskPickerScreen` 与 `scan_tasks` 需直接 `from tui.task_picker import TaskPickerScreen, scan_tasks` 导入，且不在 `tui/__init__.py` 的导出中。

### 依赖
- 内部依赖：无（独立 Screen，不依赖其他 tui widget）
- 外部依赖：标准库 `pathlib`、`tomllib`（运行时局部导入）；`textual`（ComposeResult/Vertical/Screen/Header/Footer/Label/ListView/ListItem/Input/Binding）

### 关键设计点
1. **两种选择方式**：从列表用方向键 + Enter 选择已发现任务，或在输入框直接键入自定义路径 + Enter；两者都通过 `pop_screen()` 把结果交回上层（`selected` 属性读取）。
2. **宽容解析**：`scan_tasks` 对每个 `task.toml` 用 try/except 包裹，解析失败的任务被静默跳过，保证一个坏 task 不影响整个列表加载；字段缺失时回退到目录名或 `"?"`。
3. **cosim 标签**：列表项对 `requires_cosim=True` 的任务追加 ` [cosim]` 标签，便于识别需要协同仿真的任务。
4. **agent 未启动即可退出**：`action_request_quit` 直接 `app.exit()`，无需退出确认（与 `app.py` 中运行时的 `QuitConfirmScreen` 不同）。

---

## English

### Purpose
Interactive task-selection screen (Textual Screen): scans the harness `tasks/` directory for task packages, lists them, and also accepts a custom task path typed by the user.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| scan_tasks(root) | function | Scans subdirectories containing `task.toml`; returns `[{id,type,difficulty,budget,path,requires_cosim}]`; skips/returns empty on parse failure or missing dir |
| TaskPickerScreen | class(Screen) | Task picker screen: a ListView of discovered tasks + an Input for a custom path |
| TaskPickerScreen.selected | property | Returns the selected task dict, or None (also None for custom-path selection) |
| TaskPickerScreen.compose() | method | Yields Header + Vertical(Label/ListView/Label/Input) + Footer |
| TaskPickerScreen.on_mount() | method | Calls `scan_tasks` to load tasks, appends each via `lv.append(ListItem(Label(label), name=path))`; shows a hint when no tasks found |
| TaskPickerScreen.on_list_view_selected(event) | method | On list selection (Enter), records `_selected` and calls `pop_screen()` |
| TaskPickerScreen.on_input_submitted(event) | method | On custom-path submit: validates `task.toml` exists, parses it, then `pop_screen()`; otherwise clears the input and shows a red error hint |
| TaskPickerScreen.action_request_quit() | method | `q`/Esc exits the App directly (the agent has not started yet) |

### Exports
This module has **no** `__all__`; import `TaskPickerScreen` and `scan_tasks` directly via `from tui.task_picker import TaskPickerScreen, scan_tasks`. They are not re-exported by `tui/__init__.py`.

### Dependencies
- Internal: none (standalone Screen; does not depend on other tui widgets)
- External: stdlib `pathlib`, `tomllib` (runtime local import); `textual` (ComposeResult/Vertical/Screen/Header/Footer/Label/ListView/ListItem/Input/Binding)

### Key Design Points
1. **Two selection methods**: pick a discovered task with arrow keys + Enter from the list, or type a custom path + Enter in the input; both call `pop_screen()` to hand the result back (read via the `selected` property).
2. **Tolerant parsing**: `scan_tasks` wraps each `task.toml` in try/except so a parse failure for one task is silently skipped without breaking the whole list; missing fields fall back to the directory name or `"?"`.
3. **cosim tag**: list items append ` [cosim]` for tasks with `requires_cosim=True` so cosim-requiring tasks are easy to spot.
4. **Quit allowed before agent starts**: `action_request_quit` calls `app.exit()` directly with no confirmation (unlike the runtime `QuitConfirmScreen` in `app.py`).
