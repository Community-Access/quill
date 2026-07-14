from __future__ import annotations

import types
from pathlib import Path

import pytest

from quill.core import settings_registry as registry
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.menu_customization import MenuCustomization
from quill.core.settings import Settings, load_settings
from quill.ui.main_frame import MainFrame


class _Frame:
    pass


def _build_reset_everything_frame(answer: int) -> MainFrame:
    """A bare MainFrame wired for ``reset_all_to_factory_defaults``.

    ``answer`` is what the confirmation box returns (``_wx.YES`` to proceed).
    """
    frame = _build_frame()
    frame._wx = types.SimpleNamespace(YES=5, NO=6, ICON_WARNING=1, YES_NO=2, NO_DEFAULT=4)
    frame._show_message_box = lambda *a, **k: answer
    frame.keymap = {**DEFAULT_KEYMAP, "edit.find": "Ctrl+Alt+F"}  # customized
    frame._menu_customization = MenuCustomization(hidden_top=["edit"])  # customized
    frame._reset_calls: list[str] = []  # type: ignore[attr-defined]
    frame._set_keyboard_pack = lambda *a, **k: frame._reset_calls.append("pack")
    frame._reload_shortcuts_from_keymap = lambda: frame._reset_calls.append("reload")
    frame._report_startup_task_failure = lambda name: frame._reset_calls.append(f"fail:{name}")
    frame.features = types.SimpleNamespace(
        reset_to_essential_profile=lambda: frame._reset_calls.append("features")
    )
    return frame


def test_reset_everything_resets_all_subsystems_and_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _build_reset_everything_frame(answer=5)  # YES
    frame.settings = registry.set_value(frame.settings, "soft_wrap", not Settings().soft_wrap)

    frame.reset_all_to_factory_defaults()

    # Settings, keymap, menus, and feature profile are all back to factory.
    assert frame.settings == Settings()
    assert frame.keymap == DEFAULT_KEYMAP
    assert frame._menu_customization.is_customized() is False
    assert "features" in frame._reset_calls
    assert "reload" in frame._reset_calls
    assert frame._status_message == "Reset everything to factory defaults"
    # Settings were persisted as the clean factory delta.
    assert load_settings() == Settings()
    assert "fail:" not in "".join(frame._reset_calls)


def test_reset_everything_cancelled_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _build_reset_everything_frame(answer=6)  # NO
    frame.settings = registry.set_value(frame.settings, "soft_wrap", not Settings().soft_wrap)
    custom_settings = frame.settings

    frame.reset_all_to_factory_defaults()

    assert frame.settings == custom_settings  # untouched
    assert frame.keymap["edit.find"] == "Ctrl+Alt+F"  # untouched
    assert frame._reset_calls == []
    assert frame._status_message == "Reset everything cancelled"


def _build_notice_frame(mode: str) -> MainFrame:
    from quill.core.migration_backup import pop_recent_migrations

    pop_recent_migrations()  # clear any cross-test residue
    frame = _build_frame()
    frame.settings = Settings(migration_notice=mode)
    frame._recommended_update_summaries = ["Find returns to the conventional Ctrl+F."]
    frame._recommended_update_undo = {"edit.find": "Ctrl+Shift+Grave, Z"}
    frame._spoken: list[str] = []  # type: ignore[attr-defined]
    frame._announce_result = lambda m: frame._spoken.append(m)
    return frame


def test_migration_notice_announce_speaks_the_summary() -> None:
    frame = _build_notice_frame("announce")
    frame._surface_migration_notice()
    assert frame._spoken and "Ctrl+F" in frame._spoken[0]


def test_migration_notice_silent_says_nothing() -> None:
    frame = _build_notice_frame("silent")
    frame._surface_migration_notice()
    assert frame._spoken == []


