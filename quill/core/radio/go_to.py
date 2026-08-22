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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "radio-go-to.json"

#: Ten, because 1-9 then 0 is where the number row ends.
MAX_ENTRIES = 10


@dataclass(frozen=True, slots=True)
class Destination:
    """One place, and the host method that opens it.

    *key* is the destination's own direct shortcut where it still has one, shown
    on its row so the popup teaches: somebody who uses Go To 2 for a month
    learns Ctrl+B by reading it every time, and graduates off the popup.
    """

    id: str
    title: str
    opens: str
    key: str = ""


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

_BY_ID: dict[str, Destination] = {d.id: d for d in DESTINATIONS}

#: The first ten, which is what a fresh install gets.
DEFAULT_ORDER: tuple[str, ...] = tuple(d.id for d in DESTINATIONS[:MAX_ENTRIES])


def position_key(index: int) -> str:
    """The key that jumps to *index*: ``"1"``-``"9"`` then ``"0"``.

    0 sits where a tenth key would be, because that is where a hand goes last.
    """
    if index < 0 or index >= MAX_ENTRIES:
        return ""
    return "0" if index == MAX_ENTRIES - 1 else str(index + 1)


def destination(destination_id: str) -> Destination | None:
    return _BY_ID.get(destination_id)


@dataclass(slots=True)
class GoToLayout:
    """What is in the menu, in order. Everything known and not listed is pooled."""

    order: list[str] = field(default_factory=lambda: list(DEFAULT_ORDER))

    def ordered(self) -> list[Destination]:
        """The menu, as destinations, in position order."""
        return [_BY_ID[i] for i in self.order if i in _BY_ID]

    def available_ids(self) -> list[str]:
        """Everything not in the menu, in catalogue order.

        Derived rather than stored: a destination added in a later release is
        *automatically* pooled, with no migration and no chance of it being
        inserted into somebody's numbering.
        """
        chosen = set(self.order)
        return [d.id for d in DESTINATIONS if d.id not in chosen]

    def available(self) -> list[Destination]:
        return [_BY_ID[i] for i in self.available_ids()]


def default_layout() -> GoToLayout:
    return GoToLayout(order=list(DEFAULT_ORDER))


def repair(layout: GoToLayout) -> GoToLayout:
    """Drop ids we no longer know, de-duplicate, and cap at ten.

    An unknown id is dropped rather than raising: a layout saved by a newer
    build, or one naming a destination since removed, must degrade to a working
    menu rather than to no app.
    """
    seen: set[str] = set()
    order: list[str] = []
    for destination_id in layout.order:
        if destination_id in _BY_ID and destination_id not in seen:
            seen.add(destination_id)
            order.append(destination_id)
        if len(order) == MAX_ENTRIES:
            break
    if not order:
        order = list(DEFAULT_ORDER)
    return GoToLayout(order=order)


def refusal_for_adding(layout: GoToLayout) -> str:
    """Why another entry cannot be added, or ``""`` when one can.

    A sentence rather than a disabled button: a control that says only "no" is a
    control that has to be guessed at.
    """
    if len(layout.order) < MAX_ENTRIES:
        return ""
    return (
        "The Go To menu is full: it holds ten places, numbered 1 to 9 and then "
        "0, and the number row has no eleventh key. Remove one to make room."
    )


def refusal_for_removing(layout: GoToLayout, destination_id: str) -> str:
    """Why this entry cannot be removed, or ``""`` when it can."""
    if destination_id not in layout.order:
        return ""
    if len(layout.order) > 1:
        return ""
    return "The Go To menu cannot be empty. Add another place first, then remove this one."


def load_layout(data_dir: Path) -> GoToLayout:
    """Read the saved menu, repaired. A missing or corrupt file is the default."""
    raw = read_json(data_dir / _FILE_NAME, {})
    order: list[str] = []
    if isinstance(raw, dict):
        entries = raw.get("order")
        if isinstance(entries, list):
            order = [str(entry) for entry in entries if isinstance(entry, str)]
    if not order:
        return default_layout()
    return repair(GoToLayout(order=order))


def save_layout(data_dir: Path, layout: GoToLayout) -> None:
    write_json_atomic(data_dir / _FILE_NAME, {"order": list(repair(layout).order)})
