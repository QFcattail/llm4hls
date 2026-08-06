#!/usr/bin/env python3
"""Interactive CLI to configure .env for the FPGA Agent.

Guides you through setting up the LLM endpoint, model ID, and API key
with per-provider presets. Writes the result to .env.

Usage:
    python3 scripts/setup_env.py
"""
from __future__ import annotations

import os
import sys

# ── ANSI colors ─────────────────────────────────────────────────────────
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Provider presets ─────────────────────────────────────────────────────
PRESETS = {
    "1": {
        "name": "DeepSeek V4 Pro (native)",
        "env": {
            "DEEPSEEK_API_KEY": "",
            "LLM_BASE_URL": "https://api.deepseek.com/v1/chat/completions",
            "LLM_MODEL": "deepseek-v4-pro",
            "LLM_THINKING": "deepseek",
        },
        "key_var": "DEEPSEEK_API_KEY",
        "key_hint": "Get one at https://platform.deepseek.com",
    },
    "2": {
        "name": "Qwen3.5 122B (Aliyun MaaS)",
        "env": {
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "LLM_MODEL": "qwen3.5-122b-a10b",
            "LLM_THINKING": "enable_thinking",
            "LLM_TIMEOUT": "600",
        },
        "key_var": "LLM_API_KEY",
        "key_hint": "Get one at https://dashscope.aliyun.com",
    },
    "3": {
        "name": "Qwen3.6 27B (Aliyun MaaS)",
        "env": {
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "LLM_MODEL": "qwen3.6-27b",
            "LLM_THINKING": "enable_thinking",
        },
        "key_var": "LLM_API_KEY",
        "key_hint": "Get one at https://dashscope.aliyun.com",
    },
    "4": {
        "name": "Custom (any OpenAI-compatible endpoint)",
        "env": {
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
            "LLM_THINKING": "none",
        },
        "key_var": "LLM_API_KEY",
        "key_hint": "Your provider's API key",
    },
}


def _prompt(label: str, default: str = "", hint: str = "") -> str:
    """Ask the user for input with an optional default and hint."""
    suffix = ""
    if hint:
        suffix += f" {DIM}({hint}){RESET}"
    if default:
        suffix += f" [{default}]"
    try:
        value = input(f"  {CYAN}?{RESET} {label}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n  {YELLOW}Aborted.{RESET}")
        sys.exit(1)
    return value if value else default


def _confirm(label: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        answer = input(f"  {CYAN}?{RESET} {label}{suffix}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n  {YELLOW}Aborted.{RESET}")
        sys.exit(1)
    if not answer:
        return default
    return answer in ("y", "yes")


def main() -> int:
    print(f"\n{BOLD}FPGA Agent -- LLM Configuration Setup{RESET}")
    print(f"{'=' * 50}")
    print(f"  This will create/update the .env file in the current directory.\n")

    # Check for existing .env
    if os.path.isfile(".env"):
        print(f"  {YELLOW}An .env file already exists.{RESET}")
        if not _confirm("Overwrite it?", default=False):
            print(f"  Keeping existing .env. To validate it, run:")
            print(f"    python3 scripts/check_env.py --test-api")
            return 0
        print()

    # ── Step 1: Choose a provider ────────────────────────────────────────
    print(f"{BOLD}Step 1: Choose your LLM provider{RESET}\n")
    for key, preset in PRESETS.items():
        print(f"  {BOLD}{key}{RESET}) {preset['name']}")
    print()

    choice = _prompt("Provider", default="1")
    if choice not in PRESETS:
        print(f"  {RED}Invalid choice: {choice}{RESET}")
        return 1

    preset = PRESETS[choice]
    print(f"\n  Selected: {BOLD}{preset['name']}{RESET}\n")

    # ── Step 2: API key ──────────────────────────────────────────────────
    print(f"{BOLD}Step 2: API Key{RESET}\n")
    key_var = preset["key_var"]
    api_key = _prompt(f"API key ({key_var})", hint=preset["key_hint"])
    if not api_key:
        print(f"  {RED}API key is required.{RESET}")
        return 1

    env = dict(preset["env"])
    env[key_var] = api_key

    # ── Step 3: Endpoint (custom only, or allow override) ────────────────
    if choice == "4":
        print(f"\n{BOLD}Step 3: Endpoint URL{RESET}\n")
        env["LLM_BASE_URL"] = _prompt(
            "Chat completions URL",
            hint="e.g. http://localhost:8000/v1/chat/completions",
        )
        if not env["LLM_BASE_URL"]:
            print(f"  {RED}Endpoint URL is required for custom providers.{RESET}")
            return 1

        print(f"\n{BOLD}Step 4: Model ID{RESET}\n")
        env["LLM_MODEL"] = _prompt(
            "Model identifier",
            hint="e.g. meta-llama/Llama-3-70b",
        )
        if not env["LLM_MODEL"]:
            print(f"  {RED}Model ID is required for custom providers.{RESET}")
            return 1
    else:
        print(f"\n{BOLD}Step 3: Confirm settings{RESET}\n")
        print(f"  Endpoint: {env['LLM_BASE_URL']}")
        print(f"  Model:    {env['LLM_MODEL']}")
        print(f"  Thinking: {env['LLM_THINKING']}")
        if "LLM_TIMEOUT" in env:
            print(f"  Timeout:  {env['LLM_TIMEOUT']}s")
        if not _confirm("Use these settings?"):
            env["LLM_BASE_URL"] = _prompt("Endpoint URL", default=env["LLM_BASE_URL"])
            env["LLM_MODEL"] = _prompt("Model ID", default=env["LLM_MODEL"])
            env["LLM_THINKING"] = _prompt(
                "Thinking mode",
                default=env["LLM_THINKING"],
                hint="deepseek / enable_thinking / none",
            )

    # ── Step: Write .env ─────────────────────────────────────────────────
    print(f"\n{BOLD}Writing .env...{RESET}\n")

    lines = [
        "# FPGA Agent - LLM Configuration",
        "# Generated by scripts/setup_env.py",
        "# This file is gitignored and will NOT be committed.",
        "",
    ]
    for key, value in env.items():
        if value:
            lines.append(f"export {key}={value}")

    with open(".env", "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  {GREEN}Written to .env:{RESET}\n")
    for key, value in env.items():
        if value:
            display = value if "KEY" not in key else value[:7] + "..." + value[-4:]
            print(f"    {key}={display}")

    # ── Done ─────────────────────────────────────────────────────────────
    print(f"\n{'=' * 50}")
    print(f"  {GREEN}{BOLD}Configuration saved.{RESET}\n")
    print(f"  Next steps:")
    print(f"    1. Verify:   {CYAN}python3 scripts/check_env.py --test-api{RESET}")
    print(f"    2. Run:      {CYAN}./run.sh --backend deepseek{RESET}")
    print(f"    3. Docker:   {CYAN}./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek{RESET}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
