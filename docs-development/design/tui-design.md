# TUI 交互式仪表盘设计 (TUI Design)

> 状态：v2（2026-07-17，根据实际使用反馈重设计）
> 框架：Textual + Rich
> 数据源：agent/observability.py 的 Logger 事件流 + harness transcript

---

## 1. 设计目标

实时显示 agent 运行状态，回答四个问题：
1. **现在走到哪了**（流程图 + 高亮当前阶段）
2. **上次工具报了什么错**（独立区域，显示 gcc 风格错误行号 + 内容）
3. **现在在干什么**（LLM 流式思维链 + 代码 / 工具调用状态）
4. **花了多少资源**（credit / token / 调用次数 / review 意见）

---

## 2. 布局（从上到下四个区域）

```
┌─────────────────────────────────────────────────────────────────────┐
│  区域 A：流程图（顶部，固定高度）                                       │
│  ┌──────┐    ┌────────────┐    ┌──────┐    ┌────────┐    ┌────────┐ │
│  │ 路由  │───►│ correctness │───►│ synth │───►│ optimize│───►│  提交  │ │
│  │ ✅ 2s │    │  ✅ 45s     │    │ 🔄 NOW│    │  ⚪    │    │  ⚪    │ │
│  └──────┘    └────────────┘    └──────┘    └────────┘    └────────┘ │
│                csim×3 2218tok        ↑当前在这                          │
├─────────────────────────────────────────────────────────────────────┤
│  区域 B：上次工具报错（固定高度，独立一栏）                                │
│                                                                       │
│  📋 [csim] compile_error  (3 个错误)                                   │
│    1. projection.cpp:1:2: error: invalid preprocessing directive      │
│    2. projection.cpp:4:17: error: unknown type name 'Triangle_3D'    │
│    3. projection.cpp:4:42: error: unknown type name 'Triangle_2D'    │
│    ...还有 1 个错误                                                    │
│                                                                       │
│  (工具通过时显示: ✅ [csim] pass (9.7s))                               │
├─────────────────────────────────────────────────────────────────────┤
│  区域 C：当前活动（中部，自适应高度，主视觉区）                            │
│                                                                       │
│  ▸ repair LLM 调用... 已耗时 8.2s                                     │
│  💭 The csim failed because z is missing the third term...           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ triangle_2d->z = triangle_3d.z0 / 3                            │ │
│  │     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  (工具调用时: ▸ [synth] 综合中... 已耗时 12.3s)                        │
├─────────────────────────────────────────────────────────────────────┤
│  区域 D：资源面板（底部，固定 2 行）                                     │
│                                                                       │
│  credits: 6/10 剩余 4  ████████░░░░░░  │  tokens: 3453 (reasoning 1007)  │
│  本环节: 工具 1 次 review 0 次  │  总 LLM: 2 次  │  上次 review: PASS   │
└─────────────────────────────────────────────────────────────────────┘
```

**v2 布局变更说明**（基于实际使用反馈）：
- **新增区域 B**：上次工具报错单开一栏。之前塞在状态栏第 3 行，空间不够，只能显示笼统的 `runtime_fail`。现在独立一栏，能显示 gcc 风格的行号 + 错误内容。
- **区域 D 精简为 2 行**：把"上次工具报错"移到区域 B 后，状态栏不再需要第 3 行。只保留 credit/token 和调用次数/review。
- **区域 C 的 thinking 和 code 合并**：不再分两个 panel，在同一个流里连续输出。thinking 实时刷新（逐 token），code 行缓冲 + 语法高亮。

---

## 3. 三个区域详解

### 3.1 区域 A：流程图（顶部）

**显示内容**：agent 的 5 个阶段，横向排列，标注状态和耗时。

| 阶段 | 状态符号 | 含义 |
|---|---|---|
| `⚪` | 未开始 | 还没到这步 |
| `🔄` | 进行中 | 当前正在跑（高亮闪烁） |
| `✅` | 已完成 | 通过了，标注耗时 |
| `❌` | 失败 | 没通过，标注失败原因 |
| `⏭️` | 跳过 | budget 不够或其他原因跳过 |

