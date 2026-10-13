"""A browse place saved to Favorites must come back after a restart.

Found while designing QUILL Lineups (2026-10-13): a saved place -- a podcast
show, a LibriVox book, a followed channel, a genre -- is stored as a
``RadioStation`` with an empty stream URL and a ``browse:`` id, and
``RadioStation.from_dict`` refused every record with an empty stream URL. It
also never wrote ``source``. The round trip printed ``None``: every saved place
vanished the next time Radio started, and no test noticed.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.radio import favorites
from quill.core.radio.models import RadioStation


def test_a_place_round_trips_with_its_source() -> None:
    place = favorites.place_station("pishow:123", "Planet Money", source="Podcast Index")
    back = RadioStation.from_dict(place.to_dict())
    assert back is not None
    assert favorites.is_place(back)
    assert favorites.place_node_id(back) == "pishow:123"
    assert back.source == "Podcast Index"


def test_a_place_survives_save_and_load(tmp_path: Path) -> None:
    store = favorites.RadioFavoritesStore()
    store.favorites.append(
        favorites.FavoriteStation(favorites.place_station("rbgenre:jazz", "Jazz"))
    )
    favorites.save_favorites(tmp_path, store)
    loaded = favorites.load_favorites(tmp_path)
    assert [fav.station.name for fav in loaded.favorites] == ["Jazz"]
    assert favorites.is_place(loaded.favorites[0].station)


def test_an_ordinary_station_still_needs_a_stream_and_writes_no_source_key() -> None:
    assert RadioStation.from_dict({"name": "No stream", "stream_url": ""}) is None
    data = RadioStation(name="BBC", stream_url="http://x").to_dict()
    assert "source" not in data  # a Radio Browser record is exactly what it was
