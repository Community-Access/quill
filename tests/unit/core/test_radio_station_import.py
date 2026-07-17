"""Import radio stations from JSON (quill.core.radio.station_import):
shape tolerance, skip-don't-crash on bad entries, duplicate-safe merging,
and category -> favorites-folder mapping."""

from __future__ import annotations

import pytest

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.station_import import (
    StationImportError,
    merge_stations,
    parse_stations_json,
)

# The shape accessible radio apps commonly use: a flat array of
# name/category/stream_url objects.
_COMMON_SHAPE = (
    '[{"name": "Classic FM", "category": "Classical",'
    ' "stream_url": "http://media-ice.musicradio.com:80/ClassicFM"},'
    '{"name": "Some Talk", "category": "Public Community and Speech",'
    ' "stream_url": "https://example.com/talk"}]'
)


def test_parses_the_common_shape_with_categories_as_folders() -> None:
    stations = parse_stations_json(_COMMON_SHAPE)
    assert [s.station.name for s in stations] == ["Classic FM", "Some Talk"]
    assert stations[0].folder == "Classical"
    assert stations[0].station.stream_url.startswith("http://media-ice")


def test_parses_alternate_key_spellings() -> None:
    stations = parse_stations_json(
        '[{"title": "Alt", "url": "https://example.com/a", "genre": "News"}]'
    )
    assert stations[0].station.name == "Alt"
    assert stations[0].folder == "News"


def test_parses_an_object_with_a_stations_array() -> None:
    stations = parse_stations_json(
        '{"stations": [{"name": "Wrapped", "stream_url": "https://example.com/w"}]}'
    )
    assert stations[0].station.name == "Wrapped"
    assert stations[0].folder == ""


def test_skips_entries_without_a_name_or_plausible_url() -> None:
    stations = parse_stations_json(
        '[{"name": "No URL"},'
        ' {"stream_url": "https://example.com/nameless"},'
        ' {"name": "Bad scheme", "stream_url": "file:///etc/passwd"},'
        " 42,"
        ' {"name": "Good", "stream_url": "https://example.com/good"}]'
    )
    assert [s.station.name for s in stations] == ["Good"]


def test_rejects_non_json_and_non_station_json() -> None:
    with pytest.raises(StationImportError):
        parse_stations_json("not json at all")
    with pytest.raises(StationImportError):
        parse_stations_json('{"unrelated": true}')
    with pytest.raises(StationImportError):
        parse_stations_json('[{"name": "No URL anywhere"}]')


def test_merge_adds_with_folders_and_never_duplicates() -> None:
    store = RadioFavoritesStore()
    store.add(RadioStation(name="Already", stream_url="https://example.com/talk"))
    result = merge_stations(store, parse_stations_json(_COMMON_SHAPE))
    assert result.added == 1  # Some Talk's URL was already a favorite
    assert result.skipped_duplicates == 1
    assert result.folders == 1
    imported = store.find("http://media-ice.musicradio.com:80/ClassicFM")
    assert imported is not None
    assert imported.folder == "Classical"
    assert imported.custom is True


def test_merge_never_overwrites_an_existing_favorite() -> None:
    store = RadioFavoritesStore()
    store.add(RadioStation(name="My Name", stream_url="https://example.com/talk"))
    store.favorites[0].custom_name = "Curated"
    merge_stations(store, parse_stations_json(_COMMON_SHAPE))
    kept = store.find("https://example.com/talk")
    assert kept is not None
    assert kept.custom_name == "Curated"  # the import must not disturb it
