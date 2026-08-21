"""Radio Browser's own stream check is read rather than thrown away.

``lastcheckok`` arrived on every search result and was dropped on the floor.
The tri-state matters more than it looks: "nobody has checked" and "the check
failed" are the difference between a row that says nothing and a row that warns
somebody off a station.
"""

from __future__ import annotations

from quill.core.radio.radio_browser import _coerce_check, _station_from_json


def _entry(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": "WQXR", "url": "http://example.org/stream"}
    base.update(kwargs)
    return base


def test_a_passing_check_is_read_from_the_search_result() -> None:
    station = _station_from_json(_entry(lastcheckok=1))
    assert station is not None
    assert station.last_check_ok is True


def test_a_failing_check_is_read_too() -> None:
    station = _station_from_json(_entry(lastcheckok=0))
    assert station is not None
    assert station.last_check_ok is False


def test_an_absent_check_stays_none_rather_than_becoming_false() -> None:
    # The endpoint omits the field in places, and collapsing absent to False
    # would warn listeners off stations nobody has ever checked.
    station = _station_from_json(_entry())
    assert station is not None
    assert station.last_check_ok is None


def test_every_shape_the_field_has_been_seen_in_is_accepted() -> None:
    # This app does not control the API, and the field has arrived as an int,
    # a string and a JSON boolean.
    assert _coerce_check(1) is True
    assert _coerce_check(0) is False
    assert _coerce_check("1") is True
    assert _coerce_check("0") is False
    assert _coerce_check(True) is True
    assert _coerce_check(False) is False
    assert _coerce_check("true") is True
    assert _coerce_check("no") is False


def test_an_unrecognised_value_is_unknown_rather_than_a_guess() -> None:
    assert _coerce_check("perhaps") is None
    assert _coerce_check(None) is None
    assert _coerce_check([]) is None


def test_the_check_never_changes_a_station_identity() -> None:
    """A station whose check flips must stay the same station.

    ``last_check_ok`` is excluded from equality on purpose: favorites
    de-duplicate on the model, and a row that became a *different* station when
    the directory re-checked it would quietly duplicate somebody's favorites.
    """
    healthy = _station_from_json(_entry(lastcheckok=1))
    broken = _station_from_json(_entry(lastcheckok=0))
    assert healthy == broken
