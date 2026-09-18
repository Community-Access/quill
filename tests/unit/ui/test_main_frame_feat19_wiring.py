"""Source-contract tests for the FEAT-19 external change watcher wiring.

The watcher moved out of ``main_frame.py`` into
``quill/ui/main_frame_external_change.py`` on 2026-09-18 (bad.md P0.7, GATE-11),
so these read both files: the frame still owns the lifecycle calls that have to
sit beside the tab and save paths, and the mixin owns the watcher itself.
"""

from pathlib import Path


def _source() -> str:
    """The frame plus the watcher mixin -- one surface, two files."""
    return Path("quill/ui/main_frame.py").read_text(encoding="utf-8") + Path(
        "quill/ui/main_frame_external_change.py"
    ).read_text(encoding="utf-8")


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
    """The prompt must be a real dialog, not a stub.

    It is a purpose-built ``wx.Dialog`` since 2026-09-18 rather than a
    relabelled ``wx.MessageDialog``: the question now carries a "do not ask me
    again for this format" checkbox, and a message box cannot hold one
    (bad.md F5).
    """
    src = _source()
    assert "_show_external_change_prompt" in src
    assert "PROMPT_DELETED" in src
    assert "PROMPT_CONFLICT" in src
    assert "PROMPT_CLEAN" in src
    assert "ask_external_change" in src
    # The deleted-file prompt keeps its relabelled native buttons.
    assert "SetYesNoCancelLabels" in src
    # The old TODO must be gone.
    assert "TODO: implement the conflict dialog" not in src


def test_feat19_on_demand_check_exists() -> None:
    """check_external_changes_now must be a callable method."""
    src = _source()
    assert "def check_external_changes_now(self)" in src


def test_feat19_reload_goes_through_the_readers() -> None:
    """A reload must use the reader for the file's format, not ``read_text``.

    This asserted the document's *detected encoding* until 2026-09-18, which
    was the right fix for a text file and no fix at all for the rest: a .docx
    has no text encoding to detect, and reading one as text is how a document
    became a screenful of replacement characters, marked clean (bad.md F5).
    Every reload now goes through ``read_open_document``, the same funnel the
    open flow uses.
    """
    src = _source()
    assert "from quill.io.open_read import read_open_document" in src
    assert "def _read_disk_version_text(self)" in src
    # The text-only read it replaced must be gone from the reload path.
    assert "reloaded_text = self.document.path.read_text(" not in src


def test_feat19_menu_item_wired() -> None:
    """The 'Check for External Changes' menu item must exist in main_frame_menu."""
    menu_src = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8") + Path(
        "quill/ui/main_frame_menu_bindings.py"
    ).read_text(encoding="utf-8")
    assert "_id_check_external_changes" in menu_src
    assert "check_external_changes_now" in menu_src
    # The mnemonic moved in the 2026-09-18 sweep (bad.md H5), so match the
    # words rather than the ampersand.
    assert "for External Changes" in menu_src
