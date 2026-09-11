"""The Braille A/B bench: two editors, one flag apart, both real.

The window exists to answer whether ``SES_EMULATESYSEDIT`` is worth having --
the braille fix is that flag plus the hidden border, and only the border was
ever proved load-bearing. A person and a braille display have to answer it, but
the thing they read has to be right, and that part a test can hold: editor A
must really carry the flag, editor B must really not, and they must differ by
nothing else.

Real controls, on purpose. A stub would happily report whatever the test asked
it to, and the whole value of the bench is that the two editors are the same
native RICHEDIT50W QUILL ships, built the same way, with one message sent to one
of them.
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
_SES_EMULATESYSEDIT = 0x00000001


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    del app


def _pump(times: int = 15) -> None:
    for _ in range(times):
        wx.YieldIfNeeded()


def _edit_style(control) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    send = user32.SendMessageW
    send.restype = ctypes.c_longlong
    send.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong]
    return int(send(ctypes.c_void_p(control.GetHandle()), _EM_GETEDITSTYLE, 0, 0))


class _Host:
    """What the window asks of its host, and nothing more."""

    def __init__(self, frame) -> None:
        self._wx = wx
        self.frame = frame
        self.said: list[str] = []

    def _announce(self, message: str, **_kwargs: object) -> None:
        self.said.append(str(message))


@pytest.fixture
def bench(wx_app):
    from quill.ui.braille_ab_window import open_braille_ab

    parent = wx.Frame(None)
    parent.Show()
    _pump()
    host = _Host(parent)
    window = open_braille_ab(host)
    _pump()
    yield host, window
    try:
        # A test is allowed to close it -- one of them is about closing it.
        if window is not None:
            window.Close()
    except RuntimeError:
        pass
    _pump()
    parent.Destroy()
    _pump()


def _editors(window) -> dict[str, object]:
    panel = window.GetChildren()[0]
    return {
        child.GetName(): child for child in panel.GetChildren() if isinstance(child, wx.TextCtrl)
    }


def _buttons(window) -> dict[str, object]:
    panel = window.GetChildren()[0]
    return {
        child.GetLabel(): child for child in panel.GetChildren() if isinstance(child, wx.Button)
    }


def _click(button) -> None:
    wx.PostEvent(button, wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
    _pump()


def test_editor_a_carries_the_flag_and_editor_b_does_not(bench) -> None:
    """The one difference the bench is for. Read from the controls, not the call."""
    _host, window = bench
    editors = _editors(window)

    assert set(editors) == {"Editor A", "Editor B"}
    assert _edit_style(editors["Editor A"]) & _SES_EMULATESYSEDIT, (
        "editor A is meant to be exactly what QUILL ships, braille fix and all"
    )
    assert not _edit_style(editors["Editor B"]) & _SES_EMULATESYSEDIT, (
        "editor B is the comparison; with the flag on there is nothing to compare"
    )


def test_both_editors_start_with_the_same_text_and_an_empty_last_line(bench) -> None:
    """Same text, or the two braille readings are not of the same thing.

    The trailing blank line is the other half of the flag's story: it is where
    an emulated control used to report the line above.
    """
    from quill.ui.braille_ab_window import SAMPLE_TEXT

    _host, window = bench
    for name, editor in _editors(window).items():
        assert editor.GetValue() == SAMPLE_TEXT, name
        _ok, _column, row = editor.PositionToXY(editor.GetInsertionPoint())
        assert editor.GetLineText(row) == "", (
            f"{name} starts with the caret on the empty final line, and the control "
            f"says that line is {editor.GetLineText(row)!r}"
        )


def test_selecting_the_sample_word_selects_it_in_both(bench) -> None:
    from quill.ui.braille_ab_window import SAMPLE_WORD

    host, window = bench
    _click(_buttons(window)["&Select the Sample Word"])

    for name, editor in _editors(window).items():
        start, end = editor.GetSelection()
        assert editor.GetValue()[start:end] == SAMPLE_WORD, name
    assert host.said, "the outcome of a command is announced; the reader cannot see it"


def test_reporting_the_caret_line_answers_for_both_editors(bench) -> None:
    """Never just the focused one -- pressing the button moves focus off it."""
    host, window = bench
    host.said.clear()
    _click(_buttons(window)["&Report Caret Line"])

    assert len(host.said) == 1
    spoken = host.said[0]
    assert "Editor A" in spoken and "Editor B" in spoken, spoken
    assert "blank" in spoken, f"both carets start on the empty final line: {spoken}"


def test_every_control_answers_f1(bench) -> None:
    """Authored help at the construction site, which is what the audit can see."""
    _host, window = bench
    assert window.GetHelpText(), "the window itself states its purpose"
    for name, editor in _editors(window).items():
        assert editor.GetHelpText(), name
    for label, button in _buttons(window).items():
        assert button.GetHelpText(), label


def test_opening_it_twice_raises_the_one_window(bench) -> None:
    from quill.ui.braille_ab_window import open_braille_ab

    host, window = bench
    again = open_braille_ab(host)
    _pump()

    assert again is window, "a second bench would be two of the thing being compared"
    assert len(_editors(window)) == 2


def test_closing_it_clears_the_host_handle(bench) -> None:
    """Otherwise the next open raises a destroyed window."""
    host, window = bench
    window.Close()
    _pump()

    assert getattr(host, "_braille_ab_frame", None) is None
