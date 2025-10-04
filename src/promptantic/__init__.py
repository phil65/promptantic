"""Interactive prompt_toolkit based generator for Pydantic models."""

from __future__ import annotations

from typing import Literal

from promptantic.generator import ModelGenerator
from promptantic.exceptions import PromptanticError
from promptantic.creator import ModelCreator

__version__ = "0.5.2"

SKIP_PROMPT_KEY = "skip_prompt"
SkipPromptType = bool | Literal["always"]

import warnings

warnings.filterwarnings(
    "ignore", message="Valid config keys have changed in V2:*", category=UserWarning
)

__all__ = ["SKIP_PROMPT_KEY", "ModelGenerator", "PromptanticError"]
__all__ = ["SKIP_PROMPT_KEY", "ModelCreator", "ModelGenerator", "PromptanticError"]
