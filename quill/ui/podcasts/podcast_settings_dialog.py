"""Tools > Media > Podcasts... > Podcast Settings... -- the global defaults
every show inherits unless it sets its own override (playback mode,
retention, speed, download location, and what happens to downloaded files
when you unsubscribe from a show).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

from quill.core.podcasts import settings_help, volume_boost
from quill.core.podcasts.models import SPEED_MAX, SPEED_MIN, PodcastSettings
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.podcasts.podcast_settings_choices import (
    _AUTO_DOWNLOAD_LABELS,
    _AUTO_DOWNLOAD_VALUES,
    _DELETE_LABELS,
    _DELETE_POLICIES,
    _HISTORY_LABELS,
    _HISTORY_VALUES,
    _LAUNCH_VIEW_LABELS,
    _LAUNCH_VIEW_VALUES,
    _PLAYBACK_LABELS,
    _PLAYBACK_MODES,
    _RETENTION_LABELS,
    _RETENTION_MODES,
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
        self._playback_choice.SetName(settings_help.HELP["playback_default"])
        self._playback_choice.SetHelpText(settings_help.HELP["playback_default"])
        if settings.playback_mode in _PLAYBACK_MODES:
            self._playback_choice.SetSelection(_PLAYBACK_MODES.index(settings.playback_mode))
        grid.Add(self._playback_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="Defa&ult retention:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._retention_choice = wx.Choice(self.dialog, choices=list(_RETENTION_LABELS))
        self._retention_choice.SetName(settings_help.HELP["retention"])
        self._retention_choice.SetHelpText(settings_help.HELP["retention"])
        if settings.retention in _RETENTION_MODES:
            self._retention_choice.SetSelection(_RETENTION_MODES.index(settings.retention))
        grid.Add(self._retention_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Keep the most recent:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._retention_count_ctrl = wx.SpinCtrl(self.dialog, min=1, max=999)
        self._retention_count_ctrl.SetValue(settings.retention_count)
        self._retention_count_ctrl.SetName(settings_help.HELP["keep_last_n"])
        self._retention_count_ctrl.SetHelpText(settings_help.HELP["keep_last_n"])
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
        self._auto_download_choice.SetName(settings_help.HELP["auto_download"])
        self._auto_download_choice.SetHelpText(settings_help.HELP["auto_download"])
        effective = settings.effective_auto_download_count
        self._auto_download_choice.SetSelection(
            _AUTO_DOWNLOAD_VALUES.index(effective) if effective in _AUTO_DOWNLOAD_VALUES else 0
        )
        grid.Add(self._auto_download_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="Inbox: keep at most (&0 = no limit):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._inbox_max_ctrl = wx.SpinCtrl(self.dialog, min=0, max=999)
        self._inbox_max_ctrl.SetValue(settings.inbox_max_episodes)
        self._inbox_max_ctrl.SetName(settings_help.HELP["inbox_max"])
        self._inbox_max_ctrl.SetHelpText(settings_help.HELP["inbox_max"])
        grid.Add(self._inbox_max_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Keep my listening &history for:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._history_choice = wx.Choice(self.dialog, choices=list(_HISTORY_LABELS))
        self._history_choice.SetName(settings_help.HELP["history_days"])
        self._history_choice.SetHelpText(settings_help.HELP["history_days"])
        history_days = int(getattr(settings, "history_retention_days", 90))
        self._history_choice.SetSelection(
            _HISTORY_VALUES.index(history_days) if history_days in _HISTORY_VALUES else 2
        )
        grid.Add(self._history_choice, 1, wx.EXPAND)

        self._metered_check = wx.CheckBox(
            self.dialog, label="Download automatically on a &metered connection"
        )
        self._metered_check.SetName(settings_help.HELP["metered"])
        self._metered_check.SetHelpText(settings_help.HELP["metered"])
        self._metered_check.SetValue(bool(getattr(settings, "download_on_metered", True)))
        grid.Add(self._metered_check, 0)

        self._notify_check = wx.CheckBox(self.dialog, label="&Notify me when downloads finish")
        self._notify_check.SetName(settings_help.HELP["download_notify"])
        self._notify_check.SetHelpText(settings_help.HELP["download_notify"])
        self._notify_check.SetValue(bool(getattr(settings, "download_notify", False)))
        grid.Add(self._notify_check, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Volume &Boost:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._boost_choice = wx.Choice(
            self.dialog, choices=[label for _v, label, _f in volume_boost.LEVELS]
        )
        self._boost_choice.SetName(settings_help.HELP["volume_boost"])
        self._boost_choice.SetHelpText(settings_help.HELP["volume_boost"])
        self._boost_choice.SetHelpText(settings_help.HELP["volume_boost"])
        self._boost_choice.SetSelection(
            volume_boost.index_of(getattr(settings, "volume_boost", volume_boost.OFF))
        )
        grid.Add(self._boost_choice, 1, wx.EXPAND)

        self._streaks_check = wx.CheckBox(
            self.dialog, label="Show listenin&g streaks in Statistics"
        )
        self._streaks_check.SetName(settings_help.HELP["streaks"])
        self._streaks_check.SetHelpText(settings_help.HELP["streaks"])
        self._streaks_check.SetValue(bool(getattr(settings, "stats_streaks_enabled", False)))
        grid.Add(self._streaks_check, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Delete downloads after (days, 0 = never):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._retention_days_ctrl = wx.SpinCtrl(self.dialog, min=0, max=3650)
        self._retention_days_ctrl.SetValue(settings.download_retention_days)
        self._retention_days_ctrl.SetName(settings_help.HELP["delete_after_days"])
        self._retention_days_ctrl.SetHelpText(settings_help.HELP["delete_after_days"])
        grid.Add(self._retention_days_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="When an episode has been played:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._delete_played_check = wx.CheckBox(self.dialog, label="Delete its downloaded &file")
        self._delete_played_check.SetName(settings_help.HELP["delete_after_playing"])
        self._delete_played_check.SetHelpText(settings_help.HELP["delete_after_playing"])
        self._delete_played_check.SetValue(bool(getattr(settings, "delete_after_play", False)))
        grid.Add(self._delete_played_check, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Total download storage cap (MB, 0 = none):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._storage_cap_ctrl = wx.SpinCtrl(self.dialog, min=0, max=1_000_000)
        self._storage_cap_ctrl.SetValue(settings.storage_cap_mb)
        self._storage_cap_ctrl.SetName(settings_help.HELP["storage_cap"])
        self._storage_cap_ctrl.SetHelpText(settings_help.HELP["storage_cap"])
        grid.Add(self._storage_cap_ctrl, 0)

        # Worded as reliability, not disk management, because that is what it
        # is for: a streamed episode you can seek, bookmark, find chapters in,
        # and keep listening to when the connection drops.
        grid.Add(
            wx.StaticText(self.dialog, label="Streamed episodes:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._playback_cache_ctrl = wx.CheckBox(
            self.dialog, label="Keep streamed episodes ready while they play"
        )
        self._playback_cache_ctrl.SetValue(settings.playback_cache)
        self._playback_cache_ctrl.SetName(settings_help.HELP["playback_cache"])
        self._playback_cache_ctrl.SetHelpText(settings_help.HELP["playback_cache"])
        grid.Add(self._playback_cache_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Space for streamed episodes (MB, 0 = no limit):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._playback_cache_cap_ctrl = wx.SpinCtrl(self.dialog, min=0, max=1_000_000)
        self._playback_cache_cap_ctrl.SetValue(settings.playback_cache_cap_mb)
        self._playback_cache_cap_ctrl.SetName(settings_help.HELP["playback_cache_cap"])
        self._playback_cache_cap_ctrl.SetHelpText(settings_help.HELP["playback_cache_cap"])
        grid.Add(self._playback_cache_cap_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Start on this &view:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._launch_view_choice = wx.Choice(self.dialog, choices=list(_LAUNCH_VIEW_LABELS))
        self._launch_view_choice.SetName(settings_help.HELP["launch_view"])
        self._launch_view_choice.SetHelpText(settings_help.HELP["launch_view"])
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
        self._download_root_ctrl.SetName(settings_help.HELP["download_folder"])
        self._download_root_ctrl.SetHelpText(settings_help.HELP["download_folder"])
        browse_btn = wx.Button(self.dialog, label="Browse...")
        browse_btn.SetName(settings_help.HELP["download_folder_button"])
        browse_btn.SetHelpText(settings_help.HELP["download_folder_button"])
        dest_row.Add(self._download_root_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        dest_row.Add(browse_btn, 0)
        grid.Add(dest_row, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&When I unsubscribe, delete downloaded files:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._delete_choice = wx.Choice(self.dialog, choices=list(_DELETE_LABELS))
        self._delete_choice.SetName(settings_help.HELP["unsubscribe_files"])
        self._delete_choice.SetHelpText(settings_help.HELP["unsubscribe_files"])
        if settings.delete_files_on_remove in _DELETE_POLICIES:
            self._delete_choice.SetSelection(
                _DELETE_POLICIES.index(settings.delete_files_on_remove)
            )
        grid.Add(self._delete_choice, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._auto_download_queued_check = wx.CheckBox(
            self.dialog, label="Also download anything you add to the Play &Queue"
        )
        self._auto_download_queued_check.SetName(settings_help.HELP["download_queued"])
        self._auto_download_queued_check.SetHelpText(settings_help.HELP["download_queued"])
        self._auto_download_queued_check.SetValue(settings.auto_download_queued)
        root.Add(self._auto_download_queued_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._auto_download_inbox_check = wx.CheckBox(
            self.dialog, label="Also download &everything routed to the Inbox"
        )
        self._auto_download_inbox_check.SetName(settings_help.HELP["download_inbox"])
        self._auto_download_inbox_check.SetHelpText(settings_help.HELP["download_inbox"])
        self._auto_download_inbox_check.SetValue(settings.auto_download_inbox)
        root.Add(self._auto_download_inbox_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Which shows the Inbox holds. A radio pair rather than a checkbox,
        # because the two modes are opposites rather than an on/off: reading a
        # ticked box called "opt out" and working out what it means is exactly
        # the kind of puzzle this app avoids.
        root.Add(
            wx.StaticText(self.dialog, label="Which shows go to the &Inbox:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        self._inbox_mode = wx.Choice(
            self.dialog,
            choices=[
                "Only the shows I choose",
                "Every show except the ones I exclude",
            ],
        )
        self._inbox_mode.SetName(settings_help.HELP["inbox_mode"])
        self._inbox_mode.SetHelpText(settings_help.HELP["inbox_mode"])
        self._inbox_mode.SetSelection(1 if settings.inbox_mode == "exclude" else 0)
        root.Add(self._inbox_mode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Every chapters_* switch, in one group. All six were live and none had
        # a control, which is worse than absent: a setting nobody can reach is a
        # bug with a default. Its own module because this dialog is at its
        # GATE-11 ceiling.
        from quill.ui.podcasts.chapter_settings_group import ChapterSettingsGroup

        self._chapters = ChapterSettingsGroup(self.dialog, settings)
        root.Add(self._chapters.sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        session_box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "When an episode finishes")
        self._continue_queue_check = wx.CheckBox(
            self.dialog, label="P&lay the next episode in the Play Queue"
        )
        self._continue_queue_check.SetName(settings_help.HELP["continue_queue"])
        self._continue_queue_check.SetHelpText(settings_help.HELP["continue_queue"])
        self._continue_queue_check.SetValue(settings.continue_after_queue)
        session_box.Add(self._continue_queue_check, 0, wx.ALL, 6)

        self._prebuffer_check = wx.CheckBox(
            self.dialog, label="Start loading the ne&xt episode before this one ends"
        )
        self._prebuffer_check.SetName(settings_help.HELP["prebuffer"])
        self._prebuffer_check.SetHelpText(settings_help.HELP["prebuffer"])
        self._prebuffer_check.SetValue(settings.prebuffer_next)
        session_box.Add(self._prebuffer_check, 0, wx.ALL, 6)
        self._continue_group_check = wx.CheckBox(
            self.dialog, label="When the queue is empty, keep going with the same podcast"
        )
        self._continue_group_check.SetName(settings_help.HELP["continue_group"])
        self._continue_group_check.SetHelpText(settings_help.HELP["continue_group"])
        self._continue_group_check.SetValue(settings.continue_after_group)
        session_box.Add(self._continue_group_check, 0, wx.LEFT | wx.BOTTOM, 6)
        root.Add(session_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._name_first_check = wx.CheckBox(
            self.dialog, label="Read the pod&cast name before the episode title in mixed lists"
        )
        self._name_first_check.SetName(settings_help.HELP["name_first"])
        self._name_first_check.SetHelpText(settings_help.HELP["name_first"])
        self._name_first_check.SetValue(settings.announce_show_name_first)
        root.Add(self._name_first_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._always_sync_check = wx.CheckBox(
            self.dialog,
            label="Always s&ync the full catalog (download every episode the feed offers)",
        )
        self._always_sync_check.SetName(settings_help.HELP["always_sync"])
        self._always_sync_check.SetHelpText(settings_help.HELP["always_sync"])
        self._always_sync_check.SetValue(settings.always_sync_full_catalog)
        self._always_sync_check.Bind(wx.EVT_CHECKBOX, self._on_always_sync_toggle)
        root.Add(self._always_sync_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._auto_trim_check = wx.CheckBox(
            self.dialog, label="Auto-&trim silence from downloaded episodes"
        )
        self._auto_trim_check.SetName(settings_help.HELP["auto_trim"])
        self._auto_trim_check.SetHelpText(settings_help.HELP["auto_trim"])
        self._auto_trim_check.SetValue(settings.auto_trim_silence)
        root.Add(self._auto_trim_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._normalize_check = wx.CheckBox(
            self.dialog, label="Normali&ze loudness of downloaded episodes"
        )
        self._normalize_check.SetName(settings_help.HELP["normalize"])
        self._normalize_check.SetHelpText(settings_help.HELP["normalize"])
        self._normalize_check.SetValue(settings.normalize_loudness)
        root.Add(self._normalize_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        reconnect_box = wx.StaticBoxSizer(
            wx.VERTICAL, self.dialog, "If a download's connection drops"
        )
        self._reconnect_check = wx.CheckBox(
            self.dialog, label="&Reconnect and keep downloading automatically"
        )
        self._reconnect_check.SetName(settings_help.HELP["reconnect"])
        self._reconnect_check.SetHelpText(settings_help.HELP["reconnect"])
        self._reconnect_check.SetValue(settings.reconnect_enabled)
        reconnect_box.Add(self._reconnect_check, 0, wx.ALL, 6)
        reconnect_grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        reconnect_grid.Add(
            wx.StaticText(self.dialog, label="Reconnect attempts:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._reconnect_attempts_ctrl = wx.SpinCtrl(self.dialog, min=1, max=99)
        self._reconnect_attempts_ctrl.SetValue(max(1, settings.reconnect_max_attempts))
        self._reconnect_attempts_ctrl.SetName(settings_help.HELP["reconnect_attempts"])
        self._reconnect_attempts_ctrl.SetHelpText(settings_help.HELP["reconnect_attempts"])
        reconnect_grid.Add(self._reconnect_attempts_ctrl, 0)
        reconnect_grid.Add(
            wx.StaticText(self.dialog, label="Seconds between attempts:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._reconnect_wait_ctrl = wx.SpinCtrl(self.dialog, min=1, max=600)
        self._reconnect_wait_ctrl.SetValue(max(1, settings.reconnect_wait_seconds))
        self._reconnect_wait_ctrl.SetName(settings_help.HELP["reconnect_wait"])
        self._reconnect_wait_ctrl.SetHelpText(settings_help.HELP["reconnect_wait"])
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
            inbox_mode="exclude" if self._inbox_mode.GetSelection() == 1 else "include",
            inbox_max_episodes=self._inbox_max_ctrl.GetValue(),
            **self._chapters.values(),
            history_retention_days=_HISTORY_VALUES[max(0, self._history_choice.GetSelection())],
            download_on_metered=self._metered_check.GetValue(),
            download_notify=self._notify_check.GetValue(),
            volume_boost=volume_boost.from_index(self._boost_choice.GetSelection()),
            stats_streaks_enabled=self._streaks_check.GetValue(),
            download_retention_days=self._retention_days_ctrl.GetValue(),
            storage_cap_mb=self._storage_cap_ctrl.GetValue(),
            delete_after_play=self._delete_played_check.GetValue(),
            playback_cache=self._playback_cache_ctrl.GetValue(),
            playback_cache_cap_mb=self._playback_cache_cap_ctrl.GetValue(),
            continue_after_queue=self._continue_queue_check.GetValue(),
            prebuffer_next=self._prebuffer_check.GetValue(),
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
