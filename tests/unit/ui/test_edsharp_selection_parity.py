from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.a11y_regions import RegionTracker
from quill.core.document import Document
from quill.core.locations import LocationRing
from quill.platform.sr_announce import (
    clear_transcript,
    enable_transcript_capture,
    transcript_entries,
)
from quill.ui.main_frame import MainFrame


@pytest.fixture(autouse=True)
def _isolated_quill_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


@pytest.fixture(autouse=True)
def _announce_transcript() -> None:
    enable_transcript_capture(True)
    clear_transcript()
    yield
    enable_transcript_capture(False)
    clear_transcript()


class _Editor:
    def __init__(self, text: str, insertion_point: int = 0) -> None:
        self._text = text
        self._insertion_point = insertion_point
        self.selection: tuple[int, int] = (insertion_point, insertion_point)

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._insertion_point

    def SetInsertionPoint(self, value: int) -> None:
        self._insertion_point = value
        self.selection = (value, value)

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)
        self._insertion_point = end

    def GetSelection(self) -> tuple[int, int]:
        return self.selection

    def GetRange(self, start: int, end: int) -> str:
        return self._text[start:end]

    def GetStringSelection(self) -> str:
        s, e = self.selection
        return self._text[s:e]


class _StatusBar:
    def __init__(self) -> None:
        self.status: dict[int, str] = {}

    def SetStatusText(self, value: str, index: int = 0) -> None:
        self.status[index] = value

    def SetFieldsCount(self, count: int) -> None:
        pass

    def SetStatusWidths(self, widths: list[int]) -> None:
        pass

    def Layout(self) -> None:
        pass


class _Frame:
    def __init__(self) -> None:
        self.title = ""

    def SetTitle(self, title: str) -> None:
        self.title = title


class _Notebook:
    def __init__(self) -> None:
        self.pages: list[object] = []
        self.titles: list[str] = []
        self.selection = 0

    def Bind(self, *_args: object, **_kwargs: object) -> None:
        return None

    def AddPage(self, page: object, title: str, select: bool = False) -> None:
        self.pages.append(page)
        self.titles.append(title)
        if select:
            self.selection = len(self.pages) - 1

    def GetSelection(self) -> int:
        return self.selection

    def GetPageCount(self) -> int:
        return len(self.pages)

    def GetPageText(self, index: int) -> str:
        return self.titles[index]


class _ReadAloud:
    def __init__(self, state: str = "stopped") -> None:
        self.state = state
        self.stopped = False

    def stop(self) -> None:
        self.state = "stopped"
        self.stopped = True


def _build_frame(text: str = "Hello world", insertion_point: int = 0) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(path=Path("note.md"))
    frame.editor = _Editor(text=text, insertion_point=insertion_point)
    frame.statusbar = _StatusBar()
    frame.frame = _Frame()
    frame.notebook = _Notebook()
    frame._location_ring = LocationRing()
    frame._region_tracker = RegionTracker()
    frame._active_region = "Editor"
    frame._region_tracker.enter("Editor")
    frame._status_message = "Ready"
    frame._overwrite_mode = False
    frame._insert_key_down = False
    frame._extend_selection_mode = False
    frame._extend_selection_anchor = None
    frame._selection_anchor = None
    frame._last_selection = None
    frame._compare_session = None
    frame._safe_mode = False
    frame._document_tabs = [type("Tab", (), {"editor": frame.editor, "document": frame.document})()]
    frame._active_tab_index = 0
    frame.notebook.AddPage(object(), frame.document.name, select=True)
    frame.settings = type(
        "Settings",
        (),
        {
            "persistent_undo": False,
            "title_bar_path_mode": "name",
            "dirty_title_style": "text",
            "status_bar_order": ["message"],
            "status_bar_hidden": [],
            "announcement_throttle_ms": 0,
        },
    )()
    return frame


# --- start_selection ---


def test_start_selection_sets_anchor() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame.start_selection()
    assert frame._selection_anchor == 5


def test_start_selection_announces_position() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame.start_selection()
    entries = transcript_entries()
    assert any("line" in e and "column" in e for e in entries)


# --- complete_selection ---


def test_complete_selection_makes_selection() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame._selection_anchor = 0
    frame.editor.SetInsertionPoint(5)
    frame.complete_selection()
    assert frame.editor.selection == (0, 5)
    assert frame._last_selection == (0, 5)


