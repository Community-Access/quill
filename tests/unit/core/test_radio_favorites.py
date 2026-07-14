"""Tests for the radio favorites store (pure JSON persistence; no network)."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.favorites import RadioFavoritesStore, load_favorites, save_favorites
from quill.core.radio.models import RadioStation

_STATION_A = RadioStation(name="A", stream_url="https://a.example.com", station_uuid="uuid-a")
_STATION_B = RadioStation(name="B", stream_url="https://b.example.com")  # custom, no uuid


def test_load_favorites_missing_file_returns_empty(tmp_path: Path) -> None:
    store = load_favorites(tmp_path)
    assert store.favorites == []


def test_load_favorites_corrupt_file_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "radio_favorites.json").write_text("not json", encoding="utf-8")
    store = load_favorites(tmp_path)
    assert store.favorites == []


def test_add_contains_remove() -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    assert store.contains(_STATION_A)
    assert not store.contains(_STATION_B)
    assert store.remove("uuid-a") is True
    assert not store.contains(_STATION_A)
    assert store.remove("uuid-a") is False


def test_add_is_idempotent() -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    store.add(_STATION_A)
    assert len(store.favorites) == 1


def test_add_custom_station_keys_by_stream_url() -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_B, custom=True)
    assert store.contains(_STATION_B)
    assert store.favorites[0].custom is True
    assert store.favorites[0].key == "https://b.example.com"


def test_move_reorders_within_bounds() -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    store.add(_STATION_B)
    assert store.move("uuid-a", delta=1) is True
    assert [f.station.name for f in store.favorites] == ["B", "A"]
    assert store.move("uuid-a", delta=1) is False  # already at the end
    assert store.move("missing", delta=1) is False


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    store.add(_STATION_B, custom=True, folder="Sleep")
    save_favorites(tmp_path, store)

    reloaded = load_favorites(tmp_path)
    assert len(reloaded.favorites) == 2
    assert reloaded.contains(_STATION_A)
    assert reloaded.find("https://b.example.com").folder == "Sleep"
    assert reloaded.find("https://b.example.com").custom is True
