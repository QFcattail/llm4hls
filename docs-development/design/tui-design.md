# TUI 交互式仪表盘设计 (TUI Design)

> 状态：v4（2026-07-18，区域 B 在 optimize 阶段复用为策略面板 + ToolErrorBar 改状态驱动渲染）
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
│  │route │───►│ correctness │───►│ synth │───►│optimize│───►│ submit │ │
│  │ ✅ 2s │    │  ✅ 45s     │    │ 🔄 NOW│    │  ⚪    │    │  ⚪    │ │
│  └──────┘    └────────────┘    └──────┘    └────────┘    └────────┘ │
│                csim×3 2218tok        ↑ CURRENT                        │
├─────────────────────────────────────────────────────────────────────┤
│  区域 B：上次工具报错（固定高度，独立一栏；v4 起 optimize 阶段复用为策略面板）│
│                                                                       │
│  (非 optimize 阶段, 工具失败时):                                        │
│  📋 [csim] compile_error  (3 errors)                                  │
│    1. projection.cpp:1:2: error: invalid preprocessing directive      │
│    2. projection.cpp:4:17: error: unknown type name 'Triangle_3D'    │
│    ...and 1 more errors                                               │
│                                                                       │
│  (optimize 阶段: 策略面板 ≤2 行 + 工具区 ≤3 行共存, §3.2)                │
│  🎯 3 strategies: 1.pipeline acc  2.array partition  3.unroll x4      │
│  ▶ selector picked 1+2: confirmed compatible, biggest combined gain   │
│  ✅ [csim] pass (9.7s)                                                │
├─────────────────────────────────────────────────────────────────────┤
│  区域 C：当前活动（中部，自适应高度，主视觉区）                            │
│                                                                       │
│  ▸ repair LLM call... elapsed 8.2s                                    │
│  💭 The csim failed because z is missing the third term...           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ triangle_2d->z = triangle_3d.z0 / 3                            │ │
│  │     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  (工具调用时: ▸ [synth] running synthesis... elapsed 12.3s)            │
├─────────────────────────────────────────────────────────────────────┤
│  区域 D：资源面板（底部，固定 2 行）                                     │
│                                                                       │
│  credits: 6/10 left 4  ████████░░░░░░  │  tokens: 3453 (reasoning 1007) │
│  stage: tools 1, reviews 0  │  total LLM: 2 calls  │  last review: PASS │
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
- route：`2s`（耗时）
- correctness：`csim×3 2218tok`（工具调用次数 + LLM token）
- synth：`synth×1 4cr`（工具调用次数 + credit）
- optimize：`opt×2 1500tok`
- submit：`SCORE 1.400`

**阶段标签**：v3 起全部使用英文 stage 名（`route`/`correctness`/`synth`/`optimize`/`submit`），当前阶段标记为 `↑ CURRENT`。

**交互**：按 `1`-`5` 跳转到对应阶段的详细日志。

### 3.2 区域 B：上次工具报错 + optimize 策略面板（固定高度，独立一栏）

**显示内容**：最近一次工具调用（csim/synth/cosim）的结果和错误详情；v4 起 optimize 阶段复用上部空间显示策略面板。

**工具失败时**（从日志提取 gcc 风格错误行）：
```
📋 [csim] compile_error  (3 errors)
  1. projection.cpp:1:2: error: invalid preprocessing directive
  2. projection.cpp:4:17: error: unknown type name 'Triangle_3D'
  3. projection.cpp:4:42: error: unknown type name 'Triangle_2D'
  ...and 1 more errors
```

**工具通过时**：
```
✅ [csim] pass (9.7s)
```

**错误行提取逻辑**：
- 匹配 `file:line:col: error: ...` 格式（gcc/clang 编译错误）
- 匹配 `[XFORM 203-313]`、`[SIM 211-2]` 等 Vitis 错误码
- 匹配含 `ERROR`/`error`/`fail`/`Failed` 的行
- 最多显示 5 行（optimize 阶段有策略面板时收缩为 3 行），超出显示"...and N more errors"
- runtime_fail（非编译错）时显示 test case 失败信息

**为什么独立一栏**：gcc 编译错误通常很长（行号 + 错误类型 + 上下文），塞在状态栏一行里显示不了。独立一栏能让 LLM 和用户都清楚看到"上次工具报了什么错"。

#### optimize 阶段复用为策略面板（v4 新增）

**复用理由**：optimize 循环里每次工具调用（csim/synth 重验）之前都经过 review 闸门，工具结果以 pass 为主——报错栏在 optimize 阶段大面积闲置。而 optimize 的"提了几个策略、评审 AI 选了哪几个、为什么"恰好是需要常驻显示的信息（区域 A stat 槽单行放不下 2-4 个策略名，流式输出滚过即失）。

**共存布局**（区域总高 7 行不变 = 内容 5 行）：策略区 ≤2 行 + 工具区 ≤3 行。
```
🎯 3 strategies: 1.pipeline acc  2.array partition  3.unroll x4
▶ selector picked 1+2: confirmed compatible, biggest combined gain
✅ [csim] pass (9.7s)
```
- **策略行 1（🎯）**：`strategy_select` 事件的 `all` 字段（全部候选策略名，编号 + 截断）
- **策略行 2（▶）**：同事件的 `picked`（评审 AI 选中的子集，用 `+` 连接）+ `reason` 截断；组合失败回退时由 `optimize_fallback` 事件改写为 `▶ fallback: strategy 1 only (combo failed)`
- **工具区**：照旧显示 running / pass / 错误详情；候选验证失败（optimize_discard）时错误照常显示——策略面板不遮盖真实报错
- optimize 阶段结束（`phase_exit`）后清空策略区，工具区独占 5 行（恢复非 optimize 行为）

