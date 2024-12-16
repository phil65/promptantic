"""Main generator implementation."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict, deque
import datetime
from decimal import Decimal
from enum import Enum
from fractions import Fraction
import ipaddress
from pathlib import Path
import re
import sys
import types
from typing import TYPE_CHECKING, Any, TypeVar, get_origin, overload
from uuid import UUID
from zoneinfo import ZoneInfo

from prompt_toolkit.styles import Style, merge_styles
from pydantic import BaseModel, SecretStr, ValidationError
from pydantic_core import PydanticUndefined

from promptantic.exceptions import NoHandlerError
from promptantic.handlers.constrained import ConstrainedIntHandler, ConstrainedStrHandler
from promptantic.handlers.date_time import (
    DateHandler,
    DateTimeHandler,
    TimeDeltaHandler,
    TimeHandler,
    TimezoneHandler,
)
from promptantic.handlers.enums import EnumHandler
from promptantic.handlers.literal import LiteralHandler
from promptantic.handlers.models import ModelHandler
from promptantic.handlers.network import IPv4Handler, IPv6Handler, NetworkHandler
from promptantic.handlers.primitives import (
    BoolHandler,
    DecimalHandler,
    FloatHandler,
    IntHandler,
    NoneHandler,
    StrHandler,
)
from promptantic.handlers.sequences import (
    DictHandler,
    ListHandler,
    SetHandler,
    TupleHandler,
)
from promptantic.handlers.special import (
    EmailHandler,
    ImportStringHandler,
    PathHandler,
    PatternHandler,
    SecretStrHandler,
    URLHandler,
    UUIDHandler,
)
from promptantic.handlers.stdlib import (
    CounterHandler,
    DefaultDictHandler,
    DequeHandler,
    FractionHandler,
    ModuleHandler,
)
from promptantic.handlers.unions import UnionHandler
from promptantic.type_utils import (
    is_constrained_int,
    is_constrained_str,
    is_enum_type,
    is_import_string,
    is_literal_type,
    is_model_type,
    is_skip_prompt,
    is_tuple_type,
    is_union_type,
    strip_annotated,
)
from promptantic.ui.style import DEFAULT_STYLE


M = TypeVar("M", bound=BaseModel)


if TYPE_CHECKING:
    from promptantic.type_utils import TypeHandler


class ModelGenerator:
    """Generate Pydantic model instances through interactive prompts."""

    def __init__(
        self,
        style: Style | None = None,
        show_progress: bool = True,
        allow_back: bool = True,
        retry_on_validation_error: bool = True,
    ) -> None:
        """Initialize the generator.

        Args:
            style: Optional custom style to use
            show_progress: Whether to show progress indication
            allow_back: Whether to allow going back to previous fields
            retry_on_validation_error: Whether to retry when validation fails
        """
        self.style = merge_styles([DEFAULT_STYLE, style]) if style else DEFAULT_STYLE
        self.show_progress = show_progress
        self.allow_back = allow_back
        self.retry_on_validation_error = retry_on_validation_error
        self._handlers: dict[type, TypeHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register the default type handlers."""
        # Primitive types
        self.register_handler(str, StrHandler(self))
        self.register_handler(int, IntHandler(self))
        self.register_handler(float, FloatHandler(self))
        self.register_handler(bool, BoolHandler(self))
        self.register_handler(Decimal, DecimalHandler(self))
        self.register_handler(type(None), NoneHandler(self))  # Add this line
        self.register_handler(re.Pattern, PatternHandler(self))

        # Sequence types
        self.register_handler(list, ListHandler(self))
        self.register_handler(dict, DictHandler(self))
        self.register_handler(set, SetHandler(self))
        self.register_handler(tuple, TupleHandler(self))
        # Model handler
        self.register_handler(BaseModel, ModelHandler(self))
        # Special types
        self.register_handler(SecretStr, SecretStrHandler(self))
        self.register_handler(Path, PathHandler(self))
        self.register_handler(UUID, UUIDHandler(self))

        # Network types
        self.register_handler(ipaddress.IPv4Address, IPv4Handler(self))
        self.register_handler(ipaddress.IPv6Address, IPv6Handler(self))
        self.register_handler(ipaddress.IPv4Network, NetworkHandler(self))
        self.register_handler(ipaddress.IPv6Network, NetworkHandler(self))

        # DateTime types
        self.register_handler(datetime.date, DateHandler(self))
        self.register_handler(datetime.time, TimeHandler(self))
        self.register_handler(datetime.datetime, DateTimeHandler(self))
        self.register_handler(datetime.timedelta, TimeDeltaHandler(self))
        self.register_handler(ZoneInfo, TimezoneHandler(self))
        # Enum handler
        self.register_handler(Enum, EnumHandler(self))

        # Additional stdlib handlers
        self.register_handler(Fraction, FractionHandler(self))
        self.register_handler(types.ModuleType, ModuleHandler(self))
        self.register_handler(Counter, CounterHandler(self))
        self.register_handler(deque, DequeHandler(self))
        self.register_handler(defaultdict, DefaultDictHandler(self))

        # Note: Union handler is special and handled in get_handler
        self._email_handler = EmailHandler(self)
        self._url_handler = URLHandler(self)
        # Store constrained handlers separately since they're not types
        self._constrained_str_handler = ConstrainedStrHandler(self)
        self._constrained_int_handler = ConstrainedIntHandler(self)

    def register_handler(self, typ: type, handler: TypeHandler) -> None:
        """Register a custom type handler.

        Args:
            typ: The type to handle
            handler: The handler instance
        """
        # Inject new handlers at beginning to allow extending / overriding our base set
        self._handlers = {typ: handler} | self._handlers

    def get_handler(self, typ: type[Any] | None, field_info: Any = None) -> TypeHandler:  # noqa: PLR0911
        """Get a handler for the given type."""
        typ = strip_annotated(typ)

        if typ is type(None):
            return self._handlers[type(None)]

        if typ is None:
            return self._handlers[str]

        # Check for constrained types
        if is_constrained_str(typ):
            return self._constrained_str_handler
        if is_constrained_int(typ):
            return self._constrained_int_handler

        # Check for Literal type
        if is_literal_type(typ):
            return LiteralHandler(self)

        # Check if it's a union type first
        if is_union_type(typ):
            return UnionHandler(self)

        # Check if it's a tuple type
        if is_tuple_type(typ):
            return self._handlers[tuple]

        # Check if it's an enum type
        if is_enum_type(typ):
            return self._handlers[Enum]

        # For model types, use the model handler
        if is_model_type(typ):
            return self._handlers[BaseModel]

        # Check for special string fields based on field info
        if typ is str and field_info is not None:
            if getattr(field_info, "email", False):
                return self._email_handler
            if getattr(field_info, "url", False):
                return self._url_handler
        if is_import_string(typ):
            return ImportStringHandler(self)

        # For regular types, look up the handler
        origin = get_origin(typ)
        handler = self._handlers.get(origin if origin is not None else typ)
        if handler is None:
            msg = f"No handler registered for type: {typ}"
            raise NoHandlerError(msg)
        return handler

    @overload
    def populate(self, model: type[M], _test_mode: bool = False) -> M: ...

    @overload
    def populate(self, model: M, _test_mode: bool = False) -> M: ...

    def populate(self, model: type[M] | M, _test_mode: bool = False) -> M:
        """Populate a model instance through interactive prompts.

        This is a synchronous wrapper around the async populate method.

        Args:
            model: The model class or instance to populate

        Returns:
            A populated model instance

        Raises:
            NoHandlerError: If no handler is found for a field type
        """
        if sys.platform == "win32":
            # Windows requires a specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        return asyncio.run(self.apopulate(model, _test_mode=_test_mode))

    @overload
    async def apopulate(self, model: type[M], _test_mode: bool = False) -> M: ...

    @overload
    async def apopulate(self, model: M, _test_mode: bool = False) -> M: ...

    async def apopulate(self, model: type[M] | M, _test_mode: bool = False) -> M:
        """Asynchronously populate a model instance.

        Args:
            model: The model class or instance to populate

        Returns:
            A populated model instance

        Raises:
            NoHandlerError: If no handler is found for a field type
        """
        if isinstance(model, type) and issubclass(model, BaseModel):
            model_cls = model
            defaults = {}
        elif isinstance(model, BaseModel):
            model_cls = model.__class__
            # Only get explicitly set values
            defaults = model.model_dump(exclude_unset=True)
        else:
            msg = f"Expected BaseModel class or instance, got {type(model)}"
            raise ValueError(msg)  # noqa: TRY004

        values: dict[str, Any] = {}
        total = len(model_cls.model_fields)
        current = 0

        try:
            for name, field in model_cls.model_fields.items():
                # Skip fields marked with skip_prompt
                if is_skip_prompt(field):
                    # Use default if available
                    if field.default not in (None, PydanticUndefined):
                        values[name] = field.default
                    # Use default_factory if available
                    elif field.default_factory is not None:
                        values[name] = field.default_factory()  # type: ignore
                    continue
                current += 1
                if self.show_progress:
                    print(f"\nField {current}/{total}")

                field_type = field.annotation if field.annotation is not None else str

                handler = self.get_handler(
                    field_type,
                    field_info=field,
                )
                description = field.description

                # Use instance value as default if it was set, otherwise use field default
                field_default = defaults.get(name, field.default)

                while True:
                    try:
                        value = await handler.handle(
                            field_name=name,
                            field_type=field_type,
                            description=description,
                            default=field_default,
                            field_info=field,
                            _test_mode=_test_mode,
                        )
                        values[name] = value
                        break
                    except ValidationError as e:
                        if not self.retry_on_validation_error:
                            raise
                        print(f"\033[91mValidation error: {e!s}\033[0m")
                        print("Please try again...")
                    except Exception as e:
                        msg = f"Error handling field {name}: {e!s}"
                        raise NoHandlerError(msg) from e

            return model_cls.model_validate(values)

        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            raise


if __name__ == "__main__":
    from pydantic import BaseModel, Field

    from promptantic import ModelGenerator

    class Person(BaseModel):
        name: str = Field(description="Person's full name")
        age: int = Field(description="Age in years")

    async def main():
        # Create and use the generator
        generator = ModelGenerator()
        person = await generator.apopulate(Person)
        print(person)

    import asyncio

    asyncio.run(main())
