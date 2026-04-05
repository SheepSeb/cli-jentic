from ..models import DimensionResult, Issue
from . import get_operations, pct_score

NAME = "Security & Governance"


def score(spec: dict) -> DimensionResult:
    issues: list[Issue] = []
    pts = 0.0

    components = spec.get("components") or {}
    security_schemes = components.get("securitySchemes") or {}

    # Security schemes defined (30 pts)
    if security_schemes:
        pts += 30
    else:
        issues.append(Issue(
            severity="error",
            message="No security schemes defined in components.securitySchemes",
            location="components.securitySchemes",
        ))

    # Global or per-operation security applied (30 pts)
    global_security = spec.get("security")
    operations = get_operations(spec)
    total = len(operations)

    if global_security:
        pts += 30
    elif total > 0:
        with_security = sum(1 for _, _, op in operations if op.get("security") is not None)
        if with_security == total:
            pts += 30
        elif with_security > 0:
            pts += pct_score(with_security, total, 30)
            issues.append(Issue(
                severity="warning",
                message=f"Only {with_security}/{total} operations have security applied — use global security or apply to all",
                location="paths.*.*.security",
            ))
        else:
            issues.append(Issue(
                severity="error",
                message="Security is defined but not applied to any operation (and no global security set)",
                location="security",
            ))
    else:
        issues.append(Issue(
            severity="error",
            message="No security applied — neither global 'security' nor per-operation security found",
            location="security",
        ))

    # HTTPS servers only (20 pts)
    servers = spec.get("servers") or []
    if servers:
        http_servers = [s for s in servers if isinstance(s, dict) and (s.get("url") or "").startswith("http://")]
        if http_servers:
            issues.append(Issue(
                severity="error",
                message=f"{len(http_servers)} server(s) use HTTP instead of HTTPS: {[s['url'] for s in http_servers]}",
                location="servers[*].url",
            ))
        else:
            pts += 20
    else:
        pts += 15  # No servers listed — default assumed HTTPS, partial credit
        issues.append(Issue(
            severity="info",
            message="No servers defined — add server URLs to make HTTPS enforcement explicit",
            location="servers",
        ))

    # No API keys / credentials in path parameters (20 pts)
    sensitive_keywords = {"key", "token", "secret", "password", "apikey", "api_key", "auth", "credential"}
    leaky_params: list[str] = []
    for path, _method, op in operations:
        for p in op.get("parameters", []):
            if not isinstance(p, dict):
                continue
            name = (p.get("name") or "").lower()
            location = p.get("in", "")
            if location in ("path", "query") and any(kw in name for kw in sensitive_keywords):
                leaky_params.append(f"{path}:{p['name']}({location})")

    if leaky_params:
        issues.append(Issue(
            severity="error",
            message=f"Potential credential exposure in path/query params: {', '.join(leaky_params[:3])}",
            location="paths.*.*.parameters",
        ))
    else:
        pts += 20

    return DimensionResult(name=NAME, score=round(min(pts, 100), 1), issues=issues)
