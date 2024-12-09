"""Handler for Literal types."""

from __future__ import annotations

from typing import Any, get_args

from prompt_toolkit.shortcuts import radiolist_dialog

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler


def get_literal_choices(field_type: type[Any]) -> list[tuple[Any, str]]:
    """Get choices from a Literal type.

    Args:
        field_type: The Literal type

    Returns:
        List of (value, display_name) tuples
    """
    values = get_args(field_type)
    return [(value, str(value)) for value in values]


class LiteralHandler(BaseHandler):
    """Handler for Literal types."""

    async def handle(
        self,
        field_name: str,
        field_type: type[Any],
        description: str | None = None,
        **options: Any,
    ) -> Any:
        """Handle Literal input.

        Args:
            field_name: Name of the field
            field_type: The Literal type
            description: Optional field description
            **options: Additional options

        Returns:
            Selected literal value

        Raises:
            ValidationError: If selection is cancelled
        """
        choices = get_literal_choices(field_type)

        # Let user select from literal values
        selected = await radiolist_dialog(
            title=f"Select {field_name}",
            text=description or f"Choose a value for {field_name}:",
            values=choices,
        ).run_async()

        if selected is None:
            msg = "Selection cancelled"
            raise ValidationError(msg)

        return selected
