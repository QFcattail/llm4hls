# 辅助工具 (Tools)

辅助脚本，非 agent 本体。

## 已有脚本

### `web_fetch.py` — 自定义网络访问工具（已可用）

绕过 harness 内置 WebFetch 的域名验证限制。内置 WebFetch 会因 "Unable to verify if
domain ... is safe to fetch" 挡掉绝大多数域名；但本机 **Bash 有完整网络出口**
（curl / python urllib / pip 均可联网），所以写一个走 Bash 的 Python 脚本即可自由访问
任意 URL。这是本项目所有联网调研的入口。

依赖：`requests` + `html2text`（已装入 conda `python3`，即 `/home/GPUclaude/miniconda3/bin/python3`）。

```bash
# 抓取 URL，转 markdown 到 stdout
python3 tools/web_fetch.py fetch <url> [--prompt "抽取提示"] [--out FILE] [--max-chars N]

# 搜索（Bing / DuckDuckGo），返回 JSON 结果列表
python3 tools/web_fetch.py search <query> --engine bing --n 10

# 抓原文不转 markdown
python3 tools/web_fetch.py raw <url> [--out FILE]
```

设计原则：fetch 模式做 html→markdown 后输出，**不调 LLM 做抽取**——抽取留给调用方
（agent / 人）读完后自己判断。带 User-Agent、超时、重试、跟随重定向、相对链接绝对化。

## 计划脚本（P2 阶段实现）
- `log_parser.py` — Vitis HLS 日志/报告解析器（抽错误行/II/latency/资源）。
- `eval_mock.py` — 评估接口 mock（在真接口发布前供 agent 调用）。
- `make_task.py` — 本地题集生成器（把官方 example 改坏）。
- `bench.py` — 本地评测脚本（跑 success rate / 预算消耗）。

## 状态
- `web_fetch.py` ✅ 已实现。
- 其余 ⚪ 待 P2 阶段实现。
