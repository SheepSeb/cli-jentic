"""Auto-probe all endpoints in a spec against a running mock server."""
from __future__ import annotations

import time
from typing import Any

import requests

from .generator import generate, generate_path_param, resolve_ref
from .models import ProbeIssue, ProbeResult

HTTP_METHODS = ["get", "post", "put", "patch", "delete", "head", "options"]


def _fill_path(path: str, parameters: list[dict], spec: dict) -> str:
    """Replace {param} placeholders with generated values."""
    result = path
    for param in parameters:
        if isinstance(param, dict) and "$ref" in param:
            param = resolve_ref(param["$ref"], spec)
        if not isinstance(param, dict):
            continue
        if param.get("in") == "path":
            name = param.get("name", "")
            value = generate_path_param(param, spec)
            result = result.replace(f"{{{name}}}", value)
    return result


def _build_query_params(parameters: list[dict], spec: dict) -> dict[str, str]:
    """Build query params for required parameters."""
    params: dict[str, str] = {}
    for param in parameters:
        if isinstance(param, dict) and "$ref" in param:
            param = resolve_ref(param["$ref"], spec)
        if not isinstance(param, dict):
            continue
        if param.get("in") == "query" and param.get("required"):
            schema = param.get("schema") or {}
            val = generate(schema, spec)
            params[param["name"]] = str(val) if val is not None else ""
    return params


def _build_body(operation: dict, spec: dict) -> Any:
    """Build a request body from the operation's requestBody schema/examples."""
    request_body = operation.get("requestBody") or {}
    if not isinstance(request_body, dict):
        return None

    content = request_body.get("content") or {}
    media = content.get("application/json") or next(iter(content.values()), None)
    if not media:
        return None

    if "example" in media:
        return media["example"]

    examples = media.get("examples") or {}
    if examples:
        first = next(iter(examples.values()))
        if isinstance(first, dict):
            return first.get("value")

    schema = media.get("schema") or {}
    return generate(schema, spec) if schema else None


def probe_all(spec: dict, base_url: str) -> list[ProbeResult]:
    """Send a test request to every operation and return probe results."""
    results: list[ProbeResult] = []
    paths = spec.get("paths") or {}
    session = requests.Session()

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # Collect path-level parameters
        path_params = path_item.get("parameters") or []

        for method in HTTP_METHODS:
            if method not in path_item:
                continue

            operation = path_item[method]
            if not isinstance(operation, dict):
                continue

            # Merge path-level and operation-level parameters
            op_params = operation.get("parameters") or []
            all_params = path_params + op_params

            # Build URL
            filled_path = _fill_path(path, all_params, spec)
            url = base_url.rstrip("/") + filled_path
            query_params = _build_query_params(all_params, spec)

            # Build body
            body: Any = None
            headers = {"Accept": "application/json"}
            if method in ("post", "put", "patch"):
                body = _build_body(operation, spec)
                if body is not None:
                    headers["Content-Type"] = "application/json"

            issues: list[ProbeIssue] = []

            try:
                start = time.monotonic()
                resp = session.request(
                    method=method.upper(),
                    url=url,
                    params=query_params or None,
                    json=body,
                    headers=headers,
                    timeout=5,
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                status_code = resp.status_code
                success = status_code < 400

                # Try to parse response body
                try:
                    response_body = resp.json()
                except Exception:
                    response_body = resp.text or None

                # Check for unexpected errors
                if status_code >= 500:
                    issues.append(ProbeIssue(
                        severity="error",
                        message=f"Server error {status_code} — mock server could not generate a valid response",
                    ))
                elif status_code == 400:
                    err_detail = ""
                    if isinstance(response_body, dict) and "errors" in response_body:
                        err_detail = "; ".join(response_body["errors"])
                    issues.append(ProbeIssue(
                        severity="warning",
                        message=f"Request validation failed: {err_detail}" if err_detail else "Request rejected by mock server (400)",
                    ))

                # Warn if response body is empty but a schema was defined
                responses_spec = operation.get("responses") or {}
                expected_resp = (
                    responses_spec.get(str(status_code))
                    or responses_spec.get("200")
                    or {}
                )
                has_schema = bool((expected_resp.get("content") or {}).get("application/json", {}).get("schema"))
                if has_schema and response_body is None:
                    issues.append(ProbeIssue(
                        severity="warning",
                        message="Response schema defined but body was empty",
                    ))

                # Warn if no response schema or examples were defined
                if not has_schema and status_code == 200:
                    all_content = (expected_resp.get("content") or {})
                    if not all_content:
                        issues.append(ProbeIssue(
                            severity="info",
                            message="No response schema defined — mock returned empty body",
                        ))

                results.append(ProbeResult(
                    path=path,
                    method=method,
                    status_code=status_code,
                    success=success,
                    issues=issues,
                    request_url=url,
                    request_body=body,
                    response_body=response_body,
                    response_time_ms=round(elapsed_ms, 1),
                ))

            except requests.exceptions.ConnectionError:
                results.append(ProbeResult(
                    path=path,
                    method=method,
                    status_code=None,
                    success=False,
                    issues=[ProbeIssue(severity="error", message="Could not connect to mock server")],
                    request_url=url,
                ))
            except requests.exceptions.Timeout:
                results.append(ProbeResult(
                    path=path,
                    method=method,
                    status_code=None,
                    success=False,
                    issues=[ProbeIssue(severity="error", message="Request timed out")],
                    request_url=url,
                ))

    return results
