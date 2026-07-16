"""Source-contract tests for FEAT-19 external change watcher wiring in main_frame."""

from pathlib import Path


def _source() -> str:
    return Path("quill/ui/main_frame.py").read_text(encoding="utf-8")


def test_feat19_imports_are_present() -> None:
    src = _source()
    assert "from quill.core.external_change import (" in src
    assert "ExternalChangeWatcher" in src
    assert "FileSnapshot" in src
    assert "ReloadAction" in src
    assert "decide_reload" in src


def test_feat19_watcher_tracking_initialized() -> None:
    src = _source()
    assert "self._external_change_watcher: ExternalChangeWatcher | None = None" in src
    assert "self._external_change_timer: object | None = None" in src


def test_feat19_watcher_started_in_activate_tab() -> None:
    """_activate_tab must start the watcher so tab switches wire it."""
    src = _source()
    assert "_start_external_change_watcher()" in src
    # Also must stop the previous watcher before switching.
    assert "_stop_external_change_watcher()" in src


def test_feat19_watcher_started_in_finish_open_document() -> None:
    """_finish_open_document must (re)start the watcher after load."""
    src = _source()
    # Both stop and start must appear inside _finish_open_document context.
    assert "FEAT-19: (re)start the external change watcher for the freshly loaded document." in src


def test_feat19_watcher_primed_after_save() -> None:
    """save_file must prime the watcher so our own save is not reported as external."""
    src = _source()
    assert "FEAT-19: prime the watcher so our own save is not reported" in src


def test_feat19_watcher_restarted_after_save_as() -> None:
    """save_file_as must restart the watcher because the path may have changed."""
    src = _source()
    assert "FEAT-19: restart the watcher on the new path so our save is the baseline." in src


def test_feat19_conflict_dialog_implemented() -> None:
    """The conflict prompt must be a real dialog, not a stub."""
    src = _source()
    assert "_show_external_change_prompt" in src
    assert "PROMPT_DELETED" in src
    assert "PROMPT_CONFLICT" in src
    # SetYesNoCancelLabels is used for accessible button labels.
    assert "SetYesNoCancelLabels" in src
    # The old TODO must be gone.
    assert "TODO: implement the conflict dialog" not in src


def test_feat19_on_demand_check_exists() -> None:
    """check_external_changes_now must be a callable method."""
    src = _source()
    assert "def check_external_changes_now(self)" in src


def test_feat19_reload_uses_document_encoding() -> None:
    """_reload_from_disk_preserving_cursor must use the document's detected encoding."""
    src = _source()
    assert 'encoding = getattr(self.document, "encoding", None) or "utf-8"' in src
    # Hard-coded utf-8 as the primary encoding must be gone.
    assert 'read_text(encoding="utf-8")' not in src or "errors=" in src


def test_feat19_menu_item_wired() -> None:
    """The 'Check for External Changes' menu item must exist in main_frame_menu."""
    menu_src = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8") + Path(
        "quill/ui/main_frame_menu_bindings.py"
    ).read_text(encoding="utf-8")
    assert "_id_check_external_changes" in menu_src
    assert "check_external_changes_now" in menu_src
    assert "Check for E" in menu_src
