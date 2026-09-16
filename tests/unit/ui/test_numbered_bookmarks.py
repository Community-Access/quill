"""QUILL's numbered bookmarks: the nine slots QuillLite had to itself.

The engine (``quill.core.numbered_bookmarks``) has its own tests; these are
about the half that was missing until 2026-09-16 -- QUILL's door to it. The
regression they exist to prevent is the one that already happened: the core
shipped, QuillLite called it, and nothing under ``quill/ui`` imported it for
seven days while ``navigate.set_bookmark`` sat registered with no key.

A stub host rather than a real ``MainFrame``: the mixin's contract is six
attributes wide, and a test that needs a wx frame to check that a bookmark
persists is a test that will be skipped on the machine where it matters.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.bookmarks import DocumentMemory
from quill.core.numbered_bookmarks import BookmarkSet
from quill.ui.main_frame_numbered_bookmarks import NumberedBookmarksMixin


class _Editor:
    def __init__(self, text: str = "") -> None:
        self._text = text
        self._caret = 0

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self._text

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self._caret

    def SetInsertionPoint(self, position: int) -> None:  # noqa: N802
        self._caret = position

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self._text)

    def SetFocus(self) -> None:  # noqa: N802
        pass


class _Tab:
    numbered_bookmarks = None


class _Document:
    def __init__(self, path: Path | None) -> None:
        self.path = path


class _Host(NumberedBookmarksMixin):
    """The six attributes the mixin actually needs."""

    def __init__(self, text: str, path: Path | None, memory: DocumentMemory) -> None:
        self.editor = _Editor(text)
        self.document = _Document(path)
        self._doc_memory = memory
        self._tab = _Tab()
        self.announced: list[str] = []
        self.jumps_recorded = 0

    def _active_tab(self):
        return self._tab

    def _move_point(self, position: int) -> None:
        self.editor.SetInsertionPoint(max(0, min(position, len(self.editor.GetValue()))))

    def _record_location_before_jump(self) -> None:
        self.jumps_recorded += 1

    def _announce_result(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.announced.append(message)


TEXT = "alpha line\nbeta line\ngamma line\ndelta line\n"


@pytest.fixture
def memory(tmp_path: Path) -> DocumentMemory:
    return DocumentMemory(path=tmp_path / "memory.json")


@pytest.fixture
def host(tmp_path: Path, memory: DocumentMemory) -> _Host:
    return _Host(TEXT, tmp_path / "doc.txt", memory)


# -- setting ---------------------------------------------------------------------


def test_setting_a_numbered_slot_announces_the_number_and_the_line(host: _Host) -> None:
    host.editor.SetInsertionPoint(TEXT.index("gamma"))
    host.set_numbered_bookmark_3()
    assert host.announced == ["Bookmark 3 set: gamma line"]
    assert host.numbered_bookmarks.get(3).position == TEXT.index("gamma")


def test_plain_set_takes_the_next_free_slot(host: _Host) -> None:
    host.set_numbered_bookmark()
    host.editor.SetInsertionPoint(5)
    host.set_numbered_bookmark()
    assert [m.number for m in host.numbered_bookmarks.all()] == [1, 2]


def test_setting_the_same_slot_twice_moves_it_rather_than_adding_one(host: _Host) -> None:
    host.set_numbered_bookmark_4()
    host.editor.SetInsertionPoint(TEXT.index("delta"))
    host.set_numbered_bookmark_4()
    assert len(host.numbered_bookmarks) == 1
    assert host.numbered_bookmarks.get(4).position == TEXT.index("delta")


# -- walking ---------------------------------------------------------------------


def test_next_and_previous_walk_by_position_not_by_number(host: _Host) -> None:
    host.editor.SetInsertionPoint(TEXT.index("delta"))
    host.set_numbered_bookmark_1()
    host.editor.SetInsertionPoint(TEXT.index("beta"))
    host.set_numbered_bookmark_9()
    host.editor.SetInsertionPoint(0)

    host.next_bookmark()
    assert host.editor.GetInsertionPoint() == TEXT.index("beta")
    host.next_bookmark()
    assert host.editor.GetInsertionPoint() == TEXT.index("delta")
    host.previous_bookmark()
    assert host.editor.GetInsertionPoint() == TEXT.index("beta")


def test_every_jump_is_recorded_so_alt_left_can_undo_it(host: _Host) -> None:
    # bad.md L8: QUILL's Back did not undo a bookmark jump because bookmarks
    # did not go through the location ring. This one does, from the start.
    host.set_numbered_bookmark_1()
    host.editor.SetInsertionPoint(len(TEXT))
    host.next_bookmark()
    host.go_to_numbered_bookmark(1)
    assert host.jumps_recorded == 2


def test_walking_an_empty_set_says_so_and_does_not_move(host: _Host) -> None:
    host.editor.SetInsertionPoint(7)
    host.next_bookmark()
    assert host.announced == ["No bookmarks in this document"]
    assert host.editor.GetInsertionPoint() == 7
    assert host.jumps_recorded == 0


def test_going_to_an_unset_slot_names_the_slot(host: _Host) -> None:
    host.go_to_numbered_bookmark(6)
    assert host.announced == ["Bookmark 6 is not set"]


# -- clearing --------------------------------------------------------------------


def test_clear_counts_what_it_cleared(host: _Host) -> None:
    host.set_numbered_bookmark_1()
    host.set_numbered_bookmark_2()
    host.clear_numbered_bookmarks()
    assert host.announced[-1] == "Cleared 2 bookmarks"
    assert len(host.numbered_bookmarks) == 0


def test_clearing_nothing_says_so_rather_than_claiming_success(host: _Host) -> None:
    host.clear_numbered_bookmarks()
    assert host.announced == ["No bookmarks to clear"]


def test_one_bookmark_is_cleared_in_the_singular(host: _Host) -> None:
    host.set_numbered_bookmark_1()
    host.clear_numbered_bookmarks()
    assert host.announced[-1] == "Cleared 1 bookmark"


# -- persistence -----------------------------------------------------------------


def test_bookmarks_are_written_on_every_change_not_on_close(
    tmp_path: Path, memory: DocumentMemory
) -> None:
    # bad.md L10: QuillLite writes on close, so a crash loses a clear-all.
    # QUILL already wrote named bookmarks on every Set; this follows that.
    path = tmp_path / "doc.txt"
    host = _Host(TEXT, path, memory)
    host.set_numbered_bookmark_2()

    key = DocumentMemory.key_for(path)
    assert [r["number"] for r in memory.numbered_for(key)] == [2]

    host.clear_numbered_bookmarks()
    assert memory.numbered_for(key) == []


def test_a_saved_file_reopens_with_its_bookmarks(tmp_path: Path, memory: DocumentMemory) -> None:
    path = tmp_path / "doc.txt"
    first = _Host(TEXT, path, memory)
    first.editor.SetInsertionPoint(TEXT.index("gamma"))
    first.set_numbered_bookmark_5()

    reopened = _Host(TEXT, path, memory)
    reopened._adopt_numbered_bookmarks(
        reopened._tab, memory.numbered_for(DocumentMemory.key_for(path))
    )
    assert reopened.numbered_bookmarks.get(5).position == TEXT.index("gamma")


def test_an_untitled_document_keeps_its_bookmarks_in_memory_only(
    memory: DocumentMemory,
) -> None:
    host = _Host(TEXT, None, memory)
    host.set_numbered_bookmark_1()
    assert len(host.numbered_bookmarks) == 1
    assert memory.numbered_for(None) == []


def test_a_bookmark_set_is_per_tab_not_per_frame(tmp_path: Path, memory: DocumentMemory) -> None:
    # The one thing a bookmark must never do is follow the user to another
    # document, which a frame-level cache would have made it do.
    host = _Host(TEXT, tmp_path / "a.txt", memory)
    host.set_numbered_bookmark_1()
    host._tab = _Tab()
    host.document = _Document(tmp_path / "b.txt")
    assert len(host.numbered_bookmarks) == 0


# -- keeping positions true ------------------------------------------------------


def test_an_edit_above_a_bookmark_moves_it(host: _Host) -> None:
    host.editor.SetInsertionPoint(TEXT.index("gamma"))
    host.set_numbered_bookmark_1()
    before = host.numbered_bookmarks.get(1).position
    host.shift_numbered_bookmarks(at=0, delta=6)
    assert host.numbered_bookmarks.get(1).position == before + 6


def test_a_shift_of_nothing_does_not_touch_the_store(host: _Host) -> None:
    host.set_numbered_bookmark_1()
    host.shift_numbered_bookmarks(at=0, delta=0)
    assert host.numbered_bookmarks.get(1).position == 0


def test_a_bookmark_past_the_end_is_pulled_back_inside(host: _Host) -> None:
    host.editor.SetInsertionPoint(len(TEXT))
    host.set_numbered_bookmark_1()
    host.editor._text = "short"
    host.clamp_numbered_bookmarks()
    assert host.numbered_bookmarks.get(1).position <= len("short")


# -- the list --------------------------------------------------------------------


def test_list_rows_lead_with_the_digit(host: _Host) -> None:
    # Why there is no Go-To-Bookmark-N chord family: the rows begin with the
    # number, so "3, Enter" is two keys and no new binding (bad.md 3.5).
    host.editor.SetInsertionPoint(TEXT.index("beta"))
    host.set_numbered_bookmark_3()
    assert host.numbered_bookmark_rows() == [(3, "beta line", TEXT.index("beta"))]


def test_a_malformed_store_opens_the_document_anyway(host: _Host) -> None:
    host._adopt_numbered_bookmarks(host._tab, "not records at all")
    assert isinstance(host._tab.numbered_bookmarks, BookmarkSet)
    assert len(host._tab.numbered_bookmarks) == 0
