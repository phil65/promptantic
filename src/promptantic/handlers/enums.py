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
        **options: Any,
    ) -> E:
        """Handle enum input.

        Args:
            field_name: Name of the field
            field_type: The enum class
            description: Optional field description
            **options: Additional options

        Returns:
            Selected enum value

        Raises:
            ValidationError: If selection is cancelled
            KeyboardInterrupt: If Ctrl+C is pressed
        """
        # Create choices from enum values
        choices = [(member, f"{member.name} = {member.value}") for member in field_type]

        print("\nUse arrow keys to select, Enter to confirm.")
        print("Press Esc, q, or Ctrl+C to cancel.\n")

        try:
            selected = await radiolist_dialog(
                title=f"Select {field_name}",
                text=description or f"Choose a value for {field_name}:",
                values=choices,
            ).run_async()
        except KeyboardInterrupt:
            print("\nSelection cancelled with Ctrl+C")
            raise

        if selected is None:
            msg = "Selection cancelled"
            raise ValidationError(msg)

        return selected