每个阶段下方标注**本阶段统计**：
- 路由：`2s`（耗时）
- correctness：`csim×3 2218tok`（工具调用次数 + LLM token）
- synth：`synth×1 4cr`（工具调用次数 + credit）
- optimize：`opt×2 1500tok`
- 提交：`SCORE 1.400`

**交互**：按 `1`-`5` 跳转到对应阶段的详细日志。

### 3.2 区域 B：上次工具报错（固定高度，独立一栏）

**显示内容**：最近一次工具调用（csim/synth/cosim）的结果和错误详情。

**工具失败时**（从日志提取 gcc 风格错误行）：
```
📋 [csim] compile_error  (3 个错误)
  1. projection.cpp:1:2: error: invalid preprocessing directive
  2. projection.cpp:4:17: error: unknown type name 'Triangle_3D'
  3. projection.cpp:4:42: error: unknown type name 'Triangle_2D'
  ...还有 1 个错误
```

**工具通过时**：
```
✅ [csim] pass (9.7s)
```

**错误行提取逻辑**：
- 匹配 `file:line:col: error: ...` 格式（gcc/clang 编译错误）
- 匹配 `[XFORM 203-313]`、`[SIM 211-2]` 等 Vitis 错误码
- 匹配含 `ERROR`/`error`/`fail`/`Failed` 的行
- 最多显示 5 行，超出显示"...还有 N 个错误"
- runtime_fail（非编译错）时显示 test case 失败信息

**为什么独立一栏**：gcc 编译错误通常很长（行号 + 错误类型 + 上下文），塞在状态栏一行里显示不了。独立一栏能让 LLM 和用户都清楚看到"上次工具报了什么错"。

### 3.3 区域 C：当前活动（中部，自适应高度，主视觉）

**这是最大的区域，根据当前在干什么显示不同内容：**

#### C-1. LLM 调用时（repair / review / propose_strategies）

**思维链 + 代码在同一区域连续输出**（不再分两个 panel）：
```
▸ repair LLM 调用... 已耗时 8.2s
💭 The csim failed because z is missing the third term...    ← 实时刷新，逐 token
triangle_2d->z = triangle_3d.z0 / 3                          ← 代码，语法高亮
     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;
```

**实现要点**：
- thinking 用一个 Static（`ap-thinking-live`）实时覆盖显示，每个 token 都刷新（不换行）
- 完整的 thinking 行（遇到 `\n`）写入 RichLog 保留
- code 行缓冲 + cpp 语法高亮，写入同一个 RichLog
- thinking 用 dim italic，code 用 monokai 高亮
- 输出完后自动切换到"等待工具验证"状态

#### C-2. 工具调用时（csim / synth / cosim）

```
▸ [synth] 综合中... 已耗时 14.7s
  running: vitis-run --mode hls --tcl run_hls.tcl
  (等待结果...)
```

#### C-3. 空闲/等待时

```
▸ 空闲，等待下一步...
  最后活动: 3.2s 前 (csim pass)
```

### 3.4 区域 D：资源面板（底部，固定 2 行）

**第 1 行：预算**
```
credits: 6/10 剩余 4  ████████░░░░░░  │  tokens: 3453 (reasoning 1007)
```
- 左边：credit 使用条（已用/总量 + 可视化进度条）
- 右边：累计 token（prompt + completion），括号里是 reasoning token

**第 2 行：调用统计 + review**
```
本环节: 工具 1 次 review 0 次  │  总 LLM: 2 次  │  上次 review: PASS
```
- "本环节"指当前阶段内的统计
- 三段用 `│` 分隔

---

## 4. 数据源映射

TUI 的所有数据来自现有模块，不需要改 agent 逻辑：

