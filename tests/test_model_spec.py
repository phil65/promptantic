from __future__ import annotations

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
