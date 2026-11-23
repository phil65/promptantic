"""What a form fills: a JSON Schema, or a Python type (pydantic model, dataclass, ...).

A target gives the schema the form is built from and validates the finished
value: JSON Schemas with :mod:`jsonschema` (Draft 2020-12, formats checked),
Python types with pydantic, which also turns the value into an instance.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, overload

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import TypeAdapter, ValidationError


if TYPE_CHECKING:
    from collections.abc import Callable

    from jsonschema.exceptions import ValidationError as JsonSchemaValidationError


type Path = tuple[str | int, ...]


@dataclass(frozen=True)
class Issue:
    """One problem with a finished value, at a path into it (``()``: the whole value)."""

    path: Path
    message: str


class FormCancelledError(Exception):
    """The user closed the form without submitting it."""


class FormValidationError(ValueError):
    """The finished value doesn't validate."""

    def __init__(self, issues: list[Issue]) -> None:
        self.issues = issues
        super().__init__(
            "; ".join(f"{'/'.join(map(str, i.path)) or '<root>'}: {i.message}" for i in issues)
        )


@dataclass(frozen=True)
class FormTarget[T]:
    """The schema a form is built from, and how its result is validated."""

    schema: Mapping[str, Any]
    validate_value: Callable[[Any], T]

    @property
    def title(self) -> str | None:
        return self.schema.get("title")

    def validate(self, value: Any) -> T:
        """The validated result (a model instance for Python types).

        Raises:
            FormValidationError: With every issue found, not only the first.
        """
        return self.validate_value(value)


@overload
def target_for[T](target: type[T]) -> FormTarget[T]: ...
@overload
def target_for(target: Mapping[str, Any]) -> FormTarget[dict[str, Any]]: ...
def target_for(target: type[Any] | Mapping[str, Any]) -> FormTarget[Any]:
    """The form target for a JSON Schema (as a mapping) or a Python type."""
    if isinstance(target, Mapping):
        return _schema_target(target)
    return _type_target(target)


def _schema_target(schema: Mapping[str, Any]) -> FormTarget[Any]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def validate(value: Any) -> Any:
        errors = sorted(validator.iter_errors(value), key=lambda e: list(e.absolute_path))
        # one "required" error per missing property, each naming them all: keep each once
        issues = list(dict.fromkeys(issue for error in errors for issue in _issues_of(error)))
        if issues:
            raise FormValidationError(issues)
        return value

    return FormTarget(schema=schema, validate_value=validate)


def _issues_of(error: JsonSchemaValidationError) -> list[Issue]:
    """Issues for a jsonschema error; a missing required property is placed at the property.

    jsonschema reports it at the object ("'name' is a required property"), so a form
    would show it away from the field.
    """
    path: Path = tuple(error.absolute_path)
    if error.validator == "required" and isinstance(error.instance, dict):
        missing = [name for name in error.validator_value if name not in error.instance]
        return [Issue(path=(*path, name), message="Field required") for name in missing]
    return [Issue(path=path, message=error.message)]


def _type_target(target: type[Any]) -> FormTarget[Any]:
    adapter: TypeAdapter[Any] = TypeAdapter(target)

    def validate(value: Any) -> Any:
        try:
            return adapter.validate_python(value)
        except ValidationError as exc:
            issues = [
                Issue(path=tuple(error["loc"]), message=error["msg"]) for error in exc.errors()
            ]
            raise FormValidationError(issues) from exc

    return FormTarget(schema=adapter.json_schema(), validate_value=validate)
