"""#233: the braille status-bar cell builds a resolver and renders position."""

from __future__ import annotations

from quill.core.document import Document
from quill.ui.main_frame import MainFrame


class _Editor:
    def __init__(self, pos: int) -> None:
        self._pos = pos

    def GetCurrentPos(self) -> int:
        return self._pos


def _brf_metadata() -> dict:
    return {
        "source_kind": "brf",
        "brf_suffix": "brf",
        "brf_cell_width": 40,
        "brf_line_height": 25,
        "brf_non_ascii_offsets": [],
        "brf_had_bom": False,
        "brf_profile": "ueb_english",
    }


def _brf_frame(text: str, pos: int) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(text=text, source_metadata=_brf_metadata())
    frame.editor = _Editor(pos)  # type: ignore[attr-defined]
    return frame


def test_brf_document_renders_braille_cell() -> None:
    frame = _brf_frame("hello world\x0cpage two text\x0c", 3)
    cell = frame._statusbar_braille_text()
    assert cell.startswith("BRF Pg ")
    assert "Ln " in cell and "Cell " in cell


def test_non_brf_document_has_empty_braille_cell() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(text="plain text", source_metadata={"source_kind": "text"})
    frame.editor = _Editor(0)  # type: ignore[attr-defined]
    assert frame._statusbar_braille_text() == ""


def test_resolver_is_cached_per_document_and_length() -> None:
    frame = _brf_frame("abc\x0cdef\x0c", 1)
    first = frame._active_brf_resolver()
    second = frame._active_brf_resolver()
    assert first is second  # caret move reuses the cached resolver


def test_missing_editor_is_safe() -> None:
    frame = _brf_frame("abc\x0c", 0)
    frame.editor = None  # type: ignore[attr-defined]
    assert frame._statusbar_braille_text() == ""
