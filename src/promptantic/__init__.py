"""Promptantic: main package.

Generate pydantic models using prompts.
"""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("promptantic")
__title__ = "Promptantic"

__author__ = "Philipp Temminghoff"

from typing import Literal

from promptantic.api import fill
from promptantic.form import (
    FormCancelledError,
    FormTarget,
    FormValidationError,
    SchemaError,
    target_for,
)
from promptantic.generator import ModelGenerator
from promptantic.exceptions import PromptanticError
from promptantic.creator import ModelCreator
from promptantic.model_spec import FieldSpec, ModelSpec


SKIP_PROMPT_KEY = "skip_prompt"
SkipPromptType = bool | Literal["always"]

import warnings

warnings.filterwarnings(
    "ignore", message="Valid config keys have changed in V2:*", category=UserWarning
)

__all__ = [
    "SKIP_PROMPT_KEY",
    "FieldSpec",
    "FormCancelledError",
    "FormTarget",
    "FormValidationError",
    "ModelCreator",
    "ModelGenerator",
    "ModelSpec",
    "PromptanticError",
    "SchemaError",
    "__version__",
    "fill",
    "target_for",
]
