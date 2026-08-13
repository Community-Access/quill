"""Settings for This Podcast... -- the per-show overrides (1.1.0).

Most of what 1.1.0 added is only meaningful one podcast at a time. "Keep the
newest three ready" is right for a daily news show and wrong for a weekly
three-hour interview; "expire from the queue after two days" is right for the
news show and would throw away the interview. A single global value for
either would be a value nobody wants, which is why Earshot declined to offer
one and why this dialog exists.

Every control here has a shared default behind it. Leaving a field at
**Use the shared default** stores no override at all, so changing the global
later still reaches this show -- the difference between "I have no opinion"
and "I want exactly this" is preserved rather than flattened the first time
the dialog is opened.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.models import SPEED_MAX, SPEED_MIN, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids

_AUTO_DOWNLOAD_LABELS = (
    "Use the shared default",
    "None -- download by hand",
    "The newest episode",
    "The newest 3",
    "The newest 5",
    "The newest 10",
    "Every episode (full catalog)",
)
_AUTO_DOWNLOAD_VALUES = (None, 0, 1, 3, 5, 10, -1)

_QUEUE_AGE_LABELS = (
    "Never expire",
    "After 1 day",
    "After 2 days",
    "After 3 days",
    "After 1 week",
    "After 2 weeks",
    "After 1 month",
)
_QUEUE_AGE_VALUES = (0, 1, 2, 3, 7, 14, 30)

_INBOX_AGE_LABELS = (
    "No age limit",
    "6 hours",
    "12 hours",
    "1 day",
    "3 days",
    "1 week",
    "2 weeks",
)
_INBOX_AGE_VALUES = (0, 6, 12, 24, 72, 168, 336)


def _index_for(values: tuple, wanted: object, default: int = 0) -> int:
    try:
        return values.index(wanted)
    except ValueError:
        return default


class ShowSettingsDialog:
    """Edits one show's overrides in place; ``show()`` returns whether
    anything changed (so the caller knows to persist and refresh)."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        show: PodcastShow,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._show = show
        self._announce = announce_cb or (lambda _m: None)
        self._changed = False
        settings = library.effective_settings(show)
        has_override = show.settings is not None

        self.dialog = wx.Dialog(
            parent,
            title=f"Settings for {show.title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((560, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                f"These apply to {show.title} only. Anything left at the shared "
                "default keeps following Podcast Settings when you change it there."
            ),
        )
        intro.Wrap(520)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        def add_row(label: str, make_control):
            """Label first, then the control it labels.

            The order is the whole point and the z-order gate enforces it: a
            screen reader associates a label with the control created after it,
            so a control built before its own label reads as unlabelled. Hence
            a factory rather than an already-built control.
            """
            grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            control = make_control()
            grid.Add(control, 1, wx.EXPAND)
            return control

        self._auto_download = add_row(
            "Auto-&download:", lambda: wx.Choice(self.dialog, choices=list(_AUTO_DOWNLOAD_LABELS))
        )
        self._auto_download.SetName(
            "How many of this show's newest episodes to download automatically"
        )
        self._auto_download.SetSelection(
            _index_for(
                _AUTO_DOWNLOAD_VALUES,
                settings.effective_auto_download_count if has_override else None,
            )
        )

        self._auto_queue = add_row(
            "",
            lambda: wx.CheckBox(self.dialog, label="New episodes go straight to the Play &Queue"),
        )
        self._auto_queue.SetName(
            "Auto-Queue: a new episode of this show joins the Play Queue on refresh, "
            "skipping the Inbox"
        )
        self._auto_queue.SetValue(show.auto_queue)

        self._notify = add_row(
            "", lambda: wx.CheckBox(self.dialog, label="&Announce new episodes by name")
        )
        self._notify.SetName(
            "Speak and braille this show's new episode titles when the background "
            "check finds them, and show a tray notification"
        )
        self._notify.SetValue(show.notify_new_episodes)

        self._queue_age = add_row(
            "&Expire from the queue:",
            lambda: wx.Choice(self.dialog, choices=list(_QUEUE_AGE_LABELS)),
        )
        self._queue_age.SetName(
            "Remove this show's episodes from the Play Queue once they have waited "
            "this long; they go to Recently Expired, where they can be restored"
        )
        self._queue_age.SetSelection(_index_for(_QUEUE_AGE_VALUES, settings.queue_age_limit_days))

        self._speed = add_row(
            "Playback &speed:",
            lambda: wx.SpinCtrlDouble(
                self.dialog, min=SPEED_MIN, max=SPEED_MAX, inc=0.1, initial=settings.speed
            ),
        )
        self._speed.SetDigits(1)
        self._speed.SetName(f"Playback speed for this podcast, {SPEED_MIN} to {SPEED_MAX} times")

        self._inbox_max = add_row(
            "&Inbox: keep at most (0 = no limit):",
            lambda: wx.SpinCtrl(self.dialog, min=0, max=999),
        )
        self._inbox_max.SetValue(settings.inbox_max_episodes)
        self._inbox_max.SetName(
            "At most this many of this show's episodes in the Inbox; 0 means no limit. "
            "Trimming never deletes: episodes stay unplayed in the show's own list."
        )

        self._inbox_age = add_row(
            "Inbox: drop episodes &older than:",
            lambda: wx.Choice(self.dialog, choices=list(_INBOX_AGE_LABELS)),
        )
        self._inbox_age.SetName(
            "Drop this show's episodes out of the Inbox once they are older than this"
        )
        self._inbox_age.SetSelection(_index_for(_INBOX_AGE_VALUES, settings.inbox_age_limit_hours))

        self._retention_days = add_row(
            "Delete downloads after (days, 0 = never):",
            lambda: wx.SpinCtrl(self.dialog, min=0, max=3650),
        )
        self._retention_days.SetValue(settings.download_retention_days)
        self._retention_days.SetName(
            "Delete this show's downloaded files once they are this many days old; "
            "0 means never. Queued and part-played episodes are never deleted."
        )

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._route_inbox = wx.CheckBox(self.dialog, label="&Route new episodes to the Inbox")
        self._route_inbox.SetValue(show.route_to_inbox)
        root.Add(self._route_inbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._playback_cache = wx.CheckBox(
            self.dialog, label="&Keep streamed episodes of this podcast ready while they play"
        )
        self._playback_cache.SetValue(settings.playback_cache)
        self._playback_cache.SetName(
            "Save this podcast's streamed audio as it plays, so playback continues "
            "through a dropped connection and chapters can be found in it"
        )
        root.Add(self._playback_cache, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._favorite = wx.CheckBox(self.dialog, label="A &favorite podcast")
        self._favorite.SetValue(show.is_favorite)
        root.Add(self._favorite, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
        clear_btn = wx.Button(self.dialog, label="&Follow the Shared Defaults")
        clear_btn.SetName(
            "Drop every override for this podcast so it follows Podcast Settings again"
        )
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.Add(clear_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_overrides)

    def show(self) -> bool:
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
            show_modal_dialog(
                self.dialog, f"Settings for {self._show.title}", announce=self._announce
            )
            return self._changed
        finally:
            self.dialog.Destroy()

    def _on_clear_overrides(self, _event: object) -> None:
        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        answer = show_message_box(
            f"Drop every per-podcast setting for {self._show.title} and follow the "
            "shared defaults again?",
            "Follow the Shared Defaults",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        self._show.settings = None
        self._changed = True
        self._announce(f"{self._show.title} now follows the shared defaults")
        self.dialog.EndModal(wx.ID_OK)

    def _on_ok(self, _event: object) -> None:
        show = self._show
        library = self._library
        auto_index = max(0, self._auto_download.GetSelection())
        auto_value = _AUTO_DOWNLOAD_VALUES[auto_index]
        updates: dict[str, object] = {
            "queue_age_limit_days": _QUEUE_AGE_VALUES[max(0, self._queue_age.GetSelection())],
            "speed": float(self._speed.GetValue()),
            "inbox_max_episodes": self._inbox_max.GetValue(),
            "inbox_age_limit_hours": _INBOX_AGE_VALUES[max(0, self._inbox_age.GetSelection())],
            "download_retention_days": self._retention_days.GetValue(),
            "playback_cache": self._playback_cache.GetValue(),
        }
        if auto_value is not None:
            # -1 is "the whole catalog", which is what always_sync_full_catalog
            # has always meant; keep the two in step rather than letting a show
            # hold two settings that disagree.
            updates["auto_download_count"] = auto_value
            updates["always_sync_full_catalog"] = auto_value == -1
        library.apply_show_override(show, **updates)
        show.auto_queue = self._auto_queue.GetValue()
        show.notify_new_episodes = self._notify.GetValue()
        show.route_to_inbox = self._route_inbox.GetValue()
        show.is_favorite = self._favorite.GetValue()
        self._changed = True
        self._announce(f"Saved settings for {show.title}")
        self.dialog.EndModal(self._wx.ID_OK)
