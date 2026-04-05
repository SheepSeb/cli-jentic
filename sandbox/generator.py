"""Generate synthetic values from JSON Schema definitions."""
from __future__ import annotations
from typing import Any


_STRING_FORMAT_DEFAULTS: dict[str, Any] = {
    "date-time": "2024-01-15T10:30:00Z",
    "date": "2024-01-15",
    "time": "10:30:00",
    "email": "user@example.com",
    "uri": "https://example.com",
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "hostname": "example.com",
    "ipv4": "127.0.0.1",
    "password": "s3cr3t",
    "byte": "dGVzdA==",
    "binary": "binary-data",
}


def resolve_ref(ref: str, spec: dict) -> dict:
    """Resolve a local $ref like '#/components/schemas/Task'."""
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    obj: Any = spec
    for part in parts:
        if not isinstance(obj, dict):
            return {}
        obj = obj.get(part, {})
    return obj if isinstance(obj, dict) else {}


def generate(schema: dict, spec: dict, _depth: int = 0) -> Any:
    """Recursively generate a synthetic value that matches the given JSON Schema."""
    if _depth > 6:
        return None

    # Resolve $ref
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], spec)

    # Inline example wins
    if "example" in schema:
        return schema["example"]

    # allOf / anyOf / oneOf — use first branch
    for keyword in ("allOf", "anyOf", "oneOf"):
        if keyword in schema:
            branches = schema[keyword]
            if branches:
                return generate(branches[0], spec, _depth + 1)

    schema_type = schema.get("type")

    if schema_type == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        result: dict[str, Any] = {}
        for name, prop_schema in props.items():
            if name in required or _depth == 0:
                result[name] = generate(prop_schema, spec, _depth + 1)
        return result

    if schema_type == "array":
        items = schema.get("items") or {}
        return [generate(items, spec, _depth + 1)]

    if schema_type == "string":
        if "enum" in schema:
            return schema["enum"][0]
        fmt = schema.get("format", "")
        return _STRING_FORMAT_DEFAULTS.get(fmt, schema.get("default", "string"))

    if schema_type == "integer":
        return schema.get("default", schema.get("minimum", 1))

    if schema_type == "number":
        return schema.get("default", schema.get("minimum", 1.0))

    if schema_type == "boolean":
        return schema.get("default", True)

    if schema_type == "null":
        return None

    return schema.get("default")


def generate_path_param(param: dict, spec: dict) -> str:
    """Generate a URL-safe value for a path parameter."""
    if "example" in param:
        return str(param["example"])
    schema = param.get("schema") or {}
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], spec)
    if "example" in schema:
        return str(schema["example"])
    if "enum" in schema:
        return str(schema["enum"][0])
    fmt = schema.get("format", "")
    if fmt == "uuid":
        return "123e4567-e89b-12d3-a456-426614174000"
    param_type = schema.get("type", "string")
    if param_type == "integer":
        return "1"
    return f"example-{param.get('name', 'id')}"
