"""BR-016/#239: the braille mixin restores the caret and announces on open."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.brf_sidecar import BRFSidecar, SidecarPosition, write_sidecar
from quill.ui.main_frame_braille import BrailleCommandsMixin


class _FakeEditor:
    def __init__(self) -> None:
        self.insertion: int | None = None
        self.selection: tuple[int, int] | None = None

    def SetInsertionPoint(self, offset: int) -> None:
        self.insertion = offset

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)


class _FakePosition:
    page_count = 87
    page = 12
    line = 14
    cell = 31


class _Host(BrailleCommandsMixin):
    def __init__(self, *, safe_mode: bool, editor: _FakeEditor, resolved: object) -> None:
        self.settings = SimpleNamespace(braille_save_sidecar=True)
        self._safe_mode = safe_mode
        self.editor = editor
        self._resolved = resolved

    def _braille_position(self) -> object:  # override the mixin helper
        return self._resolved


def _brf_doc(text_len: int = 5000) -> SimpleNamespace:
    return SimpleNamespace(
        source_metadata={"source_kind": "brf"}, name="notes.brf", text="x" * text_len
    )


def test_restores_caret_and_announces_position(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    write_sidecar(brf, BRFSidecar(position=SidecarPosition(last_offset=1234, print_page="7")))
    editor = _FakeEditor()
    host = _Host(safe_mode=False, editor=editor, resolved=(object(), _FakePosition()))

    message = host._brf_open_message(_brf_doc(), brf)

    assert editor.insertion == 1234
    assert editor.selection == (1234, 1234)
    assert message == (
        "BRF file opened. 87 braille pages detected. "
        "Last position: braille page 12, line 14, cell 31, print page 7."
    )


def test_safe_mode_skips_restore(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    write_sidecar(brf, BRFSidecar(position=SidecarPosition(last_offset=1234, print_page="7")))
    editor = _FakeEditor()
    host = _Host(safe_mode=True, editor=editor, resolved=(object(), _FakePosition()))

    message = host._brf_open_message(_brf_doc(), brf)

    assert editor.insertion is None  # caret not moved in safe mode
    assert message == "BRF file opened. 87 braille pages detected."


def test_no_sidecar_announces_without_position(tmp_path: Path) -> None:
    brf = tmp_path / "fresh.brf"
    editor = _FakeEditor()
    host = _Host(safe_mode=False, editor=editor, resolved=(object(), _FakePosition()))

    message = host._brf_open_message(_brf_doc(), brf)

    assert editor.insertion is None
    assert message == "BRF file opened. 87 braille pages detected."


def test_non_braille_document_uses_generic_message(tmp_path: Path) -> None:
    editor = _FakeEditor()
    host = _Host(safe_mode=False, editor=editor, resolved=None)
    doc = SimpleNamespace(source_metadata={"source_kind": "text"}, name="memo.txt", text="hello")

    message = host._brf_open_message(doc, tmp_path / "memo.txt")

    assert editor.insertion is None
    assert message == "Opened memo.txt"
