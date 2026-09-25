"""How often QUILL Lite reads its own buffer, which is the whole point.

``GetValue()`` on a multiline control copies the entire document across the
wx/native boundary. QUILL Lite had five readers doing it -- the status bar's
counts, the heading cue's change detector, the list cue, the live spell check on
every navigation key-up, and autoformat on every keystroke -- so one pause in
typing cost three full scans and two marshals, and holding the Down arrow in a
50 MB file cost one of each per repeat (bad.md V2, V3, S8, T1).

Every test here counts reads. Nothing here checks that an answer is *right*:
that is what the rest of the suite is for, and a mirror that reads the buffer
for every question would pass all of it. These are the tests that fail if
somebody puts a ``GetValue()`` back.
"""

from __future__ import annotations

import wx

DOC = "# Title\n\nSome body text with wrods in it.\n\n## Section\n\nmore text here\n"


def test_moving_the_caret_never_reads_the_buffer_twice(lite_window) -> None:
    """The live spell check and the heading cue both ride the key-up hook.

    Between them they read the whole document twice per arrow press. They read
    the mirror now, so the first press pays once and every press after it pays
    nothing at all -- until the text actually changes.
    """
    win = lite_window(DOC, cursor=0, mode="plain")
    win.control.value_reads = 0

    for position in range(0, 40, 3):
        win.control.SetInsertionPoint(position)
        win.check_spelling_at_caret(wx.WXK_DOWN)
        win.announce_structure_at_caret()

    assert win.control.value_reads == 1


def test_an_edit_costs_exactly_one_more_read(lite_window) -> None:
    win = lite_window(DOC, cursor=0, mode="plain")
    win.check_spelling_at_caret(wx.WXK_DOWN)
    win.control.value_reads = 0

    win.control.SetInsertionPoint(0)
    win.control.WriteText("x")
    win.on_text_changed()
    win.check_spelling_at_caret(wx.WXK_DOWN)
    win.announce_structure_at_caret()

    assert win.control.value_reads == 1


def test_typing_a_run_of_characters_never_reads_the_buffer(lite_window) -> None:
    """Autoformat wants the one character behind the caret, and used to read the
    document to find it -- on the hottest path in the app. It asks the control
    for that one character now, the way QUILL has since #1346."""
    win = lite_window("hello", cursor=5, mode="plain")
    win.app.settings.autoformat = True
    win.control.value_reads = 0

    for letter in "world":
        win._autoformat(letter)

    assert win.control.value_reads == 0


def test_typing_a_letter_does_not_go_looking_for_an_abbreviation(lite_window) -> None:
    """An abbreviation is recognised by the character that *follows* it, so a
    letter cannot possibly expand anything -- and finding that out used to cost
    a full read of the document, per keystroke."""
    win = lite_window("btw", cursor=3, mode="plain")
    win.control.value_reads = 0
    win._maybe_expand()
    assert win.control.value_reads == 0


def test_the_mirror_follows_a_document_that_is_replaced_wholesale(lite_window) -> None:
    """``ChangeValue`` raises no text event, so the load paths invalidate by
    hand. A mirror that missed one would answer every question about the new
    file with the old one's text."""
    win = lite_window(DOC, cursor=0, mode="plain")
    assert win.doc_text.text == DOC

    win.control.ChangeValue("something else entirely")
    win.doc_text.invalidate()
    assert win.doc_text.text == "something else entirely"


def test_the_revision_moves_on_every_edit_and_not_on_a_caret_move(lite_window) -> None:
    """The heading cue's change detector used to be the document's *length*,
    measured by reading the whole buffer. The revision answers the same question
    for nothing -- and answers it correctly for an edit that happens to leave
    the length unchanged, which a length could never see."""
    win = lite_window("alpha", cursor=0, mode="plain")
    before = win.doc_text.revision

    win.control.SetInsertionPoint(3)
    assert win.doc_text.revision == before

    win.control.SetValue("bravo")  # same length, different document
    win.on_text_changed()
    assert win.doc_text.revision != before
