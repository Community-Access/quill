"""QUILL Lite settings: the latest choice wins, in every interleaving.

plan.md (settings review, high priority) reproduced two ways a preference
could be reported saved and come back changed after a restart:

* **Queued versus synchronous overlap.** An older background write, paused
  just before its atomic write, landed *after* a newer synchronous save and put
  the old value back on disk, while memory kept the new one and the dirty flag
  said all was well.
* **A quick revert.** True -> False -> True, with the first write paused, wrote
  ``[False, False]``: the second snapshot carried a merge baseline the first
  write had already overtaken, so it looked unchanged and kept the disk's False.

Every test runs the real mixin, the real merge and the real file writer against
a temporary file; the pause is a gate inside the atomic writer, so the order of
events is set by the test, not by the scheduler. "Restart" is a fresh load of
the file, which is what the next launch reads.
"""

from __future__ import annotations

import copy
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.apps import lite_settings_persistence as persistence
from quill.core import persistence_outcome
from quill.core.lite import settings as settings_mod
from quill.core.lite import settings_merge
from quill.core.storage import write_json_atomic as _real_write

WAIT = 10.0


class _App(persistence.LiteSettingsPersistenceMixin):
    shutting_down = False

    def __init__(self) -> None:
        self.frames: list = []
        self.spoken: list[str] = []
        self.voice = SimpleNamespace(speak=self.spoken.append)
        self._stop_write_reports = lambda: None  # no Activity window in a unit test
        self.settings = settings_mod.load()
        self._settings_baseline = copy.deepcopy(self.settings)


class _Writer:
    """The atomic writer, with a gate that can hold one chosen write."""

    def __init__(self) -> None:
        self.written: list[bool] = []
        self.hold_next = False
        self.entered = threading.Event()
        self.release = threading.Event()
        self.fail_with: OSError | None = None
        self._lock = threading.Lock()

    def __call__(self, path: Path, document: dict) -> None:
        with self._lock:
            hold, self.hold_next = self.hold_next, False
        if hold:
            self.entered.set()
            assert self.release.wait(WAIT), "the test never released the held write"
        if self.fail_with is not None:
            raise self.fail_with
        self.written.append(bool(document.get("word_wrap", settings_mod.Settings().word_wrap)))
        _real_write(path, document)


@pytest.fixture
def shared_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "settings_path", lambda: target)
    monkeypatch.setattr(settings_merge, "settings_path", lambda: target)
    # Failure notices are delivered inline: no wx.App in a unit test.
    monkeypatch.setattr(persistence.wx, "CallAfter", lambda fn, *a: fn(*a), raising=False)
    return target


@pytest.fixture
def writer(monkeypatch: pytest.MonkeyPatch) -> _Writer:
    gate = _Writer()
    monkeypatch.setattr(settings_mod, "write_json_atomic", gate)
    return gate


def _start_with(shared_file: Path, *, word_wrap: bool) -> _App:
    settings_mod.save(settings_mod.Settings(word_wrap=word_wrap), shared_file)
    return _App()


def _restart(shared_file: Path) -> settings_mod.Settings:
    return settings_mod.load(shared_file)


def test_an_older_queued_write_never_lands_after_a_newer_synchronous_save(
    shared_file: Path, writer: _Writer
) -> None:
    app = _start_with(shared_file, word_wrap=False)
    app.settings.word_wrap = True  # View > Word Wrap: queued
    writer.hold_next = True
    app._queue_settings_save()
    assert writer.entered.wait(WAIT)
    app.settings.word_wrap = False  # then Preferences: synchronous
    result: list[bool] = []
    sync = threading.Thread(target=lambda: result.append(app.save_settings()))
    sync.start()
    sync.join(0.3)  # the synchronous save waits its turn, or (before) finished early
    writer.release.set()
    sync.join(WAIT)
    app.flush_settings_writes()
    assert result == [True]
    assert app.settings.word_wrap is False
    assert _restart(shared_file).word_wrap is False  # was True: the old write landed last
    assert app.settings_dirty is False