def test_complete_selection_clears_anchor() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame._selection_anchor = 0
    frame.editor.SetInsertionPoint(5)
    frame.complete_selection()
    assert frame._selection_anchor is None


def test_complete_selection_no_anchor_announces_error() -> None:
    frame = _build_frame("hello world")
    frame.complete_selection()
    assert any("anchor" in e.lower() for e in transcript_entries())


def test_complete_selection_backwards_normalizes_order() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame._selection_anchor = 5
    frame.editor.SetInsertionPoint(0)
    frame.complete_selection()
    start, end = frame.editor.selection
    assert start <= end


# --- reselect ---


def test_reselect_restores_last_selection() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame._last_selection = (2, 7)
    frame.reselect()
    assert frame.editor.selection == (2, 7)


def test_reselect_no_previous_announces_error() -> None:
    frame = _build_frame("hello world")
    frame.reselect()
    assert any("previous" in e.lower() or "no" in e.lower() for e in transcript_entries())


def test_reselect_clamps_to_text_length() -> None:
    frame = _build_frame("hi")
    frame._last_selection = (0, 999)
    frame.reselect()
    length = len("hi")
    _start, end = frame.editor.selection
    assert end <= length


# --- go_to_start_of_selection ---


def test_go_to_start_of_selection_moves_caret() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame.editor.SetSelection(2, 8)
    frame.go_to_start_of_selection()
    assert frame.editor.GetInsertionPoint() == 2


def test_go_to_start_of_selection_no_selection_announces_error() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame.go_to_start_of_selection()
    assert any("no selection" in e.lower() for e in transcript_entries())


# --- copy_all ---


def test_copy_all_copies_full_text() -> None:
    frame = _build_frame("hello world")
    copied: list[str] = []
    frame._copy_to_clipboard = lambda text: copied.append(text) or True  # type: ignore[method-assign]
    frame.copy_all()
    assert copied == ["hello world"]


def test_copy_all_empty_document_announces_error() -> None:
    frame = _build_frame("")
    frame.copy_all()
    entries = transcript_entries()
    assert any("empty" in e.lower() for e in entries)


def test_copy_all_announces_char_count() -> None:
    frame = _build_frame("hello world")
    frame._copy_to_clipboard = lambda _text: True  # type: ignore[method-assign]
    frame.copy_all()
    entries = transcript_entries()
    assert any("11" in e for e in entries)


# --- unselect_all ---


def test_unselect_all_clears_selection() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame.editor.SetSelection(2, 8)
    frame.unselect_all()
    start, end = frame.editor.selection
    assert start == end


def test_unselect_all_announces() -> None:
    frame = _build_frame("hello world")
    frame.unselect_all()
    assert any("selection cleared" in e.lower() for e in transcript_entries())


# --- say_selected ---


def test_say_selected_announces_text() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame.editor.SetSelection(0, 5)
    frame.say_selected()
    entries = transcript_entries()
    assert "hello" in entries


def test_say_selected_no_selection_announces_error() -> None:
    frame = _build_frame("hello world", insertion_point=5)
    frame.say_selected()
    entries = transcript_entries()
    assert any("nothing" in e.lower() for e in entries)


# --- toggle_extend_selection_mode ---


def test_toggle_extend_selection_mode_on_announces_anchor() -> None:
    frame = _build_frame("line one\nline two", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    entries = transcript_entries()
    assert any("line" in e and "column" in e for e in entries)


def test_toggle_extend_selection_mode_off_with_last_selection_announces_region() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame._last_selection = (0, 5)
    frame.toggle_extend_selection_mode(True)
    clear_transcript()
    frame.toggle_extend_selection_mode(False)
    entries = transcript_entries()
    assert any("line" in e and "column" in e for e in entries)


def test_toggle_extend_selection_mode_off_no_last_selection_announces_off() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    clear_transcript()
    frame.toggle_extend_selection_mode(False)
    entries = transcript_entries()
    assert any("off" in e.lower() for e in entries)


# --- apply_extend_selection tracks _last_selection ---


def test_apply_extend_selection_sets_last_selection() -> None:
    frame = _build_frame("hello world", insertion_point=0)
    frame._extend_selection_mode = True
    frame._extend_selection_anchor = 0
    frame.editor.SetInsertionPoint(5)
    frame._apply_extend_selection()
    assert frame._last_selection == (0, 5)
