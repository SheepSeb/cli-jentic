from __future__ import annotations

import re

from ..models import DimensionResult, Issue
from ..analyzer import ToolProbe

NAME = "Help & Discoverability"


def score(probe: ToolProbe) -> DimensionResult:
    issues: list[Issue] = []
    total_score = 0.0

    hr = probe.help_result
    if hr is None:
        issues.append(Issue(severity="error", message="Tool not found in PATH", location="tool"))
        return DimensionResult(name=NAME, score=0, issues=issues)

    # 1. --help works (exit 0) — 30 pts
    if hr.timed_out:
        issues.append(Issue(
            severity="error",
            message="--help timed out — tool hangs on --help, agents cannot introspect it",
            location="--help",
        ))
    elif hr.exit_code == 0:
        total_score += 30
    else:
        combined = (hr.stdout or "") + (hr.stderr or "")
        if len(combined.strip()) > 50:
            total_score += 15  # help text exists but exit code is wrong
            issues.append(Issue(
                severity="warning",
                message=f"--help exits {hr.exit_code} instead of 0 — agents may interpret this as failure",
                location="--help",
            ))
        else:
            issues.append(Issue(
                severity="error",
                message="--help produced no useful output or failed entirely",
                location="--help",
            ))

    # 2. Help text is substantial — 20 pts
    help_text = (hr.stdout or "") + (hr.stderr or "")
    help_clean = re.sub(r"\x1b\[[0-9;]*m", "", help_text).strip()
    if len(help_clean) >= 100:
        total_score += 20
    elif len(help_clean) >= 40:
        total_score += 10
        issues.append(Issue(
            severity="warning",
            message=f"Help text is very short ({len(help_clean)} chars) — agents need context to invoke the tool correctly",
            location="--help output",
        ))
    else:
        issues.append(Issue(
            severity="error",
            message="Help text is minimal or absent",
            location="--help output",
        ))

    # 3. Subcommands listed — 20 pts
    if probe.subcommand_names:
        total_score += 20
    else:
        if len(help_clean) > 200:
            total_score += 10  # likely a focused single-command tool
            issues.append(Issue(
                severity="info",
                message="No subcommands detected — if this is a multi-command tool, explicit subcommand listing helps agents discover capabilities",
                location="--help output",
            ))
        else:
            issues.append(Issue(
                severity="info",
                message="No subcommands detected in help output",
                location="--help output",
            ))

    # 4. --version works — 15 pts
    vr = probe.version_result
    if vr and vr.exit_code == 0 and (vr.stdout or vr.stderr).strip():
        total_score += 15
    elif vr and not vr.error:
        issues.append(Issue(
            severity="warning",
            message="--version flag missing or non-functional — agents cannot verify tool version for compatibility checks",
            location="--version",
        ))

    # 5. Subcommand --help works — 15 pts
    if probe.subcommand_help_results:
        working = sum(1 for _, r in probe.subcommand_help_results if r.exit_code == 0)
        ratio = working / len(probe.subcommand_help_results)
        total_score += 15 * ratio
        if ratio < 1.0:
            issues.append(Issue(
                severity="warning",
                message=f"{len(probe.subcommand_help_results) - working}/{len(probe.subcommand_help_results)} subcommands don't respond to --help",
                location="<subcommand> --help",
            ))
    else:
        total_score += 15  # no subcommands to test — not penalized

    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
