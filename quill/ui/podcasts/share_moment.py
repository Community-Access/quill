"""Share This Moment: the clipboard, and answering a link somebody opened.

Two halves of one feature.

**Sharing** puts a sentence and a link on the clipboard together. The sentence
first, because it is the half that works everywhere -- in an email, in a text
message, read down the phone -- and the person receiving it very often does not
have QUILL Cast at all. The link is the bonus for the person who does.

**Opening** takes a link off the command line, and treats it as what it is:
untrusted input. It resolves to a feed address and a GUID, both of which are
looked up in the library the listener *already subscribes to*. A feed nobody is
subscribed to is refused out loud. QUILL Cast never fetches a URL because a link
asked it to, and never adds a subscription because a link asked it to.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import share_links

__all__ = ["open_share_link", "share_moment"]


def _copy(text: str) -> bool:
    import wx

    if not text or not wx.TheClipboard.Open():
        return False
    try:
        wx.TheClipboard.SetData(wx.TextDataObject(text))
    finally:
        wx.TheClipboard.Close()
    return True


def share_moment(host: Any, show: Any, episode: Any, position_ms: int = 0) -> bool:
    """Copy a shareable sentence and link for this exact moment."""
    announce = getattr(host, "_announce", None) or (lambda _m: None)
    if show is None or episode is None:
        announce("Play or select an episode first.")
        return False
    payload = share_links.build_share(
        str(getattr(show, "title", "") or ""),
        str(getattr(episode, "title", "") or ""),
        str(getattr(show, "feed_url", "") or ""),
        str(getattr(episode, "guid", "") or ""),
        position_ms,
    )
    if not _copy(payload):
        announce("That could not be copied.")
        return False
    where = share_links.spoken_position(position_ms) if position_ms > 0 else ""
    announce(f"Copied. The link opens at {where}." if where else "Copied.")
    return True


def open_share_link(host: Any, text: str) -> bool:
    """Play what a ``quill-cast://`` link points at, if it is really ours.

    Every refusal says why. A link that silently does nothing is worse than one
    that explains itself, and this arrives from outside the app -- somebody
    double-clicked something in a chat window and is waiting to hear it play.
    """
    announce = getattr(host, "_announce", None) or (lambda _m: None)
    target = share_links.parse_link(text)
    if target is None:
        return False

    library = getattr(host, "_podcast_library", None)
    if library is None:
        return False
    show = library.find_show_by_feed_url(target.feed_url)
    if show is None:
        # Deliberately not offering to subscribe: a link should not be able to
        # add a podcast to somebody's library, and an offer here would be a
        # dialog nobody asked for on top of a window that just opened.
        announce(
            "That link is for a podcast you are not subscribed to. "
            "Subscribe to it first, then open the link again."
        )
        return False
    episode = next(
        (row for row in getattr(show, "episodes", []) or [] if row.guid == target.guid), None
    )
    if episode is None:
        announce(
            f"That link is for an episode of {show.title} this computer has not "
            "seen yet. Refresh the podcast and open the link again."
        )
        return False

    if target.position_ms > 0:
        from quill.core.podcasts import position_sync

        position_sync.remember_position(episode, target.position_ms)
    play = getattr(host, "_podcast_play_episode", None) or getattr(host, "_play_episode", None)
    if callable(play):
        play(show, episode)
    announce(
        f"Playing {episode.title} from {show.title}, at "
        f"{share_links.spoken_position(target.position_ms)}."
        if target.position_ms > 0
        else f"Playing {episode.title} from {show.title}."
    )
    return True
