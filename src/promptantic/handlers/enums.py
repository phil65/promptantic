"""Handlers for enum types."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

from prompt_toolkit.shortcuts import radiolist_dialog

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler


E = TypeVar("E", bound=Enum)


class EnumHandler(BaseHandler[E]):
    """Handler for Enum types."""

    async def handle(
        self,
        field_name: str,
        field_type: type[E],
        description: str | None = None,
        default: E | None = None,
        **options: Any,
    ) -> E:
        """Handle enum input."""
        # Create choices from enum values
        choices = [(member, f"{member.name} = {member.value}") for member in field_type]

        # Find default index if exists
        default_idx = None
        if default is not None:
            for idx, (value, _) in enumerate(choices):
                if value == default:
                    default_idx = idx
                    break

        print("\nUse arrow keys to select, Enter to confirm.")
        print("Press Esc, q, or Ctrl+C to cancel.\n")

        try:
            selected = await radiolist_dialog(
                title=f"Select {field_name}",
                text=description or f"Choose a value for {field_name}:",
                values=choices,
                default=choices[default_idx][0] if default_idx is not None else None,
            ).run_async()
        except KeyboardInterrupt:
            print("\nSelection cancelled with Ctrl+C")
            raise

        if selected is None:
            if default is not None:
                return default
            msg = "Selection cancelled"
            raise ValidationError(msg)

        return selected
