# tui/status_bar.py 说明文档

## 中文说明

### 用途
区域 D 底部资源面板 widget（固定 2 行内容 + 边框），显示 credit 进度条、token 统计、本环节调用次数与上次 review 意见。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| _BAR_WIDTH | int (=20) | credit 进度条字符宽度 |
| _NONE | str ("(无)") | 无错误/无 review 时的占位符，保持布局稳定 |
| _PASS_REVIEWS | set[str] | 视为通过的 review verdict（pass/ok/accept/accepted/(无)），显示为绿色 |
| _SUMMARY_CAP | int (=40) | last_error/last_review 摘要长度上限，防第 2 行换行 |
| _truncate(text, cap) | function | 超长截断加省略号 |
| _credit_bar(spent, total) | function | 构造可视化进度条（`█`/`░`），返回 (bar Text, remaining)；total<=0 时返回空条避免除零 |
| StatusBar | class(Static) | 底部资源面板：credits/tokens/calls/feedback |
| StatusBar.update(credits_spent=None, ...) | method | 仅更新传入的非 None 字段，其余保留旧值，支持增量刷新 |
| StatusBar.update_state(**kwargs) | method | `update` 的向后兼容别名，并把旧名 `stage_tool_calls` 映射为 `stage_calls` |
| StatusBar.render() | method | 覆写 Static.render 返回 2 行 Rich Text |
| StatusBar._render_line1() | method | 第 1 行：credit 条 + 剩余 │ tokens（reasoning 在括号内） |
| StatusBar._render_line2() | method | 第 2 行：本环节工具/review 次数 │ 总 LLM 次数 │ 上次 review（pass 绿/fail 红） |

### 导出
```python
__all__ = ["StatusBar"]
```

### 依赖
- 内部依赖：无（纯 presenter，不 import agent 包）
- 外部依赖：`textual.widgets.Static`；`rich.console.RenderableType`、`rich.text.Text`

### 关键设计点
1. **增量更新 API**：`update` 所有参数均可选（None 表示不改动），调用方可只推 `last_error` 而无需每次重发全部计数器，降低耦合。
2. **覆写 render 避免竞态**：与 FlowChart 相同，`update` 只改字段再 `refresh()`，由 Textual 在自己的 console 上下文里渲染，规避 `Static.update` 首次布局前的 None-visual 竞态。
3. **设计文档 §3.3 对齐**：字段语义对应 `docs-development/design/tui-design.md` §3.3 与 agent 可观测字段（credit 来自 Budget、token 来自 DeepSeekClient、last_error 来自 tool_result、last_review 来自 review 事件）。注意设计文档区域 D 现为 2 行（原第 3 行"上次工具报错"已移至独立区域 B/ToolErrorBar）。
4. **向后兼容别名**：`update_state` 保留给旧调用方（如 `app.py`），并做 `stage_tool_calls -> stage_calls` 命名迁移。

---

## English

### Purpose
Region D bottom resource-panel widget (fixed 2 content rows + border): shows the credit progress bar, token totals, per-stage call counts, and the last review verdict.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| _BAR_WIDTH | int (=20) | Character width of the credit progress bar |
| _NONE | str ("(无)") | Sentinel for no-error/no-review, keeping layout stable |
| _PASS_REVIEWS | set[str] | Verdicts treated as passing (pass/ok/accept/accepted/(无)), shown in green |
| _SUMMARY_CAP | int (=40) | Length cap for last_error/last_review summaries to prevent line 2 from wrapping |
| _truncate(text, cap) | function | Truncates overlong text with an ellipsis |
| _credit_bar(spent, total) | function | Builds the visual bar (`█`/`░`); returns (bar Text, remaining); renders empty bar when total<=0 to avoid divide-by-zero |
| StatusBar | class(Static) | Bottom resource panel: credits/tokens/calls/feedback |
| StatusBar.update(credits_spent=None, ...) | method | Updates only the non-None fields passed in; others retain previous values (incremental refresh) |
| StatusBar.update_state(**kwargs) | method | Back-compat alias for `update`; maps legacy `stage_tool_calls` to `stage_calls` |
| StatusBar.render() | method | Overrides Static.render to return a 2-line Rich Text |
| StatusBar._render_line1() | method | Line 1: credit bar + remaining │ tokens (reasoning in parentheses) |
| StatusBar._render_line2() | method | Line 2: per-stage tool/review counts │ total LLM calls │ last review (green on pass, red on fail) |

### Exports
```python
__all__ = ["StatusBar"]
```

### Dependencies
- Internal: none (pure presenter; does not import the agent package)
- External: `textual.widgets.Static`; `rich.console.RenderableType`, `rich.text.Text`

### Key Design Points
1. **Incremental update API**: every `update` parameter is optional (None means unchanged), so a caller can push only `last_error` without resending every counter each tick, reducing coupling.
2. **Override render to avoid the race**: like FlowChart, `update` only mutates fields then calls `refresh()`; Textual renders in its own console context, sidestepping the None-visual race that `Static.update` hits before the first layout pass.
3. **Aligned with design doc §3.3**: field semantics map to `docs-development/design/tui-design.md` §3.3 and the agent's observability fields (credits from Budget, tokens from DeepSeekClient, last_error from tool_result, last_review from review events). Note that design-doc region D is now 2 lines (the original third "last tool error" line moved to the standalone region B / ToolErrorBar).
4. **Back-compat alias**: `update_state` is kept for older callers (e.g. `app.py`) and migrates the `stage_tool_calls -> stage_calls` name.
