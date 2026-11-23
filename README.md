# Promptantic

Fill Pydantic models interactively in the terminal. promptantic walks a model's fields and
shows a type-aware [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
prompt for each one, with completion, validation and retry.

[![PyPI License](https://img.shields.io/pypi/l/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Package status](https://img.shields.io/pypi/status/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Monthly downloads](https://img.shields.io/pypi/dm/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Distribution format](https://img.shields.io/pypi/format/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Wheel availability](https://img.shields.io/pypi/wheel/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Python version](https://img.shields.io/pypi/pyversions/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Implementation](https://img.shields.io/pypi/implementation/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Releases](https://img.shields.io/github/downloads/phil65/promptantic/total.svg)](https://github.com/phil65/promptantic/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/promptantic)](https://github.com/phil65/promptantic/graphs/contributors)
[![Github Forks](https://img.shields.io/github/forks/phil65/promptantic)](https://github.com/phil65/promptantic/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/promptantic)](https://github.com/phil65/promptantic/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/promptantic)](https://github.com/phil65/promptantic/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/promptantic)](https://github.com/phil65/promptantic/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/promptantic)](https://github.com/phil65/promptantic/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/promptantic)](https://github.com/phil65/promptantic/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/promptantic)](https://github.com/phil65/promptantic/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Package status](https://codecov.io/gh/phil65/promptantic/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/promptantic/)

[Read the documentation!](https://phil65.github.io/promptantic/)

## Features

- Forms from **any JSON Schema** (2020-12: `$ref` with `$defs`, pointers, `$anchor` and
  `$id`, `allOf`, `anyOf` / `oneOf`, `enum` / `const`, type lists, `prefixItems`,
  `additionalProperties`, formats, numeric and length constraints), or from a **Python
  type**: pydantic models, dataclasses, TypedDicts, `list[...]`, ...
- A **Textual** form (all fields at once, folding sections, live checks, errors at their
  fields) that renders below the prompt, or embeds into any Textual app
- A **one-prompt-per-field** fallback (prompt-toolkit) for terminals without a full TUI
- One UI-independent core (`promptantic.form`) both renderers share; validation with
  `jsonschema` for schemas and pydantic for types (which also gives you an instance)

## Installation

```bash
pip install promptantic            # core + one-prompt-per-field
pip install "promptantic[textual]" # + the Textual form
```

## Quick Start

```python
from pydantic import BaseModel, Field
from promptantic import fill


class Order(BaseModel):
    customer: str = Field(min_length=1, description="Who ordered")
    quantity: int = Field(default=1, ge=1)
    express: bool = False


order = await fill(Order)  # an Order instance

# A JSON Schema gives a dict
answer = await fill({
    "type": "object",
    "properties": {"name": {"type": "string"}, "count": {"type": "integer", "default": 2}},
    "required": ["name"],
})
```

`fill()` uses the Textual form when it's installed and the terminal is interactive, else one
prompt per field (`ui="textual"` / `ui="sequential"` to choose). It raises
`FormCancelledError` when the user cancels.

### In a Textual app

```python
from promptantic.textual import FormScreen, FormView

# A modal that dismisses with the validated result (None when cancelled)
self.push_screen(FormScreen(Order, initial={"customer": "Ada"}), on_result)

# Or embed the form and handle FormView.Submitted / FormView.Cancelled yourself
yield FormView(target_for(schema))
```

### The core

```python
from promptantic.form import build_form, field_errors, target_for

target = target_for(Order)  # schema + validation (also for plain JSON Schemas)
root = build_form(target.schema)  # the form tree: ObjectNode, StringNode, UnionNode, ...
result = target.validate(value)  # FormValidationError lists every issue with its path
```

Nested parts of the tree are built on first access, so recursive schemas work. Generic
JSON Schema helpers (`$ref` resolution, `allOf` merging, type and constant detection) live in
[schemez](https://github.com/phil65/schemez) (`schemez.jsonschema_utils`).

### Designing a model

`ModelSpec` describes a model as data (name, fields with type, default, description; nested
objects), so it's filled with the same forms. The result becomes a JSON Schema or a class:

```python
from promptantic import ModelCreator, ModelSpec, fill

spec = await fill(ModelSpec)  # name, description, fields...
Book = spec.model_class()  # a pydantic class (pydantic.create_model)
schema = spec.json_schema()

Book = await ModelCreator().acreate("Book")  # the same in one call
```

### Skipping fields

Fields with `json_schema_extra={promptantic.SKIP_PROMPT_KEY: True}` (or `readOnly` in a
JSON Schema) aren't asked; they keep their default.

## Upgrading from 1.x

`ModelGenerator().apopulate(Model)` / `.populate(Model)` still work, as a thin wrapper
around `fill()` (an instance as argument gives the starting values). The prompt-per-type
implementation behind it is gone in 2.0, with its options (`style`, `show_progress`, ...,
accepted and ignored) and custom type handlers: a field's JSON Schema (`format`, `enum`,
constraints, `x-` keys) is what shapes its input now.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

Built with [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) and [Pydantic](https://github.com/pydantic/pydantic).
