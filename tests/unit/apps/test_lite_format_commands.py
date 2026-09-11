"""The Format menu: what reaches the rich editor, and what a plain document is told.

Formatting is a request to a Rich Edit control and there is nothing to read back
from it, so what is testable is the pair the harness records: *the right request
with the right argument*, and the sentence that followed. Both matter. A command
that toggled bold and announced "Italic on" would pass any check that only
watched the editor, and a listener has nothing but the sentence.

The other half of this file is the **refusals**. Nine of these commands do
nothing in a plain text document, and doing nothing quietly is the failure mode
that reads as a broken key -- so every refusal is asserted to be a sentence
naming the reason and, where there is one, the way out.
"""

from __future__ import annotations

import pytest

PLAIN_REFUSAL = "Not available in plain text. Press Control Shift M to switch to rich text."


# --------------------------------------------------------------------------- #
# Bold, italic, underline
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("command", "attr", "label"),
    [
        ("cmd_bold", "Bold", "Bold"),
        ("cmd_italic", "Italic", "Italic"),
        ("cmd_underline", "Underline", "Underline"),
    ],
)
def test_a_font_attribute_toggles_and_says_which_way(lite_window, command, attr, label):
    win = lite_window("hello", mode="rich")

    getattr(win, command)()
    assert ("toggle_font_attr", attr) in win.editor.calls
    assert win.announcements[-1] == f"{label} on"

    getattr(win, command)()
    assert win.announcements[-1] == f"{label} off"


@pytest.mark.parametrize("command", ["cmd_bold", "cmd_italic", "cmd_underline"])
def test_a_font_attribute_marks_the_document_modified(lite_window, command):
    win = lite_window("hello", mode="rich")
    win.modified = False
    getattr(win, command)()
    assert win.modified is True


@pytest.mark.parametrize("command", ["cmd_bold", "cmd_italic", "cmd_underline"])
def test_a_font_attribute_is_refused_in_plain_text_out_loud(lite_window, command):
    win = lite_window("hello", mode="plain")
    getattr(win, command)()
    assert win.announcements[-1] == PLAIN_REFUSAL
    assert win.editor.calls == []


def test_formatting_is_refused_when_rich_text_is_unavailable(lite_window):
    """Rich Edit can be missing. Saying so beats a key that silently does nothing."""
    win = lite_window("hello", mode="rich")
    win.editor.rtf = False
    win.cmd_bold()
    assert win.announcements[-1] == "Rich text formatting is unavailable on this system"
    assert win.editor.calls == []


# --------------------------------------------------------------------------- #
# Alignment
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("command", "alignment", "said"),
    [
        ("cmd_align_left", "left", "Aligned left"),
        ("cmd_align_center", "center", "Centred"),
        ("cmd_align_right", "right", "Aligned right"),
        ("cmd_align_justify", "justify", "Justified"),
    ],
)
def test_each_alignment_reaches_the_editor_and_is_announced(lite_window, command, alignment, said):
    win = lite_window("hello", mode="rich")
    getattr(win, command)()
    assert ("set_alignment", alignment) in win.editor.calls
    assert win.announcements[-1] == said


@pytest.mark.parametrize(
    "command",
    ["cmd_align_left", "cmd_align_center", "cmd_align_right", "cmd_align_justify"],
)
def test_alignment_is_refused_in_plain_text(lite_window, command):
    win = lite_window("hello", mode="plain")
    getattr(win, command)()
    assert win.announcements[-1] == PLAIN_REFUSAL
    assert win.editor.calls == []


def test_the_four_alignments_are_four_different_requests(lite_window):
    """The bug this catches: four menu items wired to one argument.

    Every one of them announces something plausible, and a sighted developer
    sees the text move. Only comparing the arguments finds it.
    """
    win = lite_window("hello", mode="rich")
    for command in ("cmd_align_left", "cmd_align_center", "cmd_align_right", "cmd_align_justify"):
        getattr(win, command)()
    sent = [value for name, value in win.editor.calls if name == "set_alignment"]
    assert len(set(sent)) == 4