def test_a_quick_revert_writes_the_latest_choice(shared_file: Path, writer: _Writer) -> None:
    app = _start_with(shared_file, word_wrap=True)
    writer.written.clear()
    app.settings.word_wrap = False
    writer.hold_next = True
    app._queue_settings_save()
    assert writer.entered.wait(WAIT)
    app.settings.word_wrap = True  # changed back while the first write is held
    app._queue_settings_save()
    writer.release.set()
    app.flush_settings_writes()
    assert writer.written == [False, True]  # was [False, False]
    assert app.settings.word_wrap is True
    assert _restart(shared_file).word_wrap is True
    assert app.settings_dirty is False


def test_a_revert_after_a_finished_write_is_written_too(shared_file: Path, writer: _Writer) -> None:
    app = _start_with(shared_file, word_wrap=True)
    for value in (False, True, False, True):
        app.settings.word_wrap = value
        app._queue_settings_save()
        app.flush_settings_writes()
        assert _restart(shared_file).word_wrap is value


def test_shutdown_flush_waits_for_the_held_write_and_keeps_the_last_choice(
    shared_file: Path, writer: _Writer
) -> None:
    app = _start_with(shared_file, word_wrap=True)
    app.settings.word_wrap = False
    writer.hold_next = True
    app._queue_settings_save()
    assert writer.entered.wait(WAIT)
    app.settings.word_wrap = True
    app._queue_settings_save()
    threading.Timer(0.2, writer.release.set).start()
    app.flush_settings_writes()  # Exit: returns only once everything is on disk
    assert _restart(shared_file).word_wrap is True
    assert app._settings_save_executor is None
    app.settings.word_wrap = False  # a save after the flush still works
    app._queue_settings_save()
    app.flush_settings_writes()
    assert _restart(shared_file).word_wrap is False


def test_a_failed_write_is_reported_never_claimed_and_retry_writes_what_is_current(
    shared_file: Path, writer: _Writer
) -> None:
    outcomes: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(outcomes.append)
    try:
        app = _start_with(shared_file, word_wrap=True)
        writer.fail_with = PermissionError("locked")
        app.settings.word_wrap = False
        assert app.save_settings() is False
        assert app.settings_dirty is True
        assert app.spoken == [persistence.SETTINGS_NOT_SAVED]
        assert _restart(shared_file).word_wrap is True  # nothing claimed
        failed = [o for o in outcomes if not o.ok]
        assert failed and failed[-1].retry is not None
        # The disk comes back; the listener changes their mind and it saves.
        writer.fail_with = None
        app.settings.word_wrap = True
        assert app.save_settings() is True
        assert app.settings_dirty is False
        # Activity's Retry for the old failure must not put False back.
        failed[-1].retry()
        assert _restart(shared_file).word_wrap is True
    finally:
        stop()


def test_retry_after_a_queued_failure_saves_and_clears_the_flag(
    shared_file: Path, writer: _Writer
) -> None:
    outcomes: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(outcomes.append)
    try:
        app = _start_with(shared_file, word_wrap=True)
        writer.fail_with = PermissionError("locked")
        app.settings.word_wrap = False
        app._queue_settings_save()
        app.flush_settings_writes()
        assert app.settings_dirty is True
        writer.fail_with = None
        [o for o in outcomes if not o.ok][-1].retry()
        assert app.settings_dirty is False
        assert _restart(shared_file).word_wrap is False
    finally:
        stop()


def test_a_retry_that_fails_again_says_so(shared_file: Path, writer: _Writer) -> None:
    outcomes: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(outcomes.append)
    try:
        app = _start_with(shared_file, word_wrap=True)
        writer.fail_with = PermissionError("locked")
        app.settings.word_wrap = False
        assert app.save_settings() is False
        retry = [o for o in outcomes if not o.ok][-1].retry
        with pytest.raises(OSError):
            retry()
        assert app.settings_dirty is True
    finally:
        stop()


