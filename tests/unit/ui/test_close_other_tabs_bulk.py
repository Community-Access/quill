"""Close Other Documents in QUILL (Ctrl+Shift+F4), with Save All / Don't Save Any.

QUILL has had the command since 2026-06-15 and asked one question per tab. With
sixty-eight tabs open that is sixty-eight prompts from a command whose entire
purpose is to save sixty-eight keystrokes.

The loop lives in ``quill.ui.main_frame_close_others`` so it can be driven
without a display: ``_ask_bulk_unsaved`` is the seam the window sits behind, and
everything else here is the real mixin over fake tabs. The decisions it defers
to -- the question's wording, what a "to all" answer latches, the sentence
afterwards -- are tested in ``tests/unit/core/test_close_prompt.py``; what is
held here is that QUILL wires them up the same way QUILL Lite does.
"""

from __future__ import annotations

import pytest

from quill.core.close_prompt import CANCEL, DISCARD, DISCARD_ALL, SAVE, SAVE_ALL
from quill.ui.main_frame_close_others import CloseOthersMixin


class _Document:
    def __init__(self, name: str, modified: bool = False) -> None:
        self.name = name
        self.modified = modified


class _Tab:
    def __init__(self, name: str, modified: bool = False) -> None:
        self.document = _Document(name, modified)


class _Frame(CloseOthersMixin):
    """The mixin over fake tabs, with every output recorded."""

    def __init__(self, names: list[tuple[str, bool]], keep: int = 0) -> None:
        self._document_tabs = [_Tab(name, modified) for name, modified in names]
        self._active_tab_index = keep
        self._selected = keep
        self.frame = None
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.closed: list[str] = []
        self.asked: list[str] = []
        self.script: list[str] = []
        self.saves = 0
        self.save_succeeds = True

    # -- the surface the mixin reaches for ---------------------------- #

    @property
    def document(self) -> _Document:
        return self._document_tabs[self._selected].document

    def _select_tab(self, index: int) -> None:
        self._selected = index

    def _close_tab(self, index: int) -> None:
        self.closed.append(self._document_tabs[index].document.name)
        del self._document_tabs[index]
        self._selected = min(self._selected, len(self._document_tabs) - 1)

    def _set_status(self, text: str) -> None:
        self.statuses.append(text)

    def _announce(self, text: str) -> None:
        self.announcements.append(text)

    def _ask_bulk_unsaved(self, question: str) -> str:
        self.asked.append(question)
        return self.script.pop(0) if self.script else DISCARD

    def save_file(self) -> None:
        self.saves += 1
        if not self.save_succeeds:
            raise OSError("disk full")
        self.document.modified = False


@pytest.fixture
def frame():
    """Four tabs, the first kept. Nothing modified unless a test says so."""
    return _Frame([("keep.md", False), ("a.md", False), ("b.md", False), ("c.md", False)])


def test_it_closes_every_other_tab_and_keeps_this_one(frame) -> None:
    frame.close_other_documents()

    assert [tab.document.name for tab in frame._document_tabs] == ["keep.md"]
    assert sorted(frame.closed) == ["a.md", "b.md", "c.md"]


def test_an_unmodified_tab_is_never_asked_about(frame) -> None:
    frame.close_other_documents()

    assert frame.asked == []


def test_one_tab_open_says_so_rather_than_doing_nothing() -> None:
    """A command that answers silently is one somebody presses twice."""
    only = _Frame([("keep.md", False)])

    only.close_other_documents()

    assert only.closed == []
    assert "Only one document open" in only.announcements


def test_dont_save_any_answers_every_remaining_tab() -> None:
    """The whole point: one selection, not sixty-seven."""
    frame = _Frame([("keep.md", False)] + [(f"{i}.md", True) for i in range(5)])
    frame.script.append(DISCARD_ALL)

    frame.close_other_documents()

    assert len(frame.asked) == 1
    assert len(frame.closed) == 5
    assert "discarded 5 unsaved" in frame.statuses[-1]


