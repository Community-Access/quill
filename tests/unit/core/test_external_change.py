"""External file-change detection and safe-reload decisions (FEAT-19)."""

from __future__ import annotations

from pathlib import Path

from quill.core.external_change import (
    CHANGE_DELETED,
    CHANGE_MODIFIED,
    CHANGE_NONE,
    ExternalChangeWatcher,
    FileSnapshot,
    ReloadAction,
    classify_change,
    decide_reload,
)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_snapshot_of_missing_file_does_not_exist(tmp_path: Path) -> None:
    snap = FileSnapshot.of(tmp_path / "nope.txt")
    assert snap.exists is False
    assert snap.size == 0
    assert snap.digest == ""


def test_snapshot_same_content_ignores_mtime(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    _write(target, "hello")
    first = FileSnapshot.of(target)
    # Rewrite identical bytes (a no-op save) — content hash is unchanged.
    _write(target, "hello")
    second = FileSnapshot.of(target)
    assert first.same_content_as(second) is True


def test_classify_change_detects_modification(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    _write(target, "one")
    before = FileSnapshot.of(target)
    _write(target, "two")
    after = FileSnapshot.of(target)
    assert classify_change(before, after) == CHANGE_MODIFIED


def test_classify_change_detects_deletion(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    _write(target, "one")
    before = FileSnapshot.of(target)
    target.unlink()
    after = FileSnapshot.of(target)
    assert classify_change(before, after) == CHANGE_DELETED


def test_classify_change_none_when_identical(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    _write(target, "stable")
    before = FileSnapshot.of(target)
    after = FileSnapshot.of(target)
    assert classify_change(before, after) == CHANGE_NONE


def test_watcher_reports_change_once_then_settles(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    _write(target, "one")
    watcher = ExternalChangeWatcher(target)
    assert watcher.poll() == CHANGE_NONE
    _write(target, "two")
    assert watcher.poll() == CHANGE_MODIFIED
    # The baseline advanced, so the same change is not reported again.
    assert watcher.poll() == CHANGE_NONE


def test_watcher_reports_deletion(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    _write(target, "one")
    watcher = ExternalChangeWatcher(target)
    target.unlink()
    assert watcher.poll() == CHANGE_DELETED
    assert watcher.poll() == CHANGE_NONE


def test_decide_reload_clean_buffer_asks_rather_than_replacing() -> None:
    """Reversed 2026-09-18 (bad.md F5): a clean tab used to be replaced in place.

    That is right for a text file a build regenerates and wrong for everything
    else -- a .docx rewritten by Word came back as its own bytes decoded into
    replacement characters, marked clean, with nothing said. The blanket
    ``auto_reload_when_clean`` switch below is how somebody asks for the old
    behaviour back for every format at once.
    """
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=False)
    assert decision.action is ReloadAction.PROMPT_CLEAN
    assert decision.needs_prompt is True


def test_decide_reload_clean_buffer_reloads_in_place_under_the_blanket_switch() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=False, auto_reload_when_clean=True)
    assert decision.action is ReloadAction.RELOAD
    assert decision.announcement == "Reloaded from disk."
    assert decision.needs_prompt is False


def test_decide_reload_dirty_buffer_prompts_conflict() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=True, file_name="notes.md")
    assert decision.action is ReloadAction.PROMPT_CONFLICT
    assert decision.needs_prompt is True
    assert "unsaved edits" in decision.announcement
    assert "notes.md" in decision.announcement


def test_decide_reload_deletion_prompts_and_keeps_text() -> None:
    decision = decide_reload(CHANGE_DELETED, buffer_dirty=False)
    assert decision.action is ReloadAction.PROMPT_DELETED
    assert "deleted" in decision.announcement.lower()


def test_decide_reload_quiet_when_watch_disabled() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=False, watch_enabled=False)
    assert decision.action is ReloadAction.NONE
    assert decision.announcement == ""


def test_decide_reload_clean_prompts_when_auto_reload_off() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=False, auto_reload_when_clean=False)
    assert decision.action is ReloadAction.PROMPT_CLEAN
    assert decision.needs_prompt is True


def test_decide_reload_conflict_silent_when_prompt_off() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=True, prompt_on_conflict=False)
    assert decision.action is ReloadAction.NONE


def test_decide_reload_no_change_is_quiet() -> None:
    decision = decide_reload(CHANGE_NONE, buffer_dirty=True)
    assert decision.action is ReloadAction.NONE
    assert decision.announcement == ""
