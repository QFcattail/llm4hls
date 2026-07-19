"""Task picker - interactive task selection screen.

Scans the harness tasks/ directory for task packages, lists them in a
Textual selection list, and also accepts a custom path typed by the user.
"""
from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, ListView, ListItem, Input
from textual.binding import Binding


def scan_tasks(root: Path) -> list[dict]:
    """Scan a directory for task packages (dirs containing task.toml).

    Args:
        root: Directory to scan (usually contest/fpt26-harness/tasks/).

    Returns:
        List of dicts: [{id, type, difficulty, budget, path, requires_cosim}]
    """
    import tomllib
    tasks = []
    if not root.exists():
        return tasks
    for d in sorted(root.iterdir()):
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
    return tasks


class TaskPickerScreen(Screen):
    """Interactive task selection screen.

    Shows a list of discovered tasks + an input for custom path.
    Selecting a task (Enter) or typing a path + Enter proceeds to the agent.
    """

    BINDINGS = [
        Binding("q", "request_quit", "Quit"),
        Binding("enter", "select", "Select"),
        Binding("escape", "request_quit", "Quit"),
    ]

    def action_request_quit(self) -> None:
        """Quit from picker directly (no agent running yet)."""
        self.app.exit()

    def __init__(self, tasks_root: Path | None = None) -> None:
        super().__init__()
        self.tasks_root = tasks_root or Path("contest/fpt26-harness/tasks")
        self._tasks: list[dict] = []
        self._selected: dict | None = None

    @property
    def selected(self) -> dict | None:
        """Return the selected task dict, or None if custom path was typed."""
        return self._selected

    def compose(self) -> ComposeResult:
        """Build the picker layout: title, task list, custom-path input."""
        yield Header(name="FPGA Agent - Select Task")
        with Vertical(id="picker"):
            yield Label("Select a task (↑↓ to navigate, Enter to start):",
                        id="picker-hint")
            yield ListView(id="task-list")
            yield Label("Or type a custom task path + Enter:", id="custom-hint")
            yield Input(placeholder="/path/to/task_dir", id="custom-path")
        yield Footer()

    def on_mount(self) -> None:
        """Load tasks on mount."""
        self._tasks = scan_tasks(self.tasks_root)
        lv = self.query_one("#task-list", ListView)
        for t in self._tasks:
            cosim_tag = " [cosim]" if t["requires_cosim"] else ""
            label = (
                f"{t['id']:<30} type={t['type']:<12} "
                f"diff={t['difficulty']} budget={t['budget']}{cosim_tag}"
            )
            lv.append(ListItem(Label(label), name=t["path"]))
        if not self._tasks:
            lv.append(ListItem(Label(
                f"(no tasks found in {self.tasks_root})"
            )))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle task list selection."""
        idx = event.list_view.index if event.list_view.index is not None else 0
        if idx < len(self._tasks):
            self._selected = self._tasks[idx]
            self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle custom path input."""
        path = event.value.strip()
        if path:
            toml = Path(path) / "task.toml"
            if toml.exists():
                import tomllib
                spec = tomllib.loads(toml.read_text())
                self._selected = {
                    "id": spec.get("task_id", Path(path).name),
                    "type": spec.get("task_type", "?"),
                    "difficulty": spec.get("difficulty", "?"),
                    "budget": spec.get("budget", "?"),
                    "path": path,
                    "requires_cosim": spec.get("requires_cosim", False),
                }
                self.app.pop_screen()
            else:
                self.query_one("#custom-path", Input).value = ""
                self.query_one("#picker-hint", Label).update(
                    f"[red]Not a valid task dir: {path} (no task.toml found)[/red]"
                )
