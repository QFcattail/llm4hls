# 运行约束 (Runtime Constraints)

记录影响 agent 设计与运行的硬约束。

## 已知约束
- **预算约束**：csim/cosim/synth 调用次数有上限（具体额度待规则确认）。LLM 调用是否计预算未知——若不计，可放开让强模型多推理。
- **模型约束**：可用模型范围待确认。默认假设可用商用 API（GPT/Claude 等）；若限定开源模型，需考虑 LoRA/微调。
- **工具版本**：Vitis HLS 版本与 FPGA 平台待确认（影响 pragma 语法与报告格式）。
- **平台**：开发在 Windows（Git Bash）；远端有 GPU 主机 `gpuclaude-Wuying` 可跑 Linux 工具链。

## 待确认
见工程计划与备赛学习手册第十章“风险与待确认事项”。
