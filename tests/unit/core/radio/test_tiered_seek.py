"""Tiered seek: how far one burst of Rewind or Forward presses moves (xradio2.md 4.4)."""

from __future__ import annotations

import pytest

from quill.core.radio import tiered_seek as ts


@pytest.mark.parametrize(
    ("taps", "seconds"),
    [(0, 0), (1, 12), (2, 60), (3, 300), (4, 300), (9, 300)],
)
def test_the_tiers_by_tap_count(taps: int, seconds: int) -> None:
    assert ts.seconds_for_taps(taps) == seconds


def _burst(direction: int, times: list[float]) -> ts.SeekBurst:
    burst = ts.SeekBurst()
    for at in times:
        burst.press(direction, at)
    return burst


def test_one_tap_is_twelve_seconds_back() -> None:
    assert _burst(-1, [0.0]).seconds() == -12


def test_taps_do_not_accumulate_three_taps_is_five_minutes() -> None:
    """Not 12 + 60 + 300: one seek, sized for the final count."""
    assert _burst(1, [0.0, 0.2, 0.4]).seconds() == 300


def test_two_deliberate_taps_are_a_minute() -> None:
    assert _burst(-1, [0.0, 0.25]).seconds() == -60


def test_a_held_key_moves_five_seconds_per_repeat() -> None:
    """Auto-repeat arrives every ~33 ms, far quicker than anybody taps."""
    presses = [index * 0.033 for index in range(10)]
    burst = _burst(-1, presses)
    assert burst.is_hold()
    assert burst.seconds() == -50


def test_quick_but_human_taps_are_not_a_hold() -> None:
    assert not _burst(1, [0.0, 0.12, 0.24]).is_hold()


def test_take_empties_the_burst_for_the_next_one() -> None:
    burst = _burst(1, [0.0, 0.2])
    assert burst.take() == 60
    assert not burst.active
    assert burst.seconds() == 0


def test_an_empty_burst_moves_nowhere() -> None:
    assert ts.SeekBurst().seconds() == 0
