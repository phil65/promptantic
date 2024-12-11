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


class LiteralHandler(BaseHandler[Any]):
    """Handler for Literal types."""

    async def handle(
        self,
        field_name: str,
        field_type: Any,
        description: str | None = None,
        default: Any = None,
        **options: Any,
    ) -> Any:
        """Handle Literal input."""
        # Get allowed values from the Literal type
        values = get_args(field_type)
        choices = [(value, str(value)) for value in values]

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
