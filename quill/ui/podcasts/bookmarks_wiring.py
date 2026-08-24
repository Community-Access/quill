"""QUILL Cast's half of bookmarks: what is playing, and how to go back (4.5).

Cast plays one kind of thing, so this is shorter than Quill Radio's half by
exactly the amount Radio has more kinds. What matters is that the anchor it
builds is **byte-identical** to the one Radio builds for the same episode: that
is the whole of 4.5. Nothing syncs, nothing merges, nothing negotiates -- both
apps write the same key into the same file in the shared data folder, and a
bookmark dropped in one is simply in the other's list.

Cast registers a jump handler only for podcast episodes. A station bookmark
made in Radio still *appears* here -- it is one list -- and its Go There is
dimmed with a reason, which is the honest shape: the row is real, this app
cannot open it, and saying so beats hiding it and leaving somebody to wonder
where their bookmark went.
"""

from __future__ import annotations

from typing import Any

from quill.core import bookmark_anchors, bookmark_ops
from quill.core.media.bookmarks import MediaBookmark


def target_for(host: Any) -> tuple[str, int, str]:
    """``(anchor, position_ms, title)`` for the episode QUILL Cast is playing."""
    controller = getattr(host, "_podcast_controller", None)
    state = getattr(controller, "state", None)
    show_id = str(getattr(state, "show_id", "") or "")
    guid = str(getattr(state, "episode_guid", "") or "")
    anchor = bookmark_anchors.for_episode(show_id, guid)
    if not anchor:
        return ("", 0, "")
    library = getattr(host, "_podcast_library", None)
    show = library.find_show(show_id) if library is not None else None
    episode = show.find_episode(guid) if show is not None else None
    position = 0
    probe = getattr(controller, "position_ms", None)
    if callable(probe):
        try:
            position = max(0, int(probe()))
        except Exception:  # noqa: BLE001 - a position is never worth an exception
            position = 0
    # Both names, because a bookmarks list mixes shows: "Episode 412" alone is
    # a row somebody has to open to identify. The player's own title is the
    # fallback, so a bookmark still gets a name when the library cannot be
    # read -- an unnamed row is the one thing worse than a slightly odd name.
    show_title = str(getattr(show, "title", "") or "")
    episode_title = str(getattr(episode, "title", "") or getattr(state, "title", "") or "")
    title = " -- ".join(part for part in (episode_title, show_title) if part)
    return (anchor, position, title)


def register(host: Any) -> None:
    """Teach the shared surfaces what Cast plays and what it can open."""
    host._bookmark_target = lambda: target_for(host)
    host._register_bookmark_jumps({
        bookmark_anchors.PODCAST: lambda anchor, mark: _play_episode(host, anchor, mark),
    })


def append_menu_item(host: Any, episode_menu: Any, wx: Any) -> Any:
    """Bookmark This Moment, on the Episode menu beside the transport.

    Its companion list lives on Help with the other shared surfaces; this one
    belongs where somebody's hand already is while an episode is playing.
    """
    item_id = wx.NewIdRef()
    episode_menu.Append(item_id, host._menu_label("Bookm&ark This Moment", "app.bookmark_moment"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.bookmark_this_moment(), id=item_id)
    host._keep_menu_ids(item_id)
    return item_id


def _play_episode(host: Any, anchor: str, mark: MediaBookmark) -> str:
    """Open the bookmarked episode and start it at that moment."""
    show_id, guid = bookmark_anchors.episode_parts(anchor)
    if not show_id or not guid:
        return "That bookmark does not name an episode."
    library = getattr(host, "_podcast_library", None)
    show = library.find_show(show_id) if library is not None else None
    episode = show.find_episode(guid) if show is not None else None
    if show is None or episode is None:
        return "That episode is no longer in your subscriptions."
    controller = getattr(host, "_podcast_controller", None)
    if controller is None:
        return "Nothing here can play that."
    from quill.ui.podcasts.show_actions import start_episode_playback

    # Started at the bookmark rather than at the stored resume point: somebody
    # who chose a bookmark chose a place, and resuming somewhere else would be
    # the app overruling the more specific instruction.
    start_episode_playback(
        controller,
        library,
        show,
        episode,
        resume_ms=max(0, int(mark.position_ms)),
        announce=lambda _m: None,
    )
    return f"Playing {episode.title} from {bookmark_ops.spoken_position(mark.position_ms)}."


__all__ = ["append_menu_item", "register", "target_for"]
