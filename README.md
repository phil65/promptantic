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

- One prompt per field, driven by the field's type, description and default
- Validation with retry on invalid input
- Autocompletion for paths, timezones, import strings and custom value lists
- Nested models, sequences and mappings
- Union types via a selection dialog
- Fields can be skipped (`skip_prompt`) and use their default
- Extensible: register your own handler for any type
- Customizable styling
- `ModelCreator`: define a new model class interactively

## Installation

```bash
pip install promptantic
```

## Quick Start

```python
from pydantic import BaseModel, Field

from promptantic import ModelGenerator


class Person(BaseModel):
    name: str = Field(description="Person's full name")
    age: int = Field(description="Age in years", gt=0)
    email: str = Field(description="Email address", pattern=r"[^@]+@[^@]+\.[^@]+")


generator = ModelGenerator()
person = generator.populate(Person)  # or: await generator.apopulate(Person)
print(person)
```

`populate` / `apopulate` accept a model class or an instance; values that were explicitly set
on an instance are offered as defaults.

## Supported Types

### Basic Types
- `str`, `int`, `float`, `bool`, `decimal.Decimal`, `fractions.Fraction`, `None`
- Constrained types (e.g., `constr`, `conint`)
- `Enum` classes
- `Literal` types

### Complex Types
- `list`, `set`, `tuple`, `dict` (with nested type support)
- `collections.Counter`, `deque`, `defaultdict`
- Union types (with interactive type selection)
- Nested Pydantic models

### Special Types
- `pathlib.Path` (with path autocompletion)
- `UUID`
- `SecretStr` (masked input)
- `datetime`, `date`, `time`, `timedelta`
- `ZoneInfo` (with timezone autocompletion)
- `IPv4Address`, `IPv6Address`, `IPv4Network`, `IPv6Network`
- `re.Pattern`
- `pydantic.ImportString` and `types.ModuleType` (with import path autocompletion)

## Advanced Usage

### Field options

Per-field behaviour is configured via `json_schema_extra`:

```python
from pathlib import Path

from pydantic import BaseModel, Field

from promptantic import SKIP_PROMPT_KEY


class Config(BaseModel):
    environment: str = Field(
        description="Select environment",
        json_schema_extra={"completions": ["development", "staging", "production"]},
    )
    config_path: Path = Field(
        description="Path to config file",
        json_schema_extra={"must_exist": True, "file_only": True},
    )
    internal_id: str = Field(default="auto", json_schema_extra={SKIP_PROMPT_KEY: True})
```

- `completions`: completion values for `str` fields
- `must_exist`, `file_only`, `dir_only`: path validation
- `skip_prompt` (`SKIP_PROMPT_KEY`): don't prompt, use the default / default factory

### Nested Models

```python
from pydantic import BaseModel, Field

from promptantic import ModelGenerator


class Address(BaseModel):
    street: str = Field(description="Street name")
    city: str = Field(description="City name")


class Person(BaseModel):
    name: str = Field(description="Full name")
    address: Address = Field(description="Person's address")


# Prompts for all fields recursively
person = ModelGenerator().populate(Person)
```

### Union Types

```python
from pydantic import BaseModel

from promptantic import ModelGenerator


class Student(BaseModel):
    student_id: int


class Teacher(BaseModel):
    teacher_id: str
    subject: str


class Person(BaseModel):
    name: str
    role: Student | Teacher  # Shows a selection dialog


person = ModelGenerator().populate(Person)
```

### Styling and options

```python
from prompt_toolkit.styles import Style

from promptantic import ModelGenerator


custom_style = Style.from_dict({
    "field-name": "bold #00aa00",
    "field-description": "italic #888888",
    "default-value": "#666666",
    "error": "bold #ff0000",
})

generator = ModelGenerator(
    style=custom_style,  # merged with the default style
    show_progress=True,  # print "Field i/n" before each field
    retry_on_validation_error=True,  # ask again instead of raising
)
```

### Custom type handlers

```python
from typing import Any

from prompt_toolkit import PromptSession

from promptantic import ModelGenerator
from promptantic.handlers.base import BaseHandler


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y


class PointHandler(BaseHandler[Point]):
    async def handle(
        self,
        field_name: str,
        field_type: type[Point],
        description: str | None = None,
        default: Any = None,
        **options: Any,
    ) -> Point:
        text = await PromptSession().prompt_async(f"{field_name} (x,y): ")
        x, y = text.split(",")
        return Point(float(x), float(y))


generator = ModelGenerator()
generator.register_handler(Point, PointHandler(generator))
```

### Creating models interactively

```python
import asyncio

from promptantic import ModelCreator


# Prompts for a model name, then fields (name, type, metadata) until Ctrl-D
model_cls = asyncio.run(ModelCreator().acreate())
instance = asyncio.run(ModelCreator().acreate_instance())  # create and populate
```

## Error Handling

```python
from promptantic import ModelGenerator, PromptanticError

try:
    result = ModelGenerator().populate(MyModel)
except KeyboardInterrupt:
    print("Operation cancelled by user")
except PromptanticError as e:  # e.g. NoHandlerError for unsupported field types
    print(f"Error: {e}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

Built with [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) and [Pydantic](https://github.com/pydantic/pydantic).
