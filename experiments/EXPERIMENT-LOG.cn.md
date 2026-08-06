> [English](EXPERIMENT-LOG.md)

# 实验日志（EXPERIMENT-LOG）

按时间倒序记录。每次正式测试一节。

---

## 2026-07-25 多模型对比测试（FPT'26 规则 6 合规）

**目的**：比赛规则 6 要求用三个推荐模型评估并报告结果。此前仅完成
DeepSeek V4 Pro（见报告 Table VI），本次补充阿里云 MaaS 上的
`qwen3.5-122b-a10b`（AWQ-4bit）与 `qwen3.6-27b`（FP8）。

**环境**：
- 服务器：QFS-STATION（8 核 / 32GB），Vitis 2025.2，目标 U55C @ 200MHz
- 端点：阿里云 MaaS OpenAI 兼容模式（cn-beijing）
- 接入方式：`agent/deepseek_client.py` 环境变量覆盖
  （`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`/`LLM_THINKING=enable_thinking`）
- 端点探测结论（2026-07-25）：
  - 两模型均为推理模型，默认输出 reasoning_content；
  - `enable_thinking:false` 受支持（可关推理，用于 token-mode 的廉价判定调用）；
  - usage 含 `completion_tokens_details.reasoning_tokens`，token 统计兼容。

**配置**：token-mode=full（与 DeepSeek 主实验一致，保证可比性）。

### 冒烟测试：projection_bugfix × qwen3.6-27b（2026-07-25 21:37）

- 归档目录：`experiments/2026-07-25_qwen3.6-27b_projection_bugfix/`
- 结果：**SCORE 1.400**（满分 1.400），credits 5/20，tokens 13,896
- 对比 DeepSeek V4 Pro 同题：SCORE 1.400 / credits 5 / tokens 3,629
  -> 分数相同，qwen3.6-27b token 约 3.8×（小模型推理更长）
- 时序：estimated clock 2.538 ns（target 5.0，uncertainty 1.35）-> 满足，
  保守 Fmax 257 MHz ≥ 100 MHz（规则 4 达标）
- 踩坑记录：
  1. `set -u` 与 Vitis settings64.sh 冲突（PYTHONPATH unbound）-> runner 改用 `set -o pipefail`
  2. `--work` 传相对路径会被 harness 拼错（cd 进 build 目录后路径翻倍，
     csim.exe No such file）-> runner 改用 `$PWD/runs/...` 绝对路径
  3. 首次冒烟因 bug #2 浪费约 3 credits + ~13k tokens，已终止重跑，
     作废数据未归档

### 正式矩阵结果（2026-07-25 21:40 ~ 2026-07-26 凌晨）

token-mode=full，每 (模型,任务) 跑一次。qwen 两矩阵并行 + DeepSeek vecadd 补跑。

| 任务 | qwen3.6-27b (score/cr/tok) | qwen3.5-122b (score/cr/tok) |
|---|---|---|
| projection | 1.400 / 5 / 13,896 | 1.400 / 5 / 15,077 |
| vecadd | 0.738 / 20 / 37,699 | 0.500 / 20 / 59,725 |
| dotProduct | 2.325 / 10 / 38,458 | **3.000** / 15 / 72,763 |
| fir | 1.476 / 25 / 64,349 | **2.000** / 30 / 152,157 |
| matmul | **3.000** / 30 / 54,526 | 2.156 / 10 / 67,484（重跑） |
| residual | 3.396 / 60 / 68,365 | 3.098 / 30 / 41,959 |
| **合计** | 12.335 / - / 277,293 | 12.154 / - / 409,165 |

DeepSeek 对照合计：14.091 / - / 373,451。
三模型 csim 正确性门全部 18/18 通过；synth：DS 6/6、qwen3.6 6/6、
qwen3.5 5/6。全部 17 个可综合候选时序达标（保守 Fmax 200–353 MHz）。
所有运行（含崩溃现场）已归档至本目录（qwen3.6-27b/、qwen3.5-122b-a10b/、
deepseek-v4-pro/、deepseek-v4-pro-main/），每个任务目录含 transcript、
事件 jsonl、prompts jsonl、scores、final kernel、grade/csynth.xml、ppa.json。
报告数字已全部回填（Table IV/V/VI/VIII/IX，2026-07-26 01:15 编译通过）。

DeepSeek vecadd 补跑（PPA 数据清洁化）：1.000 / 20 / 51,519，lat 262
（归档 `deepseek-v4-pro/vecadd_optimize/`）。

**关键事件与发现**：
1. **qwen3.5 vecadd 仅 0.5**：csim 全过但 4 次 synth 全部 timeout（>600s），
   20 credits 耗尽。终版 kernel 用 VEC_UNROLL=8 循环分区，设计合法但综合超时；
   同期 DeepSeek/qwen3.6 的 synth 均正常通过 -> 非机器争抢问题，是候选设计
   规模问题 + agent 未能在 timeout 后退到更保守设计。值得报告案例分析。
2. **qwen3.6 vecadd 0.738**：正确性+synth 全过但优化完全无效（lat 4102 = 基线），
   小模型优化能力弱。
3. **qwen3.6 matmul 满分 3.000**（lat 78，210×）：DeepSeek 同题只有 2.691。
   优化能力与模型规模非单调，任务相关。
4. **qwen3.5 matmul 首跑崩溃**（00:37）：LLM API 读取超时（urllib read timeout,
   默认 300s），agent 无 HTTP 层重试逻辑 -> 整跑报废、无 scores.jsonl。
   是 agent 鲁棒性缺陷（值得报告 limitation），非智力失败。
   以 LLM_TIMEOUT=600 重跑（目录 matmul_optimize_r2），崩溃现场保留归档。
   **重跑结果 2.156**：qwen3.5 的 reviewer 在 pre_csim_review 阶段两次拒掉
   未修改的正确基线（"pragma placement"、"interface error" 等可疑理由），
   并应用了让 matmul 变慢 2 倍的"修复"（lat 32827 vs 基线 16422），
   archive 在受污染代码上锚定 -> 暴露出"reviewer 可在锚定前破坏好基线"的
   真实设计缺陷（报告 §VI-C 失败模式分析 + limitation #2，修复方向：
   archive 先在原始基线上锚定）。
5. qwen3.5 122B 生成慢：fir 用了 152k tokens / 30 credits；单题最长 ~50 min。
6. 并发注意：最多 3 个 Vitis 作业并行（8 核服务器），synth 变慢但未引起
   误判（DeepSeek 同期通过）。qwen3.5 vecadd 的 synth timeout 若需铁证可
   后续单独重跑（成本低 ~60k tokens）。

**收尾**：全部完成。报告 v2 重写（report/report.tex + report.bib），
新增：多模型主表（规则 6）、全 PPA 表（规则 4 时序证据 + 资源利用率）、
规则合规自查表（附录 A）、Related Work + 13 篇参考文献、失败模式分析、
PPA 权重讨论（latency-first 的评分最优性论证）。TUI/版本历史移出正文。
