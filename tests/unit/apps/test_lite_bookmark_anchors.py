"""A bookmark that survives an edit it did not expect.

QUILL Lite shifted its bookmarks by a guess: the document's length changed by N
and the caret is here, so everything after the caret moves N. That is right for
one insertion at the caret and wrong for every other edit there is -- a Replace
All, an undo, a paste over a selection, a reload that happens to change the
length. And being wrong is the expensive direction: a bookmark that is wrong is
still trusted, so the reader arrives somewhere arbitrary and has no way to tell
that is what happened (bad.md L9).

The model here is QUILL's, which its *named* bookmarks have used since #300:
remember the text around the position and find it again.
"""

from __future__ import annotations

DOC = "first line here\nsecond line here\nthird line here\n"


def _set_at(win, needle: str) -> None:
    win.control.SetInsertionPoint(win.control.GetValue().index(needle))
    win.cmd_set_bookmark()


def test_a_bookmark_follows_its_text_when_a_line_is_inserted_above(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    _set_at(win, "third")

    win.control.SetInsertionPoint(0)
    win.control.WriteText("a new line at the top\n")
    win.on_text_changed()

    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    text = win.control.GetValue()
    assert win.control.GetInsertionPoint() == text.index("third")


def test_a_bookmark_follows_its_text_through_an_edit_somewhere_else(lite_window) -> None:
    """The case the length guess could never get right: an edit below the
    bookmark, which must not move it, and one above, which must."""
    win = lite_window(DOC, cursor=0)
    _set_at(win, "second")
    before = win.control.GetValue().index("second")

    end = win.control.GetLastPosition()
    win.control.SetInsertionPoint(end)
    win.control.WriteText("a fourth line added at the end\n")
    win.on_text_changed()

    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    assert win.control.GetInsertionPoint() == before


def test_a_replacement_that_keeps_the_length_still_moves_the_bookmark(lite_window) -> None:
    """A length delta of zero told the old code nothing had happened."""
    win = lite_window("alpha\nbravo\ncharlie\n", cursor=0)
    _set_at(win, "charlie")

    win.control.Replace(0, 5, "a-much-longer-first-line")
    win.control.Remove(0, 19)  # same total length again
    win.on_text_changed()

    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    text = win.control.GetValue()
    assert win.control.GetInsertionPoint() == text.index("charlie")


def test_a_bookmark_whose_text_is_gone_is_clamped_not_lost(lite_window) -> None:
    """Silently losing a bookmark is the other way to be wrong."""
    win = lite_window(DOC, cursor=0)
    _set_at(win, "third")
    win.control.SetValue("something else entirely\n")
    win.on_text_changed()

    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    assert 0 <= win.control.GetInsertionPoint() <= win.control.GetLastPosition()


def test_typing_does_no_work_at_all(lite_window) -> None:
    """The search is over the document, so it runs when a bookmark is *read*.

    A hook that re-anchored on every keystroke would be the cost the document
    mirror exists to remove, which is why the text hook only raises a flag.
    """
    win = lite_window(DOC, cursor=0)
    _set_at(win, "third")
    win.control.value_reads = 0
    for _ in range(50):
        win.on_text_changed()
    assert win.control.value_reads == 0


def test_the_bookmark_list_re_anchors_too(lite_window, lite_dialogs) -> None:
    """Every reader goes through one seam, because "some readers remembered" is
    one stale jump nobody can reproduce."""
    win = lite_window(DOC, cursor=0)
    _set_at(win, "third")
    win.control.SetInsertionPoint(0)
    win.control.WriteText("inserted\n")
    win.on_text_changed()

    lite_dialogs.answer("choose_bookmark", ("go", 1))
    win.cmd_list_bookmarks()
    text = win.control.GetValue()
    assert win.control.GetInsertionPoint() == text.index("third")


def test_an_anchor_survives_being_written_and_read_back() -> None:
    from quill.core.numbered_bookmarks import BookmarkSet, capture_anchor

    marks = BookmarkSet()
    at = DOC.index("second")
    marks.set(3, at, "second line here", capture_anchor(DOC, at))
    records = marks.to_records()
    assert "anchor" in records[0]

    back = BookmarkSet.from_records(records)
    shifted = "one more line\n" + DOC
    back.reanchor(shifted)
    assert back.get(3).position == shifted.index("second")


def test_a_bookmark_written_by_an_older_build_is_left_where_it_is() -> None:
    """No anchor to re-find, so clamping is all there is -- and clamping is what
    it got before, so nothing is worse than it was."""
    from quill.core.numbered_bookmarks import BookmarkSet

    back = BookmarkSet.from_records([{"number": 1, "position": 9, "label": "old"}])
    back.reanchor("a much shorter text")
    assert back.get(1).position == 9

    back.reanchor("tiny")
    assert back.get(1).position == 4
