"""Handlers for sequence types."""

from typing import Any, get_args, get_origin

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler


class SequenceHandler(BaseHandler[tuple[Any, ...]]):
    """Base handler for sequence types."""

    async def handle(
        self,
        field_name: str,
        field_type: type[tuple[Any, ...]] | type[list[Any]] | type[set[Any]],
        description: str | None = None,
        **options: Any,
    ) -> tuple[Any, ...]:
        """Handle sequence input."""
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

        return tuple(items)


class ListHandler(BaseHandler[list[Any]]):
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


class SetHandler(BaseHandler[set[Any]]):
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


class TupleHandler(BaseHandler[tuple[Any, ...]]):
    """Handler for tuple input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[tuple[Any, ...]],
        description: str | None = None,
        **options: Any,
    ) -> tuple[Any, ...]:
        """Handle tuple input."""
        # Get the item types from the tuple
        args = get_args(field_type)
        if not args:
            # Handle tuple without type args as tuple[Any, ...]
            return await SequenceHandler(self.generator).handle(
                field_name, field_type, description, **options
            )

        # Handle fixed-length tuples
        if not any(arg is ... for arg in args):
            values: list[Any] = []
            for i, item_type in enumerate(args):
                item_name = f"{field_name}[{i}]"
                item_handler = self.generator.get_handler(item_type)
                # Create a type-specific description
                type_name = getattr(item_type, "__name__", str(item_type))
                item_desc = (
                    f"{description} ({type_name})"
                    if description
                    else f"Enter {type_name}"
                )

                while True:
                    try:
                        value = await item_handler.handle(
                            field_name=item_name,
                            field_type=item_type,
                            description=item_desc,
                        )
                        values.append(value)
                        break
                    except ValidationError as e:
                        print(f"\033[91mValidation error: {e}\033[0m")
                        print("Please try again...")

            return tuple(values)

        # Handle variable-length tuples (tuple[int, ...])
        return await SequenceHandler(self.generator).handle(
            field_name, field_type, description, **options
        )
