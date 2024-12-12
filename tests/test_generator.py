from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Annotated

from pydantic import BaseModel, Field
import pytest

from promptantic import SKIP_PROMPT_KEY, ModelGenerator


def test_generator_initialization():
    """Test basic generator initialization."""
    generator = ModelGenerator()
    assert generator is not None
    assert generator.style is not None
    assert generator.show_progress is True
    assert generator.allow_back is True
    assert generator.retry_on_validation_error is True


def test_generator_custom_config():
    """Test generator with custom configuration."""
    generator = ModelGenerator(
        show_progress=False,
        allow_back=False,
        retry_on_validation_error=False,
    )
    assert generator.show_progress is False
    assert generator.allow_back is False
    assert generator.retry_on_validation_error is False


def test_registered_handlers():
    """Test that basic handlers are registered."""
    generator = ModelGenerator()

    # Test a few basic types
    assert generator.get_handler(str) is not None
    assert generator.get_handler(int) is not None
    assert generator.get_handler(bool) is not None


def test_skip_prompt_detection():
    """Test detection of skippable fields."""

    class ModelWithSkipped(BaseModel):
        # Field metadata method
        field1: str = Field(json_schema_extra={SKIP_PROMPT_KEY: True})
        # Annotated method
        field2: Annotated[datetime, {SKIP_PROMPT_KEY: True}]
        # Regular field
        field3: str

    model_cls = ModelWithSkipped
    model_cls.model_rebuild()  # This resolves ForwardRefs

    from promptantic.type_utils import is_skip_prompt

    assert is_skip_prompt(model_cls.model_fields["field1"]) is True
    assert is_skip_prompt(model_cls.model_fields["field2"]) is True
    assert is_skip_prompt(model_cls.model_fields["field3"]) is False


@pytest.mark.parametrize(
    ("model_class", "invalid"),
    [
        (str, True),
        (dict, True),
        (BaseModel, False),
        (type("DynamicModel", (BaseModel,), {}), False),
    ],
)
def test_model_type_validation(model_class: type, invalid: bool):
    """Test validation of model types."""
    generator = ModelGenerator()

    if invalid:
        with pytest.raises(ValueError):  # noqa: PT011
            generator.populate(model_class)  # type: ignore
    else:
        # Test that we get a valid handler for model types
        handler = generator.get_handler(model_class)
        from promptantic.handlers.models import ModelHandler

        assert isinstance(handler, ModelHandler)
