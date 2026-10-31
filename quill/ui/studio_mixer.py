"""The Studio Mixer: every program's sound and every sound card, in one window.

Tabs, so each part is one Ctrl+Tab away (roadmap section 5):

- **Programs**: every program playing sound, with its volume, mute and the
  sound card it plays on. Moving a program to another card is what Windows
  Settings, App volume and device preferences does, and Windows remembers it.
- **Devices**: playback and recording devices; make one the default or the
  communications device; a recording device's level and mute.

Lists have a state column, not check boxes (QUILL's list convention). The
focused row's cells change in place, which the screen reader reads itself, so
the window speaks only what it alone knows: a failure, or a change Windows
refused (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import wx

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

_DEFAULT_CARD = "Windows default"


class StudioMixerDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, *, announce: Callable[[str], None]) -> None:
        super().__init__(
            parent, title="Studio Mixer", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._announce = announce
        self.sessions: list = []
        self.outputs: list = []
        self.inputs: list = []
        self.book = wx.Notebook(self)
        set_accessible_name(self.book, "Mixer tabs")
        self.book.SetHelpText("Programs: what each program plays. Devices: your sound cards.")
        self.book.AddPage(self._programs_page(), "Programs")
        self.book.AddPage(self._devices_page(), "Devices")
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.book, 1, wx.EXPAND | wx.ALL, 10)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close the mixer. Changes stay as you made them.")
        layout.Add(close, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(layout)
        self.refresh()
        self.programs.SetFocus()

    # -- building -------------------------------------------------------------------

    def _programs_page(self) -> wx.Panel:
        page = wx.Panel(self.book)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(page, label="&Programs playing sound"), 0, wx.ALL, 6)
        self.programs = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(560, 220))
        set_accessible_name(self.programs, "Programs playing sound")
        self.programs.SetHelpText(
            "Each program with sound: whether you hear it and how loud, whether it is playing "
            "now, and its sound card. Space mutes or unmutes it; Up and Down choose a program."
        )
        for column, (title, width) in enumerate((
            ("Program", 200),
            ("You hear it", 140),
            ("Now", 80),
            ("Sound card", 220),
        )):
            self.programs.InsertColumn(column, title, width=width)
        self.programs.Bind(wx.EVT_KEY_DOWN, self._program_key)
        self.programs.Bind(wx.EVT_LIST_ITEM_SELECTED, self._program_selected)
        self.programs.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._toggle_mute())
        layout.Add(self.programs, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.mute = wx.Button(page, label="&Mute or unmute")
        self.mute.SetHelpText("Mute the selected program for you, or unmute it.")
        self.mute.Bind(wx.EVT_BUTTON, lambda _e: self._toggle_mute())
        row.Add(self.mute, 0, wx.RIGHT, 8)
        row.Add(
            wx.StaticText(page, label="&Volume, percent"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.volume = wx.SpinCtrl(page, min=0, max=100, initial=100)
        set_accessible_name(self.volume, "Volume, percent")
        self.volume.SetHelpText(
            "The selected program's own volume, 0 to 100 percent. Up and Down change it by 1, "
            "Page Up and Page Down by 10."
        )
        self.volume.Bind(wx.EVT_SPINCTRL, self._volume_changed)
        self.volume.Bind(wx.EVT_KEY_DOWN, self._volume_key)
        row.Add(self.volume, 0)
        layout.Add(row, 0, wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(page, label="Sound &card"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.card = wx.Choice(page)
        set_accessible_name(self.card, "Sound card")
        self.card.SetHelpText(
            "Which sound card the selected program plays on, as in Windows Settings. Windows "
            "default follows whatever the default device is. Windows remembers the choice."
        )
        self.card.Bind(wx.EVT_CHOICE, self._card_changed)
        row.Add(self.card, 1)
        layout.Add(row, 0, wx.EXPAND | wx.ALL, 6)
        refresh = wx.Button(page, label="&Refresh")
        refresh.SetHelpText("Read the programs and sound cards again. F5 does the same.")
        refresh.Bind(wx.EVT_BUTTON, lambda _e: self.refresh())
        layout.Add(refresh, 0, wx.ALL, 6)
        page.SetSizer(layout)
        return page

    def _devices_page(self) -> wx.Panel:
        page = wx.Panel(self.book)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(page, label="Pla&yback devices"), 0, wx.ALL, 6)
        self.playback = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(560, 110))
        set_accessible_name(self.playback, "Playback devices")
        self.playback.SetHelpText(
            "Speakers and headphones Windows can use, and which is the default."
        )
        self.playback.InsertColumn(0, "Device", width=360)
        self.playback.InsertColumn(1, "Role", width=180)
        layout.Add(self.playback, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, flow, communications in (
            ("Make &default", "Make the selected playback device the Windows default.", 0, False),
            ("Make commu&nications device", "Use the selected playback device for calls.", 0, True),
        ):
            button = wx.Button(page, label=label)
            button.SetHelpText(help_text)
            button.Bind(
                wx.EVT_BUTTON,
                lambda _e, f=flow, c=communications: self._make_default(f, c),
            )
            row.Add(button, 0, wx.RIGHT, 8)
        layout.Add(row, 0, wx.ALL, 6)
        layout.Add(wx.StaticText(page, label="Recordin&g devices"), 0, wx.ALL, 6)
        self.recording = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(560, 110))
        set_accessible_name(self.recording, "Recording devices")
        self.recording.SetHelpText(
            "Microphones and line inputs, which is the default, and each one's level."
        )
        self.recording.InsertColumn(0, "Device", width=300)
        self.recording.InsertColumn(1, "Role", width=140)
        self.recording.InsertColumn(2, "Level", width=100)
        self.recording.Bind(wx.EVT_LIST_ITEM_SELECTED, self._input_selected)
        layout.Add(self.recording, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, communications in (
            (
                "Make defa&ult recording device",
                "Make the selected input the Windows default.",
                False,
            ),
            ("Use for ca&lls", "Use the selected input as the communications device.", True),
        ):
            button = wx.Button(page, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, c=communications: self._make_default(1, c))
            row.Add(button, 0, wx.RIGHT, 8)
        layout.Add(row, 0, wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(page, label="Recording l&evel, percent"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.input_level = wx.SpinCtrl(page, min=0, max=100, initial=50)
        set_accessible_name(self.input_level, "Recording level, percent")
        self.input_level.SetHelpText("How loud the selected input records, 0 to 100 percent.")
        self.input_level.Bind(wx.EVT_SPINCTRL, self._input_level_changed)
        row.Add(self.input_level, 0, wx.RIGHT, 8)
        self.input_mute = wx.CheckBox(page, label="Mute this input")
        self.input_mute.SetHelpText("Silence the selected input for every program.")
        self.input_mute.Bind(wx.EVT_CHECKBOX, self._input_mute_changed)
        row.Add(self.input_mute, 0, wx.ALIGN_CENTER_VERTICAL)
        layout.Add(row, 0, wx.ALL, 6)
        page.SetSizer(layout)
        return page

    # -- reading --------------------------------------------------------------------

    def refresh(self) -> None:
        from quill.platform.windows import audio_routing, audio_sessions

        try:
            self.outputs = audio_routing.list_devices(audio_routing.RENDER)
            self.inputs = audio_routing.list_devices(audio_routing.CAPTURE)
        except audio_routing.AudioRoutingError as error:
            self.outputs, self.inputs = [], []
            self._announce(str(error))
        selected = self.programs.GetFirstSelected()
        previous = self.sessions[selected].process_id if 0 <= selected < len(self.sessions) else -1
        try:
            self.sessions = audio_sessions.list_sessions()
        except audio_sessions.AudioSessionError as error:
            self.sessions = []
            self._announce(str(error))
        self._cards = {}
        for session in self.sessions:
            try:
                self._cards[session.process_id] = audio_routing.app_output(session.process_id)
            except audio_routing.AudioRoutingError:
                self._cards[session.process_id] = None
        self.card.SetItems([_DEFAULT_CARD, *[d.name for d in self.outputs]])
        self._fill_programs(previous)
        self._fill_devices()

    def _card_name(self, process_id: int) -> str:
        device_id = self._cards.get(process_id)
        if device_id is None:
            return "Cannot be moved"
        if not device_id:
            return _DEFAULT_CARD
        return next((d.name for d in self.outputs if d.device_id == device_id), device_id)

    @staticmethod
    def _hear(session) -> str:
        return "Muted" if session.muted else f"Yes, {round(session.volume * 100)} percent"

    def _fill_programs(self, keep_pid: int = -1) -> None:
        self.programs.DeleteAllItems()
        for row, session in enumerate(self.sessions):
            self.programs.InsertItem(row, session.name)
            self.programs.SetItem(row, 1, self._hear(session))
            self.programs.SetItem(row, 2, "Playing" if session.peak > 0.001 else "Quiet")
            self.programs.SetItem(row, 3, self._card_name(session.process_id))
        has = bool(self.sessions)
        for control in (self.mute, self.volume, self.card):
            control.Enable(has)
        if has:
            row = next((i for i, s in enumerate(self.sessions) if s.process_id == keep_pid), 0)
            self.programs.Select(row)
            self.programs.Focus(row)
            self._show_program(row)

    def _fill_devices(self) -> None:
        from quill.platform.windows import audio_routing

        for control, devices in ((self.playback, self.outputs), (self.recording, self.inputs)):
            control.DeleteAllItems()
            for row, device in enumerate(devices):
                roles = []
                if device.is_default:
                    roles.append("Default")
                if device.is_communications:
                    roles.append("Calls")
                control.InsertItem(row, device.name)
                control.SetItem(row, 1, ", ".join(roles) or "-")
                if control is self.recording:
                    try:
                        level, muted = audio_routing.input_level(device.device_id)
                        control.SetItem(
                            row, 2, "Muted" if muted else f"{round(level * 100)} percent"
                        )
                    except audio_routing.AudioRoutingError:
                        control.SetItem(row, 2, "Unknown")
            if devices:
                control.Select(0)
        if self.inputs:
            self._input_selected(None)

    # -- programs ---------------------------------------------------------------------

    def _row(self) -> int:
        row = self.programs.GetFirstSelected()
        return row if 0 <= row < len(self.sessions) else -1

    def _show_program(self, row: int) -> None:
        session = self.sessions[row]
        self.volume.SetValue(round(session.volume * 100))
        device_id = self._cards.get(session.process_id)
        index = 0
        if device_id:
            index = next((i + 1 for i, d in enumerate(self.outputs) if d.device_id == device_id), 0)
        self.card.SetSelection(index)
        self.card.Enable(device_id is not None)

    def _program_selected(self, _event: wx.ListEvent) -> None:
        row = self._row()
        if row >= 0:
            self._show_program(row)

    def _program_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_SPACE and not event.HasAnyModifiers():
            self._toggle_mute()
            return
        if event.GetKeyCode() == wx.WXK_F5:
            self.refresh()
            return
        event.Skip()

    def _volume_key(self, event: wx.KeyEvent) -> None:
        step = {wx.WXK_PAGEUP: 10, wx.WXK_PAGEDOWN: -10}.get(event.GetKeyCode())
        if step is None:
            event.Skip()
            return
        self.volume.SetValue(min(100, max(0, self.volume.GetValue() + step)))
        self._volume_changed(None)

    def _toggle_mute(self) -> None:
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
        self.programs.SetItem(row, 1, self._hear(self.sessions[row]))

    def _volume_changed(self, _event: wx.Event | None) -> None:
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
        self.programs.SetItem(row, 1, self._hear(self.sessions[row]))

    def _card_changed(self, _event: wx.Event) -> None:
        from quill.platform.windows.audio_routing import AudioRoutingError, set_app_output

        row = self._row()
        if row < 0:
            return
        index = self.card.GetSelection()
        device_id = self.outputs[index - 1].device_id if index > 0 else ""
        session = self.sessions[row]
        try:
            set_app_output(session.process_id, device_id)
        except AudioRoutingError as error:
            self._announce(str(error))
            self._show_program(row)
            return
        self._cards[session.process_id] = device_id
        self.programs.SetItem(row, 3, self._card_name(session.process_id))

    # -- devices ------------------------------------------------------------------------

    def _make_default(self, flow: int, communications: bool) -> None:
        from quill.platform.windows.audio_routing import AudioRoutingError, set_default_device

        control, devices = (
            (self.playback, self.outputs) if flow == 0 else (self.recording, self.inputs)
        )
        row = control.GetFirstSelected()
        if not 0 <= row < len(devices):
            return
        try:
            set_default_device(devices[row].device_id, communications=communications)
        except AudioRoutingError as error:
            self._announce(str(error))
            return
        role = "communications" if communications else "default"
        self._announce(f"{devices[row].name} is now the {role} device.")
        self.refresh()

    def _input_row(self) -> int:
        row = self.recording.GetFirstSelected()
        return row if 0 <= row < len(self.inputs) else -1

    def _input_selected(self, _event: wx.ListEvent | None) -> None:
        from quill.platform.windows.audio_routing import AudioRoutingError, input_level

        row = self._input_row()
        if row < 0:
            return
        try:
            level, muted = input_level(self.inputs[row].device_id)
        except AudioRoutingError:
            return
        self.input_level.SetValue(round(level * 100))
        self.input_mute.SetValue(muted)

    def _input_level_changed(self, _event: wx.Event) -> None:
        from quill.platform.windows.audio_routing import AudioRoutingError, set_input_level

        row = self._input_row()
        if row < 0:
            return
        try:
            set_input_level(self.inputs[row].device_id, self.input_level.GetValue() / 100)
        except AudioRoutingError as error:
            self._announce(str(error))
            return
        self.recording.SetItem(row, 2, f"{self.input_level.GetValue()} percent")

    def _input_mute_changed(self, _event: wx.Event) -> None:
        from quill.platform.windows.audio_routing import AudioRoutingError, set_input_mute

        row = self._input_row()
        if row < 0:
            return
        try:
            set_input_mute(self.inputs[row].device_id, self.input_mute.GetValue())
        except AudioRoutingError as error:
            self._announce(str(error))
            return
        self.recording.SetItem(
            row,
            2,
            "Muted" if self.input_mute.GetValue() else f"{self.input_level.GetValue()} percent",
        )
