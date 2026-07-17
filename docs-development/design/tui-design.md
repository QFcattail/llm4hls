# TUI 交互式仪表盘设计 (TUI Design)

> 状态：设计文档（未实现）
> 框架：Textual + Rich
> 数据源：agent/observability.py 的 Logger 事件流 + harness transcript

---

## 1. 设计目标

实时显示 agent 运行状态，回答三个问题：
1. **现在走到哪了**（流程图 + 高亮当前阶段）
2. **现在在干什么**（具体动作 + 流式输出 + 已耗时）
3. **花了多少资源**（credit / token / 调用次数 / 上次反馈）

---

## 2. 布局（从上到下三个区域）

```
┌─────────────────────────────────────────────────────────────────────┐
│  区域 A：流程图（顶部，固定高度）                                       │
│  ┌──────┐    ┌────────────┐    ┌──────┐    ┌────────┐    ┌────────┐ │
│  │ 路由  │───►│ correctness │───►│ synth │───►│ optimize│───►│  提交  │ │
│  │ ✅ 2s │    │  ✅ 45s     │    │ 🔄 NOW│    │  ⚪    │    │  ⚪    │ │
│  └──────┘    └────────────┘    └──────┘    └────────┘    └────────┘ │
│                csim×3 2218tok        ↑当前在这                          │
├─────────────────────────────────────────────────────────────────────┤
│  区域 B：当前活动（中部，自适应高度，主视觉区）                            │
│                                                                       │
│  ▸ synth 综合中... 已耗时 12.3s                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ [流式输出区]                                                     │ │
│  │                                                                   │ │
│  │  如果是 LLM 调用：实时显示思维链 + 代码输出（像 opencode）            │ │
│  │  ┌─ thinking ─────────────────────────────────────────────────┐  │ │
│  │  │ The csim failed because the z coordinate is missing the     │  │ │
│  │  │ third term. Looking at the angle==0 branch, the code has    │  │ │
│  │  │ z0/3 + z1/3 but should have z0/3 + z1/3 + z2/3...          │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  │  ┌─ code ───────────────────────────────────────────────────────┐  │ │
│  │  │ triangle_2d->z = triangle_3d.z0 / 3                          │  │ │
│  │  │     + triangle_3d.z1 / 3 + triangle_3d.z2 / 3;|              │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  │                                                                   │ │
│  │  如果是工具调用：显示工具名 + 状态                                  │ │
│  │  [synth] running vitis-run --mode hls... (12.3s)                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  区域 C：资源面板（底部，固定 3 行）                                     │
│                                                                       │
│  credits: 6/10 剩余 4  ████████░░░░░░░░░░  │  tokens: 3453 (reasoning 1007)  │
│  本环节: synth 调用 1 次, review 0 次          │  总 LLM 调用: 2 次           │
│  上次工具报错: (无)                             │  上次 review: PASS            │
└─────────────────────────────────────────────────────────────────────┘
```

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

### 3.2 区域 B：当前活动（中部，主视觉）

**这是最大的区域，根据当前在干什么显示不同内容：**

#### B-1. LLM 调用时（repair / review / propose_strategies）

**流式显示思维链 + 输出**（需要 DeepSeek API 改为 stream 模式）：

```
▸ repair 修复中... 已耗时 8.2s
┌─ thinking ───────────────────────────────────────────────────────┐
│ The csim failed because the z coordinate is missing the third    │
│ term. Looking at the angle==0 branch, the code has z0/3 + z1/3  │
│ but should have z0/3 + z1/3 + z2/3. I need to add the missing    │
│ z2/3 term...█                                                     │  ← 光标闪烁，实时输出
└──────────────────────────────────────────────────────────────────┘
┌─ code ────────────────────────────────────────────────────────────┐
│ #include "projection.h"                                           │
│ void projection(...) {                                            │
│     if (angle == 0) {                                             │
│         ...                                                       │
│         triangle_2d->z = triangle_3d.z0 / 3 +                    │
│             triangle_3d.z1 / 3 + triangle_3d.z2 / 3;█           │  ← 实时输出
└───────────────────────────────────────────────────────────────────┘
```

**实现要点**：
- DeepSeek API 的 `stream: true` + SSE 解析，逐 token 输出
- `reasoning_content` 和 `content` 分两个区域显示
- thinking 区域用暗色/斜体，code 区域用语法高亮（Rich 的 syntax 支持）
- 输出完后自动切换到"等待工具验证"状态

#### B-2. 工具调用时（csim / synth / cosim）

```
▸ synth 综合中... 已耗时 14.7s
┌──────────────────────────────────────────────────────────────────┐
│  running: vitis-run --mode hls --tcl run_hls.tcl                 │
│  build dir: runs/projection_bugfix/agent/synth_3/                │
│                                                                   │
│  [vitis-run 输出尾]                                               │
│  Starting C-synthesis ...                                         │
│  ...                                                              │
│  Solution solution1 complete                                      │
│  Latency: 0 cycles                                                │
│  LUT: 692  FF: 0  DSP: 0  BRAM: 0                                │
└──────────────────────────────────────────────────────────────────┘
```

#### B-3. 机械检查时（mechanical_review）

```
▸ 机械检查... 已耗时 0.1s
✓ 签名未变: void projection(Triangle_3D, Triangle_2D*, bit2)
✓ Header 在: #include "projection.h"
```

#### B-4. 空闲/等待时

```
▸ 空闲，等待下一步...
  最后活动: 3.2s 前 (csim pass)
  下一步: synth 综合验证
```

### 3.3 区域 C：资源面板（底部 3 行）

**第 1 行：预算**
```
credits: 6/10 剩余 4  ████████░░░░░░░░░░  │  tokens: 3453 (reasoning 1007)
```
- 左边：credit 使用条（已用/总量 + 可视化进度条）
- 右边：累计 token（prompt + completion），括号里是 reasoning token

**第 2 行：本环节统计**
```
本环节: synth 调用 1 次, review 0 次          │  总 LLM 调用: 2 次
```
- "本环节"指当前阶段（如 synth 阶段）内的统计
- 左右用 `│` 分隔

**第 3 行：上次反馈**
```
上次工具报错: (无)                             │  上次 review: PASS
```
- 如果上次工具调用失败，显示错误摘要（红色）
- 如果上次 review 有意见，显示意见摘要
- `(无)` 表示没有（通过或还没调）

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
