#!/usr/bin/env python3
"""FPGA Agent - one-line entry point.

Launches the interactive TUI: task picker -> agent dashboard.

Usage:
    python3 fpga-agent.py                    # interactive task picker + TUI
    python3 fpga-agent.py --task <path>      # skip picker, go straight to TUI
    python3 fpga-agent.py --backend scripted # choose backend (default: deepseek)
    python3 fpga-agent.py --no-tui           # plain CLI mode (no TUI)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "contest" / "fpt26-harness"))


def _pick_task_interactive() -> str | None:
    """Interactive task picker using plain print+input (no Textual).

    Scans contest/fpt26-harness/tasks/ and lists found tasks.
    User picks by number or types a custom path.
    Returns the task directory path, or None if cancelled.

    Uses plain terminal I/O (NOT Textual) to avoid running two Textual
    App instances in one process, which causes a black screen.
    """
    import tomllib

    tasks_root = ROOT / "contest" / "fpt26-harness" / "tasks"
    tasks: list[dict] = []

    # Scan for tasks
    if tasks_root.exists():
        for d in sorted(tasks_root.iterdir()):
            toml = d / "task.toml"
            if not toml.exists():
                continue
            try:
                spec = tomllib.loads(toml.read_text())
                tasks.append({
                    "id": spec.get("task_id", d.name),
                    "type": spec.get("task_type", "?"),
                    "difficulty": spec.get("difficulty", "?"),
                    "budget": spec.get("budget", "?"),
                    "path": str(d),
                    "requires_cosim": spec.get("requires_cosim", False),
                })
            except Exception:
                continue

    print("\n" + "=" * 60)
    print("  FPGA Agent - Select a Task")
    print("=" * 60)

    if tasks:
        for i, t in enumerate(tasks, 1):
            cosim_tag = " [cosim]" if t["requires_cosim"] else ""
            print(f"  {i}. {t['id']:<30} type={t['type']:<12} "
                  f"diff={t['difficulty']} budget={t['budget']}{cosim_tag}")
        print(f"  0. Cancel")
    else:
        print("  (no tasks found in tasks/)")

    print()
    try:
        choice = input("Enter number (or type a task path): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if not choice or choice == "0":
        return None

    # Numeric selection
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(tasks):
            t = tasks[idx]
            print(f"\n  -> Selected: {t['id']} [{t['type']}]\n")
            return t["path"]
        else:
            print(f"  Invalid number: {choice}")
            return None

    # Custom path
    toml_path = Path(choice) / "task.toml"
    if toml_path.exists():
        try:
            spec = tomllib.loads(toml_path.read_text())
            print(f"\n  -> Selected: {spec.get('task_id', Path(choice).name)} "
                  f"[{spec.get('task_type', '?')}]\n")
            return choice
        except Exception:
            pass

    print(f"  Not a valid task dir: {choice} (no task.toml found)")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FPGA Agent - LLM4HLS repair & optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--task", default=None,
                    help="task directory path (skip interactive picker)")
    ap.add_argument("--backend", choices=["scripted", "deepseek", "openrouter"],
                    default="deepseek", help="LLM backend (default: deepseek)")
    ap.add_argument("--budget", type=int, default=None,
                    help="override credit budget")
    ap.add_argument("--no-tui", action="store_true",
                    help="plain CLI mode (no TUI dashboard)")
    ap.add_argument("--force", action="store_true",
                    help="run without Vitis (csim will fail, framework test only)")
    args = ap.parse_args()

    # Auto-source Vitis if vitis-run is not on PATH but settings64.sh exists.
    # This saves the user from having to manually source it every terminal session.
    import shutil
    if not shutil.which("vitis-run") and not args.force:
        candidates = [
            "/home/admin/Xilinx/2025.2/Vitis/settings64.sh",
            str(ROOT / "Xilinx/2025.2/Vitis/settings64.sh"),
        ]
        sourced = False
        for settings in candidates:
            if Path(settings).exists():
                import subprocess
                # Source it and capture the resulting PATH
                result = subprocess.run(
                    ["bash", "-c", f"source '{settings}' && echo $PATH"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    os.environ["PATH"] = result.stdout.strip()
                    sourced = True
                    break
        if not sourced:
            print(
                "ERROR: vitis-run not found and could not auto-source Vitis.\n"
                "  Source Vitis settings64.sh first:\n"
                "    source /home/admin/Xilinx/2025.2/Vitis/settings64.sh\n"
                "  Or use --force for framework testing (csim will fail).",
                file=sys.stderr,
            )
            return 1

    if args.no_tui:
        # Plain CLI mode - delegate to run_agent.py
        import subprocess
        cmd = [sys.executable, str(ROOT / "scripts" / "run_agent.py")]
        if args.task:
            cmd.append(args.task)
        else:
            print("Error: --task required in --no-tui mode", file=sys.stderr)
            return 1
        cmd.extend(["--backend", args.backend])
        if args.budget is not None:
            cmd.extend(["--budget", str(args.budget)])
        if args.force:
            cmd.append("--force")
        return subprocess.call(cmd)

    # TUI mode
    if args.task:
        # Skip picker, go straight to dashboard
        from tui.app import run_tui
        run_tui(args.task, backend=args.backend, budget=args.budget)
        return 0
    else:
        # Interactive task picker (plain terminal, NOT Textual)
        task_path = _pick_task_interactive()
        if task_path is None:
            print("No task selected.")
            return 0
        from tui.app import run_tui
        run_tui(task_path, backend=args.backend, budget=args.budget)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
