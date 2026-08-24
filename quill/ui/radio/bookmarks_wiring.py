"""Quill Radio's half of bookmarks: what is playing, and how to go back (4.3).

The shared window and the shared store know nothing about what Radio plays --
that is the whole point of anchoring by string. What Radio owns is the two
translations:

* **What is playing right now?** A station, a recording, a saved YouTube row,
  or a podcast episode from the Subscriptions branch. Each becomes a different
  anchor, and the *title* is written onto the bookmark rather than resolved
  later -- a shared list has to name a station QUILL Cast has never heard of.
* **How do I go back to one?** A station reconnects and seeks (or does not: a
  live stream has no position to seek to, and saying so is better than
  pretending). A recording opens and seeks. A podcast episode hands off to
  whatever can play it.

**A live station's bookmark is a bookmark on the station, not on the moment.**
Live radio has no timeline anybody else shares -- ten minutes in means ten
minutes into *your* listening, and tomorrow it means something else entirely.
Rather than refuse the verb, the bookmark records the station and says the
elapsed time it was made at, and Go There tunes in now. That is the honest
version of "take me back to that", and pretending to seek would be the
dishonest one.
"""

from __future__ import annotations

from typing import Any

from quill.core import bookmark_anchors, bookmark_ops
from quill.core.media.bookmarks import MediaBookmark


def target_for(host: Any) -> tuple[str, int, str]:
    """``(anchor, position_ms, title)`` for whatever Quill Radio is playing.

    Empty anchor when nothing is, which the shared verb turns into a sentence
    rather than a silent refusal.
    """
    controller = getattr(host, "_radio_controller", None)
    state = getattr(controller, "state", None)
    station = getattr(state, "station", None)
    if controller is None or station is None:
        return ("", 0, "")
    position = 0
    probe = getattr(controller, "position_ms", None)
    if callable(probe):
        try:
            position = max(0, int(probe()))
        except Exception:  # noqa: BLE001 - a position is never worth an exception
            position = 0
    title = str(getattr(station, "name", "") or "")
    url = str(getattr(station, "stream_url", "") or "")
    return (_anchor_for(station, url), position, title)


def _anchor_for(station: Any, url: str) -> str:
    """Which kind of thing this row is, by what it actually points at.

    Read off the row rather than off the player, because the player only knows
    it is playing audio: a recording, a YouTube row and a station all arrive
    at the engine as a URL, and only the row remembers which it was.
    """
    source = str(getattr(station, "source", "") or "").lower()
    if getattr(station, "episode_guid", "") and getattr(station, "show_id", ""):
        return bookmark_anchors.for_episode(station.show_id, station.episode_guid)
    if "recording" in source or url.lower().endswith((".mp3", ".ogg", ".opus", ".m4a", ".flac")):
        return bookmark_anchors.for_recording(url)
    if "youtube" in source or "youtube.com" in url or "youtu.be" in url:
        return bookmark_anchors.for_video(url)
    return bookmark_anchors.for_station(url)


def register(host: Any) -> None:
    """Teach the shared surfaces what Quill Radio plays and what it can open.

    Both halves in one call, and the target is bound onto the instance rather
    than overridden in the frame: the two are one fact about this app, and
    splitting them across two files is how one of them gets forgotten.
    """
    host._bookmark_target = lambda: target_for(host)
    host._register_bookmark_jumps({
        bookmark_anchors.STATION: lambda anchor, mark: _play(host, anchor, mark, seek=False),
        bookmark_anchors.RECORDING: lambda anchor, mark: _play(host, anchor, mark, seek=True),
        bookmark_anchors.VIDEO: lambda anchor, mark: _play(host, anchor, mark, seek=True),
        bookmark_anchors.PODCAST: lambda anchor, mark: _play_episode(host, anchor, mark),
    })


def append_menu_item(host: Any, playback_menu: Any, wx: Any) -> Any:
    """Bookmark This Moment, on Playback rather than beside the list.

    It is a thing you do *while listening*, not a thing you go and find --
    so it sits with the transport, and only the list lives on Help. The id
    ref is pinned by the host, because a garbage-collected one can be
    reissued to a different item and fire the wrong command.
    """
    item_id = wx.NewIdRef()
    playback_menu.Append(item_id, host._menu_label("Bookm&ark This Moment", "app.bookmark_moment"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.bookmark_this_moment(), id=item_id)
    host._keep_menu_ids(item_id)
    return item_id


def _play(host: Any, anchor: str, mark: MediaBookmark, *, seek: bool) -> str:
    """Tune in, and seek when the thing has a timeline to seek in."""
    from quill.core.radio.models import RadioStation

    url = bookmark_anchors.body_of(anchor)
    if not url:
        return "That bookmark has no address to open."
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return "Nothing here can play that."
    station = RadioStation(name=mark.title or url, stream_url=url)
    controller.play_station(station)
    if not seek:
        # Live radio has no shared timeline: ten minutes in meant ten minutes
        # into *that* listening, and today it means something else. Tuning in
        # is the honest version of "take me back"; a seek would be theatre.
        return f"Tuned in to {station.name}. A live station has no saved place to return to."
    if _seek(controller, mark.position_ms):
        return f"Playing {station.name} from {bookmark_ops.spoken_position(mark.position_ms)}."
    return f"Playing {station.name}. It could not be moved to that point."


def _play_episode(host: Any, anchor: str, mark: MediaBookmark) -> str:
    """A podcast bookmark, from Radio's own subscribed-episode side."""
    show_id, guid = bookmark_anchors.episode_parts(anchor)
    if not show_id or not guid:
        return "That bookmark does not name an episode."
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library

    library = load_library(app_data_dir())
    show = library.find_show(show_id)
    episode = show.find_episode(guid) if show is not None else None
    if show is None or episode is None:
        return "That episode is no longer in your subscriptions."
    from quill.core.radio.models import RadioStation

    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return "Nothing here can play that."
    url = str(getattr(episode, "downloaded_path", "") or episode.audio_url)
    controller.play_station(RadioStation(name=str(episode.title), stream_url=url))
    if _seek(controller, mark.position_ms):
        return f"Playing {episode.title} from {bookmark_ops.spoken_position(mark.position_ms)}."
    return f"Playing {episode.title}. It could not be moved to that point."


def _seek(controller: Any, position_ms: int) -> bool:
    """Move to *position_ms*, once the engine is ready to be moved.

    Best-effort and immediate: an engine that is still connecting answers
    False, and the caller says so rather than claiming a jump that did not
    happen. Waiting for the connection would mean holding the UI thread on a
    network, which is the one thing the player never does.
    """
    seek_to = getattr(controller, "seek_to", None)
    if not callable(seek_to) or position_ms <= 0:
        return False
    try:
        return bool(seek_to(int(position_ms)))
    except Exception:  # noqa: BLE001 - a failed seek is reported, never raised
        return False


__all__ = ["append_menu_item", "register", "target_for"]
