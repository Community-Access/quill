"""QUILL Studio, Quill Media Player and QUILL Transcribe: a failed save is said.

The family settings audit (2026-11-20) found these three apps catching a
failed settings write and carrying on as if it had worked: Studio's book
volume, sleep timer, play queue, library and Preferences; the Media Player's
output device; Transcribe's key choices and Dictation Settings. Nothing told
the listener, so a choice that was gone at the next launch sounded exactly
like one that had been kept.

Each test makes the change the way the app does, with the disk refusing the
write, and checks what the person meets: the failure reaches the shared
persistence-outcome feedback (Activity, with Retry), nothing claims the save
worked, and Retry -- once the disk is back -- writes what is current, which
the next launch reads back.
"""

from __future__ import annotations

import errno
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import persistence_outcome, storage


class _Disk:
    """``storage.write_json_atomic``, refusing while ``full`` is set."""

    def __init__(self, real) -> None:
        self.real = real
        self.full = True

    def __call__(self, path, data, *args, **kwargs):
        if self.full:
            raise OSError(errno.ENOSPC, "No space left on device")
        return self.real(path, data, *args, **kwargs)


@pytest.fixture
def disk(monkeypatch: pytest.MonkeyPatch) -> _Disk:
    disk = _Disk(storage.write_json_atomic)
    monkeypatch.setattr(storage, "write_json_atomic", disk)
    # QUILL's own settings writer may hold its own reference to the writer.
    monkeypatch.setattr("quill.core.settings.write_json_atomic", disk, raising=False)
    return disk


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def heard():
    outcomes: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(outcomes.append)
    yield outcomes
    stop()


def _failures(heard) -> list[persistence_outcome.WriteOutcome]:
    return [o for o in heard if not o.ok]


def _retry_last(heard, disk: _Disk) -> None:
    failure = _failures(heard)[-1]
    assert failure.retry is not None, "a failed save must offer Retry"
    disk.full = False
    failure.retry()


# -- QUILL Studio ------------------------------------------------------------------


def test_studio_book_volume_failure_is_reported_and_retry_keeps_the_latest(
    data_dir, disk, heard
) -> None:
    from quill.apps.studio import StudioAppFrame
    from quill.core.audio_studio.book_prefs import BookPrefsStore, get_prefs, load_prefs

    app = SimpleNamespace(_book_prefs_store=BookPrefsStore())
    StudioAppFrame._on_book_volume(app, "C:/books/a.m4b", 40)
    StudioAppFrame._on_book_volume(app, "C:/books/a.m4b", 55)  # still failing

    assert _failures(heard), "the failed write was swallowed"
    assert {o.what for o in _failures(heard)} == {"QUILL Studio's book settings"}
    _retry_last(heard, disk)
    # Reload from disk, as the next launch would: the latest choice won.
    assert get_prefs(load_prefs(data_dir), "C:/books/a.m4b").volume_percent == 55


def test_studio_sleep_timer_queue_and_library_failures_are_reported(data_dir, disk, heard) -> None:
    from quill.apps.studio import StudioAppFrame
    from quill.core.audio_studio.library import LibraryState
    from quill.core.audio_studio.play_queue import PlayQueue, load_queue
    from quill.core.audio_studio.sleep_timer import SleepTimerSetting, load_sleep_setting

    app = SimpleNamespace(
        _sleep_setting=SleepTimerSetting(enabled=True, delay_minutes=30),
        _play_queue=PlayQueue(),
        _library_state=LibraryState(),
        _reload_library_tree=lambda: None,
    )
    StudioAppFrame._clear_sleep_setting(app)
    StudioAppFrame._save_play_queue(app)
    StudioAppFrame._persist_library(app)

    assert [o.what for o in _failures(heard)] == [
        "QUILL Studio's sleep timer",
        "QUILL Studio's play queue",
        "QUILL Studio's library",
    ]
    disk.full = False
    for failure in _failures(heard):
        failure.retry()
    assert load_sleep_setting(data_dir).enabled is False
    assert load_queue(data_dir).entries == []


