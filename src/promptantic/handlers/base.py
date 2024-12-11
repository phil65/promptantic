"""Base handler implementation."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from promptantic.type_utils import TypeHandler


T = TypeVar("T")


class BaseHandler(Generic[T], TypeHandler[T]):
    """Base class for type handlers."""

    def __init__(self, generator: Any) -> None:  # Any for now to avoid circular import
        self.generator = generator

    def format_default(self, default: Any) -> str | None:
        """Format default value for display."""
        if default is None:
            return None
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[T],
        description: str | None = None,
        default: Any = None,
        **options: Any,
    ) -> T:
        """Handle input for this type."""
        raise NotImplementedError
