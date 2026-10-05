"""QUILL Lite watches each open document for other programs' changes.

The handlers are the shipped ``DocumentDiskWatchMixin`` on the usual
``lite_window`` stub; the clock is driven by hand (``_poll_disk_watch`` is what
the shared timer calls), and the File Changed on Disk question is patched where
the mixin imports it. Files are real, with modification times set explicitly so
nothing depends on the file system's clock resolution.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from quill.apps.lite_window_watch import DocumentDiskWatchMixin
from quill.ui.external_change_dialog import KEEP, RELOAD, SAVE_AS, ExternalChangeAnswer

_TEXT = "one\ntwo\nthree\n"


def _write(path: Path, text: str, mtime: int) -> None:
    path.write_bytes(text.encode("utf-8"))
    os.utime(path, ns=(mtime, mtime))


@pytest.fixture
def watched(lite_window: Any, tmp_path: Path) -> Any:
    """A window holding plan.md, exactly as it is on disk, caret on line 3."""
    win = lite_window(_TEXT)
    win.__class__ = type("WatchedWindow", (DocumentDiskWatchMixin, type(win)), {})
    path = tmp_path / "plan.md"
    _write(path, _TEXT, 1_000_000_000)
    win.path = path
    win._remember_disk_baseline()
    win.control.SetInsertionPoint(_TEXT.index("three"))
    return win


class _Asked(list):  # type: ignore[type-arg]
    """Every File Changed on Disk question; ``answer`` is what each gets back."""

    answer = ExternalChangeAnswer(KEEP)


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> _Asked:
    calls = _Asked()

    def ask(_parent: Any, name: str, **kwargs: Any) -> ExternalChangeAnswer:
        calls.append({"name": name, **kwargs})
        return calls.answer

    monkeypatch.setattr("quill.ui.external_change_dialog.ask_external_change", ask)
    return calls


def _rewrite(win: Any, text: str, mtime: int = 2_000_000_000) -> None:
    _write(Path(win.path), text, mtime)


def test_a_clean_document_reloads_quietly_keeping_the_caret_line(
    watched: Any, asked: _Asked
) -> None:
    watched.app.settings.external_change_auto_reload_when_clean = True
    _rewrite(watched, "uno\ndos\ntres\ncuatro\n")

    watched._poll_disk_watch()

    assert watched.control.GetValue() == "uno\ndos\ntres\ncuatro\n"
    assert watched.control.GetInsertionPoint() == len("uno\ndos\n")
    assert watched.modified is False
    assert watched.announcements[-1] == "Reloaded plan.md: changed by another program."
    assert asked == []
    # Once: the next tick has nothing new to say.
    said = len(watched.announcements)
    watched._poll_disk_watch()
    assert len(watched.announcements) == said


def test_by_default_a_change_is_asked_about_with_keep_mine_first(
    watched: Any, asked: _Asked
) -> None:
    _rewrite(watched, "rewritten by an assistant\n")

    watched._poll_disk_watch()

    assert len(asked) == 1
    assert asked[0]["name"] == "plan.md"
    assert asked[0]["alternative"] == SAVE_AS
    assert asked[0]["default_keep"] is True
    # Keep Mine (the default answer) leaves the text alone ...
    assert watched.control.GetValue() == _TEXT
    # ... and is never asked again for the same change, by the watcher or by Save.
    watched._poll_disk_watch()
    assert len(asked) == 1


def test_keep_mine_lets_save_write_without_a_second_question(
    watched: Any, asked: _Asked, monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("Save asked about a change already answered")

    monkeypatch.setattr("quill.ui.save_conflict_dialog.ask_save_conflict", never)
    _rewrite(watched, "theirs\n")
    watched._poll_disk_watch()
    assert watched.save() is True
    assert Path(watched.path).read_text(encoding="utf-8").replace("\r\n", "\n") == _TEXT


def test_unsaved_edits_are_asked_about_and_reload_replaces_them(
    watched: Any, asked: _Asked
) -> None:
    watched.app.settings.external_change_auto_reload_when_clean = True
    watched.modified = True
    asked.answer = ExternalChangeAnswer(RELOAD)
    _rewrite(watched, "theirs\n")

    watched._poll_disk_watch()

    assert asked and asked[0]["buffer_dirty"] is True
    assert watched.control.GetValue() == "theirs\n"
    assert watched.modified is False
    assert watched.announcements[-1] == "Reloaded plan.md from disk."


def test_do_not_ask_again_is_kept_and_honoured(watched: Any, asked: _Asked) -> None:
    asked.answer = ExternalChangeAnswer(KEEP, remember=True)
    _rewrite(watched, "first rewrite\n")
    watched._poll_disk_watch()
    assert watched.app.settings.external_change_always_keep == [".md"]
    assert watched.app.saved_settings == 1

    _rewrite(watched, "second rewrite\n", 3_000_000_000)
    watched._poll_disk_watch()
    assert len(asked) == 1  # answered for, not asked
    assert watched.control.GetValue() == _TEXT
    assert "Keeping what is open" in watched.announcements[-1]


def test_save_as_is_the_third_answer(
    watched: Any, asked: _Asked, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_as: list[bool] = []
    monkeypatch.setattr(type(watched), "cmd_save_as", lambda self: saved_as.append(True))
    asked.answer = ExternalChangeAnswer(SAVE_AS)
    _rewrite(watched, "theirs\n")
    watched._poll_disk_watch()
    assert saved_as == [True]


def test_a_deleted_file_is_said_once_and_left_unsaved(watched: Any, asked: _Asked) -> None:
    Path(watched.path).unlink()

    watched._poll_disk_watch()
    watched._poll_disk_watch()

    deleted = [line for line in watched.announcements if "deleted or moved" in line]
    assert len(deleted) == 1
    assert deleted[0].startswith("plan.md was deleted or moved by another program.")
    assert watched.modified is True
    assert watched.control.GetValue() == _TEXT
    assert asked == []


def test_its_own_save_is_not_another_programs_change(watched: Any, asked: _Asked) -> None:
    watched.control.SetValue("mine, edited\n")
    assert watched.save() is True
    watched._poll_disk_watch()
    assert asked == []


def test_a_document_in_the_background_is_asked_about_when_it_comes_forward(
    watched: Any, asked: _Asked
) -> None:
    watched.app.active_frame = object()
    _rewrite(watched, "theirs\n")
    watched._poll_disk_watch()
    assert asked == []

    watched.app.active_frame = watched
    watched._poll_disk_watch()
    assert len(asked) == 1


def test_watching_off_watches_nothing(watched: Any, asked: _Asked) -> None:
    watched.app.settings.external_change_watch_enabled = False
    _rewrite(watched, "theirs\n")
    watched._poll_disk_watch()
    assert asked == []
    assert watched.control.GetValue() == _TEXT


def test_busy_while_loading_or_opening(watched: Any) -> None:
    assert watched._disk_watch_busy() is False
    watched._loading = True
    assert watched._disk_watch_busy() is True
    watched._loading = False
    watched.opening_path = Path("x.txt")
    assert watched._disk_watch_busy() is True


def test_a_remembered_reload_reloads_a_clean_document_without_asking(
    watched: Any, asked: _Asked
) -> None:
    watched.app.settings.external_change_always_reload = [".md"]
    _rewrite(watched, "theirs\n")
    watched._poll_disk_watch()
    assert asked == []
    assert watched.control.GetValue() == "theirs\n"


def test_a_remembered_reload_never_throws_away_unsaved_edits(watched: Any, asked: _Asked) -> None:
    """Family rule 4: the remembered answer was about a clean tab; with unsaved
    edits QUILL Lite asks the normal question instead of reloading over them."""
    watched.app.settings.external_change_always_reload = [".md"]
    watched.control.SetValue("mine, unsaved\n")
    watched.modified = True
    _rewrite(watched, "theirs\n")
    watched._poll_disk_watch()
    assert len(asked) == 1 and asked[0]["buffer_dirty"] is True
    assert watched.control.GetValue() == "mine, unsaved\n"
