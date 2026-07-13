"""Tools > Media > Podcasts... > Podcast Settings... -- the global defaults
every show inherits unless it sets its own override (playback mode,
retention, speed, download location, and what happens to downloaded files
when you unsubscribe from a show).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.models import PodcastSettings
from quill.ui.dialog_contract import apply_modal_ids

_PLAYBACK_MODES = ("download", "stream")
_PLAYBACK_LABELS = ("Download episodes", "Stream episodes")
_RETENTION_MODES = ("keep_all", "keep_last_n", "delete_after_play")
_RETENTION_LABELS = (
    "Keep every episode",
    "Keep only the most recent episodes",
    "Delete after playing",
)
_DELETE_POLICIES = ("ask", "always", "never")
_DELETE_LABELS = ("Ask me each time", "Always delete them", "Never delete them")
_SPEED_CHOICES = ("0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x")


class PodcastSettingsDialog:
    """Returns the updated :class:`PodcastSettings`, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        settings: PodcastSettings,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: PodcastSettings | None = None

        self.dialog = wx.Dialog(
            parent, title="Podcast Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((540, 480))
        root = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(
            wx.StaticText(self.dialog, label="Default &playback mode:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._playback_choice = wx.Choice(self.dialog, choices=list(_PLAYBACK_LABELS))
        self._playback_choice.SetName(
            "Whether new podcasts download episodes or stream them by default"
        )
        if settings.playback_mode in _PLAYBACK_MODES:
            self._playback_choice.SetSelection(_PLAYBACK_MODES.index(settings.playback_mode))
        grid.Add(self._playback_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="Default &retention:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._retention_choice = wx.Choice(self.dialog, choices=list(_RETENTION_LABELS))
        self._retention_choice.SetName(
            "What happens to downloaded episode files over time, by default"
        )
        if settings.retention in _RETENTION_MODES:
            self._retention_choice.SetSelection(_RETENTION_MODES.index(settings.retention))
        grid.Add(self._retention_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Keep the most recent:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._retention_count_ctrl = wx.SpinCtrl(self.dialog, min=1, max=999)
        self._retention_count_ctrl.SetValue(settings.retention_count)
        self._retention_count_ctrl.SetName(
            "How many recent episodes to keep, when retention is set to keep only the most recent"
        )
        grid.Add(self._retention_count_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Default playback &speed:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._speed_choice = wx.Choice(self.dialog, choices=list(_SPEED_CHOICES))
        self._speed_choice.SetName("Default playback speed for podcasts without their own override")
        label = f"{settings.speed:g}x"
        self._speed_choice.SetSelection(
            _SPEED_CHOICES.index(label) if label in _SPEED_CHOICES else _SPEED_CHOICES.index("1.0x")
        )
        grid.Add(self._speed_choice, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="&Download location:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._download_root_ctrl = wx.TextCtrl(self.dialog, value=settings.download_root)
        self._download_root_ctrl.SetName(
            "Where downloaded episodes are saved; blank uses the default podcasts folder"
        )
        browse_btn = wx.Button(self.dialog, label="&Browse...")
        browse_btn.SetName("Choose a download location")
        dest_row.Add(self._download_root_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        dest_row.Add(browse_btn, 0)
        grid.Add(dest_row, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&When I unsubscribe, delete downloaded files:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._delete_choice = wx.Choice(self.dialog, choices=list(_DELETE_LABELS))
        self._delete_choice.SetName(
            "What to do with a show's downloaded episode files when you unsubscribe from it"
        )
        if settings.delete_files_on_remove in _DELETE_POLICIES:
            self._delete_choice.SetSelection(
                _DELETE_POLICIES.index(settings.delete_files_on_remove)
            )
        grid.Add(self._delete_choice, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        hint = wx.StaticText(
            self.dialog,
            label=(
                "Any podcast can override these defaults from its own context "
                "menu; these are only what a newly subscribed show starts with."
            ),
        )
        hint.Wrap(480)
        root.Add(hint, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(self.dialog, wx.ID_OK, "&Save")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.AddStretchSpacer()
        btn_row.Add(save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def show(self) -> PodcastSettings | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Podcast Settings", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_browse(self, _event: object) -> None:
        wx = self._wx
        with wx.DirDialog(
            self.dialog, "Choose a download location"
        ) as dlg:  # dialog_button_contract: exempt
            if dlg.ShowModal() == wx.ID_OK:
                self._download_root_ctrl.SetValue(dlg.GetPath())

    def _on_save(self, _event: object) -> None:
        playback_index = self._playback_choice.GetSelection()
        retention_index = self._retention_choice.GetSelection()
        speed_index = self._speed_choice.GetSelection()
        delete_index = self._delete_choice.GetSelection()
        self._result = PodcastSettings(
            playback_mode=_PLAYBACK_MODES[playback_index] if playback_index >= 0 else "download",
            retention=_RETENTION_MODES[retention_index] if retention_index >= 0 else "keep_all",
            retention_count=self._retention_count_ctrl.GetValue(),
            speed=float(_SPEED_CHOICES[speed_index].rstrip("x")) if speed_index >= 0 else 1.0,
            download_root=self._download_root_ctrl.GetValue().strip(),
            delete_files_on_remove=_DELETE_POLICIES[delete_index] if delete_index >= 0 else "ask",
        )
        self.dialog.EndModal(self._wx.ID_OK)
