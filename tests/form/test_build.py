from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr
import pytest

from promptantic.form import (
    UNSET,
    AnyNode,
    ArrayNode,
    BooleanNode,
    ChoiceNode,
    NullNode,
    NumberNode,
    ObjectNode,
    SchemaError,
    StringNode,
    TupleNode,
    UnionNode,
    build_form,
    target_for,
)


def form_of(model: type) -> ObjectNode:
    node = build_form(target_for(model).schema)
    assert isinstance(node, ObjectNode)
    return node


def prop(node: ObjectNode, name: str):
    return next(p for p in node.properties if p.name == name)


class Color(Enum):
    RED = "red"
    GREEN = "green"


class Address(BaseModel):
    street: str
    city: str = "Berlin"


class Cat(BaseModel):
    kind: Literal["cat"] = "cat"
    lives: int = 9


class Dog(BaseModel):
    kind: Literal["dog"] = "dog"
    good: bool = True


class Person(BaseModel):
    """A person."""

    name: Annotated[str, Field(min_length=1, max_length=40, description="Full name")]
    age: Annotated[int, Field(ge=0, lt=150)]
    email: str | None = None
    born: date | None = None
    color: Color = Color.RED
    mood: Literal["happy", "sad"] = "happy"
    tags: list[str] = []
    picks: set[Color] = set()
    address: Address
    previous: list[Address] = []
    scores: dict[str, int] = {}
    point: tuple[int, int] = (0, 0)
    pet: Annotated[Cat | Dog, Field(discriminator="kind")]
    password: SecretStr = SecretStr("x")


def test_pydantic_model_fields() -> None:
    form = form_of(Person)
    assert form.meta.title == "Person"
    assert form.meta.description == "A person."

    name = prop(form, "name")
    assert name.required
    assert isinstance(name.node, StringNode)
    assert (name.node.min_length, name.node.max_length) == (1, 40)
    assert name.node.meta.description == "Full name"

    age = prop(form, "age").node
    assert isinstance(age, NumberNode)
    assert age.integer
    assert (age.minimum, age.exclusive_maximum) == (0, 150)

    email = prop(form, "email")
    assert not email.required
    assert isinstance(email.node, StringNode)
    assert email.node.nullable
    assert email.node.meta.default is None

    born = prop(form, "born").node
    assert isinstance(born, StringNode)
    assert born.format == "date"
    assert born.nullable


def test_choices_from_enums_and_literals() -> None:
    form = form_of(Person)
    color = prop(form, "color").node
    assert isinstance(color, ChoiceNode)
    assert [c.value for c in color.choices] == ["red", "green"]
    assert color.meta.default == "red"
    mood = prop(form, "mood").node
    assert isinstance(mood, ChoiceNode)
    assert [c.label for c in mood.choices] == ["happy", "sad"]


def test_collections() -> None:
    form = form_of(Person)
    tags = prop(form, "tags").node
    assert isinstance(tags, ArrayNode)
    assert isinstance(tags.items, StringNode)
    assert not tags.multi_choice

    picks = prop(form, "picks").node
    assert isinstance(picks, ArrayNode)
    assert picks.unique
    assert picks.multi_choice

    scores = prop(form, "scores").node
    assert isinstance(scores, ObjectNode)
    assert scores.is_map
    assert isinstance(scores.additional, NumberNode)

    point = prop(form, "point").node
    assert isinstance(point, TupleNode)
    assert [type(p) for p in point.positions] == [NumberNode, NumberNode]


def test_nested_models_resolve_refs() -> None:
    form = form_of(Person)
    address = prop(form, "address").node
    assert isinstance(address, ObjectNode)
    assert [p.name for p in address.properties] == ["street", "city"]
    assert prop(address, "city").node.meta.default == "Berlin"
    previous = prop(form, "previous").node
    assert isinstance(previous, ArrayNode)
    assert isinstance(previous.items, ObjectNode)


def test_discriminated_union() -> None:
    pet = prop(form_of(Person), "pet").node
    assert isinstance(pet, UnionNode)
    assert pet.discriminator == "kind"
    assert [v.label for v in pet.variants] == ["cat", "dog"]
    cat = pet.variants[0].node
    assert isinstance(cat, ObjectNode)
    assert [p.name for p in cat.properties] == ["kind", "lives"]