def test_save_all_saves_every_remaining_tab() -> None:
    frame = _Frame([("keep.md", False)] + [(f"{i}.md", True) for i in range(4)])
    frame.script.append(SAVE_ALL)

    frame.close_other_documents()

    assert len(frame.asked) == 1
    assert frame.saves == 4
    assert "saved 4" in frame.statuses[-1]


def test_save_and_dont_save_apply_to_one_tab_only() -> None:
    """Neither single answer may latch -- each is about the tab in front."""
    frame = _Frame([("keep.md", False), ("a.md", True), ("b.md", True)])
    frame.script.extend([SAVE, DISCARD])

    frame.close_other_documents()

    assert len(frame.asked) == 2
    assert frame.saves == 1
    assert "saved 1" in frame.statuses[-1]
    assert "discarded 1 unsaved" in frame.statuses[-1]


def test_the_question_says_how_many_more_are_waiting() -> None:
    """What makes Don't Save Any an obvious answer rather than a discovery."""
    frame = _Frame([("keep.md", False), ("a.md", True), ("b.md", True), ("c.md", True)])
    frame.script.extend([DISCARD, DISCARD, DISCARD])

    frame.close_other_documents()

    assert "2 other documents also have unsaved changes" in frame.asked[0]
    assert "1 other document also has unsaved changes" in frame.asked[1]
    assert "also ha" not in frame.asked[2]


def test_the_question_names_the_tab_that_is_in_front() -> None:
    """A prompt naming a document other than the one on screen is the wrong question."""
    frame = _Frame([("keep.md", False), ("a.md", True)])
    frame.script.append(DISCARD)

    frame.close_other_documents()

    assert "a.md" in frame.asked[0]


def test_cancel_stops_the_whole_thing() -> None:
    frame = _Frame([("keep.md", False), ("a.md", True), ("b.md", False)])
    frame.script.append(CANCEL)

    frame.close_other_documents()

    # b.md closed first (the loop runs backwards), then a.md asked and cancelled.
    assert frame.closed == ["b.md"]
    assert [tab.document.name for tab in frame._document_tabs] == ["keep.md", "a.md"]
    assert "1 document still open" in frame.statuses[-1]


def test_cancel_before_anything_closed_says_nothing_closed() -> None:
    frame = _Frame([("keep.md", False), ("a.md", True)])
    frame.script.append(CANCEL)

    frame.close_other_documents()

    assert frame.closed == []
    assert frame.statuses[-1] == "Nothing closed."


def test_a_failed_save_stops_and_never_reads_as_consent_to_discard() -> None:
    """Closing on a failed save *is* the data loss (#1390)."""
    frame = _Frame([("keep.md", False), ("a.md", True)])
    frame.save_succeeds = False
    frame.script.append(SAVE)

    frame.close_other_documents()

    assert frame.closed == []
    assert "was not saved" in frame.statuses[-1]


def test_a_failed_save_breaks_a_save_all_latch() -> None:
    """ "Save all" cannot keep meaning "save all" once saving has stopped working."""
    frame = _Frame([("keep.md", False), ("a.md", True), ("b.md", True)])
    frame.save_succeeds = False
    frame.script.append(SAVE_ALL)

    frame.close_other_documents()

    assert frame.closed == []
    assert frame.saves == 1  # stopped at the first failure, did not try the rest


def test_focus_returns_to_the_tab_the_command_was_about_keeping() -> None:
    frame = _Frame([("keep.md", False), ("a.md", True)])
    frame.script.append(DISCARD)

    frame.close_other_documents()

    assert frame._document_tabs[frame._selected].document.name == "keep.md"


def test_an_out_of_range_keep_index_does_nothing() -> None:
    frame = _Frame([("keep.md", False), ("a.md", False)])

    frame._close_other_tabs(9)

    assert len(frame._document_tabs) == 2
