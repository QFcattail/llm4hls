# experiments/ - 测试数据归档（重要！勿删）

本目录归档**所有有成本的测试数据**（真实 LLM API 调用 + 真 Vitis 工具运行）。
测试在 QFS-STATION 服务器（Vitis 2025.2 + Alveo U55C 目标）上执行，
原始产物在服务器 `runs/`（gitignored），本目录保存**精选归档副本**。

## 为什么单独建目录

- `runs/` 被 gitignore（体积大、临时性），测试数据会随服务器清理丢失。
- 测试有真实成本（API token 费用 + 服务器机时），**数据不能直接扔在服务器上不管**。
- 报告（`report/report.tex`）中的每个数字都必须能追溯到本目录的原始记录。

## 目录结构

```
experiments/
├── README.md            本文件（归档规范）
├── EXPERIMENT-LOG.md    实验日志（按时间倒序，每次测试一节）
├── <date>_<model>_<task>/   每次正式测试一个目录
│   ├── summary.json     关键指标汇总（SCORE/credits/tokens/latency/PPA）
│   ├── transcript.txt   运行转录（stdout）
│   ├── events.jsonl     结构化事件日志（agent observability）
│   ├── prompts.jsonl    逐条 LLM prompt+response（体积大时只保留代表样本）
│   └── ppa.json         synth 报告提取的 PPA 数据（latency/资源/时序）
└── tables/              汇总表（CSV），供报告直接引用
```

## 归档流程（每次测试后必做）

1. 测试在服务器跑完后，立即 `rsync` 对应 run 目录的关键文件回本目录。
2. 在 `EXPERIMENT-LOG.md` 记录：日期、模型、任务、配置（token-mode 等）、
   结果（SCORE/credits/tokens）、异常事件、原始数据位置。
3. 报告引用的数字必须来自本目录的文件，不凭记忆填写。

## 红线

- **API key 永不入库**：`.env` 已 gitignore，归档文件若含 key 必须脱敏。
- prompts.jsonl 可能很大（单次运行可达数 MB），超过 ~10MB 时只归档
  代表性样本并在日志中说明取舍。
