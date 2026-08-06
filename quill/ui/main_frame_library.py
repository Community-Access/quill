"""Book Library command mixin (plan xxx.md Part 4).

Opens the accessible :class:`~quill.ui.library_dialog.LibraryDialog`; a chosen
book is downloaded under the app data directory and opened in the editor through
the normal ``open_file`` flow (plain text and EPUB both open natively).
"""

from __future__ import annotations

import os

from quill.core import paths
from quill.ui.library_dialog import LibraryDialog


class LibraryMixin:
    """Adds the Book Library browser command to the main frame."""

    def open_library_dialog(self) -> None:
        dest = paths.app_data_dir() / "library"
        safe_mode = os.environ.get("QUILL_SAFE_MODE") == "1"
        dialog = LibraryDialog(
            self.frame,
            dest_dir=dest,
            announce=lambda text: self._announce(text),
            on_open=lambda path: self.open_file(path),
            safe_mode=safe_mode,
        )
        try:
            self._show_modal_dialog(dialog)
        finally:
            dialog.Destroy()
