"""The status bar must not clip a cell, at any window width.

JAWS's Insert+Page Down reads the bottom line of the window *off the screen*,
so whatever wxMSW ellipsises is what a listener is told the bar says. The bar
used to be a horizontal box sizer in which Message was the only cell with a
proportion: the only cell that grew, and the only cell squeezed when twelve
cells did not fit. Two things fix that and both are asserted here -- the row
wraps instead of squeezing, and the one text with no natural ceiling is capped
in the label and read in full by Enter.
"""

from __future__ import annotations

import pytest
import wx

from quill.apps.lite_status_cells import _MESSAGE, _MESSAGE_LABEL_CHARS, CELLS, _clip_message
from quill.apps.lite_window_status import DocumentStatusMixin
from quill.core.document_text import DocumentText


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Editor:
    """The two things _cell_values asks the editor surface."""

    mode = "plain"

    def heading_level_at_caret(self) -> int:
        return 0


class _Bar(wx.Frame, DocumentStatusMixin):
    """Just enough window to build, fill and lay out the real cell row.

    The markup half of the window is stubbed rather than mixed in: this file is
    about *widths*, and what it needs from the language is the longest label the
    Format cell can ever show.
    """

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
        self.control.SetValue("A document with a few words in it.\nAnd a second line.")
        # The cells read the mirror rather than the control, so the harness
        # keeps one too. Built after the text is in, which is why it needs no
        # invalidation here.
        self.doc_text = DocumentText(lambda: self.control.GetValue())
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.control, 1, wx.EXPAND)
        layout.Add(self.status_panel, 0, wx.EXPAND)
        self.SetSizer(layout)
        self.Layout()

    def _announce(self, message: str) -> None:
        pass

    def fill_cells(self) -> None:
        """Put every cell's real text in, without waiting for the coalescer."""
        self._status_dirty = True
        self._refresh_status()


@pytest.fixture()
def bar(wx_app):
    frame = _Bar()
    frame.Show()
    wx_app.Yield()
    yield frame
    frame.Destroy()
    wx_app.Yield()


def _widest_overflow(frame: _Bar) -> int:
    """How far the widest cell's text exceeds its button, in pixels."""
    worst = 0
    for button in frame._status_buttons.values():
        text_width = button.GetTextExtent(button.GetLabel()).width
        worst = max(worst, text_width - button.GetSize().width)
    return worst


# ---------------------------------------------------------------------------
# the row wraps rather than squeezing


def test_the_cell_row_wraps(bar: _Bar) -> None:
    assert isinstance(bar.status_panel.GetSizer(), wx.WrapSizer)


def test_no_cell_is_added_with_a_proportion(bar: _Bar) -> None:
    """The bug was one cell with a proportion among eleven without."""
    sizer = bar.status_panel.GetSizer()
    assert [item.GetProportion() for item in sizer.GetChildren()] == [0] * len(CELLS)


@pytest.mark.parametrize("width", [420, 600, 900, 1400])
def test_no_label_is_wider_than_its_button(bar: _Bar, wx_app, width: int) -> None:
    """The whole point: nothing for wxMSW to ellipsise, at any width."""
    bar.SetSize((width, 300))
    bar.Layout()
    wx_app.Yield()
    bar.fill_cells()
    assert _widest_overflow(bar) <= 0


def test_a_narrow_window_makes_the_bar_taller_instead(bar: _Bar, wx_app) -> None:
    bar.SetSize((1400, 300))
    bar.Layout()
    wx_app.Yield()
    tall = bar.status_panel.GetSize().height

    bar.SetSize((420, 300))
    bar.Layout()
    wx_app.Yield()
    short = bar.status_panel.GetSize().height

    assert short > tall, "a narrow window should wrap the row, not squeeze a cell"


# ---------------------------------------------------------------------------
# the row holds still


def _cell_geometry(frame: _Bar) -> dict[str, tuple[int, int]]:
    return {
        key: (button.GetPosition().x, button.GetSize().width)
        for key, button in frame._status_buttons.items()
    }


def _cells_that_moved(frame: _Bar, before: dict[str, tuple[int, int]]) -> list[str]:
    after = _cell_geometry(frame)
    return sorted(key for key in before if before[key] != after[key])


def _select(frame: _Bar, wx_app, start: int, end: int) -> None:
    frame.control.SetInsertionPoint(start)
    frame.control.SetSelection(start, end)
    frame.doc_text.invalidate()
    frame.fill_cells()
    wx_app.Yield()


def test_a_cell_never_gives_width_back(bar: _Bar, wx_app) -> None:
    """Selecting and deselecting must not move the row twice.

    Reported from JAWS, which read the bar as "Line 1, colu Line 1, c ... No
    selectio ... B ody text" on a *maximised* window. Nothing was clipped --
    Insert+Page Down reads the bottom line off the screen, and the cells were
    moving under it: "No selection" to "1 words, 8 characters selected" is
    ninety pixels, and it shoved the nine cells after it sideways every time.
    """
    bar.fill_cells()
    wx_app.Yield()
    _select(bar, wx_app, 2, 20)  # the first wide selection settles the width
    settled = _cell_geometry(bar)

    _select(bar, wx_app, 0, 0)  # back to "No selection"
    assert _cells_that_moved(bar, settled) == []

    _select(bar, wx_app, 2, 20)  # and out again
    assert _cells_that_moved(bar, settled) == []


def test_a_cell_still_grows_for_text_that_needs_it(bar: _Bar, wx_app) -> None:
    """The ratchet may never turn into clipping: growing is still allowed."""
    bar.fill_cells()
    wx_app.Yield()
    _select(bar, wx_app, 0, 4)
    _select(bar, wx_app, 0, 51)
    assert _widest_overflow(bar) <= 0


def test_reflow_is_idempotent(bar: _Bar) -> None:
    """Re-laying out at an unchanged width must not re-enter the frame layout."""
    bar._reflow_status_bar()
    first = bar.status_panel.GetMinSize().height
    bar._reflow_status_bar()
    assert bar.status_panel.GetMinSize().height == first


# ---------------------------------------------------------------------------
# the message is the one unbounded text


def test_a_short_message_is_untouched() -> None:
    assert _clip_message("Saved") == "Saved"


def test_a_long_message_is_cut_and_marked() -> None:
    clipped = _clip_message("word " * 60)
    assert len(clipped) <= _MESSAGE_LABEL_CHARS + 3
    assert clipped.endswith("...")


def test_the_cut_falls_on_a_word_boundary() -> None:
    message = "Could not save because the folder is read only " * 4
    clipped = _clip_message(message)
    assert not clipped.removesuffix("...").endswith(" ")
    assert message.startswith(clipped.removesuffix("..."))


def test_a_single_long_word_is_still_cut() -> None:
    """No space to cut at: the budget still has to be honoured."""
    clipped = _clip_message("x" * 400)
    assert len(clipped) <= _MESSAGE_LABEL_CHARS + 3


def test_enter_on_the_message_cell_reads_the_whole_thing(bar: _Bar) -> None:
    message = "Could not open the file because the disk is full. " * 4
    bar._set_status_message(message)
    bar.fill_cells()

    assert bar._status_buttons[_MESSAGE].GetLabel() != message  # clipped on screen
    assert bar._cell_reading(_MESSAGE) == message  # whole thing to a listener


def test_a_fixed_cell_is_never_shortened(bar: _Bar) -> None:
    """Position and Encoding say two facts nothing else in the app will tell you."""
    bar.fill_cells()
    for key in ("position", "encoding", "line_endings"):
        assert not bar._status_buttons[key].GetLabel().endswith("...")