def test_undo_recommended_keymap_updates_restores_prior_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _build_frame()
    frame.keymap = {**DEFAULT_KEYMAP, "edit.find": "Ctrl+F"}  # post recommended update
    frame._recommended_update_undo = {"edit.find": "Ctrl+Alt+F"}  # the prior binding
    frame._recommended_update_summaries = ["x"]
    frame._reload_shortcuts_from_keymap = lambda: None
    frame._announce_result = lambda m: None

    frame.undo_recommended_keymap_updates()

    assert frame.keymap["edit.find"] == "Ctrl+Alt+F"  # restored
    assert frame._recommended_update_undo == {}  # consumed


def _build_frame() -> MainFrame:
    """Build a bare MainFrame with the side-effect methods stubbed out.

    The tabbed Settings dialog funnels OK, Import, and Reset through
    ``_settings_dialog_apply_refresh``; these tests exercise that shared path
    and the registry round-trip without constructing real wx widgets.
    """
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame.settings = Settings()
    frame._status_message = ""
    frame._refresh_calls = []  # type: ignore[attr-defined]

    frame._set_status = lambda message: setattr(frame, "_status_message", message)
    # Record every side effect the apply path is expected to run.
    for name in (
        "_apply_theme",
        "toggle_spellcheck_as_you_type",
        "_apply_ai_menu_enabled",
        "_refresh_ai_status",
        "_apply_soft_wrap",
        "_rebuild_tab_host",
        "_build_menu",
        "set_dirty_title_style",
        "_refresh_title",
    ):
        setattr(
            frame,
            name,
            (lambda _n: lambda *a, **k: frame._refresh_calls.append(_n))(name),
        )
    return frame


def test_apply_refresh_saves_and_runs_side_effects(monkeypatch) -> None:
    frame = _build_frame()
    saved: list[Settings] = []
    monkeypatch.setattr("quill.ui.main_frame.save_settings", lambda s: saved.append(s))

    frame._settings_dialog_apply_refresh("Updated settings")

    assert saved == [frame.settings]
    assert frame._status_message == "Updated settings"
    # The headline refreshers must all fire so the UI stays consistent.
    for expected in ("_apply_theme", "_build_menu", "_rebuild_tab_host", "_refresh_title"):
        assert expected in frame._refresh_calls


def test_reset_all_returns_factory_defaults() -> None:
    frame = _build_frame()
    frame.settings = registry.set_value(frame.settings, "soft_wrap", not Settings().soft_wrap)

    frame.settings = registry.reset_all()

    assert frame.settings == Settings()


def test_set_value_round_trip_normalizes() -> None:
    settings = Settings()
    # recent_files_limit clamps to its 1..50 range via Settings.from_dict.
    updated = registry.set_value(settings, "recent_files_limit", 9999)

    assert updated.recent_files_limit <= 50


def test_export_import_settings_round_trip() -> None:
    settings = registry.set_value(Settings(), "theme", "dark")
    exported = registry.export_settings(settings)

    restored = registry.import_settings(exported)

    assert restored.theme == "dark"
    assert exported["schema_version"] == registry.SCHEMA_VERSION


def test_suggested_save_basename_first_line_branches() -> None:
    import types
    from pathlib import Path as _Path

    frame = MainFrame.__new__(MainFrame)
    frame.editor = types.SimpleNamespace(GetValue=lambda: "# Meeting Notes\nbody")

    # Untitled + setting on -> first-line title.
    frame.document = types.SimpleNamespace(path=None, name="Untitled")
    frame.settings = Settings(first_line_as_title=True)
    assert frame._suggested_save_basename("Untitled") == "Meeting Notes"

    # Untitled + setting off -> the fallback.
    frame.settings = Settings(first_line_as_title=False)
    assert frame._suggested_save_basename("Untitled") == "Untitled"
    assert frame._suggested_save_basename() == ""

    # Titled document -> its own stem, regardless of the setting.
    frame.document = types.SimpleNamespace(path=_Path("/tmp/report.md"), name="report.md")
    frame.settings = Settings(first_line_as_title=True)
    assert frame._suggested_save_basename("x") == "report"
