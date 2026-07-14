# 背景知识笔记索引 (Background Knowledge Index)

> 2026-07-11 下载整理。所有文件存放在本目录下。仅保留 FPT'26 Track A (LLM4HLS) 相关资料。

---

## 一、赛题与规则（仓库内已有）

> 这些文件不在 notes/ 目录，而在 `contest/` 目录。列出供完整参考。

| 文件 | 位置 | 内容 |
|---|---|---|
| `选题要求.md` | `contest/` | Track A 赛道描述、agent 端到端流程、task artifacts、关键名词 |
| `Submission_Guidelines_Track-A.docx` | `contest/` | 10 条提交规则（平台/版本/模型/Docker/视频等） |
| `AMD_LLM_HLS_SHA256_Article.html` | `contest/` | **★最重要的参考**：AMD 官方 LLM4HLS SHA-256 案例研究，描述四阶段工作流 |
| `amd_llm4hls_sha256_case_study.md` | `notes/` | 上述文章的 Markdown 提取版（已清理导航/页脚） |
| `fpt26_competition_page.md` | `notes/` | FPT'26 竞赛页面 Markdown 版（含时间线、评审标准、奖项） |
| `vitis_hls_ug1399_summary.md` | `notes/` | UG1399 Vitis HLS 用户指南重点摘要（用 browser MCP 抓取 JS 渲染页） |

---

## 二、Agent 架构与方法论（必读）

| 文件 | 来源 | 内容 | 优先级 |
|---|---|---|---|
| `anthropic_building_effective_agents.md` | Anthropic 工程博客 | Agent 设计模式：工具使用、编排循环、上下文管理。直接适用于我们的 ReAct 循环设计 | ★★★ |
| `react_paper.pdf` | arXiv 2210.03629 | **ReAct 论文全文**：Reasoning + Acting 范式，我们的 agent 主循环理论基础 | ★★★ |
| `react_paper_abstract.md` | 同上摘要页 | 快速浏览版 | ★★★ |
| `sweagent_readme.md` | GitHub SWE-agent | SWE-agent 项目架构：一个成熟的"LLM + 工具反馈循环" agent，可参考其 ACI 设计 | ★★☆ |
| `sweagent_paper_abstract.md` | arXiv 2405.15793 | SWE-agent 论文摘要（PDF 下载超时，待补） | ★★☆ |
| `mcp_introduction.md` | modelcontextprotocol.io | MCP 协议介绍。赛题可能用类似接口调用 csim/cosim/synth | ★☆☆ |

---

## 三、LLM4HLS 学术论文（领域核心）

| 文件 | 来源 | 内容 | 优先级 |
|---|---|---|---|
| `hls_repair_paper.pdf` | arXiv 2407.03889 | **★核心论文（PDF 全文）**：Automated C/C++ Program Repair for HLS via LLMs（Kangwei Xu 等）。直接对应赛题任务 | ★★★ |
| `hls_repair_paper_abstract.md` | 同上摘要页 | 快速浏览版 | ★★★ |
| `hlspilot_paper_abstract.md` | arXiv 2408.06810 | **HLSPilot**：首个 LLM 驱动的全自动 HLS 框架，含 C→HLS 转换 + DSE（AMD 案例文章引用） | ★★☆ |
| `autochip_paper_abstract.md` | arXiv 2311.04887 | **AutoChip**：用 LLM + EDA 工具反馈迭代改进 Verilog。方法论可迁移到 HLS | ★★☆ |
| `rtlfixer_paper_abstract.md` | arXiv 2311.16543 | **RTLFixer**：用 LLM 自动修复 RTL 语法错误。修复策略可参考 | ★☆☆ |

---

## 四、Prompt 优化技术（进阶选读）

| 文件 | 来源 | 内容 | 优先级 |
|---|---|---|---|
| `dspy_readme.md` | GitHub stanfordnlp/dspy | DSPy：编程式 Prompt 优化框架。AMD 案例文章提及 | ★☆☆ |
| `gepa_readme.md` | GitHub gepa-ai/gepa | GEPA：遗传进化式 Prompt 适配。FPL'26 赛题建议方向 | ★☆☆ |

