"""Handlers for network-related types like IP addresses."""

from __future__ import annotations

import ipaddress
from typing import Any

from prompt_toolkit.shortcuts import PromptSession

from promptantic.exceptions import ValidationError
from promptantic.handlers.base import BaseHandler
from promptantic.ui.formatting import create_field_prompt


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
