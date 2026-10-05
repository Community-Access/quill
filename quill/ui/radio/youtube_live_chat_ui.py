"""Live Chat...: opening a YouTube video's chat from the player or a row.

Two doors, like Read Comments: **Video > YouTube > Live Chat...**
(Ctrl+Alt+Shift+7) for the video that is playing, and **Live Chat...** on a
YouTube video's row in Browse Stations. Both open
:class:`quill.ui.radio.youtube_live_chat_window.YouTubeLiveChatWindow` as a
peer window. A finished stream opens its chat replay where YouTube kept one,
released in step with playback when that same video is playing.

The send box appears only when Quill Radio may sign in to YouTube and the
listener has connected an account; the first message sent asks for the extra
permission (:mod:`quill.ui.radio.youtube_account_ui`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.radio.youtube_account_ui import app_of


def video_url(station: Any) -> str:
    """The YouTube watch address behind *station*, or ``""``."""
    from quill.core.radio.youtube_urls import is_youtube_url, youtube_video_id

    for candidate in (
        str(getattr(station, "stream_url", "") or ""),
        str(getattr(station, "homepage", "") or ""),
    ):
        if is_youtube_url(candidate) and youtube_video_id(candidate):
            return f"https://www.youtube.com/watch?v={youtube_video_id(candidate)}"
    return ""


def playing_station(app: Any) -> Any:
    controller = getattr(app, "_radio_controller", None)
    return getattr(getattr(controller, "state", None), "station", None)


def open_for_playing(app: Any) -> Any:
    """Video > YouTube > Live Chat...: the chat of the video that is playing."""
    station = playing_station(app)
    if station is None:
        app._announce("Nothing is playing. Play a YouTube live stream first, then open its chat.")
        return None
    return open_for_station(app, station)


def _playback_seconds(app: Any, url: str) -> Callable[[], float | None]:
    """Where the same video is in playback, for replay pacing; else ``None``."""

    def _where() -> float | None:
        station = playing_station(app)
        if station is None or video_url(station) != url:
            return None
        controller = getattr(app, "_radio_controller", None)
        try:
            if not controller.is_seekable():
                return None
            return float(controller.position_ms()) / 1000.0
        except Exception:  # noqa: BLE001 - no position means show everything
            return None

    return _where


def _held_back() -> bool:
    try:
        from quill.core.quiet_hours import Kind
        from quill.ui.quiet_hours_ui import held_back

        return held_back(Kind.BACKGROUND)
    except Exception:  # noqa: BLE001 - unknown quiet hours never silence a chat
        return False


def _sender(
    host: Any, url: str
) -> Callable[[str, Callable[[], None], Callable[[str], None]], object]:
    """Send one chat message through the official API, finding the chat once."""
    from quill.core.radio.youtube_urls import youtube_video_id

    video_id = youtube_video_id(url)
    found: dict[str, str] = {}

    def _send(text: str, sent: Callable[[], None], failed: Callable[[str], None]) -> object:
        from quill.core.radio import youtube_account_api as api
        from quill.core.radio.youtube_oauth import YouTubeOAuthError
        from quill.ui.radio.youtube_account_ui import run_write

        def _work(token: str) -> object:
            chat_id = found.get("id") or api.live_chat_id(token, video_id)
            if not chat_id:
                raise YouTubeOAuthError(
                    "This video's chat is not open for messages: it is not live, "
                    "or its chat has ended."
                )
            found["id"] = chat_id
            return api.send_chat_message(token, chat_id, text)

        return run_write(
            host, "Send a live chat message", _work, lambda _r: sent(), on_failed=failed
        )

    return _send


def open_for_station(host: Any, station: Any) -> Any:
    """Open the Live Chat window for *station*, if it is a YouTube video."""
    url = video_url(station)
    if not url:
        host._announce("Live chat is only available for YouTube videos.")
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

    from quill.core.radio import youtube_oauth
    from quill.ui.radio.youtube_account_ui import can_sign_in, record_problem
    from quill.ui.radio.youtube_comments_ui import _show_as_peer
    from quill.ui.radio.youtube_live_chat_window import TITLE, YouTubeLiveChatWindow

    focus = wx.Window.FindFocus()
    parent = getattr(app, "frame", None) or getattr(host, "_win", None)
    title = str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")
    can_send = can_sign_in(host) and youtube_oauth.is_signed_in()
    window = YouTubeLiveChatWindow(
        parent,
        video_title=title,
        page_url=url,
        announce=host._announce,
        held_back=_held_back,
        can_send=can_send,
        send=_sender(host, url) if can_send else None,
        playback_seconds=_playback_seconds(app, url),
        on_failure=lambda reason: record_problem(f"Live chat for {title or 'a video'}", reason),
        return_focus=focus,
    )
    _show_as_peer(app, window.frame, TITLE, host._announce, menu_label="&Chat")
    window.start()
    return window


__all__ = ["open_for_playing", "open_for_station", "video_url"]
