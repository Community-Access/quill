"""The braille fix and a correct final empty line, at the same time.

``SES_EMULATESYSEDIT`` is the #616/#813 braille fix (text from cell 1, selection
dots 7-8) and it is on by default. Its one cost was that an emulated RichEdit
answers the caret's line wrongly at the very end of a document that ends in a
paragraph mark, which is the question a screen reader asks: type "This is a
test.", press Enter, and JAWS said "This is a test." where it should have said
"blank".

That was a trade -- braille or blank lines, pick one -- until the answers were
measured (``scripts/jaws_blank_line_repro.md``). The control's *own* facts stay
right under the flag: the line count, the index of an explicit line, the text of
the empty line. Only the character-to-line mapping past the start of the final
line goes wrong, and it contradicts those facts. So the right answer is
computable, and :mod:`quill.ui.richedit_line_fix` supplies it from a window
subclass -- where a screen reader's cross-process ``SendMessage`` will find it.

These are real-control tests for the same reason
``test_richedit_empty_last_line.py`` is: every layer of QUILL's own arithmetic
was already right, and the wrong answer came from the native control. They are
written as "what does the control say the caret's line is", because that is the
sentence a listener hears.
"""

from __future__ import annotations

import ctypes
import sys

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="SES_EMULATESYSEDIT is a Windows RichEdit behaviour"
)

_EM_GETEDITSTYLE = 0x0400 + 205
_EM_EXLINEFROMCHAR = 0x0400 + 54
_EM_LINELENGTH = 0x00C1
_SES_EMULATESYSEDIT = 0x00000001


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _pump(times: int = 15) -> None:
    for _ in range(times):
        wx.YieldIfNeeded()


def _send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    send = user32.SendMessageW
    send.restype = ctypes.c_longlong
    send.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong]
    return int(send(ctypes.c_void_p(hwnd), msg, wparam, lparam))


def _caret_line(control) -> tuple[int, str]:
    """The line the *control* says the caret is on, and that line's text.

    ``wx.TextCtrl.PositionToXY`` is ``EM_EXLINEFROMCHAR`` underneath -- the same
    question a screen reader asks -- so this reads what JAWS would be told.
    """
    _ok, _col, row = control.PositionToXY(control.GetInsertionPoint())
    return row, control.GetLineText(row)


def _editor(frame, *, emulate: bool):
    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    control = create_richedit_rtf(
        wx, frame, wx.TE_MULTILINE | wx.BORDER_NONE, emulate_system_edit=emulate
    )
    _pump()
    return control


def test_the_empty_line_after_enter_reads_as_blank_with_the_braille_fix_on(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = _editor(frame, emulate=True)
        control.SetFocus()
        control.WriteText("This is a test.")
        _pump(10)
        control.WriteText("\n")
        _pump(10)

        row, text = _caret_line(control)

        assert text == "", (
            "the caret is on the empty line after Enter and the control says it is on "
            f"line {row}, {text!r}. A screen reader reads that line, so it speaks the "
            "line above instead of saying blank."
        )
    finally:
        frame.Destroy()
        _pump()


def test_the_braille_fix_is_still_applied(wx_app) -> None:
    """The point of the correction is that nothing had to be given up for it."""
    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = _editor(frame, emulate=True)
        style = _send(control.GetHandle(), _EM_GETEDITSTYLE)

        assert style & _SES_EMULATESYSEDIT, (
            "SES_EMULATESYSEDIT is what puts braille output in cell 1 and the dots 7-8 "
            "on a selection (#616/#813); correcting the line answers must not cost it"
        )
    finally:
        frame.Destroy()
        _pump()


def test_the_control_agrees_with_itself_about_the_final_line(wx_app) -> None:
    """The four line questions must give one story, not three.

    A screen reader may ask any of them. Under the raw flag they disagreed:
    line 1 started at character 16 and character 16 was said to be on line 0,
    whose length was reported as 15.
    """
    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = _editor(frame, emulate=True)
        control.SetFocus()
        control.WriteText("This is a test.\n")
        _pump(10)
        control.SetInsertionPoint(control.GetLastPosition())
        _pump()

        hwnd = control.GetHandle()
        position = control.GetInsertionPoint()
        last = control.GetNumberOfLines() - 1

        assert _send(hwnd, _EM_EXLINEFROMCHAR, 0, position) == last
        assert _send(hwnd, _EM_LINELENGTH, position, 0) == 0, (
            "the final line is empty, so its length is 0; the emulated control "
            "reported the length of the line above instead"
        )
    finally:
        frame.Destroy()
        _pump()


def test_interior_lines_are_left_alone(wx_app) -> None:
    """The correction may only speak where the control was wrong.

    Interior empty lines were always answered correctly, so a fix that changed
    them would be a new bug wearing the old one's clothes.
    """
    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = _editor(frame, emulate=True)
        control.SetValue("alpha\n\nbeta\n")
        _pump(10)

        seen = []
        for row in range(control.GetNumberOfLines()):
            control.SetInsertionPoint(control.XYToPosition(0, row))
            _pump(4)
            seen.append(_caret_line(control))

        assert seen == [
            (0, "alpha"),
            (1, ""),
            (2, "beta"),
            (3, ""),
        ], f"every line must report itself; got {seen!r}"
    finally:
        frame.Destroy()
        _pump()


def test_no_subclass_is_installed_when_the_braille_fix_is_off(wx_app) -> None:
    """Nothing sits in the message loop of a control that has nothing wrong with it."""
    from quill.ui.richedit_line_fix import is_installed

    frame = wx.Frame(None)
    try:
        frame.Show()
        _pump()
        control = _editor(frame, emulate=False)

        assert not is_installed(control.GetHandle())
        control.SetFocus()
        control.WriteText("This is a test.\n")
        _pump(10)

        _row, text = _caret_line(control)
        assert text == "", "with the flag off the control was always right on its own"
    finally:
        frame.Destroy()
        _pump()
