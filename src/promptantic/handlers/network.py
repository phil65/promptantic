"""Handlers for network-related types like IP addresses and URLs."""

from __future__ import annotations

import ipaddress
from typing import Any, TypeVar

from prompt_toolkit.shortcuts import PromptSession
from pydantic import TypeAdapter
from pydantic.networks import (
    AnyHttpUrl,
    AnyUrl,
    AnyWebsocketUrl,
    FileUrl,
    FtpUrl,
    HttpUrl,
    WebsocketUrl,
    # DSN types
    AmqpDsn,
    CockroachDsn,
    KafkaDsn,
    MariaDBDsn,
    MongoDsn,
    MySQLDsn,
    NatsDsn,
    PostgresDsn,
    RedisDsn,
    ClickHouseDsn,
    SnowflakeDsn,
)

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


T = TypeVar("T")


class IPv4Handler(BaseHandler):
    """Handler for IPv4 address input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[ipaddress.IPv4Address],
        description: str | None = None,
        default: ipaddress.IPv4Address | None = None,
        **options: Any,
    ) -> ipaddress.IPv4Address:
        """Handle IPv4 address input."""
        session: PromptSession[Any] = PromptSession()
        default_str = str(default) if default is not None else None

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter IPv4 address (e.g. 192.168.1.1)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return ipaddress.IPv4Address(result)
            except ValueError as e:
                msg = f"Invalid IPv4 address: {e!s}"
                raise ValidationError(msg) from e


class IPv6Handler(BaseHandler):
    """Handler for IPv6 address input."""

    def format_default(self, default: Any) -> str | None:
        """Format IPv6 address default value."""
        if default is None:
            return None
        # Convert string to IPv6Address if needed
        if isinstance(default, str):
            default = ipaddress.IPv6Address(default)
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[ipaddress.IPv6Address],
        description: str | None = None,
        default: ipaddress.IPv6Address | str | None = None,
        **options: Any,
    ) -> ipaddress.IPv6Address:
        """Handle IPv6 address input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter IPv6 address (e.g. 2001:db8::1)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    if isinstance(default, str):
                        return ipaddress.IPv6Address(default)
                    return default

                return ipaddress.IPv6Address(result)
            except ValueError as e:
                msg = f"Invalid IPv6 address: {e!s}"
                raise ValidationError(msg) from e


class NetworkHandler(BaseHandler):
    """Handler for IP network input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[ipaddress.IPv4Network | ipaddress.IPv6Network],
        description: str | None = None,
        default: ipaddress.IPv4Network | ipaddress.IPv6Network | None = None,
        **options: Any,
    ) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        """Handle IP network input."""
        session: PromptSession[Any] = PromptSession()
        default_str = str(default) if default is not None else None

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter IP network (e.g. 192.168.1.0/24)",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    return default

                return ipaddress.ip_network(result)
            except ValueError as e:
                msg = f"Invalid IP network: {e!s}"
                raise ValidationError(msg) from e


# URL type configurations with examples
URL_TYPE_CONFIG: dict[type, tuple[str, str]] = {
    AnyUrl: ("URL", "https://example.com or file:///path/to/file"),
    AnyHttpUrl: ("HTTP/HTTPS URL", "https://example.com"),
    HttpUrl: ("HTTP/HTTPS URL", "https://example.com"),
    AnyWebsocketUrl: ("WebSocket URL", "ws://example.com or wss://example.com"),
    WebsocketUrl: ("WebSocket URL", "wss://example.com"),
    FileUrl: ("File URL", "file:///path/to/file"),
    FtpUrl: ("FTP URL", "ftp://ftp.example.com/path"),
}

# DSN type configurations with examples
DSN_TYPE_CONFIG: dict[type, tuple[str, str]] = {
    PostgresDsn: ("PostgreSQL DSN", "postgresql://user:pass@localhost:5432/db"),
    MySQLDsn: ("MySQL DSN", "mysql://user:pass@localhost:3306/db"),
    MariaDBDsn: ("MariaDB DSN", "mariadb://user:pass@localhost:3306/db"),
    MongoDsn: ("MongoDB DSN", "mongodb://user:pass@localhost:27017/db"),
    RedisDsn: ("Redis DSN", "redis://localhost:6379/0"),
    AmqpDsn: ("AMQP DSN", "amqp://user:pass@localhost:5672/"),
    KafkaDsn: ("Kafka DSN", "kafka://localhost:9092"),
    NatsDsn: ("NATS DSN", "nats://localhost:4222"),
    CockroachDsn: ("CockroachDB DSN", "cockroachdb://user:pass@localhost:26257/db"),
    ClickHouseDsn: ("ClickHouse DSN", "clickhouse://user:pass@localhost:8123/db"),
    SnowflakeDsn: ("Snowflake DSN", "snowflake://user:pass@account/db"),
}


class UrlHandler(BaseHandler[T]):
    """Generic handler for pydantic URL types."""

    def __init__(self, generator: Any, url_type: type[T]) -> None:
        super().__init__(generator)
        self.url_type = url_type
        self._adapter = TypeAdapter(url_type)
        config = URL_TYPE_CONFIG.get(url_type, ("URL", "https://example.com"))
        self.type_name, self.example = config

    def format_default(self, default: Any) -> str | None:
        """Format URL default value."""
        if default is None:
            return None
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[T],
        description: str | None = None,
        default: T | str | None = None,
        **options: Any,
    ) -> T:
        """Handle URL input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or f"Enter {self.type_name} (e.g. {self.example})",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    if isinstance(default, str):
                        return self._adapter.validate_python(default)
                    return default

                return self._adapter.validate_python(result)
            except Exception as e:
                msg = f"Invalid {self.type_name}: {e!s}"
                raise ValidationError(msg) from e


class DsnHandler(BaseHandler[T]):
    """Generic handler for pydantic DSN (Data Source Name) types."""

    def __init__(self, generator: Any, dsn_type: type[T]) -> None:
        super().__init__(generator)
        self.dsn_type = dsn_type
        self._adapter = TypeAdapter(dsn_type)
        config = DSN_TYPE_CONFIG.get(dsn_type, ("DSN", "scheme://user:pass@host:port/db"))
        self.type_name, self.example = config

    def format_default(self, default: Any) -> str | None:
        """Format DSN default value."""
        if default is None:
            return None
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[T],
        description: str | None = None,
        default: T | str | None = None,
        **options: Any,
    ) -> T:
        """Handle DSN input."""
        session: PromptSession[Any] = PromptSession()
        default_str = self.format_default(default)

        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or f"Enter {self.type_name} (e.g. {self.example})",
                        default=default_str,
                    ),
                    default=default_str if default_str is not None else "",
                )

                # Handle empty input with default
                if not result and default is not None:
                    if isinstance(default, str):
                        return self._adapter.validate_python(default)
                    return default

                return self._adapter.validate_python(result)
            except Exception as e:
                msg = f"Invalid {self.type_name}: {e!s}"
                raise ValidationError(msg) from e


# Export all URL types for easy registration
URL_TYPES = list(URL_TYPE_CONFIG.keys())
DSN_TYPES = list(DSN_TYPE_CONFIG.keys())
