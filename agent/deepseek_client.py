"""DeepSeek LLM backend (OpenAI-compatible, native endpoint).

DeepSeek V4 Pro is a reasoning model: each call emits reasoning_tokens in
addition to the final content. Key API parameters (per api-docs.deepseek.com):

  - max_tokens: OPTIONAL. If not sent, output length is unconstrained (only
    bounded by the model's context window). We default to NOT sending it,
    so the model can think as long as it needs without truncating the answer.
  - thinking.type: "enabled" (default) / "disabled" — turns reasoning on/off.
  - thinking.reasoning_effort: "high" (default) / "max" — controls how hard
    the model thinks. "max" is for complex agent tasks. There is NO separate
    max_reasoning_tokens parameter; reasoning_effort is the only knob.

Token usage is higher than non-reasoning models (relevant to the final score,
but the first iteration ignores token cost per the architecture).

Implements the same `complete(system, user) -> str` contract as the harness
OpenRouterClient / ScriptedClient, so it is a drop-in backend for HLSLLMClient.

The API key is read from the environment (DEEPSEEK_API_KEY) and is NEVER
written into version-controlled files.
"""
from __future__ import annotations

import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-pro"


class DeepSeekClient:
    """OpenAI-compatible client for DeepSeek's native endpoint.

    Attributes:
        api_key: DeepSeek API key (never written to version-controlled files).
        model: DeepSeek model identifier to call.
        base_url: DeepSeek chat completions endpoint URL.
        temperature: Sampling temperature.
        max_tokens: Maximum output tokens (None = unlimited, default). Covers
            reasoning + output; setting it too low truncates the answer.
        reasoning_effort: "high" or "max". Controls reasoning depth.
        timeout: Request timeout in seconds.
        stream: If True, use streaming API and call on_stream callback per token.
        on_stream: Optional callback(delta_kind, delta_text) for streaming output.
            delta_kind is "thinking" or "content".
        total_prompt: Running total of prompt tokens across calls.
        total_completion: Running total of completion tokens across calls.
        total_reasoning: Running total of reasoning tokens across calls.
        calls: Number of completion calls made.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str = "high",
        timeout: float | None = None,
        stream: bool = False,
        on_stream=None,
    ) -> None:
        # Environment overrides let the same client talk to any
        # OpenAI-compatible endpoint (e.g. Aliyun MaaS for Qwen models)
        # without code changes. Defaults are byte-identical to the original
        # DeepSeek behavior when the env vars are unset.
        #   LLM_API_KEY   - API key (fallback: DEEPSEEK_API_KEY)
        #   LLM_BASE_URL  - chat-completions endpoint URL
        #   LLM_MODEL     - model identifier
        #   LLM_THINKING  - "deepseek" (default, send thinking dict) |
        #                   "enable_thinking" (Qwen-style: map effort to
        #                   enable_thinking bool, off -> false) |
        #                   "none" (omit the field entirely; some providers
        #                   reject unknown fields)
        #   LLM_TEMPERATURE - sampling temperature
        #   LLM_TIMEOUT   - request timeout in seconds
        #   LLM_MAX_RETRIES - transient-failure retries per call (default 3)
        #   LLM_RETRY_BASE_DELAY - backoff base seconds (default 10;
        #                   delay = base * 2**attempt, capped at 120s)
        self.api_key = (api_key or os.environ.get("LLM_API_KEY")
                        or os.environ.get("DEEPSEEK_API_KEY", ""))
        if not self.api_key:
            raise RuntimeError(
                "API key missing. Set LLM_API_KEY or DEEPSEEK_API_KEY in the "
                "environment (do NOT hardcode it into version-controlled files)."
            )
        self.model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL")
                         or DEFAULT_BASE_URL)
        self.temperature = (temperature if temperature is not None else
                            float(os.environ.get("LLM_TEMPERATURE", "0.2")))
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.timeout = (timeout if timeout is not None else
                        float(os.environ.get("LLM_TIMEOUT", "300")))
        self.thinking_mode = os.environ.get("LLM_THINKING", "deepseek")
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
        self.retry_base_delay = float(os.environ.get("LLM_RETRY_BASE_DELAY", "10"))
        self.stream = stream
        self.on_stream = on_stream  # callback(delta_kind: str, delta_text: str)
        # running usage stats (for later token accounting)
        self.total_prompt = 0
        self.total_completion = 0
        self.total_reasoning = 0
        self.calls = 0
        # per-call usage of the most recent call (for llm_call event logging)
        self.last_usage: dict = {}

    def complete(self, system: str, user: str,
                 response_format: dict | None = None,
                 reasoning_effort: str | None = None) -> str:
        """Send a chat completion request and return the assistant content.

        Args:
            system: System prompt text.
            user: User prompt text.
            response_format: Optional structured-output spec, e.g.
                ``{"type": "json_object"}`` to force valid JSON output
                (DeepSeek native structured output, probed 2026-07-19).
            reasoning_effort: Optional per-call override of the instance
                default. "high"/"max" keep thinking enabled at that level;
                "off" disables thinking entirely (thinking.type="disabled")
                for cheap verdict-class calls. None = instance default.

        Returns:
            The assistant's content string.

        Raises:
            RuntimeError: If the API returns an HTTPError or the request
                otherwise fails.
        """
        # Increment call count at the START so TUI can show "LLM call #N in progress"
        self.calls += 1
        effort = reasoning_effort if reasoning_effort is not None \
            else self.reasoning_effort
        thinking = ({"type": "disabled"} if effort == "off"
                    else {"type": "enabled", "reasoning_effort": effort})
        payload_dict: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            # thinking: control reasoning model behavior.
            # reasoning_effort "high" is default; "max" for complex agent tasks;
            # "off" (per-call) disables thinking for cheap verdict calls.
            # The field is DeepSeek-specific; LLM_THINKING=none omits it for
            # providers that reject unknown fields (e.g. some MaaS gateways).
            "stream": self.stream,
        }
        if self.thinking_mode == "enable_thinking":
            # Qwen-style switch: any effort other than "off" keeps the
            # model's default thinking behavior; "off" disables it.
            payload_dict["enable_thinking"] = (effort != "off")
        elif self.thinking_mode != "none":
            payload_dict["thinking"] = thinking
        # max_tokens: only send if explicitly set. If None (default), don't
        # send it - let the model use its full context window unconstrained.
        if self.max_tokens is not None:
            payload_dict["max_tokens"] = self.max_tokens
        if response_format is not None:
            payload_dict["response_format"] = response_format

        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        # Retry loop (v0.8.1): network-level failures (read timeout,
        # connection reset) and transient HTTP statuses (429/5xx) get
        # exponential backoff instead of aborting the whole agent run --
        # a 122B-class model can legitimately sit silent for minutes, and
        # one dropped connection must not discard hours of credit-funded
        # work (observed 2026-07-25: qwen3.5-122b matmul run lost to a
        # single 300s read timeout). A retried POST may double-bill tokens
        # if the server actually processed the timed-out request; that cost
        # is far smaller than losing the run. 4xx client errors (other
        # than 429) indicate a real request bug and fail immediately.
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = urllib.request.urlopen(req, timeout=self.timeout)
                if self.stream:
                    return self._read_stream(resp)
                body = json.loads(resp.read().decode("utf-8"))
                resp.close()
                return self._parse_response(body)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) \
                        and attempt < self.max_retries:
                    last_err = e
                    self._sleep_before_retry(attempt, f"HTTP {e.code}")
                    continue
                raise RuntimeError(
                    f"DeepSeek HTTP {e.code}: "
                    f"{e.read().decode('utf-8', 'replace')}"
                ) from e
            except (urllib.error.URLError, TimeoutError, ConnectionError,
                    http.client.HTTPException) as e:
                if attempt < self.max_retries:
                    last_err = e
                    self._sleep_before_retry(attempt, repr(e))
                    continue
                raise RuntimeError(
                    f"LLM request failed after {self.max_retries + 1} "
                    f"attempts: {e}"
                ) from e
        raise RuntimeError(f"LLM request failed: {last_err}")

    def _sleep_before_retry(self, attempt: int, why: str) -> None:
        """Sleep with exponential backoff and log the retry to stderr."""
        delay = min(self.retry_base_delay * (2 ** attempt), 120.0)
        print(f"[deepseek_client] transient failure ({why}); "
              f"retry {attempt + 1}/{self.max_retries} in {delay:.0f}s",
              file=sys.stderr, flush=True)
        time.sleep(delay)

    def _read_stream(self, resp) -> str:
        """Read SSE stream, call on_stream per delta, return full content."""
        content_parts: list[str] = []
        usage_data = {}
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            # extract usage from the last chunk (some APIs send it in final)
            if "usage" in chunk and chunk["usage"]:
                usage_data = chunk["usage"]
            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            # reasoning_content = thinking tokens, content = answer
            reasoning = delta.get("reasoning_content", "")
            content = delta.get("content", "")
            if reasoning and self.on_stream:
                self.on_stream("thinking", reasoning)
            if content:
                content_parts.append(content)
                if self.on_stream:
                    self.on_stream("content", content)
        resp.close()
        full_content = "".join(content_parts)
        # accumulate usage (stream may or may not include usage)
        if usage_data:
            self._accumulate_usage(usage_data)
        else:
            # estimate: count chars / 4 as rough token count
            self.total_completion += len(full_content) // 4
            self.last_usage = {"prompt": 0,
                               "completion": len(full_content) // 4,
                               "reasoning": 0}
        return full_content

    def _parse_response(self, body: dict) -> str:
        """Parse a non-streaming response body and accumulate usage."""
        msg = body["choices"][0]["message"]
        content = msg.get("content", "") or ""
        u = body.get("usage", {})
        self._accumulate_usage(u)
        return content

    def _accumulate_usage(self, u: dict) -> None:
        """Accumulate token usage stats from a usage dict."""
        self.total_prompt += u.get("prompt_tokens", 0)
        self.total_completion += u.get("completion_tokens", 0)
        cd = u.get("completion_tokens_details", {}) or {}
        self.total_reasoning += cd.get("reasoning_tokens", 0)
        self.last_usage = {
            "prompt": u.get("prompt_tokens", 0),
            "completion": u.get("completion_tokens", 0),
            "reasoning": cd.get("reasoning_tokens", 0),
        }

    def usage_summary(self) -> str:
        """Return a one-line summary of accumulated token usage across calls."""
        return (
            f"{self.model} {self.calls} calls | "
            f"prompt={self.total_prompt} completion={self.total_completion} "
            f"(reasoning={self.total_reasoning}) "
            f"total={self.total_prompt + self.total_completion}"
        )
