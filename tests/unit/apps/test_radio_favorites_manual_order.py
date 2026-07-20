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
