"""Unit tests for quill.core.git_worktree.

Everything runs through a fake runner -- no real ``git`` is ever invoked.
Unlike ``test_local_git.py`` (where git's own behaviour is the thing under
test), this module is orchestration: porcelain parsing, the exact argv QUILL
builds, and the refusal sentences a screen-reader user actually hears. All
three are testable, and worth testing, without a repository on disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from quill.core import git_worktree as gw

# ---------------------------------------------------------------------------
# Fake runner
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    """Records every argv and replays queued results in order."""

    def __init__(self, *results: _Result) -> None:
        self._results = list(results)
        self.calls: list[list[str]] = []
        self.cwds: list[str] = []

    def __call__(
        self, args: Sequence[str], *, cwd: str = "", timeout_seconds: float = 30.0
    ) -> _Result:
        self.calls.append(list(args))
        self.cwds.append(cwd)
        if self._results:
            return self._results.pop(0)
        return _Result()

    @property
    def last(self) -> list[str]:
        return self.calls[-1]


LIST_PORCELAIN = """\
worktree C:/code/quill
HEAD 1111111111111111111111111111111111111111
branch refs/heads/main

worktree C:/code/quill-feature-x
HEAD 2222222222222222222222222222222222222222
branch refs/heads/feature/x
locked on a USB drive

worktree C:/code/quill-detached
HEAD 3333333333333333333333333333333333333333
detached

worktree C:/code/quill-gone
HEAD 4444444444444444444444444444444444444444
branch refs/heads/old
prunable gitdir file points to non-existent location
"""

BARE_PORCELAIN = """\
worktree C:/code/quill.git
bare

