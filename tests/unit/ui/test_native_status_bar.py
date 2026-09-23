"""The control JAWS's Insert+Page Down is actually looking for.

Both editors' visible status bar is a panel of focusable buttons, which is the
right shape for a keyboard and the wrong shape for that one command: it
searches for a window of class ``msctls_statusbar32`` and, finding none,
scrapes the bottom line of the window. The report that started this read
``"CRLF (Windows) Modified"`` -- the last two cells of twelve, alone on the
bottom row because the other ten had wrapped above them.
"""

from __future__ import annotations

from quill.ui.native_status_bar import (
    native_status_text,
    show_native_status_bar,
    sync_native_status_bar,
)


class _Bar:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.shown = True
        self.name = ""

    def GetStatusText(self, index: int = 0) -> str:
        return self.texts[-1] if self.texts else ""

    def SetStatusText(self, text: str, index: int = 0) -> None:
        self.texts.append(text)

    def SetName(self, name: str) -> None:
        self.name = name

    def IsShown(self) -> bool:
        return self.shown

    def Show(self, show: bool) -> None:
        self.shown = show


class _Frame:
    def __init__(self, bar: _Bar | None = None) -> None:
        self.bar = bar
        self.fields = 0
        self.size_events = 0

    def GetStatusBar(self) -> _Bar | None:
        return self.bar

    def CreateStatusBar(self, fields: int = 1) -> _Bar:
        self.fields = fields
        self.bar = _Bar()
        return self.bar

    def SendSizeEvent(self) -> None:
        self.size_events += 1


# ---------------------------------------------------------------------------
# the text


def test_cells_are_joined_into_one_line() -> None:
    assert native_status_text(["Line 3, column 1 of 20", "No selection"]) == (
        "Line 3, column 1 of 20. No selection"
    )


def test_empty_cells_are_dropped_rather_than_left_as_gaps() -> None:
    assert native_status_text(["Insert", "", "   ", "UTF-8"]) == "Insert. UTF-8"


def test_a_cell_that_ends_in_a_stop_does_not_get_a_second_one() -> None:
    assert native_status_text(["Saved.", "UTF-8"]) == "Saved. UTF-8"


def test_nothing_at_all_is_an_empty_line() -> None:
    assert native_status_text([]) == ""


# ---------------------------------------------------------------------------
# the control


def test_the_bar_is_created_with_one_field() -> None:
    """Per-cell fields would be drawn at fixed widths and ellipsised, which is
    the failure this control exists to end."""
    frame = _Frame()
    sync_native_status_bar(frame, "Line 1, column 1 of 1")
    assert frame.fields == 1
    assert frame.bar is not None
    assert frame.bar.texts == ["Line 1, column 1 of 1"]


def test_an_existing_bar_is_reused() -> None:
    bar = _Bar()
    frame = _Frame(bar)
    sync_native_status_bar(frame, "one")
    assert frame.fields == 0, "a second status bar would be a second answer"
    assert bar.texts == ["one"]


def test_unchanged_text_is_not_written_again() -> None:
    """This runs on the same coalesced refresh the cells do. The native control
    repaints on every write."""
    bar = _Bar()
    frame = _Frame(bar)
    sync_native_status_bar(frame, "one")
    sync_native_status_bar(frame, "one")
    sync_native_status_bar(frame, "two")
    assert bar.texts == ["one", "two"]


def test_a_frame_that_cannot_hold_one_is_not_an_error() -> None:
    """A stub frame in a test, a platform without the control. The visible bar
    is the button row; this one is a mirror."""
    assert sync_native_status_bar(None, "text") is None
    assert sync_native_status_bar(object(), "text") is None


def test_hiding_the_bar_takes_the_row_back() -> None:
    bar = _Bar()
    frame = _Frame(bar)
    show_native_status_bar(frame, False)
    assert bar.shown is False
    assert frame.size_events == 1, "wxFrame reserves the row until it re-measures"


def test_hiding_a_hidden_bar_does_nothing() -> None:
    bar = _Bar()
    bar.shown = False
    frame = _Frame(bar)
    show_native_status_bar(frame, False)
    assert frame.size_events == 0


def test_showing_it_again_brings_the_row_back() -> None:
    bar = _Bar()
    bar.shown = False
    frame = _Frame(bar)
    show_native_status_bar(frame, True)
    assert bar.shown is True
    assert frame.size_events == 1
