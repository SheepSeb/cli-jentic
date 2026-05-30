import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from .models import ScorecardReport

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


def _score_color(score: float) -> str:
    if score >= 80:
        return "bold green"
    if score >= 60:
        return "bold yellow"
    return "bold red"


def _grade_style(grade: str) -> str:
    if grade == "A":
        return "bold green"
    if grade == "B":
        return "green"
    if grade == "C":
        return "yellow"
    if grade == "D":
        return "bold yellow"
    return "bold red"


def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    color = _score_color(score)
    return f"[{color}]{bar}[/]"


def print_report(report: ScorecardReport) -> None:
    # Header
    header = Text()
    header.append(f"  {report.api_name}", style="bold white")
    header.append(f"  v{report.api_version}", style="dim white")
    header.append(f"\n  {report.spec_path}", style="dim")

    overall_color = _score_color(report.overall_score)
    grade_style = _grade_style(report.grade)

    score_line = Text()
    score_line.append(f"\n  Overall Score: ", style="white")
    score_line.append(f"{report.overall_score:.1f}/100", style=overall_color)
    score_line.append(f"  Grade: ", style="white")
    score_line.append(report.grade, style=grade_style)

    console.print(Panel(Text.assemble(header, score_line), title="[bold]specscore[/] · OpenAPI AI readiness", border_style="bright_blue"))

    # Dimension table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_blue")
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
        console.print("\n[bold bright_blue]Issues & Recommendations[/]")
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
        console.print("\n[bold green]No issues found — this API is well-prepared for AI agents![/]")

    console.print()


def print_json(report: ScorecardReport) -> None:
    console.print_json(report.model_dump_json(indent=2))
