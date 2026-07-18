# agent/deepseek_client.py 说明文档

## 中文说明

### 用途
DeepSeek LLM 后端（OpenAI 兼容的原生端点）。DeepSeek V4 Pro 是推理模型，每次调用除最终内容外还产出 reasoning_tokens。实现与 harness OpenRouterClient/ScriptedClient 相同的 `complete(system, user) -> str` 契约，是 HLSLLMClient 的 drop-in 后端。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `DeepSeekClient` | class | OpenAI 兼容客户端，调用 DeepSeek 原生 chat completions 端点 |
| `DeepSeekClient.__init__(model=None, api_key=None, base_url=None, temperature=0.2, max_tokens=None, reasoning_effort="high", timeout=300.0, stream=False, on_stream=None)` | method | 构造；从 DEEPSEEK_API_KEY 读 key（缺失即报错），初始化用量统计 |
| `DeepSeekClient.complete(system, user) -> str` | method | 发 chat completion 请求返回 assistant 内容（calls 计数在起始自增） |
| `DeepSeekClient._read_stream(resp) -> str` | method | 读 SSE 流，按 delta 调 on_stream(thinking/content)，返回完整内容 |
| `DeepSeekClient._parse_response(body) -> str` | method | 解析非流式响应体并累计用量 |
| `DeepSeekClient._accumulate_usage(u)` | method | 累计 prompt/completion/reasoning token 统计 |
| `DeepSeekClient.usage_summary() -> str` | method | 返回累计用量一行摘要 |

### 导出
无 `__all__`；主要导出 `DeepSeekClient`；模块常量 `DEFAULT_BASE_URL`、`DEFAULT_MODEL`。

### 依赖
- 内部依赖：无（被当作 backend 注入 HLSLLMClient）
- 外部依赖：标准库 `json`、`os`、`urllib.error`、`urllib.request`；环境变量 `DEEPSEEK_API_KEY`

### 关键设计点
- API key 仅从环境 `DEEPSEEK_API_KEY` 读取，绝不写入版本控制文件；缺失即 RuntimeError。
- max_tokens 默认不发送（None=无限制，让模型在上下文窗内充分思考）；thinking.reasoning_effort（"high"/"max"）是推理深度唯一旋钮，无独立 max_reasoning_tokens。
- 用量统计：累计 prompt/completion/reasoning token 与调用数；流式无 usage 时按字符数/4 估算 completion。
- 架构注记：首版忽略 token 成本（按 architecture），但 token 用量高于非推理模型且影响最终评分。

---

## English

### Purpose
DeepSeek LLM backend (OpenAI-compatible, native endpoint). DeepSeek V4 Pro is a reasoning model: each call emits reasoning_tokens in addition to the final content. Implements the same `complete(system, user) -> str` contract as the harness OpenRouterClient/ScriptedClient, making it a drop-in backend for HLSLLMClient.

### Key Classes/Functions
| Name | Type | Responsibility |
|---|---|---|
| `DeepSeekClient` | class | OpenAI-compatible client calling DeepSeek's native chat completions endpoint |
| `DeepSeekClient.__init__(model=None, api_key=None, base_url=None, temperature=0.2, max_tokens=None, reasoning_effort="high", timeout=300.0, stream=False, on_stream=None)` | method | Construction; reads key from DEEPSEEK_API_KEY (errors if missing); initializes usage stats |
| `DeepSeekClient.complete(system, user) -> str` | method | Sends a chat completion request and returns assistant content (calls incremented at start) |
| `DeepSeekClient._read_stream(resp) -> str` | method | Reads the SSE stream, calls on_stream(thinking/content) per delta, returns full content |
| `DeepSeekClient._parse_response(body) -> str` | method | Parses a non-streaming response body and accumulates usage |
| `DeepSeekClient._accumulate_usage(u)` | method | Accumulates prompt/completion/reasoning token stats |
| `DeepSeekClient.usage_summary() -> str` | method | Returns a one-line summary of accumulated usage |

### Exports
No `__all__`; primary export is `DeepSeekClient`; module constants `DEFAULT_BASE_URL`, `DEFAULT_MODEL`.

### Dependencies
- Internal: none (injected as a backend into HLSLLMClient)
- External: standard library `json`, `os`, `urllib.error`, `urllib.request`; env var `DEEPSEEK_API_KEY`

### Key Design Points
- The API key is read only from the environment `DEEPSEEK_API_KEY` and is never written to version-controlled files; a missing key raises RuntimeError.
- max_tokens is not sent by default (None = unlimited, letting the model think fully within its context window); thinking.reasoning_effort ("high"/"max") is the only knob for reasoning depth, with no separate max_reasoning_tokens.
- Usage tracking: accumulates prompt/completion/reasoning tokens and call count; when streaming yields no usage, completion is estimated as char count / 4.
- Architecture note: the first iteration ignores token cost (per the architecture), but token usage is higher than non-reasoning models and affects the final score.
