"""Maintenance waits for a quiet moment (FUX-15, quill/core/maintenance_moment.py)."""

from __future__ import annotations

from quill.core.maintenance_moment import (
    FIRST_MINUTE,
    INPUT_IDLE_SECONDS,
    LAUNCH_SETTLE_SECONDS,
    NOT_IN_FRONT,
    QUIET_SETTLE_SECONDS,
    SETTLING,
    TYPING,
    MaintenanceMoment,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _settled() -> tuple[MaintenanceMoment, _Clock]:
    clock = _Clock()
    moment = MaintenanceMoment(clock=clock)
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    return moment, clock


def test_nothing_automatic_opens_in_the_first_minute_after_launch() -> None:
    clock = _Clock()
    moment = MaintenanceMoment(clock=clock)
    assert moment.hold_reason() == FIRST_MINUTE
    clock.now += LAUNCH_SETTLE_SECONDS - 1
    assert moment.hold_reason() == FIRST_MINUTE
    clock.now += 2
    assert moment.hold_reason() == ""


def test_busy_work_holds_and_names_itself() -> None:
    moment, _clock = _settled()
    assert moment.hold_reason([lambda: "", lambda: "the recording ends"]) == "the recording ends"


def test_the_moment_must_stay_quiet_a_while_after_work_stops() -> None:
    moment, clock = _settled()
    busy = ["playback stops"]
    probe = lambda: busy[0]  # noqa: E731
    assert moment.hold_reason([probe]) == "playback stops"
    busy[0] = ""
    assert moment.hold_reason([probe]) == SETTLING
    clock.now += QUIET_SETTLE_SECONDS + 1
    assert moment.hold_reason([probe]) == ""


def test_an_app_that_is_not_in_front_waits_and_settles_on_return() -> None:
    moment, clock = _settled()
    assert moment.hold_reason(in_front=False) == NOT_IN_FRONT
    assert moment.hold_reason(in_front=True) == SETTLING
    clock.now += QUIET_SETTLE_SECONDS + 1
    assert moment.hold_reason(in_front=True) == ""


def test_an_offer_never_takes_a_keystroke_meant_for_the_document() -> None:
    moment, _clock = _settled()
    assert moment.hold_reason(input_idle=1.0) == TYPING
    assert moment.hold_reason(input_idle=INPUT_IDLE_SECONDS + 1) == ""
    assert moment.hold_reason(input_idle=None) == ""  # unknown is not busy


def test_a_broken_probe_counts_as_idle() -> None:
    moment, _clock = _settled()

    def broken() -> str:
        raise RuntimeError("gone")

    assert moment.hold_reason([broken]) == ""


def test_a_quiet_moment_runs_the_offer_now() -> None:
    moment, _clock = _settled()
    decision = moment.offer("update", "Update 3.4.0", lambda: None, route="Help.")
    assert decision.run_now and decision.line == ""
    assert not moment.holding


def test_a_held_offer_says_once_what_waits_and_how_to_reach_it() -> None:
    moment, _clock = _settled()
    busy = [lambda: "dictation ends"]
    first = moment.offer(
        "update", "Update 3.4.0", lambda: None, route="Help, Check for Updates.", probes=busy
    )
    assert not first.run_now
    assert first.line == "Update 3.4.0 waits until dictation ends. Help, Check for Updates."
    again = moment.offer("update", "Update 3.4.0", lambda: None, route="x", probes=busy)
    assert not again.run_now and again.line == ""
    assert moment.waiting() == ["Update 3.4.0"]


def test_a_timing_hold_says_it_waits_for_a_quiet_moment() -> None:
    moment = MaintenanceMoment(clock=_Clock())
    decision = moment.offer("update", "Update 3.4.0", lambda: None, route="Help.")
    assert decision.line == "Update 3.4.0 is ready and waits for a quiet moment. Help."


def test_due_releases_held_offers_only_when_quiet() -> None:
    moment, clock = _settled()
    ran: list[str] = []
    busy = ["the live broadcast ends"]
    probe = lambda: busy[0]  # noqa: E731
    moment.offer("update", "Update 2", lambda: ran.append("update"), route="", probes=[probe])
    assert moment.due([probe]) is None
    busy[0] = ""
    clock.now += QUIET_SETTLE_SECONDS + 1
    run = moment.due([probe])
    assert run is not None
    run()
    assert ran == ["update"]
    assert not moment.holding


def test_due_opens_one_offer_at_a_time() -> None:
    clock = _Clock()
    moment = MaintenanceMoment(clock=clock)
    moment.offer("braille", "Braille", lambda: "braille", route="")
    moment.offer("update", "Update", lambda: "update", route="")
    clock.now += LAUNCH_SETTLE_SECONDS + 1
    first = moment.due()
    assert first is not None and first() == "braille"
    assert moment.waiting() == ["Update"]


def test_the_newest_offer_of_a_kind_replaces_the_older_one() -> None:
    moment = MaintenanceMoment(clock=_Clock())
    ran: list[str] = []
    moment.offer("update", "Update 1", lambda: ran.append("1"), route="")
    moment.offer("update", "Update 2", lambda: ran.append("2"), route="")
    assert moment.waiting() == ["Update 2"]


def test_an_explicit_command_takes_the_held_offer() -> None:
    moment = MaintenanceMoment(clock=_Clock())
    moment.offer("update", "Update 1", lambda: "ran", route="")
    run = moment.take("update")
    assert run is not None and run() == "ran"
    assert moment.take("update") is None
    assert not moment.holding
