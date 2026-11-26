"""Design a pydantic model interactively: a form for a :class:`~promptantic.ModelSpec`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from promptantic.api import fill
from promptantic.model_spec import ModelSpec


if TYPE_CHECKING:
    from promptantic.generator import ModelGenerator


class ModelCreator:
    """Ask for a model's name and fields, and build the pydantic class."""

    async def acreate(
        self,
        model_name: str | None = None,
        base_classes: tuple[type[BaseModel], ...] = (BaseModel,),
    ) -> type[BaseModel]:
        """A new pydantic class, designed in a form.

        Raises:
            FormCancelledError: The user cancelled.
        """
        initial = {"name": model_name} if model_name else None
        spec = await fill(ModelSpec, title="New model", initial=initial)
        return spec.model_class(base=base_classes)

    async def acreate_instance(
        self,
        model_name: str | None = None,
        base_classes: tuple[type[BaseModel], ...] = (BaseModel,),
        populator: ModelGenerator | None = None,
    ) -> BaseModel:
        """Design a model, then fill an instance of it."""
        model: type[Any] = await self.acreate(model_name, base_classes)
        if populator is not None:
            return await populator.apopulate(model)
        return await fill(model)
