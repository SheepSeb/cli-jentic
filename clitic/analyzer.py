from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field

TIMEOUT = 5.0  # seconds per probe run


@dataclass
class RunResult:
    args: list[str]
    exit_code: int
    stdout: str
    stderr: str
    elapsed: float
    timed_out: bool = False
    error: str | None = None


@dataclass
class ToolProbe:
    tool_name: str
    tool_path: str | None

    help_result: RunResult | None = None       # tool --help
    version_result: RunResult | None = None    # tool --version
    no_args_result: RunResult | None = None    # tool (no args)
    bad_args_result: RunResult | None = None   # tool --xxxxclitictest (unknown flag)
    json_results: list[RunResult] = field(default_factory=list)  # --json / --output json / etc.
    subcommand_names: list[str] = field(default_factory=list)
    subcommand_help_results: list[tuple[str, RunResult]] = field(default_factory=list)


def _run(cmd: list[str]) -> RunResult:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        elapsed = time.monotonic() - t0
        return RunResult(
            args=cmd,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed=elapsed,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - t0
        return RunResult(args=cmd, exit_code=-1, stdout="", stderr="", elapsed=elapsed, timed_out=True)
    except FileNotFoundError as exc:
        elapsed = time.monotonic() - t0
        return RunResult(args=cmd, exit_code=-1, stdout="", stderr="", elapsed=elapsed, error=str(exc))
    except Exception as exc:
        elapsed = time.monotonic() - t0
        return RunResult(args=cmd, exit_code=-1, stdout="", stderr="", elapsed=elapsed, error=str(exc))


def _extract_subcommands(help_text: str) -> list[str]:
    """Heuristically extract subcommand names from help text."""
    lines = help_text.splitlines()

    # Strategy 1: Named section headers (Commands:, Available Commands:, Subcommands:)
    in_commands_section = False
    section_subcommands: list[str] = []
    skip_words = {"usage", "options", "arguments", "flags", "help", "version", "global", "topics"}

    for line in lines:
        stripped = line.strip()
        if re.match(
            r"^(commands?|subcommands?|available commands?|sub-commands?)\s*:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_commands_section = True
            continue

        if in_commands_section:
            if not stripped:
                if section_subcommands:
                    break
                continue
            # New section header ends the commands section
            if line and not line[0].isspace() and re.search(r":\s*$", stripped):
                break
            match = re.match(r"^\s{1,8}([a-z][\w-]{0,30})\b", line)
            if match:
                candidate = match.group(1)
                if candidate.lower() not in skip_words:
                    section_subcommands.append(candidate)

    if section_subcommands:
        return section_subcommands[:8]

    # Strategy 2: Indented "word  Description" lines (git-style)
    pattern_subcommands: list[str] = []
    for line in lines:
        match = re.match(r"^\s{2,8}([a-z][\w-]{1,20})\s{2,}[A-Za-z]", line)
        if match:
            candidate = match.group(1)
            if candidate.lower() not in skip_words:
                pattern_subcommands.append(candidate)

    return pattern_subcommands[:8]


def probe(tool_name: str) -> ToolProbe:
    """Run all probes for a CLI tool and return a ToolProbe."""
    tool_path = shutil.which(tool_name)
    result = ToolProbe(tool_name=tool_name, tool_path=tool_path)

    if tool_path is None:
        return result  # tool not found; all results will be None

    cmd_base = [tool_path]

    # help probe
    result.help_result = _run(cmd_base + ["--help"])
    if result.help_result.exit_code != 0 and not result.help_result.error:
        alt = _run(cmd_base + ["-h"])
        if alt.exit_code == 0:
            result.help_result = alt

    # version probe
    result.version_result = _run(cmd_base + ["--version"])
    if result.version_result.exit_code != 0 and not result.version_result.error:
        alt = _run(cmd_base + ["-V"])
        if alt.exit_code == 0:
            result.version_result = alt

    # no-args probe
    result.no_args_result = _run(cmd_base)

    # bad args probe — unique flag an agent would never pass intentionally
    result.bad_args_result = _run(cmd_base + ["--xxxxclitictest-unknown"])

    # JSON output probes (try common patterns)
    for json_flag in [["--json"], ["--output", "json"], ["-o", "json"], ["--format", "json"]]:
        r = _run(cmd_base + json_flag)
        if not r.error:
            result.json_results.append(r)

    # Subcommand discovery
    help_text = (result.help_result.stdout or "") + (result.help_result.stderr or "")
    result.subcommand_names = _extract_subcommands(help_text)

    # Probe first few subcommands' help
    for sub in result.subcommand_names[:3]:
        sub_help = _run(cmd_base + [sub, "--help"])
        result.subcommand_help_results.append((sub, sub_help))

    return result
