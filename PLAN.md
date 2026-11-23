# Plan: JSON Schema forms

Status: done (2026-11-23): 2.0 has only the schema-based forms; acptui and agentpool use them.

Done: `promptantic.form` (core), `promptantic.textual` (FormView / FormScreen / fill_inline),
`promptantic.sequential` (fallback), `promptantic.fill()`. Generic JSON Schema helpers went to
`schemez.jsonschema_utils` (schemez 2.4.0). Decisions on the open questions below: `fill()` is
the new API and `ModelGenerator` stays as the classic API for now; `ModelCreator` stays until the
switch-over; unions use a variant select first.

Goal: promptantic becomes an automatic UI for JSON Schema. Pydantic models are one source of
schemas, not the core. The same engine serves agentpool's structured input and MCP
elicitation.

## Where it stands

- **Driven by Python types.** About 30 handlers in a dict keyed by type (`str`, `Path`,
  `ZoneInfo`, `IPv4Address`, `Counter`, `ModuleType`, ...), dispatched in `generator.py`.
  JSON Schema input (e.g. MCP elicitation, a flat restricted schema) can't be handled, so
  agentpool's `ui/stdlib_provider.get_elicitation` uses plain `input()` instead.
- **Logic and presentation are mixed.** Handlers call `print()` and open prompt-toolkit sessions
  themselves; nested models show a print-built menu ("1. Use default values ..."). Another
  frontend means rewriting every handler.
- **One-way wizard.** One field after another: no overview, no going back, validation errors only
  at the end.
- **Niche handlers** (`ModuleType`, `Counter`, `deque`, `defaultdict`, `Fraction`, ...) that no
  form will realistically ask for. 8 tests.
- **Users:** agentpool (`ui/stdlib_provider.get_structured_input`, `agentpool_cli/agent.py`),
  llmling (`cli/config.py`).

## Design

### 1. JSON Schema in, form tree as the core

- Input is a JSON Schema. For Pydantic models: `model_json_schema()`, with the final validation
  through the model.
- From the schema, build a **form tree**: field nodes with kind (`string`, `number`, `integer`,
  `boolean`, `array`, `object`, enum, union via `anyOf` / `oneOf`), constraints (`minLength`,
  `maxLength`, `pattern`, `minimum`, `maximum`, `minItems`, ...), default, title,
  description, `format`. `$ref` / `$defs` are resolved when building the tree.
- **Widgets are chosen by schema type plus `format`** (`date`, `time`, `date-time`,
  `duration`, `email`, `uri`, `uuid`, `ipv4`, `ipv6`, `password` / `writeOnly` for secrets), not by
  Python type.
- **Extras come from `x-` keys**: `x-completions` (fixed suggestions, replacing the
  `completions=` field extra), `x-path` (path completion), `x-timezone`. Pydantic models set
  them via `json_schema_extra`.
- **MCP elicitation is a special case**: its schema is a flat object of primitives, so it
  needs no extra code.
- The niche Python-type handlers either become a `format` / `x-` mapping or are dropped.

### 2. Form model and renderer separated

- A `FormRenderer` protocol: gets the form tree (plus current values / errors), returns values.
  Renderers don't validate and don't know about Pydantic.
- **Validation is shared:** per field from schema constraints while typing, then a final model
  (or JSON Schema) validation; on failure, only the failing fields are asked again, with the
  error shown next to them.
- Result: a plain dict for schemas, a model instance for Pydantic sources.

### 3. Renderers

- **Textual, inline mode (main).** `App.run(inline=True)` renders below the prompt without
  taking over the screen, which suits agent CLIs. All fields visible, Tab navigation, inline
  errors, nested objects as collapsible sections, unions as a type selector, arrays as
  add/remove lists. The widgets could live in textualicious.
- **prompt-toolkit, sequential (fallback).** For non-interactive terminals, SSH, minimal
  setups: today's behaviour, without the print menus. Union / enum selection as a choice
  prompt, nested objects recursively.
- Not questionary / InquirerPy: nicer single questions, but the same one-way wizard.

## Steps

1. **Form tree + engine**, with the prompt-toolkit renderer ported (same behaviour as today).
   Tests for the schema → tree conversion (Pydantic models, `$ref`, unions, MCP elicitation
   schemas) and for the renderer via prompt-toolkit's pipe input.
2. **Textual inline renderer**, with snapshot tests (Textual pilot / pytest-textual-snapshot).
3. **agentpool**: `get_structured_input` and `get_elicitation` in the stdlib provider both use
   the engine; elicitation passes its schema directly.
4. Remove the old type-handler registry once agentpool and llmling are switched over.

## Open questions

- Keep `ModelGenerator.apopulate(Model)` as the public entry point (as a thin wrapper over the
  schema engine), or a new API (`fill(schema)` / `fill(Model)`)? agentpool and llmling only
  use `ModelGenerator().apopulate(...)`.
- `ModelCreator` (interactive creation of Pydantic models) doesn't fit the schema core. Drop it,
  or keep it as a separate module?
- Union handling in inline forms: type selector first, or try to infer the variant from what's
  typed?
