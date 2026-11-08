"""The adaptive cushion, driven by a fake clock (an idea from BlindRadio, MIT)."""

from __future__ import annotations

from quill.core.radio import cushion
from quill.core.radio.cushion import CushionPolicy


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_stream_that_never_runs_dry_keeps_the_normal_cushion() -> None:
    clock = _Clock()
    policy = CushionPolicy(clock)
    for _ in range(10):
        clock.now += 30
        assert policy.tick() is None
    assert policy.seconds == cushion.NORMAL_SECONDS
    assert not policy.raised


def test_each_underrun_goes_one_step_deeper_up_to_fifteen() -> None:
    policy = CushionPolicy(_Clock())
    assert policy.stall_started() == 3.0
    policy.stall_ended()
    assert policy.stall_started() == 9.0
    policy.stall_ended()
    assert policy.stall_started() == 15.0
    policy.stall_ended()
    assert policy.stall_started() is None  # already as deep as it goes
    assert policy.seconds == 15.0


def test_a_clean_minute_earns_the_normal_cushion_back() -> None:
    clock = _Clock()
    policy = CushionPolicy(clock)
    policy.stall_started()
    policy.stall_started()
    clock.now += 5
    policy.stall_ended()
    clock.now += cushion.CLEAN_SECONDS - 1
    assert policy.tick() is None
    clock.now += 1
    assert policy.tick() == cushion.NORMAL_SECONDS
    assert policy.tick() is None
    assert not policy.raised


def test_time_spent_stalled_is_not_clean() -> None:
    clock = _Clock()
    policy = CushionPolicy(clock)
    policy.stall_started()
    clock.now += 600
    assert policy.tick() is None
    assert policy.seconds == 3.0


def test_a_stall_inside_the_minute_restarts_the_count() -> None:
    clock = _Clock()
    policy = CushionPolicy(clock)
    policy.stall_started()
    policy.stall_ended()
    clock.now += 50
    assert policy.stall_started() == 9.0
    policy.stall_ended()
    clock.now += 50
    assert policy.tick() is None
    clock.now += 10
    assert policy.tick() == cushion.NORMAL_SECONDS


def test_changing_station_resets_and_says_so_only_when_raised() -> None:
    policy = CushionPolicy(_Clock())
    assert policy.reset() is None
    policy.stall_started()
    assert policy.reset() == cushion.NORMAL_SECONDS
    assert policy.stall_started() == 3.0  # the new station starts from the first step


def test_mpv_value() -> None:
    assert cushion.mpv_value(3.0) == "3.0"
    assert cushion.mpv_value(cushion.NORMAL_SECONDS) == "1.0"
