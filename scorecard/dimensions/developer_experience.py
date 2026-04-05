from ..models import DimensionResult, Issue
from . import get_operations, get_all_parameters, pct_score

NAME = "Developer Experience"


def _has_example(content: dict) -> bool:
    for media in content.values():
        if isinstance(media, dict) and (media.get("example") is not None or media.get("examples")):
            return True
    return False


def score(spec: dict) -> DimensionResult:
    issues: list[Issue] = []
    operations = get_operations(spec)

    if not operations:
        return DimensionResult(name=NAME, score=0, issues=[
            Issue(severity="error", message="No operations found to evaluate", location="paths")
        ])

    total = len(operations)

    # Summaries (25 pts)
    with_summary = sum(1 for _, _, op in operations if op.get("summary"))
    s_score = pct_score(with_summary, total, 25)
    if with_summary < total:
        issues.append(Issue(
            severity="warning" if with_summary / total >= 0.5 else "error",
            message=f"{total - with_summary}/{total} operations missing 'summary'",
            location="paths.*.*.summary",
        ))

    # Descriptions (25 pts)
    with_desc = sum(1 for _, _, op in operations if op.get("description") and len((op["description"] or "").strip()) > 10)
    d_score = pct_score(with_desc, total, 25)
    if with_desc < total:
        issues.append(Issue(
            severity="warning" if with_desc / total >= 0.5 else "error",
            message=f"{total - with_desc}/{total} operations missing meaningful description",
            location="paths.*.*.description",
        ))

    # Parameter descriptions (20 pts)
    params = get_all_parameters(operations)
    if params:
        with_pdesc = sum(1 for p in params if p.get("description"))
        p_score = pct_score(with_pdesc, len(params), 20)
        if with_pdesc < len(params):
            issues.append(Issue(
                severity="warning",
                message=f"{len(params) - with_pdesc}/{len(params)} parameters missing description",
                location="paths.*.*.parameters[*].description",
            ))
    else:
        p_score = 20.0

    # Response descriptions (15 pts)
    all_responses: list[dict] = []
    for _, _, op in operations:
        for resp in op.get("responses", {}).values():
            if isinstance(resp, dict):
                all_responses.append(resp)
    if all_responses:
        with_rdesc = sum(1 for r in all_responses if r.get("description"))
        r_score = pct_score(with_rdesc, len(all_responses), 15)
        if with_rdesc < len(all_responses):
            issues.append(Issue(
                severity="warning",
                message=f"{len(all_responses) - with_rdesc}/{len(all_responses)} responses missing description",
                location="paths.*.*.responses.*.description",
            ))
    else:
        r_score = 0.0
        issues.append(Issue(severity="error", message="No responses defined on any operation", location="paths.*.*.responses"))

    # Examples (15 pts)
    ops_with_example = 0
    for _, method, op in operations:
        if method in ("post", "put", "patch"):
            rb = op.get("requestBody") or {}
            content = rb.get("content") or {} if isinstance(rb, dict) else {}
            if _has_example(content):
                ops_with_example += 1
        else:
            for resp in op.get("responses", {}).values():
                if isinstance(resp, dict) and _has_example(resp.get("content") or {}):
                    ops_with_example += 1
                    break
    e_score = pct_score(ops_with_example, total, 15)
    if ops_with_example / total < 0.5:
        issues.append(Issue(
            severity="warning",
            message=f"Only {ops_with_example}/{total} operations include request/response examples",
            location="paths.*.*.content.*.example",
        ))

    total_score = s_score + d_score + p_score + r_score + e_score
    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
