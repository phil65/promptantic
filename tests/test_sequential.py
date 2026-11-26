import asyncio
from typing import Annotated, Any, Literal

from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from pydantic import BaseModel, ConfigDict, Field, SecretStr
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


class Credentials(BaseModel):
    user: str
    token: SecretStr


class Service(BaseModel):
    name: str
    creds: Credentials
    keys: list[SecretStr] = []


async def test_editing_an_instance_keeps_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    from promptantic import ModelGenerator

    instance = Service(
        name="api",
        creds=Credentials(user="ada", token=SecretStr("real-secret")),
        keys=[SecretStr("k1")],
    )
    seen: list[Any] = []

    async def sequential_fill(target: Any, **kwargs: Any) -> Any:
        seen.append(kwargs["initial"])
        # accept every default: name, user, token, keep k1, add a key? n
        result, lines = await run(target, "\n\n\n\nn\n", initial=kwargs["initial"])
        seen.append(lines)
        return result

    monkeypatch.setattr("promptantic.generator.fill", sequential_fill)
    result = await ModelGenerator().apopulate(instance)
    assert result.creds.token.get_secret_value() == "real-secret"
    assert [k.get_secret_value() for k in result.keys] == ["k1"]
    assert "real-secret" not in str(seen[1])  # never echoed


async def test_secret_default_is_shown_masked() -> None:
    lines: list[str] = []
    prompts: list[str] = []
    with create_pipe_input() as pipe:
        pipe.send_text("\n\n")
        session: PromptSession[str] = PromptSession(input=pipe, output=DummyOutput())
        original = session.prompt_async

        async def prompt_async(message: Any, **kwargs: Any) -> str:
            prompts.append(str(message))
            return await original(message, **kwargs)

        session.prompt_async = prompt_async  # ty: ignore[invalid-assignment]
        result = await asyncio.wait_for(
            fill_sequential(
                Credentials,
                session=session,
                echo=lines.append,
                initial={"user": "ada", "token": "real-secret"},
            ),
            timeout=10,
        )
    assert result.token.get_secret_value() == "real-secret"
    assert any("[********]" in p for p in prompts)
    assert not any("real-secret" in p for p in prompts)


class Loose(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str


async def test_initial_extra_keys_are_kept() -> None:
    result, _ = await run(Loose, "\n", initial={"name": "a", "color": "red"})
    assert result.model_dump() == {"name": "a", "color": "red"}


async def test_initial_extra_keys_dropped_when_not_allowed() -> None:
    result, _ = await run(Address, "\n\n", initial={"street": "s", "bogus": 1})
    assert result == Address(street="s")
