"""Test script demonstrating all supported field types."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from enum import Enum
import ipaddress
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ImportString, SecretStr


# Test enums
class Role(Enum):
    """User roles."""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class Status(Enum):
    """User status."""

    ACTIVE = 1
    INACTIVE = 0
    PENDING = -1


# Nested model
class Address(BaseModel):
    """User address."""

    street: str
    city: str
    country: str
    # postal_code: constr(pattern=r"^\d{5}$")


# Main test model
class TestModel(BaseModel):
    """Test model with all supported field types."""

    # Basic types
    # string_field: str = Field(description="A simple string")
    # int_field: int = Field(description="A simple integer")
    # float_field: float = Field(description="A floating point number")
    # bool_field: bool = Field(description="A boolean value")
    # decimal_field: Decimal = Field(description="A decimal number")

    # Constrained types
    # username: constr(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    # age: conint(gt=0, lt=150, multiple_of=1)

    # Sequences
    # string_list: list[str] = Field(description="A list of strings")
    # int_set: set[int] = Field(description="A set of integers")
    coordinates: tuple[float, float]  #  = Field(description="Latitude and longitude")
    """Test description."""
    # Enums and Literals
    role: Role = Field(description="User role")
    status: Status = Field(description="User status")
    theme: Literal["light", "dark"] = Field(description="UI theme")
    priority: Literal[1, 2, 3] = Field(description="Priority level")

    # Date and Time
    birth_date: date = Field(description="Date of birth")
    last_login: datetime = Field(description="Last login timestamp")
    active_hours: time = Field(description="Active hours start time")
    session_timeout: timedelta = Field(description="Session timeout duration")
    timezone: ZoneInfo = Field(description="User timezone")

    # Network types
    ip_address: ipaddress.IPv4Address = Field(description="User IP address")
    network: ipaddress.IPv4Network = Field(description="Allowed network")

    # Special types
    password: SecretStr = Field(description="User password")
    avatar_path: Path = Field(description="Path to avatar image")

    # URLs and emails
    website: str = Field(description="Website URL", pattern=r"^https?://.*")
    email: str = Field(description="Email address", pattern=r"^[^@]+@[^@]+\.[^@]+$")

    # Nested model
    address: Address = Field(description="User address")
    import_path: ImportString = Field(description="Importable module path")

    model_config = ConfigDict(use_attribute_docstrings=True)


async def main() -> None:
    """Run the test script."""
    from promptantic import ModelGenerator

    generator = ModelGenerator(show_progress=True)

    print("Starting model population test...")
    print("Press Ctrl+C to skip a field or Ctrl+D to end list input")
    print("=" * 50)

    try:
        model = await generator.apopulate(TestModel)
        print("\nGenerated model:")
        print(model.model_dump_json(indent=2))
    except KeyboardInterrupt:
        print("\nTest cancelled!")
    except Exception as e:  # noqa: BLE001
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
