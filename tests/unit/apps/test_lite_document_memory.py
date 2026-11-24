"""Bookmarks and the cursor survive closing the document.

The argument for numbered bookmarks in QUILL Lite is that there is no scrollbar
to remember the position of (its PRD 3.1). That argument does not stop when the
window closes -- it is strongest then -- so until 2026-09-09 the feature was
delivering half of what justified it: nine places you marked, gone on reopen.

The store is QUILL's own :class:`~quill.core.bookmarks.DocumentMemory`, keyed by
absolute path and kept in QUILL Lite's own data folder. What the two products
share is the format and the code; they never share the file.

These tests go through the real store on a real temporary path, because the two
failures worth catching are both about the file rather than the model: a
document whose bookmarks were written by another window being overwritten, and
a bookmark restored past the end of a file that changed on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.apps.lite_window_marks import DocumentMarksMixin
from quill.core.bookmarks import DOCUMENT_MEMORY_FILENAME, DocumentMemory
from quill.core.numbered_bookmarks import BookmarkSet


class _Control:
    def __init__(self, text: str) -> None:
        self._text = text
        self._cursor = 0
        self.shown: int | None = None

    def GetValue(self) -> str:
        return self._text

    def GetLastPosition(self) -> int:
        return len(self._text)

    def GetInsertionPoint(self) -> int:
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = position

    def ShowPosition(self, position: int) -> None:
        self.shown = position


class _App:
    def __init__(self, store: DocumentMemory | None) -> None:
        self.document_memory = store


class _Window(DocumentMarksMixin):
    def __init__(self, store: DocumentMemory | None, path: Path | None, text: str) -> None:
        self.app = _App(store)
        self.path = path
        self.control = _Control(text)
        self.bookmarks = BookmarkSet()
        self._tracked_length = len(text)
        self.touched = 0

    def _announce(self, message: str) -> None:  # pragma: no cover - not used here
        raise AssertionError(f"restoring state must announce nothing; said {message!r}")

    def _touch_status(self) -> None:
        self.touched += 1


@pytest.fixture
def store(tmp_path: Path) -> DocumentMemory:
    return DocumentMemory.load(tmp_path / DOCUMENT_MEMORY_FILENAME)


def test_bookmarks_and_cursor_come_back_on_the_next_open(
    store: DocumentMemory, tmp_path: Path
) -> None:
    doc = tmp_path / "notes.txt"
    text = "alpha\nbravo\ncharlie\n"
    first = _Window(store, doc, text)
    first.bookmarks.set(1, 6, "bravo")
    first.bookmarks.set(4, 12, "charlie")
    first.control.SetInsertionPoint(12)

    first.remember_document_memory()

    reopened = _Window(DocumentMemory.load(store.path), doc, text)
    reopened.restore_document_memory()

    assert [(m.number, m.position, m.label) for m in reopened.bookmarks.all()] == [
        (1, 6, "bravo"),
        (4, 12, "charlie"),
    ]
    assert reopened.control.GetInsertionPoint() == 12
    # Scrolled as well as moved: a caret the window has not scrolled to is a
    # caret a magnifier user cannot see.
    assert reopened.control.shown == 12


def test_a_document_with_no_file_is_never_persisted(store: DocumentMemory) -> None:
    """There is nothing stable to key a scratch buffer by."""
    win = _Window(store, None, "unsaved")
    win.bookmarks.set(1, 3, "uns")

    win.remember_document_memory()

    assert store.documents == {}


def test_two_windows_do_not_overwrite_each_others_rows(
    store: DocumentMemory, tmp_path: Path
) -> None:
    """The reason the store is owned by the app and not by the window.

    Two stores loaded from one path each hold a snapshot from the moment they
    loaded, so whichever window closed last would write its snapshot back over
    the other's bookmarks. Sharing one object is what prevents it -- and this
    test fails if somebody later moves the store onto the window.
    """
    left, right = tmp_path / "left.txt", tmp_path / "right.txt"
    win_a = _Window(store, left, "aaaa")
    win_b = _Window(store, right, "bbbb")
    win_a.bookmarks.set(1, 1, "a")
    win_b.bookmarks.set(2, 2, "b")

    win_a.remember_document_memory()
    win_b.remember_document_memory()

    reread = DocumentMemory.load(store.path)
    assert reread.numbered_for(reread.key_for(left)) == [{"number": 1, "position": 1, "label": "a"}]
    assert reread.numbered_for(reread.key_for(right)) == [
        {"number": 2, "position": 2, "label": "b"}
    ]


def test_a_bookmark_past_the_end_is_pulled_back_inside(
    store: DocumentMemory, tmp_path: Path
) -> None:
    """The file can have been truncated by another program since it was marked.

    An out-of-range bookmark would send the caret nowhere, and a bookmark that
    is wrong is worse than one that does not exist, because it is trusted.
    """
    doc = tmp_path / "shrunk.txt"
    before = _Window(store, doc, "a" * 500)
    before.bookmarks.set(1, 480, "tail")
    before.control.SetInsertionPoint(480)
    before.remember_document_memory()

    after = _Window(DocumentMemory.load(store.path), doc, "a" * 10)
    after.restore_document_memory()

    assert after.bookmarks.get(1).position == 10
    # And the stale cursor is refused rather than clamped: landing at the end
    # of a file that changed under you is not "where you were".
    assert after.control.GetInsertionPoint() == 0


def test_clearing_every_bookmark_leaves_no_row_behind(
    store: DocumentMemory, tmp_path: Path
) -> None:
    """A store that grows a row per file ever opened is one somebody has to clean."""
    doc = tmp_path / "tidy.txt"
    win = _Window(store, doc, "hello")
    win.bookmarks.set(1, 1, "h")
    win.remember_document_memory()
    assert store.documents

    win.bookmarks.clear_all()
    win.control.SetInsertionPoint(0)
    win.remember_document_memory()

    assert DocumentMemory.load(store.path).numbered_for(store.key_for(doc)) == []


def test_a_malformed_row_costs_the_bookmarks_and_not_the_document(tmp_path: Path) -> None:
    """Forgiving on purpose: a truncated store must never refuse to open a file."""
    path = tmp_path / DOCUMENT_MEMORY_FILENAME
    doc = tmp_path / "notes.txt"
    key = DocumentMemory.key_for(doc)
    store = DocumentMemory.load(path)
    store.documents[key] = {
        "bookmarks": {},
        "numbered": [
            {"number": 1, "position": 2, "label": "kept"},
            {"number": "two", "position": 3, "label": "dropped"},
            "not a record at all",
            {"number": 99, "position": 4, "label": "out of range"},
        ],
    }
    store.save()

    win = _Window(DocumentMemory.load(path), doc, "hello world")
    win.restore_document_memory()

    assert [(m.number, m.label) for m in win.bookmarks.all()] == [(1, "kept")]


# --------------------------------------------------------------------------- #
# FUX-01: the place is found again by its text, and a lost one is said
# --------------------------------------------------------------------------- #


class _SavedWindow(_Window):
    """A window whose text is what its file holds, and which records what it says."""

    def __init__(self, store: DocumentMemory | None, path: Path | None, text: str) -> None:
        super().__init__(store, path, text)
        self._clean_text = text
        self.said: list[str] = []

    def _announce(self, message: str, *, interrupt: bool = True) -> None:
        self.said.append(message)
        self.interrupted = interrupt


@pytest.fixture
def call_later_now(monkeypatch):
    """``wx.CallLater`` runs at once, so what is said on arrival can be read."""
    import wx

    delays: list[int] = []

    def now(delay, fn, *args, **kwargs):
        delays.append(delay)
        fn(*args, **kwargs)

    monkeypatch.setattr(wx, "CallLater", now)
    return delays


_LONG = "".join(f"Paragraph {n} says something only paragraph {n} says.\n" for n in range(40))


def test_the_cursor_follows_its_sentence_when_text_is_added_above(
    store: DocumentMemory, tmp_path: Path
) -> None:
    """A bare offset would land 30 characters early, in the sentence before."""
    doc = tmp_path / "long.txt"
    first = _SavedWindow(store, doc, _LONG)
    where = _LONG.index("paragraph 25 says")
    first.control.SetInsertionPoint(where)
    first.remember_document_memory()

    edited = "A new opening line, added by hand.\n" + _LONG
    reopened = _SavedWindow(DocumentMemory.load(store.path), doc, edited)
    reopened.restore_document_memory()

    assert reopened.control.GetInsertionPoint() == edited.index("paragraph 25 says")
    assert reopened.said == []  # found: the reader reads the line it lands on


def test_a_place_whose_text_is_gone_is_said_once_on_arrival(
    store: DocumentMemory, tmp_path: Path, call_later_now: list[int]
) -> None:
    doc = tmp_path / "long.txt"
    first = _SavedWindow(store, doc, _LONG)
    first.control.SetInsertionPoint(_LONG.index("only paragraph 12"))
    first.remember_document_memory()

    rewritten = "".join(f"Line {n} was rewritten entirely.\n" for n in range(40))
    reopened = _SavedWindow(DocumentMemory.load(store.path), doc, rewritten)
    reopened.restore_document_memory()

    # The start of the line it was on (the thirteenth), never a guess mid-word.
    assert reopened.control.GetInsertionPoint() == rewritten.index("Line 12 ")
    # Nothing while the window is still being built: the reader's reading of
    # it, or the next document's load, would cut the sentence off.
    assert reopened.said == []

    reopened.on_window_activated()
    reopened.on_window_activated()  # once, not on every return to the window

    assert reopened.said == [
        "The text where you left off has changed. The cursor is at the start of line 13."
    ]
    assert reopened.interrupted is False  # it follows the reader's line
    assert call_later_now and call_later_now[0] > 0


def test_a_document_loaded_after_you_arrived_says_it_at_once(
    store: DocumentMemory, tmp_path: Path, call_later_now: list[int]
) -> None:
    """A large file loads in the background, behind a window you are already in."""
    doc = tmp_path / "big.txt"
    first = _SavedWindow(store, doc, _LONG)
    first.control.SetInsertionPoint(_LONG.index("only paragraph 3"))
    first.remember_document_memory()

    reopened = _SavedWindow(DocumentMemory.load(store.path), doc, "Different now.\n" * 40)
    reopened.app.active_frame = reopened
    reopened.restore_document_memory()

    assert len(reopened.said) == 1 and reopened.said[0].endswith("line 4.")


def test_unsaved_text_keeps_the_last_saved_place(store: DocumentMemory, tmp_path: Path) -> None:
    """A place in text that is then discarded is one the next open cannot check."""
    doc = tmp_path / "draft.txt"
    win = _SavedWindow(store, doc, _LONG)
    win.control.SetInsertionPoint(100)
    win.remember_document_memory()
    win.control._text = "typed but not saved " + _LONG
    win.control.SetInsertionPoint(5)

    win.remember_document_memory()
    win.remember_caret_if_moved()

    key = store.key_for(doc)
    assert store.last_position(key) == 100
    assert store.last_anchor(key) is not None


def test_the_autosave_tick_writes_the_cursor_only_when_it_moved(
    store: DocumentMemory, tmp_path: Path, monkeypatch
) -> None:
    """A crash costs one tick of place, and a window left alone writes nothing."""
    doc = tmp_path / "read.txt"
    win = _SavedWindow(store, doc, _LONG)
    win.restore_document_memory()
    writes: list[int] = []
    real = DocumentMemory.set_last_position

    def counted(self, key, position, *, anchor=None):
        writes.append(position)
        real(self, key, position, anchor=anchor)

    monkeypatch.setattr(DocumentMemory, "set_last_position", counted)

    win.remember_caret_if_moved()
    assert writes == []
    win.control.SetInsertionPoint(200)
    win.remember_caret_if_moved()
    win.remember_caret_if_moved()

    assert writes == [200]
    assert DocumentMemory.load(store.path).last_position(store.key_for(doc)) == 200
