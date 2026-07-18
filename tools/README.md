# 辅助工具 (Tools)

辅助脚本，非 agent 本体。用于开发/部署/调试。

## 工具清单

| 工具 | 用途 | 使用方法 | 状态 |
|---|---|---|---|
| `web_fetch.py` | 绕过 harness 内置 WebFetch 的域名验证限制，自由访问任意 URL（fetch/search/raw 三模式） | `python3 tools/web_fetch.py fetch <url> [--prompt "..."] [--out FILE]` | ✅ 已实现 |

### web_fetch.py 详细用法

```bash
# 抓取 URL，转 markdown 到 stdout
python3 tools/web_fetch.py fetch <url> [--prompt "抽取提示"] [--out FILE] [--max-chars N]

# 搜索（Bing / DuckDuckGo），返回 JSON 结果列表
python3 tools/web_fetch.py search <query> --engine bing --n 10

# 抓原文不转 markdown
python3 tools/web_fetch.py raw <url> [--out FILE]
```

依赖：`requests` + `html2text`（已装入 conda `python3`）。

设计原则：fetch 模式做 html->markdown 后输出，**不调 LLM 做抽取**--抽取留给调用方（agent / 人）读完后自己判断。带 User-Agent、超时、重试、跟随重定向、相对链接绝对化。

## 计划脚本

| 工具 | 用途 | 状态 |
|---|---|---|
| `log_parser.py` | Vitis HLS 日志/报告解析器（抽错误行/II/latency/资源） | ✅ 不需要（harness `report.py` 已实现 csynth.xml/cosim.rpt 解析） |
| `eval_mock.py` | 评估接口 mock | ✅ 不需要（harness ToolServer 即真接口） |
| `make_task.py` | 本地题集生成器（把官方 example 改坏） | ⚪ 待 P3 阶段实现 |
| `bench.py` | 本地评测脚本（跑 success rate / 预算消耗） | ⚪ 待 P3 阶段实现 |
