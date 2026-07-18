# tui/flow_chart.py 说明文档

## 中文说明

### 用途
区域 A 顶部流程图 widget，横向展示 agent 的 5 个固定阶段及其状态符号、耗时和统计，当前运行阶段用粗体闪烁黄色高亮。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| STAGES | list[str] | 固定阶段顺序：`["route","correctness","synth","optimize","submit"]`，镜像 `agent/main_loop.py` |
| STAGE_SYMBOLS | dict[str, str] | 状态符号：pending ⚪ / running 🔄 / done ✅ / failed ❌ / skipped ⏭️ |
| _STAGE_LABELS | dict[str, str] | 阶段中文短标签（route→路由、submit→提交，其余用英文） |
| _STATUS_STYLE | dict[str, str] | 各状态对应 Rich 样式，running 额外加 `blink` |
| _format_elapsed(elapsed) | function | 把秒数格式化为 `"2s"`/`"0.4s"`/`""`（≤0 返回空） |
| FlowChart | class(Static) | 流程图 widget，用 Rich Table 渲染三行：符号行 / 箭头行 / 统计行 |
| FlowChart.update_stage(stage_name, status, elapsed=0.0, stat="") | method | 更新某阶段的状态/耗时/统计并重渲染；未知阶段或状态抛 ValueError |
| FlowChart.mark_current(stage) | method | 把 stage 标为 running，并把更早仍 running 的阶段折叠为 done（保留终态） |
| FlowChart.reset() | method | 清空所有阶段回到 pending |
| FlowChart.render() | method | 覆写 Static.render 返回 Rich Group（Table + 当前阶段标记） |

### 导出
- 通过 `__all__`（在 `__init__.py` 中）导出：`FlowChart`、`STAGES`、`STAGE_SYMBOLS`
- 本模块内部还有 `_STAGE_LABELS`、`_STATUS_STYLE`、`_format_elapsed`（私有，下划线前缀）

### 依赖
- 内部依赖：无（纯 presenter，不 import agent 包）
- 外部依赖：`textual.widgets.Static`；`rich.console`（Group/RenderableType）、`rich.table.Table`、`rich.text.Text`

### 关键设计点
1. **覆写 render 而非 Static.update**：避免 `Static.update` 在首次布局前被调用导致的 None-visual 竞态；`update_stage` 只改内部状态再 `refresh()`。
2. **mark_current 的折叠语义**：调用方只知"现在进入阶段 X"，此方法自动把更早仍为 running 的阶段标为 done（它们必然已结束才能前进），且不覆盖 done/failed/skipped 等终态。
3. **状态符号/样式对应设计文档 §3.1**：符号表与 `docs-development/design/tui-design.md` §3.1 的表格一致，running 阶段额外加 `blink` 以吸引视线。
4. **箭头自行绘制**：Table 不显示边框/线条，箭头 `──►` 作为单独一行渲染在阶段间隙下方。

---

## English

### Purpose
Region A top flow-chart widget showing the agent's 5 fixed pipeline stages horizontally with a status symbol, elapsed time, and a short statistic; the current running stage is highlighted in bold blinking yellow.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| STAGES | list[str] | Fixed stage order `["route","correctness","synth","optimize","submit"]`, mirroring `agent/main_loop.py` |
| STAGE_SYMBOLS | dict[str, str] | Status symbols: pending ⚪ / running 🔄 / done ✅ / failed ❌ / skipped ⏭️ |
| _STAGE_LABELS | dict[str, str] | Short per-stage labels (route→路由, submit→提交, others in English) |
| _STATUS_STYLE | dict[str, str] | Rich style per status; running additionally gets `blink` |
| _format_elapsed(elapsed) | function | Formats seconds as `"2s"`/`"0.4s"`/`""` (returns empty for <=0) |
| FlowChart | class(Static) | Flow-chart widget rendering 3 rows via a Rich Table: symbol row / arrow row / stat row |
| FlowChart.update_stage(stage_name, status, elapsed=0.0, stat="") | method | Updates a stage's status/elapsed/stat and re-renders; raises ValueError on unknown stage or status |
| FlowChart.mark_current(stage) | method | Marks `stage` as running and folds any earlier still-running stages to done (terminal states preserved) |
| FlowChart.reset() | method | Clears all stages back to pending |
| FlowChart.render() | method | Overrides Static.render to return a Rich Group (Table + current-stage marker) |

### Exports
- Re-exported via `__all__` (in `__init__.py`): `FlowChart`, `STAGES`, `STAGE_SYMBOLS`
- Internal/private: `_STAGE_LABELS`, `_STATUS_STYLE`, `_format_elapsed` (underscore-prefixed)

### Dependencies
- Internal: none (pure presenter; does not import the agent package)
- External: `textual.widgets.Static`; `rich.console` (Group/RenderableType), `rich.table.Table`, `rich.text.Text`

### Key Design Points
1. **Override render, not Static.update**: avoids the None-visual race that `Static.update` hits when called before the first layout pass; `update_stage` only mutates internal state then calls `refresh()`.
2. **mark_current fold semantics**: the caller only knows "we are now in stage X"; this method auto-marks earlier still-running stages as done (they must have finished to advance) and leaves terminal states (done/failed/skipped) untouched.
3. **Symbols/styles match design doc §3.1**: the symbol table matches `docs-development/design/tui-design.md` §3.1; the running stage additionally gets `blink` to draw the eye.
4. **Arrows drawn manually**: the Table has no box/edges; the arrow `──►` is rendered as a separate row aligned under the gaps between stage columns.
