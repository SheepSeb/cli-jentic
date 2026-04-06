from __future__ import annotations

from ..models import DimensionResult, Issue
from ..analyzer import ToolProbe

NAME = "Exit Code Semantics"


def score(probe: ToolProbe) -> DimensionResult:
    issues: list[Issue] = []
    total_score = 0.0

    # 1. --help exits 0 — 25 pts
    hr = probe.help_result
    if hr and not hr.timed_out and not hr.error:
        if hr.exit_code == 0:
            total_score += 25
        else:
            issues.append(Issue(
                severity="warning",
                message=f"--help exits {hr.exit_code} instead of 0 — agents interpret non-zero as failure",
                location="--help exit code",
            ))

    # 2. --version exits 0 — 20 pts
    vr = probe.version_result
    if vr and not vr.timed_out and not vr.error:
        if vr.exit_code == 0:
            total_score += 20
        else:
            issues.append(Issue(
                severity="warning",
                message=f"--version exits {vr.exit_code} instead of 0",
                location="--version exit code",
            ))
    else:
        total_score += 10  # --version absent — partial credit, not a fatal flaw

    # 3. Unknown flag exits non-zero — 35 pts
    br = probe.bad_args_result
    if br and not br.timed_out and not br.error:
        if br.exit_code != 0:
            total_score += 35
        else:
            issues.append(Issue(
                severity="error",
                message="Unknown flag '--xxxxclitictest-unknown' returned exit 0 — agents cannot detect invalid invocations",
                location="bad args exit code",
            ))

    # 4. No-args behavior is intentional — 20 pts
    nar = probe.no_args_result
    if nar and not nar.timed_out and not nar.error:
        combined = (nar.stdout or "") + (nar.stderr or "")
        if combined.strip():
            total_score += 20  # produces output (help or usage error) — intentional
        elif nar.exit_code == 0:
            total_score += 10
            issues.append(Issue(
                severity="info",
                message="Running with no args produces no output and exits 0 — consider showing usage or help",
                location="no-args exit code",
            ))
        else:
            issues.append(Issue(
                severity="warning",
                message="No-args invocation is silent with non-zero exit — agents cannot tell what went wrong",
                location="no-args exit code",
            ))

    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
