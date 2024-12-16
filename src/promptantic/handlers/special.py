"""Handlers for special types like URLs, Paths, Emails etc."""

from __future__ import annotations

import os
from pathlib import Path, PosixPath, WindowsPath
import re
from typing import Any, cast, get_args, get_origin
from uuid import UUID

from prompt_toolkit.shortcuts import PromptSession
from pydantic import SecretStr
from pydantic_core import PydanticUndefined

from promptantic.completers import EnhancedPathCompleter, ImportStringCompleter
from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


MSG = "Enter a Python import path (e.g. 'package.module' or 'package.module:Class')"


class SecretStrHandler(BaseHandler):
    """Handler for SecretStr input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[SecretStr],
        description: str | None = None,
        default: SecretStr | None = None,
        **options: Any,
    ) -> SecretStr:
        """Handle SecretStr input."""
        session: PromptSession[Any] = PromptSession()

        # Show placeholder for default if exists
        default_placeholder = "********" if default is not None else None

        result = await session.prompt_async(
            create_field_prompt(
                field_name,
                description,
                default=default_placeholder,
            ),
            is_password=True,
        )

        # Handle empty input with default
        if not result and default is not None:
            return default

        return SecretStr(result)


class PathHandler(BaseHandler[os.PathLike[str]]):
    """Handler for path-like objects."""

    def __init__(self, generator: Any) -> None:
        super().__init__(generator)
        self.completer = EnhancedPathCompleter()
        # Cache available path classes
        self._upath = None
        try:
            from upath import UPath

            self._upath = UPath
        except ImportError:
            pass

    def _get_path_class(
        self, field_type: type[os.PathLike[str]]
    ) -> type[os.PathLike[str]]:
        """Get the appropriate path class based on the field type.

        Args:
            field_type: The requested path type

        Returns:
            The appropriate path class to use
        """
        if field_type is Path or field_type in (WindowsPath, PosixPath):
            return Path
        if self._upath is not None and field_type is self._upath:
            return self._upath
        # For generic PathLike, prefer UPath if available
        if field_type is os.PathLike and self._upath is not None:
            return self._upath
        # Default to pathlib.Path
        return Path

    def format_default(self, default: Any) -> str | None:
        """Format path default value."""
        if default is None or default is PydanticUndefined:
            return None
        if isinstance(default, str | os.PathLike):
            return str(Path(default).expanduser())
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[os.PathLike[str]],
        description: str | None = None,
        default: os.PathLike[str] | str | None = None,
        **options: Any,
    ) -> os.PathLike[str]:
        """Handle path input."""
        path_cls = self._get_path_class(field_type)
        session: PromptSession[str] = PromptSession(completer=self.completer)
        default_str = self.format_default(default)

        # Safely get field extra info
        field_info = options.get("field_info")
        json_schema_extra = getattr(field_info, "json_schema_extra", None)
        field_extra = json_schema_extra if json_schema_extra else {}

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter a file path",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return path_cls(default).expanduser()  # type: ignore

                path = path_cls(result).expanduser()  # type: ignore

                # Optional: Add validation for existence/type
                if field_extra.get("must_exist", False) and not path.exists():
                    msg = f"Path does not exist: {path}"
                    raise ValidationError(msg)  # noqa: TRY301
                if field_extra.get("file_only", False) and not path.is_file():
                    msg = f"Not a file: {path}"
                    raise ValidationError(msg)  # noqa: TRY301
                if field_extra.get("dir_only", False) and not path.is_dir():
                    msg = f"Not a directory: {path}"
                    raise ValidationError(msg)  # noqa: TRY301
            except Exception as e:
                msg = f"Invalid path: {e!s}"
                raise ValidationError(msg) from e
            else:
                return path


class UUIDHandler(BaseHandler):
    """Handler for UUID input."""

    def format_default(self, default: Any) -> str | None:
        """Format UUID default value."""
        if default is None or default is PydanticUndefined:
            return None
        # Convert string to UUID if needed
        if isinstance(default, str):
            default = UUID(default)
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[UUID],
        description: str | None = None,
        default: UUID | str | None = None,
        **options: Any,
    ) -> UUID:
        """Handle UUID input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description
                        or "Enter UUID (e.g. 123e4567-e89b-12d3-a456-426614174000)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    if isinstance(default, str):
                        return UUID(default)
                    return default

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
        default: str | None = None,
        **options: Any,
    ) -> str:
        """Handle email input."""
        session: PromptSession[Any] = PromptSession()

        # Safely get field extra info
        field_info = options.get("field_info")
        json_schema_extra = getattr(field_info, "json_schema_extra", None)
        field_extra = json_schema_extra if json_schema_extra else {}

        # Get custom regex pattern if provided
        custom_pattern = field_extra.get("email_pattern")
        regex = re.compile(custom_pattern) if custom_pattern else self._email_regex

        while True:
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    description or "Enter a valid email address",
                    default=default,
                ),
                default=default if default is not None else "",
            )

            # Handle empty input with default
            if not result and default is not None:
                if not regex.match(default):
                    msg = f"Default email is invalid: {default}"
                    raise ValidationError(msg)
                return default

            if regex.match(result):
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
        default: str | None = None,
        **options: Any,
    ) -> str:
        """Handle URL input."""
        session: PromptSession[Any] = PromptSession()

        # Safely get field extra info
        field_info = options.get("field_info")
        json_schema_extra = getattr(field_info, "json_schema_extra", None)
        field_extra = json_schema_extra if json_schema_extra else {}

        # Get custom regex pattern if provided
        custom_pattern = field_extra.get("url_pattern")
        regex = re.compile(custom_pattern) if custom_pattern else self._url_regex

        while True:
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    description or "Enter a valid URL",
                    default=default,
                ),
                default=default if default is not None else "",
            )

            # Handle empty input with default
            if not result and default is not None:
                if not regex.match(default):
                    msg = f"Default URL is invalid: {default}"
                    raise ValidationError(msg)
                return default

            if regex.match(result):
                return result

            msg = "Invalid URL format"
            raise ValidationError(msg)


