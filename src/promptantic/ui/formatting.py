"""Text formatting utilities."""

from __future__ import annotations

from prompt_toolkit.formatted_text import FormattedText


def create_field_prompt(
    field_name: str,
    description: str | None = None,
    default: str | None = None,
) -> FormattedText:
    """Create a formatted field prompt.

    Args:
        field_name: Name of the field
        description: Optional field description
        default: Optional default value

    Returns:
        Formatted text for the prompt
    """
    message = [
        ("class:field-name", field_name),
    ]

    parts = []
    if description:
        parts.append(f"({description})")
    if default is not None:
        parts.append(f"[default: {default}]")

    if parts:
        message.extend([
            ("", ": "),
            ("class:field-description", " ".join(parts)),
        ])

    message.append(("", "\n> "))
    return FormattedText(message)
