# agent/deepseek_client.py 说明文档

## 中文说明

### 用途
DeepSeek LLM 后端（OpenAI 兼容的原生端点）。DeepSeek V4 Pro 是推理模型，每次调用除最终内容外还产出 reasoning_tokens。实现与 harness OpenRouterClient/ScriptedClient 相同的 `complete(system, user) -> str` 契约，是 HLSLLMClient 的 drop-in 后端。

### 关键类/函数
| 名称 | 类型 | 职责 |
|---|---|---|
| `DeepSeekClient` | class | OpenAI 兼容客户端，调用 DeepSeek 原生 chat completions 端点 |
| `DeepSeekClient.__init__(model=None, api_key=None, base_url=None, temperature=0.2, max_tokens=None, reasoning_effort="high", timeout=300.0, stream=False, on_stream=None)` | method | 构造；从 DEEPSEEK_API_KEY 读 key（缺失即报错），初始化用量统计 |
| `DeepSeekClient.complete(system, user, response_format=None, reasoning_effort=None) -> str` | method | 发 chat completion 请求返回 assistant 内容（calls 计数在起始自增）。v0.7.0 起 `reasoning_effort` 可按调用覆盖实例默认："high"/"max" 保持思考，"off" 则 thinking.type=disabled 完全关闭推理（token-mode 分级开关的执行端，P4-03） |
| `DeepSeekClient._read_stream(resp) -> str` | method | 读 SSE 流，按 delta 调 on_stream(thinking/content)，返回完整内容 |
| `DeepSeekClient._parse_response(body) -> str` | method | 解析非流式响应体并累计用量 |
| `DeepSeekClient._accumulate_usage(u)` | method | 累计 prompt/completion/reasoning token 统计；v0.7.0 起同时刷新 `last_usage`（最近一次调用的 per-call 用量快照，供 llm_call 事件埋点） |
| `DeepSeekClient.usage_summary() -> str` | method | 返回累计用量一行摘要 |

### 导出
无 `__all__`；主要导出 `DeepSeekClient`；模块常量 `DEFAULT_BASE_URL`、`DEFAULT_MODEL`。

### 依赖
- 内部依赖：无（被当作 backend 注入 HLSLLMClient）
- 外部依赖：标准库 `json`、`os`、`urllib.error`、`urllib.request`；环境变量 `DEEPSEEK_API_KEY`

### 关键设计点
- API key 仅从环境 `DEEPSEEK_API_KEY` 读取，绝不写入版本控制文件；缺失即 RuntimeError。
- max_tokens 默认不发送（None=无限制，让模型在上下文窗内充分思考）；thinking.reasoning_effort（"high"/"max"）是推理深度唯一旋钮，无独立 max_reasoning_tokens。v0.7.0 起 complete() 接受 per-call `reasoning_effort` 覆盖，"off" 映射为 thinking.type=disabled（便宜判定类调用省 token；实测 reasoning 占 completion ~89%，是最大头）。
- 用量统计：累计 prompt/completion/reasoning token 与调用数；`last_usage` 保存最近一次调用的 per-call 快照（main_loop 的 llm_call 事件据此记 prompt_tokens/completion_tokens/reasoning_tokens，架构 §12.2）；流式无 usage 时按字符数/4 估算 completion。
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
| `DeepSeekClient.complete(system, user, response_format=None, reasoning_effort=None) -> str` | method | Sends a chat completion request and returns assistant content (calls incremented at start). Since v0.7.0 `reasoning_effort` overrides the instance default per call: "high"/"max" keep thinking on, "off" maps to thinking.type=disabled (the execution end of the token-mode graded switch, P4-03) |
| `DeepSeekClient._read_stream(resp) -> str` | method | Reads the SSE stream, calls on_stream(thinking/content) per delta, returns full content |
| `DeepSeekClient._parse_response(body) -> str` | method | Parses a non-streaming response body and accumulates usage |
| `DeepSeekClient._accumulate_usage(u)` | method | Accumulates prompt/completion/reasoning token stats; since v0.7.0 also refreshes `last_usage` (per-call usage snapshot of the most recent call, for llm_call event instrumentation) |
| `DeepSeekClient.usage_summary() -> str` | method | Returns a one-line summary of accumulated usage |

### Exports
No `__all__`; primary export is `DeepSeekClient`; module constants `DEFAULT_BASE_URL`, `DEFAULT_MODEL`.

### Dependencies
- Internal: none (injected as a backend into HLSLLMClient)
- External: standard library `json`, `os`, `urllib.error`, `urllib.request`; env var `DEEPSEEK_API_KEY`

### Key Design Points
- The API key is read only from the environment `DEEPSEEK_API_KEY` and is never written to version-controlled files; a missing key raises RuntimeError.
- max_tokens is not sent by default (None = unlimited, letting the model think fully within its context window); thinking.reasoning_effort ("high"/"max") is the only knob for reasoning depth, with no separate max_reasoning_tokens. Since v0.7.0 complete() accepts a per-call `reasoning_effort` override, with "off" mapping to thinking.type=disabled (cheap verdict-class calls save tokens; reasoning is ~89% of completion tokens, i.e. the dominant share).
- Usage tracking: accumulates prompt/completion/reasoning tokens and call count; `last_usage` holds the per-call snapshot of the most recent call (main_loop's llm_call events log prompt_tokens/completion_tokens/reasoning_tokens from it, architecture §12.2); when streaming yields no usage, completion is estimated as char count / 4.
- Architecture note: the first iteration ignores token cost (per the architecture), but token usage is higher than non-reasoning models and affects the final score.

### Environment Overrides (v0.8.1, multi-model support)
Despite the name, the client is now a generic OpenAI-compatible client. When the
following env vars are unset, behavior is byte-identical to the original DeepSeek
defaults:

| Env var | Effect |
|---|---|
| `LLM_API_KEY` | API key (takes priority over `DEEPSEEK_API_KEY`) |
| `LLM_BASE_URL` | Chat-completions endpoint URL |
| `LLM_MODEL` | Model identifier |
| `LLM_THINKING` | `deepseek` (default, send `thinking` dict) / `enable_thinking` (Qwen-style bool, `off`→false) / `none` (omit field) |
| `LLM_TEMPERATURE` | Sampling temperature (default 0.2) |
| `LLM_TIMEOUT` | Request timeout seconds (default 300) |
| `LLM_MAX_RETRIES` | Transient-failure retries per call (default 3) |
| `LLM_RETRY_BASE_DELAY` | Backoff base seconds (default 10; delay = base × 2^attempt, capped at 120s) |

Used for the FPT'26 rule-6 multi-model evaluation (Qwen3.5 122B / Qwen3.6 27B via
an Aliyun MaaS OpenAI-compatible endpoint); see `experiments/EXPERIMENT-LOG.md`.

### Retry Policy (v0.8.1)
`complete()` retries transient failures with exponential backoff instead of
aborting the run: network-level errors (`URLError`/`TimeoutError`/
`ConnectionError`/`http.client.HTTPException`, e.g. a read timeout on a slow
122B-class model) and HTTP 429/500/502/503/504. Other 4xx fail immediately
(real request bug). Each retry logs to stderr. Rationale: a single 300s read
timeout lost the entire qwen3.5-122b matmul run on 2026-07-25 (report
limitation #4, now fixed); a retried POST may double-bill tokens if the server
actually processed the timed-out request — far cheaper than losing a
credit-funded run. Retries are capped by `LLM_MAX_RETRIES` (default 3).
