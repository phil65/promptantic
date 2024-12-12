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
        default: datetime.date | None = None,
        **options: Any,
    ) -> datetime.date:
        """Handle date input."""
        session: PromptSession[Any] = PromptSession()
        default_str = default.isoformat() if default else None

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter date (YYYY-MM-DD)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return datetime.date.fromisoformat(result)
            except ValueError as e:
                msg = f"Invalid date format: {e!s}"
                raise ValidationError(msg) from e


class TimeHandler(BaseHandler):
    """Handler for time input."""

    def format_default(self, default: Any) -> str | None:
        """Format time default value."""
        if default is None:
            return None
        if isinstance(default, datetime.time):
            return default.isoformat()
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.time],
        description: str | None = None,
        default: datetime.time | None = None,
        **options: Any,
    ) -> datetime.time:
        """Handle time input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter time (HH:MM:SS)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return datetime.time.fromisoformat(result)
            except ValueError as e:
                msg = f"Invalid time format: {e!s}"
                raise ValidationError(msg) from e


class DateTimeHandler(BaseHandler):
    """Handler for datetime input."""

    def format_default(self, default: Any) -> str | None:
        """Format datetime default value."""
        if default is None:
            return None
        if isinstance(default, datetime.datetime):
            if default.tzinfo:
                return default.isoformat()
            return default.replace(tzinfo=datetime.UTC).isoformat()
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.datetime],
        description: str | None = None,
        default: datetime.datetime | None = None,
        **options: Any,
    ) -> datetime.datetime:
        """Handle datetime input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter datetime (YYYY-MM-DD HH:MM:SS[±HH:MM])",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                # Parse datetime with timezone support
                dt = datetime.datetime.fromisoformat(result)

                # Convert naive datetime to UTC if no timezone
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=datetime.UTC)
            except ValueError as e:
                msg = f"Invalid datetime format: {e!s}"
                raise ValidationError(msg) from e
            else:
                return dt


class TimeDeltaHandler(BaseHandler):
    """Handler for timedelta input."""

    def format_default(self, default: Any) -> str | None:
        """Format timedelta default value."""
        if default is None:
            return None
        if isinstance(default, datetime.timedelta):
            return str(default.total_seconds())
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[datetime.timedelta],
        description: str | None = None,
        default: datetime.timedelta | None = None,
        **options: Any,
    ) -> datetime.timedelta:
        """Handle timedelta input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter duration in seconds",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

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
        default: ZoneInfo | None = None,
        **options: Any,
    ) -> ZoneInfo:
        """Handle timezone input."""
        session: PromptSession[Any] = PromptSession(completer=self.completer)
        default_str = str(default) if default is not None else None

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter timezone name (e.g. Europe/London)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return ZoneInfo(result)
            except ValueError as e:
                msg = f"Invalid timezone: {e!s}"
                raise ValidationError(msg) from e
