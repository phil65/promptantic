"""Retry behaviour when a handler rejects the user's input."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
import pytest

from promptantic import ModelGenerator
from promptantic.exceptions import ValidationError as PromptanticValidationError


class Model(BaseModel):
    name: str


class _FlakyHandler:
    """Rejects the first answer with promptantic's own ValidationError, then accepts."""

    def __init__(self) -> None:
        self.calls = 0

    async def handle(self, **_kwargs: Any) -> str:
        self.calls += 1
        if self.calls == 1:
            msg = "bad input"
            raise PromptanticValidationError(msg)
        return "ok"


async def test_retries_on_promptantic_validation_error(monkeypatch: pytest.MonkeyPatch):
    generator = ModelGenerator(retry_on_validation_error=True)
    handler = _FlakyHandler()
    monkeypatch.setattr(generator, "get_handler", lambda *_a, **_kw: handler)
    result = await generator.apopulate(Model)
    assert result.name == "ok"
    assert handler.calls == 2  # noqa: PLR2004  (one rejected answer, one accepted)


async def test_no_retry_raises_promptantic_validation_error(monkeypatch: pytest.MonkeyPatch):
    generator = ModelGenerator(retry_on_validation_error=False)
    monkeypatch.setattr(generator, "get_handler", lambda *_a, **_kw: _FlakyHandler())
    with pytest.raises(PromptanticValidationError):
        await generator.apopulate(Model)
