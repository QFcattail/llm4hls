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

import json
import os
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
        temperature: float = 0.2,
        max_tokens: int | None = None,
        reasoning_effort: str = "high",
        timeout: float = 300.0,
        stream: bool = False,
        on_stream=None,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "DeepSeek API key missing. Set DEEPSEEK_API_KEY in the "
                "environment (do NOT hardcode it into version-controlled files)."
            )
        self.model = model or DEFAULT_MODEL
        self.base_url = base_url or DEFAULT_BASE_URL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.stream = stream
        self.on_stream = on_stream  # callback(delta_kind: str, delta_text: str)
        # running usage stats (for later token accounting)
        self.total_prompt = 0
        self.total_completion = 0
        self.total_reasoning = 0
        self.calls = 0

    def complete(self, system: str, user: str,
                 response_format: dict | None = None) -> str:
        """Send a chat completion request and return the assistant content.

        Args:
            system: System prompt text.
            user: User prompt text.
            response_format: Optional structured-output spec, e.g.
                ``{"type": "json_object"}`` to force valid JSON output
                (DeepSeek native structured output, probed 2026-07-19).

        Returns:
            The assistant's content string.

        Raises:
            RuntimeError: If the API returns an HTTPError or the request
                otherwise fails.
        """
        # Increment call count at the START so TUI can show "LLM call #N in progress"
        self.calls += 1
        payload_dict: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            # thinking: control reasoning model behavior.
            # reasoning_effort "high" is default; "max" for complex agent tasks.
            "thinking": {
                "type": "enabled",
                "reasoning_effort": self.reasoning_effort,
            },
            "stream": self.stream,
        }
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
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"DeepSeek HTTP {e.code}: {e.read().decode('utf-8', 'replace')}"
            ) from e

        if self.stream:
            return self._read_stream(resp)
        else:
            body = json.loads(resp.read().decode("utf-8"))
            resp.close()
            return self._parse_response(body)

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

    def usage_summary(self) -> str:
        """Return a one-line summary of accumulated token usage across calls."""
        return (
            f"DeepSeek {self.calls} calls | "
            f"prompt={self.total_prompt} completion={self.total_completion} "
            f"(reasoning={self.total_reasoning}) "
            f"total={self.total_prompt + self.total_completion}"
        )
