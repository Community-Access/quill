"""Tests for the radio favorites store (pure JSON persistence; no network)."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.favorites import RadioFavoritesStore, load_favorites, save_favorites
from quill.core.radio.models import RadioStation

_STATION_A = RadioStation(name="A", stream_url="https://a.example.com", station_uuid="uuid-a")
_STATION_B = RadioStation(name="B", stream_url="https://b.example.com")  # custom, no uuid


def test_per_station_channel_mode_is_stored_and_round_trips(tmp_path: Path) -> None:
    # A station can be routed to one ear as part of its own Sound Enhancements
    # override, and that choice is remembered across save/load.
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    assert store.set_enhancement(
        _STATION_A.station_uuid,
        bass_db=0.0,
        mid_db=0.0,
        treble_db=0.0,
        compressor_enabled=False,
        channel_mode="left",
    )
    fav = store.find(_STATION_A.station_uuid)
    assert fav is not None and fav.has_sound_enhancement_override and fav.channel_mode == "left"

    save_favorites(tmp_path, store)
    reloaded = load_favorites(tmp_path).find(_STATION_A.station_uuid)
    assert reloaded is not None and reloaded.channel_mode == "left"


def test_per_station_channel_mode_defaults_to_stereo(tmp_path: Path) -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    save_favorites(tmp_path, store)
    assert load_favorites(tmp_path).find(_STATION_A.station_uuid).channel_mode == "stereo"


def test_per_station_night_mode_and_optilab_round_trip(tmp_path: Path) -> None:
    # Every Sound Enhancements setting is per-stream: night mode and OptiLab
    # broadcast polish are stored on the station's override and survive a
    # save/load, just like the EQ and channel mode.
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    assert store.set_enhancement(
        _STATION_A.station_uuid,
        bass_db=0.0,
        mid_db=0.0,
        treble_db=0.0,
        compressor_enabled=False,
        channel_mode="stereo",
        night_mode_enabled=True,
        optilab_enabled=True,
        optilab_mode="podcast",
        optilab_input_db=3.0,
        optilab_auto_adapt=40,
    )
    save_favorites(tmp_path, store)
    fav = load_favorites(tmp_path).find(_STATION_A.station_uuid)
    assert fav is not None
    assert fav.night_mode_enabled is True
    assert fav.optilab_enabled is True
    assert fav.optilab_mode == "podcast"
    assert fav.optilab_input_db == 3.0
    assert fav.optilab_auto_adapt == 40


def test_per_station_night_mode_and_optilab_default_off(tmp_path: Path) -> None:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    save_favorites(tmp_path, store)
    fav = load_favorites(tmp_path).find(_STATION_A.station_uuid)
    assert fav.night_mode_enabled is False
    assert fav.optilab_enabled is False
    assert fav.optilab_mode == "off"
    assert fav.optilab_input_db == 0.0
    assert fav.optilab_auto_adapt == 0


def test_favorites_in_display_order_az_za_manual_non_mutating() -> None:
    store = RadioFavoritesStore()
    store.add(RadioStation(name="Charlie", stream_url="https://c"))
    store.add(RadioStation(name="alpha", stream_url="https://a"))
    store.add(RadioStation(name="Bravo", stream_url="https://b"))

    def labels(order: str) -> list[str]:
        return [f.display_label for f in store.favorites_in_display_order(order)]

    assert labels("az") == ["alpha", "Bravo", "Charlie"]  # case-insensitive
    assert labels("za") == ["Charlie", "Bravo", "alpha"]
    assert labels("manual") == ["Charlie", "alpha", "Bravo"]  # insertion order
    # The stored list is never mutated, so "manual" always restores hand order.
    assert [f.display_label for f in store.favorites] == ["Charlie", "alpha", "Bravo"]


def test_per_folder_sort_override_beats_the_global() -> None:
    store = RadioFavoritesStore()
    store.add(RadioStation(name="Zoo", stream_url="https://z"), folder="News")
    store.add(RadioStation(name="Ant", stream_url="https://a"), folder="News")
    ordered = store.favorites_in_display_order("za", {"News": "az"})
    news = [f.display_label for f in ordered if f.folder == "News"]
    assert news == ["Ant", "Zoo"]  # az inside News despite the global za


def test_folders_in_display_order_sorts_case_insensitively() -> None:
    store = RadioFavoritesStore()
    store.add(RadioStation(name="s1", stream_url="https://1"), folder="Zeta")
    store.add(RadioStation(name="s2", stream_url="https://2"), folder="alpha")
    assert store.folders_in_display_order("az") == ["alpha", "Zeta"]
    assert store.folders_in_display_order("za") == ["Zeta", "alpha"]
    assert store.folders_in_display_order("manual") == ["Zeta", "alpha"]  # insertion order


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


_STATION_C = RadioStation(
    name="C jazz",
    stream_url="https://c.example.com",
    station_uuid="uuid-c",
    country="Canada",
    tags=("jazz",),
)


def _store_abc() -> RadioFavoritesStore:
    store = RadioFavoritesStore()
    store.add(_STATION_A)
    store.add(_STATION_B, custom=True)
    store.add(_STATION_C)
    return store


def test_move_swaps_within_the_same_folder_only() -> None:
    store = _store_abc()
    store.set_folder("uuid-a", "News")
    store.set_folder("uuid-c", "News")
    # B sits between A and C but is unfoldered; A moves down past it to C.
    assert store.move("uuid-a", delta=1) is True
    assert [f.key for f in store.favorites] == [
        "uuid-c",
        "https://b.example.com",
        "uuid-a",
    ]
    # The lone unfoldered favorite has no same-folder partner below.
    assert store.move("https://b.example.com", delta=1) is False


def test_move_relative_to_adopts_target_folder() -> None:
    store = _store_abc()
    store.set_folder("uuid-c", "Music")
    assert store.move_relative_to("uuid-a", "uuid-c", before=False) is True
    moved = store.find("uuid-a")
    assert moved is not None and moved.folder == "Music"
    keys = [f.key for f in store.favorites]
    assert keys.index("uuid-a") == keys.index("uuid-c") + 1


def test_move_relative_to_missing_target_restores_order() -> None:
    store = _store_abc()
    before = [f.key for f in store.favorites]
    assert store.move_relative_to("uuid-a", "no-such-key", before=True) is False
    assert [f.key for f in store.favorites] == before


def test_folder_lifecycle_rename_and_delete() -> None:
    store = _store_abc()
    store.set_folder("uuid-a", "News")
    store.set_folder("uuid-c", "News")
    assert store.folder_names() == ["News"]
    assert store.rename_folder("News", "World News") == 2
    assert store.folder_names() == ["World News"]
    # Deleting a folder never deletes its stations.
    assert store.delete_folder("World News") == 2
    assert store.folder_names() == []
    assert len(store.favorites) == 3


def test_search_matches_name_country_tags_and_folder() -> None:
    store = _store_abc()
    store.set_folder("uuid-a", "Morning Shows")
    assert [f.key for f in store.search("jazz")] == ["uuid-c"]
    assert [f.key for f in store.search("canada")] == ["uuid-c"]
    assert [f.key for f in store.search("morning")] == ["uuid-a"]
    assert len(store.search("")) == 3


def test_folder_round_trips_through_save_and_load(tmp_path: Path) -> None:
    store = _store_abc()
    store.set_folder("uuid-a", "News")
    save_favorites(tmp_path, store)
    loaded = load_favorites(tmp_path)
    reloaded = loaded.find("uuid-a")
    assert reloaded is not None and reloaded.folder == "News"
    assert [f.key for f in loaded.favorites] == [f.key for f in store.favorites]


def test_nested_folder_rename_carries_descendants() -> None:
    store = _store_abc()
    store.set_folder("uuid-a", "News/Morning")
    store.set_folder("uuid-c", "News")
    assert store.rename_folder("News", "World") == 2
    a = store.find("uuid-a")
    c = store.find("uuid-c")
    assert a is not None and a.folder == "World/Morning"
    assert c is not None and c.folder == "World"


def test_nested_folder_delete_moves_all_descendants_to_top_level() -> None:
    store = _store_abc()
    store.set_folder("uuid-a", "News/Morning/Early")
    store.set_folder("uuid-c", "News")
    assert store.delete_folder("News") == 2
    assert store.folder_names() == []
    assert len(store.favorites) == 3


def test_rename_and_display_label() -> None:
    store = _store_abc()
    assert store.rename("uuid-a", "My Morning Mix") is True
    favorite = store.find("uuid-a")
    assert favorite is not None
    assert favorite.display_label == "My Morning Mix"
    assert store.rename("uuid-a", "") is True
    assert favorite.display_label == favorite.station.display_name
    # Custom names are searchable.
    store.rename("uuid-a", "Sunrise Sounds")
    assert [f.key for f in store.search("sunrise")] == ["uuid-a"]


def test_per_station_volume_clamps_and_round_trips(tmp_path: Path) -> None:
    store = _store_abc()
    assert store.set_volume("uuid-a", 140) is True
    favorite = store.find("uuid-a")
    assert favorite is not None and favorite.volume_percent == 100
    store.set_volume("uuid-a", 35)
    store.rename("uuid-a", "Named")
    save_favorites(tmp_path, store)
    loaded = load_favorites(tmp_path).find("uuid-a")
    assert loaded is not None
    assert loaded.volume_percent == 35
    assert loaded.custom_name == "Named"
    # Legacy entries without the new keys read as defaults.
    bare = load_favorites(tmp_path).find("https://b.example.com")
    assert bare is not None and bare.volume_percent == -1 and bare.custom_name == ""


def test_set_enhancement_creates_and_round_trips_an_override(tmp_path: Path) -> None:
    store = _store_abc()
    favorite = store.find("uuid-a")
    assert favorite is not None and favorite.has_sound_enhancement_override is False
    assert (
        store.set_enhancement(
            "uuid-a", bass_db=-4.0, mid_db=3.0, treble_db=0.0, compressor_enabled=True
        )
        is True
    )
    assert favorite.has_sound_enhancement_override is True
    assert (favorite.eq_bass_db, favorite.eq_mid_db, favorite.eq_treble_db) == (-4.0, 3.0, 0.0)
    assert favorite.compressor_enabled is True
    save_favorites(tmp_path, store)
    loaded = load_favorites(tmp_path).find("uuid-a")
    assert loaded is not None
    assert loaded.has_sound_enhancement_override is True
    assert (loaded.eq_bass_db, loaded.eq_mid_db, loaded.eq_treble_db) == (-4.0, 3.0, 0.0)
    assert loaded.compressor_enabled is True
    # Legacy entries without the new keys read as no override.
    bare = load_favorites(tmp_path).find("https://b.example.com")
    assert bare is not None and bare.has_sound_enhancement_override is False


def test_set_enhancement_missing_key_returns_false() -> None:
    store = _store_abc()
    assert (
        store.set_enhancement(
            "nope", bass_db=0.0, mid_db=0.0, treble_db=0.0, compressor_enabled=False
        )
        is False
    )


def test_clear_enhancement_override_restores_the_shared_default() -> None:
    store = _store_abc()
    store.set_enhancement(
        "uuid-a", bass_db=-4.0, mid_db=3.0, treble_db=0.0, compressor_enabled=True
    )
    assert store.clear_enhancement_override("uuid-a") is True
    favorite = store.find("uuid-a")
    assert favorite is not None and favorite.has_sound_enhancement_override is False
    # Nothing to clear the second time.
    assert store.clear_enhancement_override("uuid-a") is False


def test_explicit_folders_exist_without_stations_and_round_trip(tmp_path: Path) -> None:
    store = _store_abc()
    assert store.add_folder("News/Morning") is True
    assert store.add_folder("News/Morning") is False  # duplicate
    assert "News/Morning" in store.folder_names()
    save_favorites(tmp_path, store)
    loaded = load_favorites(tmp_path)
    assert "News/Morning" in loaded.folder_names()
    # Rename and delete carry the explicit registry along.
    loaded.rename_folder("News", "World")
    assert "World/Morning" in loaded.folder_names()
    loaded.delete_folder("World")
    assert loaded.folder_names() == []
