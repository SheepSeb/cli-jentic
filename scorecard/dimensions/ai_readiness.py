# Derived from the Jentic API AI-Readiness Framework (JAIRF)
# Copyright (c) 2025-2026 Jentic. Licensed under the Apache License, Version 2.0.
# Modifications copyright (c) 2025-2026 SheepSeb.
from ..models import DimensionResult, Issue
from . import get_operations, pct_score

NAME = "AI-Readiness & Agent Experience"


def _has_response_schema(op: dict) -> bool:
    for resp in op.get("responses", {}).values():
        if not isinstance(resp, dict):
            continue
        for media in (resp.get("content") or {}).values():
            if isinstance(media, dict) and media.get("schema"):
                return True
    return False


def _count_schema_props_with_desc(schema: dict) -> tuple[int, int]:
    """Returns (described, total) property counts for a schema."""
    if not isinstance(schema, dict):
        return 0, 0
    described = 0
    total = 0
    for prop in (schema.get("properties") or {}).values():
        if isinstance(prop, dict) and "$ref" not in prop:
            total += 1
            if prop.get("description"):
                described += 1
    return described, total


def score(spec: dict) -> DimensionResult:
    issues: list[Issue] = []
    operations = get_operations(spec)

    if not operations:
        return DimensionResult(name=NAME, score=0, issues=[
            Issue(severity="error", message="No operations found to evaluate", location="paths")
        ])

    total = len(operations)

    # Meaningful descriptions >30 chars (25 pts)
    meaningful = sum(
        1 for _, _, op in operations
        if len((op.get("description") or "").strip()) > 30
    )
    desc_score = pct_score(meaningful, total, 25)
    if meaningful < total:
        issues.append(Issue(
            severity="warning" if meaningful / total >= 0.4 else "error",
            message=f"{total - meaningful}/{total} operations lack descriptive intent (need >30 char description)",
            location="paths.*.*.description",
        ))

    # Error responses (4xx/5xx) documented (30 pts)
    with_errors = sum(
        1 for _, _, op in operations
        if any(str(code).startswith(("4", "5")) for code in op.get("responses", {}).keys())
    )
    err_score = pct_score(with_errors, total, 30)
    if with_errors < total:
        issues.append(Issue(
            severity="error" if with_errors / total < 0.3 else "warning",
            message=f"{total - with_errors}/{total} operations have no documented error responses (4xx/5xx) — agents cannot handle failure gracefully",
            location="paths.*.*.responses",
        ))

    # Response schemas defined (25 pts)
    with_schema = sum(1 for _, _, op in operations if _has_response_schema(op))
    schema_score = pct_score(with_schema, total, 25)
    if with_schema < total:
        issues.append(Issue(
            severity="warning",
            message=f"{total - with_schema}/{total} operations lack response body schemas",
            location="paths.*.*.responses.*.content.*.schema",
        ))

    # Component schema property descriptions (20 pts)
    schemas = (spec.get("components") or {}).get("schemas") or {}
    all_described = 0
    all_total = 0
    for schema in schemas.values():
        d, t = _count_schema_props_with_desc(schema)
        all_described += d
        all_total += t

    if all_total > 0:
        prop_score = pct_score(all_described, all_total, 20)
        if all_described < all_total:
            issues.append(Issue(
                severity="warning",
                message=f"{all_total - all_described}/{all_total} schema properties lack descriptions — agents cannot infer field purpose",
                location="components.schemas.*.properties.*.description",
            ))
    else:
        prop_score = 10.0  # No reusable schemas defined — partial credit

    total_score = desc_score + err_score + schema_score + prop_score
    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
