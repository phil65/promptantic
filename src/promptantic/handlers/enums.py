"""Handlers for enum types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prompt_toolkit.shortcuts import radiolist_dialog

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler


if TYPE_CHECKING:
    from enum import Enum


class EnumHandler(BaseHandler):
    """Handler for Enum types."""

    async def handle(
        self,
        field_name: str,
        field_type: type[Enum],
        description: str | None = None,
        **options: Any,
    ) -> Enum:
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
        """
        # Create choices from enum values
        choices = [(member, f"{member.name} = {member.value}") for member in field_type]

        # Let user select from enum values
        selected = await radiolist_dialog(
            title=f"Select {field_name}",
            text=description or f"Choose a value for {field_name}:",
            values=choices,
        ).run_async()

        if selected is None:
            msg = "Selection cancelled"
            raise ValidationError(msg)

        return selected
