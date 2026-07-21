"""Tests for quill_radio_mac.core.favorites.

Covers FavoriteStation identity/display helpers, RadioFavoritesStore's
add/remove/move/folder operations, search, and the load_favorites/
save_favorites atomic-JSON round trip (including tolerance of a missing
or corrupt file). Pure dataclass and filesystem tests against tmp_path;
no wx, no network.
"""

from __future__ import annotations

from quill_radio_mac.core.favorites import (
    FavoriteStation,
    RadioFavoritesStore,
    load_favorites,
    save_favorites,
)
from quill_radio_mac.core.models import RadioStation


def _station(name="Groove Salad", uuid="uuid-1", url="https://example.com/stream"):
    return RadioStation(name=name, stream_url=url, station_uuid=uuid)


def test_favorite_key_prefers_station_uuid():
    favorite = FavoriteStation(station=_station())
    assert favorite.key == "uuid-1"


def test_favorite_key_falls_back_to_stream_url_when_no_uuid():
    favorite = FavoriteStation(station=_station(uuid=""))
    assert favorite.key == "https://example.com/stream"


def test_favorite_display_label_prefers_custom_name():
    favorite = FavoriteStation(station=_station(name="Groove Salad"), custom_name="My Chill Station")
    assert favorite.display_label == "My Chill Station"


def test_favorite_display_label_falls_back_to_station_display_name():
    favorite = FavoriteStation(station=_station(name="Groove Salad"))
    assert favorite.display_label == favorite.station.display_name


def test_add_skips_duplicate_station():
    store = RadioFavoritesStore()
    station = _station()
    store.add(station)
    store.add(station)
    assert len(store.favorites) == 1


def test_add_and_remove_round_trip():
    store = RadioFavoritesStore()
    station = _station()
    store.add(station, folder="News")
    assert store.contains(station)
    assert store.remove(station.station_uuid) is True
    assert not store.contains(station)
    assert store.remove("missing-key") is False


def test_move_stays_within_same_folder():
    store = RadioFavoritesStore()
    a = _station(name="A", uuid="a")
    b = _station(name="B", uuid="b")
    c = _station(name="C", uuid="c")
    store.add(a, folder="News")
    store.add(b, folder="Music")
    store.add(c, folder="News")
    # b (Music) sits between a and c (both News); moving a down should
    # skip over b and swap with the nearest News-folder neighbor, c.
    assert store.move("a", delta=1) is True
    assert [f.key for f in store.favorites] == ["c", "b", "a"]


def test_move_relative_to_adopts_target_folder():
    store = RadioFavoritesStore()
    a = _station(name="A", uuid="a")
    b = _station(name="B", uuid="b")
    store.add(a, folder="")
    store.add(b, folder="News")
    assert store.move_relative_to("a", "b", before=True) is True
    assert [f.key for f in store.favorites] == ["a", "b"]
    assert store.find("a").folder == "News"


def test_set_folder_and_rename():
    store = RadioFavoritesStore()
    station = _station()
    store.add(station)
    key = station.station_uuid
    assert store.set_folder(key, "News/Morning") is True
    assert store.find(key).folder == "News/Morning"
    assert store.rename(key, "Morning Show") is True
    assert store.find(key).custom_name == "Morning Show"
    assert store.set_folder("missing", "X") is False


def test_set_volume_clamps_to_0_100():
    store = RadioFavoritesStore()
    station = _station()
    store.add(station)
    key = station.station_uuid
    assert store.set_volume(key, 150) is True
    assert store.find(key).volume_percent == 100
    store.set_volume(key, -10)
    assert store.find(key).volume_percent == 0


def test_set_and_clear_enhancement_override():
    store = RadioFavoritesStore()
    station = _station()
    store.add(station)
    key = station.station_uuid
    assert store.set_enhancement(
        key, bass_db=5.0, mid_db=1.0, treble_db=-2.0, compressor_enabled=True
    ) is True
    favorite = store.find(key)
    assert favorite.has_sound_enhancement_override is True
    assert (favorite.eq_bass_db, favorite.eq_mid_db, favorite.eq_treble_db) == (5.0, 1.0, -2.0)
    assert favorite.compressor_enabled is True
    assert store.clear_enhancement_override(key) is True
    assert store.find(key).has_sound_enhancement_override is False
    # Clearing again is a no-op that reports failure, not an exception.
    assert store.clear_enhancement_override(key) is False


