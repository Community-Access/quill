"""Back Up Settings and Restore Settings in QUILL Lite (#1501).

The point of the feature is that the file lands on a *different* machine, so the
tests are about what does and does not cross over -- and about the sentence said
afterwards, because a backup that quietly differs from the machine it came from
is exactly what the reporter was trying to avoid.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("wx")


def _backup_file(tmp_path, window):
    """Run a backup to a real file and return the path."""
    import wx

    from quill.core.lite.settings import export_portable

    payload, _report = export_portable(window.app.settings)
    target = tmp_path / "config.qsf"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert wx is not None
    return target


def test_a_backup_carries_the_preferences(lite_window, tmp_path) -> None:
    win = lite_window("", cursor=0)
    win.app.settings.font_size = 21
    win.app.settings.word_wrap = False
    payload = json.loads(_backup_file(tmp_path, win).read_text(encoding="utf-8"))
    assert payload["settings"]["font_size"] == 21
    assert payload["settings"]["word_wrap"] is False
    assert payload["app"] == "quilllite"


def test_a_backup_leaves_this_computer_behind(lite_window, tmp_path) -> None:
    """Recent files, the restored session and the window geometry describe one
    desk. Carrying them is how a restore points the app at files that are not
    there."""
    win = lite_window("", cursor=0)
    win.app.settings.recent_files = ["C:/only-here.txt"]
    win.app.settings.window_width = 1234
    payload = json.loads(_backup_file(tmp_path, win).read_text(encoding="utf-8"))
    assert "recent_files" not in payload["settings"]
    assert "window_width" not in payload["settings"]


def test_restoring_applies_the_file_and_says_what_was_different(lite_window, tmp_path) -> None:
    from quill.core.lite.settings import import_portable

    win = lite_window("", cursor=0)
    win.app.settings.font_size = 21
    source = _backup_file(tmp_path, win)
    raw = json.loads(source.read_text(encoding="utf-8"))
    restored, report = import_portable(raw)
    assert restored.font_size == 21
    assert "settings imported" in report.summary()


def test_an_older_backup_reports_what_has_been_added_since(lite_window) -> None:
    """The honest half of the "intelligent wizard" ask: a count and a list."""
    from quill.core.lite.settings import import_portable

    restored, report = import_portable({"settings": {"font_size": 15}})
    assert restored.font_size == 15
    assert report.added_since
    assert "added since this file was written" in report.summary()


def test_a_file_with_nothing_recognisable_changes_nothing(
    lite_window, tmp_path, monkeypatch
) -> None:
    """Resetting every setting to its default on the strength of the wrong file
    is the worst available reading of what the user meant."""
    import wx

    win = lite_window("", cursor=0)
    win.app.settings.font_size = 21
    source = tmp_path / "wrong.qsf"
    source.write_text(json.dumps({"settings": {"nothing_we_know": 1}}), encoding="utf-8")

    class _Dialog:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def GetPath(self):
            return str(source)

    monkeypatch.setattr(wx, "FileDialog", _Dialog)
    monkeypatch.setattr(type(win), "_show_lite_modal", lambda self, d, label: wx.ID_OK)
    win.cmd_restore_settings()
    assert win.app.settings.font_size == 21
    assert "Nothing was changed" in win.announcements[-1]


def test_cancelling_a_restore_changes_nothing(lite_window, monkeypatch) -> None:
    import wx

    win = lite_window("", cursor=0)
    win.app.settings.font_size = 21

    class _Dialog:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def GetPath(self):
            raise AssertionError("must not be read after Cancel")

    monkeypatch.setattr(wx, "FileDialog", _Dialog)
    monkeypatch.setattr(type(win), "_show_lite_modal", lambda self, d, label: wx.ID_CANCEL)
    win.cmd_restore_settings()
    win.cmd_backup_settings()
    assert win.app.settings.font_size == 21
    assert win.announcements == []


@pytest.mark.parametrize("closing", [False, True])
def test_failed_settings_save_is_reported_and_retry_clears_state(monkeypatch, caplog, closing):
    from quill.apps import lite_settings_persistence as persistence

    class App(persistence.LiteSettingsPersistenceMixin):
        pass

    app = App()
    spoken = []
    queued = []
    touched = []
    app.settings = SimpleNamespace(word_wrap=False)
    app.shutting_down = closing
    app.frames = [SimpleNamespace(_touch_status=lambda: touched.append(True))]
    app.voice = SimpleNamespace(speak=spoken.append)
    monkeypatch.setattr(persistence.wx, "CallAfter", queued.append)

    def fail(_settings):
        raise OSError("private document name must not be logged")

    monkeypatch.setattr(persistence.settings_mod, "save", fail)
    assert app.save_settings() is False
    assert app.settings_dirty
    assert app.settings.word_wrap is False
    for callback in queued:
        callback()
    assert spoken == [persistence.SETTINGS_NOT_SAVED]
    assert touched == ([] if closing else [True])
    assert "private document name" not in caplog.text
    monkeypatch.setattr(persistence.settings_mod, "save", lambda _settings: None)
    assert app.save_settings() is True
    assert not app.settings_dirty


def test_settings_warning_survives_status_expiry_and_other_messages(lite_window):
    from quill.apps.lite_settings_persistence import SETTINGS_NOT_SAVED
    from quill.apps.lite_window_status import DocumentStatusMixin

    win = lite_window("text")
    win.app.settings_dirty = True
    assert DocumentStatusMixin._live_status_message(win) == SETTINGS_NOT_SAVED


def test_preferences_does_not_claim_failed_settings_were_saved(lite_window, monkeypatch):
    from quill.apps import lite_window_view
    from quill.apps.lite_preferences import PreferencesResult

    win = lite_window("text")
    monkeypatch.setattr(win.app, "save_settings", lambda: False)
    monkeypatch.setattr(
        lite_window_view, "edit_preferences", lambda *args, **kwargs: PreferencesResult(True, False)
    )
    win.cmd_preferences()
    assert "Preferences saved" not in win.announcements
    assert win.app.reapplied == 1


def test_reopening_preferences_retries_dirty_settings(lite_window, monkeypatch):
    from quill.apps import lite_window_view
    from quill.apps.lite_preferences import PreferencesResult

    win = lite_window("text")
    win.app.settings_dirty = True
    monkeypatch.setattr(
        lite_window_view,
        "edit_preferences",
        lambda *args, **kwargs: PreferencesResult(False, False),
    )
    win.cmd_preferences()
    assert win.app.saved_settings == 1
    assert "Settings are now saved" in win.announcements


def test_real_settings_write_recovers_after_storage_failure(monkeypatch, tmp_path):
    from quill.apps import lite_settings_persistence as persistence

    class App(persistence.LiteSettingsPersistenceMixin):
        pass

    app = App()
    app.settings = persistence.settings_mod.Settings(word_wrap=False)
    app.shutting_down = False
    app.frames = []
    spoken = []
    queued = []
    app.voice = SimpleNamespace(speak=spoken.append)
    monkeypatch.setattr(persistence.wx, "CallAfter", queued.append)
    unavailable = tmp_path / "not-a-directory"
    unavailable.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(
        persistence.settings_mod, "settings_path", lambda: unavailable / "settings.json"
    )
    assert app.save_settings() is False
    assert app.settings_dirty
    target = tmp_path / "restored" / "settings.json"
    monkeypatch.setattr(persistence.settings_mod, "settings_path", lambda: target)
    assert app.save_settings() is True
    assert persistence.settings_mod.load(target).word_wrap is False
    for callback in queued:
        callback()
    assert spoken == []
    assert not app.settings_dirty


def test_shutdown_flushes_pending_settings_warning_once(monkeypatch):
    from quill.apps import lite_settings_persistence as persistence
    from quill.apps.lite import QuillLiteApp

    class App(persistence.LiteSettingsPersistenceMixin):
        pass

    app = App()
    app.settings = SimpleNamespace(word_wrap=False)
    app.shutting_down = False
    app.frames = []
    spoken = []
    queued = []
    app.voice = SimpleNamespace(speak=spoken.append)
    monkeypatch.setattr(persistence.wx, "CallAfter", queued.append)

    def fail(_settings):
        raise PermissionError("read only")

    monkeypatch.setattr(persistence.settings_mod, "save", fail)
    assert app.save_settings() is False
    assert app.save_settings() is False
    assert len(queued) == 1
    QuillLiteApp.stop_background_sources(app)
    QuillLiteApp.stop_background_sources(app)
    for callback in queued:
        callback()
    assert spoken == [persistence.SETTINGS_NOT_SAVED]