**状态驱动渲染（v4 实现要点）**：ToolErrorBar 从一次性 `update()` 改为内部状态（`_strategy_lines` + `_tool_parts`）+ `_rebuild()` 拼接渲染（同 StatusBar 的 render 模式）。否则 `_refresh_ui` 每 150ms 一次的 `show_running` 心跳会把策略行擦掉。公开方法签名不变（`show_result`/`show_running`/`clear_bar`），新增 `show_strategies(all_names, picked, reason)`。

### 3.3 区域 C：当前活动（中部，自适应高度，主视觉）

**这是最大的区域，根据当前在干什么显示不同内容：**

#### C-1. LLM 调用时（repair / review / propose_strategies）

**思维链 + 代码在同一区域连续输出**（不再分两个 panel）：
```
▸ repair LLM call... elapsed 8.2s
💭 The csim failed because z is missing the third term...    ← 实时刷新，逐 token
triangle_2d->z = triangle_3d.z0 / 3                          ← 代码，语法高亮
     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;
```

**实现要点**：
- thinking 用一个 Static（`ap-thinking-live`）实时覆盖显示，每个 token 都刷新（不换行）
- 完整的 thinking 行（遇到 `\n`）写入 RichLog 保留
- code 行缓冲 + cpp 语法高亮，写入同一个 RichLog
- thinking 用 dim italic（灰色，v3 浅色主题下保持不变），code 用 `github-light` 高亮主题（v3 起从 monokai 换掉，monokai 是深色主题，白底下看不清）
- 输出完后自动切换到"等待工具验证"状态

#### C-2. 工具调用时（csim / synth / cosim）

```
▸ [synth] running synthesis... elapsed 14.7s
  running: vitis-run --mode hls --tcl run_hls.tcl
  (waiting for result...)
```

#### C-3. 空闲/等待时

```
▸ idle, waiting for next step...
  last activity: 3.2s ago (csim pass)
```

### 3.4 区域 D：资源面板（底部，固定 2 行）

**第 1 行：预算**
```
credits: 6/10 left 4  ████████░░░░░░  │  tokens: 3453 (reasoning 1007)
```
- 左边：credit 使用条（已用/总量 + 可视化进度条）
- 右边：累计 token（prompt + completion），括号里是 reasoning token

**第 2 行：调用统计 + review**
```
stage: tools 1, reviews 0  │  total LLM: 2 calls  │  last review: PASS
```
- "stage"指当前阶段内的统计
- 三段用 `│` 分隔
- 无错误/无 review 时的占位符为 `(none)`（v3 起从中文占位符改掉）

---

## 3.5 主题配色与界面语言（v3 新增）

### 配色规格 (Theme: `fpga-light`)

| 角色 | 色值 | 用途 |
|---|---|---|
| 主题色 (primary) | `#587559`（灰绿） | 标题栏、退出对话框边框、活动面板标题文字、credits 文字 |
| 强调色/装饰色 (accent) | `#FDD100`（金黄） | 四个区域边框（装饰）、当前阶段高亮、running 状态、credit 进度条填充 |
| 背景 (background/surface) | `#FFFFFF`（白） | 全局背景 |
| 普通正文 (foreground) | `#000000`（黑） | 原来用白色的普通文字（状态栏统计、工具日志原文） |
| CoT 思维链 | 灰色不变 | `dim italic` / `$text-muted`，白底下自然呈现灰色 |
| 语义色 | 绿=pass、红=error 保留 | 表达语义，不属于装饰 |

实现方式：Textual 8.x 自定义 `Theme`（`dark=False`），在 `AgentDashboard.__init__` 里 `register_theme()` + `self.theme = "fpga-light"`。Rich 内联样式中的 `"white"` 全部改 `"black"`，`"yellow"`/`"cyan"` 装饰性高亮分别换成 `#FDD100`/`#587559`。

代码语法高亮主题从 `monokai`（深色）换成 `github-light`（浅色），配合白底。

### 界面文案语言

v3 起**所有界面文案为英文**（stage 标签、状态行、错误汇总、idle 提示等）。文档语言不变（设计文档仍按规范中文为主）。

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
| 策略面板（区域 B，optimize） | `strategy_select` 事件的 `all`/`picked`/`reason` + `optimize_fallback` 事件 | 🆕 v4 新增 |

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
| 2026-07-17 | v2 四区域重设计：工具报错独立一栏（区域 B），thinking+code 合并流式输出，资源面板精简为 2 行。 | Agent 主 |
| 2026-07-18 | v3 新增 §3.5 主题配色（`fpga-light`：primary `#587559` / accent `#FDD100` / 白底黑字 / CoT 灰色不变）；界面文案全部改英文；代码高亮主题 monokai -> `github-light`。 | Agent 主 |
| 2026-07-18 | v4 区域 B 在 optimize 阶段复用为策略面板（用户决策：该阶段工具以 pass 为主，报错栏闲置；区域 A stat 槽放不下多策略名）：策略区 ≤2 行 + 工具区 ≤3 行共存，报错不被遮盖；ToolErrorBar 改状态驱动渲染（防 150ms 心跳 show_running 擦掉策略行）。数据源表加 `strategy_select`/`optimize_fallback`。配套 agent-architecture v2.4（策略组合 + 评审 AI）。 | Agent 主 |
