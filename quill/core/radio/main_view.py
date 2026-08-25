"""What the main Quill Radio window shows.

**The main window is a frame, not a list** (2026-08-24). It used to be the
favorites tree and nothing else: every other surface -- Browse, Search,
Recordings, the Player -- was a separate window you opened on top of it. So
choosing "open Browse at startup" gave you *two* windows before you had pressed
anything, and the one you actually wanted was the one without the menu bar.

The frame is the part worth keeping in one place: the menu bar, the now-playing
line, Mute and Volume, the status bar, the tray, the transport keys. What sits
between the now-playing line and the volume row is a *choice*, and this module
is that choice.

Everything still opens as its own window on demand -- Ctrl+B is still Browse.
The difference is that the surface you live in is the one with the menu bar on
it, and nothing opens itself at launch.

This replaces :mod:`quill.core.radio.startup_window`'s question. The stored ids
are deliberately the same strings, so somebody who chose "Browse at startup"
comes back to a main window showing Browse rather than to two windows or to a
setting that quietly stopped meaning anything.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

#: The built-in favorites tree: the main window as it has always been, and the
#: default. A listener who never opens Preferences must never notice this
#: module exists.
FAVORITES = "favorites"

#: ``(id, label)`` in the order Preferences and the View submenu list them.
#: The ids are stable and stored; the labels are what the control reads aloud.
#:
#: Deliberately not "None": there is no such thing as a main window showing
#: nothing. The old ``startup_window`` list had a "None" row because it was
#: answering a different question -- which *extra* window opens -- and that
#: question is gone.
MAIN_VIEWS: tuple[tuple[str, str], ...] = (
    (FAVORITES, "Favorite stations"),
    ("browse", "Browse Stations"),
    ("search", "Search Stations"),
    ("recordings", "Radio Recordings"),
    ("player", "Player"),
)

#: What each view is for, one sentence, for the Preferences control's help and
#: for the spoken announcement when the view changes. A picker whose options
#: are five nouns makes somebody try all five to find out what they are.
DESCRIPTIONS: dict[str, str] = {
    FAVORITES: "your own stations and folders, the list Quill Radio has always opened on",
    "browse": (
        "one tree of every source -- Favorites, Popular, ACB Media, reading services and the rest"
    ),
    "search": "the field-based search across every station directory",
    "recordings": "everything you have recorded, with its player and its verbs",
    "player": "the full player: what is on, where you are in it, and the transport",
}


def is_valid(value: object) -> bool:
    """Whether *value* names a view this build can show (pure)."""
    return isinstance(value, str) and value in {view_id for view_id, _label in MAIN_VIEWS}


def normalize(value: object) -> str:
    """A stored setting as a valid id (pure). Anything unknown means favorites.

    A settings file with a typo in it should behave like one with nothing in
    it -- the same rule ``directory_source`` and the browse-source list follow.
    An unreadable value must never leave the main window with no content at
    all, which is the one outcome a listener cannot recover from by keyboard.
    """
    return value if isinstance(value, str) and is_valid(value) else FAVORITES


def label(value: object) -> str:
    """The display label for a stored id."""
    wanted = normalize(value)
    for view_id, text in MAIN_VIEWS:
        if view_id == wanted:
            return text
    return MAIN_VIEWS[0][1]


def description(value: object) -> str:
    """One sentence about what that view is."""
    return DESCRIPTIONS.get(normalize(value), "")


def index_of(value: object) -> int:
    """Which row of :data:`MAIN_VIEWS` a stored id is (pure)."""
    wanted = normalize(value)
    for position, (view_id, _label) in enumerate(MAIN_VIEWS):
        if view_id == wanted:
            return position
    return 0


def from_index(position: object) -> str:
    """The id at *position*, or favorites. Pure, and total for a wx selection."""
    if not isinstance(position, int) or not 0 <= position < len(MAIN_VIEWS):
        return FAVORITES
    return MAIN_VIEWS[position][0]


def migrate_from_startup_window(startup: object) -> str:
    """The old "which window opens at launch" choice, as a main view (pure).

    Somebody who asked for Browse at launch wanted to *be* in Browse, so they
    now open in it -- with the menu bar, and without a second window behind it.
    "None" and the old "Manage Favorites" both land on the favorites tree,
    which is what their main window showed either way.

    An upgrade must not take away a surface somebody chose to open into, and it
    must not silently add one either: those are the only two outcomes here.
    """
    wanted = startup if isinstance(startup, str) else ""
    if wanted in {"", "favorites"}:
        return FAVORITES
    return normalize(wanted)


def announcement(value: object) -> str:
    """What to say when the main window changes what it shows."""
    return f"Main window now shows {label(value)}: {description(value)}."


__all__ = [
    "DESCRIPTIONS",
    "FAVORITES",
    "MAIN_VIEWS",
    "announcement",
    "description",
    "from_index",
    "index_of",
    "is_valid",
    "label",
    "migrate_from_startup_window",
    "normalize",
]
