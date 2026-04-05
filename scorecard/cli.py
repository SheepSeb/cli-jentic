from __future__ import annotations

import sys
from pathlib import Path

import typer
from typing_extensions import Annotated

from .parser import load_spec
from .scorer import run
from . import report as reporter

app = typer.Typer(
    name="api-scorecard",
    help="Score an OpenAPI spec for AI-readiness across 6 dimensions.",
    add_completion=False,
)

_SAMPLE_SPEC = Path(__file__).parent.parent / "sample_spec.yaml"


def _run_and_output(spec_path: str, as_json: bool) -> None:
    try:
        spec = load_spec(spec_path)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"Error parsing spec: {exc}", err=True)
        raise typer.Exit(1)

    result = run(spec, spec_path)

    if as_json:
        reporter.print_json(result)
    else:
        reporter.print_report(result)

    if result.overall_score < 60:
        raise typer.Exit(2)  # Non-zero exit for failing grade


@app.command()
def score(
    spec: Annotated[str, typer.Argument(help="Path to OpenAPI spec file (JSON or YAML)")],
    json: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Score an OpenAPI spec file for AI-readiness."""
    _run_and_output(spec, json)


@app.command()
def demo(
    json: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Run the scorecard against the built-in sample spec (shows typical issues)."""
    if not _SAMPLE_SPEC.exists():
        typer.echo("Error: sample_spec.yaml not found.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Running scorecard on built-in sample spec: {_SAMPLE_SPEC}\n")
    _run_and_output(str(_SAMPLE_SPEC), json)
