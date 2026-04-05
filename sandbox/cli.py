from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import typer
from typing_extensions import Annotated
from werkzeug.serving import make_server

from scorecard.parser import load_spec
from .server import create_app
from .prober import probe_all
from .models import SandboxReport
from . import report as reporter

sandbox_app = typer.Typer(
    name="sandbox",
    help="Run a mock server from an OpenAPI spec and probe its endpoints.",
    add_completion=False,
)

_SAMPLE_SPEC = Path(__file__).parent / "data" / "sample_spec.yaml"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _find_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((DEFAULT_HOST, preferred))
            return preferred
        except OSError:
            s.bind((DEFAULT_HOST, 0))
            return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _load(spec_path: str) -> dict:
    try:
        return load_spec(spec_path)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"Error parsing spec: {exc}", err=True)
        raise typer.Exit(1)


@sandbox_app.command()
def start(
    spec: Annotated[str, typer.Argument(help="Path to OpenAPI spec file (JSON or YAML)")],
    port: Annotated[int, typer.Option("--port", "-p", help="Port to listen on")] = DEFAULT_PORT,
) -> None:
    """Start a local mock server from an OpenAPI spec. Press Ctrl+C to stop."""
    spec_dict = _load(spec)
    port = _find_free_port(port)
    base_url = f"http://{DEFAULT_HOST}:{port}"

    app = create_app(spec_dict)

    reporter.console.print(f"\n[bold bright_magenta]Sandbox Mock Server[/]")
    reporter.console.print(f"  Spec:  [dim]{spec}[/]")
    reporter.console.print(f"  URL:   [bold]{base_url}[/]\n")
    reporter.print_endpoints(spec_dict, base_url)
    reporter.console.print("[dim]Press Ctrl+C to stop.[/]\n")

    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    srv = make_server(DEFAULT_HOST, port, app)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        reporter.console.print("\n[dim]Server stopped.[/]")


def _probe(spec: str, port: int, as_json: bool) -> None:
    spec_dict = _load(spec)
    port = _find_free_port(port)
    base_url = f"http://{DEFAULT_HOST}:{port}"

    flask_app = create_app(spec_dict)

    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    srv = make_server(DEFAULT_HOST, port, flask_app)
    server_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    server_thread.start()

    if not _wait_for_server(DEFAULT_HOST, port):
        typer.echo("Error: mock server failed to start", err=True)
        raise typer.Exit(1)

    try:
        if not as_json:
            reporter.console.print(f"[dim]Mock server started at {base_url}. Probing endpoints...[/]\n")
        results = probe_all(spec_dict, base_url)
    finally:
        srv.shutdown()

    info = spec_dict.get("info") or {}
    sandbox_report = SandboxReport(
        api_name=info.get("title") or "Unknown API",
        api_version=str(info.get("version") or "unknown"),
        spec_path=spec,
        base_url=base_url,
        total_endpoints=len(results),
        results=results,
    )

    if as_json:
        reporter.print_json(sandbox_report)
    else:
        reporter.print_report(sandbox_report)

    if sandbox_report.feasibility_score < 50:
        raise typer.Exit(2)


@sandbox_app.command()
def probe(
    spec: Annotated[str, typer.Argument(help="Path to OpenAPI spec file (JSON or YAML)")],
    port: Annotated[int, typer.Option("--port", "-p", help="Port for the internal mock server")] = DEFAULT_PORT,
    json: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Auto-probe all endpoints against an internal mock server and show a feasibility report."""
    _probe(spec=spec, port=port, as_json=json)


@sandbox_app.command()
def demo(
    json: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Probe the built-in sample spec (shows typical sandbox results)."""
    if not _SAMPLE_SPEC.exists():
        typer.echo("Error: sample_spec.yaml not found.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Running sandbox probe on built-in sample spec: {_SAMPLE_SPEC}\n")
    _probe(spec=str(_SAMPLE_SPEC), port=DEFAULT_PORT, as_json=json)
