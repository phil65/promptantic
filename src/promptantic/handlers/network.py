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
        **options: Any,
    ) -> ipaddress.IPv4Address:
        """Handle IPv4 address input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter IPv4 address (e.g. 192.168.1.1)",
                    ),
                )
                return ipaddress.IPv4Address(result)
            except ValueError as e:
                msg = f"Invalid IPv4 address: {e!s}"
                raise ValidationError(msg) from e


class IPv6Handler(BaseHandler):
    """Handler for IPv6 address input."""

    async def handle(
        self,
        field_name: str,
        field_type: type[ipaddress.IPv6Address],
        description: str | None = None,
        **options: Any,
    ) -> ipaddress.IPv6Address:
        """Handle IPv6 address input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter IPv6 address",
                    ),
                )
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
        **options: Any,
    ) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        """Handle IP network input."""
        session = PromptSession()
        while True:
            try:
                result = await session.prompt_async(
                    create_field_prompt(
                        field_name,
                        description or "Enter IP network (e.g. 192.168.1.0/24)",
                    ),
                )
                return ipaddress.ip_network(result)
            except ValueError as e:
                msg = f"Invalid IP network: {e!s}"
                raise ValidationError(msg) from e
