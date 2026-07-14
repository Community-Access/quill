"""Tests for the "Hey QUILL" wake-word detection policy (Phase 3)."""

from __future__ import annotations

from quill.core.speech.conversation import CUE_WAKE
from quill.core.speech.wakeword import WakeController, WakeState


def _kinds(effects, kind):
    return [e for e in effects if e.kind == kind]


def _start(**kw):
    c = WakeController(**kw)
    c.start()
    return c


def test_start_enters_listening_and_opens_a_window() -> None:
    c = WakeController()
    effects = c.start()
    assert c.state == WakeState.LISTENING
    assert _kinds(effects, "listen_again")
    assert _kinds(effects, "announce")


def test_start_is_idempotent() -> None:
    c = _start()
    assert c.start() == []


def test_non_wake_window_keeps_listening() -> None:
    c = _start()
    effects = c.on_window("please save the document")
    assert c.state == WakeState.LISTENING
    assert _kinds(effects, "listen_again")
    assert not _kinds(effects, "sound")


def test_bare_wake_phrase_arms_the_conversation() -> None:
    c = _start()
    effects = c.on_window("hey quill")
    assert c.state == WakeState.WOKEN
    assert _kinds(effects, "sound")[0].value == CUE_WAKE
    assert _kinds(effects, "arm")
    assert not _kinds(effects, "dispatch")


def test_wake_phrase_with_inline_command_dispatches_it() -> None:
    c = _start()
    effects = c.on_window("Hey QUILL, save file")
    assert c.state == WakeState.WOKEN
    assert _kinds(effects, "sound")[0].value == CUE_WAKE
    dispatched = _kinds(effects, "dispatch")
    assert dispatched and dispatched[0].value == "save file"
    assert not _kinds(effects, "arm")


def test_cooldown_ignores_windows_right_after_a_wake() -> None:
    c = _start(cooldown_windows=1)
    c.on_window("hey quill save file")  # -> WOKEN
    c.resume_listening()  # back to LISTENING with cooldown pending
    # The first window after resuming is swallowed (tail of the wake utterance).
    effects = c.on_window("hey quill open file")
    assert c.state == WakeState.LISTENING
    assert not _kinds(effects, "sound")
    # The next real wake works.
    c.on_window("hey quill save file")
    assert c.state == WakeState.WOKEN


def test_periodic_reminder_when_idle() -> None:
    c = _start(reminder_every=3)
    reminders = 0
    for _ in range(6):
        effects = c.on_window("nothing relevant")
        reminders += len(_kinds(effects, "reminder"))
    assert reminders == 2  # at windows 3 and 6


def test_reminder_disabled_when_zero() -> None:
    c = _start(reminder_every=0)
    for _ in range(20):
        effects = c.on_window("nothing")
        assert not _kinds(effects, "reminder")


def test_stop_from_any_state() -> None:
    c = _start()
    effects = c.stop()
    assert c.state == WakeState.OFF
    assert _kinds(effects, "stop_listen")


def test_windows_ignored_when_off_or_woken() -> None:
    c = WakeController()  # OFF
    assert c.on_window("hey quill save file") == []
    c.start()
    c.on_window("hey quill")  # -> WOKEN
    assert c.on_window("hey quill save file") == []  # ignored until resume


def test_resume_returns_to_listening() -> None:
    c = _start()
    c.on_window("hey quill")
    effects = c.resume_listening()
    assert c.state == WakeState.LISTENING
    assert _kinds(effects, "listen_again")


def test_status_text_tracks_state() -> None:
    c = WakeController()
    assert c.status_text() == "Not listening"
    c.start()
    assert "Hey QUILL" in c.status_text()