def test_studio_preferences_failure_is_reported_and_not_called_saved(
    data_dir, disk, heard, monkeypatch
) -> None:
    from quill.apps import studio, studio_preferences

    prefs = studio._load_app_prefs()
    statuses: list[str] = []
    app = SimpleNamespace(
        _app_prefs=prefs,
        frame=None,
        _announce=lambda _m: None,
        _set_status_quiet=statuses.append,
    )

    class _Dialog:
        def __init__(self, *_a, **_k) -> None:
            pass

        def show(self):
            return ([False, True, True, False], [0], [])

    monkeypatch.setattr("quill.ui.app_preferences_dialog.PreferencesDialog", _Dialog)
    monkeypatch.setattr(studio_preferences.app_sounds, "preference_action", lambda _a: None)
    monkeypatch.setattr(studio_preferences.slider_keys, "preference_action", lambda _a: None)
    studio_preferences.open_preferences(app)

    assert [o.what for o in _failures(heard)] == ["QUILL Studio's preferences"]
    assert "Preferences saved" not in statuses, "a failed save was called saved"
    _retry_last(heard, disk)
    # Reopen, as the next launch does: the choice is there.
    assert studio._load_app_prefs()["check_updates_on_startup"] is False
    assert studio._load_app_prefs()["alt_f4_to_tray"] is True


def test_studio_capture_keys_failure_is_reported_and_not_called_saved(
    data_dir, disk, heard, monkeypatch
) -> None:
    from quill.apps.studio_capture_hotkeys import CAPTURE_HOTKEY_COMMANDS, StudioCaptureHotkeysMixin
    from quill.core.settings import load_settings

    command = CAPTURE_HOTKEY_COMMANDS[0][0]
    said: list[str] = []

    class _Dialog:
        def __init__(self, *_a, **_k) -> None:
            pass

        def show(self):
            return {command: "Ctrl+Alt+Shift+F7"}

    monkeypatch.setattr("quill.ui.global_hotkeys_dialog.GlobalHotkeysDialog", _Dialog)

    class _App(StudioCaptureHotkeysMixin):
        pass

    app = _App.__new__(_App)
    app.frame = None
    app.settings = load_settings()
    app._safe_mode = False
    app._show_modal_dialog = None
    app._announce = said.append
    app._reload_global_hotkeys = lambda: None
    app.open_capture_hotkeys()  # must not raise
    assert app.settings.global_hotkeys.get(command) == "Ctrl+Alt+Shift+F7"  # in use now

    assert [o.what for o in _failures(heard)] == ["QUILL settings"]
    assert not any("saved" in line.lower() for line in said), said
    _retry_last(heard, disk)
    assert load_settings().global_hotkeys.get(command) == "Ctrl+Alt+Shift+F7"


# -- Quill Media Player ----------------------------------------------------------------


def test_media_player_output_device_failure_is_reported_and_retry_merges(
    data_dir, disk, heard
) -> None:
    from quill.ui.media.output_device_apps import (
        MEDIA_PLAYER_DEVICE_KEY,
        MEDIA_PLAYER_PREFS,
        read_device_pref,
        save_device_pref,
    )

    path = data_dir / MEDIA_PLAYER_PREFS
    path.write_text(json.dumps({"something_else": 3}), encoding="utf-8")
    save_device_pref(MEDIA_PLAYER_PREFS, MEDIA_PLAYER_DEVICE_KEY, "Headphones")  # never raises

    assert [o.what for o in _failures(heard)] == ["Quill Media Player's settings"]
    _retry_last(heard, disk)
    assert read_device_pref(MEDIA_PLAYER_PREFS, MEDIA_PLAYER_DEVICE_KEY) == "Headphones"
    assert json.loads(path.read_text(encoding="utf-8"))["something_else"] == 3


