"""Handlers for Pydantic models."""

from __future__ import annotations

from typing import Any

from prompt_toolkit.shortcuts import PromptSession
from pydantic import BaseModel, ValidationError
from pydantic.fields import PydanticUndefined

from promptantic.handlers.base import BaseHandler


class ModelHandler(BaseHandler):
    """Handler for nested Pydantic models."""

    def format_default(self, default: Any) -> str | None:
        """Format model default value for display."""
        if default is None or default is PydanticUndefined:
            return None
        if isinstance(default, dict):
            return "default: <from dict>"
        if isinstance(default, BaseModel):
            return "default: <from model>"
        return str(default)

    async def handle(
        self,
        field_name: str,
        field_type: type[BaseModel],
        description: str | None = None,
        default: BaseModel | dict[str, Any] | None = None,
        **options: Any,
    ) -> BaseModel:
        """Handle nested model input.

        Args:
            field_name: Name of the field
            field_type: The Pydantic model class
            description: Optional field description
            default: Default value (can be dict or model instance)
            **options: Additional options

        Returns:
            A populated model instance

        Raises:
            ValidationError: If model validation fails
        """
        print(f"\nPopulating nested model: {field_name}")
        if description:
            print(f"Description: {description}")
        if default is PydanticUndefined:
            # Create a new instance with factory default
            field_info = options.get("field_info")
            if field_info and field_info.default_factory:
                default = field_info.default_factory()
        if default is not None:
            print("\nDefault value available. Options:")
            print("1. Use default values")
            print("2. Enter new values")
            print("3. Modify default values")

            session: PromptSession[Any] = PromptSession()
            while True:
                choice = await session.prompt_async("Choose option (1-3): ")
                if choice == "1":
                    # Use default as-is
                    if isinstance(default, BaseModel):
                        return default
                    return field_type.model_validate(default)
                if choice == "2":
                    # Enter completely new values
                    break
                if choice == "3":
                    # Modify default values
                    if isinstance(default, dict):
                        model = field_type.model_validate(default)
                    else:
                        model = default
                    # Create a new instance with defaults to modify
                    return await self.generator.apopulate(model)
                print("Invalid choice, please try again")

        # Regular flow for new values
        try:
            return await self.generator.apopulate(field_type)
        except ValidationError as e:
            msg = f"Model validation failed: {e!s}"
            raise ValidationError(msg) from e

    # async def handle(
    #     self,
    #     field_name: str,
    #     field_type: type[BaseModel],
    #     description: str | None = None,
    #     **options: Any,
    # ) -> BaseModel:
    #     """Handle nested model input."""
    #     print(f"\nPopulating nested model: {field_name}")
    #     if description:
    #         print(f"Description: {description}")

    #     field_info = options.get("field_info", {})
    #     default = field_info.get("default", None)

    #     # Use the generator to populate the nested model
    #     if default is not None:
    #         # Pre-populate with default values
    #         return field_type.model_validate(default)
    #     return await self.generator.apopulate(field_type)
