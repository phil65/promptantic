"""The form tree: what a JSON Schema asks for, independent of any UI.

A renderer walks these nodes and builds its widgets from them. Nested parts
(object properties, array items, union variants) are built on first access, so
recursive schemas (a tree whose nodes contain trees) are fine: only what a user
opens is ever built.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Final, Literal


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class _Unset(Enum):
    """Marker for "no value" where ``None`` is a real value (JSON ``null``)."""

    UNSET = "UNSET"

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final = _Unset.UNSET
"""No value given (distinct from ``None``, which is JSON ``null``)."""

type Unset = Literal[_Unset.UNSET]


@dataclass(frozen=True)
class Meta:
    """What every node carries besides its kind: labels, default, flags."""

    title: str | None = None
    description: str | None = None
    default: Any = UNSET
    """The schema's ``default``; :data:`UNSET` when it has none."""
    examples: tuple[Any, ...] = ()
    read_only: bool = False
    write_only: bool = False
    deprecated: bool = False
    extensions: Mapping[str, Any] = field(default_factory=dict)
    """``x-`` keys of the schema (e.g. ``x-completions``), without the prefix."""

    @property
    def has_default(self) -> bool:
        return self.default is not UNSET


@dataclass(frozen=True)
class NodeBase:
    """Common to all nodes."""

    meta: Meta
    nullable: bool = False
    """``null`` is allowed besides the node's own kind."""


@dataclass(frozen=True)
class StringNode(NodeBase):
    """Free text, optionally constrained."""

    kind: Literal["string"] = "string"
    format: str | None = None
    """``date``, ``date-time``, ``email``, ``uri``, ``uuid``, ... (JSON Schema formats)."""
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    content_media_type: str | None = None

    @property
    def secret(self) -> bool:
        """Input that shouldn't be shown (``format: password`` or ``writeOnly``)."""
        return self.format == "password" or self.meta.write_only


@dataclass(frozen=True)
class NumberNode(NodeBase):
    """A number; ``integer`` for whole numbers."""

    kind: Literal["number"] = "number"
    integer: bool = False
    minimum: float | None = None
    maximum: float | None = None
    exclusive_minimum: float | None = None
    exclusive_maximum: float | None = None
    multiple_of: float | None = None


@dataclass(frozen=True)
class BooleanNode(NodeBase):
    """True or false."""

    kind: Literal["boolean"] = "boolean"


@dataclass(frozen=True)
class NullNode(NodeBase):
    """Only ``null`` (e.g. the ``None`` member of a union that isn't just "optional")."""

    kind: Literal["null"] = "null"


@dataclass(frozen=True)
class Choice:
    """One allowed value of a :class:`ChoiceNode`."""

    value: Any
    label: str


@dataclass(frozen=True)
class ChoiceNode(NodeBase):
    """One of a fixed set of values (``enum``, ``const``, or ``oneOf`` of titled consts)."""

    kind: Literal["choice"] = "choice"
    choices: tuple[Choice, ...] = ()

    @property
    def fixed(self) -> bool:
        """Only one value is possible (``const``): nothing to ask."""
        return len(self.choices) == 1 and not self.nullable


@dataclass(frozen=True)
class AnyNode(NodeBase):
    """Anything (an empty schema): entered as JSON."""

    kind: Literal["any"] = "any"


@dataclass(frozen=True, eq=False)
class ArrayNode(NodeBase):
    """A list of items of one kind."""

    kind: Literal["array"] = "array"
    min_items: int | None = None
    max_items: int | None = None
    unique: bool = False
    build_items: Callable[[], FormNode] | None = field(default=None, repr=False)

    @cached_property
    def items(self) -> FormNode:
        """The node every item follows (built on first access)."""
        if self.build_items is None:
            return AnyNode(meta=Meta())
        return self.build_items()

    @property
    def multi_choice(self) -> bool:
        """Items are choices and unique: a pick-several list rather than an item editor."""
        return isinstance(self.items, ChoiceNode) and not self.items.fixed


@dataclass(frozen=True, eq=False)
class TupleNode(NodeBase):
    """A fixed sequence of positions, each of its own kind (``prefixItems``)."""

    kind: Literal["tuple"] = "tuple"
    build_positions: Callable[[], tuple[FormNode, ...]] | None = field(default=None, repr=False)

    @cached_property
    def positions(self) -> tuple[FormNode, ...]:
        return () if self.build_positions is None else self.build_positions()


@dataclass(frozen=True)
class Property:
    """One field of an :class:`ObjectNode`."""

    name: str
    node: FormNode
    required: bool

    @property
    def label(self) -> str:
        return self.node.meta.title or self.name


@dataclass(frozen=True, eq=False)
class ObjectNode(NodeBase):
    """Named fields, plus optionally free keys (``additionalProperties`` with a schema)."""

    kind: Literal["object"] = "object"
    build_properties: Callable[[], tuple[Property, ...]] | None = field(default=None, repr=False)
    build_additional: Callable[[], FormNode] | None = field(default=None, repr=False)
    """Schema of keys beyond the named ones; ``None``: no extra keys can be entered."""
    min_properties: int | None = None
    max_properties: int | None = None

    @cached_property
    def properties(self) -> tuple[Property, ...]:
        return () if self.build_properties is None else self.build_properties()

    @cached_property
    def additional(self) -> FormNode | None:
        """Node for the values of free keys, or ``None`` when there are none."""
        return None if self.build_additional is None else self.build_additional()

    @property
    def is_map(self) -> bool:
        """Only free keys (e.g. ``dict[str, int]``): a key/value editor."""
        return not self.properties and self.build_additional is not None


@dataclass(frozen=True)
class Variant:
    """One alternative of a :class:`UnionNode`."""

    label: str
    node: FormNode


@dataclass(frozen=True, eq=False)
class UnionNode(NodeBase):
    """One of several alternatives (``anyOf`` / ``oneOf`` / several types)."""

    kind: Literal["union"] = "union"
    build_variants: Callable[[], tuple[Variant, ...]] | None = field(default=None, repr=False)
    discriminator: str | None = None
    """Property whose value tells the variants apart (OpenAPI / pydantic discriminator)."""

    @cached_property
    def variants(self) -> tuple[Variant, ...]:
        return () if self.build_variants is None else self.build_variants()


type FormNode = (
    StringNode
    | NumberNode
    | BooleanNode
    | NullNode
    | ChoiceNode
    | AnyNode
    | ArrayNode
    | TupleNode
    | ObjectNode
    | UnionNode
)
"""A node of the form tree."""
