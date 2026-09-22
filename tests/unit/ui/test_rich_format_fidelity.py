r"""GATE-RICH-ROUNDTRIP: formatting a user applies must survive being saved.

Asked directly, after a user found that three headings saved to ``.rtf`` opened
in Word as three ordinary paragraphs: "are we sure that all formatting and
styles will come across when saving, and if not we need to ensure this so these
types of gaps do not exist."

Nobody was sure, because nothing checked. The heading gap had every appearance
of working -- the editor saved a file, reopened it, and found its own headings
again, because it recognises its own point-size ladder. What it did not write
was the *structure*: no stylesheet, no style reference, no outline level, which
is all Word has to go on. A round trip through our own reader cannot catch that
class of bug, and a round trip through Word cannot be automated. So this gate
checks both halves separately.

**What the control keeps.** Each attribute is applied through the same method
the menu command calls, saved with save_rtf, loaded back into a *second* control
with load_rtf, and read back. An attribute that does not survive fails here
under its own name.

**What the file declares.** Some things are true of a document and invisible to
a reader that only asks the control what it sees -- a heading is the example
that cost us. Those are asserted against the saved bytes.

The gate skips where the native control is not: a non-Windows box, or a build
without comtypes. It must not be turned into a mock -- a mock of RichEdit would
have passed happily for the whole time the heading bug was shipping.
"""

from __future__ import annotations

import os
import tempfile

import pytest
import wx

from quill.core.heading_ladder import HEADING_POINT_SIZES, heading_level_for_font

#: Written out rather than escaped: the assertions below are about RTF control
#: words, and a test that got one backslash wrong would assert nothing.
_BACKSLASH = chr(92)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _surface(frame):
    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    control = create_richedit_rtf(wx, frame, wx.TE_MULTILINE)
    return control, getattr(control, "quill_richedit", None)


@pytest.fixture()
def editors(wx_app):
    """Two rich controls: one to format and save from, one to load back into.

    A second control rather than the same one, because reloading into the
    control that just saved can pass on state the file never carried.
    """
    frame = wx.Frame(None, size=(900, 500))
    control, wrapper = _surface(frame)
    reader_control, reader = _surface(frame)
    if wrapper is None or reader is None or not wrapper.rtf_available():
        frame.Destroy()
        pytest.skip("no native Rich Edit / TOM on this build")
    wrapper.set_text_mode("rich")
    reader.set_text_mode("rich")
    frame.Show()
    wx_app.Yield()
    yield control, wrapper, reader_control, reader
    frame.Destroy()
    wx_app.Yield()


def _round_trip(wrapper, reader, wx_app) -> str:
    """Save what *wrapper* holds, load it into *reader*, return the saved RTF."""
    wx_app.Yield()
    path = os.path.join(tempfile.mkdtemp(prefix="quill_fidelity_"), "document.rtf")
    wrapper.save_rtf(path)
    reader.load_rtf(path)
    wx_app.Yield()
    with open(path, encoding="latin-1") as handle:
        return handle.read()


def _select_all(control, text: str) -> None:
    control.SetValue(text)
    control.SetSelection(0, len(text))


# --------------------------------------------------------------------------- #
# what the control keeps


@pytest.mark.parametrize(
    ("name", "apply_it", "expected"),
    [
        ("bold", lambda w: w.apply_bold(), "bold"),
        ("italic", lambda w: w.apply_italic(), "italic"),
        ("underline", lambda w: w.apply_underline(), "underline"),
        ("font size", lambda w: w.set_font_size(18), "18"),
        ("font name", lambda w: w.set_font_name("Georgia"), "georgia"),
        ("centred", lambda w: w.set_alignment("center"), "cent"),
        ("right aligned", lambda w: w.set_alignment("right"), "right"),
    ],
)
def test_the_control_keeps_what_was_applied(editors, wx_app, name, apply_it, expected) -> None:
    """Apply it, save, load into another control, and ask that one what it has."""
    control, wrapper, reader_control, reader = editors
    _select_all(control, "formatted text")
    apply_it(wrapper)
    _round_trip(wrapper, reader, wx_app)
    reader_control.SetInsertionPoint(2)
    described = reader.caret_format_description().lower()
    assert expected in described, f"{name} did not survive the save: {described!r}"


def test_the_words_survive(editors, wx_app) -> None:
    control, wrapper, reader_control, reader = editors
    _select_all(control, "the words themselves")
    wrapper.apply_bold()
    _round_trip(wrapper, reader, wx_app)
    assert "the words themselves" in reader.get_plain_text()


@pytest.mark.parametrize("level", sorted(HEADING_POINT_SIZES))
def test_a_heading_reopens_at_the_level_it_was_saved_at(editors, wx_app, level) -> None:
    control, wrapper, reader_control, reader = editors
    _select_all(control, "A heading")
    wrapper.set_heading(level)
    _round_trip(wrapper, reader, wx_app)
    reader_control.SetInsertionPoint(2)
    assert reader.heading_level_at_caret() == level


def test_a_bulleted_list_is_still_a_list(editors, wx_app) -> None:
    control, wrapper, reader_control, reader = editors
    _select_all(control, "first\nsecond\nthird")
    wrapper.set_bullets(True)
    _round_trip(wrapper, reader, wx_app)
    reader_control.SetInsertionPoint(2)
    assert reader.bullets_at_caret(), "the bullets were lost on save"


