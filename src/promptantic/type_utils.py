"""Type definitions for promptantic."""

from __future__ import annotations

import types
from typing import Any, Literal, Protocol, TypeGuard, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, conint, constr


ModelType = type[BaseModel] | BaseModel
FieldType = type | Any | None

T = TypeVar("T")
HandlerT = TypeVar("HandlerT", bound="TypeHandler")


class TypeHandler(Protocol[T]):
    """Protocol for type handlers."""

    async def handle(
        self,
        field_name: str,
        field_type: type[T],
        description: str | None = None,
        **options: Any,
    ) -> T:
        """Handle input for a specific type."""
        ...


def is_union_type(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a Union type."""
    origin = get_origin(typ)
    return origin is Union or origin is types.UnionType


def get_union_types(typ: Any) -> tuple[type, ...]:
    """Get the types in a union."""
    if not is_union_type(typ):
        msg = "Not a union type"
        raise ValueError(msg)
    return get_args(typ)


def is_model_type(typ: Any) -> TypeGuard[ModelType]:
    """Check if a type is a Pydantic model type."""
    return isinstance(typ, type) and issubclass(typ, BaseModel)


def is_literal_type(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a Literal type."""
    origin = get_origin(typ)
    return origin is Literal


def is_constrained_int(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a constrained int type."""
    return getattr(typ, "__origin__", None) is conint


def is_constrained_str(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a constrained str type."""
    return getattr(typ, "__origin__", None) is constr


def is_import_string(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a Pydantic ImportString."""
    origin = get_origin(typ)
    if origin is not None:
        args = get_args(typ)
        if not args or len(args) < 2:  # noqa: PLR2004
            return False
        # Check that it's a string annotation with ImportString validator
        return args[0] is str and any(
            getattr(arg, "__name__", "") == "ImportString" for arg in args[1:]
        )
    return False