def test_folder_names_merges_explicit_and_implied_folders():
    store = RadioFavoritesStore()
    store.add_folder("Sports")
    station = _station()
    store.add(station, folder="News")
    assert store.folder_names() == ["Sports", "News"]


def test_add_folder_rejects_blank_and_duplicate():
    store = RadioFavoritesStore()
    assert store.add_folder("News") is True
    assert store.add_folder("News") is False
    assert store.add_folder("   ") is False


def test_rename_folder_rewrites_descendants():
    store = RadioFavoritesStore()
    store.add_folder("News")
    a = _station(name="A", uuid="a")
    b = _station(name="B", uuid="b")
    store.add(a, folder="News")
    store.add(b, folder="News/Morning")
    count = store.rename_folder("News", "Headlines")
    assert count == 2
    assert store.find("a").folder == "Headlines"
    assert store.find("b").folder == "Headlines/Morning"
    assert "Headlines" in store.folders


def test_delete_folder_moves_stations_to_top_level():
    store = RadioFavoritesStore()
    store.add_folder("News")
    a = _station(name="A", uuid="a")
    b = _station(name="B", uuid="b")
    store.add(a, folder="News")
    store.add(b, folder="News/Morning")
    count = store.delete_folder("News")
    assert count == 2
    assert store.find("a").folder == ""
    assert store.find("b").folder == ""
    assert "News" not in store.folders


def test_search_matches_name_country_tags_and_folder():
    store = RadioFavoritesStore()
    station = RadioStation(
        name="Groove Salad",
        stream_url="https://example.com/gs",
        station_uuid="gs",
        country="United States",
        tags=("ambient", "chill"),
    )
    store.add(station, folder="Chillout")
    assert len(store.search("ambient")) == 1
    assert len(store.search("chillout")) == 1
    assert len(store.search("united states")) == 1
    assert len(store.search("")) == 1
    assert store.search("nonexistent") == []


def test_load_favorites_missing_file_returns_empty_store(tmp_path):
    store = load_favorites(tmp_path)
    assert store.favorites == []
    assert store.folders == []


def test_load_favorites_corrupt_file_returns_empty_store(tmp_path):
    (tmp_path / "radio_favorites.json").write_text("not json", encoding="utf-8")
    store = load_favorites(tmp_path)
    assert store.favorites == []


def test_save_and_load_favorites_round_trip(tmp_path):
    store = RadioFavoritesStore()
    store.add_folder("News")
    station = _station()
    store.add(station, folder="News", custom=True)
    key = station.station_uuid
    store.rename(key, "Morning News")
    store.set_volume(key, 40)
    store.set_enhancement(key, bass_db=3.0, mid_db=0.0, treble_db=-1.0, compressor_enabled=True)

    save_favorites(tmp_path, store)
    reloaded = load_favorites(tmp_path)

    assert reloaded.folders == ["News"]
    assert len(reloaded.favorites) == 1
    favorite = reloaded.favorites[0]
    assert favorite.station == station
    assert favorite.folder == "News"
    assert favorite.custom is True
    assert favorite.custom_name == "Morning News"
    assert favorite.volume_percent == 40
    assert favorite.has_sound_enhancement_override is True
    assert (favorite.eq_bass_db, favorite.eq_mid_db, favorite.eq_treble_db) == (3.0, 0.0, -1.0)
    assert favorite.compressor_enabled is True


def test_load_favorites_clamps_out_of_range_eq_and_volume(tmp_path):
    import json

    path = tmp_path / "radio_favorites.json"
    path.write_text(
        json.dumps(
            {
                "folders": [],
                "favorites": [
                    {
                        "station": _station().to_dict(),
                        "volume_percent": 500,
                        "eq_bass_db": 999.0,
                        "eq_treble_db": -999.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    store = load_favorites(tmp_path)
    favorite = store.favorites[0]
    assert favorite.volume_percent == -1  # out of 0-100 range: falls back to "no preference"
    assert favorite.eq_bass_db == 12.0
    assert favorite.eq_treble_db == -12.0
