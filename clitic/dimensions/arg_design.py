from __future__ import annotations

import re

from ..models import DimensionResult, Issue
from ..analyzer import ToolProbe

NAME = "Argument & Interface Design"


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def score(probe: ToolProbe) -> DimensionResult:
    issues: list[Issue] = []
    total_score = 0.0

    hr = probe.help_result
    if hr is None:
        return DimensionResult(name=NAME, score=0, issues=[
            Issue(severity="error", message="Tool not found — cannot assess argument design", location="tool")
        ])

    help_text = _strip_ansi((hr.stdout or "") + (hr.stderr or ""))
    help_lower = help_text.lower()

    long_flags = re.findall(r"--[\w-]+", help_text)
    short_flags = re.findall(r"(?<!\-)(?<!\w)-[a-zA-Z]\b", help_text)

    # 1. GNU-style long flags (--flag) present — 25 pts
    if len(long_flags) >= 2:
        total_score += 25
    elif len(long_flags) == 1:
        total_score += 12
        issues.append(Issue(
            severity="warning",
            message="Only one long flag detected — prefer GNU-style --flags for agent-readable invocations",
            location="flags",
        ))
    else:
        issues.append(Issue(
            severity="warning",
            message="No GNU-style long flags (--flag) detected — agents benefit from descriptive flag names",
            location="flags",
        ))

    # 2. Flags are kebab-case, not camelCase — 20 pts
    camel_flags = [f for f in long_flags if re.search(r"--[a-z]+[A-Z]", f)]
    if not camel_flags:
        total_score += 20
    else:
        issues.append(Issue(
            severity="warning",
            message=f"camelCase flags detected ({', '.join(camel_flags[:3])}) — prefer kebab-case (--my-flag) by convention",
            location="flags",
        ))

    # 3. Standard flags present (--verbose, --help, --quiet) — 25 pts
    standard = {
        "--verbose / -v": ["--verbose", "-v ", "--debug"],
        "--help / -h":    ["--help", "-h "],
        "--quiet / -q":   ["--quiet", "-q ", "--silent"],
    }
    found = sum(
        1 for variants in standard.values()
        if any(v in help_lower for v in variants)
    )
    total_score += (found / len(standard)) * 25
    if found < 2:
        missing = [k for k, variants in standard.items() if not any(v in help_lower for v in variants)]
        issues.append(Issue(
            severity="info",
            message=f"Missing standard flags: {', '.join(missing)} — standard flags aid agent discoverability",
            location="flags",
        ))

    # 4. Both short and long flag forms — 15 pts
    if long_flags and short_flags:
        total_score += 15
    elif long_flags:
        total_score += 8
        issues.append(Issue(
            severity="info",
            message="No short flag aliases (-x) detected — short aliases improve usability in agent-generated commands",
            location="flags",
        ))

    # 5. Config / environment variable documentation — 15 pts
    config_keywords = ["config", "env", "environment", ".env", "configuration", "settings", "$ "]
    if any(kw in help_lower for kw in config_keywords):
        total_score += 15
    else:
        issues.append(Issue(
            severity="info",
            message="No mention of config files or environment variables — agents benefit from knowing all configuration methods",
            location="--help output",
        ))

    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
