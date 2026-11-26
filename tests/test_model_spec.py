import asyncio
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, ValidationError
import pytest

import promptantic
from promptantic import FieldSpec, ModelCreator, ModelGenerator, ModelSpec
from promptantic.form import ObjectNode, build_form, target_for


SPEC = ModelSpec(
    name="Book",
    description="A book on a shelf",
    fields=[
        FieldSpec(name="title", description="As printed"),
        FieldSpec(name="pages", type="integer", default="100"),
        FieldSpec(name="published", type="date", required=False),
        FieldSpec(name="tags", type="list", items="string", required=False),
        FieldSpec(
            name="author",
            type="object",
            fields=[FieldSpec(name="name"), FieldSpec(name="born", type="integer", required=False)],
        ),
    ],
)


def test_spec_becomes_a_working_model_class() -> None:
    book_class = SPEC.model_class()
    book = book_class.model_validate({
        "title": "Dune",
        "published": "1965-08-01",
        "tags": ["sf"],
        "author": {"name": "Herbert"},
    })
    data = book.model_dump()
    assert data["pages"] == 100  # noqa: PLR2004  (default parsed from its text)
    assert data["published"] in ("1965-08-01", date(1965, 8, 1))
    assert data["author"]["name"] == "Herbert"
    with pytest.raises(ValidationError):
        book_class.model_validate({"pages": 3})  # title and author are required
    assert SPEC.json_schema()["required"] == ["title", "author"]


def test_the_spec_itself_is_a_recursive_form() -> None:
    form = build_form(target_for(ModelSpec).schema)
    assert isinstance(form, ObjectNode)
    fields = next(p for p in form.properties if p.name == "fields").node
    field = fields.items
    assert isinstance(field, ObjectNode)
    nested = next(p for p in field.properties if p.name == "fields").node
    assert isinstance(nested.items, ObjectNode)  # fields of an object field: same form again


async def test_model_creator_fills_a_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fill(target: Any, **kwargs: Any) -> Any:
        if target is ModelSpec:
            assert kwargs["initial"] == {"name": "Book"}
            return SPEC
        return target.model_validate({"title": "x", "author": {"name": "y"}})

    monkeypatch.setattr("promptantic.creator.fill", fake_fill)
    book_class = await ModelCreator().acreate("Book")
    assert set(book_class.model_fields) == {"title", "pages", "published", "tags", "author"}
    book = await ModelCreator().acreate_instance("Book")
    assert book.model_dump()["title"] == "x"


class Settings(BaseModel):
    name: str
    secret_id: str = Field(
        default="generated", json_schema_extra={promptantic.SKIP_PROMPT_KEY: True}
    )


def test_skip_prompt_fields_are_not_asked() -> None:
    form = build_form(target_for(Settings).schema)
    assert isinstance(form, ObjectNode)
    assert [p.node.meta.read_only for p in form.properties] == [False, True]


async def test_model_generator_wraps_fill(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, Any]] = []

    async def fake_fill(target: Any, **kwargs: Any) -> Any:
        calls.append((target, kwargs.get("initial")))
        return Settings(name="n")

    monkeypatch.setattr("promptantic.generator.fill", fake_fill)
    assert await ModelGenerator(show_progress=False).apopulate(Settings) == Settings(name="n")
    await ModelGenerator().apopulate(Settings(name="old"))
    assert calls[1] == (Settings, {"name": "old", "secret_id": "generated"})


@pytest.mark.parametrize(
    ("kind", "default"),
    [
        ("integer", "abc"),
        ("number", "x1"),
        ("list", "[1,"),
        ("list", '{"a": 1}'),
        ("object", "[1]"),
        ("date", "yesterday"),
        ("datetime", "noon"),
    ],
)
def test_invalid_default_is_a_field_error(kind: str, default: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        FieldSpec.model_validate({"name": "n", "type": kind, "default": default})
    assert exc_info.value.errors()[0]["loc"] == ("default",)


def test_valid_defaults_still_accepted() -> None:
    for kind, default in [
        ("integer", "42"),
        ("number", "1.5"),
        ("boolean", "yes"),
        ("list", "[1, 2]"),
        ("object", '{"a": 1}'),
        ("date", "2026-11-26"),
        ("datetime", "2026-11-26T10:00:00"),
        ("string", "anything"),
    ]:
        FieldSpec.model_validate({"name": "n", "type": kind, "default": default})


def test_field_name_with_leading_underscore_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FieldSpec(name="_private")


def test_duplicate_field_names_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Duplicate field name"):
        ModelSpec(name="M", fields=[FieldSpec(name="a"), FieldSpec(name="a")])
    with pytest.raises(ValidationError, match="Duplicate field name"):
        FieldSpec(name="o", type="object", fields=[FieldSpec(name="x"), FieldSpec(name="x")])


async def test_invalid_default_is_asked_again_with_the_input_kept() -> None:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from promptantic.sequential import fill_sequential

    # name, description, field name, type 2 (integer), required, default "abc",
    # field description, items (keep), sub-fields? n, another field? n
    # -> "Please fix", asked again with everything as defaults: Enter keeps them,
    # only the default is corrected to 7
    first = "M\n\nn\n2\ny\nabc\n\n\nn\nn\n"
    second = "\n\n\n\n\n7\n\n\nn\nn\n"
    lines: list[str] = []
    with create_pipe_input() as pipe:
        pipe.send_text(first + second)
        session: PromptSession[str] = PromptSession(input=pipe, output=DummyOutput())
        spec = await asyncio.wait_for(
            fill_sequential(ModelSpec, session=session, echo=lines.append), timeout=10
        )
    assert "Please fix:" in lines
    assert any("default" in line for line in lines)
    model = spec.model_class()
    assert model.model_validate({}).model_dump() == {"n": 7}


async def test_model_creator_uses_all_base_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    class Mixin:
        def hello(self) -> str:
            return "hi"

    class Base(BaseModel):
        pass

    async def fake_fill(target: Any, **kwargs: Any) -> Any:
        return ModelSpec(name="M", fields=[FieldSpec(name="a", required=False)])

    monkeypatch.setattr("promptantic.creator.fill", fake_fill)
    model = await ModelCreator().acreate("M", (Base, Mixin))
    assert issubclass(model, Base)
    assert issubclass(model, Mixin)
