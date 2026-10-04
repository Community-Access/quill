"""Your own station tags: parsing, where they are stored, and the round trip."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.radio import station_tags as tags_mod
from quill.core.radio.favorites import RadioFavoritesStore, load_favorites, save_favorites
from quill.core.radio.models import RadioStation


def _station(
    name: str = "97.1 The Ticket", url: str = "http://example.invalid/wxyt"
) -> RadioStation:
    return RadioStation(name=name, stream_url=url, tags=("sports", "talk"))


def test_parse_tags_trims_dedupes_and_accepts_other_separators() -> None:
    assert tags_mod.parse_tags(" Detroit Tigers, MLB;baseball\n mlb ,, ") == (
        "Detroit Tigers",
        "MLB",
        "baseball",
    )
    assert tags_mod.parse_tags("") == ()


def test_parse_tags_caps_count_and_length() -> None:
    many = ",".join(f"tag{i}" for i in range(100))
    assert len(tags_mod.parse_tags(many)) == tags_mod.MAX_TAGS
    assert len(tags_mod.parse_tags("x" * 500)[0]) == tags_mod.MAX_TAG_CHARS


def test_favorite_tags_round_trip_through_the_favorites_file(tmp_path: Path) -> None:
    store = RadioFavoritesStore()
    station = _station()
    store.add(station)
    tag_store = tags_mod.StationTagStore()
    changed = tags_mod.set_user_tags(
        station, ("Detroit Tigers", "MLB"), favorites=store, store=tag_store
    )
    assert changed == (True, False)
    save_favorites(tmp_path, store)

    loaded = load_favorites(tmp_path)
    assert loaded.favorites[0].user_tags == ("Detroit Tigers", "MLB")
    assert tags_mod.user_tags_for(station, favorites=loaded, store=None) == (
        "Detroit Tigers",
        "MLB",
    )


def test_non_favorite_tags_round_trip_through_their_own_file(tmp_path: Path) -> None:
    station = _station(name="WJR", url="http://example.invalid/wjr")
    tag_store = tags_mod.StationTagStore()
    assert tags_mod.set_user_tags(
        station, ("news",), favorites=RadioFavoritesStore(), store=tag_store
    )
    tags_mod.save_tag_store(tmp_path, tag_store)

    raw = json.loads((tmp_path / tags_mod.FILE_NAME).read_text(encoding="utf-8"))
    assert raw["stations"][0]["tags"] == ["news"]
    loaded = tags_mod.load_tag_store(tmp_path)
    assert loaded.tags_for(station) == ("news",)
    ((found_station, found_tags),) = tags_mod.tagged_stations(favorites=None, store=loaded)
    assert found_station.stream_url == station.stream_url and found_tags == ("news",)


def test_becoming_a_favorite_moves_the_tags_out_of_the_map() -> None:
    station = _station()
    tag_store = tags_mod.StationTagStore()
    tag_store.set(station, ("old",))
    favorites = RadioFavoritesStore()
    favorites.add(station)
    assert tags_mod.set_user_tags(station, ("new",), favorites=favorites, store=tag_store) == (
        True,
        True,
    )
    assert tag_store.entries == {}
    assert favorites.favorites[0].user_tags == ("new",)


def test_empty_tags_remove_the_entry() -> None:
    station = _station()
    tag_store = tags_mod.StationTagStore()
    tag_store.set(station, ("x",))
    assert tag_store.set(station, ()) is True
    assert tag_store.tags_for(station) == ()


def test_broken_or_missing_tag_file_reads_as_empty(tmp_path: Path) -> None:
    assert tags_mod.load_tag_store(tmp_path).entries == {}
    (tmp_path / tags_mod.FILE_NAME).write_text("{not json", encoding="utf-8")
    assert tags_mod.load_tag_store(tmp_path).entries == {}
    (tmp_path / tags_mod.FILE_NAME).write_text(
        json.dumps({"stations": [{"station": {"name": ""}, "tags": ["x"]}, "junk"]}),
        encoding="utf-8",
    )
    assert tags_mod.load_tag_store(tmp_path).entries == {}


def test_favorites_saved_before_tags_existed_load_with_none(tmp_path: Path) -> None:
    (tmp_path / "radio_favorites.json").write_text(
        json.dumps({"favorites": [{"station": {"name": "A", "stream_url": "http://a"}}]}),
        encoding="utf-8",
    )
    assert load_favorites(tmp_path).favorites[0].user_tags == ()


def test_details_put_your_tags_beside_the_directorys() -> None:
    station = _station()
    text = tags_mod.details_with_tags(station.details_text, ("Detroit Tigers",))
    lines = text.split("\n")
    assert lines[lines.index("Tags: sports, talk") + 1] == "Your tags: Detroit Tigers"
    bare = RadioStation(name="Plain", stream_url="http://p")
    assert "Your tags: x" in tags_mod.details_with_tags(bare.details_text, ("x",))
    assert tags_mod.details_with_tags("A", ()) == "A"


def test_the_tag_map_is_carried_by_setup_transfer_and_backup() -> None:
    from quill.core import setup_transfer
    from quill.core.radio import backup

    assert tags_mod.FILE_NAME in {item.filename for item in setup_transfer.ITEMS}
    assert tags_mod.FILE_NAME in backup.RADIO_DATA_FILES