---

## 五、非 Track A 资料（FPL'26 竞赛残留，可忽略）

> 以下文件是此前探索 FPL'26 时下载的，与 Track A 无关。待清理。

- `rapidwright_docs_index.md`、`rapidwright_timing_example.md`、`rapidwright_rwroute.md`、`rapidwright_fpga_interchange.md`
- `fpl26_contest_website.md`
- `fpt26_harness_reference.md`（内容为空，JS 渲染页）
- `vivado_tcl_reference.md`（内容为空，JS 渲染页）

---

## 阅读导读（按推荐顺序）

### 第 1 步：建立赛道全景（0.5 天）

1. **`contest/选题要求.md`**（已读）
   - 重点：agent 需完成的 6 步端到端流程、task artifacts 有哪些、correctness 优先于 PPA
2. **`contest/AMD_LLM_HLS_SHA256_Article.html`**（已解析，待精读）
   - 重点：四阶段工作流（Context Loading → Strategy Exploration → Code Generation → Synthesis Validation）
   - 关键洞察：LLM 给源码 + 综合报告一起看能做瓶颈定位，比不给报告泛泛建议强很多
   - Prompt 策略："你是资深 Vitis HLS 工程师和 FPGA 硬件架构师"这类角色 Prompt 效果好
   - 实验结果：gpt-5-turbo + claude-sonnet-4 在 2 周内实现 2.22× 加速

### 第 2 步：理解 Agent 架构核心（1 天）

3. **`react_paper.pdf`**（已下载）
   - 重点：ReAct = Reason + Act 交替执行。Thought → Action → Observation 循环
   - 对我们的意义：agent 每轮先"思考"该调用 csim 还是 synth，然后执行，解析结果，再思考下一步
4. **`anthropic_building_effective_agents.md`**（已下载）
   - 重点：五种 agent 模式（Prompt Chaining、Routing、Parallelization、Orchestrator-Worker、Evaluator-Optimizer）
   - 对我们的意义：我们最可能用 Orchestrator-Worker + Evaluator-Optimizer 组合
5. **`sweagent_readme.md`**（已下载）
   - 重点：SWE-agent 的 ACI（Agent-Computer Interface）设计——如何给 LLM 一个好用的工具接口
   - 对我们的意义：csim/cosim/synth 的调用接口要设计得对 LLM 友好

### 第 3 步：深入 LLM4HLS 学术前沿（1-2 天）

6. **`hls_repair_paper.pdf`**（已下载 PDF 全文）
   - 重点：如何用 LLM 自动修复 HLS C/C++ 代码的编译错和功能 bug
   - 对我们的意义：直接对应赛题任务，提取其修复策略和 prompt 模式
7. **`hlspilot_paper_abstract.md`**（已下载摘要）
   - 重点：C/C++ → HLS 的全自动转换 + 设计空间探索
   - 对我们的意义：理解 LLM 在 HLS 中的能力边界
8. **`autochip_paper_abstract.md`**（已下载摘要）
   - 重点：LLM + EDA 工具反馈的迭代循环（虽然是 Verilog 不是 HLS，但方法论可迁移）
   - 对我们的意义："工具反馈 → LLM 修复 → 再跑"的循环模式

### 第 4 步：选读进阶（按需）

9. `rtlfixer_paper_abstract.md` — RTL 修复，可参考错误分类思路
10. `dspy_readme.md` / `gepa_readme.md` — 如果后续要优化 prompt
11. `mcp_introduction.md` — 如果赛题用 MCP 接口调用工具

---

## 待补充

- [ ] SWE-agent 论文 PDF（arXiv 2405.15793，下载超时）
- [ ] HLSPilot 论文 PDF（arXiv 2408.06810，下载超时）
- [ ] AutoChip 论文 PDF（arXiv 2311.04887，下载超时）
- [ ] Kastner《Parallel Programming for FPGAs》前几章
- [ ] UG1399 子页面深入抓取（csim/cosynth/cosim 章节是 JS 渲染页，需 browser-use MCP 逐个抓）
