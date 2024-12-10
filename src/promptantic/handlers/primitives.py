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
        **options: Any,
    ) -> str:
        """Handle string input."""
        # Check for completions in field info
        completions = options.get("field_info", {}).get("completions")
        completer = FieldCompleter(completions) if completions else None

        session = PromptSession(completer=completer)
        return await session.prompt_async(create_field_prompt(field_name, description))


class IntHandler(BaseHandler[int]):
    """Handler for integer input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[int],
        description: str | None = None,
        **options: Any,
    ) -> int:
        """Handle integer input."""
        while True:
            try:
                session = PromptSession()
                result = await session.prompt_async(
                    create_field_prompt(field_name, description)
                )
                return int(result)
            except ValueError as e:
                msg = f"Please enter a valid integer: {e!s}"
                raise ValidationError(msg) from e


class FloatHandler(BaseHandler[float]):
    """Handler for float input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[float],
        description: str | None = None,
        **options: Any,
    ) -> float:
        """Handle float input."""
        while True:
            try:
                session = PromptSession()
                result = await session.prompt_async(
                    create_field_prompt(field_name, description)
                )
                return float(result)
            except ValueError as e:
                msg = f"Please enter a valid float: {e!s}"
                raise ValidationError(msg) from e


class DecimalHandler(BaseHandler[Decimal]):
    """Handler for decimal input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[Decimal],
        description: str | None = None,
        **options: Any,
    ) -> Decimal:
        """Handle decimal input."""
        while True:
            try:
                session = PromptSession()
                result = await session.prompt_async(
                    create_field_prompt(field_name, description)
                )
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
        **options: Any,
    ) -> bool:
        """Handle boolean input."""
        while True:
            session = PromptSession()
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    f"{description} (y/n)" if description else "(y/n)",
                )
            )
            result = result.lower().strip()
            if result in ("y", "yes", "true", "1"):
                return True
            if result in ("n", "no", "false", "0"):
                return False

            msg = "Please enter 'y' or 'n'"
            raise ValidationError(msg)