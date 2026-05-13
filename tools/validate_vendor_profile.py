#!/usr/bin/env python3
"""
validate_vendor_profile.py

Lightweight validator for vendor-profile JSON documents in
vendor-profiles/. Implements the small subset of JSON Schema that the
schema actually uses (type, required, enum, additionalProperties=false,
items, properties, minLength, minimum, $schema, $id, title, description)
so we don't pull in a jsonschema dependency.

Usage:
    python tools/validate_vendor_profile.py vendor-profiles/continental_silverline.profile.json
    python tools/validate_vendor_profile.py vendor-profiles/*.profile.json
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


SCHEMA_PATH_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vendor-profiles", "vendor_profile.schema.json",
)


# Map JSON Schema type names to Python types.
TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def _type_matches(value: Any, expected: str) -> bool:
    py = TYPE_MAP.get(expected)
    if py is None:
        return True  # Unknown type, don't block.
    if expected == "integer" and isinstance(value, bool):
        return False
    if expected == "number" and isinstance(value, bool):
        return False
    return isinstance(value, py)


def validate(value: Any, schema: dict, path: str = "$") -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type and not _type_matches(value, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
        return errors  # Type mismatch — no point validating deeper.

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not in enum {schema['enum']}")

    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path}: string shorter than minLength {schema['minLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{path}: {value} is less than minimum {schema['minimum']}")

    if isinstance(value, dict):
        props: dict = schema.get("properties", {})
        required: list = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property '{key}'")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value.keys()) - set(props.keys()))
            for key in extra:
                errors.append(f"{path}: unexpected property '{key}'")
        additional_schema = schema.get("additionalProperties")
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in props:
                errors.extend(validate(child, props[key], child_path))
            elif isinstance(additional_schema, dict):
                errors.extend(validate(child, additional_schema, child_path))

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        for i, item in enumerate(value):
            errors.extend(validate(item, item_schema, f"{path}[{i}]"))

    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args:
        print("usage: validate_vendor_profile.py PATH [PATH ...]", file=sys.stderr)
        return 2

    schema_path = SCHEMA_PATH_DEFAULT
    if args and args[0] == "--schema":
        args.pop(0)
        if not args:
            print("--schema requires a path", file=sys.stderr)
            return 2
        schema_path = args.pop(0)

    if not args:
        print("no profile paths provided", file=sys.stderr)
        return 2

    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    failures = 0
    for path in args:
        if not os.path.isfile(path):
            print(f"FAIL {path}: file not found")
            failures += 1
            continue
        with open(path, "r", encoding="utf-8") as fh:
            try:
                document = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"FAIL {path}: invalid JSON ({exc})")
                failures += 1
                continue
        errors = validate(document, schema)
        if errors:
            print(f"FAIL {path}")
            for err in errors:
                print(f"  - {err}")
            failures += 1
        else:
            print(f"OK   {path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
