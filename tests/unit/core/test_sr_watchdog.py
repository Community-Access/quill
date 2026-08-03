"""Two-strikes screen-reader liveness (16-assessment.md item 10)."""

from __future__ import annotations

from quill.core.sr_watchdog import MISSES_BEFORE_DEATH, SrWatchdog


class _Probe:
    def __init__(self, *results: str) -> None:
        self._results = list(results)

    def __call__(self) -> str:
        return self._results.pop(0) if self._results else ""


def test_never_armed_without_a_reader() -> None:
    # No reader ever seen (SAPI self-voice, sighted testing): the emergency
    # path must never fire no matter how many checks miss.
    watchdog = SrWatchdog(_Probe("", "", "", ""))
    for _ in range(4):
        assert watchdog.check().kind == "none"
    assert not watchdog.armed


def test_one_missed_check_is_not_a_death() -> None:
    # A routine JAWS/NVDA restart misses one check and comes back.
    watchdog = SrWatchdog(_Probe("JAWS", "", "JAWS"))
    assert watchdog.check().kind == "none"
    assert watchdog.check().kind == "none"  # first strike only
    assert watchdog.check().kind == "none"  # reader back; count reset


def test_two_consecutive_misses_confirm_death() -> None:
    watchdog = SrWatchdog(_Probe("NVDA", "", ""))
    watchdog.check()
    assert watchdog.check().kind == "none"
    died = watchdog.check()
    assert died.kind == "died"
    assert died.reader_name == "NVDA"
    assert MISSES_BEFORE_DEATH == 2


def test_death_fires_once_then_recovery_is_reported() -> None:
    watchdog = SrWatchdog(_Probe("JAWS", "", "", "", "JAWS"))
    watchdog.check()
    watchdog.check()
    assert watchdog.check().kind == "died"
    assert watchdog.check().kind == "none"  # still dead: no repeat firing
    recovered = watchdog.check()
    assert recovered.kind == "recovered"
    assert recovered.reader_name == "JAWS"


def test_probe_errors_count_as_misses_but_never_raise() -> None:
    calls = {"n": 0}

    def probe() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "JAWS"
        raise RuntimeError("snapshot failed")

    watchdog = SrWatchdog(probe)
    watchdog.check()
    assert watchdog.check().kind == "none"
    assert watchdog.check().kind == "died"


def test_the_string_none_is_not_a_reader() -> None:
    watchdog = SrWatchdog(_Probe("none", "none"))
    watchdog.check()
    watchdog.check()
    assert not watchdog.armed
