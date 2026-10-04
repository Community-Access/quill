"""YouTube Video: everything about one video that is not playing it.

Opened from **Video > YouTube > YouTube Video...** (Ctrl+Alt+Shift+8) for what
is playing, or **YouTube Video...** on a video's row. A peer window, like
YouTube Comments:

* what the video is right now -- live, finished, or a premiere with its
  countdown ("Starts in 2 hours 5 minutes");
* its **Description**, whole and read-only;
* the **Moments** the description lists ("The interview, 12:40"): Enter on
  one jumps there when this video is the one playing;
* **Like**, **Dislike** and **Remove Rating**; **Add to Playlist...** and
  **New Playlist...**; **Add a Comment...** -- through the listener's own
  connected account, asking Google's permission the first time;
* **Live Chat...**, **Save Audio...** (the existing download queue), and
  **Remind Me When It Goes Live...** for a premiere (Radio's own reminders).

Keys: Alt plus the underlined letter of each control; Escape, Ctrl+W or
Ctrl+F4 close it and focus goes back where it was.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import youtube_video_info as vi
from quill.ui.surface_lifetime import surface_tasks

TITLE = "YouTube Video"
ABOUT_TITLE = "About This Channel"
#: The buttons that act as the listener's YouTube account (future.youtube_oauth).
ACCOUNT_BUTTONS = frozenset({
    "_like",
    "_dislike",
    "_unrate",
    "_playlist",
    "_new_playlist",
    "_comment",
})


class YouTubeVideoWindow:
    """One video's details and account actions."""

    def __init__(
        self,
        parent: Any,
        *,
        host: Any,
        station: Any,
        page_url: str,
        fetch: Any = None,
        seek_seconds: Callable[[int], bool] | None = None,
        return_focus: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._host = host
        self._announce = host._announce
        # Tied to the frame, so details that arrive after it is gone land nowhere.
        self._task_manager = surface_tasks(
            getattr(host, "_task_manager", None), lambda: getattr(self, "frame", None)
        )
        self._station = station
        self._page_url = page_url
        self._fetch = fetch
        self._seek_seconds = seek_seconds
        self._return_focus = return_focus
        self._info = vi.VideoInfo()
        self._alive = True
        name = str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")
        self._title = name.strip() or "this video"

        self.frame = wx.Frame(parent, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.frame.SetMinSize((560, 480))
        self._panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        self._build()
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)

    def _build(self) -> None:
        wx = self._wx
        panel = self._panel
        root = wx.BoxSizer(wx.VERTICAL)
        self._heading = wx.StaticText(panel, label=self._title)
        root.Add(self._heading, 0, wx.ALL, 8)
        self._state = wx.StaticText(panel, label="Fetching details...")
        root.Add(self._state, 0, wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="&Description:"), 0, wx.LEFT | wx.TOP, 8)
        self._description = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._description.SetName("Description")
        self._description.SetHelpText(
            "What the uploader wrote about this video, whole. Read it with the "
            "arrow keys; it cannot be changed."
        )
        root.Add(self._description, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="&Moments in the description:"), 0, wx.LEFT | wx.TOP, 8)
        self._moments = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._moments.SetName("Moments in the description")
        self._moments.SetHelpText(
            "Every line of the description that gives a time, such as a track "
            "list or a running order. Press Enter on one to jump there, when "
            "this video is the one playing."
        )
        root.Add(self._moments, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._rating = wx.StaticText(panel, label="")
        root.Add(self._rating, 0, wx.ALL, 8)

        grid = wx.WrapSizer(wx.HORIZONTAL)
        specs = (
            ("_like", "&Like", "Likes this video on your YouTube account.", self.like),
            (
                "_dislike",
                "D&islike",
                "Dislikes this video on your YouTube account. "
                "YouTube counts it but no longer shows the number.",
                self.dislike,
            ),
            ("_unrate", "Remove &Rating", "Takes back your like or dislike.", self.unrate),
            (
                "_playlist",
                "Add to &Playlist...",
                "Lists your own YouTube playlists; the one you choose gets this video at its end.",
                self.add_to_playlist,
            ),
            (
                "_new_playlist",
                "&New Playlist...",
                "Makes a new playlist on your YouTube account, private unless you "
                "choose otherwise, and adds this video to it.",
                self.new_playlist,
            ),
            (
                "_comment",
                "Add a &Comment...",
                "Writes a comment on this video and posts it as your YouTube account.",
                self.add_comment,
            ),
            (
                "_chat",
                "Live C&hat...",
                "Opens the live chat, or the chat replay of a finished stream where "
                "YouTube kept one.",
                self.open_chat,
            ),
            (
                "_save",
                "&Save Audio...",
                "Adds this video's audio to the download queue, the same as Download on its row.",
                self.save_audio,
            ),
            (
                "_remind",
                "Remind Me When It &Goes Live...",
                "For a premiere or a scheduled stream: sets one of Quill Radio's own "
                "reminders, so you are told when to come back.",
                self.remind,
            ),
        )
        # The six account actions exist only when future.youtube_oauth is
        # enabled -- locked off in a public build until Google approves the
        # sign-in, whether or not a client is baked into the build.
        from quill.ui.radio.youtube_account_ui import can_sign_in

        if not can_sign_in(self._host):
            specs = tuple(spec for spec in specs if spec[0] not in ACCOUNT_BUTTONS)
        for attr, label, help_text, handler in specs:
            button = wx.Button(panel, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            setattr(self, attr, button)
            grid.Add(button, 0, wx.ALL, 3)
        self._close = wx.Button(panel, wx.ID_CLOSE, label="Close")
        self._close.SetHelpText("Closes this window and goes back to where you were.")
        grid.Add(self._close, 0, wx.ALL, 3)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(root)

        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, self._close, modeless=True)
        self._moments.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.jump_to_selected())
        self._moments.Bind(wx.EVT_KEY_DOWN, self._on_moment_key)
        self._remind.Enable(False)

    # -- loading -------------------------------------------------------------------

    def start(self) -> None:
        if self._task_manager is None:
            return
        url, fetch = self._page_url, self._fetch

        def _work(**_kwargs: Any) -> object:
            return vi.fetch_video(url, fetch=fetch)

        def _ok(_op: str, info: object) -> None:
            if self._alive and isinstance(info, vi.VideoInfo):
                self.receive(info)

        def _bad(_op: str, error: BaseException) -> None:
            if not self._alive:
                return
            from quill.core.radio.youtube_requests import plain
            from quill.ui.radio.youtube_account_ui import record_problem

            reason = plain(error)
            self._state.SetLabel(f"Details could not be fetched. {reason}")
            # announce-punctuation: exempt -- each part is a whole sentence
            self._announce(f"Details could not be fetched. {reason}")
            record_problem(f"Details for {self._title}", reason)

        self._task_manager.submit("radio-youtube-video", _work, on_success=_ok, on_failure=_bad)

    def receive(self, info: vi.VideoInfo) -> None:
        """Show the details, and say once what the reader cannot see."""
        self._info = info
        if info.title:
            self._title = info.title
        heading = self._title + (f", by {info.channel}" if info.channel else "")
        self._heading.SetLabel(heading)
        state = vi.state_sentence(info)
        self._state.SetLabel(state)
        self._description.SetValue(info.description or "The uploader wrote no description.")
        self._moments.Set([f"{m.label}, {m.clock}" for m in info.moments])
        if info.moments:
            self._moments.SetSelection(0)
        self._remind.Enable(info.is_upcoming)
        found = len(info.moments)
        moments = f" {found} moment{'' if found == 1 else 's'} in the description." if found else ""
        # announce-punctuation: exempt -- each part is a whole sentence
        self._announce(f"{state}{moments}")

    # -- moments ---------------------------------------------------------------

    def _on_moment_key(self, event: Any) -> None:
        if event.GetKeyCode() in (self._wx.WXK_RETURN, self._wx.WXK_NUMPAD_ENTER):
            self.jump_to_selected()
            return
        event.Skip()

    def jump_to_selected(self) -> None:
        index = self._moments.GetSelection()
        if not 0 <= index < len(self._info.moments):
            self._announce("Select a moment first.")
            return
        moment = self._info.moments[index]
        if self._seek_seconds is None or not self._seek_seconds(moment.seconds):
            self._announce("Play this video first, then choose a moment to jump to it.")
            return
        self._announce(f"Jumped to {moment.clock}, {moment.label}.")

    # -- account actions -------------------------------------------------------

    def _video_id(self) -> str:
        from quill.core.radio.youtube_urls import youtube_video_id

        return youtube_video_id(self._page_url) or self._info.video_id

    def _rate(self, rating: str, said: str) -> None:
        from quill.core.radio import youtube_account_api as api
        from quill.ui.radio.youtube_account_ui import run_write

        video_id = self._video_id()

        def _done(_r: object) -> None:
            self._rating.SetLabel(said)
            self._announce(said)

        run_write(
            self._host, "Rate a video on YouTube", lambda t: api.rate(t, video_id, rating), _done
        )

    def like(self) -> None:
        from quill.core.radio.youtube_account_api import LIKE

        self._rate(LIKE, "Liked.")

    def dislike(self) -> None:
        from quill.core.radio.youtube_account_api import DISLIKE

        self._rate(DISLIKE, "Disliked.")

    def unrate(self) -> None:
        from quill.core.radio.youtube_account_api import NO_RATING

        self._rate(NO_RATING, "Rating removed.")

    def add_to_playlist(self) -> None:
        from quill.core.radio import youtube_account_api as api
        from quill.ui.radio.youtube_account_ui import run_write

        def _chosen(result: object) -> None:
            playlists = list(result) if isinstance(result, list) else []
            if not playlists:
                self._announce(
                    "You have no playlists on YouTube yet. Use New Playlist to make one."
                )
                return
            choice = self._choose(
                "Add to Playlist", "Add this video to:", [t for _i, t in playlists]
            )
            if choice < 0:
                return
            playlist_id, title = playlists[choice]
            video_id = self._video_id()
            run_write(
                self._host,
                "Add to a YouTube playlist",
                lambda t: api.add_to_playlist(t, playlist_id, video_id),
                lambda _r: self._announce(f"Added to {title}."),
            )

        run_write(self._host, "List your YouTube playlists", api.my_playlists, _chosen)

    def new_playlist(self) -> None:
        from quill.core.radio import youtube_account_api as api
        from quill.ui.radio.youtube_account_ui import ask_text, run_write

        title = ask_text(self._host, "New Playlist", "Name for the new playlist:", multiline=False)
        if not title:
            return
        privacy_index = self._choose(
            "New Playlist", "Who can see it?", [label for _v, label in api.PRIVACY_CHOICES]
        )
        if privacy_index < 0:
            return
        privacy = api.PRIVACY_CHOICES[privacy_index][0]
        video_id = self._video_id()

        def _work(token: str) -> object:
            playlist_id = api.create_playlist(token, title, privacy=privacy)
            if playlist_id and video_id:
                api.add_to_playlist(token, playlist_id, video_id)
            return playlist_id

        run_write(
            self._host,
            "Make a YouTube playlist",
            _work,
            lambda _r: self._announce(f"Made the playlist {title} and added this video."),
        )

    def add_comment(self) -> None:
        from quill.core.radio import youtube_account_api as api
        from quill.ui.radio.youtube_account_ui import ask_text, run_write

        text = ask_text(self._host, "Add a Comment on YouTube", "Your comment:")
        if not text:
            return
        video_id = self._video_id()
        run_write(
            self._host,
            "Comment on YouTube",
            lambda t: api.add_comment(t, video_id, text),
            lambda _r: self._announce("Comment posted."),
        )

    def open_chat(self) -> None:
        from quill.ui.radio import youtube_live_chat_ui

        youtube_live_chat_ui.open_for_station(self._host, self._station)

    def save_audio(self) -> None:
        from quill.ui.radio import download_command

        download_command.download_station(self._host, self._station)

    def remind(self) -> None:
        from quill.ui.radio import row_reminders_wiring

        row_reminders_wiring.set_reminder(self, self._host, self._station)

    def _choose(self, title: str, prompt: str, choices: list[str]) -> int:
        wx = self._wx
        dialog = wx.SingleChoiceDialog(self.frame, prompt, title, choices)
        try:
            shower = getattr(self._host, "_show_modal_dialog", None)
            answer = (
                shower(dialog, title) if callable(shower) else dialog.ShowModal()
            )  # dialog_button_contract: exempt
            return dialog.GetSelection() if answer == wx.ID_OK else -1
        finally:
            dialog.Destroy()

    # -- window ----------------------------------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE or (event.ControlDown() and key in (ord("W"), wx.WXK_F4)):
            self.frame.Close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        self._alive = False
        target = self._return_focus
        event.Skip()
        if target is not None:
            self._wx.CallAfter(_refocus, target)


