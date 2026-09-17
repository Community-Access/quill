"""The last two dozen: find, headings, windows, bookmarks, deletes, tray pastes.

This file closes the shape-only list to zero. What is in it is a mixture, and
the grouping is by "what a listener gets back" rather than by menu:

* **Find Next before Find.** ``_repeat_find`` opens the Find window when there
  is nothing to repeat, which is the difference between F3 doing nothing and F3
  being useful on a fresh document.
* **Heading navigation works in both modes**, over the point-size ladder in
  rich text and over Markdown hashes in plain -- and says so when a document
  genuinely has none, because a silent key is indistinguishable from a broken
  one.
* **The six numbered bookmarks** exist to be pressed by number and answered by
  number, so the number in the sentence has to be the one that was pressed.
* **Window cycling** is direction-carrying: Ctrl+Tab and Ctrl+Shift+Tab differ
  only in a sign, which is exactly the sort of thing a copy-paste gets wrong.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.richedit_editing import PLAIN, RICH

# --------------------------------------------------------------------------- #
# Find, Find Next, Find Previous
# --------------------------------------------------------------------------- #


def test_find_opens_the_window_seeded_with_the_selection(lite_window, lite_dialogs):
    """Selecting a word and pressing Ctrl+F should not then require typing it."""
    dialog = _findable()
    lite_dialogs.answer("FindDialog", dialog)
    win = lite_window("alpha beta alpha")
    win.control.SetSelection(6, 10)
    win.cmd_find()

    assert lite_dialogs.args_for("FindDialog")[1] == "beta"
    assert dialog.shown == 1


def test_find_falls_back_to_the_last_search_when_nothing_is_selected(lite_window, lite_dialogs):
    lite_dialogs.answer("FindDialog", _findable())
    win = lite_window("alpha beta")
    win._find_options = {"needle": "beta"}
    win.cmd_find()
    assert lite_dialogs.args_for("FindDialog")[1] == "beta"


def test_a_second_find_raises_the_open_window_rather_than_opening_another(
    lite_window, lite_dialogs
):
    """Two Find windows over one document is two places to type and one of them
    is stale. The second press brings the first one forward."""
    dialog = _findable()
    lite_dialogs.answer("FindDialog", dialog)
    win = lite_window("alpha")
    win.cmd_find()
    win.cmd_find()

    assert lite_dialogs.names().count("FindDialog") == 1
    assert dialog.raised == 1


def test_a_destroyed_find_window_is_replaced_rather_than_raised(lite_window, lite_dialogs):
    """``Raise`` on a dead wx object raises RuntimeError.

    Swallowing it and building a fresh window is what stops Ctrl+F stopping
    working for the rest of the session after the Find window is closed.
    """

    class _Dead:
        def Raise(self):  # noqa: N802 - wx API shape
            raise RuntimeError("wrapped C/C++ object has been deleted")

    win = lite_window("alpha")
    win._find_dialog = _Dead()
    lite_dialogs.answer("FindDialog", _findable())
    win.cmd_find()
    assert lite_dialogs.names() == ["FindDialog"]


@pytest.mark.parametrize("invoke", [lambda w: w.cmd_find_next(), lambda w: w.cmd_find_previous()])
def test_repeating_a_search_with_nothing_to_repeat_opens_find(lite_window, lite_dialogs, invoke):
    """F3 on a fresh document has nothing to repeat.

    Doing nothing there is indistinguishable from a broken key, so it opens the
    window instead -- which is also what the user wanted.
    """
    lite_dialogs.answer("FindDialog", _findable())
    win = lite_window("alpha beta")
    invoke(win)
    assert lite_dialogs.names() == ["FindDialog"]


def test_find_next_moves_to_the_next_match(lite_window):
    """From the caret forwards, and a match *at* the caret counts.

    Which is what makes Ctrl+F then F3 land on the first occurrence rather than
    skipping it -- the caret is at the top of the document when a search starts.
    """
    win = lite_window("alpha beta alpha", cursor=0)
    win._find_options = {"needle": "alpha"}
    win.cmd_find_next()
    assert win.control.GetSelection() == (0, 5)


def test_pressing_find_next_again_moves_on(lite_window):
    """The half that matters for a run of presses: it must not stick."""
    win = lite_window("alpha beta alpha", cursor=0)
    win._find_options = {"needle": "alpha"}
    win.cmd_find_next()
    win.cmd_find_next()
    assert win.control.GetSelection() == (11, 16)


def test_find_previous_goes_the_other_way(lite_window):
    win = lite_window("alpha beta alpha", cursor=16)
    win._find_options = {"needle": "alpha"}
    win.cmd_find_previous()
    assert win.control.GetSelection() == (11, 16)


def test_find_next_and_previous_are_not_the_same_direction(lite_window):
    """A sign flip is the classic copy-paste bug in a pair like this, and both
    directions "work" if you only ever test one."""
    forward = lite_window("alpha beta alpha", cursor=6)
    forward._find_options = {"needle": "alpha"}
    forward.cmd_find_next()

    backward = lite_window("alpha beta alpha", cursor=6)
    backward._find_options = {"needle": "alpha"}
    backward.cmd_find_previous()

    assert forward.control.GetSelection() != backward.control.GetSelection()


def _findable():
    class _Dialog:
        shown = 0
        raised = 0

        def Show(self):  # noqa: N802 - wx API shape
            type(self).shown += 1

        def Raise(self):  # noqa: N802 - wx API shape
            type(self).raised += 1

        def Bind(self, *_a, **_k):  # noqa: N802 - wx API shape
            return None

    return _Dialog()


# --------------------------------------------------------------------------- #
# Headings
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "invoke",
    [
        lambda w: w.cmd_next_heading(),
        lambda w: w.cmd_previous_heading(),
        lambda w: w.cmd_list_headings(),
    ],
)
def test_heading_commands_say_there_are_none_when_the_document_has_none(lite_window, invoke):
    """A plain document with no Markdown hashes genuinely has no headings.

    It used to refuse with "only available in rich text", which was wrong in
    the way that matters: plain mode's headings are Markdown, Alt+Shift+Right
    changes their level quite happily, and only *navigation* pretended the
    document had no structure at all.
    """
    win = lite_window("Title\nbody", mode=PLAIN)
    invoke(win)
    assert win.announcements[-1] in {
        "No next heading",
        "No previous heading",
        "No headings in this document",
    }


def test_next_heading_moves_and_says_the_level_and_the_text(lite_window):
    """The level alone says what shape the document is, not where you landed."""
    win = lite_window("Title\nbody\nSecond\nmore", mode=RICH, cursor=0)
    win.editor.heading_rows = [(0, 1, "Title"), (11, 2, "Second")]
    win.cmd_next_heading()

    assert win.control.GetInsertionPoint() == 11
    assert win.announcements[-1] == "Heading 2: Second"


def test_previous_heading_goes_back(lite_window):
    win = lite_window("Title\nbody\nSecond\nmore", mode=RICH, cursor=15)
    win.editor.heading_rows = [(0, 1, "Title"), (11, 2, "Second")]
    win.cmd_previous_heading()
    assert win.control.GetInsertionPoint() == 11


def test_running_out_of_headings_is_announced_in_the_direction_you_were_going(lite_window):
    win = lite_window("Title\nbody", mode=RICH, cursor=0)
    win.editor.heading_rows = []

    win.cmd_next_heading()
    assert win.announcements[-1] == "No next heading"
    win.cmd_previous_heading()
    assert win.announcements[-1] == "No previous heading"


def test_list_headings_says_so_when_there_are_none(lite_window, lite_dialogs):
    win = lite_window("body only", mode=RICH)
    win.editor.heading_rows = []
    win.cmd_list_headings()
    assert win.announcements[-1] == "No headings in this document"
    assert lite_dialogs.names() == []


def test_choosing_a_heading_from_the_list_goes_there(lite_window, lite_dialogs):
    win = lite_window("Title\nbody\nSecond\nmore", mode=RICH, cursor=0)
    win.editor.heading_rows = [(0, 1, "Title"), (11, 2, "Second")]
    lite_dialogs.answer("choose_heading", 11)
    win.cmd_list_headings()
    assert win.control.GetInsertionPoint() == 11


def test_cancelling_the_heading_list_leaves_the_caret_alone(lite_window, lite_dialogs):
    win = lite_window("Title\nbody\nSecond", mode=RICH, cursor=3)
    win.editor.heading_rows = [(0, 1, "Title"), (11, 2, "Second")]
    win.cmd_list_headings()
    assert win.control.GetInsertionPoint() == 3
    assert win.control.focused is True


# --------------------------------------------------------------------------- #
# Marks
# --------------------------------------------------------------------------- #


def test_list_marks_says_so_when_there_are_none(lite_window, lite_dialogs):
    win = lite_window("one\ntwo")
    win.cmd_list_marks()
    assert win.announcements[-1] == "No marks set"
    assert lite_dialogs.names() == []


def test_list_marks_offers_them_newest_first_with_the_line_and_a_preview(lite_window, lite_dialogs):
    """Newest first because the mark you want back is almost always the last one
    you dropped, and a listener reads a list from the top."""
    win = lite_window("first line\nsecond line\nthird line")
    win.control.SetInsertionPoint(0)
    win.cmd_set_mark()
    win.control.SetInsertionPoint(11)
    win.cmd_set_mark()
    win.cmd_list_marks()

    rows = lite_dialogs.kwargs_for("choose_from_rows")["rows"]
    assert [position for position, _label in rows] == [11, 0]
    assert "second line" in rows[0][1]
    assert rows[0][1].startswith("Line 2:")


def test_a_blank_line_mark_still_reads_as_something(lite_window, lite_dialogs):
    """An empty preview would be a row a listener cannot tell from the next."""
    win = lite_window("first\n\nthird")
    win.control.SetInsertionPoint(6)
    win.cmd_set_mark()
    win.cmd_list_marks()
    assert "(blank line)" in lite_dialogs.kwargs_for("choose_from_rows")["rows"][0][1]


def test_choosing_a_mark_goes_there_and_says_the_line(lite_window, lite_dialogs):
    win = lite_window("first line\nsecond line")
    win.control.SetInsertionPoint(11)
    win.cmd_set_mark()
    win.control.SetInsertionPoint(0)
    lite_dialogs.answer("choose_from_rows", 11)
    win.cmd_list_marks()

    assert win.control.GetInsertionPoint() == 11
    assert win.announcements[-1] == "Line 2"


def test_a_mark_past_the_end_of_a_shortened_document_is_clamped(lite_window, lite_dialogs):
    """Marks are offsets and the document can shrink under them. Clamping beats
    refusing: the place is gone but the neighbourhood is still there."""
    win = lite_window("first line\nsecond line")
    win.control.SetInsertionPoint(20)
    win.cmd_set_mark()
    win.control.ChangeValue("short")
    lite_dialogs.answer("choose_from_rows", 20)
    win.cmd_list_marks()
    assert win.control.GetInsertionPoint() == len("short")


# --------------------------------------------------------------------------- #
# Numbered bookmarks
# --------------------------------------------------------------------------- #


_NUMBERED = [
    (lambda w: w.cmd_set_bookmark_4(), 4),
    (lambda w: w.cmd_set_bookmark_5(), 5),
    (lambda w: w.cmd_set_bookmark_6(), 6),
    (lambda w: w.cmd_set_bookmark_7(), 7),
    (lambda w: w.cmd_set_bookmark_8(), 8),
    (lambda w: w.cmd_set_bookmark_9(), 9),
]


@pytest.mark.parametrize(("invoke", "number"), _NUMBERED)
def test_each_numbered_bookmark_lands_in_its_own_slot(lite_window, invoke, number):
    """Nine keys, nine slots, and the number spoken back is the one pressed.

    Six of these were wired by hand, which is exactly where an off-by-one hides
    -- and a bookmark that answers to the wrong number is worse than none.
    """
    win = lite_window("some text here", cursor=5)
    invoke(win)
    assert win.bookmarks.get(number) is not None
    assert win.announcements[-1].startswith(f"Bookmark {number} set:")


def test_the_six_numbered_bookmarks_are_six_different_slots(lite_window):
    win = lite_window("some text here", cursor=5)
    for invoke, _number in _NUMBERED:
        invoke(win)
    assert sorted(mark.number for mark in win.bookmarks.all()) == [4, 5, 6, 7, 8, 9]


@pytest.mark.parametrize(("invoke", "number"), _NUMBERED)
def test_a_numbered_bookmark_remembers_where_the_caret_was(lite_window, invoke, number):
    win = lite_window("alpha beta gamma", cursor=11)
    invoke(win)
    assert win.bookmarks.get(number).position == 11


def test_setting_the_same_number_twice_moves_it_rather_than_adding_one(lite_window):
    """A numbered slot is a slot. Two bookmarks answering to 4 would make the
    key ambiguous, which is the one thing a numbered key must not be."""
    win = lite_window("alpha beta gamma", cursor=0)
    win.cmd_set_bookmark_4()
    win.control.SetInsertionPoint(11)
    win.cmd_set_bookmark_4()
    assert win.bookmarks.get(4).position == 11
    assert [mark.number for mark in win.bookmarks.all()] == [4]


# --------------------------------------------------------------------------- #
# Structured deletes
# --------------------------------------------------------------------------- #


def test_delete_to_line_start_removes_the_text_before_the_caret(lite_window):
    win = lite_window("first line\nsecond line", cursor=17)
    win.cmd_delete_to_line_start()
    assert win.control.GetValue() == "first line\n line"
    # The announcement quotes what went, like the other structured deletes.
    assert win.announcements[-1].startswith("Deleted to start of line")
    assert "second" in win.announcements[-1]


def test_delete_to_line_start_at_the_start_says_so_rather_than_nothing(lite_window):
    """At column 1 the key genuinely cannot do anything, and silence there is
    indistinguishable from an unbound key."""
    win = lite_window("first line\nsecond", cursor=11)
    win.cmd_delete_to_line_start()
    assert win.control.GetValue() == "first line\nsecond"
    assert win.announcements[-1] == "Already at the start of the line"


def test_delete_paragraph_removes_the_block_around_the_caret(lite_window):
    win = lite_window("one\ntwo\n\nthree\nfour", cursor=1)
    win.cmd_delete_paragraph()
    assert "one" not in win.control.GetValue()
    assert "three" in win.control.GetValue()
    # The announcement quotes what went, not merely that something did: a
    # paragraph is the largest thing one key here removes, and the listener has
    # no other way to know which one it caught.
    assert win.announcements[-1].startswith("Deleted paragraph")
    assert "one two" in win.announcements[-1]


def test_delete_paragraph_on_an_empty_document_says_there_is_nothing(lite_window):
    win = lite_window("")
    win.cmd_delete_paragraph()
    assert win.announcements[-1] == "Nothing to delete"


@pytest.mark.parametrize(
    "invoke",
    [lambda w: w.cmd_delete_to_line_start(), lambda w: w.cmd_delete_paragraph()],
)
def test_a_structured_delete_can_be_put_back_somewhere_else(lite_window, invoke):
    """What distinguishes these from undo: the text goes on the deletion ring
    and Restore Deletion puts it back *at the caret*."""
    win = lite_window("first line\nsecond line", cursor=17)
    invoke(win)
    win.cmd_restore_deletion()
    assert win.announcements[-1] != "Nothing deleted yet in this document"


# --------------------------------------------------------------------------- #
# Pasting from the tray and the clip library
# --------------------------------------------------------------------------- #


def test_paste_from_tray_says_how_to_fill_an_empty_tray(lite_window, lite_dialogs):
    """A refusal that names the key that fixes it. "The copy tray is empty" on
    its own leaves somebody with no next move.

    The key is read out of the keymap since 2026-09-16. It was typed into the
    sentence as Control Shift 0, which is QUILL's paste-slot-10 and has not been
    Copy to Tray here since before 1.0 (bad.md C7)."""
    win = lite_window("hello")
    win.cmd_paste_from_tray()
    assert "Control Alt Y" in win.announcements[-1]
    assert lite_dialogs.names() == []


def test_paste_from_tray_offers_only_the_slots_with_something_in_them(lite_window, lite_dialogs):
    win = lite_window("hello", cursor=5)
    win.app.copy_tray.copy_to(2, "second slot")
    win.app.copy_tray.copy_to(5, "fifth slot")
    win.cmd_paste_from_tray()

    rows = lite_dialogs.kwargs_for("choose_from_rows")["rows"]
    assert [number for number, _label in rows] == [2, 5]


def test_choosing_a_tray_slot_inserts_it_and_names_the_slot(lite_window, lite_dialogs):
    win = lite_window("hello ", cursor=6)
    win.app.copy_tray.copy_to(3, "world")
    lite_dialogs.answer("choose_from_rows", 3)
    win.cmd_paste_from_tray()

    assert win.control.GetValue() == "hello world"
    assert win.announcements[-1] == "Pasted tray slot 3"


def test_cancelling_the_tray_pastes_nothing(lite_window, lite_dialogs):
    win = lite_window("hello", cursor=5)
    win.app.copy_tray.copy_to(1, "world")
    win.cmd_paste_from_tray()
    assert win.control.GetValue() == "hello"


def test_paste_clip_says_so_when_the_library_is_empty(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.cmd_paste_clip()
    assert win.announcements[-1] == "The clip library is empty"
    assert lite_dialogs.names() == []


def test_paste_clip_inserts_the_chosen_entry(lite_window, lite_dialogs):
    from quill.core.clip_library import Fragment

    win = lite_window("hello ", cursor=6)
    win.app.clip_library.remember(Fragment(markup="world"))
    index = win.app.clip_library.all_entries()[0][0]
    lite_dialogs.answer("choose_from_rows", index)
    win.cmd_paste_clip()

    assert win.control.GetValue() == "hello world"
    assert win.announcements[-1] == "Pasted from the clip library"


def test_the_clip_library_marks_favourites_in_the_list(lite_window, lite_dialogs):
    """A favourite is a clip somebody chose to keep, and the list is newest
    first -- so without the marker it sinks out of sight like any other."""
    from quill.core.clip_library import Fragment

    win = lite_window("hello")
    win.app.clip_library.remember(Fragment(markup="kept"))
    index = win.app.clip_library.all_entries()[0][0]
    win.app.clip_library.set_favorite(index, True)
    win.cmd_paste_clip()

    rows = lite_dialogs.kwargs_for("choose_from_rows")["rows"]
    assert any(label.startswith("Favourite: ") for _index, label in rows)


# --------------------------------------------------------------------------- #
# Font size, Describe, and the mode switch
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("invoke", "larger"),
    [(lambda w: w.cmd_grow_font(), True), (lambda w: w.cmd_shrink_font(), False)],
)
def test_growing_and_shrinking_step_the_selection_in_opposite_directions(
    lite_window, invoke, larger
):
    win = lite_window("hello", mode=RICH)
    before = win.editor.font_size
    invoke(win)
    assert (win.editor.font_size > before) is larger
    assert win.announcements[-1].endswith(" point")
    assert win.modified is True


@pytest.mark.parametrize("invoke", [lambda w: w.cmd_grow_font(), lambda w: w.cmd_shrink_font()])
def test_font_stepping_is_refused_outside_rich_text_and_names_this_document(lite_window, invoke):
    """Growing the *selection's* font is rich text and nothing else.

    An untitled buffer has no markup either, so the refusal offers **both** ways
    forward -- rich text, or giving this document a markup language -- rather
    than the single piece of advice that used to be right about half the time.
    """
    win = lite_window("hello", mode=PLAIN)
    invoke(win)
    said = win.announcements[-1]
    assert "no formatting" in said
    assert "Alt Shift F" in said
    assert "Control Alt F6" in said
    assert win.editor.calls == []


def test_describe_says_plain_text_in_a_plain_document(lite_window):
    """Two words rather than a refusal: "Plain text" *is* the description, and
    the question was what the formatting at the cursor is."""
    win = lite_window("hello", mode=PLAIN)
    win.cmd_describe()
    assert win.announcements[-1] == "Plain text"


def test_describe_reads_the_formatting_back_in_rich_text(lite_window):
    """Because the codes are hidden, this is the only way to hear them."""
    win = lite_window("hello", mode=RICH)
    win.cmd_describe()
    assert win.announcements[-1] == "Body text"


def test_switch_mode_flips_between_plain_and_rich_and_says_which(lite_window, monkeypatch):
    # Leaving rich asks first -- it rewrites the buffer (bad.md R6) -- so the
    # question is answered here rather than opening a message box in CI.
    from quill.apps import lite_window_mode as modemod

    monkeypatch.setattr(modemod, "show_message_box", lambda *_a, **_k: wx.YES)

    win = lite_window("hello", mode=PLAIN)
    win.cmd_switch_mode()
    assert win.editor.mode == RICH
    assert win.announcements[-1] == "Rich text mode"

    win.cmd_switch_mode()
    assert win.editor.mode == PLAIN
    assert win.announcements[-1] == "Plain text mode"


# --------------------------------------------------------------------------- #
# Cycling between windows
# --------------------------------------------------------------------------- #


def test_next_and_previous_window_cycle_in_opposite_directions(lite_window):
    win = lite_window("hello")
    win.cmd_next_window()
    win.cmd_previous_window()
    assert win.app.cycled == [1, -1]


def test_ctrl_f6_is_the_same_move_as_ctrl_tab(lite_window):
    """Both are bound rather than one. Ctrl+F6 is what the platform documents
    and a long-time Windows user reaches for; Ctrl+Tab is what everyone else
    presses, and a key somebody expects and does not get reads as a broken app.
    """
    win = lite_window("hello")
    win.cmd_next_window()
    win.cmd_next_window_mdi()
    assert win.app.cycled == [1, 1]
