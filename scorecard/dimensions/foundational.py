# Derived from the Jentic API AI-Readiness Framework (JAIRF)
# Copyright (c) 2025-2026 Jentic. Licensed under the Apache License, Version 2.0.
# Modifications copyright (c) 2025-2026 SheepSeb.
from ..models import DimensionResult, Issue

NAME = "Foundational Compliance"


def score(spec: dict) -> DimensionResult:
    issues: list[Issue] = []
    pts = 0.0

    # OpenAPI/Swagger version present (15 pts)
    version_field = spec.get("openapi") or spec.get("swagger")
    if version_field:
        pts += 15
    else:
        issues.append(Issue(severity="error", message="Missing 'openapi' or 'swagger' version field", location="root"))

    # Info object (35 pts)
    info = spec.get("info") or {}
    if isinstance(info, dict) and info:
        if info.get("title"):
            pts += 10
        else:
            issues.append(Issue(severity="error", message="Missing API title", location="info.title"))

        if info.get("version"):
            pts += 10
        else:
            issues.append(Issue(severity="error", message="Missing API version", location="info.version"))

        desc = info.get("description", "") or ""
        if desc.strip() and len(desc.strip()) > 10:
            pts += 15
        else:
            issues.append(Issue(severity="warning", message="Missing or too-short API description", location="info.description"))
    else:
        issues.append(Issue(severity="error", message="Missing 'info' object", location="info"))

    # Paths defined (15 pts)
    paths = spec.get("paths") or {}
    if paths and isinstance(paths, dict):
        pts += 15
    else:
        issues.append(Issue(severity="error", message="No API paths defined", location="paths"))

    # Spec validation via openapi-spec-validator (35 pts)
    try:
        from openapi_spec_validator import validate  # type: ignore

        try:
            validate(spec)
            pts += 35
        except Exception as exc:
            snippet = str(exc)[:200]
            issues.append(Issue(severity="error", message=f"Spec validation failed: {snippet}", location="root"))
            pts += 5  # parseable but invalid
    except ImportError:
        pts += 20
        issues.append(Issue(severity="info", message="Install openapi-spec-validator for full schema validation", location="root"))

    return DimensionResult(name=NAME, score=round(min(pts, 100), 1), issues=issues)
