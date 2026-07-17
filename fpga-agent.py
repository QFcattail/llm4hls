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

    # Check Vitis
    import shutil
    if not shutil.which("vitis-run") and not args.force:
        print(
            "ERROR: vitis-run not found on PATH.\n"
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
        # Interactive task picker -> dashboard
        from textual.app import App
        from tui.task_picker import TaskPickerScreen

        tasks_root = ROOT / "contest" / "fpt26-harness" / "tasks"

        class PickerApp(App):
            def __init__(self):
                super().__init__()
                self.picker = TaskPickerScreen(tasks_root)

            def on_mount(self):
                self.push_screen(self.picker)

            def on_screen_suspend(self, screen):
                if isinstance(screen, TaskPickerScreen) and screen.selected:
                    task = screen.selected
                    self.exit(result=task)

        picker = PickerApp()
        result = picker.run()

        if result and isinstance(result, dict):
            task_path = result["path"]
            print(f"\nStarting agent on: {result['id']} [{result['type']}]\n")
            from tui.app import run_tui
            run_tui(task_path, backend=args.backend, budget=args.budget)
            return 0
        else:
            print("No task selected.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
