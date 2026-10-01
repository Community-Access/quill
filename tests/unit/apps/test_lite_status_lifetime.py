"""The status bar's refresh timer must not outlive the panel it refreshes.

Jeff, 2026-10-01, on exit from QUILL Lite::

    File "quill/apps/lite_window_status.py", line 289, in _refresh_status
        if not self.status_panel.IsShown():
    RuntimeError: wrapped C/C++ object of type Panel has been deleted

``_on_close`` stops the timers and then calls ``Destroy``, and something between
the two -- a text or focus event fired by the dying editor, or the settings
flush that marks the bar stale -- called ``_touch_status`` again, which armed a
fresh ``wx.CallLater`` on a window that was about to be gone. Stopping a timer
is not enough when anything can restart it; the stop has to be one-way.
"""

from __future__ import annotations

import pytest
import wx

from quill.apps.lite_window_status import DocumentStatusMixin
from quill.core.document_text import DocumentText


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


@pytest.fixture()
def bar(wx_app):
    frame = _Bar()
    frame.Show()
    wx_app.Yield()
    yield frame
    frame._stop_status_timer()
    if frame:
        frame.Destroy()
    wx_app.Yield()


def test_touching_the_bar_after_the_stop_arms_nothing(bar: _Bar) -> None:
    """The stop is one-way: a late ``_touch_status`` from a dying control must
    not schedule a refresh that will fire on a deleted panel."""
    bar._touch_status()
    assert bar._status_refresh_timer is not None
    bar._stop_status_timer()
    assert bar._status_refresh_timer is None
    bar._touch_status()
    assert bar._status_refresh_timer is None


def test_a_refresh_that_fires_on_a_destroyed_panel_is_a_no_op(bar: _Bar, wx_app) -> None:
    """Belt to the braces above: even a refresh that somehow reaches the
    callable after ``Destroy`` returns rather than raising from ``IsShown``."""
    bar._status_dirty = True
    bar.status_panel.Destroy()
    wx_app.Yield()
    bar._refresh_status()  # must not raise


def test_the_close_sequence_leaves_no_timer_behind(bar: _Bar, wx_app) -> None:
    """The real sequence: touch, stop, a late touch from teardown, Destroy.
    No timer may be armed at the end of it, so nothing is left to fire."""
    bar._touch_status()
    bar._stop_status_timer()
    bar._touch_status()
    bar.Destroy()
    wx_app.Yield()
    assert bar._status_refresh_timer is None
    assert bar._status_stopped is True
