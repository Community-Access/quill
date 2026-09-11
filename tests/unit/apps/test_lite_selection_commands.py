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
    assert win.announcements == ["Selected word, 5 characters"]


def test_select_line_takes_the_line(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_select_line()
    assert win.control.GetSelection() == (0, 19)
    assert win.announcements == ["Selected line, 19 characters"]


def test_select_paragraph_takes_the_run_between_blank_lines(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_select_paragraph()
    assert win.control.GetSelection() == (0, 36)
    assert win.announcements == ["Selected paragraph, 36 characters"]


def test_select_sentence_reports_words_as_well_as_characters(lite_window) -> None:
    """The word count is the half a listener can act on: 9 words is a quantity."""
    win = lite_window(DOC, cursor=2)
    win.cmd_select_sentence()
    start, end = win.control.GetSelection()
    assert end > start
    assert win.announcements == ["Selected sentence, 57 characters, 9 words"]


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
    assert win.announcements[-1] == "Selected word, 5 characters"
    win.cmd_expand_selection()
    assert win.announcements[-1] == "Selected line, 19 characters"


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


def test_the_mark_ring_holds_ten_and_drops_the_oldest(lite_window) -> None:
    win = lite_window("x" * 100, cursor=0)
    for position in range(15):
        win.control.SetInsertionPoint(position)
        win.cmd_set_mark()
    assert win.announcements[-1].endswith("10 marks.")


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
