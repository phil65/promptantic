"""Model creation functionality."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Annotated, Any, cast, get_args, get_origin
import uuid

from prompt_toolkit.shortcuts import PromptSession, radiolist_dialog
from pydantic import BaseModel, ConfigDict, Field

from promptantic.completers import ImportStringCompleter


if TYPE_CHECKING:
    from promptantic.generator import ModelGenerator


# Update type definitions to be more precise
FieldType = type[Any] | str | Annotated[Any, Any]
FieldInfo = Any | None  # TODO
FieldDefinition = tuple[FieldType, FieldInfo]

# Pre-defined common types for easy selection
COMMON_TYPES: dict[str, type[Any] | str] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "datetime": "datetime.datetime",
    "date": "datetime.date",
    "list[str]": "list[str]",
    "list[int]": "list[int]",
    "dict[str, Any]": "dict[str, Any]",
    "Path": "pathlib.Path",
    "UUID": "uuid.UUID",
    "Email": "str with email validation",
    "URL": "str with url validation",
}


class ModelCreator:
    """Helper class for creating Pydantic models interactively."""

    async def acreate(
        self,
        model_name: str | None = None,
        base_classes: tuple[type[BaseModel], ...] = (BaseModel,),
    ) -> type[BaseModel]:
        """Create a new Pydantic model interactively."""
        if model_name is None:
            model_name = await self._prompt_model_name()

        fields: dict[str, FieldDefinition] = {}
        print("\nDefining fields for model. Press Ctrl-D when done.")

        while True:
            try:
                field_name = await self._prompt_field_name(fields)
                field_type = await self._prompt_field_type()
                field_info = await self._prompt_field_info()
                fields[field_name] = (field_type, field_info)
            except EOFError:
                break

        # Create model namespace
        namespace: dict[str, Any] = {
            "__annotations__": {name: type_ for name, (type_, _) in fields.items()}
        }

        # Add field definitions
        for name, (_, field_info) in fields.items():
            if field_info:
                namespace[name] = field_info

        # Add model config if needed
        if self._check_needs_arbitrary_types(fields):
            namespace["model_config"] = ConfigDict(arbitrary_types_allowed=True)

        # Generate a unique module name to avoid conflicts
        namespace["__module__"] = f"promptantic_generated_{uuid.uuid4().hex[:8]}"

        return type(model_name, base_classes, namespace)

    async def acreate_instance(
        self,
        model_name: str | None = None,
        base_classes: tuple[type[BaseModel], ...] = (BaseModel,),
        populator: ModelGenerator | None = None,
    ) -> BaseModel:
        """Create and populate a new model instance interactively.

        Args:
            model_name: Optional name for the model
            base_classes: Base classes for the model
            populator: ModelPopulator instance for populating the model.
                If not provided, a new one will be created.
        """
        model_cls = await self.acreate(model_name, base_classes)

        if populator is None:
            from promptantic.generator import ModelGenerator

            populator = ModelGenerator()

        return await populator.apopulate(model_cls)

    def _check_needs_arbitrary_types(self, fields: dict[str, FieldDefinition]) -> bool:
        """Check if the model needs arbitrary types allowed."""
        for type_, _ in fields.values():
            # Handle Annotated types
            if get_origin(type_) is Annotated:
                type_ = get_args(type_)[0]

            # Check if type is a custom class that's not a built-in or standard type
            if isinstance(type_, type):
                if not any(
                    type_.__module__.startswith(prefix)
                    for prefix in ("builtins", "datetime", "uuid", "pathlib")
                ):
                    return True
            # Check string type references
            elif isinstance(type_, str) and not any(
                type_.startswith(prefix)
                for prefix in ("str", "int", "float", "bool", "list", "dict")
            ):
                return True
        return False

    async def _prompt_model_name(self) -> str:
        """Prompt for model name."""
        while True:
            name: str = await PromptSession().prompt_async("Model name: ")
            if name.isidentifier():
                return name
            print("Invalid Python identifier, try again")

    async def _prompt_field_name(self, existing: dict[str, Any]) -> str:
        """Prompt for field name."""
        while True:
            name: str = await PromptSession().prompt_async("Field name: ")
            if not name.isidentifier():
                print("Invalid Python identifier")
                continue
            if name in existing:
                print("Field already exists")
                continue
            return name

    async def _prompt_field_type(self) -> FieldType:
        """Prompt for field type."""
        choices = [(str(typ), desc) for desc, typ in COMMON_TYPES.items()]
        choices.append(("custom", "Custom type (import path)"))

        selected = await radiolist_dialog(
            title="Select field type",
            text="Choose a type:",
            values=choices,
        ).run_async()

        if selected == "custom":
            # Use ImportStringCompleter for good UX
            completer = ImportStringCompleter()
            while True:
                try:
                    path: str = await PromptSession(completer=completer).prompt_async(
                        "Enter import path: "
                    )
                    # Try to import and get the type
                    module_path, _, attr = path.partition(":")
                    module = importlib.import_module(module_path)
                    if attr:
                        return cast(type[Any], getattr(module, attr))
                    return cast(type[Any], module)
                except Exception as e:  # noqa: BLE001
                    print(f"Invalid type: {e}")
        elif selected == "str with email validation":
            return Annotated[str, Field(pattern=r"[^@]+@[^@]+\.[^@]+")]
        elif selected == "str with url validation":
            return Annotated[
                str,
                Field(
                    pattern=(
                        r"^https?://"
                        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)"
                        r"+[A-Z]{2,6}\.?|"
                        r"localhost|"
                        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
                        r"(?::\d+)?"
                        r"(?:/?|[/?]\S+)$"
                    )
                ),
            ]

        return cast(type[Any], eval(selected))

    async def _prompt_field_info(self) -> FieldInfo | None:  # noqa: PLR0911
        """Prompt for field metadata."""
        choices = [
            ("none", "No additional info"),
            ("required", "Required field"),
            ("optional", "Optional field"),
            ("default", "With default value"),
            ("description", "Add description"),
            ("validation", "Add validation"),
        ]

        selected = await radiolist_dialog(
            title="Field information",
            text="Add field metadata:",
            values=choices,
        ).run_async()

        match selected:
            case "none":
                return None
            case "required":
                return Field()
            case "optional":
                return Field(default=None)
            case "default":
                value: Any = await PromptSession().prompt_async("Default value: ")
                return Field(default=value)
            case "description":
                desc: Any = await PromptSession().prompt_async("Description: ")
                return Field(description=desc)
            case "validation":
                return await self._prompt_validation()
            case _:
                return None

    async def _prompt_validation(self) -> FieldInfo:
        """Prompt for field validation rules."""
        choices = [
            ("min_length", "Minimum length"),
            ("max_length", "Maximum length"),
            ("pattern", "Regex pattern"),
            ("gt", "Greater than"),
            ("lt", "Less than"),
            ("multiple_of", "Multiple of"),
        ]

        selected = await radiolist_dialog(
            title="Validation",
            text="Select validation rule:",
            values=choices,
        ).run_async()

        if not selected:
            return Field()

        value: Any = await PromptSession().prompt_async(f"Value for {selected}: ")
        return Field(**{selected: value})
