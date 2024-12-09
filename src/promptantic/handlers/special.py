"""Handlers for special types like URLs, Paths, Emails etc."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from uuid import UUID

from prompt_toolkit.shortcuts import PromptSession
from pydantic import SecretStr

from promptantic.completers import EnhancedPathCompleter
from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


class SecretStrHandler(BaseHandler):
    """Handler for SecretStr input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[SecretStr],
        description: str | None = None,
        **options: Any,
    ) -> SecretStr:
        """Handle SecretStr input."""
        session = PromptSession()
        result = await session.prompt_async(
            create_field_prompt(field_name, description),
            is_password=True,
        )
        return SecretStr(result)


class PathHandler(BaseHandler):
    """Handler for Path input."""

    def __init__(self, generator: Any) -> None:
        super().__init__(generator)
        self.completer = EnhancedPathCompleter()

    async def handle(
        self,
        field_name: str,
        field_type: type[Path],
        description: str | None = None,
        **options: Any,
    ) -> Path:
        """Handle Path input."""
        session = PromptSession(completer=self.completer)
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(field_name, description),
                )
                path = Path(result).resolve()
            except Exception as e:
                msg = f"Invalid path: {e!s}"
                raise ValidationError(msg) from e
            else:
                return path


class UUIDHandler(BaseHandler):
    """Handler for UUID input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[UUID],
        description: str | None = None,
        **options: Any,
    ) -> UUID:
        """Handle UUID input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(field_name, description),
                )
                return UUID(result)
            except ValueError as e:
                msg = f"Invalid UUID: {e!s}"
                raise ValidationError(msg) from e


class EmailHandler(BaseHandler):
    """Handler for email input with basic validation."""

    _email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

    async def handle(
        self,
        field_name: str,
        field_type: type[str],
        description: str | None = None,
        **options: Any,
    ) -> str:
        """Handle email input."""
        session = PromptSession()
        while True:
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    description or "Enter a valid email address",
                ),
            )
            if self._email_regex.match(result):
                return result

            msg = "Invalid email address format"
            raise ValidationError(msg)


class URLHandler(BaseHandler):
    """Handler for URL input with basic validation."""

    _url_regex = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    async def handle(
        self,
        field_name: str,
        field_type: type[str],
        description: str | None = None,
        **options: Any,
    ) -> str:
        """Handle URL input."""
        session = PromptSession()
        while True:
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    description or "Enter a valid URL",
                ),
            )
            if self._url_regex.match(result):
                return result

            msg = "Invalid URL format"
            raise ValidationError(msg)
