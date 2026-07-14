"""Unit tests for quill.core.local_git, against real temporary git repos.

Subprocess orchestration is the entire point of this module, so these tests
exercise real ``git`` (already a hard requirement for anyone using this
feature) rather than faking porcelain output -- the fake-runner style used
in test_git_sync.py is for testing *orchestration* around a git call; here
the git calls' actual behavior is what's under test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quill.core import local_git as lg

# ---------------------------------------------------------------------------
# Real subprocess runner + repo fixture helpers
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, proc: subprocess.CompletedProcess) -> None:
        self.returncode = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr


def _real_runner(args: list[str], *, cwd: str, timeout_seconds: float = 30.0) -> _Result:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout_seconds)
    return _Result(proc)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


def _write(root: Path, name: str, content: str) -> None:
    (root / name).write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _write(root, "a.txt", "line1\nline2\n")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-m", "initial")
    return root


# ---------------------------------------------------------------------------
# Status / staging
# ---------------------------------------------------------------------------


def test_get_status_clean_repo(repo: Path) -> None:
    status = lg.get_status(str(repo), runner=_real_runner)
    assert status.branch == "main"
    assert status.changes == ()
    assert status.conflicts == ()


def test_get_status_modified_and_untracked(repo: Path) -> None:
    _write(repo, "a.txt", "line1\nCHANGED\n")
    _write(repo, "b.txt", "new file\n")
    status = lg.get_status(str(repo), runner=_real_runner)
    by_path = {c.path: c for c in status.changes}
    assert by_path["a.txt"].unstaged_code == "M"
    assert by_path["a.txt"].unstaged_label == "modified"
    assert by_path["b.txt"].unstaged_code == "?"
    assert by_path["b.txt"].unstaged_label == "untracked"


def test_stage_and_unstage_file(repo: Path) -> None:
    _write(repo, "a.txt", "line1\nCHANGED\n")
    lg.stage_file(str(repo), "a.txt", runner=_real_runner)
    status = lg.get_status(str(repo), runner=_real_runner)
    assert status.changes[0].staged_code == "M"

    lg.unstage_file(str(repo), "a.txt", runner=_real_runner)
    status = lg.get_status(str(repo), runner=_real_runner)
    assert status.changes[0].staged_code == ""
    assert status.changes[0].unstaged_code == "M"


def test_stage_all(repo: Path) -> None:
    _write(repo, "b.txt", "new\n")
    _write(repo, "c.txt", "new2\n")
    lg.stage_all(str(repo), runner=_real_runner)
    status = lg.get_status(str(repo), runner=_real_runner)
    assert all(c.staged_code == "A" for c in status.changes)


def test_file_content_at_ref(repo: Path) -> None:
    assert lg.file_content_at_ref(str(repo), "HEAD", "a.txt", runner=_real_runner) == (
        "line1\nline2\n"
    )
    assert lg.file_content_at_ref(str(repo), "HEAD", "missing.txt", runner=_real_runner) == ""


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------


def test_list_local_branches_marks_current(repo: Path) -> None:
    _git(repo, "branch", "feature")
    branches = lg.list_local_branches(str(repo), runner=_real_runner)
    names = {b.name: b.is_current for b in branches}
    assert names == {"main": True, "feature": False}


def test_switch_branch_succeeds_when_clean(repo: Path) -> None:
    _git(repo, "branch", "feature")
    result = lg.switch_branch(str(repo), "feature", runner=_real_runner)
    assert result.ok is True
    status = lg.get_status(str(repo), runner=_real_runner)
    assert status.branch == "feature"


def test_switch_branch_refuses_when_dirty(repo: Path) -> None:
    _git(repo, "branch", "feature")
    _write(repo, "a.txt", "dirty\n")
    result = lg.switch_branch(str(repo), "feature", runner=_real_runner)
    assert result.ok is False
    assert "uncommitted" in result.message
    status = lg.get_status(str(repo), runner=_real_runner)
    assert status.branch == "main"  # never switched


def test_switch_branch_force_ignores_dirty_guard(repo: Path) -> None:
    _git(repo, "branch", "feature")
    _write(repo, "a.txt", "line1\nline2\nmore\n")  # still merges cleanly on switch
    result = lg.switch_branch(str(repo), "feature", runner=_real_runner, force=True)
    assert result.ok is True


# ---------------------------------------------------------------------------
# Stash
# ---------------------------------------------------------------------------


def test_stash_save_list_apply_drop(repo: Path) -> None:
    _write(repo, "a.txt", "line1\nline2\nstashed\n")
    lg.stash_save(str(repo), "my stash", runner=_real_runner)
    assert lg.get_status(str(repo), runner=_real_runner).changes == ()

    stashes = lg.list_stashes(str(repo), runner=_real_runner)
    assert len(stashes) == 1
    assert "my stash" in stashes[0].message
    ref = stashes[0].ref

    lg.stash_apply(str(repo), ref, runner=_real_runner)
    assert lg.get_status(str(repo), runner=_real_runner).changes != ()

    lg.stash_drop(str(repo), ref, runner=_real_runner)
    assert lg.list_stashes(str(repo), runner=_real_runner) == []


# ---------------------------------------------------------------------------
# Blame
# ---------------------------------------------------------------------------


def test_blame_line_reports_the_committing_author(repo: Path) -> None:
    info = lg.blame_line(str(repo), "a.txt", 1, runner=_real_runner)
    assert info.author == "Test"
    assert info.summary == "initial"
    assert len(info.commit_sha) == 40


# ---------------------------------------------------------------------------
# Bisect
# ---------------------------------------------------------------------------


def test_bisect_finds_the_first_bad_commit(repo: Path) -> None:
    good_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    for i in range(3):
        _write(repo, "a.txt", f"line1\nline2\ncommit{i}\n")
        _git(repo, "add", "a.txt")
        _git(repo, "commit", "-m", f"commit {i}")
    bad_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    status = lg.bisect_start(str(repo), bad_sha, good_sha, runner=_real_runner)
    # 3 commits between good and bad -> bisect checks out the middle one.
    assert status.done is False

    # Whichever commit bisect landed on, mark it bad until it converges.
    for _ in range(5):
        status = lg.bisect_mark(str(repo), "bad", runner=_real_runner)
        if status.done:
            break
    assert status.done is True
    assert status.culprit_sha

    lg.bisect_reset(str(repo), runner=_real_runner)
    final_status = lg.get_status(str(repo), runner=_real_runner)
    assert final_status.branch == "main"


def test_bisect_mark_rejects_unknown_verdict(repo: Path) -> None:
    with pytest.raises(lg.LocalGitError, match="Unknown bisect verdict"):
        lg.bisect_mark(str(repo), "maybe", runner=_real_runner)


# ---------------------------------------------------------------------------
# Conflict parsing (pure, no repo needed)
# ---------------------------------------------------------------------------


_CONFLICT_TEXT = """line1
<<<<<<< HEAD
mine
=======
theirs
>>>>>>> feature
line3
"""


def test_parse_conflict_hunks() -> None:
    hunks = lg.parse_conflict_hunks(_CONFLICT_TEXT)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.ours == ("mine",)
    assert hunk.theirs == ("theirs",)
    assert hunk.ours_label == "HEAD"
    assert hunk.theirs_label == "feature"


def test_resolve_conflict_hunks_ours() -> None:
    result = lg.resolve_conflict_hunks(_CONFLICT_TEXT, ["ours"])
    assert result == "line1\nmine\nline3\n"


def test_resolve_conflict_hunks_theirs() -> None:
    result = lg.resolve_conflict_hunks(_CONFLICT_TEXT, ["theirs"])
    assert result == "line1\ntheirs\nline3\n"


def test_resolve_conflict_hunks_both() -> None:
    result = lg.resolve_conflict_hunks(_CONFLICT_TEXT, ["both"])
    assert result == "line1\nmine\ntheirs\nline3\n"


def test_resolve_conflict_hunks_manual_text() -> None:
    result = lg.resolve_conflict_hunks(_CONFLICT_TEXT, ["custom line"])
    assert result == "line1\ncustom line\nline3\n"


def test_resolve_conflict_hunks_rejects_count_mismatch() -> None:
    with pytest.raises(lg.LocalGitError, match="1 conflict hunk"):
        lg.resolve_conflict_hunks(_CONFLICT_TEXT, ["ours", "theirs"])


def test_conflict_walker_against_a_real_merge_conflict(repo: Path) -> None:
    _git(repo, "checkout", "-b", "feature")
    _write(repo, "a.txt", "line1\nFEATURE\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "feature change")

    _git(repo, "checkout", "main")
    _write(repo, "a.txt", "line1\nMAIN\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "main change")

    subprocess.run(["git", "merge", "feature"], cwd=repo, capture_output=True, text=True)

    conflicted = lg.list_conflicted_files(str(repo), runner=_real_runner)
    assert conflicted == ["a.txt"]

    text = (repo / "a.txt").read_text(encoding="utf-8")
    hunks = lg.parse_conflict_hunks(text)
    assert len(hunks) == 1
    # "both" (not "ours") so the resolved content differs from either parent
    # and is guaranteed to show up as a real staged change below.
    resolved = lg.resolve_conflict_hunks(text, ["both"])
    (repo / "a.txt").write_text(resolved, encoding="utf-8")
    lg.mark_conflict_resolved(str(repo), "a.txt", runner=_real_runner)

    status = lg.get_status(str(repo), runner=_real_runner)
    assert status.conflicts == ()
    assert status.changes[0].staged_code == "M"


# ---------------------------------------------------------------------------
# Interactive rebase
# ---------------------------------------------------------------------------


def test_build_rebase_todo_lists_commits_oldest_first(repo: Path) -> None:
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    for i in range(3):
        _write(repo, "a.txt", f"line1\nline2\ncommit{i}\n")
        _git(repo, "add", "a.txt")
        _git(repo, "commit", "-m", f"commit {i}")

    todo = lg.build_rebase_todo(str(repo), base, runner=_real_runner)
    assert [entry.subject for entry in todo] == ["commit 0", "commit 1", "commit 2"]
    assert all(entry.action == "pick" for entry in todo)


def test_execute_rebase_clean_pick_all(repo: Path) -> None:
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    for i in range(2):
        _write(repo, "a.txt", f"line1\nline2\ncommit{i}\n")
        _git(repo, "add", "a.txt")
        _git(repo, "commit", "-m", f"commit {i}")

    todo = lg.build_rebase_todo(str(repo), base, runner=_real_runner)
    result = lg.execute_rebase(
        str(repo),
        base,
        todo,
        runner=_real_runner,
        sequence_editor_command=lg.default_sequence_editor_command,
    )
    assert result.ok is True
    log = subprocess.run(
        ["git", "log", "--format=%s", base + "..HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout
    assert log.splitlines() == ["commit 1", "commit 0"]  # newest first in log output


def test_execute_rebase_drop_removes_a_commit(repo: Path) -> None:
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    # Two commits touching *different* files, so dropping the first is a
    # clean, non-conflicting drop -- dropping a commit a later one's diff
    # actually depends on is a real, separate conflict scenario, not this one.
    _write(repo, "b.txt", "commit 0 content\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-m", "commit 0")
    _write(repo, "a.txt", "line1\nline2\ncommit1\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "commit 1")

    todo = lg.build_rebase_todo(str(repo), base, runner=_real_runner)
    todo[0].action = "drop"
    result = lg.execute_rebase(
        str(repo),
        base,
        todo,
        runner=_real_runner,
        sequence_editor_command=lg.default_sequence_editor_command,
    )
    assert result.ok is True
    log = subprocess.run(
        ["git", "log", "--format=%s", base + "..HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout
    assert log.splitlines() == ["commit 1"]


def test_execute_rebase_stops_for_conflicts(repo: Path) -> None:
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    # Two commits that touch the same line differently -> reordering them
    # (via squash-then-pick isn't needed; a direct conflicting amend is
    # simplest) forces a real conflict when rebased onto a diverged base.
    _write(repo, "a.txt", "line1\nfeatureline\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "feature change")

    # Diverge the base itself so replaying the commit above conflicts.
    _git(repo, "checkout", base)
    _git(repo, "checkout", "-b", "diverged")
    _write(repo, "a.txt", "line1\nbaseline\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "diverged base change")
    new_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    _git(repo, "checkout", "main")
    todo = lg.build_rebase_todo(str(repo), base, runner=_real_runner)
    result = lg.execute_rebase(
        str(repo),
        new_base,
        todo,
        runner=_real_runner,
        sequence_editor_command=lg.default_sequence_editor_command,
    )
    assert result.ok is False
    assert result.stopped_for_conflicts is True

    # Resolve and continue.
    text = (repo / "a.txt").read_text(encoding="utf-8")
    resolved = lg.resolve_conflict_hunks(text, ["theirs"])
    (repo / "a.txt").write_text(resolved, encoding="utf-8")
    lg.mark_conflict_resolved(str(repo), "a.txt", runner=_real_runner)
    continued = lg.rebase_continue(str(repo), runner=_real_runner)
    assert continued.ok is True


def test_rebase_abort_restores_original_head(repo: Path) -> None:
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    _write(repo, "a.txt", "line1\nfeatureline\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "feature change")
    original_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    _git(repo, "checkout", base)
    _git(repo, "checkout", "-b", "diverged")
    _write(repo, "a.txt", "line1\nbaseline\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "diverged base change")
    new_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    _git(repo, "checkout", "main")
    todo = lg.build_rebase_todo(str(repo), base, runner=_real_runner)
    result = lg.execute_rebase(
        str(repo),
        new_base,
        todo,
        runner=_real_runner,
        sequence_editor_command=lg.default_sequence_editor_command,
    )
    assert result.stopped_for_conflicts is True

    lg.rebase_abort(str(repo), runner=_real_runner)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    assert head == original_head
