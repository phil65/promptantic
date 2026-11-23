from __future__ import annotations

from pydantic import BaseModel, Field
import pytest

from promptantic.form import (
    UNSET,
    AnyNode,
    ArrayNode,
    FieldError,
    FormValidationError,
    Meta,
    NumberNode,
    ObjectNode,
    StringNode,
    build_form,
    field_errors,
    parse_text,
    target_for,
)


def test_parse_text() -> None:
    integer = NumberNode(meta=Meta(), integer=True)
    number = NumberNode(meta=Meta())
    parsed = [parse_text(integer, " 1_000 "), parse_text(number, "2.5"), parse_text(number, "3")]
    assert parsed == [1000, 2.5, 3]
    assert parse_text(StringNode(meta=Meta()), "") is UNSET
    assert parse_text(AnyNode(meta=Meta()), '{"a": [1]}') == {"a": [1]}
    with pytest.raises(FieldError, match="whole number"):
        parse_text(integer, "1.5")
    with pytest.raises(FieldError, match="JSON"):
        parse_text(AnyNode(meta=Meta()), "{nope")


@pytest.mark.parametrize(
    ("node", "value", "expected"),
    [
        (StringNode(meta=Meta(), min_length=2), "a", ["At least 2 character(s)"]),
        (StringNode(meta=Meta(), pattern=r"^\d+$"), "12a", [r"Must match ^\d+$"]),
        (StringNode(meta=Meta(), format="email"), "nope", ["Not a valid email"]),
        (StringNode(meta=Meta(), format="email"), "a@b.de", []),
        (NumberNode(meta=Meta(), minimum=0, maximum=10), 11, ["At most 10"]),
        (NumberNode(meta=Meta(), exclusive_minimum=0), 0, ["More than 0"]),
        (NumberNode(meta=Meta(), multiple_of=0.1), 0.3, []),
        (NumberNode(meta=Meta(), integer=True), 1.5, ["Must be a whole number"]),
        (StringNode(meta=Meta()), None, ["A value is required"]),
        (StringNode(meta=Meta(), nullable=True), None, []),
    ],
)
def test_field_errors(node, value, expected: list[str]) -> None:
    assert field_errors(node, value) == expected


def test_collection_field_errors() -> None:
    schema = {"type": "array", "items": {"type": "integer"}, "minItems": 1, "uniqueItems": True}
    node = build_form(schema)
    assert isinstance(node, ArrayNode)
    assert field_errors(node, []) == ["At least 1 item(s)"]
    assert field_errors(node, [1, 1]) == ["Items must be unique"]
    obj = build_form({"properties": {"a": {"type": "string", "title": "A"}}, "required": ["a"]})
    assert isinstance(obj, ObjectNode)
    assert field_errors(obj, {}) == ["A is required"]


def test_json_schema_target_reports_every_issue() -> None:
    target = target_for({
        "type": "object",
        "properties": {"age": {"type": "integer", "minimum": 0}, "mail": {"format": "email"}},
        "required": ["age"],
    })
    assert target.validate({"age": 3}) == {"age": 3}
    with pytest.raises(FormValidationError) as info:
        target.validate({"age": -1, "mail": "nope"})
    assert {issue.path for issue in info.value.issues} == {("age",), ("mail",)}


class Item(BaseModel):
    name: str = Field(min_length=1)
    qty: int = 1


def test_type_target_returns_instances() -> None:
    target = target_for(Item)
    assert target.title == "Item"
    item = target.validate({"name": "pen"})
    assert item == Item(name="pen")
    with pytest.raises(FormValidationError) as info:
        target.validate({"name": "", "qty": "x"})
    assert {issue.path for issue in info.value.issues} == {("name",), ("qty",)}


def test_other_python_types() -> None:
    from dataclasses import dataclass

    @dataclass
    class Point:
        x: int
        y: int = 0

    target = target_for(Point)
    assert target.validate({"x": 1}) == Point(1, 0)
    assert target_for(list[int]).validate([1, 2]) == [1, 2]


def test_missing_required_properties_are_placed_at_the_property() -> None:
    target = target_for({
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "string"}, "c": {}},
        "required": ["a", "b"],
    })
    with pytest.raises(FormValidationError) as info:
        target.validate({"c": 1})
    assert [(issue.path, issue.message) for issue in info.value.issues] == [
        (("a",), "Field required"),
        (("b",), "Field required"),
    ]
