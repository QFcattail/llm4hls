#!/usr/bin/env python3
"""Validate .env configuration and test LLM API connectivity.

Checks every environment variable the agent recognizes, prints a summary
table, and optionally sends a real API request to verify the key works.

Usage:
    python3 scripts/check_env.py              # check config only
    python3 scripts/check_env.py --test-api   # check + live API call
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ── ANSI colors ─────────────────────────────────────────────────────────
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

OK = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}⚠{RESET}"
SKIP = f"{DIM}--{RESET}"


def _load_dotenv(path: str = ".env") -> dict[str, str]:
    """Parse .env file and return key=value pairs (exported or plain)."""
    result: dict[str, str] = {}
    if not os.path.isfile(path):
        return result
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip leading "export "
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key:
                result[key] = value
    return result


def _mask(key: str) -> str:
    """Mask an API key for display: show first 7 and last 4 chars."""
    if len(key) <= 12:
        return key[:4] + "..." + key[-2:]
    return key[:7] + "..." + key[-4:]


def _check_var(
    name: str,
    env: dict[str, str],
    source: dict[str, str],
    required: bool = False,
    default: str = "",
    secret: bool = False,
    choices: list[str] | None = None,
) -> bool:
    """Check one env var. Returns True if OK."""
    value = env.get(name, "")
    in_dotenv = name in source
    display = _mask(value) if secret and value else (value or default or "(not set)")

    if not value and required:
        print(f"  {FAIL} {BOLD}{name}{RESET}  {RED}REQUIRED but not set{RESET}")
        return False
    if not value:
        print(f"  {SKIP} {name}  {DIM}using default: {default or 'none'}{RESET}")
        return True
    if choices and value not in choices:
        print(f"  {WARN} {name}={display}  {YELLOW}unexpected value (expected one of: {', '.join(choices)}){RESET}")
        return True

    origin = f"{DIM}(.env){RESET}" if in_dotenv else f"{DIM}(shell){RESET}"
    print(f"  {OK} {BOLD}{name}{RESET}={display}  {origin}")
    return True


def _test_api(env: dict[str, str]) -> bool:
    """Send a minimal chat completion request to verify the API key works."""
    api_key = env.get("LLM_API_KEY") or env.get("DEEPSEEK_API_KEY", "")
    base_url = env.get("LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
    model = env.get("LLM_MODEL", "deepseek-v4-pro")
    timeout = float(env.get("LLM_TIMEOUT", "30"))

    if not api_key:
        print(f"\n  {FAIL} No API key configured -- cannot test.")
        return False

    print(f"\n  {CYAN}Testing API connectivity...{RESET}")
    print(f"  Endpoint: {base_url}")
    print(f"  Model:    {model}")
    print(f"  Key:      {_mask(api_key)}")
    print()

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Reply with exactly: OK"},
            {"role": "user", "content": "Say OK"},
        ],
        "max_tokens": 16,
        "temperature": 0.0,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = json.loads(resp.read().decode("utf-8"))
        resp.close()
        content = body["choices"][0]["message"].get("content", "")
        usage = body.get("usage", {})
        prompt_tok = usage.get("prompt_tokens", "?")
        completion_tok = usage.get("completion_tokens", "?")
        print(f"  {OK} {GREEN}API call succeeded{RESET}")
        print(f"     Response: {content[:80]}")
        print(f"     Tokens:   prompt={prompt_tok} completion={completion_tok}")
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", "replace")[:200]
        print(f"  {FAIL} {RED}HTTP {e.code}{RESET}: {error_body}")
        if e.code == 401:
            print(f"     {YELLOW}The API key is invalid or expired.{RESET}")
        elif e.code == 404:
            print(f"     {YELLOW}The endpoint URL may be wrong (check LLM_BASE_URL).{RESET}")
        elif e.code == 429:
            print(f"     {YELLOW}Rate limited -- the key works but you're hitting limits.{RESET}")
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  {FAIL} {RED}Connection failed{RESET}: {e}")
        print(f"     {YELLOW}Check the endpoint URL and your network.{RESET}")
        return False
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"  {WARN} {YELLOW}Unexpected response format{RESET}: {e}")
        print(f"     The endpoint responded but the response doesn't look like OpenAI format.")
        return False


def main() -> int:
    test_api = "--test-api" in sys.argv

    print(f"\n{BOLD}FPGA Agent -- Environment Configuration Check{RESET}")
    print(f"{'=' * 50}\n")

    # Load .env
    dotenv = _load_dotenv(".env")
    if dotenv:
        print(f"  {OK} .env file found ({len(dotenv)} variables)")
    else:
        print(f"  {WARN} No .env file found (checked: .env)")
        print(f"     Create one: cp .env.example .env")

    # Merge: shell env takes precedence over .env
    merged = dict(dotenv)
    merged.update({k: v for k, v in os.environ.items() if k.startswith(("LLM_", "DEEPSEEK_", "VITIS"))})

    # ── API Key ──────────────────────────────────────────────────────────
    print(f"\n{BOLD}API Key:{RESET}")
    has_key = False
    key_val = merged.get("LLM_API_KEY", "")
    ds_key_val = merged.get("DEEPSEEK_API_KEY", "")
    if key_val:
        print(f"  {OK} {BOLD}LLM_API_KEY{RESET}={_mask(key_val)}")
        has_key = True
    elif ds_key_val:
        print(f"  {OK} {BOLD}DEEPSEEK_API_KEY{RESET}={_mask(ds_key_val)}")
        has_key = True
    else:
        print(f"  {FAIL} {RED}No API key set.{RESET} Set LLM_API_KEY or DEEPSEEK_API_KEY.")

    # ── Model Configuration ──────────────────────────────────────────────
    print(f"\n{BOLD}Model Configuration:{RESET}")
    _check_var("LLM_BASE_URL", merged, dotenv,
               default="https://api.deepseek.com/v1/chat/completions")
    _check_var("LLM_MODEL", merged, dotenv,
               default="deepseek-v4-pro")
    _check_var("LLM_THINKING", merged, dotenv,
               default="deepseek",
               choices=["deepseek", "enable_thinking", "none"])
    _check_var("LLM_TEMPERATURE", merged, dotenv, default="0.2")

    # ── Advanced ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}Advanced:{RESET}")
    _check_var("LLM_TIMEOUT", merged, dotenv, default="300")
    _check_var("LLM_MAX_RETRIES", merged, dotenv, default="3")
    _check_var("LLM_RETRY_BASE_DELAY", merged, dotenv, default="10")

    # ── Vitis ────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Vitis:{RESET}")
    vitis = merged.get("VITIS_ROOT", merged.get("LLM4HLS_VITIS_HLS_ROOT", ""))
    if vitis:
        if os.path.isdir(vitis):
            print(f"  {OK} {BOLD}VITIS_ROOT{RESET}={vitis}  (directory exists)")
        else:
            print(f"  {WARN} {BOLD}VITIS_ROOT{RESET}={vitis}  {YELLOW}(directory not found){RESET}")
    else:
        print(f"  {SKIP} VITIS_ROOT not set (will try auto-detect)")

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 50}")
    if has_key:
        model = merged.get("LLM_MODEL", "deepseek-v4-pro")
        url = merged.get("LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
        thinking = merged.get("LLM_THINKING", "deepseek")
        print(f"  {GREEN}{BOLD}Configuration looks good.{RESET}")
        print(f"  Model:    {BOLD}{model}{RESET}")
        print(f"  Endpoint: {url}")
        print(f"  Thinking: {thinking}")
    else:
        print(f"  {RED}{BOLD}Configuration incomplete -- set an API key.{RESET}")
        print(f"  Run: python3 scripts/setup_env.py")

    # ── Live API test ────────────────────────────────────────────────────
    if test_api:
        if not has_key:
            print(f"\n  {FAIL} Cannot test API without a key.")
            return 1
        ok = _test_api(merged)
        print(f"\n{'=' * 50}")
        if ok:
            print(f"  {GREEN}{BOLD}All checks passed. Ready to run.{RESET}")
            print(f"  Try: python3 scripts/run_agent.py contest/fpt26-harness/tasks/projection_bugfix --backend deepseek")
        else:
            print(f"  {RED}{BOLD}API test failed. Fix the issue above and try again.{RESET}")
        return 0 if ok else 1
    else:
        if has_key:
            print(f"\n  To verify the key actually works, run:")
            print(f"    {CYAN}python3 scripts/check_env.py --test-api{RESET}")
        return 0 if has_key else 1


if __name__ == "__main__":
    raise SystemExit(main())
