# tui/tool_error_bar.py 说明文档

## 中文说明

### 用途
区域 B（位于流程图与当前活动面板之间）的固定高度工具错误栏，展示最近一次工具调用（csim/synth/cosim）的结果与解析出的错误详情。v4 起（tui-design §3.2）在 optimize 阶段与**策略面板**共享：上部 ≤2 行显示"提了几个策略、评审 AI 选了哪几个、理由"，下部照常显示工具结果——optimize 阶段工具以 pass 为主，闲置空间复用，但策略面板绝不遮盖真实报错。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| _GCC_ERROR_RE 等 5 个正则 | re.Pattern | 错误行分级提取（gcc/Vitis 码/Test Case/通用 error/噪声过滤） |
| _MAX_ERRORS_SHOWN | int (=5) | 错误行硬上限（无策略面板时） |
| _CONTENT_ROWS | int (=5) | widget 内容总行数（高 7 减边框） |
| _LINE_CAP | int (=130) | 单行字符上限，防长策略名换行 |
| ToolErrorBar | class(Static) | 固定高度（7）的错误栏 + 策略面板 widget |
| ToolErrorBar.show_result(kind, phase, ok, elapsed=0, log="") | method | 更新工具区：ok 绿色成功行；失败解析错误行（无结构化错误回退日志尾部 3 行） |
| ToolErrorBar.show_running(kind, elapsed=0) | method | 工具运行中状态行（金色 `#FDD100`），只动工具区 |
| ToolErrorBar.clear_bar() | method | 工具区重置为等待态（策略区保留） |
| ToolErrorBar.show_strategies(all_names, picked, reason="") | method | 显示策略面板：🎯 目录行（全部候选编号+名）+ ▶ 选中行（评审 AI 子集+理由）；空列表时显示"proposing strategies..."就绪行 |
| ToolErrorBar.update_picked(picked, reason="") | method | 只改写 ▶ 行（optimize_fallback 事件：组合失败回退首策略） |
| ToolErrorBar.clear_strategies() | method | 清除策略面板（optimize 阶段结束） |
| ToolErrorBar._compose() -> Text | method | 拼接策略区+工具区为一份 Text（无头测试直接断言它） |
| ToolErrorBar._rebuild() | method | 把 _compose 结果推入 widget |
| ToolErrorBar._extract_errors(log) | method | 从日志提取错误行（去重、保序，跳过噪声行） |

### 导出
本模块**无** `__all__`；`ToolErrorBar` 需直接 `from tui.tool_error_bar import ToolErrorBar` 导入，且不在 `tui/__init__.py` 的导出中。

### 依赖
- 内部依赖：无（纯 presenter）
- 外部依赖：标准库 `re`；`textual.widgets.Static`；`rich.text.Text`

### 关键设计点
1. **状态驱动渲染（v4 关键改动）**：内部状态（`_strategy_all/_picked/_reason/_ready` + `_tool_header/_tool_errors`）+ 统一 `_rebuild()`。`app.py` 的 `_refresh_ui` 每 150ms 调一次 `show_running`——若沿用一次性 `update()`，策略行会被心跳擦掉；状态驱动后任何 show_* 只更新自己负责的分区。
2. **共存布局**：策略区 ≤2 行 + 工具 header 1 行 + 错误行填满剩余（有策略面板时错误预算 2 行，无则 4 行），截断时末行显示"...and N more errors"，总行数恒 ≤5。
3. **公开签名向后兼容**：`show_result`/`show_running`/`clear_bar` 签名不变，app.py 既有调用零改动；v4 新增 show_strategies/update_picked/clear_strategies。
4. **独立成栏的原因**：gcc 编译错误行很长（行号 + 错误类型 + 上下文），塞在状态栏一行里显示不下（设计文档 §3.2）。

---

## English

### Purpose
Region B (between the flow chart and the activity panel): a fixed-height bar showing the last tool call's (csim/synth/cosim) result and parsed error details. Since v4 (tui-design §3.2) the bar is shared with a **strategy panel** during the optimize stage: up to 2 lines on top show "how many strategies were proposed, which subset the selector AI picked, and why", while the tool zone below keeps showing results — optimize-stage tool calls mostly pass, so the idle space is reused, but the panel never hides real errors.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| 5 regexes (_GCC_ERROR_RE etc.) | re.Pattern | Tiered error-line extraction (gcc / Vitis codes / test cases / generic errors / noise filter) |
| _MAX_ERRORS_SHOWN | int (=5) | Hard cap on error lines (without a strategy panel) |
| _CONTENT_ROWS | int (=5) | Total content rows (widget height 7 minus border) |
| _LINE_CAP | int (=130) | Per-line character cap so long strategy names never wrap |
| ToolErrorBar | class(Static) | Fixed-height (7) error bar + strategy panel widget |
| ToolErrorBar.show_result(kind, phase, ok, elapsed=0, log="") | method | Updates the tool zone: green success line on ok; parsed error lines on failure (falls back to the last 3 log lines) |
| ToolErrorBar.show_running(kind, elapsed=0) | method | Running-state line (accent gold `#FDD100`); touches only the tool zone |
| ToolErrorBar.clear_bar() | method | Resets the tool zone to waiting (strategy zone kept) |
| ToolErrorBar.show_strategies(all_names, picked, reason="") | method | Shows the strategy panel: 🎯 catalog line (all proposals, numbered) + ▶ pick line (selector subset + reason); empty lists show a "proposing strategies..." ready line |
| ToolErrorBar.update_picked(picked, reason="") | method | Rewrites only the ▶ line (optimize_fallback event: combo failed, retrying first strategy) |
| ToolErrorBar.clear_strategies() | method | Removes the strategy panel (optimize stage exited) |
| ToolErrorBar._compose() -> Text | method | Joins strategy zone + tool zone into one Text (headless tests assert on it directly) |
| ToolErrorBar._rebuild() | method | Pushes the _compose output into the widget |
| ToolErrorBar._extract_errors(log) | method | Extracts error lines from a log (deduplicated, order preserved, noise skipped) |

### Exports
This module has **no** `__all__`; import `ToolErrorBar` directly via `from tui.tool_error_bar import ToolErrorBar`. It is not re-exported by `tui/__init__.py`.

### Dependencies
- Internal: none (pure presenter)
- External: stdlib `re`; `textual.widgets.Static`; `rich.text.Text`

### Key Design Points
1. **State-driven rendering (the key v4 change)**: internal state (`_strategy_all/_picked/_reason/_ready` + `_tool_header/_tool_errors`) plus a single `_rebuild()`. `app.py`'s `_refresh_ui` calls `show_running` every 150 ms — with the old one-shot `update()` pattern the heartbeat would wipe the strategy lines; with state-driven rendering each show_* method only touches its own zone.
2. **Coexistence layout**: strategy zone <=2 rows + tool header 1 row + error lines fill the rest (error budget 2 rows with a panel, 4 without); truncation appends an "...and N more errors" tail so the total never exceeds 5 rows.
3. **Backward-compatible public signatures**: `show_result`/`show_running`/`clear_bar` are unchanged (existing app.py calls keep working); v4 adds show_strategies/update_picked/clear_strategies.
4. **Why a separate bar**: gcc compile-error lines are long (line number + error type + context) and cannot fit in a single status-bar row (design doc §3.2).
