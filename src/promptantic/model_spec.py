"""Describe a model as data, fill that description with a form, get a pydantic class.

:class:`ModelSpec` is an ordinary pydantic model, so :func:`promptantic.fill` asks for
it like for any other: field by field, nested objects recursively. The filled spec
becomes a JSON Schema (:meth:`ModelSpec.json_schema`) or a pydantic class
(:meth:`ModelSpec.model_class`, built with :func:`pydantic.create_model`).
"""

from __future__ import annotations

import datetime as dt
import json
from types import GenericAlias
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, create_model


type FieldType = Literal[
    "string", "integer", "number", "boolean", "date", "datetime", "email", "uri", "list", "object"
]
type ItemType = Literal["string", "integer", "number", "boolean"]

_SCHEMAS: dict[str, dict[str, Any]] = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "datetime": {"type": "string", "format": "date-time"},
    "email": {"type": "string", "format": "email"},
    "uri": {"type": "string", "format": "uri"},
}


class FieldSpec(BaseModel):
    """One field of a model being designed."""

    name: str = Field(min_length=1, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: FieldType = "string"
    required: bool = True
    default: str | None = Field(
        default=None, description="As you'd type it: 42, true, a text, or JSON for lists"
    )
    description: str | None = None
    items: ItemType = Field(default="string", description="Item type (for lists)")
    fields: list[FieldSpec] = Field(default=[], description="Its fields (for objects)")

    def json_schema(self) -> dict[str, Any]:
        """The field as a JSON Schema property."""
        match self.type:
            case "list":
                schema: dict[str, Any] = {"type": "array", "items": dict(_SCHEMAS[self.items])}
            case "object":
                schema = _object_schema(self.fields)
            case kind:
                schema = dict(_SCHEMAS[kind])
        if self.description:
            schema["description"] = self.description
        if self.default is not None:
            schema["default"] = _parse_default(self.type, self.default)
        return schema


class ModelSpec(BaseModel):
    """A model being designed: its name, description and fields."""

    name: str = Field(min_length=1, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    description: str | None = None
    fields: list[FieldSpec] = Field(min_length=1)

    def json_schema(self) -> dict[str, Any]:
        """The model as a JSON Schema object."""
        schema = {"title": self.name, **_object_schema(self.fields)}
        if self.description:
            schema["description"] = self.description
        return schema

    def model_class(self, *, base: type[BaseModel] = BaseModel) -> type[BaseModel]:
        """A pydantic class for the spec (nested objects become nested classes)."""
        return _model_class(self.name, self.fields, base=base, doc=self.description)


_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "date": dt.date,
    "datetime": dt.datetime,
    "email": Annotated[str, Field(json_schema_extra={"format": "email"})],
    "uri": Annotated[str, Field(json_schema_extra={"format": "uri"})],
}


def _model_class(
    name: str, fields: list[FieldSpec], *, base: type[BaseModel], doc: str | None
) -> type[BaseModel]:
    definitions: dict[str, Any] = {}
    for spec in fields:
        match spec.type:
            case "list":
                annotation: Any = GenericAlias(list, (_TYPES[spec.items],))
            case "object":
                annotation = _model_class(
                    f"{name}{spec.name.title().replace('_', '')}",
                    spec.fields,
                    base=BaseModel,
                    doc=None,
                )
            case kind:
                annotation = _TYPES[kind]
        if spec.default is not None:
            default: Any = _parse_default(spec.type, spec.default)
        elif spec.required:
            default = ...
        else:
            annotation, default = annotation | None, None
        definitions[spec.name] = (annotation, Field(default, description=spec.description))
    return create_model(name, __base__=base, __doc__=doc, **definitions)


def _object_schema(fields: list[FieldSpec]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field.name: field.json_schema() for field in fields},
        "required": [field.name for field in fields if field.required and field.default is None],
    }


def _parse_default(kind: str, text: str) -> Any:
    """A default typed as text, as a value of the field's type."""
    match kind:
        case "integer":
            return int(text)
        case "number":
            return float(text)
        case "boolean":
            return text.strip().lower() in {"true", "yes", "y", "1"}
        case "list" | "object":
            return json.loads(text)
        case _:
            return text
