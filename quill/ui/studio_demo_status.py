"""The Recording status window: pause, mark, mute and stop without Studio's main window.

Modeless and never focus-stealing (REC-013): it appears without activation so
the demonstrated program keeps focus, and is reachable from the tray and the
taskbar when the presenter wants it. Its windows are kept out of a display
recording by the host. The status text is a read-only field refreshed once a
second without speaking; "Recording status" (a key or this window's button)
is how the line is heard on request.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.ui.dialog_contract import bind_close_button, set_accessible_name

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class RecordingStatusFrame(wx.Frame):
    def __init__(
        self,
        parent: wx.Window | None,
        *,
        status: Callable[[], str],
        pause: Callable[[], None],
        marker: Callable[[], None],
        mute: Callable[[], None],
        speak_status: Callable[[], None],
        stop: Callable[[], None],
        discard: Callable[[], None],
        has_microphone: bool,
    ) -> None:
        super().__init__(
            parent,
            title="Recording status",
            # Its own taskbar button: reachable while Studio is hidden in the tray.
            style=wx.DEFAULT_FRAME_STYLE | (wx.FRAME_FLOAT_ON_PARENT if parent else 0),
        )
        self._status = status
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(panel, label="Status"), 0, wx.LEFT | wx.TOP, 10)
        self.text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(420, 80))
        set_accessible_name(self.text, "Status")
        self.text.SetHelpText(
            "Elapsed time, the sounds being recorded, whether the screen reader is in the "
            "recording, dropped frames and disk space left. It updates every second."
        )
        layout.Add(self.text, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.pause_button = wx.Button(panel, label="&Pause")
        self.pause_button.SetHelpText(
            "Pause the recording; nothing is recorded until you resume. The same button resumes."
        )
        self.pause_button.Bind(wx.EVT_BUTTON, lambda _e: pause())
        row.Add(self.pause_button, 0, wx.RIGHT, 6)
        marker_button = wx.Button(panel, label="Add &marker")
        marker_button.SetHelpText("Note this moment, with an optional label, in the marker list.")
        marker_button.Bind(wx.EVT_BUTTON, lambda _e: marker())
        row.Add(marker_button, 0, wx.RIGHT, 6)
        self.mute_button = wx.Button(panel, label="M&ute microphone")
        self.mute_button.SetHelpText(
            "Silence the microphone in the recording; the device stays open and the muted "
            "stretch is marked. Press again to unmute."
        )
        self.mute_button.Bind(wx.EVT_BUTTON, lambda _e: mute())
        self.mute_button.Enable(has_microphone)
        row.Add(self.mute_button, 0, wx.RIGHT, 6)
        status_button = wx.Button(panel, label="Spea&k status")
        status_button.SetHelpText("Say the status line now.")
        status_button.Bind(wx.EVT_BUTTON, lambda _e: speak_status())
        row.Add(status_button, 0)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        stop_button = wx.Button(panel, label="&Stop and save")
        stop_button.SetHelpText("Stop recording, finish the video, check it and save it.")
        stop_button.Bind(wx.EVT_BUTTON, lambda _e: stop())
        row.Add(stop_button, 0, wx.RIGHT, 6)
        discard_button = wx.Button(panel, label="&Discard recording...")
        discard_button.SetHelpText("Stop and delete this recording after you confirm.")
        discard_button.Bind(wx.EVT_BUTTON, lambda _e: discard())
        row.Add(discard_button, 0, wx.RIGHT, 6)
        close = wx.Button(panel, wx.ID_CLOSE, label="Close")
        close.SetHelpText(
            "Hide this window; recording continues. Reopen it from the tray or the Capture menu."
        )
        bind_close_button(self, close, modeless=True)
        row.Add(close, 0)
        layout.Add(row, 0, wx.ALL, 10)
        panel.SetSizer(layout)
        layout.Fit(self)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _e: self.refresh(), self._timer)
        self._timer.Start(1000)
        self.refresh()

    def refresh(self) -> None:
        try:
            text = self._status()
        except Exception as error:  # noqa: BLE001 - a status read must not break the window
            text = f"Status unavailable: {error}"
        if text != self.text.GetValue():
            self.text.ChangeValue(text)

    def set_paused(self, paused: bool) -> None:
        self.pause_button.SetLabel("&Resume" if paused else "&Pause")

    def set_muted(self, muted: bool) -> None:
        self.mute_button.SetLabel("Unm&ute microphone" if muted else "M&ute microphone")

    def _on_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Hide()
            return
        event.Skip()

    def _on_close(self, event: wx.CloseEvent) -> None:
        # Closing hides; the recording owns the window's lifetime (finish()).
        if event.CanVeto():
            event.Veto()
            self.Hide()
            return
        self.finish()
        event.Skip()

    def show_quietly(self) -> None:
        """Show without taking focus from the program being demonstrated."""
        self.ShowWithoutActivating()

    def finish(self) -> None:
        if self._timer.IsRunning():
            self._timer.Stop()
        self.Destroy()
