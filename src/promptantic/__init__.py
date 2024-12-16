"""Interactive prompt_toolkit based generator for Pydantic models."""

from __future__ import annotations

from typing import Literal

from promptantic.generator import ModelGenerator
from promptantic.exceptions import PromptanticError

__version__ = "0.5.0"

SKIP_PROMPT_KEY = "skip_prompt"
SkipPromptType = bool | Literal["always"]

__all__ = ["SKIP_PROMPT_KEY", "ModelGenerator", "PromptanticError"]
