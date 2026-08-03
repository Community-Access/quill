"""A burst of different braille messages settles instead of flickering.

The dedupe layers (braille_output and the announce policy) only suppress an
identical repeat inside 2 s; a cascade of *different* messages still replaced
each other on the display faster than cell one could be read. The
CoalescingBrailleWriter writes the first message of a quiet period straight
through (no added latency), then conflates anything arriving inside a short
window down to the newest message.
"""

from __future__ import annotations

from quill.ui.announce_wiring import CoalescingBrailleWriter


class _FakeTimer:
    def __init__(self) -> None:
        self.running = True

    def IsRunning(self) -> bool:  # noqa: N802 - wx.CallLater spelling
        return self.running


class _FakeScheduler:
    """Deterministic stand-in for wx.CallLater."""

    def __init__(self) -> None:
        self.timers: list[_FakeTimer] = []
        self.callbacks: list[object] = []

    def __call__(self, delay_ms: int, fn: object) -> _FakeTimer:
        timer = _FakeTimer()
        self.timers.append(timer)
        self.callbacks.append(fn)
        return timer

    def close_window(self) -> None:
        """Expire the newest window and run its flush callback."""
        timer = self.timers[-1]
        callback = self.callbacks[-1]
        timer.running = False
        callback()  # type: ignore[operator]


def _writer() -> tuple[CoalescingBrailleWriter, list[str], _FakeScheduler]:
    written: list[str] = []

    def write(text: str) -> str:
        written.append(text)
        return ""

    scheduler = _FakeScheduler()
    return CoalescingBrailleWriter(write, schedule=scheduler), written, scheduler


def test_first_message_writes_through_immediately() -> None:
    writer, written, _scheduler = _writer()

    writer("Saved note.md")

    assert written == ["Saved note.md"]


def test_a_burst_conflates_to_the_newest_message() -> None:
    writer, written, scheduler = _writer()

    writer("Connecting")
    writer("Buffering")
    writer("Playing: Morning Show")
    scheduler.close_window()

    # First writes through; the two burst messages collapse to the newest.
    assert written == ["Connecting", "Playing: Morning Show"]


def test_a_quiet_period_resets_the_window() -> None:
    writer, written, scheduler = _writer()

    writer("First")
    scheduler.close_window()  # window expires with nothing pending
    writer("Second")

    assert written == ["First", "Second"]


def test_a_sustained_burst_writes_once_per_window() -> None:
    writer, written, scheduler = _writer()

    writer("m1")
    writer("m2")
    writer("m3")
    scheduler.close_window()  # writes m3, re-arms
    writer("m4")
    writer("m5")
    scheduler.close_window()

    assert written == ["m1", "m3", "m5"]


def test_without_a_timer_every_message_writes_through() -> None:
    written: list[str] = []

    def write(text: str) -> str:
        written.append(text)
        return ""

    writer = CoalescingBrailleWriter(write, schedule=lambda _delay, _fn: None)

    writer("one")
    writer("two")

    assert written == ["one", "two"]


def test_write_errors_pass_through_for_immediate_writes() -> None:
    def write(_text: str) -> str:
        return "Braille output failed: display unplugged"

    writer = CoalescingBrailleWriter(write, schedule=lambda _delay, _fn: None)

    assert "failed" in writer("hello")
