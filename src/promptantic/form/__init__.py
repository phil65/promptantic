"""The UI-independent core: JSON Schema -> form tree -> values -> validation.

Renderers (Textual, prompt-toolkit) build their widgets from the tree of
:func:`build_form`, check fields with :func:`field_errors` while the user types,
and hand the finished value to :meth:`FormTarget.validate`.
"""

from promptantic.form.build import SchemaError, build_form
from promptantic.form.nodes import (
    UNSET,
    AnyNode,
    ArrayNode,
    BooleanNode,
    Choice,
    ChoiceNode,
    FormNode,
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
from promptantic.form.target import (
    FormCancelledError,
    FormTarget,
    FormValidationError,
    Issue,
    target_for,
)
from promptantic.form.values import FieldError, field_errors, initial_value, parse_text


__all__ = [
    "UNSET",
    "AnyNode",
    "ArrayNode",
    "BooleanNode",
    "Choice",
    "ChoiceNode",
    "FieldError",
    "FormCancelledError",
    "FormNode",
    "FormTarget",
    "FormValidationError",
    "Issue",
    "Meta",
    "NullNode",
    "NumberNode",
    "ObjectNode",
    "Property",
    "SchemaError",
    "StringNode",
    "TupleNode",
    "UnionNode",
    "Variant",
    "build_form",
    "field_errors",
    "initial_value",
    "parse_text",
    "target_for",
]
