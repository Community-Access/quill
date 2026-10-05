"""The YouTube branch's newer rows: channels you found, live tabs, My YouTube.

Kept out of :mod:`quill.core.radio.browse_yours` and
:mod:`quill.core.radio.browse_sources` (GATE-11: both are near their budgets)
and registered with one ``_HANDLERS.update`` line there. Every kind here is a
folder whose children are ordinary rows -- videos you play, playlists and
channels you open -- so the browse tree needs nothing new to show them.

Kinds:

``ytchannel:<url>\\t<handle url>``
    A channel that came from a search or from My YouTube rather than from
    the channels you follow. Opens exactly like a followed one -- Uploads,
    Live, then its playlists -- and its menu offers Follow instead of Stop
    Following.
``ytstreams:<url>\\t<page>``
    A channel's live tab: what is live now first, then past broadcasts. A
    channel that has never streamed answers with nothing rather than an error.
``myyoutube`` and ``myyt*``
    My YouTube, shown only while Use my YouTube sign-in is on in Preferences
    (:mod:`quill.core.radio.youtube_signin`). Home, the newest videos from your
    subscriptions, the channels you subscribe to, Watch Later, Liked videos and
    your own playlists -- each one flat listing, through yt-dlp's own feed
    keywords (``:ytrec``, ``:ytsubs``, ``:ytwatchlater``, ``:ytfav``) and
    YouTube's ``feed/channels`` and ``feed/playlists`` pages.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.browse_nodes import BrowseNode, folder, make_id
from quill.core.radio.youtube_requests import Fetch, YouTubeRequestError, run
from quill.core.radio.youtube_search import (
    CHANNEL,
    PLAYLIST,
    VIDEO,
    parse_results,
    to_node,
)

#: One page of a feed or a live tab.
PAGE_SIZE = 50

#: My YouTube's video feeds: ``key -> (row label, what yt-dlp is asked for)``.
FEEDS: dict[str, tuple[str, str]] = {
    "home": ("Home", ":ytrec"),
    "subs": ("New from Your Subscriptions", ":ytsubs"),
    "watchlater": ("Watch Later", ":ytwatchlater"),
    "liked": ("Liked Videos", ":ytfav"),
}

CHANNELS_PAGE = "https://www.youtube.com/feed/channels"
PLAYLISTS_PAGE = "https://www.youtube.com/feed/playlists"

#: Swapped by tests for a recorded answer. ``None`` means the real request.
FETCH: Fetch | None = None


def _flat(target: str, *, page: int = 1, size: int = PAGE_SIZE) -> dict[str, object]:
    start = max(0, (page - 1) * size)
    return run(
        target,
        {
            "extract_flat": "in_playlist",
            "playliststart": start + 1,
            # One extra row says whether there is another page, without a
            # second request and without claiming a total nobody knows.
            "playlistend": start + size + 1,
        },
        fetch=FETCH,
    )


def _page(args: list[str]) -> int:
    return int(args[1]) if len(args) > 1 and args[1].isdigit() else 1


def _videos(info: dict[str, object], size: int = PAGE_SIZE) -> tuple[list[BrowseNode], bool]:
    found = parse_results(info, VIDEO, cap=size + 1)
    return [to_node(result) for result in found[:size]], len(found) > size


def _signed_in(safe_mode: bool) -> bool:
    from quill.core.radio import youtube_signin

    return youtube_signin.is_on(safe_mode=safe_mode)


# --- channels ------------------------------------------------------------------


def browse_channel(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A found channel: Uploads, Live, then its playlists."""
    from quill.core.radio import youtube_channels as yt

    if not args or not args[0]:
        return []
    url = args[0]
    nodes = [
        folder(make_id("youtubevideos", url, "1"), "Uploads"),
        folder(make_id("ytstreams", url, "1"), "Live", note="live now and past broadcasts"),
    ]
    from quill.core.radio.browse_youtube_extra import shorts_row

    nodes.append(shorts_row(url))
    for title, playlist_url in yt.playlists(url, safe_mode=safe_mode):
        nodes.append(folder(make_id("youtubevideos", playlist_url, "1"), title, note="playlist"))
    return nodes


def browse_streams(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A channel's live tab, live-now rows first. Empty, not broken, if none."""
    from quill.core.radio.youtube_channels import normalize_channel_url

    if not args or not args[0] or safe_mode:
        return []
    base = normalize_channel_url(args[0]) or args[0].rstrip("/")
    page = _page(args)
    try:
        info = _flat(f"{base}/streams", page=page)
    except YouTubeRequestError as error:
        # A channel that has never streamed has no live tab, and YouTube says
        # so as an error. That is an empty folder, not a failure.
        if "not available" in str(error) or "did not answer" in str(error):
            return []
        raise
    rows, more = _videos(info)
    rows.sort(key=lambda node: "live now" not in node.note)
    if more:
        rows.append(folder(make_id("ytstreams", args[0], str(page + 1)), "More..."))
    return rows


# --- My YouTube ----------------------------------------------------------------


def browse_my_youtube(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """My YouTube's own rows. Nothing at all while sign-in is off."""
    if not _signed_in(safe_mode):
        return []
    return [
        folder(make_id("myytfeed", "home", "1"), "Home", note="what YouTube recommends for you"),
        folder("myytsubs", "Subscriptions", note="new videos and your channels"),
        folder(make_id("myytfeed", "watchlater", "1"), "Watch Later"),
        folder(make_id("myytfeed", "liked", "1"), "Liked Videos"),
        folder("myytplaylists", "Your Playlists"),
        _history_row(),
    ]


def _history_row() -> BrowseNode:
    from quill.core.radio.browse_youtube_extra import history_row

    return history_row()


def browse_my_subscriptions(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    if not _signed_in(safe_mode):
        return []
    return [
        folder(make_id("myytfeed", "subs", "1"), "New from Your Subscriptions"),
        folder("myytchannels", "Your Channels", note="every channel you subscribe to"),
    ]


def browse_feed(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """One of My YouTube's video feeds, a page at a time."""
    if not args or args[0] not in FEEDS or not _signed_in(safe_mode):
        return []
    page = _page(args)
    rows, more = _videos(_flat(FEEDS[args[0]][1], page=page))
    if more:
        rows.append(folder(make_id("myytfeed", args[0], str(page + 1)), "More..."))
    return rows


def browse_my_channels(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Every channel the signed-in account subscribes to, as openable rows."""
    if not _signed_in(safe_mode):
        return []
    info = _flat(CHANNELS_PAGE, size=500)
    return [to_node(result) for result in parse_results(info, CHANNEL, cap=500)]


def browse_my_playlists(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The signed-in account's own and saved playlists."""
    if not _signed_in(safe_mode):
        return []
    info = _flat(PLAYLISTS_PAGE, size=200)
    return [to_node(result) for result in parse_results(info, PLAYLIST, cap=200)]


#: Registered into ``browse_sources._HANDLERS``.
HANDLERS: dict[str, Callable[..., list[BrowseNode]]] = {
    "ytchannel": browse_channel,
    "ytstreams": browse_streams,
    "myyoutube": browse_my_youtube,
    "myytsubs": browse_my_subscriptions,
    "myytfeed": browse_feed,
    "myytchannels": browse_my_channels,
    "myytplaylists": browse_my_playlists,
}


__all__ = ["FEEDS", "HANDLERS", "browse_channel", "browse_my_youtube", "browse_streams"]