# --------------------------------------------------------------------------- #
# what the file declares, which is the half our own reader cannot see


@pytest.mark.parametrize("level", sorted(HEADING_POINT_SIZES))
def test_the_saved_file_names_the_heading_style(editors, wx_app, level) -> None:
    """The reported gap: Word needs a style reference, not a big bold paragraph.

    Reading the file back into our own control proves nothing here -- it found
    its headings by their size the whole time the bug was live.
    """
    control, wrapper, reader_control, reader = editors
    _select_all(control, "A heading")
    wrapper.set_heading(level)
    rtf = _round_trip(wrapper, reader, wx_app)
    assert f"{_BACKSLASH}s{level}" in rtf
    assert f"{_BACKSLASH}outlinelevel{level - 1}" in rtf
    assert f"heading {level};" in rtf, "the stylesheet entry Word matches by name"


def test_the_saved_file_carries_a_stylesheet(editors, wx_app) -> None:
    control, wrapper, reader_control, reader = editors
    _select_all(control, "A heading")
    wrapper.set_heading(2)
    rtf = _round_trip(wrapper, reader, wx_app)
    assert _BACKSLASH + "stylesheet" in rtf


def test_bold_body_text_is_not_a_heading(editors, wx_app) -> None:
    """The other half of the same report: Ctrl+B announced "heading level 4".

    A rich heading is a ladder point size plus bold, Heading 4 is twelve point,
    and twelve point was what a paragraph naming no size was written at.
    """
    control, wrapper, reader_control, reader = editors
    _select_all(control, "ordinary emphatic text")
    wrapper.apply_bold()
    _round_trip(wrapper, reader, wx_app)
    reader_control.SetInsertionPoint(2)
    assert reader.heading_level_at_caret() is None, "bold body text is being reported as a heading"
    assert heading_level_for_font(11.0, bold=True) is None


@pytest.mark.parametrize(
    ("name", "apply_it", "control_word"),
    [
        ("text colour", lambda w: w.set_color("#c80000"), "cf"),
        ("highlight", lambda w: w.set_highlight("#ffff00"), "highlight"),
        ("line spacing", lambda w: w.set_line_spacing(5), "sl"),
    ],
)
def test_the_saved_file_carries_what_the_reader_cannot_describe(
    editors, wx_app, name, apply_it, control_word
) -> None:
    """Colour, highlight and line spacing, asserted against the bytes.

    ``caret_format_description`` answers "Segoe UI, 9 point" for coloured text:
    it describes the face, the size and the weight and says nothing about
    colour, so reading it back through the control would assert nothing at all.
    That is the same blind spot that let the heading gap through, and the answer
    is the same -- ask the file.
    """
    control, wrapper, reader_control, reader = editors
    _select_all(control, "text with something applied to it")
    apply_it(wrapper)
    rtf = _round_trip(wrapper, reader, wx_app)
    assert _BACKSLASH + control_word in rtf, f"{name} is not in the saved file"


# --------------------------------------------------------------------------- #
# Normal Text: the way back out of formatting


@pytest.mark.parametrize(
    ("name", "apply_it"),
    [
        ("bold", lambda w: w.apply_bold()),
        ("italic", lambda w: w.apply_italic()),
        ("underline", lambda w: w.apply_underline()),
        ("a heading", lambda w: w.set_heading(1)),
        ("a big font", lambda w: w.set_font_size(24)),
        ("a colour", lambda w: w.set_color("#c80000")),
        ("an alignment", lambda w: w.set_alignment("center")),
        ("a list", lambda w: w.set_bullets(True)),
    ],
)
def test_normal_text_takes_it_off_again(editors, wx_app, name, apply_it) -> None:
    """Word's Ctrl+Shift+N, asked for while testing and checked on the real control.

    One command has to undo every other one in the menu, so every other one is
    applied here and the result is read back. The heading case is the sharp end:
    a heading is a size and a bold, and if either survived the paragraph would
    still be a heading to the navigation and the headings list.
    """
    control, wrapper, reader_control, reader = editors
    _select_all(control, "text with something applied")
    apply_it(wrapper)
    wx_app.Yield()
    _select_all(control, "text with something applied")
    wrapper.clear_formatting()
    _round_trip(wrapper, reader, wx_app)
    reader_control.SetInsertionPoint(2)
    assert reader.heading_level_at_caret() is None, f"{name} left a heading behind"
    described = reader.caret_format_description().lower()
    for leftover in ("bold", "italic", "underline", "cent", "right"):
        assert leftover not in described, f"{name} survived Normal Text: {described!r}"


def test_normal_text_leaves_the_words_alone(editors, wx_app) -> None:
    control, wrapper, reader_control, reader = editors
    _select_all(control, "the words themselves")
    wrapper.apply_bold()
    _select_all(control, "the words themselves")
    wrapper.clear_formatting()
    _round_trip(wrapper, reader, wx_app)
    assert "the words themselves" in reader.get_plain_text()


def test_normal_text_leaves_the_typeface_alone(editors, wx_app) -> None:
    """A document's face is part of the document, not a stray attribute."""
    control, wrapper, reader_control, reader = editors
    _select_all(control, "set in Georgia on purpose")
    wrapper.set_font_name("Georgia")
    _select_all(control, "set in Georgia on purpose")
    wrapper.clear_formatting()
    _round_trip(wrapper, reader, wx_app)
    reader_control.SetInsertionPoint(2)
    assert "georgia" in reader.caret_format_description().lower()
