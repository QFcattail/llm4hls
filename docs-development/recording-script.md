# P3-07 里程碑演示录屏脚本

> 目标：一段 ≤5 分钟的录屏（P4-07 演示视频可复用素材），展示 agent 在真 Vitis
> 上自主完成 HLS 修复/优化的全过程。在 **QFS-STATION 服务器**上录制。
> 2026-07-20 整理。

## 录制前准备

```bash
ssh QFS-STATION
cd /home/admin/fpga-agent
source /home/admin/Xilinx/2025.2/Vitis/settings64.sh
source .env
source /home/admin/venv-fpga/bin/activate
```

录屏工具：终端用 `asciinema rec demo.cast`（可转 GIF/视频）或直接 OBS 录屏。
终端字体调大（≥16pt），清屏后开始。

## 推荐拍摄内容（三选一，或拼接）

### 镜头 A：修复题（projection_bugfix，~3 分钟）

展示「功能 bug 自主修复」：csim 挂 → agent 诊断 → 修复 → 全绿。

```bash
python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
```

看点（讲解词要点）：
1. `[log] route` —— agent 识别题型 repair，走 csim 正确性关卡
2. `tool_result csim runtime_fail` —— 真实 Vitis csim 失败日志
3. `kb_search` —— 错误签名检索知识库
4. `checkpoint 0→1` —— 修复后 csim 通过、存档升级
5. Scorecard：`functional (hidden TB): PASS`，SCORE 1.400

### 镜头 B：优化题（dotProduct_optimize，~10 分钟，可快进）

展示「PPA 优化闭环」：73 倍加速满分。

```bash
python3 scripts/run_agent.py contest/fpt26-harness/tasks/dotProduct_optimize --backend deepseek
```

看点：
1. `phase_enter optimize` —— 进入优化阶段
2. `design_brief` —— AMD 四阶段工作流：先提炼设计摘要
3. `llm_call propose_strategies` + `strategy_select` —— 策略探索 + 评审 AI 双重确认
4. latency 轨迹 38→37→22→14 —— 每轮 re-synth 验证、同级择优
5. Scorecard：SCORE 3.000 满分（baseline 1027 → 14 cyc，73.36×）

### 镜头 C：死锁题（residual_stream_deadlock，~10 分钟，可快进）

展示「csim 发现不了的 cosim 死锁」：agent 在 pre-csim review 阶段就修掉。

```bash
python3 scripts/run_agent.py contest/fpt26-harness/tasks/residual_stream_deadlock --backend deepseek
```

看点：
1. `pre_csim_fix_applied` —— 第一次 csim 前就修掉 DATAFLOW 死锁
2. cosim 三次全通（正确性关卡 / 优化后 RTL 体检 / 隐藏评分）
3. `rollback` 机制就绪（best 未变则跳过回验）

## 拍完后日志在哪

- JSONL 结构化日志：`runs/<task>/<task>.jsonl`（解读见 runs/README.md）
- 得分历史：`runs/<task>/scores.jsonl`
- 最终 kernel：`runs/<task>/final_<kernel>.cpp`

## 剪辑建议（P4-07 ≤5 分钟）

1. 开头 15s：任务介绍（题目、预算、题型）
2. 主体 3.5min：镜头 A 完整 + 镜头 B 快进（heartbeat 等待段剪掉的）
3. 结尾 1min：Scorecard + latency 轨迹 + 一句话总结（正确性优先、预算内收敛）
