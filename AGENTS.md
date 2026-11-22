# AGENTS.md

## Overview

promptantic fills Pydantic v2 models interactively in the terminal. `ModelGenerator`
walks a model's fields and, for each field type, asks a type-specific handler to show a
prompt_toolkit prompt (with completion and validation). `ModelCreator` goes the other
way: it asks the user to define a new model class (field names, types, metadata). Used as
a library by other projects (e.g. agentpool), so keep the public API stable.

## Architecture

- `src/promptantic/__init__.py`: public API: `ModelGenerator`, `ModelCreator`,
  `PromptanticError`, `SKIP_PROMPT_KEY`.
- `src/promptantic/generator.py`: `ModelGenerator`. `_register_default_handlers()` maps
  types to handler instances; `get_handler(typ, field_info)` resolves a type (in this order:
  `Annotated` stripping, `None`, constrained str/int, `Literal`, unions, tuples, enums,
  models, email/url, `ImportString`, then lookup by `get_origin(typ)` or the type itself).
  `apopulate()` iterates `model_fields`, skips fields marked with `skip_prompt`, calls
  `handler.handle(...)`, retries on `promptantic.exceptions.ValidationError` and
  finally runs `model_validate`. `populate()` is the sync wrapper (`asyncio.run`).
- `src/promptantic/type_utils.py`: `TypeHandler` protocol plus `is_*_type` type guards,
  `strip_annotated`, `is_skip_prompt`.
- `src/promptantic/handlers/`: one module per type family. All handlers subclass
  `handlers/base.py:BaseHandler[T]` and implement
  `async handle(field_name, field_type, description, default, **options)`.
  `options` carries `field_info` (the pydantic `FieldInfo`) and `_test_mode`.
  - `primitives.py` (str/int/float/bool/Decimal/None), `constrained.py`, `literal.py`,
    `enums.py`, `unions.py` (radiolist dialog to pick a type), `models.py` (nested models,
    recursion into the generator), `sequences.py` (list/set/tuple/dict),
    `date_time.py`, `network.py` (ipaddress), `special.py` (SecretStr, Path/UPath, UUID,
    email, URL, ImportString, re.Pattern), `stdlib.py` (Fraction, ModuleType, Counter,
    deque, defaultdict).
- `src/promptantic/completers.py`: prompt_toolkit completers (timezones, paths, fixed
  values, import strings). `ImportStringCompleter` collects modules lazily on first use;
  keep it that way (eager loading imported every installed package in `ModelGenerator()`).
- `src/promptantic/creator.py`: `ModelCreator` (`acreate`, `acreate_instance`);
  `COMMON_TYPES` maps menu labels to types or type specs resolved by `_resolve_type_spec`.
- `src/promptantic/ui/`: `style.py` (`DEFAULT_STYLE`), `formatting.py`
  (`create_field_prompt`).
- `src/promptantic/exceptions.py`: `PromptanticError` > `ValidationError`,
  `TypeHandlerError` > `NoHandlerError`.

Per-field behaviour is configured through `json_schema_extra`: `skip_prompt`,
`completions` (str), `must_exist` / `file_only` / `dir_only` (paths), `email_pattern`,
`url_pattern`, `regex_flags`, `maxlen` (deque).

## Where to look

| Task | File |
| --- | --- |
| Support a new type | new handler in `src/promptantic/handlers/`, register in `generator.py:_register_default_handlers` (or special-case in `get_handler`) |
| Type detection bugs | `src/promptantic/type_utils.py`, `generator.py:get_handler` |
| Prompt look/feel | `src/promptantic/ui/`, `handlers/*` |
| Completion | `src/promptantic/completers.py` |
| Interactive model definition | `src/promptantic/creator.py` |
| Manual demo of all types | `scripts/test.py` (interactive) |
| Tests | `tests/test_generator.py`, `tests/test_handlers.py`, `tests/test_creator.py` |

## Commands

```bash
uv sync --all-extras                 # setup (default groups: dev, lint, docs)
uv run pytest                        # tests (addopts deselect -m slow)
uvx ruff check . && uvx ruff format --check .
uv run ty check                      # type check (src only, warnings fail CI)
uv run deptry src                    # dependency check
uv run mkdocs-mknodes build          # docs (also: uv run duty build / serve)
uv build
```

`duties.py` wraps these (`duty test`, `duty lint`, `duty lint_check`, `duty build`,
`duty serve`, `duty update`, `duty version`). Pre-commit hooks run ruff, tombi, ty and
pytest.

## Conventions

- Python >= 3.13, `from __future__ import annotations`, Google docstrings, line length 100,
  ruff with preview formatting (Markdown code blocks in README are formatted too).
- `import datetime as dt` (ruff ICN001).
- Type checking is ty, not mypy: use `# ty: ignore[rule]` sparingly, no `# type: ignore`.
- Tests are async (`asyncio_mode = "auto"`) and drive prompts via
  `prompt_toolkit.input.create_pipe_input()` + `create_app_session(input=..., output=DummyOutput())`.
  Dialogs (`radiolist_dialog`) are easiest to test by monkeypatching the module-level name.
  Pass `_test_mode=True` to `apopulate` so list input ends on an empty line.
- pytest config lives in the native `[tool.pytest]` table (pytest 9); markers:
  `slow`, `unit`, `integration`.

## Pitfalls

- Copier-managed project (`.copier-answers.yml`, template `copier-phil65`): workflows,
  `duties.py`, `.pre-commit-config.yaml`, `mkdocs.yml` and most of `pyproject.toml` come
  from the template. Add dependencies only below the `# Only add below (Copier)` markers.
- Docs use the mkdocs-mknodes default site: README.md is the index page, the API pages
  are generated; `docs/` is intentionally empty. Avoid self-imports such as
  `from promptantic import X` inside `promptantic/x.py` (griffe reports cyclic aliases
  and the docs build fails).
- `ModelGenerator(allow_back=...)` is stored but not used by any handler yet.
- Handlers need a terminal; anything that calls `prompt_async` without a pipe input
  hangs or fails in CI.
- Handlers are looked up by exact type (or `get_origin`), not by subclass: e.g. only
  `pathlib.Path` is registered, so `UPath` fields need `register_handler(UPath, ...)`.
