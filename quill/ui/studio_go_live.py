"""Broadcast live: the setup window for Icecast and SHOUTcast (roadmap section 6).

Top to bottom: the server, the show, the sound quality (plain presets, with
Custom for every technical choice), what goes into the stream (a list with a
state column; the screen reader asks first), a saved copy, then Check. The
check's result takes focus and is read once; Go live stays disabled while
any Stop remains, and any change asks for a new check.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import wx

from quill.core.streaming import (
    BITRATES,
    FORMATS,
    LOUDNESS,
    QUALITY_PRESETS,
    SAMPLE_RATES,
    StreamingError,
    StreamSettings,
    validate,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

_IN, _OUT = "In the stream", "Left out"


class GoLiveDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        settings: StreamSettings,
        password: str,
        *,
        check: Callable[[StreamSettings, str, Callable[[str, bool], None]], None],
        test: Callable[[StreamSettings, str], None],
        confirm: Callable[[str, str], bool],
    ) -> None:
        super().__init__(
            parent, title="Broadcast live", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        from wx.lib.scrolledpanel import ScrolledPanel

        self._check_cb = check
        self._test_cb = test
        self._confirm = confirm
        self.sources = list(settings.sources)
        self.checked: tuple[StreamSettings, str] | None = None
        panel = ScrolledPanel(self)
        outer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, hgap=8, vgap=6)
        grid.AddGrowableCol(1)

        def label(text: str) -> None:
            # The label is created first, so it comes before its field in tab order.
            grid.Add(wx.StaticText(panel, label=text), 0, wx.ALIGN_CENTER_VERTICAL)

        def place(control: wx.Window, text: str) -> None:
            set_accessible_name(control, text.replace("&", ""))
            grid.Add(control, 1, wx.EXPAND)

        label("Server t&ype")
        self.kind = wx.Choice(panel, choices=["Icecast", "SHOUTcast"])
        self.kind.SetHelpText(
            "Which kind of server your stream host runs. Your host's settings page says."
        )
        place(self.kind, "Server t&ype")
        self.kind.SetSelection(0 if settings.kind == "icecast" else 1)
        label("Server &address")
        self.host = wx.TextCtrl(panel, value=settings.host)
        self.host.SetHelpText("The server's address, such as stream.example.org, without http.")
        place(self.host, "Server &address")
        label("&Port")
        self.port = wx.SpinCtrl(panel, min=1, max=65535, initial=settings.port)
        self.port.SetHelpText("The server's port, often 8000.")
        place(self.port, "&Port")
        label("&Mount (Icecast)")
        self.mount = wx.TextCtrl(panel, value=settings.mount)
        self.mount.SetHelpText(
            "Icecast only: the mount point, starting with a slash, such as /live."
        )
        place(self.mount, "&Mount (Icecast)")
        label("Stream &number (SHOUTcast)")
        self.stream_id = wx.SpinCtrl(panel, min=1, max=99, initial=settings.stream_id)
        self.stream_id.SetHelpText("SHOUTcast only: the stream number on the server, usually 1.")
        place(self.stream_id, "Stream &number (SHOUTcast)")
        label("&User name (Icecast)")
        self.user = wx.TextCtrl(panel, value=settings.user)
        self.user.SetHelpText("Icecast only: usually source.")
        place(self.user, "&User name (Icecast)")
        label("Pass&word")
        self.password = wx.TextCtrl(panel, value=password, style=wx.TE_PASSWORD)
        self.password.SetHelpText(
            "The source password. Studio keeps it in Windows Credential Manager, "
            "never in its settings or logs."
        )
        place(self.password, "Pass&word")
        self.secure = wx.CheckBox(panel, label="Use a secure connection")
        self.secure.SetValue(settings.secure)
        self.secure.SetHelpText("Only if your server offers TLS. Most radio servers do not.")
        grid.AddSpacer(1)
        grid.Add(self.secure)
        label("Show &title")
        self.title_field = wx.TextCtrl(panel, value=settings.title)
        self.title_field.SetHelpText("What listeners and directories see as the stream's name.")
        place(self.title_field, "Show &title")
        label("&Description")
        self.description = wx.TextCtrl(panel, value=settings.description)
        self.description.SetHelpText("A sentence about the show.")
        place(self.description, "&Description")
        label("&Genre")
        self.genre = wx.TextCtrl(panel, value=settings.genre)
        self.genre.SetHelpText("Such as Talk, Music or Podcast.")
        place(self.genre, "&Genre")
        label("Webs&ite")
        self.website = wx.TextCtrl(panel, value=settings.website)
        self.website.SetHelpText("Your show's web address, if any.")
        place(self.website, "Webs&ite")
        self.public = wx.CheckBox(panel, label="List this stream in public directories")
        self.public.SetValue(settings.public)
        self.public.SetHelpText(
            "Off keeps the stream unlisted: only people with the address find it."
        )
        grid.AddSpacer(1)
        grid.Add(self.public)
        label("Sound &quality")
        self.quality = wx.Choice(panel, choices=[v[0] for v in QUALITY_PRESETS.values()])
        self.quality.SetHelpText(
            "Speech is smallest; Music sounds best; Custom shows every technical choice below."
        )
        place(self.quality, "Sound &quality")
        self.quality.SetSelection(
            list(QUALITY_PRESETS).index(settings.quality)
            if settings.quality in QUALITY_PRESETS
            else 1
        )
        label("&Format")
        self.format = wx.Choice(panel, choices=[v[0] for v in FORMATS.values()])
        self.format.SetHelpText("The kind of sound listeners receive. SHOUTcast takes MP3 or AAC.")
        place(self.format, "&Format")
        self.format.SetSelection(list(FORMATS).index(settings.format))
        label("&Bit rate, kilobits a second")
        self.bitrate = wx.Choice(panel, choices=[str(b) for b in BITRATES])
        self.bitrate.SetHelpText("Higher sounds better and needs a faster upload.")
        place(self.bitrate, "&Bit rate, kilobits a second")
        self.bitrate.SetSelection(
            BITRATES.index(settings.bitrate) if settings.bitrate in BITRATES else 6
        )
        label("&Channels")
        self.channels = wx.Choice(panel, choices=["Stereo", "Mono"])
        self.channels.SetHelpText("Mono halves the size and suits a single voice.")
        place(self.channels, "&Channels")
        self.channels.SetSelection(0 if settings.channels == 2 else 1)
        label("Sample &rate, hertz")
        self.rate = wx.Choice(panel, choices=[str(r) for r in SAMPLE_RATES])
        self.rate.SetHelpText("44100 suits most streams.")
        place(self.rate, "Sample &rate, hertz")
        self.rate.SetSelection(SAMPLE_RATES.index(settings.sample_rate))
        label("&Loudness")
        self.loudness = wx.Choice(panel, choices=[v[0] for v in LOUDNESS.values()])
        self.loudness.SetHelpText(
            "An automatic level so the stream sounds even, with a limiter against "
            "distortion. Off sends the mix exactly as it is."
        )
        place(self.loudness, "&Loudness")
        self.loudness.SetSelection(
            list(LOUDNESS).index(settings.loudness) if settings.loudness in LOUDNESS else 0
        )
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        outer.Add(wx.StaticText(panel, label="What goes into the &stream"), 0, wx.LEFT, 10)
        self.list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=dip_size(panel, -1, 130)
        )
        set_accessible_name(self.list, "What goes into the stream")
        self.list.SetHelpText(
            "Each sound and whether listeners hear it. Space puts the selected one in or leaves "
            "it out. Your screen reader starts left out and asks first."
        )
        for column, (title, width) in enumerate((("Sound", 300), ("State", 140), ("Level", 80))):
            self.list.InsertColumn(column, title, width=width)
        self.list.Bind(wx.EVT_KEY_DOWN, self._list_key)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._show_level())
        outer.Add(self.list, 0, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(panel, label="Le&vel in the stream, decibels"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.level = wx.SpinCtrl(panel, min=-60, max=12, initial=0)
        set_accessible_name(self.level, "Level in the stream, decibels")
        self.level.SetHelpText(
            "How loud the selected sound is in the stream; recordings are separate."
        )
        self.level.Bind(wx.EVT_SPINCTRL, self._level_changed)
        row.Add(self.level, 0)
        outer.Add(row, 0, wx.LEFT | wx.RIGHT, 10)
        self.archive = wx.CheckBox(panel, label="Sav&e a copy of the show on this computer")
        self.archive.SetValue(settings.archive)
        self.archive.SetHelpText(
            "Keep a copy as FLAC while you broadcast, even through reconnects."
        )
        outer.Add(self.archive, 0, wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="Folder for the saved copy"), 0, wx.LEFT, 10)
        self.folder = wx.TextCtrl(panel, value=settings.archive_folder)
        set_accessible_name(self.folder, "Folder for the saved copy")
        self.folder.SetHelpText("Where the saved copy goes.")
        outer.Add(self.folder, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        actions = wx.BoxSizer(wx.HORIZONTAL)
        check = wx.Button(panel, label="Chec&k")
        check.SetHelpText("Check everything before going live. The result is read once.")
        check.Bind(wx.EVT_BUTTON, self._on_check)
        actions.Add(check, 0, wx.RIGHT, 8)
        test = wx.Button(panel, label="Test the c&onnection")
        test.SetHelpText("A private two-second test of the address and password. Nobody hears it.")
        test.Bind(wx.EVT_BUTTON, self._on_test)
        actions.Add(test, 0)
        outer.Add(actions, 0, wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="Check result"), 0, wx.LEFT, 10)
        self.result = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(panel, -1, 140)
        )
        set_accessible_name(self.result, "Check result")
        self.result.SetHelpText("Where the stream goes, what is in it, then every Stop and Warn.")
        self.result.ChangeValue("Fill in your server, then press Check.")
        outer.Add(self.result, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(outer)
        panel.SetupScrolling(scroll_x=False)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(panel, 1, wx.EXPAND)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            self, affirmative_id=wx.ID_OK, affirmative_label="Go live", cancel_id=wx.ID_CANCEL
        )
        self.go = self.FindWindow(wx.ID_OK)
        if self.go is not None:
            self.go.SetHelpText("Start broadcasting. Available after a check finds no Stop.")
            self.go.Enable(False)
        cancel = self.FindWindow(wx.ID_CANCEL)
        if cancel is not None:
            cancel.SetHelpText("Close without broadcasting.")
        self.SetSizer(layout)
        available = wx.GetClientDisplayRect()
        self.SetSize((min(760, available.width), min(820, available.height)))
        for control in panel.GetChildren():
            for event in (wx.EVT_TEXT, wx.EVT_CHOICE, wx.EVT_CHECKBOX, wx.EVT_SPINCTRL):
                control.Bind(event, self._stale)
        self.quality.Bind(wx.EVT_CHOICE, self._quality_changed)
        self._fill()
        self._quality_changed(None)
        self.host.SetFocus()

    # -- sources ---------------------------------------------------------------------

    def _fill(self, select: int = 0) -> None:
        self.list.DeleteAllItems()
        for row, source in enumerate(self.sources):
            self.list.InsertItem(row, source.label)
            self.list.SetItem(row, 1, _IN if source.on else _OUT)
            self.list.SetItem(row, 2, f"{source.level_db:+.0f} dB")
        if self.sources:
            self.list.Select(min(select, len(self.sources) - 1))
            self._show_level()

    def _row(self) -> int:
        row = self.list.GetFirstSelected()
        return row if 0 <= row < len(self.sources) else -1

    def _show_level(self) -> None:
        row = self._row()
        if row >= 0:
            self.level.SetValue(round(self.sources[row].level_db))

    def _list_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_SPACE and not event.HasAnyModifiers():
            self.toggle()
            return
        event.Skip()

    def toggle(self) -> None:
        row = self._row()
        if row < 0:
            return
        source = self.sources[row]
        if (
            source.is_screen_reader
            and not source.on
            and not self._confirm(
                "Listeners will hear everything your screen reader says while you are live. "
                "Put it in?",
                "Screen reader in the stream",
            )
        ):
            return
        self.sources[row] = replace(source, on=not source.on)
        self.list.SetItem(row, 1, _IN if self.sources[row].on else _OUT)
        self._stale(None)

    def _level_changed(self, event: wx.Event) -> None:
        row = self._row()
        if row >= 0:
            self.sources[row] = replace(self.sources[row], level_db=float(self.level.GetValue()))
            self.list.SetItem(row, 2, f"{self.level.GetValue():+d} dB")
        self._stale(event)

    # -- settings and the check ---------------------------------------------------------

    def _quality_changed(self, event: wx.Event | None) -> None:
        custom = list(QUALITY_PRESETS)[max(0, self.quality.GetSelection())] == "custom"
        for control in (self.format, self.bitrate, self.channels, self.rate):
            control.Enable(custom)
        self._stale(event)

    def _stale(self, event: wx.Event | None) -> None:
        self.checked = None
        if getattr(self, "go", None) is not None:
            self.go.Enable(False)
        if event is not None:
            event.Skip()

    def build(self) -> StreamSettings:
        settings = StreamSettings(
            kind="icecast" if self.kind.GetSelection() == 0 else "shoutcast",
            host=self.host.GetValue().strip(),
            port=self.port.GetValue(),
            mount=self.mount.GetValue().strip() or "/live",
            stream_id=self.stream_id.GetValue(),
            user=self.user.GetValue().strip() or "source",
            secure=self.secure.GetValue(),
            title=self.title_field.GetValue().strip(),
            description=self.description.GetValue().strip(),
            genre=self.genre.GetValue().strip(),
            website=self.website.GetValue().strip(),
            public=self.public.GetValue(),
            quality=list(QUALITY_PRESETS)[max(0, self.quality.GetSelection())],
            format=list(FORMATS)[max(0, self.format.GetSelection())],  # type: ignore[arg-type]
            bitrate=BITRATES[max(0, self.bitrate.GetSelection())],
            channels=2 if self.channels.GetSelection() == 0 else 1,
            sample_rate=SAMPLE_RATES[max(0, self.rate.GetSelection())],
            loudness=list(LOUDNESS)[max(0, self.loudness.GetSelection())],
            archive=self.archive.GetValue(),
            archive_folder=self.folder.GetValue().strip(),
            sources=tuple(self.sources),
        )
        return settings

    def _on_check(self, _event: wx.Event) -> None:
        settings, password = self.build(), self.password.GetValue()
        self.result.ChangeValue("Checking.")

        def done(text: str, ok: bool) -> None:
            if not self:
                return
            self.result.ChangeValue(text)
            self.checked = (settings, password) if ok else None
            if self.go is not None:
                self.go.Enable(ok)
            self.result.SetFocus()

        self._check_cb(settings, password, done)

    def _on_test(self, _event: wx.Event) -> None:
        settings = self.build()
        try:
            validate(settings)
        except StreamingError as error:
            self.result.ChangeValue(f"Stop: {error}")
            self.result.SetFocus()
            return
        self._test_cb(settings, self.password.GetValue())
