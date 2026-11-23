"""``fill()``: one call to get a value from the user, whatever the terminal can do."""

from __future__ import annotations

import importlib.util
import sys
from typing import TYPE_CHECKING, Any, Literal, overload

from promptantic.form import FormTarget, target_for


if TYPE_CHECKING:
    from collections.abc import Mapping


type UI = Literal["auto", "textual", "sequential"]


@overload
async def fill[T](
    target: type[T] | FormTarget[T],
    *,
    title: str | None = None,
    initial: Mapping[str, Any] | None = None,
    ui: UI = "auto",
) -> T: ...
@overload
async def fill(
    target: Mapping[str, Any],
    *,
    title: str | None = None,
    initial: Mapping[str, Any] | None = None,
    ui: UI = "auto",
) -> dict[str, Any]: ...
async def fill(
    target: type[Any] | FormTarget[Any] | Mapping[str, Any],
    *,
    title: str | None = None,
    initial: Mapping[str, Any] | None = None,
    ui: UI = "auto",
) -> Any:
    """Ask the user to fill a form and return the validated result.

    Args:
        target: A JSON Schema (gives a dict), or a Python type such as a pydantic
            model or dataclass (gives an instance).
        title: Heading of the form (default: the schema's title).
        initial: Starting values (default: the schema's defaults).
        ui: ``textual`` (a form below the prompt), ``sequential`` (one prompt per field),
            or ``auto``: textual when it's installed and the terminal is interactive.

    Raises:
        FormCancelledError: The user cancelled.
    """
    form_target = target if isinstance(target, FormTarget) else target_for(target)
    if ui == "auto":
        ui = "textual" if _textual_usable() else "sequential"
    if ui == "textual":
        from promptantic.textual import fill_inline

        return await fill_inline(form_target, title=title, initial=initial)
    from promptantic.sequential import fill_sequential

    return await fill_sequential(form_target, title=title, initial=initial)


def _textual_usable() -> bool:
    if importlib.util.find_spec("textual") is None:
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()
