"""Handlers for union types."""

from __future__ import annotations

from typing import Any
from prompt_toolkit.shortcuts import radiolist_dialog, create_confirm_session
from pydantic.fields import PydanticUndefined

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.type_utils import get_union_types, is_model_type, strip_annotated


def get_type_display_name(typ: type[Any] | None) -> str:
    """Get a user-friendly display name for a type.

    Args:
        typ: The type to get a name for

    Returns:
        A user-friendly name for the type
    """
    if typ is None:
        return "None"
    if is_model_type(typ):
        return typ.__name__  # type: ignore
    return typ.__name__.lower() if hasattr(typ, "__name__") else str(typ)


class UnionHandler(BaseHandler[Any]):
    """Handler for union types."""

    def get_type_display_name(self, typ: type[Any] | None) -> str:
        """Get user-friendly display name for a type."""
        if typ is None:
            return "None"
        if is_model_type(typ):
            return typ.__name__ if hasattr(typ, "__name__") else str(typ)
        if hasattr(typ, "__name__"):
            return typ.__name__.lower()
        return str(typ)

    async def handle(
        self,
        field_name: str,
        field_type: Any,
        description: str | None = None,
        default: Any = None,
        **options: Any,
    ) -> Any:
        """Handle union type input."""
        field_type = strip_annotated(field_type)

        types = get_union_types(field_type)

        # If we have a default, try to determine its type
        default_type = None
        if default is not None and default is not PydanticUndefined:
            for typ in types:
                try:
                    if typ is None and default is None:
                        default_type = None
                        break
                    if isinstance(default, typ):
                        default_type = typ
                        break
                except TypeError:
                    continue

        # Create choices for type selection
        choices = [(typ, self.get_type_display_name(typ)) for typ in types]
        input_type = None
        # If we have a default type, put it first
        if default_type is not None:
            choices = [(default_type, self.get_type_display_name(default_type))] + [
                (t, n) for t, n in choices if t != default_type
            ]
        elif len(choices) == 2:  # if default is None
            # Put None type first
            for _t, _n in choices:
                if _t is not None:
                    input_type = _t
                    break
            result = await create_confirm_session(f"Default value for {field_name} is None. Use None as default?").prompt_async(
                default="y"
            )
            if result:
                return None

        if input_type is None:
            print("\nSelect type to use:")
            print("Use arrow keys to select, Enter to confirm.")
            print("Press Esc, q, or Ctrl+C to cancel.\n")

            try:
                selected_type = await radiolist_dialog(
                    title=f"Select type for {field_name}",
                    text=description or "Choose the type to use:",
                    values=choices,
                    default=default_type if default_type is not None else None,
                ).run_async()
            except KeyboardInterrupt:
                print("\nSelection cancelled with Ctrl+C")
                raise

            if selected_type is None:
                msg = "Type selection cancelled"
                raise ValidationError(msg)
        else:
            selected_type = input_type

        # Get handler for selected type and use it
        handler = self.generator.get_handler(selected_type)

        # Pass the default only if it matches the selected type
        type_default = default if selected_type == default_type else None

        return await handler.handle(
            field_name=field_name,
            field_type=selected_type,
            description=description,
            default=type_default,
            **options,
        )
