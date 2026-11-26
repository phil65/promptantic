# AGENTS.md

## Overview

promptantic fills Pydantic v2 models (or any JSON Schema / Python type pydantic can
describe) interactively in the terminal. A schema becomes a UI-independent form tree,
rendered either as a Textual form below the prompt or as one prompt-toolkit prompt per
field; the finished value is validated by pydantic (types) or jsonschema (schemas).
`ModelCreator` goes the other way: the user designs a model as a `ModelSpec`, which becomes
a pydantic class. Used as a library by other projects (e.g. agentpool), so keep the public
API stable.

## Architecture

- `src/promptantic/__init__.py`: public API: `fill`, `target_for`, `FormTarget`,
  `FormCancelledError`, `FormValidationError`, `SchemaError`, `ModelGenerator`,
  `ModelCreator`, `ModelSpec`, `FieldSpec`, `PromptanticError`, `SKIP_PROMPT_KEY`.
- `src/promptantic/api.py`: `fill(target, title=, initial=, ui=)`: picks the renderer
  (`textual` when installed and stdin/stdout are TTYs, else `sequential`).
- `src/promptantic/form/`: the core, no UI.
  - `target.py`: `FormTarget[T]` (schema + `validate()`); `target_for()` for a JSON Schema
    (jsonschema Draft 2020-12, formats checked, gives a dict) or a Python type (pydantic
    `TypeAdapter`, gives an instance). Validation problems become `Issue`s (path +
    message) in a `FormValidationError`.
  - `build.py`: `build_form(schema)`: JSON Schema -> node tree (`$ref`s via `referencing`,
    `allOf` merged, `anyOf`/`oneOf` as unions or choices, nullable forms, `prefixItems`,
    `additionalProperties`/`patternProperties`). `readOnly` or `skip_prompt`
    (`json_schema_extra`) marks a field as not asked.
  - `nodes.py`: the node types (`StringNode`, `NumberNode`, `BooleanNode`, `ChoiceNode`,
    `ArrayNode`, `TupleNode`, `ObjectNode` with `properties` / `additional` / `is_map`,
    `UnionNode`, `NullNode`, `AnyNode`), `Meta`, and `UNSET` ("no value", unlike `None`).
    Nested parts are built lazily, so recursive schemas work.
  - `values.py`: `parse_text()` (input text -> value) and `field_errors()` (one field's
    own constraints, shown while typing).
- `src/promptantic/sequential.py`: `fill_sequential()`: walks the tree with one
  prompt-toolkit prompt per field (`_Asker`); lists/maps ask "Add ...?", unions and choices
  are numbered lists. After the last field the whole value is validated; on issues they
  are listed and the form is asked again with everything entered as the defaults.
- `src/promptantic/textual/`: `editors.py` (one `Editor` widget per node kind,
  `make_editor()`), `view.py` (`FormView` widget, `FormScreen` modal, `fill_inline()`
  inline app).
- `src/promptantic/generator.py`: `ModelGenerator`, the classic API as a thin wrapper
  around `fill` (constructor options are ignored). `apopulate(instance)` starts from the
  instance's values via `initial_values()` (secrets unmasked: `model_dump(mode="json")`
  would turn them into `"**********"`).
- `src/promptantic/model_spec.py`: `ModelSpec` / `FieldSpec` (a model described as data,
  itself filled with `fill`), `json_schema()` and `model_class()` (`create_model`).
  Validators reject bad defaults, field names with a leading underscore and duplicate
  names during the form, not in `model_class()`.
- `src/promptantic/creator.py`: `ModelCreator` (`acreate`, `acreate_instance`): fills a
  `ModelSpec`, builds the class.
- `src/promptantic/exceptions.py`: `PromptanticError` (and legacy subclasses).

## Where to look

| Task | File |
| --- | --- |
| Support a schema construct / type | `src/promptantic/form/build.py` (+ a node in `nodes.py`, editors in both renderers) |
| Input parsing, per-field checks | `src/promptantic/form/values.py` |
| Final validation, issue paths | `src/promptantic/form/target.py` |
| Prompt-per-field UI | `src/promptantic/sequential.py` |
| Textual UI | `src/promptantic/textual/` |
| Interactive model definition | `src/promptantic/model_spec.py`, `src/promptantic/creator.py` |
| Manual demo of many types | `scripts/test.py` (interactive) |
| Tests | `tests/form/` (tree, values), `tests/test_sequential.py`, `tests/textual/` (Textual pilot), `tests/test_model_spec.py` |

## Commands

```bash
uv sync --all-extras                 # setup (default groups: dev, lint, docs)
uv run pytest                        # tests (addopts deselect -m slow)
uvx ruff check . && uvx ruff format --check .
uv run ty check                      # type check (src only, warnings fail CI)
uv run deptry src                    # dependency check
uv run mknodes build                 # docs (also: uv run duty build / serve)
uv build
```

`duties.py` wraps these (`duty test`, `duty lint`, `duty lint_check`, `duty build`,
`duty serve`, `duty update`, `duty version`). Pre-commit hooks run ruff, tombi, ty and
pytest.

## Conventions

- Python >= 3.14, no `from __future__ import annotations` (PEP 649; banned via ruff TID251), Google docstrings, line length 100,
  ruff with preview formatting (Markdown code blocks in README are formatted too).
- `import datetime as dt` (ruff ICN001).
- Type checking is ty, not mypy: use `# ty: ignore[rule]` sparingly, no `# type: ignore`.
- Tests are async (`asyncio_mode = "auto"`). Sequential forms are driven with
  `prompt_toolkit.input.create_pipe_input()` + `PromptSession(input=pipe,
  output=DummyOutput())` passed as `fill_sequential(session=...)`; wrap them in
  `asyncio.wait_for` (input the form doesn't accept is asked again forever). Textual forms
  use `App.run_test()` / pilot.
- pytest config lives in the native `[tool.pytest]` table (pytest 9); markers:
  `slow`, `unit`, `integration`.

## Pitfalls

- Copier-managed project (`.copier-answers.yml`, template `copier-phil65`): workflows,
  `duties.py`, `.pre-commit-config.yaml`, `mkdocs.yml` and most of `pyproject.toml` come
  from the template. Add dependencies only below the `# Only add below (Copier)` markers.
- Docs use the mknodes default site: README.md is the index page, the API pages
  are generated; `docs/` is intentionally empty. Avoid self-imports such as
  `from promptantic import X` inside `promptantic/x.py` (griffe reports cyclic aliases
  and the docs build fails).
- Anything that prompts without a pipe input (or outside `run_test()`) hangs or fails in CI.
- `initial` values must be JSON-like (what the form shows and edits); build them from an
  instance with `promptantic.generator.initial_values()`, not `model_dump(mode="json")`.