def _refocus(target: Any) -> None:
    try:
        if target:
            target.SetFocus()
    except Exception:  # noqa: BLE001 - the opener may have closed meanwhile
        return


def _seeker(app: Any, url: str) -> Callable[[int], bool]:
    """Jump the player, but only when this same video is what is playing."""

    def _seek(seconds: int) -> bool:
        from quill.ui.radio.youtube_live_chat_ui import playing_station, video_url

        station = playing_station(app)
        controller = getattr(app, "_radio_controller", None)
        if station is None or video_url(station) != url or controller is None:
            return False
        try:
            return bool(controller.is_seekable() and controller.seek_to(seconds * 1000))
        except Exception:  # noqa: BLE001 - a refusal is said, not raised
            return False

    return _seek


def open_for_playing(app: Any) -> Any:
    from quill.ui.radio.youtube_live_chat_ui import playing_station

    station = playing_station(app)
    if station is None:
        app._announce("Nothing is playing. Play a YouTube video first.")
        return None
    return open_for_station(app, station)


def open_for_station(host: Any, station: Any) -> Any:
    from quill.ui.radio.youtube_account_ui import app_of
    from quill.ui.radio.youtube_live_chat_ui import video_url

    url = video_url(station)
    if not url:
        host._announce("This is only available for YouTube videos.")
        return None
    app = app_of(host)
    if bool(getattr(app, "_safe_mode", False) or getattr(host, "_safe_mode", False)):
        host._announce("YouTube is not available in Safe Mode.")
        return None
    if hasattr(app, "_radio_history") and hasattr(app, "_show_message_box"):
        from quill.ui.radio.youtube_ui import ask_youtube_consent

        if not ask_youtube_consent(app):
            return None
    import wx

    from quill.ui.radio.youtube_comments_ui import _show_as_peer

    window = YouTubeVideoWindow(
        getattr(app, "frame", None) or getattr(host, "_win", None),
        host=app,
        station=station,
        page_url=url,
        seek_seconds=_seeker(app, url),
        return_focus=wx.Window.FindFocus(),
    )
    _show_as_peer(app, window.frame, TITLE, host._announce, menu_label="&Video")
    window.start()
    return window


