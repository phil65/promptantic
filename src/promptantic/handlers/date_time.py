"""Handlers for datetime-related types."""

from __future__ import annotations

import datetime
from typing import Any
from zoneinfo import ZoneInfo

from prompt_toolkit.shortcuts import PromptSession

from promptantic.completers import TimezoneCompleter
from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


class DateHandler(BaseHandler):
    """Handler for date input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.date],
        description: str | None = None,
        **options: Any,
    ) -> datetime.date:
        """Handle date input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter date (YYYY-MM-DD)",
                    ),
                )
                return datetime.date.fromisoformat(result)
            except ValueError as e:
                msg = f"Invalid date format: {e!s}"
                raise ValidationError(msg) from e


class TimeHandler(BaseHandler):
    """Handler for time input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.time],
        description: str | None = None,
        **options: Any,
    ) -> datetime.time:
        """Handle time input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter time (HH:MM:SS)",
                    ),
                )
                return datetime.time.fromisoformat(result)
            except ValueError as e:
                msg = f"Invalid time format: {e!s}"
                raise ValidationError(msg) from e


class DateTimeHandler(BaseHandler):
    """Handler for datetime input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.datetime],
        description: str | None = None,
        **options: Any,
    ) -> datetime.datetime:
        """Handle datetime input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter datetime (YYYY-MM-DD HH:MM:SS)",
                    ),
                )
                return datetime.datetime.fromisoformat(result)
            except ValueError as e:
                msg = f"Invalid datetime format: {e!s}"
                raise ValidationError(msg) from e


class TimeDeltaHandler(BaseHandler):
    """Handler for timedelta input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.timedelta],
        description: str | None = None,
        **options: Any,
    ) -> datetime.timedelta:
        """Handle timedelta input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter duration in seconds",
                    ),
                )
                return datetime.timedelta(seconds=float(result))
            except ValueError as e:
                msg = f"Invalid duration: {e!s}"
                raise ValidationError(msg) from e


class TimezoneHandler(BaseHandler):
    """Handler for timezone input."""

    def __init__(self, generator: Any) -> None:
        super().__init__(generator)
        self.completer = TimezoneCompleter()

    async def handle(
        self,
        field_name: str,
        field_type: type[ZoneInfo],
        description: str | None = None,
        **options: Any,
    ) -> ZoneInfo:
        """Handle timezone input."""
        session = PromptSession(completer=self.completer)
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter timezone name (e.g. Europe/London)",
                    ),
                )
                return ZoneInfo(result)
            except ValueError as e:
                msg = f"Invalid timezone: {e!s}"
                raise ValidationError(msg) from e
