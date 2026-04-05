from ..models import DimensionResult, Issue
from . import get_operations, pct_score

NAME = "Agent Usability"


def score(spec: dict) -> DimensionResult:
    issues: list[Issue] = []
    operations = get_operations(spec)

    if not operations:
        return DimensionResult(name=NAME, score=0, issues=[
            Issue(severity="error", message="No operations found to evaluate", location="paths")
        ])

    total = len(operations)

    # operationId present (40 pts)
    operation_ids = []
    with_op_id = 0
    for _, _, op in operations:
        oid = op.get("operationId")
        if oid:
            with_op_id += 1
            operation_ids.append(oid)
    op_id_score = pct_score(with_op_id, total, 40)
    if with_op_id < total:
        issues.append(Issue(
            severity="error" if with_op_id / total < 0.5 else "warning",
            message=f"{total - with_op_id}/{total} operations missing 'operationId' — agents cannot reliably reference these operations",
            location="paths.*.*.operationId",
        ))

    # operationIds are unique (20 pts)
    if len(operation_ids) != len(set(operation_ids)):
        duplicates = {oid for oid in operation_ids if operation_ids.count(oid) > 1}
        issues.append(Issue(
            severity="error",
            message=f"Duplicate operationIds found: {', '.join(sorted(duplicates))}",
            location="paths.*.*.operationId",
        ))
        unique_score = 0.0
    else:
        unique_score = 20.0

    # GET operations should not have request bodies (15 pts)
    gets_with_body = sum(
        1 for _, method, op in operations
        if method == "get" and op.get("requestBody")
    )
    if gets_with_body:
        issues.append(Issue(
            severity="warning",
            message=f"{gets_with_body} GET operation(s) define a requestBody — GET requests should not have a body",
            location="paths.*.get.requestBody",
        ))
        method_score = 0.0
    else:
        method_score = 15.0

    # DELETE operations target a specific resource (path param present) (10 pts)
    bad_deletes = 0
    for path, method, op in operations:
        if method == "delete":
            has_path_param = "{" in path or any(
                p.get("in") == "path" for p in op.get("parameters", []) if isinstance(p, dict)
            )
            if not has_path_param:
                bad_deletes += 1
    if bad_deletes:
        issues.append(Issue(
            severity="warning",
            message=f"{bad_deletes} DELETE operation(s) have no path parameter — bulk deletes are dangerous for agents",
            location="paths.*.delete",
        ))
        delete_score = 0.0
    else:
        delete_score = 10.0

    # At least one success response (2xx) per operation (15 pts)
    without_success = sum(
        1 for _, _, op in operations
        if not any(str(code).startswith("2") for code in op.get("responses", {}).keys())
    )
    success_score = pct_score(total - without_success, total, 15)
    if without_success:
        issues.append(Issue(
            severity="warning",
            message=f"{without_success}/{total} operations have no documented success (2xx) response",
            location="paths.*.*.responses",
        ))

    total_score = op_id_score + unique_score + method_score + delete_score + success_score
    return DimensionResult(name=NAME, score=round(min(total_score, 100), 1), issues=issues)
