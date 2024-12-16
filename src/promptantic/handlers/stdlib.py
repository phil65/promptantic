"""Handlers for additional stdlib types."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from fractions import Fraction
import importlib
import types
from typing import Any, TypeVar, get_args

from prompt_toolkit.shortcuts import PromptSession
from pydantic_core import PydanticUndefined

from promptantic.completers import ImportStringCompleter
from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


T = TypeVar("T")


class FractionHandler(BaseHandler[Fraction]):
    """Handler for Fraction input."""

    def format_default(self, default: Any) -> str | None:
        """Format fraction default value."""
        if default is None or default is PydanticUndefined:
            return None
        if isinstance(default, int | float):
            return str(Fraction(default))
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[Fraction],
        description: str | None = None,
        default: Fraction | int | float | str | None = None,  # noqa: PYI041
        **options: Any,
    ) -> Fraction:
        """Handle fraction input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter a fraction (e.g. '3/4' or '0.75')",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                if not result and default is not None:
                    if isinstance(default, int | float | str):
                        return Fraction(default)
                    return default

                return Fraction(result)
            except ValueError as e:
                msg = f"Invalid fraction: {e}"
                raise ValidationError(msg) from e


class ModuleHandler(BaseHandler[types.ModuleType]):
    """Handler for ModuleType input."""

    def __init__(self, generator: Any) -> None:
        super().__init__(generator)
        self.completer = ImportStringCompleter()

    def format_default(self, default: Any) -> str | None:
        """Format module default value."""
        if default is None or default is PydanticUndefined:
            return None
        if isinstance(default, str):
            return default
        if isinstance(default, types.ModuleType):
            return default.__name__
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[types.ModuleType],
        description: str | None = None,
        default: types.ModuleType | str | None = None,
        **options: Any,
    ) -> types.ModuleType:
        """Handle module input."""
        session: PromptSession[Any] = PromptSession(completer=self.completer)
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter a Python module name",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                if not result and default is not None:
                    if isinstance(default, str):
                        return importlib.import_module(default)
                    return default

                return importlib.import_module(result)
            except ImportError as e:
                msg = f"Module not found: {e}"
                raise ValidationError(msg) from e


class CounterHandler(BaseHandler[Counter[T]]):
    """Handler for Counter input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[Counter[T]],
        description: str | None = None,
        default: Counter[T] | None = None,
        **options: Any,
    ) -> Counter[T]:
        """Handle Counter input.

        Format: "key1:count1,key2:count2"
        """
        session: PromptSession[Any] = PromptSession()
        default_str = (
            ",".join(f"{k}:{v}" for k, v in default.items()) if default else None
        )

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter counts as 'key:count,key:count,...'",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                if not result and default is not None:
                    return default

                if not result:
                    return Counter()

                pairs = (pair.split(":") for pair in result.split(","))
                return Counter({key.strip(): int(count) for key, count in pairs})
            except (ValueError, IndexError) as e:
                msg = "Invalid format. Use 'key:count,key:count,...'"
                raise ValidationError(msg) from e


class DequeHandler(BaseHandler[deque[T]]):
    """Handler for deque input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[deque[T]],
        description: str | None = None,
        default: deque[T] | None = None,
        **options: Any,
    ) -> deque[T]:
        """Handle deque input."""
        # Get the item handler for the deque's type parameter
        item_type = get_args(field_type)[0] if get_args(field_type) else Any
        item_handler = self.generator.get_handler(item_type)

        # Get maxlen from field options
        field_info = options.get("field_info")
        json_schema_extra = getattr(field_info, "json_schema_extra", {})
        maxlen = json_schema_extra.get("maxlen")

        items: list[T] = []
        index = 0

        print(f"\nEntering items for {field_name}")
        if default:
            print(f"Default values: {list(default)}")
        print("Press Ctrl-D when done, Ctrl-C to remove last item")

        while True:
            try:
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

        return deque(items, maxlen=maxlen)


class DefaultDictHandler(BaseHandler[defaultdict[Any, Any]]):
    """Handler for defaultdict input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[defaultdict[Any, Any]],
        description: str | None = None,
        default: defaultdict[Any, Any] | None = None,
        **options: Any,
    ) -> defaultdict[Any, Any]:
        """Handle defaultdict input."""
        key_type, value_type = get_args(field_type)

        # Get handlers for key and value types
        key_handler = self.generator.get_handler(key_type)
        value_handler = self.generator.get_handler(value_type)

        # First, get the default factory
        while True:
            try:
                default_value = await value_handler.handle(
                    field_name="default_value",
                    field_type=value_type,
                    description="Enter default value for missing keys",
                )
                break
            except ValidationError:
                print("Invalid default value, try again")

        # Create the defaultdict with the factory
        result_dict: defaultdict[Any, Any] = defaultdict(lambda: default_value)

        # Now handle like a regular dict
        print("\nEntering key-value pairs")
        print("Press Ctrl-D when done, Ctrl-C to remove last item")

        while True:
            try:
                key = await key_handler.handle(
                    field_name=f"{field_name} key",
                    field_type=key_type,
                    description="Enter key",
                )

                value = await value_handler.handle(
                    field_name=f"{field_name}[{key}]",
                    field_type=value_type,
                    description=None,
                )

                result_dict[key] = value

            except EOFError:
                break
            except KeyboardInterrupt:
                if result_dict:
                    last_key = next(reversed(result_dict))
                    del result_dict[last_key]
                    print("\nRemoved last item")
                continue

        return result_dict
