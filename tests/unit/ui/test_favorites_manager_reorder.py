"""Favorites Manager: Move Up/Down (and Mark + Move Above/Below) must work from
the default A-Z view, not only when the folder is already in manual order.

Regression: a listener reported the Move buttons in the Manage Favorites dialog
did nothing. They were disabled unless the folder was already manual, so from
the default Ascending sort they were inert. The dialog now switches to manual on
the first move -- exactly like the main window's Alt+Shift+Up/Down -- WITHOUT
rewriting the stored order (baking the A-Z view would silently destroy a
hand-arranged list, #1186); the reload reveals the preserved order and the move
happens within it.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.radio.favorites_manager_dialog import FavoritesManagerDialog


@pytest.fixture(scope="module")
def _app() -> wx.App:
    return wx.App()


def _store_az_out_of_order() -> RadioFavoritesStore:
    # Stored order is Charlie, Alice, Bravo -- deliberately not alphabetical, so
    # the A-Z display order (Alice, Bravo, Charlie) differs from storage.
    store = RadioFavoritesStore()
    for name in ("Charlie", "Alice", "Bravo"):
        store.add(RadioStation(name=name, stream_url=f"http://{name}.example/stream"))
    return store


def _folder_names_in_store(store: RadioFavoritesStore) -> list[str]:
    return [f.station.name for f in store.favorites]


def test_move_down_from_az_view_switches_to_manual_preserving_order(_app: wx.App) -> None:
    store = _store_az_out_of_order()  # stored: Charlie, Alice, Bravo
    switched: list[bool] = []
    frame = wx.Frame(None)
    try:
        dlg = FavoritesManagerDialog(
            frame,
            favorites=store,
            controller=SimpleNamespace(state=SimpleNamespace(station=None)),
            announce_cb=lambda _m: None,
            on_changed=lambda: None,
            on_switch_to_manual=lambda: switched.append(True),
            sort="az",
            folder_sorts={},
        )

        # Pretend Alice (first in the A-Z view) is selected, and Move Down.
        dlg._selected_favorite = lambda: store.find(  # type: ignore[method-assign]
            next(f.key for f in store.favorites if f.station.name == "Alice")
        )
        dlg._on_move(1)

        # The switch was recorded and the list is now manual, but the STORED
        # order was preserved (not baked to A-Z) -- Alice simply moved one place
        # down within the stored order Charlie, Alice, Bravo.
        assert switched == [True]
        assert dlg._sort == "manual"
        assert _folder_names_in_store(store) == ["Charlie", "Bravo", "Alice"]
    finally:
        frame.Destroy()


def test_move_in_already_manual_folder_does_not_switch(_app: wx.App) -> None:
    store = _store_az_out_of_order()
    switched: list[bool] = []
    frame = wx.Frame(None)
    try:
        dlg = FavoritesManagerDialog(
            frame,
            favorites=store,
            controller=SimpleNamespace(state=SimpleNamespace(station=None)),
            announce_cb=lambda _m: None,
            on_changed=lambda: None,
            on_switch_to_manual=lambda: switched.append(True),
            sort="manual",
            folder_sorts={},
        )
        dlg._selected_favorite = lambda: store.find(  # type: ignore[method-assign]
            next(f.key for f in store.favorites if f.station.name == "Charlie")
        )
        dlg._on_move(1)

        # No switch callback for an already-manual list, and the stored order is
        # untouched except for the one swap (Charlie down past Alice).
        assert switched == []
        assert _folder_names_in_store(store) == ["Alice", "Charlie", "Bravo"]
    finally:
        frame.Destroy()
