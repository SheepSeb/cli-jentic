"""Flask mock server generated from an OpenAPI spec."""
from __future__ import annotations

import json
import re
from typing import Any

from flask import Flask, Response, request as flask_request

from .generator import generate, resolve_ref

HTTP_METHODS = ["get", "post", "put", "patch", "delete", "head", "options"]


def _openapi_path_to_flask(path: str) -> str:
    """Convert /tasks/{taskId} → /tasks/<taskId>"""
    return re.sub(r"\{(\w+)\}", r"<\1>", path)


def _pick_response(operation: dict, spec: dict) -> tuple[int, Any]:
    """
    Choose the best status code and generate a body for it.
    Prefers 200, then 201, then the first 2xx.
    """
    responses = operation.get("responses") or {}

    # Prefer documented 2xx codes in order
    for code in ("200", "201", "202", "204"):
        if code in responses:
            body = _extract_body(responses[code], spec)
            return int(code), body

    # Fallback to first 2xx
    for code, resp in responses.items():
        if str(code).startswith("2"):
            body = _extract_body(resp, spec)
            return int(code), body

    return 200, {}


def _extract_body(response_def: dict, spec: dict) -> Any:
    """Extract or generate the response body from a response definition."""
    if not isinstance(response_def, dict):
        return None

    content = response_def.get("content") or {}

    # Prefer application/json
    media = content.get("application/json") or next(iter(content.values()), None)
    if not media:
        return None

    # Prefer explicit example
    if "example" in media:
        return media["example"]

    # Prefer first named example
    examples = media.get("examples") or {}
    if examples:
        first = next(iter(examples.values()))
        if isinstance(first, dict):
            return first.get("value")

    # Generate from schema
    schema = media.get("schema") or {}
    if schema:
        return generate(schema, spec)

    return None


def _validate_request(operation: dict, spec: dict) -> list[str]:
    """Basic request validation. Returns list of error messages."""
    errors: list[str] = []

    # Check required parameters are present
    for param in operation.get("parameters") or []:
        if isinstance(param, dict) and "$ref" in param:
            param = resolve_ref(param["$ref"], spec)
        if not isinstance(param, dict):
            continue
        if param.get("required") and param.get("in") == "query":
            name = param.get("name", "")
            if name and name not in flask_request.args:
                errors.append(f"Missing required query parameter: '{name}'")

    # Check required request body
    request_body = operation.get("requestBody") or {}
    if isinstance(request_body, dict) and request_body.get("required"):
        if flask_request.method in ("POST", "PUT", "PATCH"):
            if not flask_request.get_data():
                errors.append("Missing required request body")

    return errors


def create_app(spec: dict) -> Flask:
    """Build a Flask app that mocks every operation in the spec."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    paths = spec.get("paths") or {}
    registered: set[str] = set()

    for openapi_path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        flask_path = _openapi_path_to_flask(openapi_path)
        methods_for_path = [
            m.upper() for m in HTTP_METHODS if m in path_item
        ]

        if not methods_for_path:
            continue

        # Capture variables for the closure
        _path_item = path_item
        _openapi_path = openapi_path

        def make_handler(path_item: dict, openapi_path: str):
            def handler(**kwargs: str) -> Response:
                method = flask_request.method.lower()
                operation = path_item.get(method) or {}

                validation_errors = _validate_request(operation, spec)
                if validation_errors:
                    return Response(
                        json.dumps({"errors": validation_errors}),
                        status=400,
                        mimetype="application/json",
                    )

                status_code, body = _pick_response(operation, spec)

                if body is None:
                    return Response(status=status_code)

                return Response(
                    json.dumps(body),
                    status=status_code,
                    mimetype="application/json",
                )

            handler.__name__ = f"route_{openapi_path.replace('/', '_').replace('{', '').replace('}', '')}"
            return handler

        if flask_path not in registered:
            app.add_url_rule(
                flask_path,
                endpoint=f"ep_{flask_path}",
                view_func=make_handler(_path_item, _openapi_path),
                methods=methods_for_path,
            )
            registered.add(flask_path)

    return app
