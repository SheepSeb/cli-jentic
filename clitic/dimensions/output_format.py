from __future__ import annotations

import json
import re

from ..models import DimensionResult, Issue
from ..analyzer import ToolProbe

NAME = "Machine-Readable Output"


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _is_valid_json(text: str) -> bool:
    try:
        parsed = json.loads(text.strip())
        return isinstance(parsed, (dict, list))
    except (json.JSONDecodeError, ValueError):
        return False


def score(probe: ToolProbe) -> DimensionResult:
    issues: list[Issue] = []
    total_score = 0.0

    help_text = ""
    if probe.help_result:
        help_text = _strip_ansi(
            (probe.help_result.stdout or "") + (probe.help_result.stderr or "")
        ).lower()

    # 1. Help mentions JSON/structured output — 20 pts
    json_keywords = ["--json", "--output", "--format", "-o json", "json output", "structured"]
    mentions_json = any(kw in help_text for kw in json_keywords)
    if mentions_json:
        total_score += 20
    else:
        issues.append(Issue(
            severity="warning",
            message="No mention of JSON or structured output flags in help text — agents rely on parseable output",
            location="--help output",
        ))

    # 2. JSON flag actually produces valid JSON — 50 pts
    json_produced = False
    for r in probe.json_results:
        stdout = (r.stdout or "").strip()
        if stdout and _is_valid_json(stdout):
            json_produced = True
            if r.exit_code == 0:
                total_score += 50
            else:
                total_score += 35
                issues.append(Issue(
                    severity="warning",
                    message="JSON output produced but exit code is non-zero",
                    location=" ".join(r.args[1:]),
                ))
            break

    if not json_produced:
        if mentions_json:
            issues.append(Issue(
                severity="error",
                message="Help mentions JSON output but none of the JSON flags produced valid JSON in this probe",
                location="--json / --output json / --format json",
            ))
        else:
            issues.append(Issue(
                severity="error",
                message="No JSON output support detected — agents cannot reliably parse tool output",
                location="--json / --output json / --format json",
            ))

    # 3. No unconditional ANSI codes in normal stdout — 15 pts
    no_args = probe.no_args_result
    if no_args and no_args.stdout:
        if not re.search(r"\x1b\[", no_args.stdout):
            total_score += 15
        else:
            issues.append(Issue(
                severity="warning",
                message="Tool emits ANSI color codes unconditionally — may corrupt agent input pipelines when piped",
                location="stdout",
            ))
    else:
        total_score += 15  # nothing to check — not penalized

    # 4. Subcommands also mention output flags — 15 pts
    if probe.subcommand_help_results:
        with_output_flags = sum(
            1
            for _, r in probe.subcommand_help_results
            if any(
                kw in _strip_ansi((r.stdout or "") + (r.stderr or "")).lower()
                for kw in ["--json", "--output", "--format"]
            )
        )
        ratio = with_output_flags / len(probe.subcommand_help_results)
        total_score += 15 * ratio
        if ratio < 0.5:
            issues.append(Issue(
                severity="warning",
                message=f"Only {with_output_flags}/{len(probe.subcommand_help_results)} subcommands mention output format flags",
                location="<subcommand> --help",
            ))
    else:
        total_score += 15  # no subcommands to penalize

    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
