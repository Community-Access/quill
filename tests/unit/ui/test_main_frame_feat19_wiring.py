"""Source-contract test for FEAT-19 external change watcher wiring in main_frame."""

from pathlib import Path


def test_feat19_imports_are_present() -> None:
    """FEAT-19 wiring imports external_change module."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # Core external_change imports must be present.
    assert "from quill.core.external_change import (" in source
    assert "ExternalChangeWatcher" in source
    assert "FileSnapshot" in source
    assert "ReloadAction" in source
    assert "decide_reload" in source


def test_feat19_watcher_tracking_initialized() -> None:
    """FEAT-19 wiring initializes watcher tracking fields."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # The watcher and timer are initialized in __init__.
    assert "self._external_change_watcher: ExternalChangeWatcher | None = None" in source
    assert "self._external_change_timer: object | None = None" in source


def test_feat19_start_watcher_method_exists() -> None:
    """FEAT-19 wiring has _start_external_change_watcher method."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    assert "def _start_external_change_watcher(self)" in source
    # The method creates a watcher.
    assert "ExternalChangeWatcher(self.document.path)" in source
    # The method primes the watcher.
    assert "self._external_change_watcher.prime(FileSnapshot.of(" in source
    # The method starts a timer for polling.
    assert "wx.Timer(self.frame)" in source


def test_feat19_stop_watcher_method_exists() -> None:
    """FEAT-19 wiring has _stop_external_change_watcher method."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    assert "def _stop_external_change_watcher(self)" in source
    # The method stops the timer.
    assert "self._external_change_timer.Stop()" in source


def test_feat19_reload_method_exists() -> None:
    """FEAT-19 wiring has _reload_from_disk_preserving_cursor method."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    assert "def _reload_from_disk_preserving_cursor(self)" in source
    # The method saves cursor position.
    assert "caret = self.editor.GetInsertionPoint()" in source
    # The method reloads from path.
    assert "self.document.path.read_text(" in source
    # The method restores cursor.
    assert "self.editor.SetInsertionPoint(capped_caret)" in source


def test_feat19_uses_decide_reload() -> None:
    """FEAT-19 wiring uses decide_reload to make reload decisions."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # The watcher polls and calls decide_reload.
    assert "decide_reload(" in source
    assert "buffer_dirty=self.document.modified" in source
    # Settings are passed to decide_reload.
    assert "watch_enabled=" in source
    assert "auto_reload_when_clean=" in source
    assert "prompt_on_conflict=" in source


def test_feat19_respects_reload_action() -> None:
    """FEAT-19 wiring respects ReloadAction from decide_reload."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # The watcher handles RELOAD action.
    assert "ReloadAction.RELOAD" in source
    assert "_reload_from_disk_preserving_cursor()" in source
    # The watcher handles prompt actions.
    assert "decision.needs_prompt" in source
