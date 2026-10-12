"""Inkwell menu preferences persist off the UI path and keep the latest choice."""

from __future__ import annotations

import copy
import threading

import pytest
import wx


@pytest.fixture
def app():
    instance = wx.App(False)
    yield instance
    instance.Destroy()


@pytest.fixture
def frame(app, tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    from quill.apps.inkwell import QuillInkwellFrame

    instance = QuillInkwellFrame(safe_mode=True)
    yield instance
    instance._preference_saver.flush()
    instance._task_manager.shutdown(wait=True)
    timer = getattr(instance, "_ipc_timer", None)
    if timer is not None:
        timer.Stop()
    instance._remove_tray_icon()
    instance.frame.Destroy()


def test_preference_effect_is_immediate_while_storage_is_blocked(frame, monkeypatch):
    from quill.apps import inkwell_preference_save as inkwell

    entered = threading.Event()
    release = threading.Event()
    returned = threading.Event()

    def blocked_save(_data_dir, _settings):
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(inkwell, "save_settings", blocked_save)
    # Long enough that a slow CI worker starts the save well before it fires.
    timer = threading.Timer(5.0, release.set)
    timer.start()
    try:
        frame._set_injection_mode(True)
        returned.set()
        assert frame._settings.injection_mode == "paste"
        assert frame._status_message == (
            "Expansions are pasted; the clipboard is restored afterwards."
        )
        assert entered.wait(5)
        assert returned.is_set()
        assert not release.is_set()
    finally:
        release.set()
        timer.cancel()


def test_repeated_changes_coalesce_to_a_detached_latest_snapshot(frame, monkeypatch):
    from quill.apps import inkwell_preference_save as inkwell

    entered = threading.Event()
    release = threading.Event()
    saved = []

    def blocked_save(_data_dir, settings):
        if not saved:
            entered.set()
            assert release.wait(5)
        saved.append(copy.deepcopy(settings))

    monkeypatch.setattr(inkwell, "save_settings", blocked_save)
    try:
        frame._set_pref("announce_expansions", True)
        assert entered.wait(1)
        frame._set_pref("start_in_tray", True)
        frame._set_pref("start_in_tray", False)
        frame._set_pref("start_in_tray", True)
        frame._set_injection_mode(True)
        frame._set_injection_mode(False)
    finally:
        release.set()

    frame._preference_saver.flush()
    assert len(saved) == 2
    assert saved[0].announce_expansions
    assert not saved[0].start_in_tray
    assert saved[0].injection_mode == "type"
    assert saved[1].announce_expansions
    assert saved[1].start_in_tray
    assert saved[1].injection_mode == "type"


def test_failed_preference_write_is_announced_and_keeps_live_value(frame, monkeypatch):
    from quill.apps import inkwell_preference_save as inkwell
    from quill.stability import task_manager

    callbacks = []

    def fail_save(_data_dir, _settings):
        raise OSError("settings file unavailable")

    monkeypatch.setattr(inkwell, "save_settings", fail_save)
    monkeypatch.setattr(task_manager, "call_ui_safely", callbacks.append)
    announcements = []
    monkeypatch.setattr(frame, "_announce", announcements.append)
    frame._set_pref("start_in_tray", True)

    task = frame._preference_saver._task
    with pytest.raises(OSError, match="settings file unavailable"):
        task.future.result(timeout=5)
    frame._preference_saver.flush()
    for callback in callbacks:
        callback()

    assert frame._settings.start_in_tray
    assert frame._preference_saver._dirty
    assert announcements == [
        "Inkwell preferences could not be saved. Changes remain active for this session."
    ]
