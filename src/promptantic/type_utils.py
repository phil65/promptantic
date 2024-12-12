"""Type definitions for promptantic."""

from __future__ import annotations

from enum import Enum
import types
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Protocol,
    TypeGuard,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, conint, constr


if TYPE_CHECKING:
    from collections.abc import Iterable


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
        default: Any = None,
        **options: Any,
    ) -> T:
        """Handle input for a specific type."""
        ...


def strip_annotated(typ: Any) -> Any:
    """Strip Annotated wrapper from a type if present.

    Args:
        typ: The type to strip

    Returns:
        The underlying type without Annotated wrapper
    """
    if get_origin(typ) is Annotated:
        return get_args(typ)[0]
    return typ


def is_union_type(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a Union type."""
    typ = strip_annotated(typ)
    origin = get_origin(typ)
    return origin is Union or origin is types.UnionType


def get_union_types(typ: Any) -> tuple[type, ...]:
    """Get the types in a union."""
    if not is_union_type(typ):
        msg = "Not a union type"
        raise ValueError(msg)
    return get_args(strip_annotated(typ))


def is_model_type(typ: Any) -> TypeGuard[ModelType]:
    """Check if a type is a Pydantic model type."""
    typ = strip_annotated(typ)
    return isinstance(typ, type) and issubclass(typ, BaseModel)


def is_literal_type(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a Literal type."""
    typ = strip_annotated(typ)
    origin = get_origin(typ)
    return origin is Literal


def is_constrained_int(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a constrained int type."""
    typ = strip_annotated(typ)
    return getattr(typ, "__origin__", None) is conint


def is_constrained_str(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a constrained str type."""
    typ = strip_annotated(typ)
    return getattr(typ, "__origin__", None) is constr


def is_import_string(typ: Any) -> TypeGuard[Any]:
    """Check if a type is a Pydantic ImportString."""
    typ = strip_annotated(typ)
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


def is_tuple_type(typ: Any) -> bool:
    """Check if a type is a tuple type."""
    typ = strip_annotated(typ)
    return get_origin(typ) is tuple


def is_enum_type(typ: Any) -> TypeGuard[type[Enum]]:
    """Check if a type is an Enum type."""
    typ = strip_annotated(typ)
    return isinstance(typ, type) and issubclass(typ, Enum)


def is_valid_sequence(value: Any) -> TypeGuard[Iterable[Any]]:
    """Check if a value is a valid sequence.

    Args:
        value: Value to check

    Returns:
        True if value is a valid sequence (list, tuple, set)
    """
    if value is None:
        return False
    try:
        iter(value)
        return isinstance(value, list | tuple | set)
    except TypeError:
        return False


def is_skip_prompt(field: Any) -> bool:
    """Check if a field should be skipped during prompting.

    Args:
        field: The pydantic field to check

    Returns:
        True if the field should be skipped, False otherwise
    """
    # Check direct field metadata
    from promptantic import SKIP_PROMPT_KEY

    # Check direct field metadata
    json_schema_extra = getattr(field, "json_schema_extra", {})
    if json_schema_extra and json_schema_extra.get(SKIP_PROMPT_KEY):
        return True

    # Check metadata array for Annotated fields
    metadata = getattr(field, "metadata", [])
    if isinstance(metadata, list):
        for item in metadata:
            if isinstance(item, dict) and item.get(SKIP_PROMPT_KEY):
                return True

    return False
