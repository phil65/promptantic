from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest

from promptantic import ModelCreator
from promptantic.creator import COMMON_TYPES


class _FakeDialog:
    def __init__(self, result: str | None) -> None:
        self.result = result

    async def run_async(self) -> str | None:
        return self.result


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("str", str),
        ("int", int),
        ("datetime", dt.datetime),
        ("date", dt.date),
        ("list[str]", list[str]),
        ("dict[str, Any]", dict[str, Any]),
        ("Path", Path),
    ],
)
async def test_prompt_field_type_resolves_common_types(
    monkeypatch: pytest.MonkeyPatch, choice: str, expected: Any
):
    """Every predefined type choice resolves to the actual type."""
    assert choice in COMMON_TYPES
    monkeypatch.setattr(
        "promptantic.creator.radiolist_dialog", lambda **kwargs: _FakeDialog(choice)
    )
    assert await ModelCreator()._prompt_field_type() == expected


async def test_prompt_field_type_cancel_raises_eof(monkeypatch: pytest.MonkeyPatch):
    """Cancelling the type dialog ends field definition like Ctrl-D."""
    monkeypatch.setattr("promptantic.creator.radiolist_dialog", lambda **kwargs: _FakeDialog(None))
    with pytest.raises(EOFError):
        await ModelCreator()._prompt_field_type()
