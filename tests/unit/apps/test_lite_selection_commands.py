"""The Select menu's commands, run rather than read.

The table gate beside this one (``tests/unit/core/lite/test_lite_selection.py``)
checks that the menu is complete and that its keys match QUILL's. It says so
itself: *"the behaviour of the commands themselves needs a real window and belongs
to the sign-off checklist"*. That was true when the only stand-in available was a
running build, and it is what left F8 broken through however many sign-offs.

So: the commands, with a text model under them. What every test here asserts is
the pair -- **what changed, and what was said about it** -- because for a listener
the sentence is not commentary on the outcome, it is the only part of the outcome
they get. "It selected the paragraph and said nothing" and "it selected the
paragraph and said how much" are different features.

F8 extend mode has a file of its own (``test_lite_extend_selection.py``): it is
the only one here that spans a command and an event hook.
"""

from __future__ import annotations

DOC = "alpha bravo charlie\nsecond line here\n\nEcho FOXTROT delta\n"


# --------------------------------------------------------------------- #
# Structure: take a whole thing without knowing where it starts
# --------------------------------------------------------------------- #


def test_select_word_takes_the_word_and_counts_it(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_select_word()
    assert win.control.GetSelection() == (0, 5)
    assert win.announcements == ["Selected word, 1 word"]


def test_select_line_takes_the_line(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_select_line()
    assert win.control.GetSelection() == (0, 19)
    assert win.announcements == ["Selected line, 3 words"]


def test_select_paragraph_takes_the_run_between_blank_lines(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_select_paragraph()
    assert win.control.GetSelection() == (0, 36)
    assert win.announcements == ["Selected paragraph, 6 words"]


def test_every_selection_is_announced_in_the_shape_quill_uses(lite_window) -> None:
    """Scope, then words -- one shape, in core (bad.md L14).

    QUILL said "Selected paragraph, 41 words" and QuillLite said "Selected
    paragraph, 412 characters, 41 words". Neither was wrong; having two was,
    because somebody who uses both had to work out which product they were in
    before they could parse the answer. Words rather than characters because a
    word count is a size a person can picture and 412 characters is a number
    they then have to divide.
    """
    win = lite_window(DOC, cursor=2)
    win.cmd_select_sentence()
    start, end = win.control.GetSelection()
    assert end > start
    assert win.announcements == ["Selected sentence, 9 words"]
    assert "characters" not in win.announcements[-1]


def test_the_line_range_is_only_on_an_f8_span(lite_window) -> None:
    """The one selection whose reach cannot be worked out from its scope name.

    "Selected paragraph" tells you where it ends; an F8 span between two
    arbitrary points does not, so that is the one that carries lines (5.3).
    """
    win = lite_window(DOC, cursor=0)
    win.cmd_select_line()
    assert "line" not in win.announcements[-1].split(", ")[-1]

    win.control.SetInsertionPoint(0)
    win.cmd_start_selection()
    win.control.SetInsertionPoint(30)
    win.cmd_complete_selection()
    assert win.announcements[-1].endswith("lines 1 to 2")


def test_select_block_takes_the_block(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_select_block()
    assert win.control.GetSelection() == (0, 36)
    assert "block" in win.announcements[0]


def test_select_sentence_off_any_sentence_says_why(lite_window) -> None:
    win = lite_window("", cursor=0)
    win.cmd_select_sentence()
    assert win.announcements == ["No sentence at the cursor"]
    assert win.control.GetSelection() == (0, 0)


# --------------------------------------------------------------------- #
# The expand / shrink ladder
# --------------------------------------------------------------------- #


def test_expand_climbs_from_word_to_line(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_expand_selection()
    assert win.announcements[-1] == "Selected word, 1 word"
    win.cmd_expand_selection()
    assert win.announcements[-1] == "Selected line, 3 words"


def test_shrink_is_computed_not_remembered(lite_window) -> None:
    """It has to work on a selection made some other way.

    Shrink reads the text rather than popping an expansion history, which is the
    whole reason it can answer here -- the selection below was never expanded
    into, so a history stack would have nothing to pop.
    """
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(0, 19)
    win.cmd_shrink_selection()
    start, end = win.control.GetSelection()
    assert (end - start) < 19
    assert "Selected" in win.announcements[-1]


def test_shrink_with_nothing_selected_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_shrink_selection()
    assert win.announcements == ["Nothing is selected"]


def test_shrink_at_the_bottom_of_the_ladder_says_so(lite_window) -> None:
    """A refusal, not silence: the selection is unchanged and that is the news."""
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_shrink_selection()
    assert win.announcements == ["Nothing smaller to select"]
    assert win.control.GetSelection() == (0, 5)


# --------------------------------------------------------------------- #
# Clearing, restoring, and getting to the start
# --------------------------------------------------------------------- #


def test_unselect_all_clears_and_leaves_the_caret_at_the_start(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(5, 11)
    win.cmd_unselect_all()
    assert win.control.GetSelection() == (5, 5)
    assert win.announcements == ["Selection cleared"]


def test_unselect_all_remembers_it_so_reselect_can_undo_it(lite_window) -> None:
    """Clearing a selection is exactly the action people immediately regret."""
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(5, 11)
    win.cmd_unselect_all()
    win.cmd_reselect()
    assert win.control.GetSelection() == (5, 11)
    assert "Reselected" in win.announcements[-1]


def test_reselect_with_nothing_remembered_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_reselect()
    assert win.announcements == ["No previous selection to restore"]


def test_reselect_clamps_to_a_document_that_has_since_shrunk(lite_window) -> None:
    """The remembered span may no longer exist; that is a sentence, not a crash."""
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(30, 36)
    win.cmd_unselect_all()
    win.control.ChangeValue("tiny")
    win.cmd_reselect()
    assert win.announcements[-1] == "The previous selection is no longer there"


def test_go_to_selection_start_keeps_the_selection(lite_window) -> None:
    """After extending downwards the caret is at the far end; reading starts here.

    The selection has to survive the trip, or "go to the start so I can read it"
    would throw away the thing being read.
    """
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(6, 19)
    win.cmd_go_to_selection_start()
    assert win.control.GetSelection() == (6, 19)
    assert 6 in win.control.shown_positions
    assert win.announcements == ["At the start of the selection"]
    # The caret, which is the entire point and was the bug: SetInsertionPoint
    # followed by SetSelection(start, end) put it straight back at the far end,
    # so the command announced an arrival it had not made (bad.md L13).
    assert win.control.GetInsertionPoint() == 6


def test_go_to_selection_start_with_nothing_selected_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_go_to_selection_start()
    assert win.announcements == ["Nothing is selected"]


# --------------------------------------------------------------------- #
# Marks: where you were standing ten seconds ago
# --------------------------------------------------------------------- #


def test_set_mark_counts_them_in_words_a_listener_can_hear(lite_window) -> None:
    """ "1 mark" and "2 marks", never "1 marks" -- this text is read aloud."""
    win = lite_window(DOC, cursor=2)
    win.cmd_set_mark()
    assert win.announcements[-1] == "Mark set at line 1. 1 mark."
    win.control.SetInsertionPoint(25)
    win.cmd_set_mark()
    assert win.announcements[-1] == "Mark set at line 2. 2 marks."


def test_pop_mark_goes_back_and_uses_the_mark_up(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_set_mark()
    win.control.SetInsertionPoint(30)
    win.cmd_pop_mark()
    assert win.control.GetInsertionPoint() == 2
    assert "no marks left" in win.announcements[-1].lower()


def test_pop_mark_with_an_empty_ring_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_pop_mark()
    assert win.announcements == ["No marks set"]


def test_the_mark_ring_holds_twenty_and_drops_the_oldest(lite_window) -> None:
    """Twenty, because the ring is the shared one now (bad.md L6).

    QuillLite had a plain list of its own capped at ten, with no
    de-duplication, beside ``quill.core.marks.MarkRing``, which is capped at
    twenty and de-dupes. Two implementations of something this simple are not a
    bug on their own; they are the mechanism by which the two editors drift.
    """
    win = lite_window("x" * 100, cursor=0)
    for position in range(25):
        win.control.SetInsertionPoint(position)
        win.cmd_set_mark()
    assert win.announcements[-1].endswith("20 marks.")


def test_marking_the_same_place_twice_does_not_fill_the_ring(lite_window) -> None:
    """The de-duplication QuillLite's own list did not have."""
    win = lite_window("x" * 100, cursor=0)
    for _ in range(5):
        win.control.SetInsertionPoint(7)
        win.cmd_set_mark()
    assert win.announcements[-1].endswith("1 mark.")


def test_a_mark_finds_its_own_text_again_after_an_edit(lite_window) -> None:
    """Marks used to be bare offsets: insert a paragraph above one and it
    pointed at whatever had since moved into that offset (bad.md L6).

    The anchor is the same one the numbered bookmarks take -- a window of text
    around the position, re-found rather than shifted by a length guess, which
    is right for one insertion at the caret and wrong for a Replace All, an
    undo, a paste over a selection and a reload.
    """
    win = lite_window("alpha\nbeta\ngamma\n", cursor=0)
    win.control.SetInsertionPoint(6)  # the start of "beta"
    win.cmd_set_mark()

    win.control.SetInsertionPoint(0)
    win.control.WriteText("a new first line\n")

    win.control.SetInsertionPoint(0)
    win.cmd_pop_mark()
    text = win.control.GetValue()
    assert text[win.control.GetInsertionPoint() :].startswith("beta")


def test_popping_a_mark_can_be_undone_with_back(lite_window) -> None:
    """Pop, list and exchange set the caret straight onto the control, so
    Alt+Left skipped them -- and a Back key that misses some of the places you
    have been is worse than no Back key (bad.md L8)."""
    win = lite_window(DOC, cursor=0)
    win.control.SetInsertionPoint(30)
    win.cmd_set_mark()
    win.control.SetInsertionPoint(2)

    win.cmd_pop_mark()
    assert win.control.GetInsertionPoint() == 30

    # Alt+Left, from where the pop landed.
    assert win.locations.back(win.control.GetInsertionPoint()) == 2


def test_exchange_point_and_mark_swaps_and_selects_between(lite_window) -> None:
    """Two things at once, deliberately: you arrive *and* the span is selected."""
    win = lite_window(DOC, cursor=2)
    win.cmd_set_mark()
    win.control.SetInsertionPoint(11)
    win.cmd_exchange_point_mark()
    assert win.control.GetSelection() == (2, 11)
    assert "Swapped with mark" in win.announcements[-1]


def test_exchange_with_the_mark_where_you_stand_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=5)
    win.cmd_set_mark()
    win.cmd_exchange_point_mark()
    assert win.announcements[-1] == "Cursor and mark are in the same place"


def test_exchange_with_no_marks_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_exchange_point_mark()
    assert win.announcements == ["No marks set"]


# --------------------------------------------------------------------- #
# Reading back and duplicating
# --------------------------------------------------------------------- #


def test_say_selection_reads_a_short_selection_out(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_say_selection()
    assert win.announcements == ["alpha"]


def test_say_selection_summarises_a_long_one_instead_of_reading_it(lite_window) -> None:
    """Forty seconds of speech you cannot usefully interrupt is not an answer."""
    win = lite_window("word " * 200, cursor=0)
    win.control.SetSelection(0, 900)
    win.cmd_say_selection()
    spoken = win.announcements[-1]
    assert spoken.startswith("900 characters")
    assert "Begins:" in spoken and "Ends:" in spoken
    assert len(spoken) < 400


def test_say_selection_with_nothing_selected_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_say_selection()
    assert win.announcements == ["Nothing is selected"]


def test_duplicate_selection_puts_the_copy_straight_after(lite_window) -> None:
    win = lite_window("alpha bravo\n", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_duplicate_selection()
    assert win.control.GetValue() == "alphaalpha bravo\n"
    assert win.announcements[-1] == "Duplicated selection, 5 characters"
    assert win.modified is True


def test_duplicate_with_nothing_selected_duplicates_the_line(lite_window) -> None:
    """Which is what the command is nearly always wanted for."""
    win = lite_window("alpha bravo\ncharlie\n", cursor=3)
    win.cmd_duplicate_selection()
    assert win.control.GetValue().startswith("alpha bravo\nalpha bravo\n")
    assert win.announcements[-1] == "Duplicated line, 11 characters"


def test_duplicate_in_an_empty_document_says_there_is_nothing_to_copy(lite_window) -> None:
    win = lite_window("", cursor=0)
    win.cmd_duplicate_selection()
    assert win.announcements == ["Nothing to duplicate"]
    assert win.modified is False
