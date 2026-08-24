"""The one window Quill Radio opens itself with, if the listener chose one.

Extracted from ``quill/apps/radio.py`` under GATE-11 (extract, never
rebaseline), and it belongs out here anyway: which window opens is a *policy*
about the app's surfaces, and the app frame's job is only to have the surfaces.

The choice itself, its labels and its migration from the old
"Open Browse Stations at startup" checkbox are pure and live in
:mod:`quill.core.radio.startup_window`. This is the half that knows which
method opens which window.

**One window, or none.** Everything not chosen stays closed. Favorites and
Browse both appearing at launch is the app deciding, on somebody's behalf, that
they want two windows open before they have pressed anything (reported
2026-08-23) -- and the default is still none, because an app that opens a window
you did not ask for is an app you have to close a window to start using.
"""

from __future__ import annotations

from typing import Any

#: Stored id -> the app method that opens that window. Every one of them is the
#: *same* command the menu runs, so a window opened at startup and a window
#: opened by hand can never behave differently.
OPENERS: dict[str, str] = {
    "browse": "open_browse_stations",
    "search": "open_internet_radio",
    "favorites": "open_manage_radio_favorites",
    "recordings": "open_radio_recordings",
    "player": "_radio_go_to_player",
}


def open_startup_window(app: Any) -> str:
    """Open the chosen window. Returns the id opened, or "" for none.

    Never raises: a launch that fails because of a *courtesy* window is a worse
    launch than one that quietly opens nothing, and the listener still has the
    main window and every menu.
    """
    from quill.core.radio import startup_window

    history = getattr(app, "_radio_history", None)
    chosen = startup_window.normalize(getattr(history, "startup_window", ""))
    method = OPENERS.get(chosen)
    if method is None:
        return ""
    opener = getattr(app, method, None)
    if not callable(opener):
        return ""
    try:
        opener()
    except Exception:  # noqa: BLE001 - a courtesy window never breaks a launch
        return ""
    return chosen
