"""Style definitions for model_prompter."""

from __future__ import annotations

from prompt_toolkit.styles import Style


DEFAULT_STYLE = Style.from_dict({
    "field-name": "bold #00aa00",  # Green bold
    "field-description": "italic #888888",  # Gray italic
    "error": "bold #ff0000",  # Red bold
    "prompt": "#00aa00",  # Green
})
