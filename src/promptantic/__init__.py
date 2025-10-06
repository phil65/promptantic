"""Interactive prompt_toolkit based generator for Pydantic models."""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("promptantic")

from typing import Literal

from promptantic.generator import ModelGenerator
from promptantic.exceptions import PromptanticError
from promptantic.creator import ModelCreator


SKIP_PROMPT_KEY = "skip_prompt"
SkipPromptType = bool | Literal["always"]

import warnings

warnings.filterwarnings(
    "ignore", message="Valid config keys have changed in V2:*", category=UserWarning
)

__all__ = [
    "SKIP_PROMPT_KEY",
    "ModelGenerator",
    "PromptanticError",
    "__version__",
]
__all__ = [
    "SKIP_PROMPT_KEY",
    "ModelCreator",
    "ModelGenerator",
    "PromptanticError",
    "__version__",
]
