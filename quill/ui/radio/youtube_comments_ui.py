"""Read Comments...: opening the comments window from a row or from the player.

Two doors. **Video > Read Comments...** (Ctrl+Shift+7) reads the comments of
whatever YouTube video is playing; **Read Comments...** on a YouTube video's
row in Browse Stations (and its search results) reads that video's. Both land
in the same window (:mod:`quill.ui.radio.youtube_comments_window`), a peer
window like Browse Stations: it has its own Close and Window menus, Escape
closes it, and focus goes back to where it was opened from.

A failure is said in one plain sentence and written to Recent Problems, the
way every other Radio failure is.
"""

from __future__ import annotations

from typing import Any


def _app(host: Any) -> Any:
    """The app frame behind *host* (a browse window carries it as download host)."""
    return getattr(host, "_download_host", None) or host


def open_for_playing(app: Any) -> None:
    """Video > Read Comments...: the comments of the video that is playing."""
    controller = getattr(app, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None:
        app._announce("Nothing is playing. Play a YouTube video first, then read its comments.")
        return
    open_for_station(app, station)


def open_for_station(host: Any, station: Any) -> Any:
    """Open the comments window for *station*, if it is a YouTube video."""
    from quill.core.radio.youtube_urls import is_youtube_url, youtube_video_id

    url = str(getattr(station, "stream_url", "") or getattr(station, "homepage", "") or "")
    if not is_youtube_url(url) or not youtube_video_id(url):
        page = str(getattr(station, "homepage", "") or "")
        url = page if is_youtube_url(page) and youtube_video_id(page) else ""
    if not url:
        host._announce("Comments are only available for YouTube videos.")
        return None
    app = _app(host)
    if bool(getattr(app, "_safe_mode", False) or getattr(host, "_safe_mode", False)):
        host._announce("YouTube is not available in Safe Mode.")
        return None
    if hasattr(app, "_radio_history") and hasattr(app, "_show_message_box"):
        from quill.ui.radio.youtube_ui import ask_youtube_consent

        if not ask_youtube_consent(app):
            return None
    wx = getattr(host, "_wx", None) or app._wx
    focus = wx.Window.FindFocus()
    # The app frame, not the Browse window: closing Browse must not take the
    # comments with it -- they are a peer window, not a child of the tree.
    parent = getattr(app, "frame", None) or getattr(host, "_win", None)
    title = str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")

    from quill.ui.radio.youtube_comments_window import TITLE, YouTubeCommentsWindow

    window = YouTubeCommentsWindow(
        parent,
        video_title=title,
        page_url=url,
        task_manager=getattr(host, "_task_manager", None) or app._task_manager,
        announce=host._announce,
        on_failure=lambda reason: _record(title, reason),
        return_focus=focus,
        account_app=app,  # Reply / Add a Comment / Delete (youtube_comments_write)
    )
    _show_as_peer(app, window.frame, TITLE, host._announce)
    window.start()
    return window


def _record(title: str, reason: str) -> None:
    """Into Recent Problems. Never raises."""
    try:
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(
            app_data_dir(),
            problem_log.KIND_OTHER,
            f"Comments on {title or 'a YouTube video'}",
            reason,
        )
    except Exception:  # noqa: BLE001 - a problem list is never worth a crash
        return


def _show_as_peer(
    app: Any, frame: Any, title: str, announce: Any, menu_label: str = "Comme&nts"
) -> None:
    """A peer window when the app has a window manager; plainly shown otherwise."""
    import wx

    windows = getattr(app, "_windows", None)
    if windows is not None:
        menu_bar = wx.MenuBar()
        own = wx.Menu()
        close_id = wx.NewIdRef()
        own.Append(close_id, "&Close\tCtrl+W")
        frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
        menu_bar.Append(own, menu_label)
        windows.install(frame, menu_bar)
        frame.SetMenuBar(menu_bar)
        keep = getattr(app, "_keep_menu_ids", None)
        if callable(keep):
            keep(close_id)
        windows.register(frame, title)

        def _on_close(event: Any) -> None:
            from quill.ui.dialog_contract import announce_surface_exit

            windows.unregister(frame)
            announce_surface_exit(title, announce)
            event.Skip()

        frame.Bind(wx.EVT_CLOSE, _on_close)
    from quill.ui.dialog_contract import show_modeless_surface

    show_modeless_surface(frame, title, announce=announce)


__all__ = ["open_for_playing", "open_for_station"]
