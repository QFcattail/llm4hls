# 内部笔记 (Internal Notes)

本目录存放开发过程中的探索性笔记、临时决策、踩坑记录。不追求排版精美，但要真实。

## 文件
- `tech-debt.md` — 技术债清单：已知问题、临时方案、待根治项。
- `备赛学习手册.docx` — 早期编写的备赛学习手册（**注意：该手册基于早期不完整信息编写，部分内容已过时，具体规则以 `runtime-constraints.md` 为准**）

## 2026-07-11 重要发现：赛题全景已明确

本仓库实际涉及**两个独立竞赛、三条赛道**：

| 竞赛 | 赛道 | 状态 |
|---|---|---|
| FPT'26 | Track A (LLM4HLS Agent) | 已有提交指南，缺评估接口规格 |
| FPT'26 | Track B (Attention Acceleration) | 仅有提交指南，缺 starter kit |
| FPL'26 | Agentic FPGA Backend Optimization | **材料最完整**：参考实现 + 13 benchmark + 评分公式 |

备赛手册主要围绕 FPT'26 Track A 编写，当时未见 FPL'26 赛题。现 FPL'26 参考实现已入库（`contest/fpl26_reference/`），工程计划已据实重写。

## 状态
- 待随开发过程追加。
