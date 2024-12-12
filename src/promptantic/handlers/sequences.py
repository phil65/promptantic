"""Handlers for sequence types."""

from typing import Any, get_args, get_origin

from prompt_toolkit.shortcuts import PromptSession
from pydantic_core import PydanticUndefined

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.type_utils import is_valid_sequence


class SequenceHandler(BaseHandler[tuple[Any, ...]]):
    """Base handler for sequence types."""

    def format_default(self, default: Any) -> str | None:
        """Format sequence default value."""
        if default is None:
            return None
        return f"[{len(default)} items]"

    async def handle(
        self,
        field_name: str,
        field_type: type[tuple[Any, ...]] | type[list[Any]] | type[set[Any]],
        description: str | None = None,
        default: tuple[Any, ...] | list[Any] | set[Any] | None = None,
        **options: Any,
    ) -> tuple[Any, ...]:
        """Handle sequence input."""
        # Get the type of items in the sequence
        item_type = get_args(field_type)[0] if get_args(field_type) else Any
        origin = get_origin(field_type)
        if origin is None:
            msg = f"Invalid sequence type: {field_type}"
            raise ValidationError(msg)

        # Get handler for item type
        item_handler = self.generator.get_handler(item_type)

        items: list[Any] = []
        index = 0

        if is_valid_sequence(default):
            print(f"\nDefault values available for {field_name}:")
            print("1. Use default values")
            print("2. Enter new values")
            print("3. Start with defaults and add more")

            session: PromptSession[Any] = PromptSession()
            while True:
                choice = await session.prompt_async("Choose option (1-3): ")
                if choice == "1":
                    # default is guaranteed to be Iterable here due to TypeGuard
                    return tuple(default)
                if choice == "2":
                    break
                if choice == "3":
                    items = list(default)
                    index = len(items)
                    break
                print("Invalid choice, please try again")
        else:
            print(f"\nEntering items for {field_name}")

        print("Press Ctrl-D when done, Ctrl-C to remove last item")

        while True:
            try:
                # Create prompt for each item
                item_name = f"{field_name}[{index}]"
                value = await item_handler.handle(
                    field_name=item_name,
                    field_type=item_type,
                    description=description,
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
        default: list[Any] | None = None,
        **options: Any,
    ) -> list[Any]:
        """Handle list input."""
        # Get the type of items in the list
        item_type = get_args(field_type)[0] if get_args(field_type) else Any

        # Get handler for item type
        item_handler = self.generator.get_handler(item_type)

        items: list[Any] = []
        index = 0

        print(f"\nEntering items for {field_name}")
        # Check if we have a valid default value
        if is_valid_sequence(default):
            print(f"Default values: {default}")
            print("Press Enter to keep defaults or input new values")
            items = list(default)
            index = len(items)
        print("Press Ctrl-D when done, or enter an empty line in test mode")

        while True:
            try:
                item_name = f"{field_name}[{index}]"
                value = await item_handler.handle(
                    field_name=item_name,
                    field_type=item_type,
                    description=description,
                )
                # In test mode, treat empty string as termination
                if not value and options.get("_test_mode"):  # Updated here
                    break
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

        return items


class SetHandler(BaseHandler[set[Any]]):
    """Handler for set input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[set[Any]],
        description: str | None = None,
        default: set[Any] | None = None,
        **options: Any,
    ) -> set[Any]:
        """Handle set input."""
        result = await SequenceHandler(self.generator).handle(
            field_name=field_name,
            field_type=field_type,
            description=description,
            default=list(default) if default is not None else None,
            **options,
        )
        return set(result)


class TupleHandler(BaseHandler[tuple[Any, ...]]):
    """Handler for tuple input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[tuple[Any, ...]],
        description: str | None = None,
        default: tuple[Any, ...] | None = None,
        **options: Any,
    ) -> tuple[Any, ...]:
        """Handle tuple input."""
        # Get the item types from the tuple
        args = get_args(field_type)
        if not args:
            # Handle tuple without type args as tuple[Any, ...]
            return await SequenceHandler(self.generator).handle(
                field_name=field_name,
                field_type=field_type,
                description=description,
                default=default,
                **options,
            )

        # Handle fixed-length tuples
        if not any(arg is ... for arg in args):
            values: list[Any] = []
            # Create default values array
            default_values: list[Any] = (
                list(default) if is_valid_sequence(default) else [None] * len(args)
            )

            for i, (item_type, default_value) in enumerate(zip(args, default_values)):
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
                            default=default_value,
                            **options,
                        )
                        values.append(value)
                        break
                    except ValidationError as e:
                        print(f"\033[91mValidation error: {e}\033[0m")
                        print("Please try again...")

            return tuple(values)

        # Handle variable-length tuples (tuple[int, ...])
        return await SequenceHandler(self.generator).handle(
            field_name=field_name,
            field_type=field_type,
            description=description,
            default=default,
            **options,
        )


class DictHandler(BaseHandler[dict[Any, Any]]):
    """Handler for dictionary input."""

    def format_default(self, default: Any) -> str | None:
        """Format dictionary default value."""
        if default is None or default is PydanticUndefined:
            return None
        return f"[{len(default)} items]"

    async def handle(
        self,
        field_name: str,
        field_type: type[dict[Any, Any]],
        description: str | None = None,
        default: dict[Any, Any] | None = None,
        **options: Any,
    ) -> dict[Any, Any]:
        """Handle dictionary input."""
        # Get the key and value types from the generic parameters
        key_type, value_type = get_args(field_type)

        # Get handlers for key and value types
        key_handler = self.generator.get_handler(key_type)
        value_handler = self.generator.get_handler(value_type)

        items: dict[Any, Any] = {}

        if default is not None and default is not PydanticUndefined:
            print(f"\nDefault values available for {field_name}:")
            print("1. Use default values")
            print("2. Enter new values")
            print("3. Start with defaults and add more")

            session: PromptSession[Any] = PromptSession()
            while True:
                choice = await session.prompt_async("Choose option (1-3): ")
                if choice == "1":
                    return dict(default)
                if choice == "2":
                    break
                if choice == "3":
                    items = dict(default)
                    break
                print("Invalid choice, please try again")
        else:
            print(f"\nEntering items for {field_name}")

        print("Press Ctrl-D when done, Ctrl-C to remove last item")

        while True:
            try:
                # Get key
                key_name = f"{field_name} key"
                key = await key_handler.handle(
                    field_name=key_name,
                    field_type=key_type,
                    description="Enter key",
                )

                # Get value
                value_name = f"{field_name}[{key}]"
                value = await value_handler.handle(
                    field_name=value_name,
                    field_type=value_type,
                    description=description,
                )

                items[key] = value

            except EOFError:
                break
            except KeyboardInterrupt:
                if items:
                    last_key = next(reversed(items))
                    items.pop(last_key)
                    print("\nRemoved last item")
                continue
            except ValidationError:
                print("\nValidation failed, try again...")
                continue

        return items
