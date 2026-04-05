from ..models import DimensionResult, Issue
from . import get_operations, pct_score

NAME = "AI Discoverability"

_GENERIC_IDS = {
    "get", "post", "put", "patch", "delete", "operation", "endpoint",
    "api", "handler", "action", "call", "request", "response",
}


def _is_descriptive(op_id: str) -> bool:
    """True if operationId is not a single generic word and is long enough."""
    lower = op_id.lower()
    if lower in _GENERIC_IDS:
        return False
    if len(op_id) < 5:
        return False
    # Flag things like op1, op2, operation123
    if lower.startswith("op") and op_id[2:].isdigit():
        return False
    return True


def score(spec: dict) -> DimensionResult:
    issues: list[Issue] = []
    operations = get_operations(spec)
    total = len(operations)

    if total == 0:
        return DimensionResult(name=NAME, score=0, issues=[
            Issue(severity="error", message="No operations found to evaluate", location="paths")
        ])

    # operationId present (20 pts)
    with_op_id = sum(1 for _, _, op in operations if op.get("operationId"))
    op_id_score = pct_score(with_op_id, total, 20)
    if with_op_id < total:
        issues.append(Issue(
            severity="error",
            message=f"{total - with_op_id}/{total} operations missing 'operationId' — AI cannot reliably reference them",
            location="paths.*.*.operationId",
        ))

    # operationIds are descriptive (20 pts)
    op_ids = [op.get("operationId") for _, _, op in operations if op.get("operationId")]
    non_descriptive = [oid for oid in op_ids if not _is_descriptive(oid)]
    if non_descriptive:
        issues.append(Issue(
            severity="warning",
            message=f"Non-descriptive operationIds: {', '.join(non_descriptive[:5])} — use verb+noun style (e.g. 'listTasks', 'createUser')",
            location="paths.*.*.operationId",
        ))
        desc_score = pct_score(len(op_ids) - len(non_descriptive), max(len(op_ids), 1), 20)
    else:
        desc_score = 20.0

    # Tags used on operations (25 pts)
    with_tags = sum(1 for _, _, op in operations if op.get("tags"))
    tag_score = pct_score(with_tags, total, 25)
    if with_tags < total:
        issues.append(Issue(
            severity="warning",
            message=f"{total - with_tags}/{total} operations missing tags — tags help AI group related capabilities",
            location="paths.*.*.tags",
        ))

    # Tag descriptions defined in top-level tags list (15 pts)
    top_tags: list[dict] = spec.get("tags") or []
    if top_tags:
        tags_with_desc = sum(1 for t in top_tags if isinstance(t, dict) and t.get("description"))
        if tags_with_desc == len(top_tags):
            tag_desc_score = 15.0
        else:
            tag_desc_score = pct_score(tags_with_desc, len(top_tags), 15)
            issues.append(Issue(
                severity="info",
                message=f"{len(top_tags) - tags_with_desc}/{len(top_tags)} tags in the top-level 'tags' list lack descriptions",
                location="tags[*].description",
            ))
    else:
        tag_desc_score = 0.0
        issues.append(Issue(
            severity="warning",
            message="No top-level 'tags' array defined — add tag descriptions so AI understands API domains",
            location="tags",
        ))

    # Substantive API-level description (20 pts)
    info = spec.get("info") or {}
    api_desc = (info.get("description") or "").strip()
    if len(api_desc) >= 80:
        api_desc_score = 20.0
    elif len(api_desc) >= 30:
        api_desc_score = 10.0
        issues.append(Issue(
            severity="info",
            message="API description is short (<80 chars) — a richer description improves AI discoverability",
            location="info.description",
        ))
    else:
        api_desc_score = 0.0
        issues.append(Issue(
            severity="warning",
            message="Missing or too-short API description — AI has no context for what this API does",
            location="info.description",
        ))

    total_score = op_id_score + desc_score + tag_score + tag_desc_score + api_desc_score
    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
