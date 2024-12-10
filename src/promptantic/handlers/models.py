"""Handlers for Pydantic models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from promptantic.handlers.base import BaseHandler


if TYPE_CHECKING:
    from pydantic import BaseModel


class ModelHandler(BaseHandler):
    """Handler for nested Pydantic models."""

    async def handle(
        self,
        field_name: str,
        field_type: type[BaseModel],
        description: str | None = None,
        **options: Any,
    ) -> BaseModel:
        """Handle nested model input.

        Args:
            field_name: Name of the field
            field_type: The Pydantic model class
            description: Optional field description
            **options: Additional options

        Returns:
            A populated model instance
        """
        print(f"\nPopulating nested model: {field_name}")
        if description:
            print(f"Description: {description}")

        # Use the generator to populate the nested model
        return await self.generator.apopulate(field_type)
