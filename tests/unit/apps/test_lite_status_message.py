"""What the status bar answers with, and how long it goes on saying it.

Two reports, one bar. The first: Insert+Page Down read back ``"CRLF (Windows)
Modified"`` and nothing else -- the last two of twelve cells, alone on the
bottom row of a wrapping panel, which is the only row a reader scraping the
window can see. The fix is a real ``msctls_statusbar32`` carrying the whole row
(:mod:`quill.ui.native_status_bar`), asserted here end to end.

The second: "if I go do a bunch of edits and still see Find not found, that is
a problem, is it not?" It is, and :mod:`quill.core.status_message` is the rule.
This is that rule reaching the cell.
"""

from __future__ import annotations

import pytest
import wx

from quill.apps.lite_status_cells import _MESSAGE, _MESSAGE_LABEL_CHARS
from quill.apps.lite_window_status import DocumentStatusMixin
from quill.core.document_text import DocumentText
from quill.core.status_message import IDLE_MESSAGE


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Editor:
    mode = "plain"

    def heading_level_at_caret(self) -> int:
        return 0


class _Bar(wx.Frame, DocumentStatusMixin):
    """Just enough window to build and fill the real cell row."""

    def document_kind_label(self) -> str:
        return "Plain text"

    def markup_surface(self) -> str | None:
        return None

    def __init__(self) -> None:
        super().__init__(None, size=(900, 300))
        self.editor = _Editor()
        self.encoding = "utf-8"
        self.newline = "\r\n"
        self.modified = False
        self._overwrite_mode = False
        self._tab_inserts_literal = True
        self._init_status_bar()
        self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.control.SetValue("A document with a few words in it.")
        self.doc_text = DocumentText(lambda: self.control.GetValue())
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.control, 1, wx.EXPAND)
        layout.Add(self.status_panel, 0, wx.EXPAND)
        self.SetSizer(layout)
        self.Layout()

    def _announce(self, message: str) -> None:
        self._set_status_message(message)

    def fill_cells(self) -> None:
        self._status_dirty = True
        self._refresh_status()


@pytest.fixture()
def bar(wx_app):
    frame = _Bar()
    frame.Show()
    wx_app.Yield()
    yield frame
    frame._stop_status_timer()
    frame.Destroy()
    wx_app.Yield()


def _native(frame: _Bar) -> str:
    native = frame.GetStatusBar()
    assert native is not None, "the control the reader looks for must exist"
    return native.GetStatusText(0)


# ---------------------------------------------------------------------------
# the native bar


def test_the_frame_has_a_native_status_bar(bar: _Bar) -> None:
    """wxStatusBar on wxMSW *is* msctls_statusbar32, which is the whole point:
    the role on the panel was never going to answer a command that searches by
    window class."""
    assert bar.GetStatusBar() is not None


def test_it_carries_every_cell_not_just_the_bottom_row(bar: _Bar) -> None:
    """The report verbatim. "CRLF (Windows) Modified" was the tail of the row;
    everything ahead of it had wrapped out of reach."""
    bar.fill_cells()
    text = _native(bar)
    assert "Line 1, column 1" in text
    assert "No selection" in text
    assert "Encoding: UTF-8" in text
    assert "Line Endings: CRLF (Windows)" in text
    assert text.index("Line 1, column 1") < text.index("Line Endings: CRLF (Windows)")


def test_a_cell_that_does_not_name_itself_gets_its_label(bar: _Bar) -> None:
    """On the button row the reader announces each cell's name for us. Read as
    one line, "Insert" and "UTF-8" are not sentences."""
    bar.fill_cells()
    text = _native(bar)
    assert "Typing Mode: Insert" in text
    assert "Tab Mode: Tab char" in text


def test_a_cell_that_does_name_itself_is_left_alone(bar: _Bar) -> None:
    bar.fill_cells()
    text = _native(bar)
    assert "Word Count:" not in text
    assert "words" in text


def test_an_idle_message_is_left_out_altogether(bar: _Bar) -> None:
    """Rather than reading "Ready" at the end of every answer."""
    bar.fill_cells()
    assert IDLE_MESSAGE not in _native(bar)


def test_the_message_reads_last(bar: _Bar) -> None:
    """The facts somebody pressed the key for come first."""
    bar._set_status_message("String not found")
    bar.fill_cells()
    text = _native(bar)
    assert text.endswith("String not found")


def test_the_native_bar_carries_the_message_unclipped(bar: _Bar) -> None:
    """The button label is cut to what fits a button. SB_GETTEXT has no such
    limit, so the one place the whole wording survives is here."""
    long_message = ("Reviewed 9,696 words, " + "and a great deal more besides " * 4).strip()
    bar._set_status_message(long_message)
    bar.fill_cells()
    assert long_message in _native(bar)
    assert len(bar._status_buttons[_MESSAGE].GetLabel()) <= _MESSAGE_LABEL_CHARS + 3


def test_hiding_the_bar_hides_the_native_one_too(bar: _Bar, wx_app) -> None:
    """The setting means "no status bar", not "no status bar unless you ask a
    different way"."""

    class _Settings:
        show_status_bar = False

    class _App:
        settings = _Settings()

    bar.app = _App()
    bar.apply_status_bar_visibility()
    wx_app.Yield()
    assert bar.GetStatusBar().IsShown() is False


# ---------------------------------------------------------------------------
# where the message cell sits


def test_the_message_cell_is_last_in_the_row() -> None:
    """Load-bearing three times over: the row wraps, so the one cell with no
    width ceiling must have nothing after it to push; the native bar reads the
    message last, so the two now walk in the same order; and F6 lands on
    Position rather than on "Ready"."""
    from quill.apps.lite_status_cells import CELLS

    assert CELLS[-1].key == _MESSAGE
    assert CELLS[0].key == "position"


def test_f6_lands_on_position_rather_than_on_an_empty_message(bar: _Bar) -> None:
    from quill.apps.lite_status_cells import CELLS

    assert CELLS[bar._active_cell_index].key == "position"


# ---------------------------------------------------------------------------
# the message expires


def test_a_message_reads_back_while_it_is_fresh(bar: _Bar) -> None:
    bar._set_status_message("String not found")
    assert bar._cell_reading(_MESSAGE) == "String not found"


def test_the_next_edit_clears_it(bar: _Bar) -> None:
    """A page of editing must not leave "String not found" in the bar."""
    bar._set_status_message("String not found")
    bar.control.SetValue("Something else entirely")
    bar.doc_text.invalidate()
    bar.fill_cells()
    assert bar._cell_reading(_MESSAGE) == IDLE_MESSAGE
    assert bar._status_buttons[_MESSAGE].GetLabel() == IDLE_MESSAGE


def test_it_ages_out_without_an_edit(bar: _Bar, monkeypatch) -> None:
    """Reading rather than typing would keep it forever under the edit rule."""
    import quill.apps.lite_window_status as status

    bar._set_status_message("String not found")
    later = bar._status_message_at + 61.0
    monkeypatch.setattr(status.time, "monotonic", lambda: later)
    bar.fill_cells()
    assert bar._cell_reading(_MESSAGE) == IDLE_MESSAGE


def test_an_untimed_message_never_expires(bar: _Bar) -> None:
    """Nothing in the app assigns the attribute directly; a test does, and it
    should get back what it assigned rather than a clock it never set."""
    bar._status_message = "Assigned by hand"
    bar._status_message_at = None
    assert bar._cell_reading(_MESSAGE) == "Assigned by hand"
