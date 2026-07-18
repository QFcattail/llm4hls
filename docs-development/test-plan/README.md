# 测试用例 (Test Plan)

> 本目录存放 agent 的测试用例与测试策略，基于 P2 详细设计编写。每条用例必须可追溯到需求 ID 和设计章节。

## 文档清单

| 文档 | 内容 | 状态 |
|---|---|---|
| `test-strategy.md` | 测试策略（本地题集构造、success rate 统计、预算消耗记录） | ⚪ 待编写 |
| `agent-tests.md` | agent 行为测试：能否修通编译错/csim/cosim 各类题 | ⚪ 待编写 |
| `local-tasks/` | 本地评测题集（坏代码 + 预期修法 + 已知答案） | ⚪ 待构造 |

> **说明**：当前测试以官方 harness 的 3 道公开题（projection_bugfix / dotProduct_optimize / residual_stream_deadlock）为基准，通过 `scripts/run_agent.py` 跑端到端验证。正式测试用例文档待 P3 阶段配合本地题集建设补充。

## 测试用例编写原则

### 1. 用户行为视角

每条用例只描述：
1. **前置条件 (Given)** - agent/系统当前在什么状态（如：某道题的初始代码有 csim bug）。
2. **用户动作 (When)** - 用户跑了什么命令、给了什么输入。
3. **可观察反馈 (Then)** - 用户看到了什么 scorecard、SCORE 值、日志输出。

**不描述内部实现**。

### 2. 覆盖维度

每个功能至少覆盖：Happy Path / 错误异常 / 重试恢复 / Monkey 乱点（如超预算、空输入、畸形代码）。

### 3. 可自动化性标注

- **A** (Automated) - 可编写自动化测试（如 csim/synth/cosim 通过率）。
- **M** (Manual) - 必须人工验证（如 TUI 渲染效果、演示视频）。
- **S** (Semi) - 部分可自动化，部分需人工。

## 用例编号规则

格式：`TC-<子系统>-<三位序号>`

| 子系统代码 | 含义 |
|---|---|
| `AGT` | agent 本体（main_loop / router / checkpoint 等） |
| `TUI` | TUI 仪表盘 |
| `KB` | 知识库 |
| `HAR` | harness 对接 |

## 用例模板

```markdown
### TC-AGT-NNN: 用例标题

**优先级**: P0 / P1 / P2
**可自动化**: A / M / S
**对应需求**: REQ-AGT-XX
**对应设计**: `design/agent-architecture.md` §X.X

**前置条件 (Given)**:
- ...

**用户动作 (When)**:
1. ...

**期望反馈 (Then)**:
- ...

**Monkey 变体**:
- 超预算 / 空输入 / 畸形代码 / 重复操作 ...
```

## 评审

测试用例完成后，提交评审（记录在 [`../reviews/`](../reviews/)），通过后方可进入 P4 编码实现。
