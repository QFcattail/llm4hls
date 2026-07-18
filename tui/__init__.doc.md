# tui/__init__.py 说明文档

## 中文说明

### 用途
`tui` 包的入口，汇总导出三个独立的 TUI 展示组件（流程图、当前活动面板、状态栏）以及阶段常量。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| FlowChart | class | 区域 A：5 阶段流程图（从 `.flow_chart` 导入） |
| ActivityPanel | class | 区域 C：当前活动 + LLM 流式输出（从 `.activity_panel` 导入） |
| StatusBar | class | 区域 D：底部资源面板（从 `.status_bar` 导入） |
| STAGES | list[str] | 固定的 5 阶段顺序：route/correctness/synth/optimize/submit |
| STAGE_SYMBOLS | dict[str, str] | 阶段状态对应的符号（pending/running/done/failed/skipped） |

### 导出
通过 `__all__` 显式导出：
```python
__all__ = ["FlowChart", "ActivityPanel", "StatusBar", "STAGES", "STAGE_SYMBOLS"]
```

注意：`ToolErrorBar`（`tool_error_bar.py`）和 `TaskPickerScreen`、`scan_tasks`（`task_picker.py`）**不在** `__init__` 的导出中，需要使用方直接从各自子模块导入（`from tui.tool_error_bar import ToolErrorBar`、`from tui.task_picker import TaskPickerScreen`）。`app.py` 即采用这种直接导入方式。

### 依赖
- 内部依赖：`.flow_chart`（FlowChart/STAGES/STAGE_SYMBOLS）、`.activity_panel`（ActivityPanel）、`.status_bar`（StatusBar）
- 外部依赖：无（本文件不直接依赖 textual/rich，仅转发子模块导出）

### 关键设计点
1. **纯展示组件**：三个 widget 是纯 presenters，数据通过方法调用推入，从不直接 import agent 包；详见 `docs-development/design/tui-design.md`。
2. **按区域划分**：三个组件分别对应设计文档中的区域 A（FlowChart）、区域 C（ActivityPanel）、区域 D（StatusBar），区域 B（ToolErrorBar）刻意未放入 `__init__` 导出，以保持"三件套"的简洁对外接口。
3. **阶段常量随 FlowChart 一起导出**：`STAGES`/`STAGE_SYMBOLS` 与流程图强相关，故从 `.flow_chart` 透传到包顶层。

---

## English

### Purpose
Package entry point for `tui`, re-exporting the three independent presenter widgets (flow chart, activity panel, status bar) plus stage constants.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| FlowChart | class | Region A: 5-stage flow chart (imported from `.flow_chart`) |
| ActivityPanel | class | Region C: current activity + LLM streaming output (from `.activity_panel`) |
| StatusBar | class | Region D: bottom resource panel (from `.status_bar`) |
| STAGES | list[str] | Fixed 5-stage order: route/correctness/synth/optimize/submit |
| STAGE_SYMBOLS | dict[str, str] | Symbols per stage state (pending/running/done/failed/skipped) |

### Exports
Explicit `__all__`:
```python
__all__ = ["FlowChart", "ActivityPanel", "StatusBar", "STAGES", "STAGE_SYMBOLS"]
```

Note: `ToolErrorBar` (`tool_error_bar.py`) and `TaskPickerScreen` / `scan_tasks` (`task_picker.py`) are **not** re-exported here; callers must import them directly from their submodules (e.g. `from tui.tool_error_bar import ToolErrorBar`). `app.py` does exactly this.

### Dependencies
- Internal: `.flow_chart` (FlowChart/STAGES/STAGE_SYMBOLS), `.activity_panel` (ActivityPanel), `.status_bar` (StatusBar)
- External: none (this file does not directly depend on textual/rich; it only forwards submodule exports)

### Key Design Points
1. **Pure presenter widgets**: the three widgets are pure presenters - data is pushed in via method calls and they never import the agent package directly; see `docs-development/design/tui-design.md`.
2. **Region-based split**: the three widgets map to design-doc regions A (FlowChart), C (ActivityPanel), and D (StatusBar). Region B (ToolErrorBar) is deliberately omitted from `__init__` exports to keep a clean "three-piece" public interface.
3. **Stage constants travel with FlowChart**: `STAGES`/`STAGE_SYMBOLS` are tightly coupled to the flow chart, so they are re-exported from `.flow_chart` to the package top level.
