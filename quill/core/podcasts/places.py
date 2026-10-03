"""The Places list: what it holds, in what order, and what each row says (qc.md 4.3).

Pure. The list in the main window is built from :func:`visible`, the counts
from :func:`count`, the names from :func:`label`, and the sentence an empty
place says on arrival from :func:`empty_state` -- so every one of those is
testable without a window, and the window cannot answer any of them
differently from Go To, the View menu or the status bar.

**The list is fully the listener's** (Jeff, 2026-09-30). Order and the hidden
set are one string setting, ``PodcastSettings.places_layout``, stored with the
library so it travels with a synced data folder; names reuse ``view_names``,
the same store the renamed pinned views already used, so a name given to the
Inbox before this list existed is still its name. A place whose *feature* is
off in Customize Features (section 17) is not in the list at all, which is the
difference between hiding a place and not having one.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "KIND_EPISODES",
    "KIND_NOTICES",
    "KIND_PLAYLISTS",
    "KIND_PODCASTS",
    "KIND_TREE",
    "PLACES",
    "Place",
    "PlacesLayout",
    "count",
    "decode",
    "empty_state",
    "encode",
    "hide",
    "label",
    "move",
    "move_sentence",
    "place",
    "reset",
    "show",
    "visible",
]

#: What the content pane shows for a place.
KIND_EPISODES = "episodes"
KIND_PODCASTS = "podcasts"
KIND_TREE = "tree"
KIND_NOTICES = "notices"
KIND_PLAYLISTS = "playlists"


@dataclass(frozen=True, slots=True)
class Place:
    """One row of the Places list, as shipped."""

    id: str
    label: str
    kind: str
    #: The Customize Features area that owns it ("" means always present).
    area: str
    #: The sentence said once on arriving at it empty (qc.md 4.9).
    empty: str


PLACES: tuple[Place, ...] = (
    Place(
        "inbox",
        "Inbox",
        KIND_EPISODES,
        "inbox",
        "The Inbox is empty. Episodes arrive here from podcasts set to send new "
        "episodes to the Inbox, in Settings for This Podcast.",
    ),
    Place(
        "new_episodes",
        "New Episodes",
        KIND_EPISODES,
        "",
        "No unheard episodes. Refresh All Now in the Podcasts menu looks for new ones.",
    ),
    Place(
        "continue_listening",
        "Continue Listening",
        KIND_EPISODES,
        "",
        "Nothing half-heard. Start any episode and stop part way, and it will be here.",
    ),
    Place(
        "favorites",
        "Favorites",
        KIND_PODCASTS,
        "",
        "No favourites yet. Add to Favorites on any podcast.",
    ),
    Place(
        "playlists",
        "Playlists",
        KIND_PLAYLISTS,
        "playlists",
        "No playlists yet. The Applications key here makes one, smart or by hand, "
        "or adds five worth having.",
    ),
    Place(
        "personal_audio",
        "Personal Audio",
        KIND_EPISODES,
        "personal_audio",
        "Add Personal Audio, in the Podcasts menu, imports your own recordings and "
        "audiobooks. The original file stays where it is.",
    ),
    Place(
        "queue",
        "Play Queue",
        KIND_EPISODES,
        "queue",
        "The queue is empty. Space on any episode adds it.",
    ),
    Place(
        "recently_expired",
        "Recently Expired",
        KIND_EPISODES,
        "queue",
        "Nothing has expired from the queue. A podcast with Expire from the queue "
        "set moves what waited too long here, and Restore puts it back.",
    ),
    Place(
        "downloads",
        "Downloads",
        KIND_EPISODES,
        "downloads",
        "Nothing downloaded. Download on any episode keeps it here.",
    ),
    Place(
        "notifications",
        "Notifications",
        KIND_NOTICES,
        "notifications",
        "Nothing to tell you yet. New episodes, finished downloads and feeds that "
        "need attention are listed here as they happen.",
    ),
    Place(
        "podcasts",
        "Podcasts",
        KIND_TREE,
        "",
        "No podcasts yet. Add Podcast in the Podcasts menu, or Import OPML, fills this.",
    ),
)

_BY_ID: dict[str, Place] = {entry.id: entry for entry in PLACES}
DEFAULT_ORDER: tuple[str, ...] = tuple(entry.id for entry in PLACES)
#: Shipped hidden: rarely visited, one key away in View and Go To, and the
#: chooser shows it again (it was a Podcast Manager view until 2026-10-02).
DEFAULT_HIDDEN: frozenset[str] = frozenset({"recently_expired"})


def place(place_id: str) -> Place | None:
    return _BY_ID.get(place_id)


# -- the layout ---------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PlacesLayout:
    """The order, and which rows the listener hid."""

    order: tuple[str, ...] = DEFAULT_ORDER
    hidden: frozenset[str] = DEFAULT_HIDDEN

    @property
    def is_default(self) -> bool:
        return self.order == DEFAULT_ORDER and self.hidden == DEFAULT_HIDDEN


def decode(text: str) -> PlacesLayout:
    """The saved string, tolerant: anything unreadable is the shipped layout,
    an unknown id is dropped, and a place missing from a saved order (a build
    newer than the file) is appended where it ships."""
    try:
        raw = json.loads(text or "")
    except (TypeError, ValueError):
        return PlacesLayout()
    if not isinstance(raw, dict):
        return PlacesLayout()
    order_raw = raw.get("order")
    hidden_raw = raw.get("hidden")
    order: list[str] = []
    if isinstance(order_raw, list):
        order = [str(item) for item in order_raw if str(item) in _BY_ID]
    seen = set(order)
    order.extend(place_id for place_id in DEFAULT_ORDER if place_id not in seen)
    hidden = (
        frozenset(str(item) for item in hidden_raw if str(item) in _BY_ID)
        if isinstance(hidden_raw, list)
        else DEFAULT_HIDDEN
    )
    return PlacesLayout(tuple(order), hidden)


def encode(layout: PlacesLayout) -> str:
    """The string to save; empty for the shipped layout, so the file only
    ever stores a genuine customization."""
    if layout.is_default:
        return ""
    return json.dumps({"order": list(layout.order), "hidden": sorted(layout.hidden)})


def move(layout: PlacesLayout, place_id: str, delta: int) -> PlacesLayout:
    """*place_id* moved by *delta* rows among the places that are shown.

    Hidden rows are skipped over rather than counted, so Alt+Shift+Down moves
    to the row the listener hears next, not to one they cannot see.
    """
    if place_id not in layout.order or delta == 0:
        return layout
    order = list(layout.order)
    shown = [item for item in order if item not in layout.hidden]
    if place_id not in shown:
        return layout
    index = shown.index(place_id)
    target = max(0, min(len(shown) - 1, index + delta))
    if target == index:
        return layout
    shown.pop(index)
    shown.insert(target, place_id)
    # Rebuild the full order: shown rows in their new order, hidden rows kept
    # where they were relative to their neighbours.
    rebuilt: list[str] = []
    shown_iter = iter(shown)
    for item in order:
        rebuilt.append(item if item in layout.hidden else next(shown_iter))
    return PlacesLayout(tuple(rebuilt), layout.hidden)


def move_sentence(layout: PlacesLayout, place_id: str, name: str) -> str:
    """ "Continue Listening moved to first." -- what a move says."""
    shown = [item for item in layout.order if item not in layout.hidden]
    if place_id not in shown:
        return f"{name} is hidden."
    position = shown.index(place_id)
    if position == 0:
        where = "first"
    elif position == len(shown) - 1:
        where = "last"
    else:
        where = _ordinal(position + 1)
    return f"{name} moved to {where}."


def _ordinal(number: int) -> str:
    suffix = "th"
    if number % 100 not in (11, 12, 13):
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def hide(layout: PlacesLayout, place_id: str) -> PlacesLayout:
    if place_id not in _BY_ID:
        return layout
    return PlacesLayout(layout.order, layout.hidden | {place_id})


def show(layout: PlacesLayout, place_id: str) -> PlacesLayout:
    return PlacesLayout(layout.order, layout.hidden - {place_id})


def reset() -> PlacesLayout:
    return PlacesLayout()


def visible(
    layout: PlacesLayout,
    *,
    enabled: Callable[[str], bool] = lambda _area: True,
    include_hidden: bool = False,
) -> list[Place]:
    """The rows the list shows, in order.

    *enabled* answers for a Customize Features area; a place whose area is
    off is absent even from the chooser, because the chooser is for hiding
    what you have, not for discovering what you turned off.
    """
    rows: list[Place] = []
    for place_id in layout.order:
        entry = _BY_ID.get(place_id)
        if entry is None:
            continue
        if entry.area and not enabled(entry.area):
            continue
        if place_id in layout.hidden and not include_hidden:
            continue
        rows.append(entry)
    return rows


# -- names and counts ----------------------------------------------------------- #


def label(library: PodcastLibrary, place_id: str) -> str:
    """The row's name: the listener's own when they gave one, else as shipped."""
    entry = _BY_ID.get(place_id)
    if entry is None:
        return place_id
    custom = str(library.settings.view_names.get(place_id, "") or "").strip()
    return custom or entry.label


def count(library: PodcastLibrary, place_id: str, *, unread_notices: int = 0) -> int:
    """The live count the row carries (qc.md 4.3, the Counts column)."""
    if place_id == "notifications":
        return int(unread_notices)
    if place_id == "podcasts":
        return len(library.shows)
    if place_id == "favorites":
        return sum(1 for show_ in library.shows if show_.is_favorite)
    if place_id == "personal_audio":
        return sum(len(show_.episodes) for show_ in library.shows if show_.is_local)
    if place_id == "queue":
        return len(library.queue)
    if place_id == "playlists":
        return len(library.playlists)
    if place_id == "downloads":
        return sum(1 for show_ in library.shows for ep in show_.episodes if ep.downloaded_path)
    from quill.core.podcasts.virtual_views import virtual_view_pairs

    return len(virtual_view_pairs(library, place_id))


def empty_state(library: PodcastLibrary, place_id: str) -> str:
    """What an empty place says on arrival, once (qc.md 4.9)."""
    entry = _BY_ID.get(place_id)
    if entry is None:
        return ""
    if place_id == "inbox":
        from quill.core.podcasts import inbox_scope

        scoped = inbox_scope.empty_state(library, library.settings.inbox_folder_scope)
        if scoped:
            return scoped
    return entry.empty
