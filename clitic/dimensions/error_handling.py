from __future__ import annotations

import re

from ..models import DimensionResult, Issue
from ..analyzer import ToolProbe

NAME = "Error Handling"


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _looks_like_traceback(text: str) -> bool:
    patterns = [
        r"Traceback \(most recent call last\)",
        r'^\s+File ".*", line \d+',
        r"^\s+at \w+[\.\w]+ \(",  # JS/Java
        r"\w+Error:",
        r"Exception in thread",
    ]
    return any(re.search(p, text, re.MULTILINE) for p in patterns)


def _error_is_informative(text: str) -> bool:
    clean = _strip_ansi(text).lower().strip()
    if not clean or len(clean) < 20:
        return False
    helpful_keywords = ["usage", "try", "see", "run", "--help", "expected", "unknown",
                        "unrecognized", "invalid", "error:", "did you mean"]
    return any(kw in clean for kw in helpful_keywords)


def score(probe: ToolProbe) -> DimensionResult:
    issues: list[Issue] = []
    total_score = 0.0

    br = probe.bad_args_result
    if br is None or br.error:
        return DimensionResult(name=NAME, score=50, issues=[
            Issue(severity="info", message="Could not probe error handling — tool unavailable", location="error probe")
        ])

    stdout_clean = _strip_ansi(br.stdout or "")
    stderr_clean = _strip_ansi(br.stderr or "")
    combined = stdout_clean + stderr_clean

    # 1. Error output goes to stderr — 30 pts
    if br.exit_code != 0:
        if stderr_clean.strip():
            total_score += 30
        elif stdout_clean.strip():
            total_score += 15
            issues.append(Issue(
                severity="warning",
                message="Error message printed to stdout instead of stderr — agents parsing stdout may misinterpret it as valid output",
                location="stderr",
            ))
        else:
            issues.append(Issue(
                severity="warning",
                message="Bad args produced no error output at all",
                location="stderr",
            ))

    # 2. Error message is informative — 40 pts
    if _error_is_informative(combined):
        total_score += 40
    elif combined.strip():
        total_score += 20
        issues.append(Issue(
            severity="warning",
            message="Error message for unknown flag is minimal — agents need clear guidance on what went wrong",
            location="error message",
        ))
    else:
        issues.append(Issue(
            severity="error",
            message="No error message for invalid flag — agents cannot diagnose the failure",
            location="error message",
        ))

    # 3. No stack trace exposed — 30 pts
    if not _looks_like_traceback(combined):
        total_score += 30
    else:
        issues.append(Issue(
            severity="error",
            message="Stack trace exposed on invalid input — leaks internals and confuses agents parsing errors",
            location="stderr",
        ))

    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
