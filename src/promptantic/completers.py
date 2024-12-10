"""Completers for various types."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
import sys
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


class ImportStringCompleter(Completer):
    """Completer for Python import strings."""

    def __init__(self) -> None:
        self._modules: set[str] = set()
        self._load_modules()

    def _load_modules(self) -> None:
        """Load available Python modules."""
        # Get all installed distributions
        for dist in metadata.distributions():
            try:
                # Add the distribution name
                name = dist.metadata["Name"]
                self._modules.add(name)

                # Try to import the main module to get submodules
                try:
                    from importlib import import_module

                    module = import_module(name)
                    self._modules.update(
                        f"{name}.{submod}"
                        for submod in dir(module)
                        if not submod.startswith("_")
                    )
                except ImportError:
                    pass

                # Add modules from distribution files
                if dist.files:
                    for file in dist.files:
                        if file.name.endswith(".py"):
                            module_path = str(file.parent).replace("/", ".")
                            if module_path and not module_path.startswith("_"):
                                self._modules.add(module_path)
            except Exception:  # noqa: BLE001
                continue

        # Add modules from sys.modules that might not be from distributions
        self._modules.update(
            name
            for name in sys.modules
            if not name.startswith("_") and "." not in name  # only top-level modules
        )

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Get import path completions."""
        word = document.get_word_before_cursor()
        parts = word.split(".")

        # Handle module path vs attribute path differently
        if ":" in word:
            module_path, attr_path = word.split(":", 1)
            # If we're completing attributes, try to get them from the module
            try:
                # Only attempt if we have a complete module path
                from importlib import import_module

                module = import_module(module_path)
                attrs = [name for name in dir(module) if not name.startswith("_")]
                current = attr_path.split(".")[-1]
                for attr in attrs:
                    if attr.startswith(current):
                        full_path = f"{module_path}:{attr_path[: -len(current)]}{attr}"
                        yield Completion(
                            full_path,
                            start_position=-len(word),
                            display_meta="attribute",
                        )
            except ImportError:
                pass
            else:
                return

        # Module path completion
        current = parts[-1] if parts else ""
        prefix = ".".join(parts[:-1])

        for module_name in self._modules:
            if module_name.lower().startswith(current.lower()):
                full_path = f"{prefix}.{module_name}" if prefix else module_name
                yield Completion(
                    full_path,
                    start_position=-len(word),
                    display_meta="module",
                )