def test_the_failure_reaches_activity_with_retry_and_the_fix_is_said(
    data_dir, disk, monkeypatch
) -> None:
    """The person's view: Activity says it once, with Retry; Retry saves; that is said."""
    from quill.core import activity
    from quill.ui import persistence_reporting
    from quill.ui.media.output_device_apps import (
        MEDIA_PLAYER_DEVICE_KEY,
        MEDIA_PLAYER_PREFS,
        read_device_pref,
        save_device_pref,
    )

    results: list[tuple[activity.ActionResult, dict]] = []
    monkeypatch.setattr(
        persistence_reporting,
        "report_result",
        lambda _host, result, actions=None: results.append((result, actions or {})),
    )
    reporter = persistence_reporting.PersistenceReporter(
        SimpleNamespace(), call_after=lambda fn, *a: fn(*a)
    )
    stop = persistence_outcome.subscribe(reporter)
    try:
        assert save_device_pref(MEDIA_PLAYER_PREFS, MEDIA_PLAYER_DEVICE_KEY, "Speakers") is False
        failed, actions = results[-1]
        assert failed.outcome == activity.FAILED
        assert activity.RETRY in failed.next_actions
        disk.full = False
        assert actions[activity.RETRY.id]() == "Saved Quill Media Player's settings."
    finally:
        stop()
    assert results[-1][0].outcome == activity.COMPLETED
    assert read_device_pref(MEDIA_PLAYER_PREFS, MEDIA_PLAYER_DEVICE_KEY) == "Speakers"


# -- QUILL Transcribe ----------------------------------------------------------------


def _transcribe_app(data_dir: Path, said: list[str]):
    from quill.apps.transcribe_commands import TranscribeCommandsMixin
    from quill.core.transcribe.settings import load_settings

    class _App(TranscribeCommandsMixin):
        pass

    app = _App()
    app._data_dir = data_dir
    app._settings = load_settings(data_dir)
    app._safe_mode = False
    app._announce = said.append
    app._set_status = said.append
    return app


def test_transcribe_save_failure_is_reported_once_with_retry(data_dir, disk, heard) -> None:
    from quill.core.transcribe.settings import load_settings

    said: list[str] = []
    app = _transcribe_app(data_dir, said)
    app._settings.close_to_tray = not app._settings.close_to_tray
    wanted = app._settings.close_to_tray
    assert app._save() is False

    assert [o.what for o in _failures(heard)] == ["QUILL Transcribe's settings"]
    # Activity says it, with Retry; the app saying it as well is the same fact twice.
    assert not any("could not be saved" in line for line in said), said
    _retry_last(heard, disk)
    assert load_settings(data_dir).close_to_tray is wanted


def test_transcribe_key_choice_failure_does_not_escape(data_dir, disk, heard, monkeypatch) -> None:
    from quill.apps.transcribe_keys import TranscribeKeysMixin
    from quill.core.transcribe.settings import load_settings

    said: list[str] = []
    app = _transcribe_app(data_dir, said)
    kept: dict[str, str] = {}

    def run(host, _wx, *, save, **_picker) -> None:
        save("Ctrl+Alt+Shift+F9")  # the picker's keep step
        host._announce("Ctrl+Alt+Shift+F9 now starts and stops dictation.")

    monkeypatch.setattr("quill.ui.show_hide_key_picker.run_system_key_command", run)
    app._own_keys = lambda _field: {}

    def save(chord: str) -> None:
        kept["chord"] = chord
        app._settings.dictation_hotkey = chord

    TranscribeKeysMixin._choose_key(app, save=save, field="dictation")  # must not raise

    assert [o.what for o in _failures(heard)] == ["QUILL Transcribe's settings"]
    _retry_last(heard, disk)
    assert load_settings(data_dir).dictation_hotkey == "Ctrl+Alt+Shift+F9"
