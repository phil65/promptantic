"""``ModelGenerator``: the classic API, now a thin wrapper around :func:`promptantic.fill`."""

from __future__ import annotations

import asyncio
from typing import Any, overload

from pydantic import BaseModel, SecretBytes, SecretStr
from pydantic_core import to_jsonable_python

from promptantic.api import fill


def initial_values(model: BaseModel) -> dict[str, Any]:
    """The instance's values as form starting values, with secrets unmasked.

    ``model_dump(mode="json")`` masks ``SecretStr`` / ``SecretBytes`` as
    ``"**********"``; accepting such a default would replace the real secret. The
    forms show secret fields masked anyway.
    """
    return to_jsonable_python(_unmask(model.model_dump()))


def _unmask(value: Any) -> Any:
    match value:
        case SecretStr() | SecretBytes():
            return value.get_secret_value()
        case dict():
            return {k: _unmask(v) for k, v in value.items()}
        case list() | tuple() | set() | frozenset():
            return type(value)(_unmask(v) for v in value)
        case _:
            return value


class ModelGenerator:
    """Fill a pydantic model interactively; prefer :func:`promptantic.fill`.

    The constructor's options (``style``, ``show_progress``, ...) belonged to the old
    prompt-per-type implementation and are accepted but ignored.
    """

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    @overload
    async def apopulate[M: BaseModel](self, model: type[M]) -> M: ...
    @overload
    async def apopulate[M: BaseModel](self, model: M) -> M: ...
    async def apopulate[M: BaseModel](self, model: type[M] | M) -> M:
        """An instance of ``model``; given an instance, its values are the starting values."""
        if isinstance(model, BaseModel):
            return await fill(type(model), initial=initial_values(model))
        return await fill(model)

    @overload
    def populate[M: BaseModel](self, model: type[M]) -> M: ...
    @overload
    def populate[M: BaseModel](self, model: M) -> M: ...
    def populate[M: BaseModel](self, model: type[M] | M) -> M:
        """Like :meth:`apopulate`, for code that isn't async."""
        return asyncio.run(self.apopulate(model))
