"""
MCP Tool Argument Validation
=============================

Validates tool call arguments against their inputSchema before execution.
Lightweight JSON Schema subset validator — supports type checks, required
fields, and enum constraints without pulling in a full jsonschema library.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.mcp.arg_validator")

# JSON Schema type → Python types mapping
_TYPE_MAP = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


def validate_tool_arguments(
    tool_name: str,
    arguments: Dict[str, Any],
    input_schema: Dict[str, Any],
) -> List[str]:
    """Validate arguments against the tool's inputSchema.

    Returns a list of error strings.  Empty list means valid.
    Does NOT raise — callers decide how to handle errors.
    """
    errors: List[str] = []

    if not isinstance(arguments, dict):
        return [f"Arguments must be a dict, got {type(arguments).__name__}"]

    properties = input_schema.get("properties", {})
    required_fields = input_schema.get("required", [])

    # Check required fields are present
    for field in required_fields:
        if field not in arguments:
            errors.append(f"Missing required field: '{field}'")

    # Validate each provided argument
    for key, value in arguments.items():
        if key not in properties:
            # Extra keys are allowed (lenient) — just skip type check
            continue

        prop_schema = properties[key]
        expected_type = prop_schema.get("type")

        # Type check
        if expected_type and value is not None:
            allowed_types = _TYPE_MAP.get(expected_type)
            if allowed_types and not isinstance(value, allowed_types):
                errors.append(
                    f"Field '{key}': expected {expected_type}, "
                    f"got {type(value).__name__}"
                )

        # Enum check
        enum_values = prop_schema.get("enum")
        if enum_values is not None and value not in enum_values:
            errors.append(
                f"Field '{key}': value '{value}' not in allowed values {enum_values}"
            )

    return errors


def validate_and_log(
    tool_name: str,
    arguments: Dict[str, Any],
    input_schema: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Validate and return error response dict if invalid, else None.

    Convenience wrapper: returns a JSON-RPC-style error dict on failure,
    or None if validation passes.
    """
    errors = validate_tool_arguments(tool_name, arguments, input_schema)
    if errors:
        msg = f"Argument validation failed for '{tool_name}': {'; '.join(errors)}"
        logger.warning(msg)
        return {
            "content": [{"type": "text", "text": msg}],
            "isError": True,
        }
    return None
