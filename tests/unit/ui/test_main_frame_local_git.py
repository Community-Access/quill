"""Tests for LocalGitMixin: the Tools > Local Git command handlers.

Mirrors test_main_frame_git_sync.py's convention: wx dialog helpers are
monkeypatched per test, _run_background_task runs synchronously, and
quill.core.local_git's functions are monkeypatched at their defining module
so the mixin's local imports resolve to fakes -- the underlying git
orchestration itself is already covered end-to-end against real repos in
test_local_git.py; this file is about the mixin's own gating/sequencing.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui.main_frame_local_git import LocalGitMixin


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _Host(LocalGitMixin):
    def __init__(self) -> None:
        self._wx = SimpleNamespace(ICON_INFORMATION=1, OK=1)
        self.frame = object()
        self.commands = _FakeCommands()
        self.document = SimpleNamespace(path=None)
        self.editor = SimpleNamespace(GetCurrentLine=lambda: 0)
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.background_tasks: list[tuple[str, Any]] = []

    def _binding_for(self, _command_id: str) -> str:
        return ""

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _show_modal_dialog(self, _dialog: object, _title: str) -> int:  # pragma: no cover
        raise AssertionError("wx dialogs must be short-circuited by per-test patches")

    def _show_message_box(self, _message: str, _title: str, _style: int) -> int:
        return 0

    def _run_background_task(self, label: str, work: Any, on_success: Any, **_kw: Any) -> None:
        self.background_tasks.append((label, work))
        on_success(work(lambda *_a: None))


@pytest.fixture(autouse=True)
def _clear_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


@pytest.fixture(autouse=True)
def _git_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.git_available", lambda: True)


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------


def test_safe_mode_blocks_every_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    host = _Host()
    host.local_git_uncommitted_changes()
    assert host.statuses == ["Local git commands are disabled in Safe Mode"]
    assert host.background_tasks == []


def test_missing_git_binary_shows_a_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.git_available", lambda: False)
    host = _Host()
    host.local_git_uncommitted_changes()
    assert host.background_tasks == []


def test_repo_root_found_from_document_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "file.txt"))
    root = host._local_git_repo_root()
    assert root == str(repo)


def test_repo_root_prompts_when_no_document(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host._wx = SimpleNamespace(
        DirDialog=lambda *a, **k: _FakeDirDialog(str(repo)), DD_DEFAULT_STYLE=0, ID_OK="OK"
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    root = host._local_git_repo_root()
    assert root == str(repo)


def test_repo_root_reports_when_chosen_folder_is_not_a_repo(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    host = _Host()
    host._wx = SimpleNamespace(
        DirDialog=lambda *a, **k: _FakeDirDialog(str(not_a_repo)), DD_DEFAULT_STYLE=0, ID_OK="OK"
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    root = host._local_git_repo_root()
    assert root is None
    assert "not a git repository" in host.statuses[-1]


# ---------------------------------------------------------------------------
# Uncommitted changes
# ---------------------------------------------------------------------------


def test_uncommitted_changes_reports_when_clean(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "file.txt"))
    monkeypatch.setattr(
        "quill.core.local_git.get_status",
        lambda root, *, runner: SimpleNamespace(changes=(), conflicts=()),
    )
    host.local_git_uncommitted_changes()
    assert host.statuses == ["No uncommitted changes"]


def test_uncommitted_changes_opens_dialog_with_stage_callbacks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "file.txt"))
    change = SimpleNamespace(path="a.txt", staged_code="", unstaged_code="M")
    monkeypatch.setattr(
        "quill.core.local_git.get_status",
        lambda root, *, runner: SimpleNamespace(changes=(change,), conflicts=()),
    )
    opened: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.local_git_dialogs.UncommittedChangesDialog",
        lambda *a, **k: opened.append(k) or SimpleNamespace(show=lambda: None),
    )
    host.local_git_uncommitted_changes()
    assert len(opened) == 1
    assert opened[0]["diff_provider"] is not None


def test_stage_and_unstage_helpers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    host = _Host()
    staged: list[str] = []
    unstaged: list[str] = []
    monkeypatch.setattr(
        "quill.core.local_git.stage_file", lambda root, path, *, runner: staged.append(path)
    )
    monkeypatch.setattr(
        "quill.core.local_git.unstage_file", lambda root, path, *, runner: unstaged.append(path)
    )
    host._local_git_stage(str(tmp_path), "a.txt")
    host._local_git_unstage(str(tmp_path), "a.txt")
    assert staged == ["a.txt"]
    assert unstaged == ["a.txt"]
    assert host.statuses == ["Staged a.txt", "Unstaged a.txt"]


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------


def test_switch_branch_no_other_branches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "file.txt"))
    current = SimpleNamespace(name="main", is_current=True)
    monkeypatch.setattr(
        "quill.core.local_git.list_local_branches", lambda root, *, runner: [current]
    )
    host.local_git_switch_branch()
    assert host.statuses == ["No other local branches"]


def test_switch_branch_offers_force_switch_when_dirty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "file.txt"))
    current = SimpleNamespace(name="main", is_current=True)
    feature = SimpleNamespace(name="feature", is_current=False)
    monkeypatch.setattr(
        "quill.core.local_git.list_local_branches", lambda root, *, runner: [current, feature]
    )
    host._wx = SimpleNamespace(
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog("feature"), ID_OK="OK"
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    dirty_result = SimpleNamespace(ok=False, message="1 uncommitted change(s) present.")
    monkeypatch.setattr(
        "quill.core.local_git.switch_branch",
        lambda root, name, *, runner, force=False: dirty_result,
    )
    host._local_git_confirm = lambda message, title: True
    forced: list[str] = []
    host._local_git_force_switch = lambda root, name: forced.append(name)
    host.local_git_switch_branch()
    assert forced == ["feature"]


# ---------------------------------------------------------------------------
# Bisect
# ---------------------------------------------------------------------------


def test_bisect_status_loop_marks_good_or_bad(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    not_done = SimpleNamespace(done=False, message="Bisecting", culprit_sha="")
    done = SimpleNamespace(done=True, message="abc is the first bad commit", culprit_sha="abc")
    marked: list[str] = []

    def fake_mark(root: str, verdict: str, *, runner: object) -> SimpleNamespace:
        marked.append(verdict)
        return done  # converge immediately so the mixin's chained call stops

    monkeypatch.setattr("quill.core.local_git.bisect_mark", fake_mark)
    host._local_git_confirm = lambda message, title: True  # "bad"
    host._on_local_git_bisect_status("/repo", not_done)
    assert marked == ["bad"]


def test_bisect_status_done_reports_culprit() -> None:
    host = _Host()
    done = SimpleNamespace(
        done=True, message="abc123 is the first bad commit", culprit_sha="abc123"
    )
    host._on_local_git_bisect_status("/repo", done)
    assert "Bisect complete" in host.statuses[-1]


# ---------------------------------------------------------------------------
# Merge conflicts
# ---------------------------------------------------------------------------


def test_resolve_conflicts_none_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "file.txt"))
    monkeypatch.setattr("quill.core.local_git.list_conflicted_files", lambda root, *, runner: [])
    host.local_git_resolve_conflicts()
    assert host.statuses == ["No conflicts to resolve"]


def test_resolve_conflicts_walks_each_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    conflicted_file = repo / "a.txt"
    conflicted_file.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> f\n", encoding="utf-8")

    host = _Host()
    resolved_paths: list[str] = []
    monkeypatch.setattr(
        "quill.core.local_git.mark_conflict_resolved",
        lambda root, path, *, runner: resolved_paths.append(path),
    )
    monkeypatch.setattr(
        "quill.ui.local_git_dialogs.MergeConflictDialog",
        lambda *a, **k: SimpleNamespace(show=lambda: ["ours"]),
    )
    host._on_local_git_conflicted_files(str(repo), ["a.txt"])
    assert resolved_paths == ["a.txt"]
    assert host.statuses == ["Resolved 1 file(s)"]
    assert conflicted_file.read_text(encoding="utf-8") == "mine\n"


def test_resolve_conflicts_reports_skip_on_cancel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    conflicted_file = repo / "a.txt"
    conflicted_file.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> f\n", encoding="utf-8")

    host = _Host()
    monkeypatch.setattr(
        "quill.ui.local_git_dialogs.MergeConflictDialog",
        lambda *a, **k: SimpleNamespace(show=lambda: None),
    )
    host._on_local_git_conflicted_files(str(repo), ["a.txt"])
    assert "Skipped a.txt" in host.statuses[-1]


# ---------------------------------------------------------------------------
# Interactive rebase
# ---------------------------------------------------------------------------


def test_rebase_todo_empty_reports_no_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._on_local_git_rebase_todo("/repo", "main", [])
    assert "No commits between" in host.statuses[-1]


def test_rebase_cancelled_at_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    monkeypatch.setattr(
        "quill.ui.local_git_dialogs.InteractiveRebaseDialog",
        lambda *a, **k: SimpleNamespace(show=lambda: None),
    )
    host._on_local_git_rebase_todo("/repo", "main", [SimpleNamespace(sha="abc", subject="x")])
    assert host.statuses == ["Rebase cancelled"]


def test_rebase_result_ok_sets_status() -> None:
    host = _Host()
    host._on_local_git_rebase_result("/repo", SimpleNamespace(ok=True, message="Rebase completed."))
    assert host.statuses == ["Rebase completed."]


def test_rebase_result_conflict_offers_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._local_git_confirm = lambda message, title: True
    called: list[str] = []
    host._local_git_resolve_rebase_conflicts = lambda root: called.append(root)
    result = SimpleNamespace(ok=False, stopped_for_conflicts=True, message="stopped")
    host._on_local_git_rebase_result("/repo", result)
    assert called == ["/repo"]


# ---------------------------------------------------------------------------
# Command palette registration
# ---------------------------------------------------------------------------


def test_register_local_git_commands() -> None:
    host = _Host()
    host._register_local_git_commands()
    ids = {entry[0] for entry in host.commands.registered}
    assert ids == {
        "localgit.uncommitted_changes",
        "localgit.switch_branch",
        "localgit.stash_changes",
        "localgit.manage_stashes",
        "localgit.blame_at_cursor",
        "localgit.bisect_start",
        "localgit.bisect_reset",
        "localgit.resolve_conflicts",
        "localgit.interactive_rebase",
        "localgit.rebase_abort",
    }


class _FakeDirDialog:
    def __init__(self, path: str) -> None:
        self._path = path
        self.result = "OK"

    def GetPath(self) -> str:
        return self._path

    def __enter__(self) -> _FakeDirDialog:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeChoiceDialog:
    def __init__(self, choice: str) -> None:
        self._choice = choice
        self.result = "OK"

    def GetStringSelection(self) -> str:
        return self._choice

    def __enter__(self) -> _FakeChoiceDialog:
        return self

    def __exit__(self, *exc: object) -> None:
        return None
