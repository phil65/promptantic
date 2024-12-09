"""Handlers for union types."""

from __future__ import annotations

from typing import Any

from prompt_toolkit.shortcuts import radiolist_dialog

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.type_utils import get_union_types, is_model_type


def get_type_display_name(typ: type[Any]) -> str:
    """Get a user-friendly display name for a type.

    Args:
        typ: The type to get a name for

    Returns:
        A user-friendly name for the type
    """
    if is_model_type(typ):
        return typ.__name__  # type: ignore
    return typ.__name__.lower()


class UnionHandler(BaseHandler):
    """Handler for union types."""

    async def handle(
        self,
        field_name: str,
        field_type: Any,
        description: str | None = None,
        **options: Any,
    ) -> Any:
        """Handle union type input.

        Args:
            field_name: Name of the field
            field_type: The union type
            description: Optional field description
            **options: Additional options

        Returns:
            A value of one of the union types
        """
        # Get the possible types from the union
        types = get_union_types(field_type)

        # Create choices for the dialog
        choices = [(typ, get_type_display_name(typ)) for typ in types]

        # Let user select the type
        selected_type = await radiolist_dialog(
            title=f"Select type for {field_name}",
            text=description or "Choose the type to use:",
            values=choices,
        ).run_async()

        if selected_type is None:
            msg = "Type selection cancelled"
            raise ValidationError(msg)

        # Get handler for selected type and use it
        handler = self.generator.get_handler(selected_type)
        return await handler.handle(
            field_name=field_name,
            field_type=selected_type,
            description=description,
            **options,
        )
