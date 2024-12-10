"""Handlers for constrained types."""

from __future__ import annotations

import re
from typing import Any

from prompt_toolkit.shortcuts import PromptSession

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


class ConstrainedStrHandler(BaseHandler):
    """Handler for constrained string input."""

    async def handle(
        self,
        field_name: str,
        field_type: Any,  # Can't use precise type due to Pydantic internals
        description: str | None = None,
        **options: Any,
    ) -> str:
        """Handle constrained string input."""
        # Get constraints from the type object
        min_length = getattr(field_type, "min_length", None)
        max_length = getattr(field_type, "max_length", None)
        pattern = getattr(field_type, "pattern", None)

        constraints = []
        if min_length is not None:
            constraints.append(f"min length: {min_length}")
        if max_length is not None:
            constraints.append(f"max length: {max_length}")
        if pattern is not None:
            constraints.append(f"pattern: {pattern}")

        constraint_desc = " | ".join(constraints)
        full_desc = f"{description or ''}\nConstraints: {constraint_desc}"

        session = PromptSession()
        while True:
            result = await session.prompt_async(
                create_field_prompt(field_name, full_desc),
            )

            try:
                # Validate length constraints
                if (
                    field_type.min_length is not None
                    and len(result) < field_type.min_length
                ):
                    msg = f"String too short (min: {field_type.min_length})"
                    raise ValueError(msg)  # noqa: TRY301

                if (
                    field_type.max_length is not None
                    and len(result) > field_type.max_length
                ):
                    msg = f"String too long (max: {field_type.max_length})"
                    raise ValueError(msg)  # noqa: TRY301

                # Validate pattern
                if field_type.pattern is not None and not re.match(
                    field_type.pattern, result
                ):
                    msg = f"String does not match pattern: {field_type.pattern}"
                    raise ValueError(msg)  # noqa: TRY301

            except ValueError as e:
                msg = f"Validation failed: {e!s}"
                raise ValidationError(msg) from e
            else:
                return result


class ConstrainedIntHandler(BaseHandler):
    """Handler for constrained integer input."""

    async def handle(
        self,
        field_name: str,
        field_type: Any,  # Can't use precise type due to Pydantic internals
        description: str | None = None,
        **options: Any,
    ) -> int:
        """Handle constrained integer input."""
        # Get constraints from the type object
        gt = getattr(field_type, "gt", None)
        ge = getattr(field_type, "ge", None)
        lt = getattr(field_type, "lt", None)
        le = getattr(field_type, "le", None)
        multiple_of = getattr(field_type, "multiple_of", None)

        # Build constraint description
        constraints = []
        if gt is not None:
            constraints.append(f"greater than {gt}")
        if ge is not None:
            constraints.append(f"greater or equal to {ge}")
        if lt is not None:
            constraints.append(f"less than {lt}")
        if le is not None:
            constraints.append(f"less or equal to {le}")
        if multiple_of is not None:
            constraints.append(f"multiple of {multiple_of}")

        constraint_desc = " | ".join(constraints)
        full_desc = (
            f"{description or ''}\nConstraints: {constraint_desc}"
            if constraints
            else description
        )

        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(field_name, full_desc),
                )
                value = int(result)

                # Validate constraints
                if gt is not None and value <= gt:
                    msg = f"Must be greater than {gt}"
                    raise ValueError(msg)  # noqa: TRY301
                if ge is not None and value < ge:
                    msg = f"Must be greater than or equal to {ge}"
                    raise ValueError(msg)  # noqa: TRY301
                if lt is not None and value >= lt:
                    msg = f"Must be less than {lt}"
                    raise ValueError(msg)  # noqa: TRY301
                if le is not None and value > le:
                    msg = f"Must be less than or equal to {le}"
                    raise ValueError(msg)  # noqa: TRY301
                if multiple_of is not None and value % multiple_of != 0:
                    msg = f"Must be multiple of {multiple_of}"
                    raise ValueError(msg)  # noqa: TRY301
            except ValueError as e:
                msg = f"Validation failed: {e!s}"
                raise ValidationError(msg) from e
            else:
                return value