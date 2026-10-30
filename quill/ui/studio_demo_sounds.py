"""Sounds you hear: mute, unmute or turn down any program, as the Windows mixer does.

This changes what the listener hears, and therefore what any recording of the
system hears -- the Windows session mute, not Studio's "leave it out of the
recording" (MX-121 keeps the two separately named). Windows remembers a muted
program, so the window says so: unmuting is one key away here, and in the
Windows volume mixer.

A list with a state column (QUILL's list convention): Space mutes or unmutes
the selected program; the volume field sets its level.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class SoundsYouHearDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, *, announce: Callable[[str], None]) -> None:
        super().__init__(
            parent, title="Sounds you hear", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._announce = announce
        self.sessions: list = []
        layout = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "Programs playing sound now. Space mutes or unmutes the selected program for "
                "you, and for any recording of the system. Windows remembers a muted program "
                "until you unmute it."
            ),
        )
        intro.Wrap(520)
        layout.Add(intro, 0, wx.ALL, 10)
        layout.Add(wx.StaticText(self, label="&Programs"), 0, wx.LEFT, 10)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(520, 220))
        set_accessible_name(self.list, "Programs")
        self.list.SetHelpText(
            "Each program with sound. The state says whether you hear it, at what volume, and "
            "whether it is playing now. Space mutes or unmutes it."
        )
        for column, (title, width) in enumerate((
            ("Program", 220),
            ("You hear it", 160),
            ("Now", 110),
        )):
            self.list.InsertColumn(column, title, width=width)
        self.list.Bind(wx.EVT_KEY_DOWN, self._key)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._selected)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._toggle())
        layout.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.mute = wx.Button(self, label="&Mute or unmute")
        self.mute.SetHelpText("Mute the selected program for you, or unmute it.")
        self.mute.Bind(wx.EVT_BUTTON, lambda _e: self._toggle())
        row.Add(self.mute, 0, wx.RIGHT, 8)
        row.Add(
            wx.StaticText(self, label="&Volume, percent"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.volume = wx.SpinCtrl(self, min=0, max=100, initial=100)
        set_accessible_name(self.volume, "Volume, percent")
        self.volume.SetHelpText("The selected program's own volume, 0 to 100 percent.")
        self.volume.Bind(wx.EVT_SPINCTRL, self._volume_changed)
        row.Add(self.volume, 0, wx.RIGHT, 8)
        refresh = wx.Button(self, label="&Refresh")
        refresh.SetHelpText("Read the list of programs playing sound again.")
        refresh.Bind(wx.EVT_BUTTON, lambda _e: self.refresh())
        row.Add(refresh, 0)
        layout.Add(row, 0, wx.ALL, 10)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close this window. Mutes you set stay until you unmute them.")
        layout.Add(close, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(layout)
        self.refresh()
        self.list.SetFocus()

    @staticmethod
    def _cells(session) -> tuple[str, str, str]:
        hear = "Muted" if session.muted else f"Yes, {round(session.volume * 100)} percent"
        now = "Playing" if session.peak > 0.001 else "Quiet"
        return session.name, hear, now

    def refresh(self) -> None:
        from quill.platform.windows.audio_sessions import AudioSessionError, list_sessions

        selected = self.list.GetFirstSelected()
        previous = self.sessions[selected].process_id if 0 <= selected < len(self.sessions) else -1
        try:
            self.sessions = list_sessions()
        except AudioSessionError as error:
            self.sessions = []
            self._announce(str(error))
        self.list.DeleteAllItems()
        for row, session in enumerate(self.sessions):
            name, hear, now = self._cells(session)
            self.list.InsertItem(row, name)
            self.list.SetItem(row, 1, hear)
            self.list.SetItem(row, 2, now)
        if self.sessions:
            row = next((i for i, s in enumerate(self.sessions) if s.process_id == previous), 0)
            self.list.Select(row)
            self.list.Focus(row)
            self.volume.SetValue(round(self.sessions[row].volume * 100))
        self.mute.Enable(bool(self.sessions))
        self.volume.Enable(bool(self.sessions))

    def _row(self) -> int:
        row = self.list.GetFirstSelected()
        return row if 0 <= row < len(self.sessions) else -1

    def _selected(self, _event: wx.ListEvent) -> None:
        row = self._row()
        if row >= 0:
            self.volume.SetValue(round(self.sessions[row].volume * 100))

    def _key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_SPACE and not event.HasAnyModifiers():
            self._toggle()
            return
        if event.GetKeyCode() == wx.WXK_F5:
            self.refresh()
            return
        event.Skip()

    def _toggle(self) -> None:
        from dataclasses import replace

        from quill.platform.windows.audio_sessions import AudioSessionError, set_process_mute

        row = self._row()
        if row < 0:
            return
        session = self.sessions[row]
        try:
            set_process_mute(session.process_id, not session.muted)
        except AudioSessionError as error:
            self._announce(str(error))
            return
        self.sessions[row] = replace(session, muted=not session.muted)
        # The focused row's cell changes; the reader re-reads the row itself.
        self.list.SetItem(row, 1, self._cells(self.sessions[row])[1])

    def _volume_changed(self, _event: wx.Event) -> None:
        from dataclasses import replace

        from quill.platform.windows.audio_sessions import AudioSessionError, set_process_volume

        row = self._row()
        if row < 0:
            return
        level = self.volume.GetValue() / 100
        try:
            set_process_volume(self.sessions[row].process_id, level)
        except AudioSessionError as error:
            self._announce(str(error))
            return
        self.sessions[row] = replace(self.sessions[row], volume=level)
        self.list.SetItem(row, 1, self._cells(self.sessions[row])[1])
