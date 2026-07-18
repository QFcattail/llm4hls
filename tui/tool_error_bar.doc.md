# tui/tool_error_bar.py 说明文档

## 中文说明

### 用途
区域 B（位于流程图与当前活动面板之间）的固定高度工具错误栏，展示最近一次工具调用（csim/synth/cosim）的结果与解析出的错误详情；通过时显示绿色成功行，失败时显示 gcc 风格错误行（最多 5 条）。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| _GCC_ERROR_RE | re.Pattern | 匹配 `file:line:col: error:` 风格 gcc/clang 编译错误行 |
| _VITIS_ERROR_RE | re.Pattern | 匹配 Vitis 错误码 `[XFORM/RTGEN/SIM/VPP NNN-NNN]`（排除 `[HLS 200-xxx]` 这类 INFO） |
| _TESTCASE_RE | re.Pattern | 匹配 `Test Case ... fail/Failed/FAIL` 测试用例失败行 |
| _GENERIC_ERROR_RE | re.Pattern | 匹配含 `ERROR/error/Error:` 的通用错误行 |
| _NOISE_RE | re.Pattern | 排除 INFO/WARNING/Resolution 等噪声行 |
| _MAX_ERRORS_SHOWN | int (=5) | 最多显示的错误行数，超出显示"...and N more errors" |
| ToolErrorBar | class(Static) | 固定高度（7）的错误栏 widget |
| ToolErrorBar.show_result(kind, phase, ok, elapsed=0, log="") | method | 更新栏内容：ok 时显示绿色成功行；失败时解析错误行并展示前 5 条，无结构化错误则回退显示日志尾部 3 行 |
| ToolErrorBar._extract_errors(log) | method | 从日志提取错误行（去重、保序，跳过噪声行） |
| ToolErrorBar.clear_bar() | method | 重置为空状态（"waiting for tool call..."） |
| ToolErrorBar.show_running(kind, elapsed=0) | method | 工具运行中状态：显示 `🔄 [kind] running {label}... elapsed {elapsed}s`（强调金色 `#FDD100`），label 按 kind 映射英文（csim->C simulation/synth->synthesis/cosim->co-simulation） |

### 导出
本模块**无** `__all__`；`ToolErrorBar` 需直接 `from tui.tool_error_bar import ToolErrorBar` 导入，且不在 `tui/__init__.py` 的导出中。

### 依赖
- 内部依赖：无（纯 presenter）
- 外部依赖：标准库 `re`；`textual.widgets.Static`；`rich.text.Text`

### 关键设计点
1. **独立成栏的原因**：gcc 编译错误行很长（行号 + 错误类型 + 上下文），塞在状态栏一行里显示不下；独立一栏让 LLM 与用户都能看清"上次工具报了什么错"（对应设计文档 §3.2）。
2. **多正则分级提取**：分别处理 gcc/clang 编译错误、Vitis 错误码、测试用例失败、通用 error 行，并用 `_NOISE_RE` 过滤 INFO/WARNING，结果去重保序，最多 5 条。
3. **运行中实时计时**：`show_running` 由 `app.py` 在工具运行期间周期调用，刷新已耗时秒数；`show_result` 在 `tool_result` 事件到达时给出最终结果。

---

## English

### Purpose
Region B (between the flow chart and the activity panel) fixed-height tool error bar showing the last tool call's (csim/synth/cosim) result and parsed error details; shows a green success line when passing, and gcc-style error lines (up to 5) when failing.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| _GCC_ERROR_RE | re.Pattern | Matches `file:line:col: error:` gcc/clang compile-error lines |
| _VITIS_ERROR_RE | re.Pattern | Matches Vitis error codes `[XFORM/RTGEN/SIM/VPP NNN-NNN]` (excludes `[HLS 200-xxx]` INFO) |
| _TESTCASE_RE | re.Pattern | Matches `Test Case ... fail/Failed/FAIL` test-case failure lines |
| _GENERIC_ERROR_RE | re.Pattern | Matches generic lines containing `ERROR/error/Error:` |
| _NOISE_RE | re.Pattern | Excludes INFO/WARNING/Resolution noise lines |
| _MAX_ERRORS_SHOWN | int (=5) | Max error lines shown; beyond that shows "...and N more errors" |
| ToolErrorBar | class(Static) | Fixed-height (7) error-bar widget |
| ToolErrorBar.show_result(kind, phase, ok, elapsed=0, log="") | method | Updates the bar: on ok shows a green success line; on failure parses error lines and shows the top 5, falling back to the last 3 log lines if no structured errors found |
| ToolErrorBar._extract_errors(log) | method | Extracts error lines from a log (deduplicated, order preserved, noise skipped) |
| ToolErrorBar.clear_bar() | method | Resets to empty state ("waiting for tool call...") |
| ToolErrorBar.show_running(kind, elapsed=0) | method | Running state: shows `🔄 [kind] running {label}... elapsed {elapsed}s` (accent gold `#FDD100`); label maps kind to English (csim->C simulation/synth->synthesis/cosim->co-simulation) |

### Exports
This module has **no** `__all__`; import `ToolErrorBar` directly via `from tui.tool_error_bar import ToolErrorBar`. It is not re-exported by `tui/__init__.py`.

### Dependencies
- Internal: none (pure presenter)
- External: stdlib `re`; `textual.widgets.Static`; `rich.text.Text`

### Key Design Points
1. **Why a separate bar**: gcc compile-error lines are long (line number + error type + context) and cannot fit in a single status-bar row; a dedicated bar lets both the LLM and the user clearly see "what the last tool reported" (design doc §3.2).
2. **Tiered multi-regex extraction**: separately handles gcc/clang compile errors, Vitis error codes, test-case failures, and generic error lines; `_NOISE_RE` filters INFO/WARNING; results are deduplicated and order-preserved, capped at 5.
3. **Live timer while running**: `show_running` is called periodically by `app.py` while a tool runs to refresh the elapsed seconds; `show_result` gives the final outcome when the `tool_result` event arrives.
