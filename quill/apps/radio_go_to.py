"""Go To (Ctrl+G): the command, and the few places that needed a door.

The list, its ten positions and its repair rules are pure and live in
:mod:`quill.core.radio.go_to`. The popup is in
:mod:`quill.ui.radio.go_to_dialog`. This is the thin middle: load the layout,
show the list, and open whatever was chosen.

**Raise, do not open twice.** Every destination that has a window of its own is
opened through the app's existing handler, which already raises an open window
rather than stacking a second -- so Go To inherits that rather than inventing a
second answer to it.

A few destinations had no single method to call, only a menu item with a lambda.
They get one here rather than in ``radio.py``, which is at its GATE-11 ceiling.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import go_to


def open_go_to(app: Any) -> None:
    """Ctrl+G. Never raises: a way of getting around must not be a way to crash."""
    try:
        from quill.core.paths import app_data_dir
        from quill.ui.radio import go_to_dialog

        data_dir = app_data_dir()
        layout = go_to.load_layout(data_dir)
        chosen = go_to_dialog.open_popup(app, layout)
        if chosen == "__settings__":
            from quill.ui.radio import go_to_settings_dialog

            go_to_settings_dialog.edit(app, layout, data_dir)
            return
        if chosen:
            _open_destination(app, chosen)
    except Exception:  # noqa: BLE001 - navigation must never take the window down
        announce = getattr(app, "_announce", None)
        if callable(announce):
            announce("Go To could not open.")


def _open_destination(app: Any, destination_id: str) -> None:
    destination = go_to.destination(destination_id)
    if destination is None:
        return
    handler = getattr(app, destination.opens, None)
    if callable(handler):
        handler()
        return
    # Destinations that had no method of their own get one here rather than in
    # radio.py, which is at its GATE-11 ceiling.
    shim = globals().get(destination.opens)
    if callable(shim):
        shim(app)
        return
    # A destination whose door has been renamed says so, rather than doing
    # nothing: a menu entry that silently no-ops is indistinguishable from a
    # broken app.
    announce = getattr(app, "_announce", None)
    if callable(announce):
        announce(f"{destination.title} is not available in this build.")


# -- the doors that did not exist as methods -----------------------------------


def go_to_favorites(app: Any) -> None:
    """Back to the main window, focus on the list itself.

    Not merely raising the frame: somebody who asked for Favorites wants to be
    *in* the tree, not standing next to it.
    """
    frame = getattr(app, "frame", None)
    if frame is None:
        return
    frame.Show()
    frame.Iconize(False)
    frame.Raise()
    tree = getattr(app, "_favorites_tree", None)
    if tree is not None:
        tree.SetFocus()


def go_to_statistics(app: Any) -> None:
    from quill.ui.radio.stats_dialog import open_for_host

    open_for_host(app)


def go_to_find_stations(app: Any) -> None:
    """Browse, landing in its search box rather than on the tree."""
    opener = getattr(app, "open_internet_radio", None)
    if callable(opener):
        opener(focus_search=True)


def go_to_scheduled_recordings(app: Any) -> None:
    opener = getattr(app, "_radio_open_schedule_recording", None)
    if callable(opener):
        opener()


def go_to_catalog_status(app: Any) -> None:
    opener = getattr(app, "radio_catalog_status", None)
    if callable(opener):
        opener()


def go_to_audio_health(app: Any) -> None:
    opener = getattr(app, "radio_audio_health", None)
    if callable(opener):
        opener()
