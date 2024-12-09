"""Handlers for sequence types."""

from __future__ import annotations

from typing import Any, TypeVar, get_args, get_origin

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler


T = TypeVar("T")


class SequenceHandler(BaseHandler):
    """Base handler for sequence types."""

    async def handle(
        self,
        field_name: str,
        field_type: type[list[Any] | set[Any] | tuple[Any, ...]],
        description: str | None = None,
        **options: Any,
    ) -> list[Any] | set[Any] | tuple[Any, ...]:
        """Handle sequence input.

        Args:
            field_name: Name of the field
            field_type: Type of the sequence (e.g. list[int], set[str])
            description: Optional field description
            **options: Additional options

        Returns:
            The populated sequence
        """
        # Get the type of items in the sequence
        item_type = get_args(field_type)[0]
        origin = get_origin(field_type)
        if origin is None:
            msg = f"Invalid sequence type: {field_type}"
            raise ValidationError(msg)

        # Get handler for item type
        item_handler = self.generator.get_handler(item_type)

        items: list[Any] = []
        index = 0

        print(f"\nEntering items for {field_name} (press Ctrl-D when done):")

        while True:
            try:
                # Create prompt for each item
                item_name = f"{field_name}[{index}]"
                value = await item_handler.handle(
                    field_name=item_name,
                    field_type=item_type,
                    description=None,
                )
                items.append(value)
                index += 1
            except EOFError:
                break
            except KeyboardInterrupt:
                if items:
                    items.pop()
                    index -= 1
                    print("\nRemoved last item")
                continue

        # Convert to appropriate sequence type
        if origin is list:
            return items
        if origin is set:
            return set(items)
        if origin is tuple:
            return tuple(items)

        msg = f"Unsupported sequence type: {origin}"
        raise ValidationError(msg)


class ListHandler(BaseHandler):
    """Handler for list input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[list[Any]],
        description: str | None = None,
        **options: Any,
    ) -> list[Any]:
        """Handle list input."""
        result = await SequenceHandler(self.generator).handle(
            field_name, field_type, description, **options
        )
        return list(result)


class SetHandler(BaseHandler):
    """Handler for set input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[set[Any]],
        description: str | None = None,
        **options: Any,
    ) -> set[Any]:
        """Handle set input."""
        result = await SequenceHandler(self.generator).handle(
            field_name, field_type, description, **options
        )
        return set(result)


class TupleHandler(BaseHandler):
    """Handler for tuple input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[tuple[Any, ...]],
        description: str | None = None,
        **options: Any,
    ) -> tuple[Any, ...]:
        """Handle tuple input."""
        result = await SequenceHandler(self.generator).handle(
            field_name, field_type, description, **options
        )
        return tuple(result)
