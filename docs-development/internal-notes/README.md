# 内部过程笔记 (Internal Process Notes)

本目录存放**只有开发者自己需要看**的过程性内容，不追求排版和结构的完美，但要求真实、
有用。例如：

- 探索某个技术方案时走过的弯路和放弃的原因
- 临时的调试记录、命令行速查
- 一些还不成熟、没必要写进正式文档但又不想丢掉的想法

## 与 dev-log 的区别

| 目录 | 性质 | 内容 |
|---|---|---|
| `dev-log/` | 面向所有人的正式日志 | 结论性记录：做了什么、结果是什么 |
| `internal-notes/` | 仅开发者自己 | 过程性草稿：走过的弯路、临时命令、不成熟的想法 |

> 简单判断：如果这条信息对"接手项目的新人"有用且结论明确，放 `dev-log/`；如果只是"我试过这个不行"的探索过程，放 `internal-notes/`。

## 与 notes/ 的区别

| 目录 | 内容 |
|---|---|
| `internal-notes/` | 本项目开发过程自身的探索性笔记、踩坑记录、技术债 |
| `notes/`（`docs-development/notes/`） | 外部背景资料库（论文、工具文档、赛题资料），不随项目进度变化 |

## 当前内容

- [`tech-debt.md`](tech-debt.md) - 技术债清单：已知问题、临时方案、待根治项（按 Critical/High/Medium/Low 分级）
- `备赛学习手册.docx` / `.tex` - 早期编写的备赛学习手册（**注意：该手册基于早期不完整信息编写，部分内容已过时，具体规则以 `runtime-constraints.md` 为准**）

## 2026-07-11 重要发现：赛题全景已明确

本仓库实际涉及**两个独立竞赛、三条赛道**：

| 竞赛 | 赛道 | 状态 |
|---|---|---|
| FPT'26 | Track A (LLM4HLS Agent) | 已有提交指南，缺评估接口规格 |
| FPT'26 | Track B (Attention Acceleration) | 仅有提交指南，缺 starter kit |
| FPL'26 | Agentic FPGA Backend Optimization | **材料最完整**：参考实现 + 13 benchmark + 评分公式 |

备赛手册主要围绕 FPT'26 Track A 编写，当时未见 FPL'26 赛题。现 FPL'26 参考实现已入库（`contest/fpl26_reference/`），工程计划已据实重写。**本项目最终聚焦 FPT'26 Track A**。

## 状态
- 待随开发过程追加。