def test_secret() -> None:
    password = prop(form_of(Person), "password").node
    assert isinstance(password, StringNode)
    assert password.secret


class Tree(BaseModel):
    value: int
    children: list[Tree] = []


def test_recursive_model_builds_lazily() -> None:
    form = form_of(Tree)
    children = prop(form, "children").node
    assert isinstance(children, ArrayNode)
    child = children.items
    assert isinstance(child, ObjectNode)
    grandchildren = prop(child, "children").node
    assert isinstance(grandchildren, ArrayNode)
    assert isinstance(grandchildren.items, ObjectNode)


def test_json_schema_2020_12_features() -> None:
    schema = {
        "$id": "https://example.com/thing.json",
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "size": {"type": ["integer", "string"]},
            "maybe": {"type": ["boolean", "null"]},
            "pair": {"type": "array", "prefixItems": [{"type": "string"}, {"$ref": "#count"}]},
            "level": {"oneOf": [{"const": 1, "title": "Low"}, {"const": 2, "title": "High"}]},
            "nothing": {"type": "null"},
            "free": {},
            "labelled": {"enum": ["a", "b"], "x-enumNames": ["Option A", "Option B"]},
            "legacy": {"type": "number", "minimum": 0, "exclusiveMinimum": True},
            "extras": {"x-completions": ["one", "two"], "type": "string"},
        },
        "$defs": {"count": {"$anchor": "count", "type": "integer", "minimum": 0}},
    }
    form = build_form(schema)
    assert isinstance(form, ObjectNode)
    assert prop(form, "id").required
    size = prop(form, "size").node
    assert isinstance(size, UnionNode)
    assert [v.label for v in size.variants] == ["integer", "string"]
    maybe = prop(form, "maybe").node
    assert isinstance(maybe, BooleanNode)
    assert maybe.nullable
    pair = prop(form, "pair").node
    assert isinstance(pair, TupleNode)
    count = pair.positions[1]
    assert isinstance(count, NumberNode)
    assert count.integer
    level = prop(form, "level").node
    assert isinstance(level, ChoiceNode)
    assert [(c.value, c.label) for c in level.choices] == [(1, "Low"), (2, "High")]
    assert isinstance(prop(form, "nothing").node, NullNode)
    assert isinstance(prop(form, "free").node, AnyNode)
    labelled = prop(form, "labelled").node
    assert isinstance(labelled, ChoiceNode)
    assert [c.label for c in labelled.choices] == ["Option A", "Option B"]
    legacy = prop(form, "legacy").node
    assert isinstance(legacy, NumberNode)
    assert legacy.exclusive_minimum == 0
    assert prop(form, "extras").node.meta.extensions == {"completions": ["one", "two"]}


def test_all_of_and_openapi_nullable() -> None:
    schema = {
        "allOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
            {"properties": {"b": {"type": "integer", "nullable": True}}},
        ]
    }
    form = build_form(schema)
    assert isinstance(form, ObjectNode)
    assert [(p.name, p.required) for p in form.properties] == [("a", True), ("b", False)]
    assert form.properties[1].node.nullable


def test_mcp_elicitation_schema() -> None:
    """MCP elicitation: a flat object of primitives, the restricted subset."""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "title": "Your name", "minLength": 1},
            "count": {"type": "integer", "minimum": 1, "default": 3},
            "agree": {"type": "boolean"},
            "size": {"type": "string", "enum": ["s", "m"], "enumNames": ["Small", "Medium"]},
            "tags": {"type": "array", "items": {"type": "string", "enum": ["x", "y"]}},
        },
        "required": ["name"],
    }
    form = build_form(schema)
    assert isinstance(form, ObjectNode)
    assert [p.label for p in form.properties] == ["Your name", "count", "agree", "size", "tags"]
    assert [prop(form, "count").node.meta.default] == [3]
    assert prop(form, "name").node.meta.default is UNSET
    tags = prop(form, "tags").node
    assert isinstance(tags, ArrayNode)
    assert tags.multi_choice


def test_unresolvable_ref() -> None:
    form = build_form({"properties": {"x": {"$ref": "#/$defs/missing"}}})
    assert isinstance(form, ObjectNode)
    with pytest.raises(SchemaError, match="missing"):
        _ = form.properties
