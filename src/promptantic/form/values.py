"""Turning input into values, and checking a single field while it's being filled.

The whole value is validated at the end (:mod:`promptantic.form.target`); these
checks are what a renderer shows next to a field as the user types.
"""

from __future__ import annotations

import json
import math
import re
from typing import TYPE_CHECKING, Any

from jsonschema import FormatChecker

from promptantic.form.nodes import (
    UNSET,
    AnyNode,
    ArrayNode,
    ChoiceNode,
    NumberNode,
    ObjectNode,
    StringNode,
)


if TYPE_CHECKING:
    from promptantic.form.nodes import FormNode, Unset


_FORMATS = FormatChecker()


class FieldError(ValueError):
    """Input that can't become a value of the field (e.g. "abc" for a number)."""


def initial_value(node: FormNode) -> Any | Unset:
    """The value a field starts with: its default, else :data:`UNSET`."""
    return node.meta.default


def parse_text(node: StringNode | NumberNode | AnyNode, text: str) -> Any | Unset:
    """The value typed ``text`` stands for; :data:`UNSET` for empty input.

    Raises:
        FieldError: ``text`` isn't a number (number fields) or JSON (free fields).
    """
    if text == "" and not (isinstance(node, StringNode) and node.min_length == 0):
        return UNSET
    match node:
        case StringNode():
            return text
        case NumberNode(integer=True):
            try:
                return int(text.strip().replace("_", ""))
            except ValueError:
                msg = "Enter a whole number"
                raise FieldError(msg) from None
        case NumberNode():
            try:
                number = float(text.strip().replace("_", ""))
            except ValueError:
                msg = "Enter a number"
                raise FieldError(msg) from None
            if not math.isfinite(number):
                msg = "Enter a finite number"
                raise FieldError(msg)
            return int(number) if number.is_integer() and "." not in text else number
        case AnyNode():
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                msg = f"Enter JSON ({exc.msg})"
                raise FieldError(msg) from None


def field_errors(node: FormNode, value: Any) -> list[str]:  # noqa: PLR0911
    """What's wrong with ``value`` for this field alone (empty when it fits).

    Covers the field's own constraints (length, pattern, format, bounds, item and
    key counts, allowed choices); the full document is validated at the end.
    """
    if value is None:
        return [] if node.nullable or node.kind in ("null", "any") else ["A value is required"]
    match node:
        case StringNode():
            return _string_errors(node, value)
        case NumberNode():
            return _number_errors(node, value)
        case ChoiceNode():
            allowed = [choice.value for choice in node.choices]
            return [] if value in allowed else ["Pick one of the options"]
        case ArrayNode():
            if not isinstance(value, list):
                return ["Expected a list"]
            errors = []
            if node.min_items is not None and len(value) < node.min_items:
                errors.append(f"At least {node.min_items} item(s)")
            if node.max_items is not None and len(value) > node.max_items:
                errors.append(f"At most {node.max_items} item(s)")
            if node.unique and len({json.dumps(item, sort_keys=True) for item in value}) < len(
                value
            ):
                errors.append("Items must be unique")
            return errors
        case ObjectNode():
            if not isinstance(value, dict):
                return ["Expected an object"]
            errors = [
                f"{prop.label} is required"
                for prop in node.properties
                if prop.required and prop.name not in value
            ]
            if node.min_properties is not None and len(value) < node.min_properties:
                errors.append(f"At least {node.min_properties} entries")
            if node.max_properties is not None and len(value) > node.max_properties:
                errors.append(f"At most {node.max_properties} entries")
            return errors
        case _:
            return []


def _string_errors(node: StringNode, value: Any) -> list[str]:
    if not isinstance(value, str):
        return ["Expected text"]
    errors = []
    if node.min_length is not None and len(value) < node.min_length:
        errors.append(f"At least {node.min_length} character(s)")
    if node.max_length is not None and len(value) > node.max_length:
        errors.append(f"At most {node.max_length} character(s)")
    if node.pattern is not None and re.search(node.pattern, value) is None:
        errors.append(f"Must match {node.pattern}")
    if node.format is not None and not _FORMATS.conforms(value, node.format):
        errors.append(f"Not a valid {node.format}")
    return errors


def _number_errors(node: NumberNode, value: Any) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return ["Expected a number"]
    errors = []
    if node.integer and not float(value).is_integer():
        errors.append("Must be a whole number")
    if node.minimum is not None and value < node.minimum:
        errors.append(f"At least {node.minimum:g}")
    if node.maximum is not None and value > node.maximum:
        errors.append(f"At most {node.maximum:g}")
    if node.exclusive_minimum is not None and value <= node.exclusive_minimum:
        errors.append(f"More than {node.exclusive_minimum:g}")
    if node.exclusive_maximum is not None and value >= node.exclusive_maximum:
        errors.append(f"Less than {node.exclusive_maximum:g}")
    if node.multiple_of and not _is_multiple(value, node.multiple_of):
        errors.append(f"A multiple of {node.multiple_of:g}")
    return errors


def _is_multiple(value: float, step: float) -> bool:
    quotient = value / step
    return math.isclose(quotient, round(quotient), abs_tol=1e-9)
