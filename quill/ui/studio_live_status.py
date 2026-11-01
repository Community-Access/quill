"""The live broadcast window: status, now playing, mute everything public, stop.

Modeless and shown without taking focus, like the Recording status window.
Closing it hides it; the broadcast continues until Stop broadcasting.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.stability.wx_dispatch import guard_timer_callback
from quill.ui.dialog_contract import bind_close_button, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class LiveStatusFrame(wx.Frame):
    def __init__(
        self,
        *,
        status: Callable[[], str],
        update_title: Callable[[str], None],
        mute: Callable[[], None],
        stop: Callable[[], None],
    ) -> None:
        super().__init__(None, title="Live broadcast")
        self._status = status
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(panel, label="Status"), 0, wx.LEFT | wx.TOP, 10)
        self.text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(panel, 440, 70)
        )
        set_accessible_name(self.text, "Status")
        self.text.SetHelpText(
            "On air or reconnecting, time live, sounds in the stream, reconnects."
        )
        layout.Add(self.text, 0, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(panel, label="&Now playing"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.now = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.now, "Now playing")
        self.now.SetHelpText("The title listeners see. Press Enter or Update the title to send it.")
        self.now.Bind(wx.EVT_TEXT_ENTER, lambda _e: update_title(self.now.GetValue().strip()))
        row.Add(self.now, 1, wx.RIGHT, 6)
        send = wx.Button(panel, label="&Update the title")
        send.SetHelpText("Send the now-playing title to the server.")
        send.Bind(wx.EVT_BUTTON, lambda _e: update_title(self.now.GetValue().strip()))
        row.Add(send, 0)
        layout.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.mute = wx.Button(panel, label="&Mute everything public")
        self.mute.SetHelpText(
            "Listeners hear silence at once; the connection and any saved copy continue. "
            "Press again to unmute."
        )
        self.mute.Bind(wx.EVT_BUTTON, lambda _e: mute())
        row.Add(self.mute, 0, wx.RIGHT, 6)
        stop_button = wx.Button(panel, label="&Stop broadcasting")
        stop_button.SetHelpText("End the broadcast and finish the saved copy.")
        stop_button.Bind(wx.EVT_BUTTON, lambda _e: stop())
        row.Add(stop_button, 0, wx.RIGHT, 6)
        close = wx.Button(panel, wx.ID_CLOSE, label="Close")
        close.SetHelpText("Hide this window; the broadcast continues.")
        bind_close_button(self, close, modeless=True)
        row.Add(close, 0)
        layout.Add(row, 0, wx.ALL, 10)
        panel.SetSizer(layout)
        layout.Fit(self)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._timer = wx.Timer(self)
        tick = guard_timer_callback(lambda _e: self.refresh(), name="Broadcast status refresh")
        self.Bind(wx.EVT_TIMER, tick, self._timer)
        self._timer.Start(1000)
        self.refresh()

    def refresh(self) -> None:
        try:
            text = self._status()
        except Exception as error:  # noqa: BLE001 - a status read must not break the window
            text = f"Status unavailable: {error}"
        if text != self.text.GetValue():
            self.text.ChangeValue(text)

    def set_muted(self, muted: bool) -> None:
        self.mute.SetLabel("Un&mute everything public" if muted else "&Mute everything public")

    def _on_close(self, event: wx.CloseEvent) -> None:
        if event.CanVeto():
            event.Veto()
            self.Hide()
            return
        self.finish()

    def finish(self) -> None:
        if self._timer.IsRunning():
            self._timer.Stop()
        self.Destroy()
