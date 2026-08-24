"""Go To: one key for every place in the app, in the order you choose.

**The problem is recall, not reach.** Almost every destination already had a
key -- Browse Ctrl+B, Recordings Ctrl+G, Manage Favorites Ctrl+Shift+M, Player
Ctrl+Shift+G, Song History Ctrl+Shift+H, Downloads Ctrl+Shift+J, Statistics
Ctrl+Shift+Q, Preferences Ctrl+comma. Eight chords is the cost, and it is paid
by the people least able to afford hunting for a key.

The Window menu (Ctrl+Tab, Ctrl+1..9) does not answer it either, for a specific
reason: **it renumbers.** It lists windows that are *open*, in the order they
opened, so Recordings might be 3 today and 5 tomorrow -- and if it is not open,
no number reaches it at all. Position can never become memory.

So: one key opens a short numbered list of *places*, open or not, and **the
numbering does not move**. That stability is the entire value. The moment the
list reorders itself, this is just a slower command palette.

**Ten positions, 1-9 then 0** -- the number row, in the order a hand meets it.
Ten is the ceiling because that is where the number row ends; an eleventh entry
would have no key, and a menu where some rows have a number and others do not is
worse than a shorter menu.

**The list is yours.** Fixed numbering does not mean chosen by us -- a list you
arranged is more memorable than one we arranged, because you put the thing you
use most at 1. A destination added in a later release lands in the *pool*, never
in the menu, so an upgrade can never renumber the entries you have learned. The
pool is the protection; empty slots would not have been.

This is the third store of this shape (``core.quick_actions`` orders actions,
``core.media.list_columns`` orders columns with a hidden set and a repair pass).
It is deliberately the same shape as both.

wx-free, strict-typed.

**The machinery moved.** Everything structural here -- fixed numbering, the
derived pool, repair, the refusals -- is now :mod:`quill.core.go_to_menu`,
shared with QUILL Cast, which had no Go To at all (list.md 5.2). What stays in
this module is what is genuinely Radio's: which places, and in what order. Two
copies of "the pool is what makes the numbering permanent" is exactly how two
apps come to disagree about it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core import go_to_menu
from quill.core.go_to_menu import MAX_ENTRIES, Destination, position_key

_FILE_NAME = "radio-go-to.json"

#: Every place Go To can reach. Order here is the *default* menu order for the
#: first ten; the rest start in the pool. Adding to this tuple is safe by
#: construction -- a new entry appears in the pool for anyone with a saved
#: layout, so nobody's numbering moves.
DESTINATIONS: tuple[Destination, ...] = (
    Destination("favorites", "Favorites", "go_to_favorites"),
    Destination("browse", "Browse Stations", "open_browse_stations", "Ctrl+B"),
    Destination("player", "The Player", "_radio_go_to_player", "Ctrl+Shift+G"),
    Destination("recordings", "Recordings", "open_radio_recordings"),
    Destination("downloads", "Downloads", "_open_download_queue", "Ctrl+Shift+J"),
    Destination(
        "manage_favorites", "Manage Favorites", "open_manage_radio_favorites", "Ctrl+Shift+M"
    ),
    Destination("song_history", "Song History", "radio_song_history", "Ctrl+Shift+H"),
    Destination("statistics", "Listening Statistics", "go_to_statistics", "Ctrl+Shift+Q"),
    Destination("find_stations", "Find Stations", "go_to_find_stations", "Ctrl+F"),
    Destination("preferences", "Preferences", "_open_preferences", "Ctrl+,"),
    # -- the pool: available to add, not in the menu by default ---------------
    Destination("scheduled", "Scheduled Recordings", "go_to_scheduled_recordings"),
    Destination("catalog_status", "Station Catalog Status", "go_to_catalog_status"),
    Destination("audio_health", "Audio Health", "go_to_audio_health"),
    Destination("shortcuts", "Keyboard Shortcuts", "open_keymap_editor", "Ctrl+Alt+K"),
    Destination("whats_playing", "What's Playing", "radio_whats_playing_details", "Ctrl+T"),
)

#: The first ten, which is what a fresh install gets.
DEFAULT_ORDER: tuple[str, ...] = go_to_menu.default_order(DESTINATIONS)


@dataclass
class GoToLayout(go_to_menu.GoToLayout):
    """Radio's layout: the shared shape, with this app's catalogue built in.

    A subclass rather than a parameter so that ``GoToLayout(order=[...])``
    keeps meaning what it has always meant here -- the dialogs construct these
    inline, and a layout that arrived without its catalogue would report every
    destination as unknown and quietly repair itself to the default.
    """

    catalogue: tuple[Destination, ...] = DESTINATIONS


def destination(destination_id: str) -> Destination | None:
    return go_to_menu.lookup(DESTINATIONS, destination_id)


def default_layout() -> GoToLayout:
    return GoToLayout(order=list(DEFAULT_ORDER))


def repair(layout: GoToLayout) -> GoToLayout:
    """Drop ids we no longer know, de-duplicate, and cap at ten."""
    return GoToLayout(order=list(go_to_menu.repair(_shared(layout)).order))


def refusal_for_adding(layout: GoToLayout) -> str:
    """Why another entry cannot be added, or ``""`` when one can."""
    return go_to_menu.refusal_for_adding(_shared(layout))


def refusal_for_removing(layout: GoToLayout, destination_id: str) -> str:
    """Why this entry cannot be removed, or ``""`` when it can."""
    return go_to_menu.refusal_for_removing(_shared(layout), destination_id)


def load_layout(data_dir: Path) -> GoToLayout:
    """Read the saved menu, repaired. A missing or corrupt file is the default."""
    shared = go_to_menu.load_layout(data_dir, file_name=_FILE_NAME, catalogue=DESTINATIONS)
    return GoToLayout(order=list(shared.order))


def save_layout(data_dir: Path, layout: GoToLayout) -> None:
    go_to_menu.save_layout(data_dir, _shared(layout), file_name=_FILE_NAME)


def _shared(layout: go_to_menu.GoToLayout) -> go_to_menu.GoToLayout:
    """This layout as the shared machinery wants it, catalogue attached."""
    return go_to_menu.GoToLayout(order=list(layout.order), catalogue=DESTINATIONS)


__all__ = [
    "DEFAULT_ORDER",
    "DESTINATIONS",
    "MAX_ENTRIES",
    "Destination",
    "GoToLayout",
    "default_layout",
    "destination",
    "load_layout",
    "position_key",
    "refusal_for_adding",
    "refusal_for_removing",
    "repair",
    "save_layout",
]
