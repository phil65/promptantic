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

    # Always show description if available, independently of other parts
    if description:
        message.extend([
            ("", "\n"),
            ("class:field-description", f"{description}"),
        ])

    # Show default value if available
    if default is not None:
        message.extend([
            ("", "\n"),
            ("class:default-value", f"[default: {default}]"),
        ])

    # Add the final prompt marker
    message.extend([
        ("", "\n"),
        ("class:prompt", "> "),
    ])

    return FormattedText(message)