# --------------------------------------------------------------------------- #
# Line spacing
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("command", "constant", "said"),
    [
        ("cmd_spacing_single", "LINE_SPACING_SINGLE", "Single spacing"),
        ("cmd_spacing_one_half", "LINE_SPACING_ONE_AND_A_HALF", "One and a half spacing"),
        ("cmd_spacing_double", "LINE_SPACING_DOUBLE", "Double spacing"),
    ],
)
def test_each_line_spacing_reaches_the_editor(lite_window, command, constant, said):
    """The Rich Edit *rule* number, not a multiplier.

    Asserted against the named constant rather than a literal, because the
    numbers are the ones the Text Object Model uses and a test that hard-coded
    1, 5 and 2 would be pinning a coincidence.
    """
    import quill.apps.lite_window_format as fmt

    win = lite_window("hello", mode="rich")
    getattr(win, command)()
    assert ("set_line_spacing", getattr(fmt, constant)) in win.editor.calls
    assert win.announcements[-1] == said


def test_the_three_spacings_are_three_different_rules(lite_window):
    win = lite_window("hello", mode="rich")
    for command in ("cmd_spacing_single", "cmd_spacing_one_half", "cmd_spacing_double"):
        getattr(win, command)()
    sent = [value for name, value in win.editor.calls if name == "set_line_spacing"]
    assert len(set(sent)) == 3


@pytest.mark.parametrize(
    "command", ["cmd_spacing_single", "cmd_spacing_one_half", "cmd_spacing_double"]
)
def test_line_spacing_is_refused_in_plain_text(lite_window, command):
    win = lite_window("hello", mode="plain")
    getattr(win, command)()
    assert win.announcements[-1] == PLAIN_REFUSAL


# --------------------------------------------------------------------------- #
# Headings
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
def test_each_heading_level_reaches_the_editor_and_is_named(lite_window, level):
    win = lite_window("hello", mode="rich")
    getattr(win, f"cmd_heading_{level}")()
    assert ("set_heading", level) in win.editor.calls
    assert win.announcements[-1] == f"Heading {level}"


def test_heading_zero_is_body_text_and_says_so(lite_window):
    """Level 0 is the only one whose announcement is not its number.

    "Heading 0" would be a level that does not exist; the listener needs to hear
    that the paragraph stopped being a heading at all.
    """
    win = lite_window("hello", mode="rich")
    win.cmd_heading_0()
    assert ("set_heading", 0) in win.editor.calls
    assert win.announcements[-1] == "Body text"


@pytest.mark.parametrize("level", [0, 1, 6])
def test_headings_are_refused_in_plain_text(lite_window, level):
    win = lite_window("hello", mode="plain")
    getattr(win, f"cmd_heading_{level}")()
    assert win.announcements[-1] == PLAIN_REFUSAL


def test_a_heading_marks_the_document_modified(lite_window):
    win = lite_window("hello", mode="rich")
    win.modified = False
    win.cmd_heading_2()
    assert win.modified is True


# --------------------------------------------------------------------------- #
# Bullets
# --------------------------------------------------------------------------- #


def test_toggle_bullets_flips_and_announces_both_ways(lite_window):
    win = lite_window("hello", mode="rich")
    win.cmd_toggle_bullets()
    assert ("set_bullets", True) in win.editor.calls
    first = win.announcements[-1]
    win.cmd_toggle_bullets()
    assert ("set_bullets", False) in win.editor.calls
    assert win.announcements[-1] != first, "on and off must not read the same"


def test_toggle_bullets_is_refused_in_plain_text(lite_window):
    win = lite_window("hello", mode="plain")
    win.cmd_toggle_bullets()
    assert win.announcements[-1] == PLAIN_REFUSAL
    assert win.editor.calls == []