def show_text(host: Any, heading: str, text: str) -> None:
    """A read-only reader for a block of text (About This Channel)."""
    import wx

    from quill.ui.radio.youtube_account_ui import app_of

    app = app_of(host)
    parent = getattr(host, "_win", None) or getattr(app, "frame", None)
    dialog = wx.Dialog(parent, title=ABOUT_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(dialog, label=f"&{heading}:"), 0, wx.ALL, 8)
    box = wx.TextCtrl(dialog, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
    box.SetName(heading)
    box.SetHelpText(
        "The channel's name, its subscriber count and the description it wrote "
        "about itself. Read it with the arrow keys."
    )
    box.SetMinSize((520, 320))
    sizer.Add(box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    close = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close.SetHelpText("Closes this and goes back to the channel's row.")
    sizer.Add(close, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizerAndFit(sizer)
    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL)
    try:
        shower = getattr(app, "_show_modal_dialog", None)
        if callable(shower):
            shower(dialog, ABOUT_TITLE)
        else:
            dialog.ShowModal()  # dialog_button_contract: exempt
    finally:
        dialog.Destroy()


__all__ = [
    "ABOUT_TITLE",
    "TITLE",
    "YouTubeVideoWindow",
    "open_for_playing",
    "open_for_station",
    "show_text",
]
