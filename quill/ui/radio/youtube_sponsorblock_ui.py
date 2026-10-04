"""Skip Sponsor Segments: the settings dialog, and the watcher that skips.

**Video > YouTube > Skip Sponsor Segments...** (Ctrl+Alt+Shift+9) opens a small
dialog: one check box to turn skipping on, and one per kind of segment. Off by
default; what is sent is said in the dialog before it is turned on (see
:mod:`quill.core.radio.youtube_sponsorblock`).

The watcher is one ``wx.Timer`` on the app frame, ticking once a second only
while skipping is on. When a YouTube video starts it fetches that video's
marked segments on the task manager; when playback enters one it seeks past
it and says "Skipped a sponsor segment." -- once per segment, never again if
the listener goes back into it on purpose.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import youtube_sponsorblock as sb

TITLE = "Skip Sponsor Segments"

EXPLAINER = (
    "SponsorBlock is a list, kept by volunteers, of the parts of YouTube videos "
    "that are sponsor reads, self-promotion, intros and the like. With this on, "
    "Quill Radio jumps over the kinds you tick while a video plays, and says "
    "what it skipped. To look a video up it sends SponsorBlock only the first "
    "four characters of a scrambled form of the video's id -- never the video's "
    "address, and nothing about you -- so SponsorBlock cannot tell what you are "
    "watching."
)


class SponsorBlockWatcher:
    """Skips marked segments in the YouTube video that is playing."""

    def __init__(self, app: Any) -> None:
        import wx

        self._app = app
        self._wx = wx
        self.settings = sb.load()
        self._video = ""
        self._skipper = sb.Skipper()
        self._fetching = False
        self._timer = wx.Timer(app.frame)
        app.frame.Bind(wx.EVT_TIMER, lambda _e: self.tick(), self._timer)
        self.apply()

    def apply(self) -> None:
        """Start or stop ticking to match :attr:`settings`."""
        if self.settings.enabled and self.settings.categories:
            if not self._timer.IsRunning():
                self._timer.Start(1000)
        else:
            self._timer.Stop()
            self._video = ""
            self._skipper = sb.Skipper()

    def stop(self) -> None:
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001 - shutting down
            pass

    def _playing_video(self) -> str:
        from quill.core.radio.youtube_urls import youtube_video_id
        from quill.ui.radio.youtube_live_chat_ui import playing_station, video_url

        station = playing_station(self._app)
        url = video_url(station) if station is not None else ""
        return youtube_video_id(url) or "" if url else ""

    def tick(self) -> None:
        controller = getattr(self._app, "_radio_controller", None)
        if controller is None or bool(getattr(self._app, "_safe_mode", False)):
            return
        video = self._playing_video()
        if video != self._video:
            self._video = video
            self._skipper = sb.Skipper()
            if video:
                self._fetch(video)
            return
        if not video or not self._skipper.segments:
            return
        try:
            if not controller.is_seekable():
                return
            position = controller.position_ms() / 1000.0
        except Exception:  # noqa: BLE001 - no position, nothing to skip
            return
        segment = self._skipper.check(position)
        if segment is not None and controller.seek_to(int(segment.end * 1000)):
            self._app._announce(sb.spoken(segment))

    def _fetch(self, video: str) -> None:
        manager = getattr(self._app, "_task_manager", None)
        if manager is None or self._fetching:
            return
        self._fetching = True
        categories = self.settings.categories

        def _work(**_kwargs: object) -> object:
            return sb.fetch_segments(video, categories)

        def _ok(_op: str, found: object) -> None:
            self._fetching = False
            if video == self._video and isinstance(found, list):
                self._skipper = sb.Skipper(found)

        def _bad(_op: str, _error: BaseException) -> None:
            # Quietly: a video with no list is the normal case, and an
            # unreachable list just means nothing is skipped this time.
            self._fetching = False

        manager.submit("radio-sponsorblock", _work, on_success=_ok, on_failure=_bad)


def watcher(app: Any) -> SponsorBlockWatcher:
    """The app's one watcher, made on first use."""
    existing = getattr(app, "_sponsorblock_watcher", None)
    if existing is None:
        existing = SponsorBlockWatcher(app)
        app._sponsorblock_watcher = existing
    return existing


def start_if_on(app: Any) -> None:
    """At menu build: begin watching when the listener left skipping on."""
    if bool(getattr(app, "_safe_mode", False)):
        return
    if sb.load().enabled:
        watcher(app)


def open_settings(app: Any) -> None:
    """The settings dialog; saves and applies on OK."""
    import wx

    if bool(getattr(app, "_safe_mode", False)):
        app._announce("SponsorBlock is not used in Safe Mode.")
        return
    current = sb.load()
    dialog = wx.Dialog(app.frame, title=TITLE)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(dialog, label=EXPLAINER), 0, wx.ALL, 10)
    enabled = wx.CheckBox(dialog, label="&Skip marked segments in YouTube videos")
    enabled.SetValue(current.enabled)
    enabled.SetHelpText(
        "Off by default. When on, Quill Radio jumps over the kinds of segment "
        "ticked below while a YouTube video plays, and says what it skipped."
    )
    sizer.Add(enabled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
    sizer.Add(wx.StaticText(dialog, label="Kinds to skip:"), 0, wx.LEFT, 10)
    letters = "PMRIECTF"
    boxes: list[tuple[str, Any]] = []
    for (category, label), letter in zip(sb.CATEGORIES, letters, strict=True):
        at = label.lower().find(letter.lower())
        marked = label[:at] + "&" + label[at:] if at >= 0 else label
        box = wx.CheckBox(dialog, label=marked)
        box.SetValue(category in current.categories)
        box.SetHelpText(f"Skip {label.lower()} when SponsorBlock has them marked.")
        sizer.Add(box, 0, wx.LEFT | wx.TOP, 6)
        boxes.append((category, box))
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    sizer.Add(buttons, 0, wx.ALL | wx.EXPAND, 10)
    dialog.SetSizerAndFit(sizer)
    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(
        dialog,
        affirmative_id=wx.ID_OK,
        affirmative_label="OK",
        cancel_id=wx.ID_CANCEL,
        cancel_label="Cancel",
    )
    try:
        if app._show_modal_dialog(dialog, TITLE) != wx.ID_OK:
            return
        chosen = sb.SkipSettings(
            enabled=enabled.GetValue(),
            categories=tuple(category for category, box in boxes if box.GetValue()),
        )
    finally:
        dialog.Destroy()
    sb.save(chosen)
    active = watcher(app)
    active.settings = chosen
    active.apply()
    if chosen.enabled and chosen.categories:
        count = len(chosen.categories)
        app._announce(
            f"Skipping {count} kind{'' if count == 1 else 's'} of segment in YouTube videos."
        )
    elif chosen.enabled:
        app._announce("Nothing is ticked, so nothing will be skipped.")
    else:
        app._announce("Not skipping segments.")


__all__ = ["TITLE", "SponsorBlockWatcher", "open_settings", "start_if_on", "watcher"]