| TUI 显示 | 数据源 | 现有/新增 |
|---|---|---|
| 流程图状态 + 耗时 | Logger 的 `phase_enter`/`phase_exit` 事件 | ✅ 已有 |
| 当前活动（工具调用） | Logger 的 `tool_result` 事件 + heartbeat 的 `stage` | ✅ 已有 |
| LLM 流式输出 | DeepSeek API `stream: true` + SSE 解析 | 🆕 需改 deepseek_client |
| credit 使用量 | `Budget.spent` / `Budget.total` | ✅ 已有 |
| token 统计 | `DeepSeekClient.total_prompt/completion/reasoning` | ✅ 已有 |
| 本环节调用次数 | 从 transcript 按 kind 过滤计数 | ✅ 已有 |
| 上次工具报错 | 最近一条 `tool_result` 的 `phase` + `log_tail` | ✅ 已有 |
| 上次 review 意见 | 最近一条 `review` 事件的 `issues` | ✅ 已有 |

**唯一需要新增的**：DeepSeek API 改为 stream 模式（`stream: true`），逐 token 返回 reasoning_content 和 content。这是区域 B 流式输出的前提。

---

## 5. 交互设计

| 按键 | 功能 |
|---|---|
| `q` / `Ctrl+C` | 退出（agent 后台继续跑，退出 TUI 不中断 agent） |
| `1`-`5` | 跳转到对应阶段的详细日志 |
| `l` | 查看完整 JSONL 日志（翻页） |
| `t` | 查看 transcript（工具调用历史） |
| `r` | 刷新（手动触发，正常自动刷新） |
| `↑`/`↓` | 滚动当前区域的输出 |

---

## 6. 技术方案

### 6.1 框架

- **Textual**：TUI 框架，提供布局（Container/Widget）、事件循环、CSS 样式
- **Rich**：渲染引擎（Textual 底层用 Rich），提供颜色、表格、进度条、语法高亮、Markdown

### 6.2 依赖

```
textual>=0.40.0
rich>=13.0.0
```

装到服务器 venv：`pip install textual rich`

### 6.3 架构

```
agent 主循环（不变）
  │
  ├── Logger.event(...)  ──► JSONL 文件（不变，已有）
  │                    ──► TUI 事件总线（新增，内存队列）
  │
  └── DeepSeekClient（改 stream 模式）
        │
        ├── 每 token 产出 ──► TUI 流式输出区（新增回调）
        └── 完整 response ──► Logger（不变）
```

**关键设计**：TUI 不改 agent 逻辑，只消费 Logger 的事件流。agent 在后台跑，TUI 是一个"观察者"。

### 6.4 实现拆分

| 模块 | 职责 | 估计工作量 |
|---|---|---|
| `tui/app.py` | Textual App 主入口，布局组装 | 0.5 天 |
| `tui/flow_chart.py` | 区域 A：流程图 widget | 0.5 天 |
| `tui/activity_panel.py` | 区域 B：当前活动 + 流式输出 | 1 天 |
| `tui/status_bar.py` | 区域 C：资源面板 | 0.5 天 |
| `agent/deepseek_client.py` | 加 stream 模式 + 回调 | 0.5 天 |
| `agent/observability.py` | 加 TUI 事件总线（内存队列） | 0.5 天 |
| 集成 + 调试 | | 1 天 |
| **合计** | | **约 4-5 天** |

---

## 7. 不做的事

- ❌ Web 版（Textual 已经够好，Web 版开发量翻倍）
- ❌ 远程访问（TUI 在服务器上跑，SSH 里看；不支持浏览器远程）
- ❌ 历史回放（只看当前运行；历史看 JSONL 日志）
- ❌ 编辑功能（TUI 只观察，不交互编辑代码）

---

## 8. 实现时机

**建议在 P2 末尾或 P3 初期实现**，前提：
1. agent 核心功能稳定（dotProduct + residual 题跑通）
2. 知识库有基本条目
3. DeepSeek stream 模式验证可用

TUI 是体验优化，不是功能必需。先用 `tail -f` JSONL 日志（已有）凑合，等 agent 稳定后再投入 TUI 开发。

---

## 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-07-15 | v1 初稿。基于用户 UI 描述设计三区域布局（流程图/当前活动/资源面板）。 | Agent 主 |
