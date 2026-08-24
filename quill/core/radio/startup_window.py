"""Which one window Quill Radio opens itself with, if any.

This began as a checkbox -- "Open Browse Stations at startup" -- and a checkbox
was the wrong control for the question. Once the heavy surfaces became real
windows there were six things that *could* open, the answer is "at most one of
them", and a checkbox can only ever answer for one candidate: to open Search
instead you had to know Search existed, find its command, and open it by hand
every launch, while the checkbox went on offering you Browse.

So it is a **choice**, of exactly one window or none, and everything not chosen
stays closed. That last part is the half that was reported: Favorites and Browse
both appearing at launch is the app deciding, on your behalf, that you want two
windows open before you have pressed anything.

"None" is the default and stays the default. An app that opens a window you did
not ask for is an app you have to close a window to start using.

wx-free, strict-typed, pure: the ids are the same keys the window manager
registers under, so the app opens one by looking it up rather than by a branch
per window.
"""

from __future__ import annotations

#: ``(id, label)`` in the order Preferences lists them. The ids are stable and
#: stored; the labels are what the choice control reads aloud.
STARTUP_WINDOWS: tuple[tuple[str, str], ...] = (
    ("", "None -- just the main window"),
    ("browse", "Browse Stations"),
    ("search", "Search Stations"),
    ("favorites", "Manage Favorites"),
    ("recordings", "Radio Recordings"),
    ("player", "Player"),
)

#: Nothing opens. The default, and what an unreadable stored value reads as.
NONE = ""


def is_valid(value: object) -> bool:
    """Whether *value* names a window this build can open (pure)."""
    return isinstance(value, str) and value in {wid for wid, _label in STARTUP_WINDOWS}


def normalize(value: object) -> str:
    """A stored setting as a valid id (pure). Anything unknown means none.

    A settings file with a typo in it should behave like one with nothing in
    it -- the same rule ``directory_source`` and the browse-source list follow.
    """
    return value if isinstance(value, str) and is_valid(value) else NONE


def label(value: object) -> str:
    """The display label for a stored id."""
    wanted = normalize(value)
    for window_id, text in STARTUP_WINDOWS:
        if window_id == wanted:
            return text
    return STARTUP_WINDOWS[0][1]


def index_of(value: object) -> int:
    """Which row of :data:`STARTUP_WINDOWS` a stored id is (pure)."""
    wanted = normalize(value)
    for position, (window_id, _label) in enumerate(STARTUP_WINDOWS):
        if window_id == wanted:
            return position
    return 0


def from_index(position: object) -> str:
    """The id at *position*, or none. Pure, and total for a wx selection."""
    if not isinstance(position, int) or not 0 <= position < len(STARTUP_WINDOWS):
        return NONE
    return STARTUP_WINDOWS[position][0]


def migrate_from_checkbox(open_browse: object) -> str:
    """The old ``open_browse_at_startup`` flag, as a choice (pure).

    Somebody who ticked the box asked for Browse and still gets Browse: an
    upgrade must not quietly take away a window somebody chose to have.
    """
    return "browse" if bool(open_browse) else NONE
