"""QUILL puts the cursor back in its sentence on reopen, or says it cannot (FUX-01).

The rule is :mod:`quill.core.resume_place`; this drives QUILL's wiring
(``main_frame_bookmarks``) through a duck-typed host, because what is under
test is which text is remembered and where the cursor lands, not a window.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.bookmarks import DOCUMENT_MEMORY_FILENAME, DocumentMemory
from quill.ui.main_frame_bookmarks import BookmarksFoldsMixin

TEXT = "".join(f"Sentence {n} belongs to line {n} alone.\n" for n in range(30))


class _Editor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.caret = 0

    def GetValue(self) -> str:
        return self.text

    def GetInsertionPoint(self) -> int:
        return self.caret

    def SetInsertionPoint(self, position: int) -> None:
        self.caret = position

    def ShowPosition(self, _position: int) -> None:
        pass


class _Host(BookmarksFoldsMixin):
    def __init__(self, store: DocumentMemory, path: Path, text: str, *, modified: bool) -> None:
        self._doc_memory = store
        self.document = SimpleNamespace(path=path, modified=modified)
        self.editor = _Editor(text)
        self.said: list[str] = []
        self.active: object = None

    def _active_tab(self) -> object:
        return self.active

    def _adopt_numbered_bookmarks(self, _tab: object, _records: object) -> None:
        pass

    def _announce_result(self, message: str) -> None:
        self.said.append(message)


def _reopen(
    store: DocumentMemory, path: Path, text: str, monkeypatch, *, active: bool = True
) -> _Host:
    import wx

    monkeypatch.setattr(wx, "CallAfter", lambda fn, *args: fn(*args))
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *args: fn(*args))
    host = _Host(store, path, text, modified=False)
    host.tab = SimpleNamespace(document=host.document, editor=host.editor)
    if active:
        host.active = host.tab
    host._restore_document_memory(host.tab)
    return host


def test_quill_finds_the_sentence_after_an_edit_above(tmp_path: Path, monkeypatch) -> None:
    store = DocumentMemory.load(tmp_path / DOCUMENT_MEMORY_FILENAME)
    doc = tmp_path / "doc.txt"
    host = _Host(store, doc, TEXT, modified=False)
    host.editor.caret = TEXT.index("line 18")
    host._remember_active_caret()

    edited = "A heading added later.\n\n" + TEXT
    reopened = _reopen(DocumentMemory.load(store.path), doc, edited, monkeypatch)

    assert reopened.editor.caret == edited.index("line 18")
    assert reopened.said == []


def test_quill_says_when_the_place_is_gone(tmp_path: Path, monkeypatch) -> None:
    store = DocumentMemory.load(tmp_path / DOCUMENT_MEMORY_FILENAME)
    doc = tmp_path / "doc.txt"
    host = _Host(store, doc, TEXT, modified=False)
    host.editor.caret = TEXT.index("line 4 alone")
    host._remember_active_caret()

    other = "".join(f"Rewritten {n}.\n" for n in range(30))
    reopened = _reopen(DocumentMemory.load(store.path), doc, other, monkeypatch)

    assert reopened.editor.caret == other.index("Rewritten 4.")
    assert reopened.said == [
        "The text where you left off has changed. The cursor is at the start of line 5."
    ]


def test_quill_says_it_in_a_background_tab_only_when_you_arrive(
    tmp_path: Path, monkeypatch
) -> None:
    store = DocumentMemory.load(tmp_path / DOCUMENT_MEMORY_FILENAME)
    doc = tmp_path / "doc.txt"
    host = _Host(store, doc, TEXT, modified=False)
    host.editor.caret = TEXT.index("line 4 alone")
    host._remember_active_caret()

    other = "".join(f"Rewritten {n}.\n" for n in range(30))
    reopened = _reopen(DocumentMemory.load(store.path), doc, other, monkeypatch, active=False)
    assert reopened.said == []

    reopened.active = reopened.tab
    reopened._say_place_note_if_active(reopened.tab)
    reopened._say_place_note_if_active(reopened.tab)
    assert len(reopened.said) == 1


def test_quill_keeps_the_last_saved_place_while_unsaved(tmp_path: Path) -> None:
    """A place in text that may be discarded is one the next open cannot check."""
    store = DocumentMemory.load(tmp_path / DOCUMENT_MEMORY_FILENAME)
    doc = tmp_path / "doc.txt"
    host = _Host(store, doc, TEXT, modified=False)
    host.editor.caret = 40
    host._remember_active_caret()
    host.document.modified = True
    host.editor.caret = 12

    host._remember_active_caret()

    key = store.key_for(doc)
    assert store.last_position(key) == 40
    assert store.last_anchor(key) is not None
