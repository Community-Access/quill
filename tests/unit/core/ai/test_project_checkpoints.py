"""Checkpoints and Undo Last Turn (code.md 4.5, Phase 2 gates)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.change_set import ChangeSet
from quill.core.ai.checkpoints import CheckpointStore
from quill.core.ai.project import Project


@pytest.fixture
def setup(tmp_path: Path) -> tuple[Project, CheckpointStore]:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.py").write_text("a = 1\n", encoding="utf-8")
    (root / "b.py").write_text("b = 1\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    project = Project(root)
    return project, CheckpointStore(project, tmp_path / "data")


def _tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_apply_some_then_undo_is_byte_identical(setup) -> None:
    project, store = setup
    before = _tree(project.root)
    changes = ChangeSet()
    changes.propose_edit("a.py", "a = 1\n", "a = 2\n")
    changes.propose_create("new/c.py", "c = 1\n")
    changes.propose_delete("b.py", "b = 1\n")
    store.ensure_turn()
    assert changes.apply(project.resolve).ok
    store.record_after()
    store.close_turn()
    assert _tree(project.root) != before
    report = store.undo_last()
    assert report.ok, report.sentence
    after = _tree(project.root)
    # The empty folder the turn made may stay; every file is exactly as it was.
    assert after == before
    assert report.sentence.startswith("Undid turn 1.")
    assert "new/c.py" in report.removed


def test_undo_refuses_when_the_person_edited_since(setup) -> None:
    project, store = setup
    changes = ChangeSet()
    changes.propose_edit("a.py", "a = 1\n", "a = 2\n")
    store.ensure_turn()
    changes.apply(project.resolve)
    store.close_turn()
    (project.root / "a.py").write_text("a = 99  # mine\n", encoding="utf-8")
    report = store.undo_last()
    assert not report.ok
    assert report.edited_since == ("a.py",)
    assert "a.py has changed since the agent's turn" in report.sentence
    assert (project.root / "a.py").read_text(encoding="utf-8") == "a = 99  # mine\n"


def test_secrets_are_never_copied(setup) -> None:
    project, store = setup
    store.ensure_turn()
    turn = store.open_turn
    assert turn is not None and ".env" not in turn.before
    objects = store.folder / "objects"
    stored = b"".join(p.read_bytes() for p in objects.iterdir()) if objects.exists() else b""
    assert b"SECRET=1" not in stored


def test_store_lives_outside_the_project(setup) -> None:
    project, store = setup
    assert project.root not in store.folder.parents


def test_nothing_to_undo(setup) -> None:
    _project, store = setup
    report = store.undo_last()
    assert not report.ok and "no agent turn to undo" in report.sentence


def test_two_turns_undo_newest_first(setup) -> None:
    project, store = setup
    for value in ("2", "3"):
        changes = ChangeSet()
        current = (project.root / "a.py").read_text(encoding="utf-8")
        changes.propose_edit("a.py", current, f"a = {value}\n")
        store.ensure_turn()
        changes.apply(project.resolve)
        store.close_turn()
    assert store.undo_last().ok
    assert (project.root / "a.py").read_text(encoding="utf-8") == "a = 2\n"
    assert store.undo_last().ok
    assert (project.root / "a.py").read_text(encoding="utf-8") == "a = 1\n"
