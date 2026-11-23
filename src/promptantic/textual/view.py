"""The form as a Textual widget, a modal screen, and a small inline app.

* :class:`FormView`: embed it in any Textual app; it posts :class:`FormView.Submitted`
  (with the validated result) or :class:`FormView.Cancelled`.
* :class:`FormScreen`: a modal around it that dismisses with the result (``None`` when
  cancelled), e.g. for an agent's elicitation in a chat app.
* :func:`fill_inline`: fill a form from a plain CLI; renders below the prompt.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from promptantic.form import (
    UNSET,
    FieldError,
    FormCancelledError,
    FormValidationError,
    build_form,
    target_for,
)
from promptantic.textual.editors import Editor, make_editor


if TYPE_CHECKING:
    from collections.abc import Mapping

    from textual.app import ComposeResult

    from promptantic.form import FormTarget
    from promptantic.form.target import Path


class FormView(Widget):
    """A form for a :class:`~promptantic.form.FormTarget`, validated on submit."""

    DEFAULT_CSS = """
    FormView { height: auto; }
    FormView > #pa-fields { height: auto; max-height: 70vh; }
    FormView .pa-field { margin: 0 0 1 0; }
    FormView > #pa-summary { color: $text-error; height: auto; }
    FormView > #pa-summary.-empty { display: none; }
    """

    class Submitted(Message):
        """The form validated; ``result`` is the dict or model instance."""

        def __init__(self, view: FormView, result: Any) -> None:
            super().__init__()
            self.view = view
            self.result = result

    class Cancelled(Message):
        """The form was closed without a result."""

        def __init__(self, view: FormView) -> None:
            super().__init__()
            self.view = view

    def __init__(
        self,
        target: FormTarget[Any],
        *,
        initial: Mapping[str, Any] | None = None,
        id: str | None = None,  # noqa: A002 (Textual widget convention)
    ) -> None:
        super().__init__(id=id)
        self.target = target
        self.root = build_form(target.schema)
        self.initial = dict(initial) if initial is not None else UNSET
        self._editors: dict[Path, Editor] = {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="pa-fields"):
            yield make_editor(self.root, (), self.initial, self._register)
        yield Static("", id="pa-summary", classes="-empty")

    def on_mount(self) -> None:
        self.call_after_refresh(self.focus_first)

    def focus_first(self) -> None:
        """Focus the first input, so typing goes straight into the form."""
        for widget in self.query_one("#pa-fields").query("*"):
            if widget.focusable:
                widget.focus()
                return

    def _register(self, path: Path, editor: Editor) -> None:
        self._editors[path] = editor

    def value(self) -> Any:
        """The value entered so far, unvalidated.

        Raises:
            FieldError: Some input can't become a value.
        """
        root = self.query_one("#pa-fields").query_children(Editor).first()
        value = root.get_value()
        return {} if value is UNSET else value

    def submit(self) -> None:
        """Validate; post :class:`Submitted`, or show the problems at their fields."""
        for editor in self._editors.values():
            if editor.is_attached:
                editor.show_errors([])
        try:
            value = self.value()
        except FieldError as exc:
            self._summary([str(exc)])
            return
        try:
            result = self.target.validate(value)
        except FormValidationError as exc:
            unplaced: list[str] = []
            for issue in exc.issues:
                if editor := self._editor_for(issue.path):
                    editor.show_errors([issue.message])
                else:
                    unplaced.append(issue.message)
            self._summary(unplaced or ["Please fix the marked fields"])
            return
        self._summary([])
        self.post_message(self.Submitted(self, result))

    def cancel(self) -> None:
        self.post_message(self.Cancelled(self))

    def _editor_for(self, path: Path) -> Editor | None:
        """The editor of the longest prefix of ``path`` that's on screen."""
        for end in range(len(path), 0, -1):
            editor = self._editors.get(path[:end])
            if editor is not None and editor.is_attached:
                return editor
        return None

    def _summary(self, messages: list[str]) -> None:
        summary = self.query_one("#pa-summary", Static)
        summary.update("\n".join(messages))
        summary.set_class(not messages, "-empty")