class ImportStringHandler(BaseHandler[str]):
    """Handler for Pydantic ImportString with autocompletion."""

    def __init__(self, generator: Any) -> None:
        super().__init__(generator)
        self.completer = ImportStringCompleter()

    async def handle(
        self,
        field_name: str,
        field_type: Any,
        description: str | None = None,
        default: str | None = None,
        **options: Any,
    ) -> str:
        """Handle ImportString input."""
        # Get the actual validation function from the Annotated type
        validator = None
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if args and len(args) > 1:
                validator = args[1]

        if not validator:
            msg = "Invalid ImportString type"
            raise ValueError(msg)

        session: PromptSession[Any] = PromptSession(completer=self.completer)

        while True:
            result = await session.prompt_async(
                create_field_prompt(
                    field_name,
                    description or "Enter a Python import path",
                    default=default,
                ),
                default=default if default is not None else "",
            )

            # Handle empty input with default
            if not result and default is not None:
                try:
                    validator(default)
                except ValueError as e:
                    msg = f"Default import path is invalid: {e}"
                    raise ValidationError(msg) from e
                else:
                    return default

            try:
                validator(result)
            except ValueError as e:
                msg = f"Invalid import path: {e}"
                raise ValidationError(msg) from e
            else:
                return result


class PatternHandler(BaseHandler[re.Pattern[str]]):
    """Handler for regular expression patterns."""

    def format_default(self, default: Any) -> str | None:
        """Format regex pattern default value."""
        if default is None or default is PydanticUndefined:
            return None
        if isinstance(default, str):
            return default
        if isinstance(default, re.Pattern):
            return default.pattern
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[re.Pattern[str]],
        description: str | None = None,
        default: re.Pattern[str] | str | None = None,
        **options: Any,
    ) -> re.Pattern[str]:
        """Handle regex pattern input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        # Get field options for flags
        field_info = options.get("field_info")
        json_schema_extra = getattr(field_info, "json_schema_extra", {})
        flags = json_schema_extra.get("regex_flags", 0)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter a regular expression pattern",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    if isinstance(default, str):
                        return re.compile(default, flags)
                    return default

                # Validate by attempting to compile
                pattern = re.compile(result, flags)
                # Pattern might be Any due to older Python type hints
                return cast(re.Pattern[str], pattern)

            except re.error as e:
                msg = f"Invalid regular expression: {e}"
                raise ValidationError(msg) from e
