"""Textual renderer (``pip install promptantic[textual]``).

Embed :class:`FormView` or :class:`FormScreen` in a Textual app, or call
:func:`fill_inline` from a plain CLI.
"""

from promptantic.textual.editors import Editor, make_editor
from promptantic.textual.view import (
    FormApp,
    FormCancelledError,
    FormPanel,
    FormScreen,
    FormView,
    fill_inline,
)


__all__ = [
    "Editor",
    "FormApp",
    "FormCancelledError",
    "FormPanel",
    "FormScreen",
    "FormView",
    "fill_inline",
    "make_editor",
]
