"""Text formatting utilities."""

from __future__ import annotations

from prompt_toolkit.formatted_text import FormattedText


def create_field_prompt(
    field_name: str,
    description: str | None = None,
) -> FormattedText:
    """Create a formatted field prompt.

    Args:
        field_name: Name of the field
        description: Optional field description

    Returns:
        Formatted text for the prompt
    """
    message = [
        ("class:field-name", field_name),
    ]
    if description:
        message.extend([
            ("", ": "),
            ("class:field-description", f"({description})"),
        ])
    message.append(("", "\n> "))

    return FormattedText(message)
