> [中文](README.cn.md)

# Tools

Helper scripts, not part of the agent core. Used for development/deployment/debugging.

## Tool List

| Tool | Purpose | Usage | Status |
|---|---|---|---|
| `web_fetch.py` | Bypasses the harness's built-in WebFetch domain-verification restriction, freely accessing any URL (fetch/search/raw modes) | `python3 tools/web_fetch.py fetch <url> [--prompt "..."] [--out FILE]` | ✅ Implemented |

### web_fetch.py Detailed Usage

```bash
# Fetch a URL, convert to markdown, print to stdout
python3 tools/web_fetch.py fetch <url> [--prompt "extraction prompt"] [--out FILE] [--max-chars N]

# Search (Bing / DuckDuckGo), return a JSON list of results
python3 tools/web_fetch.py search <query> --engine bing --n 10

# Fetch raw content without markdown conversion
python3 tools/web_fetch.py raw <url> [--out FILE]
```

Dependencies: `requests` + `html2text` (already installed in the conda `python3`).

Design principle: the fetch mode converts html -> markdown and outputs it, and **does not call an LLM for extraction** -- extraction is left to the caller (agent / human), who reads the result and judges it themselves. It sets a User-Agent, timeout, retries, follows redirects, and absolutizes relative links.

## Planned Scripts

| Tool | Purpose | Status |
|---|---|---|
| `log_parser.py` | Vitis HLS log/report parser (extract error lines/II/latency/resources) | ✅ Not needed (the harness `report.py` already implements csynth.xml/cosim.rpt parsing) |
| `eval_mock.py` | Evaluation interface mock | ✅ Not needed (the harness ToolServer is the real interface) |
| `make_task.py` | Local task-set generator (corrupts the official examples) | ⚪ Pending, to be implemented in the P3 phase |
| `bench.py` | Local benchmarking script (run success rate / budget consumption) | ⚪ Pending, to be implemented in the P3 phase |
