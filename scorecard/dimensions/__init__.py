HTTP_METHODS = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]


def get_operations(spec: dict) -> list[tuple[str, str, dict]]:
    """Returns list of (path, method, operation) tuples."""
    operations = []
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            if method in path_item:
                op = path_item[method]
                if isinstance(op, dict):
                    operations.append((path, method, op))
    return operations


def get_all_parameters(operations: list[tuple[str, str, dict]]) -> list[dict]:
    """Returns all inline (non-$ref) parameters across all operations."""
    params = []
    for _path, _method, op in operations:
        for p in op.get("parameters", []):
            if isinstance(p, dict) and "$ref" not in p:
                params.append(p)
    return params


def pct_score(met: int, total: int, max_pts: float) -> float:
    if total == 0:
        return max_pts
    return (met / total) * max_pts
