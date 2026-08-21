"""A favorites folder as a place you listen from, not just a place things are filed.

Radio has had folders on favorites for a long time and has never had a single
action *on* one. You could file forty stations into "News" and then had to open
the folder and pick one, every time -- which means the folder organised the list
and did nothing for the listening.

Three actions close that, and they are the Radio-shaped subset of what a podcast
folder wants. There is deliberately no folder-settings dialog: a station has far
fewer per-item settings than a podcast, and nothing worth batch-applying.

**A folder means its whole subtree.** Radio's folders are a flat ``/``-separated
path on each favorite (``core/radio/favorites.py``), so "News" and "News/Local"
are two folders that look like one tree. Playing "News" and getting only the
stations filed exactly there, while the six in "News/Local" sat unplayed, would
be the wrong answer to the question that was asked.

**Shuffle is a fixed permutation, not a coin flip per step.** The same rule
``core/radio/play_queue.py`` already follows: a shuffle you can walk backwards
through is a shuffle; one that re-rolls on every Next is a random walk, and it
will play the same station twice before it plays some others once.

wx-free, strict-typed, pure. No playback, no I/O -- the caller owns both.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore

__all__ = [
    "describe_folder",
    "is_in_folder",
    "shuffled",
    "stations_in_folder",
]


def is_in_folder(favorite_folder: str, folder: str) -> bool:
    """Whether a favorite filed in *favorite_folder* belongs to *folder*'s subtree.

    An exact match, or anything below it. ``"News"`` matches ``"News/Local"``
    and does **not** match ``"Newsroom"`` -- the separator has to be there, or a
    folder would capture every sibling whose name it happens to prefix.
    """
    if not folder:
        return True
    here = (favorite_folder or "").strip("/")
    wanted = folder.strip("/")
    return here == wanted or here.startswith(f"{wanted}/")


def stations_in_folder(
    store: RadioFavoritesStore,
    folder: str,
    *,
    include_subfolders: bool = True,
    sort: str = "manual",
) -> list[FavoriteStation]:
    """Every favorite in *folder*, in the order the list shows them.

    The display order rather than the stored order, because the listener asked
    for "this folder" while looking at it, and playing them in a different
    sequence from the one they can see is the sort of small dishonesty that
    makes a feature feel unpredictable.
    """
    rows = store.favorites_in_display_order(sort=sort)
    if include_subfolders:
        return [row for row in rows if is_in_folder(row.folder, folder)]
    wanted = folder.strip("/")
    return [row for row in rows if (row.folder or "").strip("/") == wanted]


def shuffled(
    stations: Sequence[FavoriteStation], *, rng: random.Random | None = None
) -> list[FavoriteStation]:
    """One fixed permutation of *stations*.

    Fixed, so Next and Previous walk the same order in both directions. An
    ``rng`` can be supplied to make a test deterministic; nothing in the app
    passes one.
    """
    rows = list(stations)
    (rng or random).shuffle(rows)
    return rows


def describe_folder(store: RadioFavoritesStore, folder: str) -> str:
    """A folder row as a whole sentence: "News, folder, 6 stations".

    One line, because a screen reader reads a row's own text and a tree that
    makes somebody arrow into a folder to find out whether it is worth opening
    has charged them for the question.
    """
    name = (folder or "").rstrip("/").rsplit("/", 1)[-1] or "Favorites"
    count = len(stations_in_folder(store, folder))
    if count == 1:
        return f"{name}, folder, 1 station"
    return f"{name}, folder, {count} stations"
