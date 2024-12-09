# Promptantic

An interactive CLI tool for populating Pydantic models using prompt-toolkit.

[![PyPI License](https://img.shields.io/pypi/l/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Package status](https://img.shields.io/pypi/status/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Daily downloads](https://img.shields.io/pypi/dd/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Weekly downloads](https://img.shields.io/pypi/dw/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Monthly downloads](https://img.shields.io/pypi/dm/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Distribution format](https://img.shields.io/pypi/format/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Wheel availability](https://img.shields.io/pypi/wheel/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Python version](https://img.shields.io/pypi/pyversions/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Implementation](https://img.shields.io/pypi/implementation/promptantic.svg)](https://pypi.org/project/promptantic/)
[![Releases](https://img.shields.io/github/downloads/phil65/promptantic/total.svg)](https://github.com/phil65/promptantic/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/promptantic)](https://github.com/phil65/promptantic/graphs/contributors)
[![Github Discussions](https://img.shields.io/github/discussions/phil65/promptantic)](https://github.com/phil65/promptantic/discussions)
[![Github Forks](https://img.shields.io/github/forks/phil65/promptantic)](https://github.com/phil65/promptantic/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/promptantic)](https://github.com/phil65/promptantic/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/promptantic)](https://github.com/phil65/promptantic/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/promptantic)](https://github.com/phil65/promptantic/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/promptantic)](https://github.com/phil65/promptantic/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/promptantic)](https://github.com/phil65/promptantic/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/promptantic)](https://github.com/phil65/promptantic/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Github commits this week](https://img.shields.io/github/commit-activity/w/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Github commits this year](https://img.shields.io/github/commit-activity/y/phil65/promptantic)](https://github.com/phil65/promptantic)
[![Package status](https://codecov.io/gh/phil65/promptantic/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/promptantic/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyUp](https://pyup.io/repos/github/phil65/promptantic/shield.svg)](https://pyup.io/repos/github/phil65/promptantic/)

[Read the documentation!](https://phil65.github.io/promptantic/)


## Features

- Interactive prompts for populating Pydantic models
- Rich formatting and syntax highlighting
- Type-aware input with validation
- Autocompletion for paths, timezones, and custom values
- Support for all common Python and Pydantic types
- Nested model support
- Union type handling via selection dialogs
- Sequence input (lists, sets, tuples)
- Customizable styling

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

# Create and use the generator
generator = ModelGenerator()
person = await generator.populate(Person)
print(person)
```

## Supported Types

### Basic Types
- `str`, `int`, `float`, `bool`, `decimal.Decimal`
- Constrained types (e.g., `constr`, `conint`)
- `Enum` classes
- `Literal` types

### Complex Types
- `list`, `set`, `tuple` (with nested type support)
- `Union` types (with interactive type selection)
- Nested Pydantic models

### Special Types
- `Path` (with path autocompletion)
- `UUID`
- `SecretStr` (masked input)
- `datetime`, `date`, `time`, `timedelta`
- `ZoneInfo` (with timezone autocompletion)
- `IPv4Address`, `IPv6Address`, `IPv4Network`, `IPv6Network`
- Email addresses (with validation)
- URLs (with validation)

## Advanced Usage

### Custom Completions

```python
from pydantic import BaseModel, Field
from pathlib import Path

class Config(BaseModel):
    environment: str = Field(
        description="Select environment",
        completions=["development", "staging", "production"]
    )
    config_path: Path = Field(description="Path to config file")  # Has path completion
```

### Nested Models

```python
class Address(BaseModel):
    street: str = Field(description="Street name")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")

class Person(BaseModel):
    name: str = Field(description="Full name")
    address: Address = Field(description="Person's address")

# Will prompt for all fields recursively
person = await ModelGenerator().populate(Person)
```

### Union Types

```python
class Student(BaseModel):
    student_id: int

class Teacher(BaseModel):
    teacher_id: str
    subject: str

class Person(BaseModel):
    name: str
    role: Student | Teacher  # Will show selection dialog

# Will prompt for type selection before filling fields
person = await ModelGenerator().populate(Person)
```

### Styling

```python
from prompt_toolkit.styles import Style
from promptantic import ModelGenerator

custom_style = Style.from_dict({
    "field-name": "bold #00aa00",  # Green bold
    "field-description": "italic #888888",  # Gray italic
    "error": "bold #ff0000",  # Red bold
})

generator = ModelGenerator(style=custom_style)
```

### Options

```python
generator = ModelGenerator(
    show_progress=True,        # Show field progress
    allow_back=True,          # Allow going back to previous fields
    retry_on_validation_error=True  # Retry on validation errors
)
```

## Error Handling

```python
from promptantic import ModelGenerator, PromptanticError

try:
    result = await ModelGenerator().populate(MyModel)
except KeyboardInterrupt:
    print("Operation cancelled by user")
except PromptanticError as e:
    print(f"Error: {e}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

Built with [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) and [Pydantic](https://github.com/pydantic/pydantic).
