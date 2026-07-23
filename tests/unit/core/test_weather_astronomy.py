"""Moon almanac: phase and illumination are checked exactly against known
lunations; rise/set is checked for physical correctness (a full moon rises near
sunset and sets near sunrise) rather than to-the-minute, since the compact
theory is only good to a few minutes."""

from __future__ import annotations

from quill.core.weather import astronomy


def _to_hours(clock: str) -> float:
    """'6:40 PM' -> 18.666..., for tolerant time comparisons."""
    hm, suffix = clock.rsplit(" ", 1)
    h, m = (int(p) for p in hm.split(":"))
    if suffix == "PM" and h != 12:
        h += 12
    if suffix == "AM" and h == 12:
        h = 0
    return h + m / 60.0


# -- phase + illumination (exact) --------------------------------------------


def test_reference_new_moon_is_dark() -> None:
    # 2000-01-06 is the reference new moon.
    alm = astronomy.almanac("2000-01-06", 32.22, -110.97, -7)
    assert alm.phase_name == "New Moon"
    assert alm.illumination_percent == 0


def test_full_moon_is_fully_lit() -> None:
    # 2000-01-21: the well-known total lunar eclipse -- a full moon.
    alm = astronomy.almanac("2000-01-21", 32.22, -110.97, -7)
    assert alm.phase_name == "Full Moon"
    assert alm.illumination_percent == 100


def test_quarters_are_half_lit() -> None:
    first = astronomy.almanac("2000-01-13", 32.22, -110.97, -7)
    last = astronomy.almanac("2000-01-28", 32.22, -110.97, -7)
    assert first.phase_name == "First Quarter"
    assert last.phase_name == "Last Quarter"
    assert 45 <= first.illumination_percent <= 55
    assert 45 <= last.illumination_percent <= 55


def test_age_and_illumination_are_pure() -> None:
    jd = astronomy.julian_day(2000, 1, 21, 12.0)
    age = astronomy.moon_age_days(jd)
    assert 14.0 <= age <= 16.0  # ~half a synodic month after the reference
    assert astronomy.illumination_percent(age) >= 99


# -- rise/set (physical correctness) -----------------------------------------


def test_full_moon_rises_near_sunset_and_sets_near_sunrise() -> None:
    # A full moon is opposite the Sun: it rises about when the Sun sets and
    # sets about when the Sun rises. Tucson in late January: sunset ~17:40,
    # sunrise ~07:25. Allow a generous window for the compact theory.
    alm = astronomy.almanac("2000-01-21", 32.22, -110.97, -7)
    assert alm.moonrise and alm.moonset
    assert 16.5 <= _to_hours(alm.moonrise) <= 20.0
    assert 6.0 <= _to_hours(alm.moonset) <= 9.5


def test_rise_set_within_a_day() -> None:
    alm = astronomy.almanac("2026-07-19", 40.71, -74.01, -4)
    for clock in (alm.moonrise, alm.moonset):
        if clock:
            assert 0.0 <= _to_hours(clock) < 24.0


def test_bad_date_returns_empty_almanac() -> None:
    alm = astronomy.almanac("not-a-date", 40.0, -74.0, -4)
    assert alm.phase_name == ""
    assert alm.moonrise == ""
    assert alm.illumination_percent == 0


def test_line_is_spoken_and_self_contained() -> None:
    alm = astronomy.MoonAlmanac(
        phase_name="Waxing Gibbous", illumination_percent=78, moonrise="3:14 PM", moonset="2:02 AM"
    )
    line = alm.line
    assert "waxing gibbous" in line
    assert "78 percent lit" in line
    assert "Moonrise 3:14 PM" in line
    assert "Moonset 2:02 AM" in line
