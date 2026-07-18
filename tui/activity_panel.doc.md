# tui/activity_panel.py 说明文档

## 中文说明

### 用途
区域 C 中部主视觉 widget，用单一 RichLog 展示 agent 当前活动：LLM 调用时思维链 + 代码在同一流中交错输出，工具调用时输出工具日志，空闲时显示"等待下一步..."。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| ActivityType | type(Literal) | 活动类型：`"llm"`/`"tool"`/`"mechanical"`/`"idle"` |
| StreamKind | type(Literal) | 流式片段类型：`"thinking"`/`"content"` |
| _ERROR_LINE_RE / _COMPILE_ERROR_RE | re.Pattern | 用于 `show_tool_errors` 提取 Vitis/gcc 风格错误行的正则 |
| ActivityPanel | class(Static) | 当前活动面板：标题行 + thinking 实时预览 Static + 单一 RichLog |
| ActivityPanel.set_activity(activity_type, title) | method | 切换活动模式，重置标题/缓冲并清空日志体（idle 时写空闲提示） |
| ActivityPanel.append_stream(kind, text) | method | 追加 LLM 流式 delta：thinking 实时覆盖预览 + 完整行入 RichLog；content 行缓冲 + cpp 语法高亮 |
| ActivityPanel.append_log(text) | method | 追加原始工具输出文本 |
| ActivityPanel.show_tool_errors(log_text, phase) | method | 解析工具日志，显示错误总数 + 前 5 条错误行 |
| ActivityPanel.clear_log() | method | 清空日志 |
| ActivityPanel.refresh_title() | method | 仅重渲染标题行（周期 tick 调用） |
| ActivityPanel._write_code_line(log, line) | method | 写入单行代码，用 `Syntax(line, "cpp", theme="monokai")` 高亮，失败回退纯文本 |

### 导出
```python
__all__ = ["ActivityPanel", "ActivityType", "StreamKind"]
```

### 依赖
- 内部依赖：无（纯 presenter）
- 外部依赖：标准库 `re`/`time`/`typing`；`textual`（ComposeResult/Vertical/Static/RichLog）；`rich.syntax.Syntax`、`rich.text.Text`

### 关键设计点
1. **思维链与代码合并到同一 RichLog**：不再分两个 panel（设计文档 v2 变更），避免宽度问题；thinking 用 dim italic，code 用 monokai 高亮，连续输出。
2. **逐 token 实时反馈**：thinking 的部分行通过独立 Static（`#ap-thinking-live`）每个 token 覆盖刷新（截取最后 200 字符），完整行（遇 `\n`）才写入 RichLog 保留；content 行缓冲遇 `\n` 才写。这避免了"每个 token 单独一行"的问题。
3. **三类模式共用同一日志体**：llm/tool/mechanical/idle 共享一个 RichLog，`set_activity` 时清空重置，状态机简单。

---

## English

### Purpose
Region C middle main-visual widget: uses a single RichLog to show the agent's current activity - interleaving thinking + code in one stream during LLM calls, showing tool logs during tool calls, and "等待下一步..." when idle.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| ActivityType | type(Literal) | Activity kinds: `"llm"`/`"tool"`/`"mechanical"`/`"idle"` |
| StreamKind | type(Literal) | Stream fragment kinds: `"thinking"`/`"content"` |
| _ERROR_LINE_RE / _COMPILE_ERROR_RE | re.Pattern | Regexes used by `show_tool_errors` to extract Vitis/gcc-style error lines |
| ActivityPanel | class(Static) | Current-activity panel: title line + a thinking-live Static + a single RichLog |
| ActivityPanel.set_activity(activity_type, title) | method | Switches activity mode, resets title/buffers and clears the log body (writes idle hint when idle) |
| ActivityPanel.append_stream(kind, text) | method | Appends an LLM streaming delta: thinking overwrites the live preview + complete lines go to RichLog; content is line-buffered + cpp syntax-highlighted |
| ActivityPanel.append_log(text) | method | Appends raw tool output text |
| ActivityPanel.show_tool_errors(log_text, phase) | method | Parses a tool log and shows total error count + top 5 error lines |
| ActivityPanel.clear_log() | method | Clears the log |
| ActivityPanel.refresh_title() | method | Re-renders only the title line (called from periodic tick) |
| ActivityPanel._write_code_line(log, line) | method | Writes one code line with `Syntax(line, "cpp", theme="monokai")`, falling back to plain text on failure |

### Exports
```python
__all__ = ["ActivityPanel", "ActivityType", "StreamKind"]
```

### Dependencies
- Internal: none (pure presenter)
- External: stdlib `re`/`time`/`typing`; `textual` (ComposeResult/Vertical/Static/RichLog); `rich.syntax.Syntax`, `rich.text.Text`

### Key Design Points
1. **Thinking and code merged into one RichLog**: no longer split into two panels (design-doc v2 change) to avoid width issues; thinking uses dim italic, code uses monokai highlighting, output continuously.
2. **Per-token live feedback**: the partial thinking line is overwritten each token via a dedicated Static (`#ap-thinking-live`, last 200 chars), and only complete lines (on `\n`) are written to the RichLog; content is line-buffered and written on `\n`. This avoids the "each token on its own line" problem.
3. **Three modes share one log body**: llm/tool/mechanical/idle share a single RichLog; `set_activity` clears and resets it, keeping the state machine simple.
