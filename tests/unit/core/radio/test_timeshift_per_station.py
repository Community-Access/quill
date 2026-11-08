"""A station's own time-shift length: resolution and persistence (idea: BlindRadio, MIT)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.radio import favorites as fav
from quill.core.radio import timeshift as ts
from quill.core.radio.models import RadioStation


@pytest.mark.parametrize(
    ("own", "global_minutes", "expected"),
    [
        (-1, 60, 60),
        (120, 60, 120),
        (0, 300, 0),  # memory only is a real choice, not "unset"
        (45, 60, 60),  # not a length we offer: follow Preferences
        ("junk", 30, 30),
        (None, 999, ts.DEFAULT_MINUTES),
    ],
)
def test_resolve_minutes(own: object, global_minutes: object, expected: int) -> None:
    assert ts.resolve_minutes(own, global_minutes) == expected


def test_station_choices_lead_with_what_preferences_means_now() -> None:
    rows = ts.station_choices(120)
    assert rows[0] == (ts.FOLLOW_PREFERENCES, "Same as Preferences (2 hours, on disk)")
    assert [m for m, _l in rows[1:]] == [m for m, _l in ts.CHOICES]
    assert all("(default)" not in label for _m, label in rows)


def test_the_override_survives_a_save_and_load(tmp_path: Path) -> None:
    store = fav.RadioFavoritesStore()
    station = RadioStation(name="Jazz", stream_url="http://example.invalid/jazz")
    store.add(station)
    store.favorites[0].timeshift_minutes = 180
    fav.save_favorites(tmp_path, store)
    loaded = fav.load_favorites(tmp_path)
    assert loaded.favorites[0].timeshift_minutes == 180


@pytest.mark.parametrize("stored", ["x", 45, None])
def test_an_old_or_corrupt_value_follows_preferences(tmp_path: Path, stored: object) -> None:
    store = fav.RadioFavoritesStore()
    store.add(RadioStation(name="Jazz", stream_url="http://example.invalid/jazz"))
    store.favorites[0].timeshift_minutes = 120
    fav.save_favorites(tmp_path, store)
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["favorites"][0]["timeshift_minutes"] = stored
    path.write_text(json.dumps(data), encoding="utf-8")
    assert fav.load_favorites(tmp_path).favorites[0].timeshift_minutes == ts.FOLLOW_PREFERENCES


def test_a_file_from_before_the_field_follows_preferences(tmp_path: Path) -> None:
    store = fav.RadioFavoritesStore()
    store.add(RadioStation(name="Jazz", stream_url="http://example.invalid/jazz"))
    fav.save_favorites(tmp_path, store)
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["favorites"][0]["timeshift_minutes"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert fav.load_favorites(tmp_path).favorites[0].timeshift_minutes == ts.FOLLOW_PREFERENCES
