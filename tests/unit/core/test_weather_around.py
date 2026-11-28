"""Weather Around Me: 17 points in one request, the geometry, and the words --
what is where, and whether it is heading this way."""

from __future__ import annotations

from typing import Any

from quill.core.weather import around


def _reply(precip: float = 0.0, code: int = 3, wind_from: float = 270, wind: float = 20) -> Any:
    return {
        "current": {
            "precipitation": precip,
            "snowfall": 0.0,
            "weather_code": code,
            "wind_speed_10m": wind,
            "wind_direction_10m": wind_from,
        }
    }


def test_rain_to_the_west_moving_toward_you() -> None:
    spots = around.points(40.0, -100.0)
    assert len(spots) == 17
    replies = [_reply() for _ in spots]
    west_inner = next(i for i, s in enumerate(spots) if s[0] == 270 and s[1] == 40.0)
    replies[west_inner] = _reply(0.5, 63, wind_from=270)  # a west wind carries it east
    east_outer = next(i for i, s in enumerate(spots) if s[0] == 90 and s[1] == 80.0)
    replies[east_outer] = _reply(0.5, 71, wind_from=270)
    lines = around.describe(around.parse(replies, 40.0, -100.0))
    assert lines[0] == "Dry here now."
    assert lines[1] == "Rain 25 miles west, moving toward you."
    assert lines[2] == "Snow 50 miles east, moving away."
    assert lines[3] == "Dry in every other direction."
    assert lines[-1] == around.CAVEAT


def test_nothing_around() -> None:
    lines = around.describe(around.parse([_reply() for _ in range(17)], 1, 2), metric=True)
    assert lines == [
        "Dry here now.",
        "No rain or snow within about 80 kilometres in any direction.",
    ]


def test_barely_moving_and_passing() -> None:
    still = around.Sample(270.0, 40.0, 1.0, 0.0, 61, 2.0, 270.0)
    assert around.movement(still) == "barely moving"
    passing = around.Sample(0.0, 40.0, 1.0, 0.0, 61, 20.0, 270.0)  # north of us, going east
    assert around.movement(passing) == "moving east"


def test_one_request_weighted_by_place_count() -> None:
    url, weight = around.request_url(40.0, -100.0)
    assert weight == 17 and url.count("%2C") >= 32


def test_offset_goes_the_right_way() -> None:
    lat, lon = around.offset(40.0, -100.0, 90, 80)
    assert abs(lat - 40.0) < 0.05 and lon > -100.0
    lat, _lon = around.offset(40.0, -100.0, 0, 80)
    assert lat > 40.0


def test_a_few_dry_directions_are_named() -> None:
    spots = around.points(40.0, -100.0)
    replies = [_reply() for _ in spots]
    for i, s in enumerate(spots):
        if s[0] not in (None, 0.0, 90.0, 180.0) and s[1] == 40.0:
            replies[i] = _reply(0.5, 63)
    lines = around.describe(around.parse(replies, 40.0, -100.0))
    assert "Dry to the north, east and south." in lines
