"""The change set and code-mode review words (code.md 4.2, 5.4; GATE-PROJECT-REVIEW)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.change_set import ChangeKind, ChangeSet, ChangeSetError
from quill.core.ai.code_diff import describe_file, describe_hunk, numbered_lines, token_changes
from quill.core.ai.project import Project

ORIGINAL = "import sys\n\ndef parse(args):\n    tokn = args[0]\n    return tokn\n\nprint(1)\n"


@pytest.fixture
def project(tmp_path: Path) -> Project:
    root = tmp_path / "p"
    root.mkdir()
    (root / "cli.py").write_text(ORIGINAL, encoding="utf-8")
    (root / "crlf.txt").write_bytes(b"one\r\ntwo\r\nthree\r\n")
    (root / "old.py").write_text("x = 1\n", encoding="utf-8")
    return Project(root)


def _two_hunk_edit(changes: ChangeSet) -> None:
    revised = ORIGINAL.replace("tokn", "token").replace("print(1)", "print(2)")
    changes.propose_edit("cli.py", ORIGINAL, revised, "Fix the typo.")


def test_nothing_is_written_when_proposed(project: Project) -> None:
    changes = ChangeSet()
    _two_hunk_edit(changes)
    changes.propose_create("tests/test_cli.py", "def test_x():\n    pass\n")
    assert (project.root / "cli.py").read_text(encoding="utf-8") == ORIGINAL
    assert not (project.root / "tests").exists()


def test_rejected_change_never_reaches_disk(project: Project) -> None:
    changes = ChangeSet()
    _two_hunk_edit(changes)
    changes.propose_create("new.py", "y = 2\n")
    change = changes.get("cli.py")
    assert change is not None and change.change_count == 2
    change.hunks[1].accepted = False  # keep print(1)
    changes.get("new.py").accepted = False  # type: ignore[union-attr]
    outcome = changes.outcome_text()
    report = changes.apply(project.resolve)
    assert report.ok and report.written == ("cli.py",)
    text = (project.root / "cli.py").read_text(encoding="utf-8")
    assert "token" in text and "print(1)" in text and "print(2)" not in text
    assert not (project.root / "new.py").exists()
    assert "Accepted 1 of 2 changes in cli.py" in outcome and "line 7" in outcome
    assert "rejected creating new.py" in outcome


def test_reject_all_writes_nothing(project: Project) -> None:
    changes = ChangeSet()
    _two_hunk_edit(changes)
    changes.reject_all()
    report = changes.apply(project.resolve)
    assert report.ok and report.touched == ()
    assert (project.root / "cli.py").read_text(encoding="utf-8") == ORIGINAL


def test_line_endings_are_kept(project: Project) -> None:
    changes = ChangeSet()
    original = (project.root / "crlf.txt").read_bytes().decode()
    changes.propose_edit("crlf.txt", original, original.replace("two", "TWO"))
    changes.apply(project.resolve)
    assert (project.root / "crlf.txt").read_bytes() == b"one\r\nTWO\r\nthree\r\n"


def test_second_edit_builds_on_the_first(project: Project) -> None:
    changes = ChangeSet()
    first = ORIGINAL.replace("tokn", "token")
    changes.propose_edit("cli.py", ORIGINAL, first)
    changes.propose_edit("cli.py", first, first.replace("print(1)", "print(3)"))
    change = changes.get("cli.py")
    assert change is not None and change.original == ORIGINAL and change.change_count == 2


def test_no_op_edit_is_refused() -> None:
    with pytest.raises(ChangeSetError):
        ChangeSet().propose_edit("a.py", "x\n", "x\n")


def test_delete_and_rename(project: Project) -> None:
    changes = ChangeSet()
    changes.propose_delete("old.py", "x = 1\n")
    changes.propose_rename("crlf.txt", "docs/lines.txt")
    report = changes.apply(project.resolve)
    assert report.ok
    assert not (project.root / "old.py").exists()
    assert (project.root / "docs" / "lines.txt").exists() and not (
        project.root / "crlf.txt"
    ).exists()


def test_partial_failure_rolls_the_whole_turn_back(project: Project, monkeypatch) -> None:
    import quill.core.ai.change_set as module

    changes = ChangeSet()
    _two_hunk_edit(changes)
    changes.propose_create("made.py", "z = 3\n")
    changes.propose_delete("old.py", "x = 1\n")
    real_replace = module.os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError(28, "No space left on device")
        return real_replace(src, dst)

    monkeypatch.setattr(module.os, "replace", flaky)
    report = changes.apply(project.resolve)
    monkeypatch.setattr(module.os, "replace", real_replace)
    assert not report.ok and "Nothing was written" in report.error
    assert (project.root / "cli.py").read_text(encoding="utf-8") == ORIGINAL
    assert not (project.root / "made.py").exists()
    assert (project.root / "old.py").exists()
    assert not list(project.root.glob(".quill-*.tmp"))


def test_apply_refuses_a_path_outside_the_project(project: Project) -> None:
    changes = ChangeSet()
    changes.propose_create("../escape.txt", "no\n")
    report = changes.apply(project.resolve)
    assert not report.ok
    assert not (project.root.parent / "escape.txt").exists()


def test_row_text_is_one_sentence() -> None:
    changes = ChangeSet()
    _two_hunk_edit(changes)
    changes.propose_create("tests/test_cli.py", "a\nb\nc\n")
    changes.propose_delete("old_util.py", "x\n")
    rows = [f.row_text() for f in changes.files]
    assert rows == [
        "cli.py, changed, 2 changes, taken",
        "tests/test_cli.py, new file, 3 lines, taken",
        "old_util.py, deleted, taken",
    ]
    changes.get("cli.py").hunks[0].accepted = False  # type: ignore[union-attr]
    assert changes.get("cli.py").row_text().endswith("1 of 2 taken")  # type: ignore[union-attr]


def test_code_mode_words() -> None:
    changes = ChangeSet()
    _two_hunk_edit(changes)
    change = changes.get("cli.py")
    assert change is not None and change.kind is ChangeKind.EDIT
    first = describe_hunk(change, 0)
    assert first.heading.startswith("Change 1 of 2, lines 4 to 5, in function parse.")
    second = describe_hunk(change, 1)
    assert "line 7" in second.heading
    assert "changed 1 to 2" in second.body
    assert "The agent's reason: Fix the typo." in second.body
    assert token_changes("    tokn = 1", "    token = 1") == ["changed tokn to token"]
    lines = numbered_lines(["def a():", "    x = 1", "    y = 2", "", "z = 3"], 10)
    assert lines == [
        "10: indent 0, def a():",
        "11: indent 4, x = 1",
        "12: y = 2",
        "13: blank",
        "14: indent 0, z = 3",
    ]
    created = ChangeSet().propose_create("n.py", "a = 1\nb = 2\n")
    assert describe_file(created).heading.startswith("New file n.py, 2 lines.")
