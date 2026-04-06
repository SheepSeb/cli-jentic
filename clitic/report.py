from __future__ import annotations

import os
import sys
import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from .models import CLIToolReport

console = Console()

SEVERITY_STYLES = {
    "error": "bold red",
    "warning": "yellow",
    "info": "dim cyan",
}

SEVERITY_ICONS = {
    "error": "[bold red]x[/]",
    "warning": "[yellow]![/]",
    "info": "[dim cyan]i[/]",
}

# clitic logo frames — the (*) star pulses in and out
_LOGO_FRAMES = [
    "[bold magenta]([/][bold bright_magenta] [/][bold magenta])[/]",
    "[bold magenta]([/][bold bright_white]*[/][bold magenta])[/]",
    "[bold magenta]([/][bold bright_magenta]*[/][bold magenta])[/]",
    "[bold magenta]([/][bold bright_yellow]*[/][bold magenta])[/]",
    "[bold magenta]([/][bold bright_magenta]*[/][bold magenta])[/]",
    "[bold magenta]([/][bold bright_white]*[/][bold magenta])[/]",
    "[bold magenta]([/][bold bright_magenta] [/][bold magenta])[/]",
]

_LOGO_STATIC = "[bold magenta]([/][bold bright_yellow]*[/][bold magenta])[/]"

_TITLE = "[bold bright_magenta]clitic[/][dim] — CLI Intelligence & Compliance Tester[/]"

_PHASE_MESSAGES = [
    ("Feeding", "[bold magenta]Feeding[/] [white]cli tool[/] into the tester..."),
    ("Eating",  "[bold bright_magenta]Eating[/] [white]cli tool[/] [dim](nom nom nom)[/]..."),
    ("Digesting results",    "[dim]Digesting[/] the results for [white]cli tool[/]..."),
]


_MIN_ANIMATION_SECS = 2.0  # always show animation for at least this long


def _cli_tool_display_name(tool_name: str) -> str:
    """Short command name for UI (basename when *tool_name* is a path)."""
    base = os.path.basename(tool_name.strip())
    return base or tool_name


def animate_probe(tool_name: str, fn, *args, **kwargs):
    """Run *fn* while showing the animated logo and probe phases."""
    # Don't animate if stdout is not a TTY (e.g. --json piped output)
    if not sys.stdout.isatty():
        return fn(*args, **kwargs)

    import threading

    phases = _PHASE_MESSAGES
    frame_idx = 0
    phase_idx = 0
    phase_ticks = [8, 8, 4]  # ticks per phase (each tick ~0.12 s)
    tick = 0

    result_holder: list = []
    worker_done = threading.Event()

    def _worker():
        result_holder.append(fn(*args, **kwargs))
        worker_done.set()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    start_time = time.monotonic()

    with Live(console=console, refresh_per_second=8) as live:
        while True:
            elapsed = time.monotonic() - start_time
            if worker_done.is_set() and elapsed >= _MIN_ANIMATION_SECS:
                break

            logo = _LOGO_FRAMES[frame_idx % len(_LOGO_FRAMES)]
            _, phase_tmpl = phases[min(phase_idx, len(phases) - 1)]
            phase_msg = phase_tmpl.format(tool=_cli_tool_display_name(tool_name))
            live.update(Text.from_markup(f"  {logo}  {phase_msg}"))

            time.sleep(0.12)
            frame_idx += 1
            tick += 1

            if phase_idx < len(phases) - 1 and tick >= sum(phase_ticks[: phase_idx + 1]):
                phase_idx += 1

    thread.join()
    console.print()  # blank line after animation
    return result_holder[0] if result_holder else None


def _score_color(score: float) -> str:
    if score >= 80:
        return "bold green"
    if score >= 60:
        return "bold yellow"
    return "bold red"


def _grade_style(grade: str) -> str:
    styles = {"A": "bold green", "B": "green", "C": "yellow", "D": "bold yellow"}
    return styles.get(grade, "bold red")


def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{_score_color(score)}]{bar}[/]"


def print_report(report: CLIToolReport) -> None:
    # Header panel
    header = Text()
    header.append(f"  {report.tool_name}", style="bold white")
    header.append(f"\n  {report.tool_path}", style="dim")

    score_line = Text()
    score_line.append(f"\n  Overall Score: ", style="white")
    score_line.append(f"{report.overall_score:.1f}/100", style=_score_color(report.overall_score))
    score_line.append("  Grade: ", style="white")
    score_line.append(report.grade, style=_grade_style(report.grade))

    console.print(Panel(
        Text.assemble(header, score_line),
        title=f"{_LOGO_STATIC}  {_TITLE}",
        border_style="bright_magenta",
    ))

    # Dimension table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_magenta")
    table.add_column("Dimension", style="white", min_width=32)
    table.add_column("Score", justify="right", min_width=10)
    table.add_column("Grade", justify="center", min_width=6)
    table.add_column("Progress", min_width=22)
    table.add_column("Issues", justify="right", min_width=6)

    for dim in report.dimensions:
        table.add_row(
            dim.name,
            Text(f"{dim.score:.1f}/100", style=_score_color(dim.score)),
            Text(dim.grade, style=_grade_style(dim.grade)),
            _score_bar(dim.score),
            str(len(dim.issues)),
        )

    console.print(table)

    # Issues per dimension
    any_issues = any(dim.issues for dim in report.dimensions)
    if any_issues:
        console.print(f"\n[bold bright_magenta]Issues & Recommendations[/]")
        for dim in report.dimensions:
            if not dim.issues:
                continue
            console.print(f"\n  [bold]{dim.name}[/]")
            for issue in dim.issues:
                icon = SEVERITY_ICONS[issue.severity]
                style = SEVERITY_STYLES[issue.severity]
                console.print(f"    {icon} [{style}]{issue.message}[/]")
                console.print(f"       [dim]{issue.location}[/]")
    else:
        console.print("\n[bold green]No issues — this CLI tool is well-prepared for AI agents![/]")

    console.print()


def print_json(report: CLIToolReport) -> None:
    console.print_json(report.model_dump_json(indent=2))
