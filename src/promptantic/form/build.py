"""Build the form tree (:mod:`promptantic.form.nodes`) from a JSON Schema.

Covers JSON Schema 2020-12 as far as a form can use it: ``$ref`` (``$defs``,
JSON pointers, ``$anchor``, ``$id`` scopes, via :mod:`referencing`), ``allOf``
(merged), ``anyOf`` / ``oneOf`` (unions, or choices when every variant is a
constant), ``enum`` / ``const``, type lists, ``prefixItems`` (tuples),
``additionalProperties`` / ``patternProperties`` (free keys), and the ways
schemas say "or null" (``type: [..., "null"]``, a ``null`` variant, OpenAPI's
``nullable``). Keywords a form can't use (``if``/``then``/``else``, ``not``,
``contains``, ``dependentSchemas``) are left to validation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from schemez.jsonschema_utils import (
    JsonSchema,
    SchemaError,
    const_value,
    create_resolver,
    is_null_schema,
    merge_schemas,
    normalize_schema,
    schema_types,
)

from promptantic.form.nodes import (
    UNSET,
    AnyNode,
    ArrayNode,
    BooleanNode,
    Choice,
    ChoiceNode,
    Meta,
    NullNode,
    NumberNode,
    ObjectNode,
    Property,
    StringNode,
    TupleNode,
    UnionNode,
    Variant,
)


if TYPE_CHECKING:
    from referencing._core import Resolver

    from promptantic.form.nodes import FormNode


__all__ = ["SchemaError", "build_form"]

_STRING_KEYS = frozenset({"minLength", "maxLength", "pattern", "format", "contentMediaType"})
_NUMBER_KEYS = frozenset({
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
})
_OBJECT_KEYS = frozenset({"properties", "additionalProperties", "patternProperties", "required"})
_ARRAY_KEYS = frozenset({"items", "prefixItems", "minItems", "maxItems", "uniqueItems"})
# Keywords that describe the value itself (kept when a schema is split into variants)
_ANNOTATIONS = frozenset({
    "title",
    "description",
    "default",
    "examples",
    "readOnly",
    "writeOnly",
    "deprecated",
})


def build_form(schema: JsonSchema) -> FormNode:
    """The form tree for ``schema`` (nested parts are built on first access).

    Raises:
        SchemaError: The schema (or a ``$ref`` in it) can't be resolved.
    """
    return _node(schema, create_resolver(schema))


# --- nodes ---------------------------------------------------------------------------


def _meta(schema: Mapping[str, Any]) -> Meta:
    return Meta(
        title=schema.get("title"),
        description=schema.get("description"),
        default=schema.get("default", UNSET),
        examples=tuple(schema.get("examples", ())),
        # readOnly, or promptantic's skip_prompt (json_schema_extra): don't ask, keep the default
        read_only=bool(schema.get("readOnly", False) or schema.get("skip_prompt", False)),
        write_only=bool(schema.get("writeOnly", False)),
        deprecated=bool(schema.get("deprecated", False)),
        extensions={
            key.removeprefix("x-"): value for key, value in schema.items() if key.startswith("x-")
        },
    )


def _label(value: Any) -> str:
    return value if isinstance(value, str) else repr(value)


def _node(schema: JsonSchema, resolver: Resolver[Any]) -> FormNode:
    resolved, resolver = normalize_schema(schema, resolver)
    return _node_from(resolved, resolver)


def _node_from(s: dict[str, Any], resolver: Resolver[Any]) -> FormNode:  # noqa: PLR0911
    meta = _meta(s)
    types, nullable = schema_types(s)

    if "const" in s:
        if s["const"] is None:
            return NullNode(meta=meta)
        return ChoiceNode(
            meta=meta, nullable=nullable, choices=(Choice(s["const"], _label(s["const"])),)
        )

    if isinstance(enum := s.get("enum"), list):
        values = [value for value in enum if value is not None]
        names = s.get("x-enumNames") or s.get("enumNames")
        labels = (
            [str(name) for name in names]
            if isinstance(names, list) and len(names) == len(enum)
            else [_label(value) for value in enum]
        )
        label_of = dict(zip([repr(v) for v in enum], labels, strict=True))
        return ChoiceNode(
            meta=meta,
            nullable=nullable or len(values) < len(enum),
            choices=tuple(Choice(value, label_of[repr(value)]) for value in values),
        )

    for keyword in ("oneOf", "anyOf"):
        if isinstance(alternatives := s.get(keyword), list):
            return _alternatives(s, keyword, alternatives, meta, nullable, resolver)

    if is_null_schema(s):
        return NullNode(meta=meta)

    if len(types) > 1:
        return _type_union(s, types, meta, nullable, resolver)

    kind = types[0] if types else _infer_type(s)
    return _typed(kind, s, meta, nullable, resolver)


def _infer_type(s: Mapping[str, Any]) -> str | None:
    keys = s.keys()
    if keys & _OBJECT_KEYS:
        return "object"
    if keys & _ARRAY_KEYS:
        return "array"
    if keys & _STRING_KEYS:
        return "string"
    if keys & _NUMBER_KEYS:
        return "number"
    return None


def _typed(  # noqa: PLR0911
    kind: str | None,
    s: dict[str, Any],
    meta: Meta,
    nullable: bool,
    resolver: Resolver[Any],
) -> FormNode:
    match kind:
        case "string":
            return StringNode(
                meta=meta,
                nullable=nullable,
                format=s.get("format"),
                min_length=s.get("minLength"),
                max_length=s.get("maxLength"),
                pattern=s.get("pattern"),
                content_media_type=s.get("contentMediaType"),
            )
        case "integer" | "number":
            return NumberNode(
                meta=meta,
                nullable=nullable,
                integer=kind == "integer",
                minimum=s.get("minimum"),
                maximum=s.get("maximum"),
                exclusive_minimum=_exclusive(s, "exclusiveMinimum", "minimum"),
                exclusive_maximum=_exclusive(s, "exclusiveMaximum", "maximum"),
                multiple_of=s.get("multipleOf"),
            )
        case "boolean":
            return BooleanNode(meta=meta, nullable=nullable)
        case "null":
            return NullNode(meta=meta)
        case "array":
            return _array(s, meta, nullable, resolver)
        case "object":
            return _object(s, meta, nullable, resolver)
        case _:
            return AnyNode(meta=meta, nullable=nullable)


def _exclusive(s: Mapping[str, Any], keyword: str, legacy_bound: str) -> float | None:
    """2020-12 exclusive bounds are numbers; draft 4 used booleans next to min/max."""
    match s.get(keyword):
        case bool(flag):
            return s.get(legacy_bound) if flag else None
        case int() | float() as bound:
            return bound
        case _:
            return None


def _array(
    s: dict[str, Any], meta: Meta, nullable: bool, resolver: Resolver[Any]
) -> ArrayNode | TupleNode:
    if isinstance(prefix := s.get("prefixItems"), list):
        positions = list(prefix)
        return TupleNode(
            meta=meta,
            nullable=nullable,
            build_positions=lambda: tuple(_node(p, resolver) for p in positions),
        )
    items = s.get("items", True)
    if isinstance(items, list):  # draft 4-7 tuple form
        positions = list(items)
        return TupleNode(
            meta=meta,
            nullable=nullable,
            build_positions=lambda: tuple(_node(p, resolver) for p in positions),
        )
    return ArrayNode(
        meta=meta,
        nullable=nullable,
        min_items=s.get("minItems"),
        max_items=s.get("maxItems"),
        unique=bool(s.get("uniqueItems", False)),
        build_items=lambda: _node(items, resolver),
    )


def _object(s: dict[str, Any], meta: Meta, nullable: bool, resolver: Resolver[Any]) -> ObjectNode:
    properties: Mapping[str, JsonSchema] = s.get("properties", {})
    required = set(s.get("required", ()))
    additional = s.get("additionalProperties", UNSET)
    patterns: Mapping[str, JsonSchema] = s.get("patternProperties", {})
    match additional:
        case Mapping():
            extra: JsonSchema | None = cast("JsonSchema", additional)
        case True:
            extra = True
        case False:
            extra = None
        case _:  # absent: free keys only when nothing else is declared
            extra = next(iter(patterns.values())) if patterns else (None if properties else True)

    def build_properties() -> tuple[Property, ...]:
        return tuple(
            Property(
                name=name,
                node=_node(prop, resolver),
                required=name in required,
                title=prop.get("title") if isinstance(prop, Mapping) else None,
            )
            for name, prop in properties.items()
        )

    return ObjectNode(
        meta=meta,
        nullable=nullable,
        build_properties=build_properties if properties else None,
        build_additional=(lambda: _node(extra, resolver)) if extra is not None else None,
        min_properties=s.get("minProperties"),
        max_properties=s.get("maxProperties"),
    )


# --- unions --------------------------------------------------------------------------


def _alternatives(
    s: dict[str, Any],
    keyword: str,
    alternatives: list[JsonSchema],
    meta: Meta,
    nullable: bool,
    resolver: Resolver[Any],
) -> FormNode:
    """``anyOf`` / ``oneOf``: a choice, an "or null", or a real union."""
    base = {key: value for key, value in s.items() if key not in {"oneOf", "anyOf"}}
    structural = {k: v for k, v in base.items() if k not in _ANNOTATIONS and k != "discriminator"}
    variants: list[tuple[dict[str, Any], Resolver[Any], JsonSchema]] = []
    for alternative in alternatives:
        schema, variant_resolver = normalize_schema(alternative, resolver)
        if structural:
            schema = merge_schemas(
                schema, {k: v for k, v in structural.items() if not k.startswith("x-")}
            )
        if is_null_schema(schema):
            nullable = True
            continue
        variants.append((schema, variant_resolver, alternative))

    if len(variants) == 1:  # "X or null": the variant itself, with the outer labels
        schema, variant_resolver, _ = variants[0]
        merged = {**schema, **{k: v for k, v in base.items() if k in _ANNOTATIONS}}
        node = _node_from(merged, variant_resolver)
        return _with_nullable(node, nullable=True) if nullable else node

    consts = [const_value(schema) for schema, _, _ in variants]
    if variants and all(is_const for is_const, _ in consts):
        choices = tuple(
            Choice(value, schema.get("title") or _label(value))
            for (_, value), (schema, _, _) in zip(consts, variants, strict=True)
        )
        return ChoiceNode(meta=meta, nullable=nullable, choices=choices)

    discriminator = _discriminator(s, [schema for schema, _, _ in variants])
    mapping = _discriminator_mapping(s)

    def build_variants() -> tuple[Variant, ...]:
        return tuple(
            Variant(
                label=_variant_label(schema, raw, discriminator, mapping),
                node=_node_from(schema, variant_resolver),
            )
            for schema, variant_resolver, raw in variants
        )

    return UnionNode(
        meta=meta, nullable=nullable, build_variants=build_variants, discriminator=discriminator
    )


def _type_union(
    s: dict[str, Any], types: list[str], meta: Meta, nullable: bool, resolver: Resolver[Any]
) -> UnionNode:
    """``type: [a, b]``: a union with one variant per type, sharing the other keywords."""
    rest = {k: v for k, v in s.items() if k not in _ANNOTATIONS and k != "type"}

    def build_variants() -> tuple[Variant, ...]:
        return tuple(
            Variant(label=kind, node=_typed(kind, rest, Meta(), False, resolver)) for kind in types
        )

    return UnionNode(meta=meta, nullable=nullable, build_variants=build_variants)


def _with_nullable(node: FormNode, *, nullable: bool) -> FormNode:
    if isinstance(node, NullNode):
        return node
    return replace(node, nullable=nullable)


def _discriminator(s: Mapping[str, Any], variants: list[dict[str, Any]]) -> str | None:
    """The property telling variants apart: declared, or one that's a const in every variant."""
    match s.get("discriminator"):
        case {"propertyName": str(name)}:
            return name
        case str(name):
            return name
    candidates: set[str] | None = None
    for variant in variants:
        props = variant.get("properties", {})
        names = {
            name
            for name, prop in props.items()
            if isinstance(prop, Mapping) and const_value(prop)[0]
        }
        candidates = names if candidates is None else candidates & names
    return min(candidates) if candidates else None


def _discriminator_mapping(s: Mapping[str, Any]) -> dict[str, str]:
    """``$ref`` -> tag, from an OpenAPI discriminator's ``mapping``."""
    match s.get("discriminator"):
        case {"mapping": Mapping() as mapping}:
            return {str(ref): str(tag) for tag, ref in mapping.items()}
    return {}


def _variant_label(
    schema: Mapping[str, Any],
    raw: JsonSchema,
    discriminator: str | None,
    mapping: Mapping[str, str],
) -> str:
    if discriminator and isinstance(
        prop := schema.get("properties", {}).get(discriminator), Mapping
    ):
        is_const, value = const_value(prop)
        if is_const:
            return _label(value)
    ref = raw.get("$ref") if isinstance(raw, Mapping) else None
    if isinstance(ref, str) and ref in mapping:
        return mapping[ref]
    if title := schema.get("title"):
        return str(title)
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    types, _ = schema_types(schema)
    if types == ["array"] and isinstance(items := schema.get("items"), Mapping):
        item_types, _ = schema_types(items)
        return f"list of {item_types[0]}" if item_types else "list"
    return types[0] if types else (_infer_type(schema) or "value")
