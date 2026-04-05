import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from .models import SandboxReport, ProbeResult

console = Console()

SEVERITY_ICONS = {
    "error": "[bold red]x[/]",
    "warning": "[yellow]![/]",
    "info": "[dim cyan]i[/]",
}

SEVERITY_STYLES = {
    "error": "bold red",
    "warning": "yellow",
    "info": "dim cyan",
}

METHOD_STYLES = {
    "get": "bold cyan",
    "post": "bold green",
    "put": "bold yellow",
    "patch": "yellow",
    "delete": "bold red",
    "head": "dim",
    "options": "dim",
}


def _feasibility_color(score: float) -> str:
    if score >= 80:
        return "bold green"
    if score >= 50:
        return "bold yellow"
    return "bold red"


def _status_cell(result: ProbeResult) -> Text:
    code = result.status_code
    if code is None:
        return Text("TIMEOUT", style="bold red")
    if code < 300:
        return Text(str(code), style="bold green")
    if code < 400:
        return Text(str(code), style="yellow")
    return Text(str(code), style="bold red")


def _result_cell(result: ProbeResult) -> Text:
    if result.success and not result.issues:
        return Text("OK", style="bold green")
    if result.success and result.issues:
        return Text("WARN", style="yellow")
    return Text("FAIL", style="bold red")


def print_report(report: SandboxReport) -> None:
    fc = _feasibility_color(report.feasibility_score)

    header = Text()
    header.append(f"  {report.api_name}", style="bold white")
    header.append(f"  v{report.api_version}", style="dim white")
    header.append(f"\n  Mock server: {report.base_url}", style="dim")
    header.append(f"\n\n  Endpoints probed:  ", style="white")
    header.append(str(report.total_endpoints), style="bold white")
    header.append(f"    Successful: ", style="white")
    header.append(str(report.successful), style="bold green")
    header.append(f"    Failed: ", style="white")
    header.append(str(report.total_endpoints - report.successful), style="bold red" if report.total_endpoints > report.successful else "bold green")
    header.append(f"\n  Feasibility Score: ", style="white")
    header.append(f"{report.feasibility_score}%", style=fc)

    console.print(Panel(header, title="[bold]Sandbox Probe Report[/]", border_style="bright_magenta"))

    # Results table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_magenta")
    table.add_column("Method", min_width=8)
    table.add_column("Path", min_width=28)
    table.add_column("Status", justify="center", min_width=7)
    table.add_column("Result", justify="center", min_width=7)
    table.add_column("Time (ms)", justify="right", min_width=9)
    table.add_column("Issues", justify="right", min_width=6)

    for r in report.results:
        method_style = METHOD_STYLES.get(r.method, "white")
        table.add_row(
            Text(r.method.upper(), style=method_style),
            r.path,
            _status_cell(r),
            _result_cell(r),
            f"{r.response_time_ms:.1f}" if r.response_time_ms is not None else "—",
            str(len(r.issues)) if r.issues else "",
        )

    console.print(table)

    # Issues section
    results_with_issues = [r for r in report.results if r.issues]
    if results_with_issues:
        console.print("\n[bold bright_magenta]Issues Found[/]")
        for r in results_with_issues:
            console.print(f"\n  [bold]{r.method.upper()} {r.path}[/]")
            for issue in r.issues:
                icon = SEVERITY_ICONS[issue.severity]
                style = SEVERITY_STYLES[issue.severity]
                console.print(f"    {icon} [{style}]{issue.message}[/]")

    # Request/response preview for failed probes
    failed = [r for r in report.results if not r.success]
    if failed:
        console.print("\n[bold bright_magenta]Failed Probe Details[/]")
        for r in failed:
            console.print(f"\n  [bold red]{r.method.upper()} {r.path}[/]  →  {r.request_url}")
            if r.request_body is not None:
                body_str = json.dumps(r.request_body, indent=2)
                console.print(f"  [dim]Request body:[/]")
                for line in body_str.splitlines()[:10]:
                    console.print(f"    [dim]{line}[/]")
            if r.response_body:
                console.print(f"  [dim]Response:[/] {str(r.response_body)[:200]}")

    console.print()


def print_endpoints(spec: dict, base_url: str) -> None:
    """Print the available mock endpoints (for the 'start' command)."""
    from scorecard.dimensions import get_operations
    import re

    operations = get_operations(spec)
    console.print(f"\n[bold bright_magenta]Available endpoints[/]  ([dim]{base_url}[/])\n")

    method_styles = METHOD_STYLES

    for path, method, op in operations:
        example_path = re.sub(r"\{(\w+)\}", r"[dim]<\1>[/]", path)
        method_str = method.upper().ljust(7)
        style = method_styles.get(method, "white")
        summary = op.get("summary", "")
        summary_str = f"  [dim]{summary}[/]" if summary else ""
        console.print(f"  [{style}]{method_str}[/]  {base_url}{example_path}{summary_str}")

    console.print()


def print_json(report: SandboxReport) -> None:
    console.print_json(report.model_dump_json(indent=2))
