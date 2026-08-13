"""Tools > Media > Podcasts... > Podcast Settings... -- the global defaults
every show inherits unless it sets its own override (playback mode,
retention, speed, download location, and what happens to downloaded files
when you unsubscribe from a show).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

from quill.core.podcasts.models import SPEED_MAX, SPEED_MIN, PodcastSettings
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
#: Auto-download (1.1.0): the acquisition policy every new show starts with.
_AUTO_DOWNLOAD_LABELS = (
    "None -- download by hand",
    "The newest episode",
    "The newest 3",
    "The newest 5",
    "The newest 10",
    "Every episode (full catalog)",
)
_AUTO_DOWNLOAD_VALUES = (0, 1, 3, 5, 10, -1)
#: Which node the library tree lands on at launch.
_LAUNCH_VIEW_LABELS = (
    "The top of the library",
    "New Episodes",
    "Continue Listening",
    "Inbox",
    "Favorites",
    "Recently Expired",
)
_LAUNCH_VIEW_VALUES = (
    "",
    "new_episodes",
    "continue_listening",
    "inbox",
    "favorites",
    "recently_expired",
)


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
        # 1.1.0 added the acquisition, storage, and session rows; the dialog
        # is sized to its content (Fit below) with a floor, rather than a
        # fixed height that would clip the new controls off the bottom.
        self.dialog.SetMinSize((620, 640))
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
        # A continuum, not six fixed choices (1.1.0): 0.5x to 5.0x in tenths,
        # which is the range Earshot offers and the range the engines hold
        # pitch across. Speed Up / Speed Down on the Episode menu step the
        # same value, so the dialog and the keys cannot disagree.
        self._speed_ctrl = wx.SpinCtrlDouble(
            self.dialog, min=SPEED_MIN, max=SPEED_MAX, inc=0.1, initial=settings.speed
        )
        self._speed_ctrl.SetDigits(1)
        self._speed_ctrl.SetName(
            f"Default playback speed, {SPEED_MIN} to {SPEED_MAX} times normal, "
            "for podcasts without their own override"
        )
        grid.Add(self._speed_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="&Automatically download:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._auto_download_choice = wx.Choice(self.dialog, choices=list(_AUTO_DOWNLOAD_LABELS))
        self._auto_download_choice.SetName(
            "How many of a show's newest episodes to fetch without being asked, "
            "on subscribe and on every refresh"
        )
        effective = settings.effective_auto_download_count
        self._auto_download_choice.SetSelection(
            _AUTO_DOWNLOAD_VALUES.index(effective) if effective in _AUTO_DOWNLOAD_VALUES else 0
        )
        grid.Add(self._auto_download_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Inbox: keep at most (0 = no limit):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._inbox_max_ctrl = wx.SpinCtrl(self.dialog, min=0, max=999)
        self._inbox_max_ctrl.SetValue(settings.inbox_max_episodes)
        self._inbox_max_ctrl.SetName(
            "At most this many episodes in the Inbox per show. Trimming never "
            "deletes: episodes stay unplayed in their show's own list, and anything "
            "played, started, or queued is never trimmed."
        )
        grid.Add(self._inbox_max_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Delete downloads after (days, 0 = never):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._retention_days_ctrl = wx.SpinCtrl(self.dialog, min=0, max=3650)
        self._retention_days_ctrl.SetValue(settings.download_retention_days)
        self._retention_days_ctrl.SetName(
            "Delete a downloaded file once it is this many days old. Queued and "
            "part-played episodes are never deleted."
        )
        grid.Add(self._retention_days_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Total download storage cap (MB, 0 = none):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._storage_cap_ctrl = wx.SpinCtrl(self.dialog, min=0, max=1_000_000)
        self._storage_cap_ctrl.SetValue(settings.storage_cap_mb)
        self._storage_cap_ctrl.SetName(
            "A ceiling on total podcast download storage. When it is exceeded, "
            "already-played downloads are removed oldest first; a queued or "
            "part-played episode is never removed."
        )
        grid.Add(self._storage_cap_ctrl, 0)

        # Worded as reliability, not disk management, because that is what it
        # is for: a streamed episode you can seek, bookmark, find chapters in,
        # and keep listening to when the connection drops.
        grid.Add(
            wx.StaticText(self.dialog, label="&Streamed episodes:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._playback_cache_ctrl = wx.CheckBox(
            self.dialog, label="Keep streamed episodes ready while they play"
        )
        self._playback_cache_ctrl.SetValue(settings.playback_cache)
        self._playback_cache_ctrl.SetName(
            "Save a streamed episode's audio as it plays, so playback continues "
            "through a dropped connection, chapters can be found in it, and "
            "keeping it costs no second download. The audio is removed "
            "automatically; nothing you are listening to is ever removed."
        )
        grid.Add(self._playback_cache_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Space for streamed episodes (MB, 0 = no limit):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._playback_cache_cap_ctrl = wx.SpinCtrl(self.dialog, min=0, max=1_000_000)
        self._playback_cache_cap_ctrl.SetValue(settings.playback_cache_cap_mb)
        self._playback_cache_cap_ctrl.SetName(
            "How much room streamed episodes may use between them. The "
            "least-recently-played is removed first, and the episode playing "
            "now is never removed."
        )
        grid.Add(self._playback_cache_cap_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Start on this &view:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._launch_view_choice = wx.Choice(self.dialog, choices=list(_LAUNCH_VIEW_LABELS))
        self._launch_view_choice.SetName("Which part of the library QUILL Cast opens on")
        self._launch_view_choice.SetSelection(
            _LAUNCH_VIEW_VALUES.index(settings.default_launch_view)
            if settings.default_launch_view in _LAUNCH_VIEW_VALUES
            else 0
        )
        grid.Add(self._launch_view_choice, 1, wx.EXPAND)

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

        self._auto_download_queued_check = wx.CheckBox(
            self.dialog, label="Also download anything you add to the Play &Queue"
        )
        self._auto_download_queued_check.SetName(
            "An episode you queue is one you mean to play, so fetch it even if it is "
            "older than the automatic download count"
        )
        self._auto_download_queued_check.SetValue(settings.auto_download_queued)
        root.Add(self._auto_download_queued_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._auto_download_inbox_check = wx.CheckBox(
            self.dialog, label="Also download everything routed to the In&box"
        )
        self._auto_download_inbox_check.SetName(
            "Off by default: the Inbox is where episodes wait to be triaged, not a "
            "commitment to listen to them"
        )
        self._auto_download_inbox_check.SetValue(settings.auto_download_inbox)
        root.Add(self._auto_download_inbox_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        session_box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "When an episode finishes")
        self._continue_queue_check = wx.CheckBox(
            self.dialog, label="Play the next episode in the Play &Queue"
        )
        self._continue_queue_check.SetName(
            "Auto-advance through the Play Queue. On by default -- this is what "
            "QUILL Cast has always done."
        )
        self._continue_queue_check.SetValue(settings.continue_after_queue)
        session_box.Add(self._continue_queue_check, 0, wx.ALL, 6)
        self._continue_group_check = wx.CheckBox(
            self.dialog, label="When the queue is empty, keep going with the same podcast"
        )
        self._continue_group_check.SetName(
            "Carry on with the show's next unplayed episode once the queue runs out. "
            "Off by default: with both of these off, playback stops at the end of "
            "the episode you started."
        )
        self._continue_group_check.SetValue(settings.continue_after_group)
        session_box.Add(self._continue_group_check, 0, wx.LEFT | wx.BOTTOM, 6)
        root.Add(session_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._name_first_check = wx.CheckBox(
            self.dialog, label="Read the podcast &name before the episode title in mixed lists"
        )
        self._name_first_check.SetName(
            "In the Inbox, New Episodes, and other cross-show lists, put the podcast "
            "name first so rows group by show when you skim by first letter"
        )
        self._name_first_check.SetValue(settings.announce_show_name_first)
        root.Add(self._name_first_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

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
        self.dialog.Fit()

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
        delete_index = self._delete_choice.GetSelection()
        auto_index = max(0, self._auto_download_choice.GetSelection())
        auto_count = _AUTO_DOWNLOAD_VALUES[auto_index]
        launch_index = max(0, self._launch_view_choice.GetSelection())
        # Always Sync and "download every episode" are the same instruction;
        # either control setting one sets the other, so the two can never end
        # up saying different things about the same library.
        always_sync = self._always_sync_check.GetValue() or auto_count == -1
        self._result = dataclasses.replace(
            self._settings,
            playback_mode=_PLAYBACK_MODES[playback_index] if playback_index >= 0 else "download",
            retention=_RETENTION_MODES[retention_index] if retention_index >= 0 else "keep_all",
            retention_count=self._retention_count_ctrl.GetValue(),
            speed=float(self._speed_ctrl.GetValue()),
            download_root=self._download_root_ctrl.GetValue().strip(),
            delete_files_on_remove=_DELETE_POLICIES[delete_index] if delete_index >= 0 else "ask",
            always_sync_full_catalog=always_sync,
            auto_download_count=-1 if always_sync else auto_count,
            auto_download_queued=self._auto_download_queued_check.GetValue(),
            auto_download_inbox=self._auto_download_inbox_check.GetValue(),
            inbox_max_episodes=self._inbox_max_ctrl.GetValue(),
            download_retention_days=self._retention_days_ctrl.GetValue(),
            storage_cap_mb=self._storage_cap_ctrl.GetValue(),
            playback_cache=self._playback_cache_ctrl.GetValue(),
            playback_cache_cap_mb=self._playback_cache_cap_ctrl.GetValue(),
            continue_after_queue=self._continue_queue_check.GetValue(),
            continue_after_group=self._continue_group_check.GetValue(),
            announce_show_name_first=self._name_first_check.GetValue(),
            default_launch_view=_LAUNCH_VIEW_VALUES[launch_index],
            auto_trim_silence=self._auto_trim_check.GetValue(),
            normalize_loudness=self._normalize_check.GetValue(),
            reconnect_enabled=self._reconnect_check.GetValue(),
            reconnect_max_attempts=self._reconnect_attempts_ctrl.GetValue(),
            reconnect_wait_seconds=self._reconnect_wait_ctrl.GetValue(),
        )
        self.dialog.EndModal(self._wx.ID_OK)
