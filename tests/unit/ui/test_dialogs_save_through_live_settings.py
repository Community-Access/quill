"""QUILL dialogs change the main window's settings, not a copy it never sees.

The family settings audit (2026-11-20) found dialogs that loaded a fresh copy
of QUILL's settings file, changed it and saved it. The main window kept its
own, older settings object, so the change did nothing until a restart -- and
the window's next save (any toggle) wrote the old value back over the file.

Each test does what the person does: the main window is open, the dialog
changes a setting, the feature reads it straight away, the window saves for
some other reason, and the next launch reloads from disk. The change must
survive all of it. A gate below keeps the shape from coming back.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import live_settings
from quill.core.settings import load_settings, save_settings

ROOT = Path(__file__).resolve().parents[3]


class _MainWindow:
    """What a QUILL main window is to its settings: the owner of a live copy."""

    def __init__(self) -> None:
        self.settings = load_settings()


@pytest.fixture
def main_window(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    live_settings._forget()
    window = _MainWindow()
    live_settings.register(window)
    yield window
    live_settings._forget()


def _next_save_and_relaunch(window: _MainWindow):
    """The window saves for its own reasons; then the next launch reads the file."""
    save_settings(window.settings)
    return load_settings()


def test_vision_prompt_manager_change_reaches_the_main_window(
    wx_session_app, main_window, monkeypatch
) -> None:
    from quill.ui.vision_prompt_manager_dialog import VisionPromptManagerDialog

    # Opened from the Assistant's AI settings, which hands it a fresh copy.
    dialog = VisionPromptManagerDialog(None, load_settings())
    monkeypatch.setattr(dialog.dialog, "EndModal", lambda _code: None)
    builtin = "detailed"
    dialog._disabled.add(builtin)
    dialog._on_close(None)
    dialog.dialog.Destroy()

    assert builtin in main_window.settings.vision_disabled_builtin_styles  # in effect now
    assert builtin in _next_save_and_relaunch(main_window).vision_disabled_builtin_styles


def test_chapter_nudge_step_reaches_the_main_window(main_window) -> None:
    from quill.core.speech.chapters import NUDGE_STEPS_MS
    from quill.ui.audio_studio.chapter_workbench_edits import ChapterEditsMixin

    wanted = NUDGE_STEPS_MS[-1]
    assert main_window.settings.audio_studio_chapter_nudge_ms != wanted
    workbench = SimpleNamespace(
        _step_choice=SimpleNamespace(GetSelection=lambda: len(NUDGE_STEPS_MS) - 1)
    )
    ChapterEditsMixin._on_step_changed(workbench)

    assert main_window.settings.audio_studio_chapter_nudge_ms == wanted
    assert _next_save_and_relaunch(main_window).audio_studio_chapter_nudge_ms == wanted


def test_ai_hub_services_reach_the_main_window(main_window, monkeypatch) -> None:
    from quill.ui.ai_hub_dialog import AIHubDialog

    monkeypatch.setattr("quill.core.datalab_ocr.save_datalab_api_key", lambda _key: True)
    said: list[str] = []
    hub = SimpleNamespace(
        _services_values=lambda: {
            "enabled": True,
            "endpoint": "https://ocr.example.test",
            "mode": "accurate",
            "output": "markdown",
            "paginate": True,
            "key": "",
        },
        _announce=said.append,
        _refresh_services_status=lambda: None,
    )
    AIHubDialog._on_save_services(hub, None)

    assert main_window.settings.datalab_enabled is True
    assert main_window.settings.datalab_endpoint == "https://ocr.example.test"
    reloaded = _next_save_and_relaunch(main_window)
    assert (reloaded.datalab_enabled, reloaded.datalab_endpoint) == (
        True,
        "https://ocr.example.test",
    )


def test_with_no_window_open_a_change_still_reaches_the_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    live_settings._forget()
    live_settings.change_and_save(lambda s: setattr(s, "datalab_paginate", True))
    assert load_settings().datalab_paginate is True


def test_every_window_that_owns_quills_settings_registers(monkeypatch, tmp_path) -> None:
    """MainFrame and every AppShellFrame install the persistence reporter, which
    registers the window; a dialog's change then reaches that window's copy."""
    from quill.ui import persistence_reporting

    for rel in ("quill/ui/main_frame_activity.py", "quill/ui/app_shell.py"):
        assert "persistence_reporting import install" in (ROOT / rel).read_text("utf-8"), rel
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    live_settings._forget()
    window = _MainWindow()
    stop = persistence_reporting.install(window)
    try:
        assert live_settings.live_copies() == [window.settings]
        assert live_settings.live_copies()[0] is window.settings
    finally:
        stop()
        live_settings._forget()


# -- the gate ------------------------------------------------------------------

#: A function here may load QUILL's settings fresh and save them, with the reason.
_ALLOWED = {
    # Studio's capture keys: re-reads the file so another family app's keys
    # saved meanwhile are kept, then makes that copy the window's own
    # (``self.settings = fresh``) -- the "refresh the frame" half of the rule.
    "quill/apps/studio_capture_hotkeys.py::open_capture_hotkeys",
    # QUILL Lite's Sound Scheme: Lite holds no copy of QUILL's settings in
    # memory (its window keeps Lite's own), so the copy it loads is the only
    # one, and it hands that saved copy straight to the sound manager.
    "quill/apps/lite_window_view.py::cmd_sound_scheme",
}


def _settings_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    loads, saves = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "quill.core.settings":
            for alias in node.names:
                name = alias.asname or alias.name
                if alias.name == "load_settings":
                    loads.add(name)
                elif alias.name == "save_settings":
                    saves.add(name)
    return loads, saves


def _fresh_copy_savers() -> set[str]:
    found: set[str] = set()
    for folder in ("quill/ui", "quill/apps"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            loads, saves = _settings_aliases(tree)
            if not loads or not saves:
                continue
            for func in ast.walk(tree):
                if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
                names = {c.func.id for c in calls if isinstance(c.func, ast.Name)}
                fresh = any(
                    isinstance(c.func, ast.Name) and c.func.id in loads and not c.args
                    for c in calls
                )
                if fresh and names & saves:
                    found.add(f"{path.relative_to(ROOT).as_posix()}::{func.name}")
    return found


def test_no_dialog_saves_a_fresh_copy_of_quills_settings() -> None:
    """Load-change-save on a copy is the shape that lost these choices.

    Change QUILL's settings with ``quill.core.live_settings.change_and_save``
    (or the window's own ``settings``), so the window sees it and its next
    save keeps it.
    """
    assert _fresh_copy_savers() - _ALLOWED == set()
    assert _ALLOWED <= _fresh_copy_savers(), "an allowance outlived its function"
