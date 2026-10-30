"""Do Not Disturb and keep awake: always put back, even after a crash (roadmap P7)."""

from __future__ import annotations

import pytest

from quill.platform.windows import focus_guard
from quill.platform.windows.focus_guard import DoNotDisturb, restore_after_crash


@pytest.fixture
def quiet_hours(monkeypatch):
    """A fake Windows quiet-hours state, so no real notification setting changes."""
    state = {"value": 0, "writable": True}

    def read():
        return state["value"]

    def write(profile):
        if not state["writable"]:
            return False
        state["value"] = profile
        return True

    monkeypatch.setattr(focus_guard, "dnd_state", read)
    monkeypatch.setattr(focus_guard, "_set_dnd", write)
    return state


def test_turns_on_and_puts_back(tmp_path, quiet_hours):
    guard = DoNotDisturb(tmp_path)
    assert guard.start() == ""
    assert quiet_hours["value"] == focus_guard.QUIET_PRIORITY
    assert (tmp_path / "studio-dnd-restore.json").is_file()
    guard.stop()
    assert quiet_hours["value"] == focus_guard.QUIET_OFF
    assert not (tmp_path / "studio-dnd-restore.json").exists()


def test_already_quiet_is_left_alone(tmp_path, quiet_hours):
    quiet_hours["value"] = focus_guard.QUIET_ALARMS
    guard = DoNotDisturb(tmp_path)
    assert guard.start() == ""
    guard.stop()
    assert quiet_hours["value"] == focus_guard.QUIET_ALARMS


def test_refusal_is_said_and_nothing_is_left_behind(tmp_path, quiet_hours):
    quiet_hours["writable"] = False
    guard = DoNotDisturb(tmp_path)
    assert "did not turn on" in guard.start()
    assert not (tmp_path / "studio-dnd-restore.json").exists()


def test_unreadable_state_changes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(focus_guard, "dnd_state", lambda: None)
    assert "left as it is" in DoNotDisturb(tmp_path).start()


def test_a_crash_is_repaired_on_next_launch(tmp_path, quiet_hours):
    DoNotDisturb(tmp_path).start()  # never stopped: the "crash"
    assert quiet_hours["value"] == focus_guard.QUIET_PRIORITY
    assert restore_after_crash(tmp_path)
    assert quiet_hours["value"] == focus_guard.QUIET_OFF
    assert not restore_after_crash(tmp_path)
