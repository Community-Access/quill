"""Turning a set of picks into subscriptions and favorites, in order.

Asked for on 2026-08-25: *"When they do this create it as a folder in their
Favorites as well as in subscriptions"*.

Two stores, one act, and they mean different things:

* **Subscriptions** is the library -- the app fetches these feeds and tracks
  their episodes. This is what "subscribe" means.
* **Favorites** is where a listener keeps what they reach for. A podcast lands
  there as a **place** (``favorites.place_station``) pointing at
  ``mypodcastshow:<feed-url>``, which the browse tree already renders as that
  show's **Episodes** -- so a podcast in Favorites opens into the episode list
  with the same row actions as any other podcast view, rather than being an
  inert name. That was the "expose podcasts richly" requirement, and it needed
  no new browse code: the node kind already existed.

A station has no feed to subscribe to, so it lands in Favorites only.

Pure and wx-free: it takes the stores and mutates them, and the caller saves.
Written this way so the ordering promise -- *the folder is in the order you
arranged it* -- can be tested without a display or a disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id

#: A podcast favorite points at this browse node, which expands to Episodes.
PODCAST_NODE_PREFIX = "mypodcastshow:"


@dataclass(frozen=True, slots=True)
class PickToApply:
    """One thing to add. ``feed_url`` xor ``stream_url`` decides what it is."""

    title: str
    feed_url: str = ""
    stream_url: str = ""
    homepage: str = ""
    description: str = ""
    language: str = ""
    category: str = ""
    #: A browse node id, for a pick that is a place rather than either.
    node_id: str = ""

    @property
    def is_podcast(self) -> bool:
        return bool(self.feed_url)


@dataclass(frozen=True, slots=True)
class ApplyOutcome:
    """What actually happened, in numbers a sentence can be built from."""

    subscribed: int = 0
    favorited: int = 0
    already_subscribed: int = 0
    already_favorited: int = 0

    @property
    def nothing_happened(self) -> bool:
        return not (self.subscribed or self.favorited)


def apply_picks(
    picks: Sequence[PickToApply],
    *,
    library: PodcastLibrary | None,
    favorites: Any | None,
    folder: str,
    stream_source: str = "",
) -> ApplyOutcome:
    """Add *picks* to both stores, in the order given. Never raises.

    ``folder`` names the library folder and the favorites folder path alike, so
    the two read the same when somebody goes looking. Either store may be
    ``None`` -- an app without a podcast library still gets its favorites.

    Order is preserved by construction: both stores append, and the picks
    arrive in the order the picker left them.
    """
    subscribed = favorited = already_subscribed = already_favorited = 0

    for pick in picks:
        if pick.is_podcast and library is not None:
            if library.find_show_by_feed_url(pick.feed_url) is None:
                library.add_show(_show_for(pick, library, folder))
                subscribed += 1
            else:
                already_subscribed += 1
        if favorites is None:
            continue
        if _add_favorite(favorites, pick, folder, stream_source):
            favorited += 1
        else:
            already_favorited += 1

    return ApplyOutcome(
        subscribed=subscribed,
        favorited=favorited,
        already_subscribed=already_subscribed,
        already_favorited=already_favorited,
    )


def _show_for(pick: PickToApply, library: PodcastLibrary, folder: str) -> PodcastShow:
    from quill.core.podcasts.models import PodcastSettings

    show = PodcastShow(
        id=new_id(),
        title=pick.title,
        feed_url=pick.feed_url,
        homepage=pick.homepage,
        description=pick.description,
        language=pick.language,
        category=pick.category,
        folder_id=library.find_or_create_folder_path([folder]),
    )
    # Stream-only, like every bulk subscribe: choosing forty shows must not
    # queue forty downloads somebody never asked for.
    show.settings = PodcastSettings(playback_mode="stream")
    return show


def _add_favorite(favorites: Any, pick: PickToApply, folder: str, stream_source: str) -> bool:
    """Add one favorite. False when it was already there.

    Deliberately tolerant of the store's shape: Quill Radio's
    ``RadioFavoritesStore`` is the only implementation today, and this module
    stays testable with a stand-in rather than dragging the whole radio model
    into a pure test.
    """
    from quill.core.radio.favorites import place_station
    from quill.core.radio.models import RadioStation

    if pick.is_podcast or pick.node_id:
        node = pick.node_id or f"{PODCAST_NODE_PREFIX}{pick.feed_url}"
        station = place_station(node, pick.title, source=stream_source)
    elif pick.stream_url:
        station = RadioStation(
            name=pick.title,
            stream_url=pick.stream_url,
            homepage=pick.homepage,
            source=stream_source,
        )
    else:
        return False
    added = favorites.add(station, folder=folder, custom=True)
    return bool(added)


__all__ = ["PODCAST_NODE_PREFIX", "ApplyOutcome", "PickToApply", "apply_picks"]
