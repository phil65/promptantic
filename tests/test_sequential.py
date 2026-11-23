from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from pydantic import BaseModel, Field
import pytest

from promptantic import fill
from promptantic.sequential import fill_sequential


class Address(BaseModel):
    street: str
    city: str = "Berlin"


class Order(BaseModel):
    customer: Annotated[str, Field(min_length=1)]
    quantity: Annotated[int, Field(ge=1)] = 1
    express: bool = False
    size: Literal["s", "m", "l"] = "m"
    notes: list[str] = []
    ship_to: Address | None = None


async def run(target, keys: str, **kwargs):
    lines: list[str] = []
    with create_pipe_input() as pipe:
        pipe.send_text(keys)
        session: PromptSession[str] = PromptSession(input=pipe, output=DummyOutput())
        result = await asyncio.wait_for(
            fill_sequential(target, session=session, echo=lines.append, **kwargs), timeout=10
        )
    return result, lines


async def test_fields_in_turn() -> None:
    # customer, quantity, express, size (3 = l), add a note? y, note, another? n, fill address? y,
    # street, city (keep default)
    keys = "Ada\n3\ny\n3\ny\nfragile\nn\ny\nMain St 1\n\n"
    result, lines = await run(Order, keys)
    assert result == Order(
        customer="Ada",
        quantity=3,
        express=True,
        size="l",
        notes=["fragile"],
        ship_to=Address(street="Main St 1"),
    )
    assert "  3) l" in lines


async def test_defaults_and_initial_values() -> None:
    # every prompt accepts its default; the optional address is skipped
    result, _ = await run(Order, "\n\n\n\nn\nn\n", initial={"customer": "Eve"})
    assert result == Order(customer="Eve")


async def test_invalid_input_is_asked_again() -> None:
    # quantity "0" is rejected while typing (minimum 1), then "2" is accepted
    result, _ = await run(Order, "Kim\n0\n2\n\n\nn\nn\n")
    assert result.quantity == 2  # noqa: PLR2004


async def test_json_schema_gives_a_dict() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "tags": {"type": "array", "items": {"enum": ["x", "y", "z"]}, "uniqueItems": True},
            "size": {"type": ["integer", "string"]},
        },
        "required": ["name"],
    }
    result, _ = await run(schema, "n\n1,3\n2\nbig\n")
    assert result == {"name": "n", "tags": ["x", "z"], "size": "big"}


async def test_fill_picks_sequential_without_a_terminal(monkeypatch) -> None:
    calls: list[str] = []

    async def fake(target, **kwargs):
        calls.append("sequential")
        return {"ok": True}

    monkeypatch.setattr("promptantic.sequential.fill_sequential", fake)
    assert await fill({"type": "object"}) == {"ok": True}  # pytest's stdin isn't a TTY
    assert calls == ["sequential"]


async def test_end_of_input_cancels() -> None:
    from promptantic import FormCancelledError

    with create_pipe_input() as pipe:
        pipe.send_text("Ada\n")
        pipe.close()
        session: PromptSession[str] = PromptSession(input=pipe, output=DummyOutput())
        with pytest.raises(FormCancelledError):
            await asyncio.wait_for(fill_sequential(Order, session=session, echo=print), 10)
