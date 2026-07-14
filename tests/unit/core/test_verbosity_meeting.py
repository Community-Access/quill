"""Tests for Meeting Mode (§10)."""

from __future__ import annotations

from quill.core.verbosity.meeting import MeetingMode


def test_starts_inactive() -> None:
    assert not MeetingMode().is_active


def test_enter_exit() -> None:
    meeting = MeetingMode()
    assert meeting.enter() == "Meeting Mode on"
    assert meeting.is_active
    assert meeting.exit() == "Meeting Mode off"
    assert not meeting.is_active


def test_toggle() -> None:
    meeting = MeetingMode()
    assert meeting.toggle() == "Meeting Mode on"
    assert meeting.toggle() == "Meeting Mode off"


def test_construct_active() -> None:
    assert MeetingMode(active=True).is_active
