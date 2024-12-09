"""Completers for various types."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import available_timezones

from prompt_toolkit.completion import CompleteEvent, Completer, Completion, PathCompleter


if TYPE_CHECKING:
    from collections.abc import Iterable

    from prompt_toolkit.document import Document


class TimezoneCompleter(Completer):
    """Completer for timezone names."""

    def __init__(self) -> None:
        self._timezones = list(available_timezones())

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Get timezone completions."""
        word = document.get_word_before_cursor()

        for tz in self._timezones:
            if tz.lower().startswith(word.lower()):
                yield Completion(
                    tz,
                    start_position=-len(word),
                    display_meta="timezone",
                )


class EnhancedPathCompleter(PathCompleter):
    """Enhanced path completer with better defaults."""

    def __init__(self) -> None:
        super().__init__(
            only_directories=False,
            min_input_len=0,
            get_paths=lambda: [str(Path.cwd())],
            expanduser=True,
            file_filter=None,
        )

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Get path completions with additional metadata."""
        path_text = document.text_before_cursor

        # Expand user directory
        path = Path(path_text)
        if path_text.startswith("~"):
            path = Path(path_text).expanduser()

        directory = path.parent
        prefix = path.name

        # Get all entries in the directory
        try:
            paths = list((directory or Path()).iterdir())
        except OSError:
            return

        # Filter and yield completions
        for entry_path in paths:
            if entry_path.name.startswith(prefix):
                full_path = directory / entry_path.name
                display = entry_path.name + ("/" if entry_path.is_dir() else "")
                meta = "dir" if entry_path.is_dir() else "file"

                yield Completion(
                    str(full_path),
                    start_position=-len(prefix) if prefix else 0,
                    display=display,
                    display_meta=meta,
                )


class FieldCompleter(Completer):
    """Completer for fields with custom completion values."""

    def __init__(self, values: list[str]) -> None:
        self.values = values

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Get completions from the predefined values."""
        word = document.get_word_before_cursor()

        for value in self.values:
            if value.lower().startswith(word.lower()):
                yield Completion(
                    value,
                    start_position=-len(word),
                )