def test_another_instances_change_survives_queued_writes_and_a_revert(
    shared_file: Path, writer: _Writer
) -> None:
    first = _start_with(shared_file, word_wrap=True)
    second = _App()
    second.settings.theme = "dark" if second.settings.theme != "dark" else "system"
    assert second.save_settings()
    first.settings.word_wrap = False
    writer.hold_next = True
    first._queue_settings_save()
    assert writer.entered.wait(WAIT)
    first.settings.word_wrap = True
    first._queue_settings_save()
    writer.release.set()
    first.flush_settings_writes()
    after = _restart(shared_file)
    assert after.word_wrap is True
    assert after.theme == second.settings.theme  # the other instance's choice kept
    assert first.settings.theme != second.settings.theme  # and not adopted mid-session


# -- what the listener meets: the View command, Preferences, a restart ------------- #


class _Window:
    """The real View-menu handlers on a window with no wx behind it."""

    def __init__(self, app: _App) -> None:
        from quill.apps.lite_window_view import DocumentViewCommandsMixin

        self.app = app
        self.said: list[str] = []
        self.control = SimpleNamespace(SetFocus=lambda: None)
        self._view = DocumentViewCommandsMixin
        app.features = None
        app.applied = []  # what the editor was showing after each change
        app.reapply_settings = lambda: app.applied.append(app.settings.word_wrap)

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def toggle_wrap(self) -> None:
        self._view.cmd_toggle_wrap(self)

    def preferences(self, monkeypatch: pytest.MonkeyPatch, choose) -> list[bool]:
        """Open Preferences; *choose* edits like the window would, or cancels."""
        from quill.apps import lite_window_view
        from quill.apps.lite_preferences import PreferencesResult

        seen: list[bool] = []

        def edit(_parent, settings, **_kwargs):
            seen.append(settings.word_wrap)  # what the reopened window shows
            changed = choose(settings)
            return PreferencesResult(changed, False)

        monkeypatch.setattr(lite_window_view, "edit_preferences", edit)
        self._view.cmd_preferences(self)
        return seen


def test_wrap_toggled_twice_then_preferences_ok_cancel_and_restart(
    shared_file: Path, writer: _Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _start_with(shared_file, word_wrap=True)
    window = _Window(app)
    writer.hold_next = True
    window.toggle_wrap()  # off, its write held
    assert writer.entered.wait(WAIT)
    window.toggle_wrap()  # straight back on
    assert window.said == ["Word wrap off", "Word wrap on"]
    assert app.applied == [False, True]  # the editor followed each press
    writer.release.set()
    app.flush_settings_writes()
    assert _restart(shared_file).word_wrap is True

    def turn_off(settings) -> bool:
        settings.word_wrap = False
        return True

    seen = window.preferences(monkeypatch, turn_off)  # OK
    assert seen == [True]
    assert window.said[-1] == "Preferences saved"
    assert app.applied[-1] is False
    seen = window.preferences(monkeypatch, lambda _settings: False)  # Cancel or Escape
    assert seen == [False]  # the reopened window shows the saved choice
    assert window.said[-1] == "Preferences saved"  # nothing new claimed on Cancel
    app.flush_settings_writes()
    assert _restart(shared_file).word_wrap is False  # the next launch agrees


def test_preferences_ok_on_a_locked_file_is_never_called_saved(
    shared_file: Path, writer: _Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _start_with(shared_file, word_wrap=True)
    window = _Window(app)
    writer.fail_with = PermissionError("locked")

    def turn_off(settings) -> bool:
        settings.word_wrap = False
        return True

    window.preferences(monkeypatch, turn_off)
    assert "Preferences saved" not in window.said
    assert app.spoken == [persistence.SETTINGS_NOT_SAVED]
    assert app.applied[-1] is False  # still in use this session
    assert _restart(shared_file).word_wrap is True
    writer.fail_with = None
    window.preferences(monkeypatch, lambda _settings: False)  # reopening retries
    assert "Settings are now saved" in window.said
    assert _restart(shared_file).word_wrap is False
