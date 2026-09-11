"""The empty line after Enter must read as blank, not as the line above it.

Type "This is a test.", press Enter, and ask a screen reader to read the current
line. It should say "blank". For as long as QuillLite has existed it said "This
is a test." instead -- on every empty line at the end of every plain text
document, which in a Notepad replacement is most of them.

The cause was ``EM_SETTEXTMODE`` with ``TM_PLAINTEXT``. In that mode
RICHEDIT50W does not treat the position after a trailing line break as a line of
its own: ``EM_LINEFROMCHAR`` for the caret answers with the *previous* line, and
a screen reader asks the control exactly that question. Rich-text mode and an
untouched control both answer correctly, so the fix was to stop asking for
plain-text mode at all and keep the plain/rich distinction where it belongs --
in the document, not in the control (``RichEditDocument.set_text_mode``).

This is a real-control test on purpose. Nothing in a stub could have caught it:
every layer of QUILL's own arithmetic was right, and the wrong answer came from
the native control. It is also why the check is written as "what does the
control say the caret's line is" rather than "is the flag set" -- the flag is
the cause we found, and the sentence a listener hears is the thing that has to
stay true.
"""

from __future__ import annotations

import sys

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="RICHEDIT50W text modes are a Windows behaviour"
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _pump(times: int = 15) -> None:
    for _ in range(times):
        wx.YieldIfNeeded()


def _caret_line(control) -> tuple[int, str]:
    """The line the *control* says the caret is on, and that line's text.

    ``wx.TextCtrl.PositionToXY`` is ``EM_LINEFROMCHAR`` underneath, which is the
    same question a screen reader asks, so this reads what JAWS would be told.
    """
    _ok, _col, row = control.PositionToXY(control.GetInsertionPoint())
    return row, control.GetLineText(row)


@pytest.mark.parametrize("mode", ["plain", "rich"])
def test_the_line_after_a_trailing_newline_reads_as_blank(wx_app, mode: str) -> None:
    from quill.ui.richedit_editing import RichEditDocument

    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL)
        _pump()
        RichEditDocument(control, mode).set_text_mode(mode)
        control.SetFocus()
        control.WriteText("This is a test.")
        _pump(10)
        control.WriteText("\n")
        _pump()

        row, text = _caret_line(control)

        assert text == "", (
            f"{mode} mode: the caret is on the empty line after Enter and the control "
            f"says it is on line {row}, {text!r}. A screen reader reads that line, so "
            "it speaks the line above instead of saying blank."
        )
    finally:
        frame.Destroy()
        _pump()


def test_the_control_is_never_put_into_plain_text_mode(wx_app) -> None:
    """The document's mode is recorded; the control's own mode is not changed.

    Belt and braces beside the behavioural check above: this one names the cause,
    so a future change that reinstates ``TM_PLAINTEXT`` fails with the reason
    rather than with a puzzling line number.
    """
    from quill.ui.richedit_editing import PLAIN, RichEditDocument

    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL)
        _pump()
        surface = RichEditDocument(control, PLAIN)
        surface.set_text_mode(PLAIN)
        _pump()

        assert surface.mode == PLAIN, "the document is still a plain text document"
        assert surface.current_text_mode() == "rich", (
            "the control must stay in rich-text mode: in plain-text mode it reports "
            "the caret on an empty final line as being on the line above, which is "
            "the line a screen reader then reads out"
        )
    finally:
        frame.Destroy()
        _pump()