class FormPanel(Vertical):
    """A titled :class:`FormView` with Submit / Cancel buttons."""

    DEFAULT_CSS = """
    FormPanel { height: auto; }
    FormPanel > #pa-title { text-style: bold; margin: 0 0 1 0; }
    FormPanel > #pa-buttons { height: auto; margin: 1 0 0 0; }
    FormPanel > #pa-buttons Button { margin: 0 1 0 0; }
    """

    def __init__(
        self, target: FormTarget[Any], *, title: str | None, initial: Mapping[str, Any] | None
    ) -> None:
        super().__init__()
        self.form = FormView(target, initial=initial)
        self.title_text = title or target.title

    def compose(self) -> ComposeResult:
        if self.title_text:
            yield Label(self.title_text, id="pa-title")
        yield self.form
        with Horizontal(id="pa-buttons"):
            yield Button("Submit", variant="primary", id="pa-submit")
            yield Button("Cancel", id="pa-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "pa-submit":
            self.form.submit()
        elif event.button.id == "pa-cancel":
            self.form.cancel()


class FormScreen(ModalScreen[Any]):
    """A modal form; dismisses with the validated result, or ``None`` when cancelled."""

    DEFAULT_CSS = """
    FormScreen { align: center middle; }
    FormScreen > FormPanel {
        width: 90%; max-width: 110; max-height: 90%;
        border: thick $accent; background: $surface; padding: 0 1;
    }
    """
    BINDINGS: ClassVar = [
        Binding("ctrl+s", "submit", "Submit", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        target: FormTarget[Any] | type[Any] | Mapping[str, Any],
        *,
        title: str | None = None,
        initial: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.panel = FormPanel(_as_target(target), title=title, initial=initial)

    def compose(self) -> ComposeResult:
        yield self.panel

    def action_submit(self) -> None:
        self.panel.form.submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_form_view_submitted(self, event: FormView.Submitted) -> None:
        self.dismiss(event.result)

    def on_form_view_cancelled(self, _event: FormView.Cancelled) -> None:
        self.dismiss(None)


class FormApp(App[Any]):
    """A one-form app; :meth:`run_async` returns the result (``None``: cancelled)."""

    CSS = "Screen { height: auto; overflow: hidden; } FormPanel { padding: 0 1; }"
    BINDINGS: ClassVar = [
        Binding("ctrl+s", "submit", "Submit", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        target: FormTarget[Any],
        *,
        title: str | None = None,
        initial: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.panel = FormPanel(target, title=title, initial=initial)
        self.cancelled = False

    def compose(self) -> ComposeResult:
        yield self.panel

    def action_submit(self) -> None:
        self.panel.form.submit()

    def action_cancel(self) -> None:
        self.cancelled = True
        self.exit(None)

    def on_form_view_submitted(self, event: FormView.Submitted) -> None:
        self.exit(event.result)

    def on_form_view_cancelled(self, _event: FormView.Cancelled) -> None:
        self.action_cancel()


def _as_target(target: FormTarget[Any] | type[Any] | Mapping[str, Any]) -> FormTarget[Any]:
    from promptantic.form import FormTarget

    return target if isinstance(target, FormTarget) else target_for(target)


async def fill_inline(
    target: FormTarget[Any] | type[Any] | Mapping[str, Any],
    *,
    title: str | None = None,
    initial: Mapping[str, Any] | None = None,
) -> Any:
    """Show the form below the prompt and return the validated result.

    Raises:
        FormCancelledError: The user cancelled.
    """
    app = FormApp(_as_target(target), title=title, initial=initial)
    result = await app.run_async(inline=True)
    if app.cancelled:
        raise FormCancelledError
    return result
