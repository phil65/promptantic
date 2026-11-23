from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
import pytest
from textual.app import App
from textual.widgets import Input, Select, Static, Switch

from promptantic.form import target_for
from promptantic.textual import FormApp, FormScreen, FormView
from promptantic.textual.editors import ListEditor, UnionEditor


pytest.importorskip("textual")


class Cat(BaseModel):
    kind: Literal["cat"] = "cat"
    lives: int = 9


class Dog(BaseModel):
    kind: Literal["dog"] = "dog"
    good: bool = True


class Address(BaseModel):
    street: str
    city: str = "Berlin"


class Order(BaseModel):
    customer: Annotated[str, Field(min_length=1)]
    quantity: Annotated[int, Field(ge=1)] = 1
    express: bool = False
    size: Literal["s", "m", "l"] = "m"
    notes: list[str] = []
    pet: Annotated[Cat | Dog, Field(discriminator="kind")] = Cat()
    ship_to: Address | None = None


def inputs(app: App[Any]) -> list[Input]:
    return list(app.query(Input))


async def test_fill_and_submit_a_model() -> None:
    app = FormApp(target_for(Order))
    async with app.run_test() as pilot:
        customer, quantity, *_ = inputs(app)
        customer.value = "Ada"
        quantity.value = "3"
        app.query_one(Switch).value = True
        await pilot.pause()
        app.action_submit()
        await pilot.pause()
    assert app.return_value == Order(customer="Ada", quantity=3, express=True)


async def test_errors_show_at_their_fields() -> None:
    app = FormApp(target_for(Order))
    async with app.run_test() as pilot:
        inputs(app)[1].value = "0"  # quantity, below its minimum
        await pilot.pause()
        app.action_submit()
        await pilot.pause()
        shown = [str(w.render()) for w in app.query(".errors") if not w.has_class("-empty")]
        assert app.is_running  # not submitted
        assert any("required" in text.lower() for text in shown)  # customer
        assert any("1" in text for text in shown)  # quantity >= 1
        summary = app.query_one("#summary", Static)
        assert not summary.has_class("-empty")


async def test_union_switches_variant_and_lists_add_rows() -> None:
    app = FormApp(target_for(Order))
    async with app.run_test() as pilot:
        inputs(app)[0].value = "Bob"
        union = app.query_one(UnionEditor)
        union.query_children(Select).first().value = 1  # dog
        await pilot.pause()
        notes = app.query_one(ListEditor)
        await pilot.click(notes.query_children(".add").first())
        await pilot.pause()
        notes.query(Input).last().value = "fragile"
        await pilot.pause()
        app.action_submit()
        await pilot.pause()
    result = app.return_value
    assert isinstance(result, Order)
    assert isinstance(result.pet, Dog)
    assert result.notes == ["fragile"]


async def test_json_schema_gives_a_dict() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "count": {"type": "integer", "default": 2},
            "tags": {"type": "array", "items": {"enum": ["x", "y"]}, "uniqueItems": True},
        },
        "required": ["name"],
    }
    app = FormApp(target_for(schema))
    async with app.run_test() as pilot:
        inputs(app)[0].value = "n"
        await pilot.pause()
        app.action_submit()
        await pilot.pause()
    assert app.return_value == {"name": "n", "count": 2, "tags": []}


async def test_initial_values_and_cancel() -> None:
    app = FormApp(target_for(Order), initial={"customer": "Eve", "size": "l"})
    async with app.run_test() as pilot:
        assert inputs(app)[0].value == "Eve"
        app.action_cancel()
        await pilot.pause()
    assert app.cancelled
    assert app.return_value is None


async def test_form_screen_in_a_host_app() -> None:
    results: list[Any] = []

    class Host(App[None]):
        def on_mount(self) -> None:
            self.push_screen(FormScreen(Order, initial={"customer": "Kim"}), results.append)

    app = Host()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, FormScreen)
        screen.query_one(FormView).submit()
        await pilot.pause()
    assert results == [Order(customer="Kim")]


async def test_optional_nested_object_is_switched_on_explicitly() -> None:
    app = FormApp(target_for(Order), initial={"customer": "Lu"})
    async with app.run_test() as pilot:
        app.action_submit()  # address switched off: no street needed
        await pilot.pause()
    assert app.return_value == Order(customer="Lu", ship_to=None)

    app = FormApp(target_for(Order), initial={"customer": "Lu"})
    async with app.run_test() as pilot:
        toggle = app.query(".enabled").first(Switch)
        toggle.value = True
        await pilot.pause()
        inputs(app)[-2].value = "Main St 1"  # street (city follows)
        await pilot.pause()
        app.action_submit()
        await pilot.pause()
    assert app.return_value == Order(customer="Lu", ship_to=Address(street="Main St 1"))
