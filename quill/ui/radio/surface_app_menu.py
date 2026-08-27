"""The app's own commands, on every window that is not the main one.

WHY THIS EXISTS
---------------
Quill Radio's windows are peers, not dialogs -- Browse Stations, Find Stations,
the player, Recordings all stand on their own. Each was given a *surface* menu
bar carrying two things: its own **&Close**, and the shared **&Window** menu
that makes Ctrl+Tab and Ctrl+1..9 reach every open window. Everything else --
Browse Stations, Search Stations, Add Custom Station, the Favorites Manager,
Preferences -- lived only on the main window's bar.

Reported 2026-08-26, twice: *"alt+s is not bringing up the Station menu"*, and
then *"all top level menu items on the menu bar need rich ways to invoke
them"*. Both are the same gap. Standing in Browse Stations, Alt+S opened
nothing, because the Station menu was somewhere else and there was no way to
find that out from where you were standing.

So a **&Station** menu now rides on every radio surface, carrying the commands
that make sense from anywhere and calling the same host methods the main
window's items call. There is no second implementation of any command here:
this module is a table of *(label, key, method name)* and a loop.

THREE RULES IT KEEPS
--------------------
* **Only what exists.** Each row is included only when the host actually has
  that method, so a surface hosted by something other than the radio app (or a
  future app that has fewer commands) simply gets a shorter menu instead of a
  broken item.
* **Real keys, and the listener's own.** Where a command has a rebindable key
  the label is built with the host's ``_menu_label``, so it shows *what is
  bound* rather than what shipped -- the house rule for every other menu.
* **Nothing that the surface itself already owns.** Ctrl+F focuses the Find box
  inside Browse Stations; putting Search Stations on Ctrl+F here would shadow
  it. Commands whose keys a surface claims are named by that surface in
  ``skip``.

wx is used only through the ``wx`` handed in, exactly like every other module
in this folder.
"""

from __future__ import annotations

from typing import Any

#: ``(label, keymap command id or "", fallback accelerator, host method)``.
#:
#: The order is the main window's Station menu order, minus the items that only
#: make sense with the main window's own selection. A keymap id means the label
#: follows a rebind; the fallback accelerator is used when the host has no
#: ``_menu_label`` (a test double, or an app that does not use the keymap).
COMMANDS: tuple[tuple[str, str, str, str], ...] = (
    ("&Browse Stations...", "radio.browse", "Ctrl+B", "open_browse_stations"),
    ("&Search Stations...", "", "Ctrl+F", "open_internet_radio"),
    ("&Manage Favorites...", "radio.manage_favorites", "", "open_manage_radio_favorites"),
    ("Recordin&gs...", "radio.recordings", "", "open_radio_recordings"),
    ("&Preferences...", "", "Ctrl+,", "_open_preferences"),
)


def _label(host: Any, text: str, command_id: str, fallback: str) -> str:
    """The menu label, following a rebind where the host can tell us about one."""
    if command_id:
        maker = getattr(host, "_menu_label", None)
        if callable(maker):
            try:
                return str(maker(text, command_id))
            except Exception:  # noqa: BLE001 - a label is never worth failing a menu on
                pass
    return f"{text}\t{fallback}" if fallback else text


def host_of(dialog: Any) -> Any:
    """The app shell behind *dialog*, whatever this surface calls it.

    The surfaces grew up separately and each named its reference for the job it
    used it for -- ``_host``, ``_transport_host``, ``_download_host``,
    ``_app_host`` -- and all four are the same object: the app frame that owns
    the commands. Resolving here keeps eight call sites from repeating the
    chain, and keeps the next surface from inventing a fifth name.
    """
    for name in ("_host", "_transport_host", "_download_host", "_app_host"):
        host = getattr(dialog, name, None)
        if host is not None and host is not dialog:
            return host
    return None


def install(
    *,
    win: Any,
    host: Any,
    menu_bar: Any,
    wx: Any,
    skip: tuple[str, ...] = (),
) -> list[Any]:
    """Append a **&Station** menu to *menu_bar*, bound on *win*.

    *host* is the app shell that owns the commands (the surfaces are handed it
    as ``download_host``). *skip* names host methods this surface owns a key
    for already, so a surface never shadows its own keyboard.

    Returns the ids it created, for the caller to keep alive -- wx id refs are
    recycled once nothing holds them, and a recycled id is a menu item that
    fires somebody else's command.
    """
    if host is None or menu_bar is None:
        return []
    menu = wx.Menu()
    ids: list[Any] = []
    for text, command_id, fallback, method_name in COMMANDS:
        if method_name in skip:
            continue
        method = getattr(host, method_name, None)
        if not callable(method):
            continue
        item_id = wx.NewIdRef()
        menu.Append(item_id, _label(host, text, command_id, fallback))
        win.Bind(wx.EVT_MENU, lambda _e, call=method: call(), id=item_id)
        ids.append(item_id)
    if not ids:
        return []
    menu_bar.Append(menu, "&Station")
    return ids
