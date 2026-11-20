"""Back Up and Restore Settings in QUILL Lite: what stays on this computer.

plan.md (settings review, portable settings boundaries):

* an export carried ``startup_folder`` -- a folder on the source PC -- into
  the restored settings on another one;
* a QUILL backup (``app="quill"``) was imported by QUILL Lite without a word:
  109 settings, including theme and find-wrap choices. Decision for this fix:
  refuse it, and say plainly it came from another app in the family;
* a restore rebuilt everything from defaults, so the destination's own recent
  files, session and window size were wiped by the restore itself.

These run the real Restore Settings command on a real file.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("wx")


def _restore(win, monkeypatch, source) -> None:
    import wx

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


def test_the_startup_folder_is_never_exported(lite_window) -> None:
    from quill.core.lite.settings import export_portable

    win = lite_window("", cursor=0)
    win.app.settings.startup_folder = r"C:\OnlyOnSourcePC\Writing"
    payload, report = export_portable(win.app.settings)
    assert "startup_folder" not in payload["settings"]
    assert "startup_folder" in report.local


def test_an_old_file_with_a_startup_folder_does_not_bring_it_in(
    lite_window, tmp_path, monkeypatch
) -> None:
    win = lite_window("", cursor=0)
    win.app.settings.startup_folder = r"D:\HereOnThisPC"
    source = tmp_path / "old.qsf"
    source.write_text(
        json.dumps({
            "schema_version": 1,
            "app": "quilllite",
            "settings": {"font_size": 19, "startup_folder": r"C:\OnlyOnSourcePC\Writing"},
        }),
        encoding="utf-8",
    )
    _restore(win, monkeypatch, source)
    assert win.app.settings.font_size == 19
    assert win.app.settings.startup_folder == r"D:\HereOnThisPC"


def test_a_restore_keeps_this_computers_local_settings(lite_window, tmp_path, monkeypatch) -> None:
    win = lite_window("", cursor=0)
    win.app.settings.recent_files = ["C:/here/notes.txt"]
    win.app.settings.session_files = ["C:/here/open.txt"]
    win.app.settings.window_width = 1111
    source = tmp_path / "from-elsewhere.qsf"
    source.write_text(
        json.dumps({"schema_version": 1, "app": "quilllite", "settings": {"font_size": 22}}),
        encoding="utf-8",
    )
    _restore(win, monkeypatch, source)
    assert win.app.settings.font_size == 22
    assert win.app.settings.recent_files == ["C:/here/notes.txt"]
    assert win.app.settings.session_files == ["C:/here/open.txt"]
    assert win.app.settings.window_width == 1111


def test_a_quill_backup_is_refused_with_a_plain_reason(lite_window, tmp_path, monkeypatch) -> None:
    from quill.core.settings import Settings as QuillSettings
    from quill.core.settings_registry import export_portable_settings_with_report

    win = lite_window("", cursor=0)
    win.app.settings.font_size = 21
    before = win.app.settings.theme
    quill_settings = QuillSettings()
    payload, _report = export_portable_settings_with_report(quill_settings)
    assert payload["app"] == "quill"
    source = tmp_path / "quill-backup.qsf"
    source.write_text(json.dumps(payload), encoding="utf-8")
    _restore(win, monkeypatch, source)
    assert win.app.settings.font_size == 21
    assert win.app.settings.theme == before
    assert win.app.queued_settings == 0
    said = win.announcements[-1]
    assert "QUILL" in said and "another app" in said and "Nothing was changed" in said


def test_a_file_without_an_envelope_still_restores(lite_window, tmp_path, monkeypatch) -> None:
    win = lite_window("", cursor=0)
    source = tmp_path / "bare.qsf"
    source.write_text(json.dumps({"font_size": 17}), encoding="utf-8")
    _restore(win, monkeypatch, source)
    assert win.app.settings.font_size == 17
