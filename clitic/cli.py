from __future__ import annotations

import shutil

import typer
from typing_extensions import Annotated

from .analyzer import probe
from .scorer import run
from . import report as reporter

clitic_app = typer.Typer(
    name="clitic",
    help="Score a CLI tool for AI-agent readiness — the CLI Intelligence & Compliance Tester.",
    add_completion=False,
)

_DEMO_TOOL = "git"


def _score_tool(tool_name: str, as_json: bool) -> None:
    if not as_json:
        tool_probe = reporter.animate_probe(
            tool_name,
            probe,
            tool_name,
        )
    else:
        tool_probe = probe(tool_name)

    if tool_probe is None or tool_probe.tool_path is None:
        typer.echo(f"Error: '{tool_name}' not found in PATH", err=True)
        raise typer.Exit(1)

    result = run(tool_probe)

    if as_json:
        reporter.print_json(result)
    else:
        reporter.print_report(result)

    if result.overall_score < 60:
        raise typer.Exit(2)


@clitic_app.command()
def score(
    tool: Annotated[str, typer.Argument(help="CLI tool name or path (e.g. 'git', 'gh', 'curl')")],
    json: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Score a CLI tool for AI-agent readiness across 5 dimensions."""
    _score_tool(tool, json)


@clitic_app.command()
def demo(
    json: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Score 'git' as a demo — see how a real-world CLI tool fares for AI agents."""
    if shutil.which(_DEMO_TOOL) is None:
        typer.echo(f"Error: '{_DEMO_TOOL}' not found in PATH — install git to run the demo.", err=True)
        raise typer.Exit(1)
    _score_tool(_DEMO_TOOL, json)
