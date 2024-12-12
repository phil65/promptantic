# tests/test_handlers.py
from __future__ import annotations

import datetime
from decimal import Decimal
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from pydantic import BaseModel, Field
import pytest

from promptantic import ModelGenerator


@pytest.fixture
def generator():
    return ModelGenerator()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_class", "field_type", "test_input", "expected"),
    [
        ("StrHandler", str, "test string", "test string"),
        ("IntHandler", int, "42", 42),
        ("FloatHandler", float, "3.14", 3.14),
        ("BoolHandler", bool, "y", True),
        ("DecimalHandler", Decimal, "3.14", Decimal("3.14")),
        (
            "UUIDHandler",
            UUID,
            "123e4567-e89b-12d3-a456-426614174000",
            UUID("123e4567-e89b-12d3-a456-426614174000"),
        ),
        # Use os.path.sep to handle platform differences
        (
            "PathHandler",
            Path,
            "tmp/test".replace("/", os.path.sep),
            Path("tmp/test").resolve().relative_to(Path.cwd()),
        ),
    ],
)
async def test_handlers(
    generator: ModelGenerator,
    handler_class: str,
    field_type: type,
    test_input: str,
    expected: Any,
):
    """Test individual handlers with simulated input."""
    # Get the handler instance
    handler = generator.get_handler(field_type)

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        pipe_input.send_text(f"{test_input}\n")

        result = await handler.handle(
            field_name="test_field",
            field_type=field_type,
            description="Test field",
        )

        if isinstance(result, Path):
            result = result.resolve().relative_to(Path.cwd())
        assert result == expected


@pytest.mark.asyncio
async def test_model_with_skipped_fields():
    """Test model generation with skipped fields."""

    class TestModel(BaseModel):
        name: str
        age: int
        created_at: datetime.datetime = Field(
            default_factory=datetime.datetime.now, json_schema_extra={"skip_prompt": True}
        )

    generator = ModelGenerator()

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        # Simulate user input for name and age
        pipe_input.send_text("Test User\n")
        pipe_input.send_text("25\n")

        model = await generator.apopulate(TestModel)

        assert model.name == "Test User"
        assert model.age == 25  # noqa: PLR2004
        assert isinstance(model.created_at, datetime.datetime)


# Optional: Test complex types separately
@pytest.mark.asyncio
async def test_list_handler():
    """Test list handler with multiple inputs."""

    class ModelWithList(BaseModel):
        items: list[str]

    generator = ModelGenerator()

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        # Simulate entering two items and then empty line
        pipe_input.send_text("item1\n")
        pipe_input.send_text("item2\n")
        pipe_input.send_text("\n")  # Empty line to terminate

        # Pass test_mode flag
        model = await generator.apopulate(
            ModelWithList,
            _test_mode=True,
        )
        assert model.items == ["item1", "item2"]
