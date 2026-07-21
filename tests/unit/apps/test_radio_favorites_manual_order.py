"""Reordering a favorite from a sorted view must not destroy the manual order.

Regression guard for #1186: a listener's hand-arranged favorites order was
silently overwritten with the alphabetized view the first time they pressed the
reorder key while A-Z sorting was active, and (with no backup) could not be
recovered. ``_force_favorites_manual_order`` must now switch the sort to manual
*without* rewriting the stored list.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import quill.core.paths as paths
from quill.apps.radio import RadioAppFrame
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.history import RadioHistory
from quill.core.radio.models import RadioStation


def _store_with_manual_order(names: list[str]) -> RadioFavoritesStore:
    store = RadioFavoritesStore()
    for name in names:
        store.add(
            RadioStation(
                name=name,
                stream_url=f"https://{name}.example.com",
                station_uuid=f"uuid-{name}",
            )
        )
    return store


def test_force_manual_order_preserves_hand_arranged_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    # Deliberately non-alphabetical hand-arranged order; A-Z would reorder it.
    store = _store_with_manual_order(["Zeta", "Alpha", "Mu"])
    history = RadioHistory()
    history.favorites_sort = "az"  # viewing A-Z (display would be Alpha, Mu, Zeta)

    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame._radio_favorites = store
    frame._radio_history = history

    frame._force_favorites_manual_order()

    # The stored list is the manual order and must be untouched -- only the sort
    # flips. Previously this baked the A-Z view over the stored order (#1186).
    assert [f.station.name for f in store.favorites] == ["Zeta", "Alpha", "Mu"]
    assert history.favorites_sort == "manual"
    assert history.folder_sort_orders == {}


def test_mark_and_move_drops_below_target_in_one_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #1190: mark a station, then Move Marked Below a destination drops it there
    # in one step (no Alt+Shift+Down 30 times) and clears the mark.
    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    store = _store_with_manual_order(["Alpha", "Beta", "Gamma"])
    history = RadioHistory()  # default manual

    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame._radio_favorites = store
    frame._radio_history = history
    frame._marked_favorite_key = store.favorites[0].key  # marked Alpha
    frame._selected_favorite = lambda: store.favorites[2]  # destination Gamma
    frame._announce = lambda *_a, **_k: None
    frame._save_radio_favorites = lambda: None
    frame._reload_favorites_tree = lambda **_k: None

    frame._on_move_marked_favorite(before=False)  # Alpha below Gamma

    assert [f.station.name for f in store.favorites] == ["Beta", "Gamma", "Alpha"]
    assert frame._marked_favorite_key is None  # mark cleared after the move
