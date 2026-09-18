"""The status bar stops answering for a document that has no answer (F7, P2.8).

``self.encoding`` and ``self.newline`` are only ever set by the *plain* load
path, so opening a ``.rtf`` left them at the window's birth defaults and the
Encoding and Line Endings cells read "UTF-8" and "CRLF" for every rich document
-- confidently, and wrongly, about a file that has neither.

Being read a fact about your file that is not true of it is worse than the cell
not existing: File Encoding and Line Endings already refuses in rich mode, so
the status bar was the last place still claiming it.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps.lite_window_status import (
    RICH_ENCODING_CELL,
    RICH_LINE_ENDINGS_CELL,
    DocumentStatusMixin,
)
from quill.ui.richedit_editing import PLAIN, RICH


class _Window:
    _encoding_cell = DocumentStatusMixin._encoding_cell
    _line_endings_cell = DocumentStatusMixin._line_endings_cell

    def __init__(self, mode: str, *, encoding: str = "utf-8", newline: str = "\r\n") -> None:
        self.editor = SimpleNamespace(mode=mode)
        self.encoding = encoding
        self.newline = newline


def test_a_rich_document_says_it_has_no_text_encoding() -> None:
    window = _Window(RICH)
    assert window._encoding_cell() == RICH_ENCODING_CELL
    assert window._line_endings_cell() == RICH_LINE_ENDINGS_CELL


def test_a_plain_document_still_reports_its_own_format() -> None:
    window = _Window(PLAIN, encoding="cp1252", newline="\n")
    assert window._encoding_cell() == "Windows-1252 (ANSI)"
    assert window._line_endings_cell() == "LF (Unix, macOS, most build tools)"


def test_the_rich_cells_never_name_a_codec() -> None:
    """The point of the fix: no UTF-8, no CRLF, for a file that has neither."""
    assert "UTF-8" not in RICH_ENCODING_CELL
    assert "CRLF" not in RICH_LINE_ENDINGS_CELL
    assert "rich text" in RICH_ENCODING_CELL
