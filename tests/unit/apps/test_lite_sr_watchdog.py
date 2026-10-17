"""QUILL Lite: a screen reader dying mid-session saves work first, then explains.

The same wx-free core as QUILL (``quill.core.sr_watchdog``); fakes only -- no
real reader is detected and no wx timer is armed.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.apps.lite_sr_watchdog import LiteSrWatchdogMixin
from quill.core.sr_watchdog import SrWatchdog


class _Frame:
    def __init__(self, *, modified: bool, fails: bool = False) -> None:
        self.modified = modified
        self._slot: Any = object() if modified else None
        self.fails = fails
        self.copies = 0
        self.said: list[str] = []

    def _write_recovery_copy(self) -> None:
        if self.fails:
            raise RuntimeError("the window went away")
        self.copies += 1

    def _announce(self, message: str) -> None:
        self.said.append(message)


class _Voice:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.reprobed = 0

    def speak(self, message: str) -> None:
        self.spoken.append(message)

    def reprobe(self) -> None:
        self.reprobed += 1


class _App(LiteSrWatchdogMixin):
    def __init__(self, frames: list[_Frame]) -> None:
        self.frames = frames
        self.active_frame = frames[0] if frames else None
        self.voice = _Voice()
        self.shutting_down = False
        self.scheduled = 0

    def _schedule_sr_watchdog_check(self) -> None:
        self.scheduled += 1


def test_death_copies_every_unsaved_document_then_explains() -> None:
    dirty, clean, other = _Frame(modified=True), _Frame(modified=False), _Frame(modified=True)
    app = _App([dirty, clean, other])

    app._on_screen_reader_died("NVDA")

    assert (dirty.copies, clean.copies, other.copies) == (1, 0, 1)
    assert len(dirty.said) == 1  # the active window: spoken and in its status bar
    message = dirty.said[0]
    assert message.startswith("NVDA appears to have stopped.")
    assert "2 documents snapshotted" in message
    assert "QUILL Lite keeps running" in message


def test_one_failing_window_does_not_stop_the_rest() -> None:
    broken, fine = _Frame(modified=True, fails=True), _Frame(modified=True)
    app = _App([broken, fine])

    assert app._sr_emergency_flush() == 1
    assert fine.copies == 1


def test_nothing_unsaved_is_said_plainly() -> None:
    app = _App([_Frame(modified=False)])

    app._on_screen_reader_died("")

    said = app.frames[0].said[0]
    assert said.startswith("Your screen reader appears to have stopped.")
    assert "no unsaved work" in said


def test_with_no_window_the_voice_still_gets_the_sentence() -> None:
    app = _App([])

    app._on_screen_reader_died("JAWS")

    assert app.voice.spoken and "JAWS appears to have stopped" in app.voice.spoken[0]


def test_recovery_reprobes_the_voice_and_says_so() -> None:
    frame = _Frame(modified=False)
    app = _App([frame])

    app._on_screen_reader_recovered("NVDA")

    assert app.voice.reprobed == 1
    assert frame.said == ["NVDA is running again."]


def test_two_misses_through_the_tick_fire_the_flush_once() -> None:
    frame = _Frame(modified=True)
    app = _App([frame])
    sightings = iter(["NVDA", "", "", "", "NVDA"])
    app._sr_watchdog = SrWatchdog(lambda: next(sightings))

    for _ in range(5):
        app._on_sr_watchdog_tick()

    assert frame.copies == 1  # one confirmed death, one flush
    assert frame.said[0].startswith("NVDA appears to have stopped.")
    assert frame.said[-1] == "NVDA is running again."
    assert app.scheduled == 5  # each tick re-arms the cadence


def test_shutting_down_stops_the_cadence() -> None:
    app = _App([_Frame(modified=True)])
    app._sr_watchdog = SrWatchdog(lambda: "")
    app.shutting_down = True

    app._on_sr_watchdog_tick()

    assert app.scheduled == 0


def test_a_watchdog_error_never_reaches_the_app() -> None:
    app = _App([_Frame(modified=True)])

    class _Broken:
        def check(self) -> Any:
            raise ValueError("boom")

    app._sr_watchdog = _Broken()
    app._on_sr_watchdog_tick()  # must not raise

    assert app.scheduled == 1


def test_stopping_is_safe_before_and_after_starting() -> None:
    app = _App([])
    app._stop_sr_watchdog()  # never started

    class _Call:
        stopped = 0

        def Stop(self) -> None:  # noqa: N802 - wx shape
            _Call.stopped += 1

    app._sr_watchdog_call = _Call()
    app._stop_sr_watchdog()
    app._stop_sr_watchdog()

    assert _Call.stopped == 1


def test_start_is_windows_only_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.apps.lite_sr_watchdog as mod

    app = _App([])
    monkeypatch.setattr(mod.sys, "platform", "linux")
    app._start_sr_watchdog()
    assert getattr(app, "_sr_watchdog", None) is None

    monkeypatch.setattr(mod.sys, "platform", "win32")
    app._start_sr_watchdog()
    first = app._sr_watchdog
    app._start_sr_watchdog()
    assert app._sr_watchdog is first
    assert app.scheduled == 1


def test_quill_lite_runs_the_watchdog() -> None:
    from quill.apps.lite import QuillLiteApp

    assert issubclass(QuillLiteApp, LiteSrWatchdogMixin)
