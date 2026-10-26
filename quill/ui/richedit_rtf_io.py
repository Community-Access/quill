"""RTF in and out of the rich surface, with tables real in the editor.

Extracted from :mod:`quill.ui.richedit_rtf_surface` under GATE-11 when rich text
gained real tables (2026-10-25). Every path is the Text Object Model's
``ITextDocument::Open`` / ``::Save`` against a file -- never a stream callback,
which crashes msftedit (see that module's docstring).

**Tables.** In the editor a table is RichEdit's own; everywhere else QUILL hands
tables around as Markdown pipe rows. :mod:`quill.io.rtf_tables` bridges the two:

* :meth:`load_rtf` (and :meth:`set_rtf`, which goes through it) turns pipe rows
  into real tables -- a Word document's tables arrive as pipe rows, and so does a
  Markdown document switched to rich text;
* :meth:`save_rtf` writes real tables, each first row marked as its header row
  (RichEdit drops that mark, and Word reads it);
* :meth:`get_rtf` hands out pipe rows, because what reads it -- Save as Word,
  the switch to Markdown or plain text -- reads tables in that form.

The host provides ``hwnd()``.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

__all__ = ["RtfIoMixin"]


class RtfIoMixin:
    """``load_rtf`` / ``save_rtf`` / ``get_rtf`` / ``set_rtf`` for a QuillRichEdit."""

    hwnd: Any

    def load_rtf(self, path: str) -> None:
        """Load an RTF file via ``ITextDocument::Open``, pipe rows as real tables."""
        from quill.io.rtf_tables import pipe_rows_as_tables
        from quill.ui import richedit_rtf_surface as surface

        itd = surface._get_text_document(self.hwnd())
        with pipe_rows_as_tables(str(path)) as readable:
            try:
                itd.Open(readable, surface._TOM_OPEN_EXISTING | surface._TOM_RTF, 0)
            except Exception as exc:  # noqa: BLE001 - map COM/file errors to our type
                raise surface.RichEditRtfError(f"Could not open RTF file: {exc}") from exc

    def _save_tom(self, path: str) -> None:
        """``ITextDocument::Save`` to *path*, exactly as the control holds it."""
        from quill.io.rtf_heading_promotion import promote_heading_styles_in_file
        from quill.ui import richedit_rtf_surface as surface

        itd = surface._get_text_document(self.hwnd())
        try:
            itd.Save(str(path), surface._TOM_CREATE_ALWAYS | surface._TOM_RTF, 0)
        except Exception as exc:  # noqa: BLE001
            raise surface.RichEditRtfError(f"Could not save RTF file: {exc}") from exc
        promote_heading_styles_in_file(str(path))

    def save_rtf(self, path: str) -> None:
        """Save to an RTF file: real tables, each first row marked as its header."""
        from quill.io.rtf_tables import mark_header_rows_in_file
        from quill.ui import richedit_rtf_surface as surface

        self._save_tom(path)
        try:
            mark_header_rows_in_file(path)
        except OSError as exc:
            raise surface.RichEditRtfError(f"Could not mark the table headers: {exc}") from exc

    def get_rtf(self) -> bytes:
        """The document as RTF bytes, tables as pipe rows (see the module doc)."""
        from quill.io.rtf_tables import tables_to_pipe_rows_bytes
        from quill.ui import richedit_rtf_surface as surface

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quill.rtf")
            self._save_tom(path)
            try:
                with open(path, "rb") as handle:
                    return tables_to_pipe_rows_bytes(handle.read())
            except OSError as exc:
                raise surface.RichEditRtfError(f"Could not read the saved RTF: {exc}") from exc

    def set_rtf(self, data: bytes) -> None:
        """Replace the document with RTF bytes (TOM Open from a temp file)."""
        from quill.ui import richedit_rtf_surface as surface

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quill.rtf")
            try:
                with open(path, "wb") as handle:
                    handle.write(data)
            except OSError as exc:
                raise surface.RichEditRtfError(f"Could not stage RTF for loading: {exc}") from exc
            self.load_rtf(path)
