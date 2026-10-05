"""Two more YouTube places in Browse Stations: a channel's Shorts, and your watch history.

Beside :mod:`quill.core.radio.browse_youtube_more` (which owns a found
channel's Uploads, Live and playlists, and My YouTube), registered into
``browse_sources._HANDLERS`` the same way:

* **Shorts** -- a channel's ``/shorts`` tab, a page at a time. Each Short is
  an ordinary playable row.
* **History** under My YouTube -- what the signed-in account watched, newest
  first, through yt-dlp's ``:ythis`` feed. Like the rest of My YouTube it is
  there only while Use my YouTube sign-in is on in Preferences.

wx-free, strict-typed. Network only through
:func:`quill.core.radio.youtube_requests.run` (via the shared flat reader).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio import browse_youtube_more as more
from quill.core.radio.browse_nodes import BrowseNode, folder, make_id
from quill.core.radio.youtube_requests import YouTubeRequestError

HISTORY_FEED = ":ythis"


def shorts_row(channel_url: str) -> BrowseNode:
    """The Shorts folder a channel lists after Uploads and Live (pure)."""
    return folder(make_id("ytshorts", channel_url, "1"), "Shorts", note="short vertical videos")


def history_row() -> BrowseNode:
    """My YouTube's History folder (pure)."""
    return folder(make_id("myythistory", "1"), "History", note="what you watched, newest first")


def browse_shorts(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A channel's Shorts tab. Empty, not broken, for a channel with none."""
    from quill.core.radio.youtube_channels import normalize_channel_url

    if not args or not args[0] or safe_mode:
        return []
    base = normalize_channel_url(args[0]) or args[0].rstrip("/")
    page = more._page(args)
    try:
        info = more._flat(f"{base}/shorts", page=page)
    except YouTubeRequestError as error:
        if "not available" in str(error) or "did not answer" in str(error):
            return []
        raise
    rows, has_more = more._videos(info)
    if has_more:
        rows.append(folder(make_id("ytshorts", args[0], str(page + 1)), "More..."))
    return rows


def browse_history(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The signed-in account's watch history, a page at a time."""
    if not more._signed_in(safe_mode):
        return []
    page = int(args[0]) if args and args[0].isdigit() else 1
    rows, has_more = more._videos(more._flat(HISTORY_FEED, page=page))
    if has_more:
        rows.append(folder(make_id("myythistory", str(page + 1)), "More..."))
    return rows


#: Registered into ``browse_sources._HANDLERS``.
HANDLERS: dict[str, Callable[..., list[BrowseNode]]] = {
    "ytshorts": browse_shorts,
    "myythistory": browse_history,
}


__all__ = ["HANDLERS", "browse_history", "browse_shorts", "history_row", "shorts_row"]
