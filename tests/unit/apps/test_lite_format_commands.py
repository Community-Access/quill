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


#: ``(invoke, editor argument, spoken label)`` for the three font attributes.
#: The command is a **lambda that calls it**, not its name as a string, and
#: that is not a style preference: GATE-LITE-COVER detects coverage by finding
#: an attribute call in the AST, so ``getattr(win, name)()`` over a
#: parametrized string reads as no coverage at all -- which is what it did
#: until 2026-09-11, leaving fourteen genuinely tested handlers recorded as
#: untested. A lambda keeps the table and puts a real ``win.cmd_italic()`` in
#: the source, where the scanner and a human reader can both see it.
_ATTRS = [
    (lambda w: w.cmd_bold(), "Bold", "Bold"),
    (lambda w: w.cmd_italic(), "Italic", "Italic"),
    (lambda w: w.cmd_underline(), "Underline", "Underline"),
]


@pytest.mark.parametrize(("invoke", "attr", "label"), _ATTRS)
def test_a_font_attribute_toggles_and_says_which_way(lite_window, invoke, attr, label):
    win = lite_window("hello", mode="rich")

    invoke(win)
    assert ("toggle_font_attr", attr) in win.editor.calls
    assert win.announcements[-1] == f"{label} on"

    invoke(win)
    assert win.announcements[-1] == f"{label} off"


@pytest.mark.parametrize(("invoke", "attr", "label"), _ATTRS)
def test_a_font_attribute_marks_the_document_modified(lite_window, invoke, attr, label):
    win = lite_window("hello", mode="rich")
    win.modified = False
    invoke(win)
    assert win.modified is True


@pytest.mark.parametrize(("invoke", "attr", "label"), _ATTRS)
def test_a_font_attribute_is_refused_in_plain_text_out_loud(lite_window, invoke, attr, label):
    win = lite_window("hello", mode="plain")
    invoke(win)
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


_ALIGNMENTS = [
    (lambda w: w.cmd_align_left(), "left", "Aligned left"),
    (lambda w: w.cmd_align_center(), "center", "Centred"),
    (lambda w: w.cmd_align_right(), "right", "Aligned right"),
    (lambda w: w.cmd_align_justify(), "justify", "Justified"),
]


@pytest.mark.parametrize(("invoke", "alignment", "said"), _ALIGNMENTS)
def test_each_alignment_reaches_the_editor_and_is_announced(lite_window, invoke, alignment, said):
    win = lite_window("hello", mode="rich")
    invoke(win)
    assert ("set_alignment", alignment) in win.editor.calls
    assert win.announcements[-1] == said


@pytest.mark.parametrize(("invoke", "alignment", "said"), _ALIGNMENTS)
def test_alignment_is_refused_in_plain_text(lite_window, invoke, alignment, said):
    win = lite_window("hello", mode="plain")
    invoke(win)
    assert win.announcements[-1] == PLAIN_REFUSAL
    assert win.editor.calls == []


def test_the_four_alignments_are_four_different_requests(lite_window):
    """The bug this catches: four menu items wired to one argument.

    Every one of them announces something plausible, and a sighted developer
    sees the text move. Only comparing the arguments finds it.
    """
    win = lite_window("hello", mode="rich")
    win.cmd_align_left()
    win.cmd_align_center()
    win.cmd_align_right()
    win.cmd_align_justify()
    sent = [value for name, value in win.editor.calls if name == "set_alignment"]
    assert len(set(sent)) == 4


# --------------------------------------------------------------------------- #
# Line spacing
# --------------------------------------------------------------------------- #


_SPACINGS = [
    (lambda w: w.cmd_spacing_single(), "LINE_SPACING_SINGLE", "Single spacing"),
    (
        lambda w: w.cmd_spacing_one_half(),
        "LINE_SPACING_ONE_AND_A_HALF",
        "One and a half spacing",
    ),
    (lambda w: w.cmd_spacing_double(), "LINE_SPACING_DOUBLE", "Double spacing"),
]


@pytest.mark.parametrize(("invoke", "constant", "said"), _SPACINGS)
def test_each_line_spacing_reaches_the_editor(lite_window, invoke, constant, said):
    """The Rich Edit *rule* number, not a multiplier.

    Asserted against the named constant rather than a literal, because the
    numbers are the ones the Text Object Model uses and a test that hard-coded
    1, 5 and 2 would be pinning a coincidence.
    """
    import quill.apps.lite_window_format as fmt

    win = lite_window("hello", mode="rich")
    invoke(win)
    assert ("set_line_spacing", getattr(fmt, constant)) in win.editor.calls
    assert win.announcements[-1] == said


def test_the_three_spacings_are_three_different_rules(lite_window):
    win = lite_window("hello", mode="rich")
    win.cmd_spacing_single()
    win.cmd_spacing_one_half()
    win.cmd_spacing_double()
    sent = [value for name, value in win.editor.calls if name == "set_line_spacing"]
    assert len(set(sent)) == 3


@pytest.mark.parametrize(("invoke", "constant", "said"), _SPACINGS)
def test_line_spacing_is_refused_in_plain_text(lite_window, invoke, constant, said):
    win = lite_window("hello", mode="plain")
    invoke(win)
    assert win.announcements[-1] == PLAIN_REFUSAL


# --------------------------------------------------------------------------- #
# Headings
# --------------------------------------------------------------------------- #


_HEADINGS = [
    (lambda w: w.cmd_heading_1(), 1),
    (lambda w: w.cmd_heading_2(), 2),
    (lambda w: w.cmd_heading_3(), 3),
    (lambda w: w.cmd_heading_4(), 4),
    (lambda w: w.cmd_heading_5(), 5),
    (lambda w: w.cmd_heading_6(), 6),
]


@pytest.mark.parametrize(("invoke", "level"), _HEADINGS)
def test_each_heading_level_reaches_the_editor_and_is_named(lite_window, invoke, level):
    win = lite_window("hello", mode="rich")
    invoke(win)
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


@pytest.mark.parametrize(
    "invoke",
    [lambda w: w.cmd_heading_0(), *(entry[0] for entry in _HEADINGS)],
)
def test_headings_are_refused_in_plain_text(lite_window, invoke):
    win = lite_window("hello", mode="plain")
    invoke(win)
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
