"""Subscribe to a podcast you found while browsing, from Quill Radio.

Quill Radio grew a whole podcast directory in 3.0 -- Apple's storefronts,
genres and charts, walkable with no account -- and then had nowhere to put a
show you liked. You could play an episode; you could not follow the show. The
answer was always sitting in the shared data store: Quill Cast's library is
JSON in the same profile, so a show followed here is simply *there* the next
time Cast opens, with no export, no import and no second copy.

Two properties this leans on, both already true:

* **The feed is the identity.** Apple is discovery only -- a show resolves to
  the publisher's own RSS address, and everything after that (episodes, audio,
  artwork) comes from the feed. So following a show means storing a feed URL,
  which is exactly what ``PodcastShow`` holds.
* **Following twice is not an error.** A listener who subscribes to a show
  they already have should be told so, not given a duplicate; the library is
  keyed by feed URL for precisely this.

wx-free: resolving and storing only. The window says what happened.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FollowResult:
    """What happened, and what to say about it."""

    #: True when the library gained a show.
    added: bool
    #: The show's title, as stored.
    title: str
    #: True when it was already followed (added is then False).
    already: bool = False

    @property
    def spoken(self) -> str:
        if self.already:
            return (
                f"You already follow {self.title}. "
                "Find it under Podcasts, Subscriptions, and in Quill Cast."
            )
        if self.added:
            return (
                f"Subscribed to {self.title}. "
                "Find it under Podcasts, Subscriptions, and in Quill Cast."
            )
        return "That podcast could not be subscribed to."


def follow_feed(
    data_dir: Path, *, feed_url: str, title: str, homepage: str = "", artwork_url: str = ""
) -> FollowResult:
    """Add *feed_url* to the shared podcast library (idempotent).

    Returns a :class:`FollowResult` rather than raising for the ordinary
    outcomes, because "you already follow this" is an answer, not a failure.
    """
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.subscriptions import load_library, new_id, save_library

    url = (feed_url or "").strip()
    name = (title or "").strip() or url
    if not url:
        return FollowResult(added=False, title=name)

    library = load_library(data_dir)
    existing = library.find_show_by_feed_url(url)
    if existing is not None:
        return FollowResult(added=False, title=existing.title or name, already=True)

    show = PodcastShow(
        id=new_id(),
        title=name,
        feed_url=url,
        homepage=(homepage or "").strip(),
        artwork_url=(artwork_url or "").strip(),
    )
    if not library.add_show(show):
        return FollowResult(added=False, title=name, already=True)
    save_library(data_dir, library)
    return FollowResult(added=True, title=name)


@dataclass(frozen=True, slots=True)
class UnfollowResult:
    """What unsubscribing did, and what to say about it."""

    #: True when the library lost the show.
    removed: bool
    #: The show's title, as it was stored.
    title: str

    @property
    def spoken(self) -> str:
        if self.removed:
            return f"Unsubscribed from {self.title}."
        return "That podcast was not in your subscriptions."


def unfollow_feed(data_dir: Path, feed_url: str) -> UnfollowResult:
    """Drop *feed_url* from the shared podcast library (the Unsubscribe half
    of :func:`follow_feed`; idempotent the same way)."""
    from quill.core.podcasts.subscriptions import load_library, save_library

    url = (feed_url or "").strip()
    if not url:
        return UnfollowResult(removed=False, title="")
    library = load_library(data_dir)
    show = library.find_show_by_feed_url(url)
    if show is None or not library.remove_show(show.id):
        return UnfollowResult(removed=False, title=url)
    save_library(data_dir, library)
    return UnfollowResult(removed=True, title=show.title or url)


def is_followed(data_dir: Path, feed_url: str) -> bool:
    """Whether the shared library already carries this feed."""
    url = (feed_url or "").strip()
    if not url:
        return False
    try:
        from quill.core.podcasts.subscriptions import load_library

        return load_library(data_dir).find_show_by_feed_url(url) is not None
    except Exception:  # noqa: BLE001 - a menu must never fail on a library read
        return False
