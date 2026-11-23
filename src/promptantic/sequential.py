"""Ask for a form one field at a time (prompt-toolkit), where a full TUI can't run.

Walks the same form tree as the Textual renderer: each field is a prompt that
checks its input as it's typed (the field's own constraints), choices and union
variants are numbered lists, lists and maps ask whether to add another entry,
and optional objects ask whether to fill them in at all. After the last field the
whole value is validated; on problems they're listed and the form is asked again,
with everything entered so far as the defaults.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from prompt_toolkit import PromptSession
from prompt_toolkit.validation import ValidationError as PromptValidationError, Validator

from promptantic.form import (
    UNSET,
    AnyNode,
    ArrayNode,
    BooleanNode,
    ChoiceNode,
    FieldError,
    FormCancelledError,
    FormTarget,
    FormValidationError,
    NullNode,
    NumberNode,
    ObjectNode,
    StringNode,
    TupleNode,
    UnionNode,
    build_form,
    field_errors,
    parse_text,
    target_for,
)


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from prompt_toolkit.document import Document

    from promptantic.form import FormNode
    from promptantic.form.nodes import Unset


_YES = ("y", "yes", "j", "ja", "true", "1")
_NO = ("n", "no", "nein", "false", "0")


async def fill_sequential(
    target: FormTarget[Any] | type[Any] | Mapping[str, Any],
    *,
    title: str | None = None,
    initial: Mapping[str, Any] | None = None,
    session: PromptSession[str] | None = None,
    echo: Callable[[str], None] = print,
) -> Any:
    """Ask for every field in turn and return the validated result."""
    form_target = target if isinstance(target, FormTarget) else target_for(target)
    asker = _Asker(session or PromptSession(), echo)
    root = build_form(form_target.schema)
    if heading := title or form_target.title:
        echo(heading)
    value: Any = dict(initial) if initial is not None else UNSET
    while True:
        try:
            value = await asker.ask(root, "", value, required=True, depth=0)
        except (EOFError, KeyboardInterrupt):  # Ctrl-D / Ctrl-C
            raise FormCancelledError from None
        try:
            return form_target.validate({} if value is UNSET else value)
        except FormValidationError as exc:
            echo("Please fix:")
            for issue in exc.issues:
                where = ".".join(map(str, issue.path)) or "value"
                echo(f"  {where}: {issue.message}")


class _Asker:
    def __init__(self, session: PromptSession[str], echo: Callable[[str], None]) -> None:
        self.session = session
        self.echo = echo

    async def ask(  # noqa: PLR0911
        self, node: FormNode, label: str, initial: Any, *, required: bool, depth: int
    ) -> Any | Unset:
        if initial is UNSET:
            initial = node.meta.default
        match node:
            case StringNode() | NumberNode() | AnyNode():
                return await self._text(node, label, initial, required=required)
            case BooleanNode():
                return await self._boolean(node, label, initial)
            case ChoiceNode():
                return await self._choice(node, label, initial, required=required)
            case NullNode():
                return None
            case ArrayNode() if node.multi_choice:
                return await self._multi_choice(node, label, initial)
            case ArrayNode():
                return await self._array(node, label, initial, depth)
            case TupleNode():
                return [
                    await self.ask(p, f"{label}[{i}]", _at(initial, i), required=True, depth=depth)
                    for i, p in enumerate(node.positions)
                ]
            case ObjectNode() if node.is_map:
                return await self._map(node, label, initial, depth)
            case ObjectNode():
                return await self._object(node, label, initial, depth)
            case UnionNode():
                return await self._union(node, label, initial, required=required, depth=depth)

    async def _prompt(
        self,
        message: str,
        *,
        default: str = "",
        validator: Callable[[str], object] | None = None,
        secret: bool = False,
    ) -> str:
        """Ask once; empty input means ``default`` (shown in brackets, not pre-filled)."""
        shown = "" if default == "" or secret else f" [{default}]"

        def check(text: str) -> None:
            if validator is not None:
                validator(text or default)

        answer = await self.session.prompt_async(
            f"{message}{shown}: ",
            validator=_validator(check),
            is_password=secret,
            validate_while_typing=False,
        )
        return answer or default

    async def _text(
        self, node: StringNode | NumberNode | AnyNode, label: str, initial: Any, *, required: bool
    ) -> Any | Unset:
        if node.meta.description:
            self.echo(f"  ({node.meta.description})")
        allow_empty = not required or node.nullable

        def check(text: str) -> None:
            value = parse_text(node, text)
            if value is UNSET:
                if not allow_empty:
                    raise FieldError("A value is required")
                return
            if errors := field_errors(node, value):
                raise FieldError("; ".join(errors))

        default = "" if initial in (UNSET, None) else _format(node, initial)
        secret = isinstance(node, StringNode) and node.secret
        text = await self._prompt(label, default=default, validator=check, secret=secret)
        value = parse_text(node, text)
        return None if value is UNSET and node.nullable and required else value

    async def _boolean(self, node: BooleanNode, label: str, initial: Any) -> Any:
        default = {True: "y", False: "n"}.get(initial, "") if isinstance(initial, bool) else ""

        def check(text: str) -> None:
            answer = text.strip().lower()
            if answer in _YES or answer in _NO or (answer == "" and node.nullable):
                return
            raise FieldError("Answer y or n")

        answer = await self._prompt(f"{label} [y/n]", default=default, validator=check)
        answer = answer.strip().lower()
        return None if answer == "" else answer in _YES

    async def _choice(self, node: ChoiceNode, label: str, initial: Any, *, required: bool) -> Any:
        if node.fixed:
            return node.choices[0].value
        labels = [choice.label for choice in node.choices]
        index = await self._pick(
            label, labels, _index_of(node, initial), optional=node.nullable or not required
        )
        return (None if node.nullable else UNSET) if index is None else node.choices[index].value

    async def _pick(
        self, label: str, labels: list[str], default: int | None, *, optional: bool
    ) -> int | None:
        self.echo(f"{label}:")
        for i, text in enumerate(labels, start=1):
            self.echo(f"  {i}) {text}")

        def check(text: str) -> None:
            if _parse_pick(text, labels) is None and not (optional and text.strip() == ""):
                raise FieldError(f"Enter 1-{len(labels)}")

        text = await self._prompt(
            "Choice", default="" if default is None else str(default + 1), validator=check
        )
        return _parse_pick(text, labels)

    async def _multi_choice(self, node: ArrayNode, label: str, initial: Any) -> list[Any]:
        items = node.items
        assert isinstance(items, ChoiceNode)  # multi_choice
        self.echo(f"{label} (numbers, comma-separated):")
        for i, choice in enumerate(items.choices, start=1):
            self.echo(f"  {i}) {choice.label}")
        values = [c.value for c in items.choices]
        selected = initial if isinstance(initial, list) else []
        default = ",".join(str(values.index(v) + 1) for v in selected if v in values)

        def parse(text: str) -> list[int]:
            picks = [part.strip() for part in text.split(",") if part.strip()]
            indexes = [int(p) - 1 for p in picks if p.isdigit()]
            if len(indexes) != len(picks) or any(not 0 <= i < len(values) for i in indexes):
                raise FieldError(f"Enter numbers 1-{len(values)}")
            return list(dict.fromkeys(indexes))

        text = await self._prompt("Choices", default=default, validator=parse)
        return [values[i] for i in parse(text)]

    async def _array(self, node: ArrayNode, label: str, initial: Any, depth: int) -> list[Any]:
        items: list[Any] = []
        for i, value in enumerate(initial if isinstance(initial, list) else []):
            item = await self.ask(
                node.items, f"{label}[{i}]", value, required=True, depth=depth + 1
            )
            items.append(None if item is UNSET else item)
        while (node.max_items is None or len(items) < node.max_items) and (
            len(items) < (node.min_items or 0) or await self._confirm(f"Add an item to {label}")
        ):
            item = await self.ask(
                node.items, f"{label}[{len(items)}]", UNSET, required=True, depth=depth + 1
            )
            items.append(None if item is UNSET else item)
        return items

    async def _map(self, node: ObjectNode, label: str, initial: Any, depth: int) -> dict[str, Any]:
        value_node = node.additional
        assert value_node is not None  # is_map
        result: dict[str, Any] = {}
        for key, value in initial.items() if isinstance(initial, dict) else ():
            result[key] = await self.ask(
                value_node, f"{label}.{key}", value, required=True, depth=depth + 1
            )
        while await self._confirm(f"Add an entry to {label}"):
            key = await self._prompt("Key", validator=_non_empty)
            result[key] = await self.ask(
                value_node, f"{label}.{key}", UNSET, required=True, depth=depth + 1
            )
        return result

    async def _object(self, node: ObjectNode, label: str, initial: Any, depth: int) -> Any:
        if node.nullable and not await self._confirm(
            f"Fill in {label or 'this'}", default=isinstance(initial, dict)
        ):
            return None
        if label:
            self.echo(f"{label}:")
        values = initial if isinstance(initial, dict) else {}
        result: dict[str, Any] = {}
        for prop in node.properties:
            if prop.node.meta.read_only:
                continue
            name = f"{'  ' * depth}{prop.label}{' *' if prop.required else ''}"
            value = await self.ask(
                prop.node,
                name,
                values.get(prop.name, UNSET),
                required=prop.required,
                depth=depth + 1,
            )
            if value is not UNSET:
                result[prop.name] = value
        return result

    async def _union(
        self, node: UnionNode, label: str, initial: Any, *, required: bool, depth: int
    ) -> Any | Unset:
        variants = node.variants
        default = 0
        if node.discriminator and isinstance(initial, dict):
            tags = [variant.label for variant in variants]
            tag = initial.get(node.discriminator)
            default = tags.index(tag) if tag in tags else 0
        index = await self._pick(
            label or "Kind",
            [v.label for v in variants],
            default,
            optional=node.nullable or not required,
        )
        if index is None:
            return None if node.nullable else UNSET
        return await self.ask(variants[index].node, label, initial, required=required, depth=depth)

    async def _confirm(self, question: str, *, default: bool = False) -> bool:
        answer = await self._prompt(f"{question}? [{'Y/n' if default else 'y/N'}]")
        answer = answer.strip().lower()
        return default if answer == "" else answer in _YES


def _validator(check: Callable[[str], object]) -> Validator:
    """A prompt-toolkit validator from a function raising :class:`FieldError`."""

    class _Check(Validator):
        def validate(self, document: Document) -> None:
            try:
                check(document.text)
            except FieldError as exc:
                # cursor at the end, to correct the input from there
                raise PromptValidationError(
                    cursor_position=len(document.text), message=str(exc)
                ) from None

    return _Check()


def _non_empty(text: str) -> None:
    if not text.strip():
        raise FieldError("Enter a key")


def _format(node: FormNode, value: Any) -> str:
    return json.dumps(value) if isinstance(node, AnyNode) else str(value)


def _at(values: Any, index: int) -> Any:
    return values[index] if isinstance(values, list | tuple) and index < len(values) else UNSET


def _index_of(node: ChoiceNode, value: Any) -> int | None:
    values = [choice.value for choice in node.choices]
    return values.index(value) if value in values else None


def _parse_pick(text: str, labels: list[str]) -> int | None:
    text = text.strip()
    if text.isdigit() and 1 <= int(text) <= len(labels):
        return int(text) - 1
    lowered = [label.lower() for label in labels]
    return lowered.index(text.lower()) if text.lower() in lowered else None
