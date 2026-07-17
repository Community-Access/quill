"""Move Up/Down announces the neighbor it now sits next to (quill-radio #1).

Both the store's neighbor lookup and the wx-free announcement helper are pure,
so no widgets are constructed.
"""

from __future__ import annotations

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.radio.favorites_manager_dialog import move_announcement


def _store(*names: str, folder: str = "") -> RadioFavoritesStore:
    store = RadioFavoritesStore()
    for name in names:
        store.add(RadioStation(name=name, stream_url=f"https://{name}.example.com"), folder=folder)
    return store


def _key(store: RadioFavoritesStore, name: str) -> str:
    return next(f.key for f in store.favorites if f.station.name == name)


def test_neighbor_in_folder_finds_adjacent_and_stops_at_edges() -> None:
    store = _store("A", "B", "C")
    b = _key(store, "B")
    below = store.neighbor_in_folder(b, 1)
    above = store.neighbor_in_folder(b, -1)
    assert below is not None and below.station.name == "C"
    assert above is not None and above.station.name == "A"
    # Edges return None.
    assert store.neighbor_in_folder(_key(store, "A"), -1) is None
    assert store.neighbor_in_folder(_key(store, "C"), 1) is None


def test_neighbor_lookup_skips_other_folders() -> None:
    store = RadioFavoritesStore()
    store.add(RadioStation(name="A", stream_url="https://a"), folder="Rock")
    store.add(RadioStation(name="X", stream_url="https://x"), folder="Jazz")
    store.add(RadioStation(name="B", stream_url="https://b"), folder="Rock")
    a = _key(store, "A")
    # A's in-folder neighbor below is B, skipping the Jazz entry between them.
    below = store.neighbor_in_folder(a, 1)
    assert below is not None and below.station.name == "B"


def test_move_down_names_the_station_now_below() -> None:
    # Move A down (swaps with B): A is now between B (above) and C (below).
    store = _store("A", "B", "C")
    a = _key(store, "A")
    store.move(a, delta=1)
    assert move_announcement(store, a, 1) == "Moved down, now above C"


def test_move_up_names_the_station_now_above() -> None:
    # Move C up (swaps with B): C is now between A (above) and B (below).
    store = _store("A", "B", "C")
    c = _key(store, "C")
    store.move(c, delta=-1)
    assert move_announcement(store, c, -1) == "Moved up, now below A"


def test_move_down_at_bottom_edge_names_the_neighbor_above() -> None:
    # Move B down to the last position: nothing below it, so name the one above.
    store = _store("A", "B", "C")
    b = _key(store, "B")
    store.move(b, delta=1)  # B and C swap; B is now last
    assert move_announcement(store, b, 1) == "Moved down, now below C"


def test_single_entry_has_no_reference_point() -> None:
    store = _store("Solo")
    solo = _key(store, "Solo")
    assert move_announcement(store, solo, 1) == "Moved down"
