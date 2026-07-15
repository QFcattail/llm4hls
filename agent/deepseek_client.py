"""DeepSeek LLM backend (OpenAI-compatible, native endpoint).

DeepSeek V4 Pro is a reasoning model: each call emits reasoning_tokens in
addition to the final content. Two implications:
  - max_tokens must be large (it covers reasoning + output).
  - token usage is higher than non-reasoning models (relevant to the final
    score, but the first iteration ignores token cost per the architecture).

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
        max_tokens: Maximum tokens (covers reasoning + output).
        timeout: Request timeout in seconds.
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
        max_tokens: int = 16384,
        timeout: float = 300.0,
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
        self.timeout = timeout
        # running usage stats (for later token accounting)
        self.total_prompt = 0
        self.total_completion = 0
        self.total_reasoning = 0
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        """Send a chat completion request and return the assistant content.

        Args:
            system: System prompt text.
            user: User prompt text.

        Returns:
            The assistant's content string.

        Raises:
            RuntimeError: If the API returns an HTTPError or the request
                otherwise fails.
        """
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }).encode("utf-8")
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
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"DeepSeek HTTP {e.code}: {e.read().decode('utf-8', 'replace')}"
            ) from e

        msg = body["choices"][0]["message"]
        content = msg.get("content", "") or ""
        # accumulate usage for later token analysis (second iteration)
        u = body.get("usage", {})
        self.total_prompt += u.get("prompt_tokens", 0)
        self.total_completion += u.get("completion_tokens", 0)
        cd = u.get("completion_tokens_details", {}) or {}
        self.total_reasoning += cd.get("reasoning_tokens", 0)
        self.calls += 1
        return content

    def usage_summary(self) -> str:
        """Return a one-line summary of accumulated token usage across calls."""
        return (
            f"DeepSeek {self.calls} calls | "
            f"prompt={self.total_prompt} completion={self.total_completion} "
            f"(reasoning={self.total_reasoning}) "
            f"total={self.total_prompt + self.total_completion}"
        )
