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


# -- folders, from Radio's side -----------------------------------------------
# The same library folders Quill Cast's manager edits, one thin save-included
# operation each, returning what to say. Radio's Subscriptions branch shows
# the tree (browse_libraries._my_podcast_level); these are its verbs.


def create_podcast_folder(data_dir: Path, name: str, *, parent_folder_id: str | None = None) -> str:
    """Add a library folder; returns the sentence to announce."""
    from quill.core.podcasts.subscriptions import load_library, save_library

    cleaned = (name or "").strip()
    if not cleaned:
        return "A folder needs a name. Nothing was created."
    library = load_library(data_dir)
    if parent_folder_id and library.find_folder(parent_folder_id) is None:
        return "That folder no longer exists. Refresh and try again."
    folder = library.add_folder(cleaned, parent_folder_id=parent_folder_id)
    save_library(data_dir, library)
    where = library.find_folder(parent_folder_id) if parent_folder_id else None
    inside = f" inside {where.name}" if where is not None else ""
    return f"Created folder {folder.name}{inside}. It is shared with Quill Cast."


def rename_podcast_folder(data_dir: Path, folder_id: str, name: str) -> str:
    """Rename a library folder; returns the sentence to announce."""
    from quill.core.podcasts.subscriptions import load_library, save_library

    cleaned = (name or "").strip()
    if not cleaned:
        return "A folder needs a name. Nothing was renamed."
    library = load_library(data_dir)
    folder = library.find_folder(folder_id)
    if folder is None:
        return "That folder no longer exists. Refresh and try again."
    old = folder.name
    folder.name = cleaned
    save_library(data_dir, library)
    return f"Renamed {old} to {cleaned}."


def delete_podcast_folder(data_dir: Path, folder_id: str) -> str:
    """Delete a library folder, promoting its contents (never its shows).

    The promote rule is :meth:`PodcastLibrary.delete_folder`'s own -- shows
    and subfolders move up to the deleted folder's parent -- so deleting a
    folder here can never silently unsubscribe anything.
    """
    from quill.core.podcasts.subscriptions import load_library, save_library

    library = load_library(data_dir)
    folder = library.find_folder(folder_id)
    if folder is None:
        return "That folder no longer exists. Refresh and try again."
    name = folder.name
    library.delete_folder(folder_id, contents="promote")
    save_library(data_dir, library)
    return f"Deleted folder {name}. Its podcasts moved up a level; nothing was unsubscribed."


def mark_show_played(data_dir: Path, feed_url: str) -> str:
    """Mark every unplayed episode of a subscribed show as played, and save.

    The same shared state Quill Cast's Mark All as Played edits, so the badge
    clears in both apps at once. Returns the sentence to announce; marking a
    show with nothing unheard says so instead of pretending to work.
    """
    from quill.core.podcasts.subscriptions import load_library, save_library

    library = load_library(data_dir)
    show = library.find_show_by_feed_url((feed_url or "").strip())
    if show is None:
        return "That show is not in your subscriptions."
    unplayed = [episode for episode in show.episodes if not episode.played]
    if not unplayed:
        return f"Every episode of {show.title or show.feed_url} is already marked played."
    for episode in unplayed:
        episode.played = True
    save_library(data_dir, library)
    count = len(unplayed)
    return (
        f"Marked {count} episode{'s' if count != 1 else ''} of "
        f"{show.title or show.feed_url} as played."
    )


def unheard_for_feed(data_dir: Path, feed_url: str) -> int:
    """Unplayed episodes for a followed feed, 0 when unknown (a local read)."""
    try:
        from quill.core.podcasts.sorting import unheard_count
        from quill.core.podcasts.subscriptions import load_library

        show = load_library(data_dir).find_show_by_feed_url((feed_url or "").strip())
        return unheard_count(show) if show is not None else 0
    except Exception:  # noqa: BLE001 - a menu must never fail on a library read
        return 0


def move_show_to_folder(data_dir: Path, feed_url: str, folder_id: str | None) -> str:
    """File a subscribed show into a folder (None = the top level)."""
    from quill.core.podcasts.subscriptions import load_library, save_library

    library = load_library(data_dir)
    show = library.find_show_by_feed_url((feed_url or "").strip())
    if show is None:
        return "That show is not in your subscriptions."
    destination = library.find_folder(folder_id) if folder_id else None
    if folder_id and destination is None:
        return "That folder no longer exists. Refresh and try again."
    show.folder_id = folder_id or None
    save_library(data_dir, library)
    where = destination.name if destination is not None else "the top level"
    return f"Moved {show.title or show.feed_url} to {where}."
