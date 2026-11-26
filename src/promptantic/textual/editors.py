"""One Textual editor per kind of form node.

Every editor shows its field, checks it while the user types (the field's own
constraints, from :func:`~promptantic.form.field_errors`), and gives its current
value (:meth:`Editor.get_value`). The whole value is validated on submit.
"""

import json
from typing import TYPE_CHECKING, Any, ClassVar, cast

from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Input, Label, Select, SelectionList, Static, Switch

from promptantic.form import (
    UNSET,
    AnyNode,
    ArrayNode,
    BooleanNode,
    ChoiceNode,
    FieldError,
    NullNode,
    NumberNode,
    ObjectNode,
    StringNode,
    TupleNode,
    UnionNode,
    field_errors,
    parse_text,
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import ComposeResult

    from promptantic.form import FormNode
    from promptantic.form.nodes import Unset
    from promptantic.form.target import Path


type Registry = Callable[[Path, Editor], None]
"""Called by every editor on mount, so the form can show issues at their path."""


class Editor(Widget):
    """Base of all editors: a node, its path in the value, and an error line."""

    DEFAULT_CSS = """
    Editor { height: auto; }
    Editor > .pa-errors { color: $text-error; height: auto; }
    Editor > .pa-errors.-empty { display: none; }
    """

    def __init__(self, node: FormNode, path: Path, initial: Any, register: Registry) -> None:
        super().__init__()
        self.node = node
        self.path = path
        self.initial = initial
        self._register = register

    def on_mount(self) -> None:
        self._register(self.path, self)

    def errors_widget(self) -> Static:
        return Static("", classes="pa-errors -empty")

    def get_value(self) -> Any | Unset:
        """The value entered so far (:data:`UNSET`: nothing).

        Raises:
            FieldError: Input that can't become a value (e.g. text in a number field).
        """
        raise NotImplementedError

    def show_errors(self, messages: list[str]) -> None:
        errors = self.query_children(".pa-errors").first(Static)
        errors.update("\n".join(messages))
        errors.set_class(not messages, "-empty")

    def check(self) -> None:
        """Show what's wrong with this field alone (on every change)."""
        try:
            value = self.get_value()
        except FieldError as exc:
            self.show_errors([str(exc)])
            return
        self.show_errors([] if value is UNSET else field_errors(self.node, value))


def make_editor(node: FormNode, path: Path, initial: Any, register: Registry) -> Editor:  # noqa: PLR0911
    """The editor for ``node`` (``initial``: its starting value, or :data:`UNSET`)."""
    if initial is UNSET:
        initial = node.meta.default
    match node:
        case StringNode() | NumberNode() | AnyNode():
            return TextEditor(node, path, initial, register)
        case BooleanNode():
            return BooleanEditor(node, path, initial, register)
        case ChoiceNode():
            return ChoiceEditor(node, path, initial, register)
        case NullNode():
            return NullEditor(node, path, initial, register)
        case ArrayNode() if node.multi_choice:
            return MultiChoiceEditor(node, path, initial, register)
        case ArrayNode() | TupleNode():
            return ListEditor(node, path, initial, register)
        case ObjectNode() if node.is_map:
            return MapEditor(node, path, initial, register)
        case ObjectNode():
            return ObjectEditor(node, path, initial, register)
        case UnionNode():
            return UnionEditor(node, path, initial, register)


def _hint(node: FormNode) -> str:
    """Placeholder text: an example, the format, or what kind of value goes here."""
    if node.meta.examples:
        return f"e.g. {node.meta.examples[0]}"
    match node:
        case StringNode(format=str(fmt)):
            return {
                "date": "YYYY-MM-DD",
                "date-time": "YYYY-MM-DDThh:mm:ss",
                "time": "hh:mm:ss",
            }.get(fmt, fmt)
        case NumberNode(integer=True):
            return "whole number"
        case NumberNode():
            return "number"
        case AnyNode():
            return "JSON"
        case _:
            return ""


class TextEditor(Editor):
    """Typed input: text, numbers, or free JSON."""

    node: StringNode | NumberNode | AnyNode

    def compose(self) -> ComposeResult:
        node = self.node
        text = "" if self.initial in (UNSET, None) else self._format(self.initial)
        input_type = "text"
        if isinstance(node, NumberNode):
            input_type = "integer" if node.integer else "number"
        yield Input(
            value=text,
            placeholder=_hint(node),
            password=isinstance(node, StringNode) and node.secret,
            type=input_type,
            compact=True,
        )
        yield self.errors_widget()

    def _format(self, value: Any) -> str:
        if isinstance(self.node, AnyNode):
            return json.dumps(value)
        return str(value)

    def get_value(self) -> Any | Unset:
        text = self.query_one(Input).value
        value = parse_text(self.node, text)
        return None if value is UNSET and self.node.nullable and text == "" else value

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self.check()


class BooleanEditor(Editor):
    """A switch; a three-way select when ``null`` is allowed too."""

    node: BooleanNode
    _OPTIONS: ClassVar = [("Yes", True), ("No", False)]

    def compose(self) -> ComposeResult:
        if self.node.nullable:
            value = self.initial if isinstance(self.initial, bool) else Select.NULL
            yield Select(self._OPTIONS, value=value, prompt="(none)", compact=True)
        else:
            yield Switch(value=self.initial is True)
        yield self.errors_widget()

    def get_value(self) -> Any | Unset:
        if self.node.nullable:
            value = self.query_one(Select).value
            return None if value is Select.NULL else value
        return self.query_one(Switch).value


class ChoiceEditor(Editor):
    """A select of the allowed values; just the value when there's only one (``const``)."""

    node: ChoiceNode

    def compose(self) -> ComposeResult:
        choices = self.node.choices
        if self.node.fixed:
            yield Label(choices[0].label, classes="pa-fixed")
        else:
            values = [choice.value for choice in choices]
            index = values.index(self.initial) if self.initial in values else Select.NULL
            yield Select(
                [(choice.label, i) for i, choice in enumerate(choices)],
                value=index,
                prompt="(none)" if self.node.nullable else "Select…",
                compact=True,
            )
        yield self.errors_widget()

    def get_value(self) -> Any | Unset:
        if self.node.fixed:
            return self.node.choices[0].value
        index = self.query_one(Select).value
        if index is Select.NULL:
            return None if self.node.nullable else UNSET
        return self.node.choices[cast("int", index)].value

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        self.check()


class MultiChoiceEditor(Editor):
    """Pick several of a fixed set (a unique list of choices)."""

    node: ArrayNode

    def compose(self) -> ComposeResult:
        items = cast("ChoiceNode", self.node.items)
        selected = self.initial if isinstance(self.initial, list) else []
        yield SelectionList[int](*[
            (choice.label, i, choice.value in selected) for i, choice in enumerate(items.choices)
        ])
        yield self.errors_widget()

    def get_value(self) -> Any | Unset:
        items = cast("ChoiceNode", self.node.items)
        return [items.choices[i].value for i in sorted(self.query_one(SelectionList).selected)]


class NullEditor(Editor):
    """Nothing to enter: the value is ``null``."""

    def compose(self) -> ComposeResult:
        yield Label("null", classes="pa-fixed")
        yield self.errors_widget()

    def get_value(self) -> Any | Unset:
        return None


class _Row(Horizontal):
    """One entry of a list or map editor: its editors and a remove button."""

    DEFAULT_CSS = """
    _Row { height: auto; }
    _Row > .pa-entry { width: 1fr; height: auto; }
    _Row > Button { min-width: 5; width: 5; }
    """


class ListEditor(Editor):
    """Items of one kind (add / remove), or the fixed positions of a tuple."""

    node: ArrayNode | TupleNode
    DEFAULT_CSS = """
    ListEditor > .pa-rows { height: auto; padding-left: 2; }
    ListEditor > .pa-add { width: auto; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(classes="pa-rows"):
            initial = self.initial if isinstance(self.initial, list | tuple) else []
            if isinstance(self.node, TupleNode):
                for i, position in enumerate(self.node.positions):
                    value = initial[i] if i < len(initial) else UNSET
                    yield make_editor(position, (*self.path, i), value, self._register)
            else:
                for value in initial:
                    yield self._row(value)
        if isinstance(self.node, ArrayNode):
            yield Button("+ Add", classes="pa-add", compact=True)
        yield self.errors_widget()

    def _row(self, value: Any) -> _Row:
        node = cast("ArrayNode", self.node)
        index = len(self.query(".pa-rows > _Row")) if self.is_mounted else 0
        editor = make_editor(node.items, (*self.path, index), value, self._register)
        if isinstance(editor, ObjectEditor):
            editor.heading = f"#{index + 1}"  # rather than the item schema's (class) name
        editor.add_class("pa-entry")
        return _Row(editor, Button("✕", classes="pa-remove", compact=True))

    def _editors(self) -> list[Editor]:
        rows = self.query_children(".pa-rows").first(Vertical)
        if isinstance(self.node, TupleNode):
            return list(rows.query_children(Editor))
        return [row.query_children(Editor).first() for row in rows.query_children(_Row)]

    def get_value(self) -> Any | Unset:
        values = [editor.get_value() for editor in self._editors()]
        return [None if value is UNSET else value for value in values]

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.has_class("pa-add"):
            await self.query_children(".pa-rows").first(Vertical).mount(self._row(UNSET))
        elif event.button.has_class("pa-remove") and isinstance(event.button.parent, _Row):
            await event.button.parent.remove()
        self.check()


class MapEditor(Editor):
    """Free keys with values of one kind (``dict[str, X]``)."""

    node: ObjectNode
    DEFAULT_CSS = """
    MapEditor > .pa-rows { height: auto; padding-left: 2; }
    MapEditor .pa-key { width: 20; }
    MapEditor > .pa-add { width: auto; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(classes="pa-rows"):
            if isinstance(self.initial, dict):
                for key, value in self.initial.items():
                    yield self._row(str(key), value)
        yield Button("+ Add", classes="pa-add", compact=True)
        yield self.errors_widget()

    def _row(self, key: str, value: Any) -> _Row:
        value_node = self.node.additional
        assert value_node is not None  # is_map
        editor = make_editor(value_node, (*self.path, key), value, self._register)
        editor.add_class("pa-entry")
        return _Row(
            Input(value=key, placeholder="key", classes="pa-key", compact=True),
            editor,
            Button("✕", classes="pa-remove", compact=True),
        )

    def get_value(self) -> Any | Unset:
        result: dict[str, Any] = {}
        rows = self.query_children(".pa-rows").first(Vertical)
        for row in rows.query_children(_Row):
            key = row.query_children(Input).first().value
            if key:
                value = row.query_children(Editor).first().get_value()
                result[key] = None if value is UNSET else value
        return result

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.has_class("pa-add"):
            await self.query_children(".pa-rows").first(Vertical).mount(self._row("", UNSET))
        elif event.button.has_class("pa-remove") and isinstance(event.button.parent, _Row):
            await event.button.parent.remove()


class ObjectEditor(Editor):
    """Named fields; nested objects fold (the outermost one doesn't).

    Fields with only one possible value (``const``, e.g. a union's discriminator) aren't
    shown; their value is still part of the result. An object that may be ``null``
    starts with a switch: off means ``null``, on shows its fields.
    """

    node: ObjectNode
    fold = True
    """Show as a folding section (off at the root and for a union's chosen variant)."""
    heading: str | None = None
    """Title of the folding section (the field's label, set by the containing object)."""

    DEFAULT_CSS = """
    ObjectEditor .pa-field { height: auto; margin: 0 0 1 0; }
    ObjectEditor .pa-label { text-style: bold; }
    ObjectEditor .pa-help { color: $text-muted; }
    ObjectEditor Collapsible { padding-left: 1; }
    ObjectEditor > .pa-toggle { height: auto; }
    ObjectEditor .pa-fields { height: auto; }
    ObjectEditor .pa-fields.-off { display: none; }
    """

    def compose(self) -> ComposeResult:
        self._editors: dict[str, Editor] = {}
        enabled = not self.node.nullable or isinstance(self.initial, dict)
        if self.node.nullable:
            with Horizontal(classes="pa-toggle"):
                yield Switch(value=enabled, classes="pa-enabled")
                yield Label(self.heading or self.node.meta.title or "Fill in")
        fields = Vertical(*self._fields(), classes="pa-fields")
        fields.set_class(not enabled, "-off")
        if self.path and self.fold and not self.node.nullable:
            with Collapsible(title=self.heading or self.node.meta.title or "", collapsed=False):
                yield fields
        else:
            yield fields
        yield self.errors_widget()

    def _fields(self) -> list[Widget]:
        initial = self.initial if isinstance(self.initial, dict) else {}
        widgets: list[Widget] = []
        for prop in self.node.properties:
            if prop.node.meta.read_only:
                continue
            editor = make_editor(
                prop.node, (*self.path, prop.name), initial.get(prop.name, UNSET), self._register
            )
            self._editors[prop.name] = editor
            if isinstance(prop.node, ChoiceNode) and prop.node.fixed:
                editor.display = False
                widgets.append(editor)
                continue
            label = f"{prop.label}{' *' if prop.required else ''}"
            parts: list[Widget] = []
            if isinstance(editor, ObjectEditor):
                editor.heading = label  # its section (or switch) carries the label
            else:
                parts.append(Label(label, classes="pa-label"))
            if description := prop.node.meta.description:
                parts.append(Static(description, classes="pa-help"))
            parts.append(editor)
            widgets.append(Vertical(*parts, classes="pa-field"))
        return widgets

    def _enabled(self) -> bool:
        if not self.node.nullable:
            return True
        return self.query_children(".pa-toggle").first().query_children(Switch).first().value

    def get_value(self) -> Any | Unset:
        if not self._enabled():
            return None
        result: dict[str, Any] = {}
        if self.node.additional is not None and isinstance(self.initial, dict):
            # free keys allowed: keep the extra starting values (no editor for them)
            declared = {prop.name for prop in self.node.properties}
            result.update({k: v for k, v in self.initial.items() if k not in declared})
        for name, editor in self._editors.items():
            value = editor.get_value()
            if value is not UNSET:
                result[name] = value
        return result

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if not event.switch.has_class("pa-enabled"):
            return
        event.stop()
        self.query_children(".pa-fields").first().set_class(not event.value, "-off")


class UnionEditor(Editor):
    """Pick the kind first, then fill that kind's editor."""

    node: UnionNode
    DEFAULT_CSS = "UnionEditor > .pa-variant { height: auto; padding-left: 2; margin: 1 0 0 0; }"

    def compose(self) -> ComposeResult:
        variants = self.node.variants
        index = self._initial_variant()
        yield Select(
            [(variant.label, i) for i, variant in enumerate(variants)],
            value=index,
            allow_blank=self.node.nullable,
            prompt="(none)",
            compact=True,
        )
        with Vertical(classes="pa-variant"):
            if isinstance(index, int):
                yield self._variant_editor(index, self.initial)
        yield self.errors_widget()

    def _initial_variant(self) -> int | Any:
        """The variant the initial value belongs to (by discriminator), else the first."""
        variants = self.node.variants
        if self.initial is None and self.node.nullable:
            return Select.NULL
        if self.node.discriminator and isinstance(self.initial, dict):
            tag = self.initial.get(self.node.discriminator)
            for i, variant in enumerate(variants):
                if variant.label == tag:
                    return i
        return 0 if variants else Select.NULL

    def get_value(self) -> Any | Unset:
        holder = self.query_children(".pa-variant").first(Vertical)
        editors = list(holder.query_children(Editor))
        if not editors:
            return None if self.node.nullable else UNSET
        return editors[0].get_value()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.parent is not self:
            return
        event.stop()
        holder = self.query_children(".pa-variant").first(Vertical)
        await holder.remove_children()
        if isinstance(event.value, int):
            await holder.mount(self._variant_editor(event.value, UNSET))

    def _variant_editor(self, index: int, initial: Any) -> Editor:
        editor = make_editor(self.node.variants[index].node, self.path, initial, self._register)
        if isinstance(editor, ObjectEditor):
            editor.fold = False  # the select above already names it
        return editor
