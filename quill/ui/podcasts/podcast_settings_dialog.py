"""Tools > Media > Podcasts... > Podcast Settings... -- the global defaults
every show inherits unless it sets its own override (playback mode,
retention, speed, download location, and what happens to downloaded files
when you unsubscribe from a show).
"""

from __future__ import annotations

import dataclasses
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
        #: The starting record, so Save can dataclasses.replace() the fields
        #: this dialog actually edits and carry every other field through
        #: unchanged (view mode, sort mode, EQ, skip seconds, ...) instead of
        #: constructing a fresh PodcastSettings() that silently resets them
        #: to their class defaults.
        self._settings = settings

        self.dialog = wx.Dialog(
            parent, title="Podcast Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((540, 560))
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

        self._always_sync_check = wx.CheckBox(
            self.dialog,
            label="Always s&ync the full catalog (download every episode the feed offers)",
        )
        self._always_sync_check.SetName(
            "Always Sync: backfill and download the show's whole catalog, not just new episodes; "
            "works best with retention set to keep all"
        )
        self._always_sync_check.SetValue(settings.always_sync_full_catalog)
        self._always_sync_check.Bind(wx.EVT_CHECKBOX, self._on_always_sync_toggle)
        root.Add(self._always_sync_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._auto_trim_check = wx.CheckBox(
            self.dialog, label="Auto-&trim silence from downloaded episodes"
        )
        self._auto_trim_check.SetName(
            "Trim leading and trailing silence from each finished download"
        )
        self._auto_trim_check.SetValue(settings.auto_trim_silence)
        root.Add(self._auto_trim_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._normalize_check = wx.CheckBox(
            self.dialog, label="&Normalize loudness of downloaded episodes"
        )
        self._normalize_check.SetName(
            "Even out volume across downloaded episodes using the audiobook builder's loudness pass"
        )
        self._normalize_check.SetValue(settings.normalize_loudness)
        root.Add(self._normalize_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        reconnect_box = wx.StaticBoxSizer(
            wx.VERTICAL, self.dialog, "If a download's connection drops"
        )
        self._reconnect_check = wx.CheckBox(
            self.dialog, label="&Reconnect and keep downloading automatically"
        )
        self._reconnect_check.SetName(
            "When the internet hiccups mid-download, retry automatically instead of "
            "landing in Failed status; the partial file resumes from where it left off"
        )
        self._reconnect_check.SetValue(settings.reconnect_enabled)
        reconnect_box.Add(self._reconnect_check, 0, wx.ALL, 6)
        reconnect_grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        reconnect_grid.Add(
            wx.StaticText(self.dialog, label="Reconnect &attempts:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._reconnect_attempts_ctrl = wx.SpinCtrl(self.dialog, min=1, max=99)
        self._reconnect_attempts_ctrl.SetValue(max(1, settings.reconnect_max_attempts))
        self._reconnect_attempts_ctrl.SetName(
            "How many times to try reconnecting before giving up on the download"
        )
        reconnect_grid.Add(self._reconnect_attempts_ctrl, 0)
        reconnect_grid.Add(
            wx.StaticText(self.dialog, label="Seconds &between attempts:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._reconnect_wait_ctrl = wx.SpinCtrl(self.dialog, min=1, max=600)
        self._reconnect_wait_ctrl.SetValue(max(1, settings.reconnect_wait_seconds))
        self._reconnect_wait_ctrl.SetName("How long to wait before each reconnect attempt")
        reconnect_grid.Add(self._reconnect_wait_ctrl, 0)
        reconnect_box.Add(reconnect_grid, 0, wx.LEFT | wx.BOTTOM, 6)
        root.Add(reconnect_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

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
        save_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
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
            affirmative_label="OK",
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

    def _on_always_sync_toggle(self, _event: object) -> None:
        # Always Sync fights keep_last_n retention (backfill the catalog while
        # pruning to N undoes itself) -- nudge toward keep_all, never force it.
        if self._always_sync_check.GetValue():
            retention_index = self._retention_choice.GetSelection()
            if retention_index >= 0 and _RETENTION_MODES[retention_index] == "keep_last_n":
                self._retention_choice.SetSelection(_RETENTION_MODES.index("keep_all"))
                self._announce(
                    "Retention set to keep all episodes; Always Sync backfills the "
                    "whole catalog, which keep-last-N would immediately prune."
                )

    def _on_save(self, _event: object) -> None:
        playback_index = self._playback_choice.GetSelection()
        retention_index = self._retention_choice.GetSelection()
        speed_index = self._speed_choice.GetSelection()
        delete_index = self._delete_choice.GetSelection()
        self._result = dataclasses.replace(
            self._settings,
            playback_mode=_PLAYBACK_MODES[playback_index] if playback_index >= 0 else "download",
            retention=_RETENTION_MODES[retention_index] if retention_index >= 0 else "keep_all",
            retention_count=self._retention_count_ctrl.GetValue(),
            speed=float(_SPEED_CHOICES[speed_index].rstrip("x")) if speed_index >= 0 else 1.0,
            download_root=self._download_root_ctrl.GetValue().strip(),
            delete_files_on_remove=_DELETE_POLICIES[delete_index] if delete_index >= 0 else "ask",
            always_sync_full_catalog=self._always_sync_check.GetValue(),
            auto_trim_silence=self._auto_trim_check.GetValue(),
            normalize_loudness=self._normalize_check.GetValue(),
            reconnect_enabled=self._reconnect_check.GetValue(),
            reconnect_max_attempts=self._reconnect_attempts_ctrl.GetValue(),
            reconnect_wait_seconds=self._reconnect_wait_ctrl.GetValue(),
        )
        self.dialog.EndModal(self._wx.ID_OK)
