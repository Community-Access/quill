"""Automatic maintenance offers wait for a quiet moment (FUX-15, maintenance_moment_ui)."""

from __future__ import annotations

import pytest

from quill.core.maintenance_moment import (
    LAUNCH_SETTLE_SECONDS,
    QUIET_SETTLE_SECONDS,
    MaintenanceMoment,
)
from quill.ui import maintenance_moment_ui as ui


class _Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


class _Later:
    """wx.CallLater stand-in: holds the callbacks until the test fires them."""

    def __init__(self) -> None:
        self.queue: list[tuple[int, object]] = []

    def __call__(self, delay_ms, run):
        self.queue.append((delay_ms, run))

    def fire(self) -> None:
        _delay, run = self.queue.pop(0)
        run()


class _Window:
    def __init__(self) -> None:
        self.front = True
        self.dead = False
        self.idle: float | None = None

    def __bool__(self) -> bool:
        return not self.dead


@pytest.fixture
def clock():
    ui.reset_for_tests()
    clock = _Clock()
    ui._MOMENTS["app"] = MaintenanceMoment(clock=clock)
    yield clock
    ui.reset_for_tests()


def _offer(window, later, notes, ran, probes=(), label="Update 2.0"):
    return ui.offer_when_quiet(
        "app",
        kind="update",
        label=label,
        run=lambda: ran.append(label),
        route="Help, Check for Updates offers it now.",
        window=window,
        note=notes.append,
        probes=probes,
        in_front=lambda: window.front,
        idle=lambda: window.idle,
        later=later,
    )


def test_the_first_minute_holds_the_offer_and_says_so_once(clock) -> None:
    window, later, notes, ran = _Window(), _Later(), [], []
    assert _offer(window, later, notes, ran) is False
    assert ran == []
    assert notes == [
        "Update 2.0 is ready and waits for a quiet moment. Help, Check for Updates offers it now."
    ]
    assert later.queue and later.queue[0][0] == ui.POLL_MS
    later.fire()  # still the first minute: polls again, says nothing more
    assert ran == [] and len(notes) == 1 and later.queue
    clock.now += LAUNCH_SETTLE_SECONDS
    later.fire()
    assert ran == ["Update 2.0"]
    assert later.queue == []  # nothing held: the poll stops


def test_a_quiet_moment_opens_it_at_once(clock) -> None:
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    window, later, notes, ran = _Window(), _Later(), [], []
    assert _offer(window, later, notes, ran) is True
    assert ran == ["Update 2.0"] and notes == [] and later.queue == []


def test_recording_holds_it_until_the_recording_ends_and_settles(clock) -> None:
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    busy = ["the recording ends"]
    window, later, notes, ran = _Window(), _Later(), [], []
    _offer(window, later, notes, ran, probes=[lambda: busy[0]])
    assert notes[0].startswith("Update 2.0 waits until the recording ends.")
    later.fire()
    assert ran == []
    busy[0] = ""
    later.fire()  # just stopped: not on the keystroke that stopped it
    assert ran == []
    clock.now += QUIET_SETTLE_SECONDS + 1
    later.fire()
    assert ran == ["Update 2.0"]


def test_it_waits_while_the_window_is_not_in_front(clock) -> None:
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    window, later, notes, ran = _Window(), _Later(), [], []
    window.front = False
    _offer(window, later, notes, ran)
    later.fire()
    assert ran == []
    window.front = True
    later.fire()  # back in front: finding their place first
    assert ran == []
    clock.now += QUIET_SETTLE_SECONDS + 1
    later.fire()
    assert ran == ["Update 2.0"]


def test_it_waits_while_the_person_is_typing(clock) -> None:
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    window, later, notes, ran = _Window(), _Later(), [], []
    window.idle = 0.5
    _offer(window, later, notes, ran)
    assert ran == []
    window.idle = 30.0
    later.fire()
    assert ran == ["Update 2.0"]


def test_the_waits_line_is_cleared_as_the_offer_opens(clock) -> None:
    window, later, notes, ran, cleared = _Window(), _Later(), [], [], []
    ui.offer_when_quiet(
        "app",
        kind="update",
        label="Update 2.0",
        run=lambda: ran.append(cleared[:]),
        route="",
        window=window,
        note=notes.append,
        in_front=lambda: True,
        idle=lambda: None,
        clear=lambda: cleared.append("cleared"),
        later=later,
    )
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    later.fire()
    assert ran == [["cleared"]]


def test_the_poll_stops_when_the_window_is_gone(clock) -> None:
    window, later, notes, ran = _Window(), _Later(), [], []
    _offer(window, later, notes, ran)
    window.dead = True
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    later.fire()
    assert ran == [] and later.queue == []


def test_an_explicit_command_takes_what_waits(clock) -> None:
    window, later, notes, ran = _Window(), _Later(), [], []
    _offer(window, later, notes, ran)
    run = ui.take_held("app", "update")
    assert run is not None
    run()
    assert ran == ["Update 2.0"]
    assert ui.take_held("app", "update") is None
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    later.fire()  # nothing left to open twice
    assert ran == ["Update 2.0"]
