"""Handlers for primitive types."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prompt_toolkit.shortcuts import PromptSession

from promptantic.completers import FieldCompleter
from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


class StrHandler(BaseHandler[str]):
    """Handler for string input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[str],
        description: str | None = None,
        default: Any = None,
        **options: Any,
    ) -> str:
        """Handle string input."""
        field_info = options.get("field_info")
        # Get completions from field info extra attributes
        completions = (
            getattr(field_info, "json_schema_extra", {}).get("completions")
            if field_info
            else None
        )
        completer = FieldCompleter(completions) if completions else None

        session = PromptSession(completer=completer)
        default_str = self.format_default(default)

        return await session.prompt_async(
            create_field_prompt(field_name, description, default=default_str),
            default=default_str if default_str is not None else "",
        )


class IntHandler(BaseHandler[int]):
    """Handler for integer input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[int],
        description: str | None = None,
        default: Any = None,
        **options: Any,
    ) -> int:
        """Handle integer input."""
        while True:
            try:
                session = PromptSession()
                default_str = self.format_default(default)
                result = await session.prompt_async(
                    create_field_prompt(field_name, description, default=default_str),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return int(result)
            except ValueError as e:
                msg = f"Please enter a valid integer: {e!s}"
                raise ValidationError(msg) from e


class FloatHandler(BaseHandler[float]):
    """Handler for float input."""

    def format_default(self, default: Any) -> str | None:
        """Format float default value."""
        if default is None:
            return None
        # Use repr to preserve precision
        return repr(float(default))

    async def handle(
        self,
        field_name: str,
        field_type: type[float],
        description: str | None = None,
        default: float | None = None,
        **options: Any,
    ) -> float:
        """Handle float input."""
        while True:
            try:
                session = PromptSession()
                default_str = self.format_default(default)
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description,
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return float(result)
            except ValueError as e:
                msg = f"Please enter a valid float: {e!s}"
                raise ValidationError(msg) from e


class DecimalHandler(BaseHandler[Decimal]):
    """Handler for decimal input."""

    def format_default(self, default: Any) -> str | None:
        """Format decimal default value."""
        if default is None:
            return None
        # Convert to Decimal if not already
        if not isinstance(default, Decimal):
            default = Decimal(str(default))
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[Decimal],
        description: str | None = None,
        default: Decimal | float | int | str | None = None,  # noqa: PYI041
        **options: Any,
    ) -> Decimal:
        """Handle decimal input."""
        while True:
            try:
                session = PromptSession()
                default_str = self.format_default(default)
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description,
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    # Ensure default is converted to Decimal
                    if isinstance(default, Decimal):
                        return default
                    return Decimal(str(default))

                return Decimal(result)
            except (ValueError, ArithmeticError) as e:
                msg = f"Please enter a valid decimal: {e!s}"
                raise ValidationError(msg) from e


class BoolHandler(BaseHandler[bool]):
    """Handler for boolean input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[bool],
        description: str | None = None,
        default: bool | None = None,
        **options: Any,
    ) -> bool:
        """Handle boolean input."""
        default_str = None
        if default is not None:
            default_str = "y" if default else "n"

        while True:
            session = PromptSession()
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    f"{description} (y/n)" if description else "(y/n)",
                    default=default_str,
                ),
                default=default_str if default_str is not None else "",
            )

            # Handle empty input with default
            if not result and default is not None:
                return default

            result = result.lower().strip()
            if result in ("y", "yes", "true", "1"):
                return True
            if result in ("n", "no", "false", "0"):
                return False

            msg = "Please enter 'y' or 'n'"
            raise ValidationError(msg)
