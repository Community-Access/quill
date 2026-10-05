"""Search YouTube..., answered inside Browse Stations.

Two doors, one search. **Station > Search YouTube...** (Ctrl+Shift+6, and the
Command Palette) opens Browse Stations and asks; the **Search YouTube...** row
at the top of the YouTube branch asks from where you already are. Either way
the answer lands as the tree's Search Results branch -- the same branch Search
All Sources uses, so Escape in the Find box and Close Search Results both clear
it, and every row is a real browse row: a video plays on Enter, a playlist
opens into its videos, and a channel opens into its uploads, its live
broadcasts and its playlists, with Follow and Subscribe on YouTube on its menu.

The search is three requests -- videos, playlists, channels -- made at once on
a worker thread (:mod:`quill.core.radio.youtube_search`); nothing here touches
the network. The count is said once when the answer arrives, never per row.

Quill (the editor) has no browse tree; there the command opens Search Stations
narrowed to YouTube, which finds videos.
"""

from __future__ import annotations

from typing import Any

TITLE = "Search YouTube"
PROMPT = "What would you like to find on YouTube? Videos, playlists and channels are all searched."


def search_youtube(host: Any) -> None:
    """The menu and palette command: open Browse Stations, then ask."""
    if bool(getattr(host, "_safe_mode", False)):
        host._announce("YouTube is not available in Safe Mode.")
        return
    opener = getattr(host, "open_browse_stations", None)
    if not callable(opener) or getattr(host, "_windows", None) is None:
        search = getattr(host, "open_internet_radio", None)
        if callable(search):
            search(focus_search=True, source_facet="YouTube")
        return
    from quill.ui.radio.youtube_ui import ask_youtube_consent

    if not ask_youtube_consent(host):
        return
    opened = opener()
    dialog = opened or getattr(host, "_radio_browse_dialog", None)
    if dialog is None or not getattr(dialog, "_tree", None):
        host._announce("Browse Stations could not be opened, so YouTube was not searched.")
        return
    host._wx.CallAfter(run_in_tree, dialog)


def run_in_tree(dialog: Any, query: str = "") -> None:
    """Ask for the words (unless given), search off-thread, show the rows."""
    from quill.core.radio import youtube_search
    from quill.ui.radio import browse_feedback, browse_search_all

    if bool(getattr(dialog, "_safe_mode", False)):
        dialog._announce("YouTube is not available in Safe Mode.")
        return
    text = query.strip() or browse_search_all._ask_query(dialog, title=TITLE, prompt=PROMPT)
    if not text:
        return
    dialog._announce(f"Searching YouTube for {text}...")
    browse_feedback.start_search_notice(dialog, "YouTube", text)

    def _work(**_kwargs: Any) -> object:
        return youtube_search.search(text, safe_mode=bool(getattr(dialog, "_safe_mode", False)))

    def _ok(_op: str, found: object) -> None:
        browse_feedback.stop_search_notice(dialog)
        browse_search_all.show_results(dialog, text, found)  # type: ignore[arg-type]

    def _failed(_op: str, error: BaseException) -> None:
        from quill.core.radio.youtube_requests import plain

        browse_feedback.stop_search_notice(dialog)
        reason = plain(error)
        said = f"YouTube could not be searched. {reason}"
        _record_problem(f"Search YouTube for {text}", reason)
        if getattr(dialog, "_tree", None):
            dialog._announce(said)

    dialog._task_manager.submit("radio-youtube-search", _work, on_success=_ok, on_failure=_failed)


def _record_problem(subject: str, reason: str) -> None:
    """Into Recent Problems, like every other Radio failure. Never raises."""
    try:
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(app_data_dir(), problem_log.KIND_OTHER, subject, reason)
    except Exception:  # noqa: BLE001 - a problem list is never worth a crash
        return


__all__ = ["run_in_tree", "search_youtube"]