worktree C:/code/quill-main
HEAD 5555555555555555555555555555555555555555
branch refs/heads/main
"""


def _list_runner(text: str = LIST_PORCELAIN) -> FakeRunner:
    return FakeRunner(_Result(0, text))


# ---------------------------------------------------------------------------
# Porcelain parsing
# ---------------------------------------------------------------------------


def test_parse_multiple_worktrees() -> None:
    entries = gw.parse_worktree_porcelain(LIST_PORCELAIN)
    assert len(entries) == 4
    assert [e.path for e in entries] == [
        "C:/code/quill",
        "C:/code/quill-feature-x",
        "C:/code/quill-detached",
        "C:/code/quill-gone",
    ]


def test_parse_main_worktree_flags() -> None:
    main = gw.parse_worktree_porcelain(LIST_PORCELAIN)[0]
    assert main.is_main is True
    assert main.branch == "main"
    assert main.head == "1111111"
    assert not main.is_locked and not main.is_prunable and not main.is_detached


def test_parse_linked_worktree_is_not_main() -> None:
    linked = gw.parse_worktree_porcelain(LIST_PORCELAIN)[1]
    assert linked.is_main is False
    assert linked.branch == "feature/x"


def test_parse_locked_worktree_keeps_reason() -> None:
    linked = gw.parse_worktree_porcelain(LIST_PORCELAIN)[1]
    assert linked.is_locked is True
    assert linked.lock_reason == "on a USB drive"


def test_parse_detached_head() -> None:
    detached = gw.parse_worktree_porcelain(LIST_PORCELAIN)[2]
    assert detached.is_detached is True
    assert detached.branch == ""
    assert detached.head == "3333333"


def test_parse_prunable_worktree_keeps_reason() -> None:
    gone = gw.parse_worktree_porcelain(LIST_PORCELAIN)[3]
    assert gone.is_prunable is True
    assert "non-existent" in gone.prune_reason


def test_parse_bare_repository() -> None:
    entries = gw.parse_worktree_porcelain(BARE_PORCELAIN)
    assert entries[0].is_bare is True
    assert entries[0].branch == "" and entries[0].head == ""
    assert entries[1].branch == "main"


def test_parse_empty_output() -> None:
    assert gw.parse_worktree_porcelain("") == ()


def test_parse_tolerates_trailing_blank_lines() -> None:
    assert len(gw.parse_worktree_porcelain(LIST_PORCELAIN + "\n\n\n")) == 4


# ---------------------------------------------------------------------------
# describe(): the spoken sentence
# ---------------------------------------------------------------------------


def test_describe_main() -> None:
    main = gw.parse_worktree_porcelain(LIST_PORCELAIN)[0]
    assert main.describe() == "Main worktree at C:/code/quill, on branch main"


def test_describe_linked_and_locked() -> None:
    linked = gw.parse_worktree_porcelain(LIST_PORCELAIN)[1]
    text = linked.describe()
    assert text.startswith("Linked worktree at C:/code/quill-feature-x, on branch feature/x")
    assert "locked: on a USB drive" in text


def test_describe_detached_names_the_commit() -> None:
    detached = gw.parse_worktree_porcelain(LIST_PORCELAIN)[2]
    assert "not on a branch, at commit 3333333" in detached.describe()


def test_describe_prunable_says_what_to_do() -> None:
    gone = gw.parse_worktree_porcelain(LIST_PORCELAIN)[3]
    assert "ready to prune" in gone.describe()


def test_describe_bare() -> None:
    bare = gw.parse_worktree_porcelain(BARE_PORCELAIN)[0]
    assert bare.describe() == "Bare repository at C:/code/quill.git"


# ---------------------------------------------------------------------------
# list_worktrees
# ---------------------------------------------------------------------------


def test_list_worktrees_argv_and_cwd() -> None:
    runner = _list_runner()
    gw.list_worktrees(runner, "C:/code/quill")
    assert runner.last == ["git", "worktree", "list", "--porcelain"]
    assert runner.cwds[-1] == "C:/code/quill"


def test_list_worktrees_counts_in_the_message() -> None:
    result = gw.list_worktrees(_list_runner(), "C:/code/quill")
    assert result.ok is True
    assert len(result.worktrees) == 4
    assert result.message.startswith("4 worktrees")


def test_list_worktrees_singular_message() -> None:
    text = "worktree C:/code/quill\nHEAD 1111111\nbranch refs/heads/main\n"
    result = gw.list_worktrees(_list_runner(text), "C:/code/quill")
    assert result.message == "1 worktree: just the main one."


def test_list_worktrees_failure_is_a_sentence_not_stderr() -> None:
    runner = FakeRunner(_Result(128, "", "fatal: not a git repository"))
    result = gw.list_worktrees(runner, "C:/tmp")
    assert result.ok is False
    assert "fatal:" not in result.message
    assert "git repository" in result.message
    assert result.detail == "fatal: not a git repository"


def test_runner_launch_failure_raises_coded_error() -> None:
    def boom(args: Sequence[str], **kwargs: object) -> object:
        raise OSError("git not found")

    with pytest.raises(gw.WorktreeError) as caught:
        gw.list_worktrees(boom, "C:/code/quill")
    assert "QUILL-GIT-WORKTREE-NO-GIT" in str(caught.value)
    assert "Download Optional Components" in caught.value.user_message()


# ---------------------------------------------------------------------------
# add_worktree
# ---------------------------------------------------------------------------


def test_add_existing_branch_argv(tmp_path: Path) -> None:
    target = tmp_path / "wt" / "feature-y"
    runner = FakeRunner(_Result(0, LIST_PORCELAIN), _Result(0, "Preparing worktree"))
    result = gw.add_worktree(runner, str(tmp_path / "repo"), str(target), "feature/y")
    assert result.ok is True
    assert runner.last == ["git", "worktree", "add", str(target), "feature/y"]
    assert "feature/y" in result.message


def test_add_new_branch_argv(tmp_path: Path) -> None:
    target = tmp_path / "wt" / "feature-z"
    runner = FakeRunner(_Result(0, LIST_PORCELAIN), _Result(0, ""))
    gw.add_worktree(runner, str(tmp_path / "repo"), str(target), "feature/z", create_branch=True)
    assert runner.last == ["git", "worktree", "add", "-b", "feature/z", str(target)]


def test_add_new_branch_from_ref_argv(tmp_path: Path) -> None:
    target = tmp_path / "wt" / "hotfix"
    runner = FakeRunner(_Result(0, LIST_PORCELAIN), _Result(0, ""))
    gw.add_worktree(
        runner,
        str(tmp_path / "repo"),
        str(target),
        "hotfix",
        create_branch=True,
        from_ref="origin/main",
    )
    assert runner.last == [
        "git",
        "worktree",
        "add",
        "-b",
        "hotfix",
        str(target),
        "origin/main",
    ]


def test_add_refuses_empty_branch(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = gw.add_worktree(runner, str(tmp_path), str(tmp_path / "wt"), "  ")
    assert result.ok is False
    assert "branch" in result.message.lower()
    assert runner.calls == []


def test_add_refuses_empty_path(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = gw.add_worktree(runner, str(tmp_path), "", "main")
    assert result.ok is False
    assert "folder" in result.message.lower()
    assert runner.calls == []


def test_add_refuses_path_inside_the_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = FakeRunner()
    result = gw.add_worktree(runner, str(repo), str(repo / "inner"), "main")
    assert result.ok is False
    assert "cannot live inside" in result.message
    assert runner.calls == []


def test_add_refuses_non_empty_folder(tmp_path: Path) -> None:
    target = tmp_path / "busy"
    target.mkdir()
    (target / "note.txt").write_text("hi", encoding="utf-8")
    runner = FakeRunner()
    result = gw.add_worktree(runner, str(tmp_path / "repo"), str(target), "main")
    assert result.ok is False
    assert "already has files" in result.message
    assert runner.calls == []


def test_add_accepts_an_empty_existing_folder(tmp_path: Path) -> None:
    target = tmp_path / "empty"
    target.mkdir()
    runner = FakeRunner(_Result(0, LIST_PORCELAIN), _Result(0, ""))
    assert gw.add_worktree(runner, str(tmp_path / "repo"), str(target), "feature/y").ok is True


def test_add_refuses_a_file_as_the_target(tmp_path: Path) -> None:
    target = tmp_path / "afile.txt"
    target.write_text("x", encoding="utf-8")
    result = gw.add_worktree(FakeRunner(), str(tmp_path / "repo"), str(target), "main")
    assert result.ok is False
    assert "is a file, not a folder" in result.message


def test_add_refuses_branch_checked_out_elsewhere(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(0, LIST_PORCELAIN))
    result = gw.add_worktree(
        runner, str(tmp_path / "repo"), str(tmp_path / "wt" / "x"), "feature/x"
    )
    assert result.ok is False
    assert "already checked out at C:/code/quill-feature-x" in result.message
    assert "one worktree at a time" in result.message
    # Refused before git was asked to do anything destructive.
    assert len(runner.calls) == 1


def test_add_refuses_creating_a_branch_that_is_checked_out(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(0, LIST_PORCELAIN))
    result = gw.add_worktree(
        runner,
        str(tmp_path / "repo"),
        str(tmp_path / "wt" / "x"),
        "main",
        create_branch=True,
    )
    assert result.ok is False
    assert "already a branch named main" in result.message


def test_add_translates_gits_already_checked_out_error(tmp_path: Path) -> None:
    runner = FakeRunner(
        _Result(0, ""),
        _Result(128, "", "fatal: 'feature/q' is already checked out at 'C:/elsewhere'"),
    )
    result = gw.add_worktree(
        runner, str(tmp_path / "repo"), str(tmp_path / "wt" / "q"), "feature/q"
    )
    assert result.ok is False
    assert "only one worktree at a time" in result.message
    assert "fatal:" not in result.message


def test_add_translates_branch_already_exists(tmp_path: Path) -> None:
    runner = FakeRunner(
        _Result(0, ""),
        _Result(128, "", "fatal: a branch named 'dev' already exists"),
    )
    result = gw.add_worktree(
        runner, str(tmp_path / "repo"), str(tmp_path / "wt" / "d"), "dev", create_branch=True
    )
    assert result.ok is False
    assert "Create a new branch" in result.message


def test_add_translates_unknown_ref(tmp_path: Path) -> None:
    runner = FakeRunner(
        _Result(0, ""),
        _Result(128, "", "fatal: invalid reference: nope"),
    )
    result = gw.add_worktree(runner, str(tmp_path / "repo"), str(tmp_path / "wt" / "n"), "nope")
    assert result.ok is False
    assert "did not recognise" in result.message


# ---------------------------------------------------------------------------
# remove_worktree
# ---------------------------------------------------------------------------


def test_remove_argv(tmp_path: Path) -> None:
    target = tmp_path / "wt"
    runner = FakeRunner(_Result(0, ""))
    result = gw.remove_worktree(runner, str(tmp_path / "repo"), str(target))
    assert runner.last == ["git", "worktree", "remove", str(target)]
    assert result.ok is True
    assert "Removed the worktree" in result.message


def test_remove_force_argv(tmp_path: Path) -> None:
    target = tmp_path / "wt"
    runner = FakeRunner(_Result(0, ""))
    gw.remove_worktree(runner, str(tmp_path / "repo"), str(target), force=True)
    assert runner.last == ["git", "worktree", "remove", "--force", str(target)]


def test_remove_refuses_empty_path(tmp_path: Path) -> None:
    runner = FakeRunner()
    assert gw.remove_worktree(runner, str(tmp_path), "").ok is False
    assert runner.calls == []


def test_remove_surfaces_uncommitted_changes_without_forcing(tmp_path: Path) -> None:
    runner = FakeRunner(
        _Result(1, "", "fatal: 'wt' contains modified or untracked files, use --force to delete it")
    )
    result = gw.remove_worktree(runner, str(tmp_path / "repo"), str(tmp_path / "wt"))
    assert result.ok is False
    assert "not committed" in result.message
    assert "--force" not in result.message
    # QUILL did not silently retry with force.
    assert len(runner.calls) == 1


def test_remove_explains_main_worktree(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(1, "", "fatal: 'x' is a main working tree"))
    result = gw.remove_worktree(runner, str(tmp_path / "repo"), str(tmp_path / "x"))
    assert result.ok is False
    assert "main folder" in result.message


def test_remove_explains_locked(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(1, "", "fatal: 'x' is locked"))
    result = gw.remove_worktree(runner, str(tmp_path / "repo"), str(tmp_path / "x"))
    assert result.ok is False
    assert "Unlock it first" in result.message


# ---------------------------------------------------------------------------
# prune_worktrees
# ---------------------------------------------------------------------------


def test_prune_argv() -> None:
    runner = FakeRunner(_Result(0, ""))
    gw.prune_worktrees(runner, "C:/code/quill")
    assert runner.last == ["git", "worktree", "prune", "--verbose"]


def test_prune_nothing_to_do() -> None:
    result = gw.prune_worktrees(FakeRunner(_Result(0, "")), "C:/code/quill")
    assert result.ok is True
    assert result.pruned == ()
    assert "Nothing to tidy up" in result.message


def test_prune_reports_what_it_removed() -> None:
    stdout = (
        "Removing worktrees/old-feature: gitdir file points to non-existent location\n"
        "Removing worktrees/spike: gitdir file points to non-existent location\n"
    )
    result = gw.prune_worktrees(FakeRunner(_Result(0, stdout)), "C:/code/quill")
    assert result.ok is True
    assert result.pruned == ("old-feature", "spike")
    assert "old-feature" in result.message and "spike" in result.message


def test_prune_failure_message() -> None:
    result = gw.prune_worktrees(FakeRunner(_Result(1, "", "boom")), "C:/code/quill")
    assert result.ok is False
    assert "boom" not in result.message


# ---------------------------------------------------------------------------
# move_worktree
# ---------------------------------------------------------------------------


def test_move_argv(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(0, ""))
    src, dest = tmp_path / "a", tmp_path / "b"
    result = gw.move_worktree(runner, str(tmp_path / "repo"), str(src), str(dest))
    assert runner.last == ["git", "worktree", "move", str(src), str(dest)]
    assert result.ok is True


def test_move_refuses_destination_inside_the_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = FakeRunner()
    result = gw.move_worktree(runner, str(repo), str(tmp_path / "a"), str(repo / "inner"))
    assert result.ok is False
    assert "cannot live inside" in result.message
    assert runner.calls == []


def test_move_refuses_missing_arguments(tmp_path: Path) -> None:
    assert gw.move_worktree(FakeRunner(), str(tmp_path), "", "").ok is False


def test_move_explains_locked(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(1, "", "fatal: 'a' is locked"))
    result = gw.move_worktree(
        runner, str(tmp_path / "repo"), str(tmp_path / "a"), str(tmp_path / "b")
    )
    assert result.ok is False
    assert "Unlock it first" in result.message


# ---------------------------------------------------------------------------
# lock / unlock
# ---------------------------------------------------------------------------


def test_lock_argv(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(0, ""))
    target = tmp_path / "wt"
    gw.lock_worktree(runner, str(tmp_path / "repo"), str(target))
    assert runner.last == ["git", "worktree", "lock", str(target)]


def test_lock_with_reason_argv(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(0, ""))
    target = tmp_path / "wt"
    result = gw.lock_worktree(runner, str(tmp_path / "repo"), str(target), reason="on a USB drive")
    assert runner.last == [
        "git",
        "worktree",
        "lock",
        "--reason",
        "on a USB drive",
        str(target),
    ]
    assert "on a USB drive" in result.message


def test_lock_refuses_empty_path(tmp_path: Path) -> None:
    runner = FakeRunner()
    assert gw.lock_worktree(runner, str(tmp_path), "").ok is False
    assert runner.calls == []


def test_lock_already_locked(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(1, "", "fatal: 'wt' is already locked"))
    result = gw.lock_worktree(runner, str(tmp_path / "repo"), str(tmp_path / "wt"))
    assert result.ok is False
    assert "already locked" in result.message


def test_unlock_argv(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(0, ""))
    target = tmp_path / "wt"
    result = gw.unlock_worktree(runner, str(tmp_path / "repo"), str(target))
    assert runner.last == ["git", "worktree", "unlock", str(target)]
    assert result.ok is True


def test_unlock_not_locked(tmp_path: Path) -> None:
    runner = FakeRunner(_Result(1, "", "fatal: 'wt' is not locked"))
    result = gw.unlock_worktree(runner, str(tmp_path / "repo"), str(tmp_path / "wt"))
    assert result.ok is False
    assert "was not locked" in result.message


def test_unlock_refuses_empty_path(tmp_path: Path) -> None:
    runner = FakeRunner()
    assert gw.unlock_worktree(runner, str(tmp_path), "").ok is False
    assert runner.calls == []
