"""QUILL's message cell expires, and its bar has a control the reader can find.

The same two reports as QUILL Lite's (``tests/unit/apps/test_lite_status_message.py``)
and the same two fixes, because the bars are the same bar twice: a panel of
focusable buttons that no ``msctls_statusbar32``-seeking reader could find, and
a message cell that held "String not found" through a page of editing.
"""

from __future__ import annotations

from quill.core.status_message import IDLE_MESSAGE, MESSAGE_TTL_SECONDS
from quill.ui.main_frame_statusbar import StatusBarMixin, _StatusBarCell


class _Document:
    text = "A document."

    def __init__(self) -> None:
        self.revision = 1
        self.path = None


class _Button:
    def __init__(self) -> None:
        self.label = ""

    def GetLabel(self) -> str:
        return self.label

    def SetLabel(self, label: str) -> None:
        self.label = label

    def SetHelpText(self, text: str) -> None:
        pass

    def SetName(self, name: str) -> None:
        pass


class _NativeBar:
    def __init__(self) -> None:
        self.text = ""

    def GetStatusText(self, index: int = 0) -> str:
        return self.text

    def SetStatusText(self, text: str, index: int = 0) -> None:
        self.text = text

    def SetName(self, name: str) -> None:
        pass


class _Frame:
    def __init__(self) -> None:
        self.bar: _NativeBar | None = None

    def GetStatusBar(self) -> _NativeBar | None:
        return self.bar

    def CreateStatusBar(self, fields: int = 1) -> _NativeBar:
        self.bar = _NativeBar()
        return self.bar


class _Panel:
    def Layout(self) -> None:
        pass


class _Timer:
    def __init__(self) -> None:
        self.stopped = False

    def Stop(self) -> None:
        self.stopped = True


class _Wx:
    def __init__(self) -> None:
        self.delays: list[int] = []

    def CallLater(self, delay: int, _callable: object) -> _Timer:
        self.delays.append(delay)
        return _Timer()


def _host(*, items: tuple[str, ...] = ("message",)) -> StatusBarMixin:
    host = StatusBarMixin.__new__(StatusBarMixin)
    host.document = _Document()  # type: ignore[attr-defined]
    host._wx = _Wx()  # type: ignore[attr-defined]
    host.frame = _Frame()  # type: ignore[attr-defined]
    host.statusbar = _Panel()  # type: ignore[attr-defined]
    host._STATUS_BAR_FEATURES = {}  # type: ignore[attr-defined]
    host._STATUS_BAR_LABELS = {item: item.title() for item in items}  # type: ignore[attr-defined]
    host._dirty_title_suffix = lambda: ""  # type: ignore[attr-defined,method-assign]
    host._record_spoken = lambda _message: None  # type: ignore[attr-defined,method-assign]
    host._schedule_statusbar_refresh = lambda: None  # type: ignore[attr-defined,method-assign]
    host._statusbar_cells = [  # type: ignore[attr-defined]
        _StatusBarCell(item=item, button=_Button()) for item in items
    ]
    return host


# ---------------------------------------------------------------------------
# the message expires


def test_a_fresh_message_reads_back() -> None:
    host = _host()
    host._set_status_quiet("String not found")
    assert host._statusbar_text_for_item("message") == "String not found"


def test_the_next_edit_clears_it() -> None:
    """The report: a page of editing with "Find not found" still in the bar."""
    host = _host()
    host._set_status_quiet("String not found")
    host.document.revision += 1
    assert host._statusbar_text_for_item("message") == IDLE_MESSAGE


def test_it_survives_its_own_edit() -> None:
    """The stamp is taken after the edit, so the message about it lives."""
    host = _host()
    host.document.revision += 1
    host._set_status_quiet("Replaced 3 occurrences")
    assert host._statusbar_text_for_item("message") == "Replaced 3 occurrences"


def test_it_ages_out_without_an_edit(monkeypatch) -> None:
    import quill.ui.main_frame_statusbar as statusbar

    host = _host()
    host._set_status_quiet("String not found")
    later = host._status_message_at + MESSAGE_TTL_SECONDS + 1.0
    monkeypatch.setattr(statusbar.time, "monotonic", lambda: later)
    assert host._statusbar_text_for_item("message") == IDLE_MESSAGE


def test_a_refresh_is_armed_for_the_moment_it_expires() -> None:
    """The timeout exists for the case where nothing else is happening, so
    something has to come back on its own and clear the cell."""
    host = _host()
    host._set_status_quiet("String not found")
    assert host._wx.delays == [int(MESSAGE_TTL_SECONDS * 1000) + 100]


def test_a_message_set_by_hand_never_expires() -> None:
    """Stub frames in older tests assign the attribute directly and should get
    back what they assigned rather than a clock they never set."""
    host = _host()
    host._status_message = "Assigned by hand"
    assert host._statusbar_text_for_item("message") == "Assigned by hand"


# ---------------------------------------------------------------------------
# the native bar


def test_the_refresh_fills_a_native_status_bar() -> None:
    host = _host(items=("message", "line_column"))
    host._statusbar_button_label = lambda item: {  # type: ignore[attr-defined,method-assign]
        "message": "Ready",
        "line_column": "Line 3, column 1 of 20",
    }[item]
    host._statusbar_help_text = lambda _item: ""  # type: ignore[attr-defined,method-assign]
    host._refresh_statusbar()
    assert host.frame.bar is not None
    assert host.frame.bar.text == "Line 3, column 1 of 20"


def test_the_message_reads_last_and_an_idle_one_not_at_all() -> None:
    host = _host(items=("message", "line_column"))
    labels = {"message": "String not found", "line_column": "Line 3, column 1 of 20"}
    host._statusbar_button_label = lambda item: labels[item]  # type: ignore[attr-defined,method-assign]
    host._statusbar_help_text = lambda _item: ""  # type: ignore[attr-defined,method-assign]
    host._refresh_statusbar()
    assert host.frame.bar.text == "Line 3, column 1 of 20. String not found"


def test_the_message_is_appended_rather_than_inserted_first() -> None:
    """It used to be forced to index 0 whenever it was not already listed. The
    message is a replay of something already spoken rather than a fact you
    cannot otherwise get, and it is the one cell whose text has no ceiling --
    put first in a wrapping row it shoves every fixed cell out of reach."""
    from quill.core.settings_normalizers import STATUS_BAR_ITEMS

    assert STATUS_BAR_ITEMS[-1] == "message"
    assert STATUS_BAR_ITEMS[0] == "line_column"
