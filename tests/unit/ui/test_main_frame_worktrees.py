"""Tests for WorktreesMixin: the Tools > Local Git > Worktrees handlers.

Same convention as ``test_main_frame_local_git.py``: wx surfaces are
short-circuited per test, ``_run_background_task`` runs synchronously, and
``quill.core.git_worktree``'s functions are patched at their defining module
so the mixin's local imports resolve to fakes. The engine itself is covered
in ``tests/unit/core/test_git_worktree.py``; this file is about the mixin's
gating, sequencing, and -- above all -- the fact that removing a worktree
with uncommitted work needs two separate confirmations.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.git_worktree import WorktreeEntry
from quill.ui.main_frame_local_git import LocalGitMixin
from quill.ui.main_frame_worktrees import WorktreesMixin

MAIN = WorktreeEntry(path="C:/repo", branch="main", head="1111111", is_main=True)
LINKED = WorktreeEntry(path="C:/repo-feature", branch="feature/x", head="2222222")
LOCKED = WorktreeEntry(path="C:/repo-usb", branch="usb", head="3333333", is_locked=True)


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _Host(WorktreesMixin, LocalGitMixin):
    def __init__(self) -> None:
        self._wx = SimpleNamespace(ICON_INFORMATION=1, OK=1)
        self.frame = object()
        self.commands = _FakeCommands()
        self.document = SimpleNamespace(path=None)
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.opened: list[Path] = []
        self.confirmations: list[bool] = []
        self.confirm_titles: list[str] = []

    def _binding_for(self, _command_id: str) -> str:
        return ""

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _local_git_runner(self) -> Any:
        return lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="", stderr="")

    def open_file(self, path: Path, **_kwargs: Any) -> None:
        self.opened.append(path)

    def _worktree_confirm(self, _message: str, title: str) -> bool:
        self.confirm_titles.append(title)
        return self.confirmations.pop(0) if self.confirmations else False

    def _run_background_task(self, label: str, work: Any, on_success: Any, **_kw: Any) -> None:
        on_success(work(lambda *_a: None))


@pytest.fixture(autouse=True)
def _clear_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


@pytest.fixture(autouse=True)
def _git_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.git_available", lambda: True)


def _result(ok: bool = True, message: str = "done", **extra: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {"worktrees": (), "pruned": ()}
    fields.update(extra)
    return SimpleNamespace(ok=ok, message=message, **fields)


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------


def test_safe_mode_blocks_worktrees(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    host = _Host()
    host.local_git_worktrees()
    assert host.statuses == ["Local git commands are disabled in Safe Mode"]


def test_missing_git_blocks_worktrees(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.git_available", lambda: False)
    host = _Host()
    host._show_message_box = lambda *_a, **_k: 0  # type: ignore[method-assign]
    host.local_git_worktrees()
    assert host.opened == []


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_failure_is_reported_not_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._local_git_repo_root = lambda: "C:/repo"  # type: ignore[method-assign]
    monkeypatch.setattr(
        "quill.core.git_worktree.list_worktrees",
        lambda *_a, **_k: _result(False, "Not a git repository."),
    )
    host.local_git_worktrees()
    assert host.statuses == ["Not a git repository."]


def test_worktree_entries_returns_empty_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    monkeypatch.setattr(
        "quill.core.git_worktree.list_worktrees", lambda *_a, **_k: _result(False, "nope")
    )
    assert host._worktree_entries("C:/repo") == ()


def test_branch_chooser_hides_branches_already_checked_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host()
    monkeypatch.setattr(
        "quill.core.git_worktree.list_worktrees",
        lambda *_a, **_k: _result(True, "ok", worktrees=(MAIN, LINKED)),
    )
    monkeypatch.setattr(
        "quill.core.local_git.list_local_branches",
        lambda *_a, **_k: [
            SimpleNamespace(name="main"),
            SimpleNamespace(name="feature/x"),
            SimpleNamespace(name="spike"),
        ],
    )
    assert host._worktree_branch_names("C:/repo") == ["spike"]


# ---------------------------------------------------------------------------
# Remove: two confirmations, never a silent force
# ---------------------------------------------------------------------------


def test_remove_declined_keeps_the_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host.confirmations = [False]
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "quill.core.git_worktree.remove_worktree",
        lambda *a, **k: calls.append(k) or _result(True, "removed"),
    )
    assert host._worktree_remove("C:/repo", LINKED) == "Worktree kept."
    assert calls == []


def test_remove_confirmed_calls_git_without_force(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host.confirmations = [True]
    seen: list[bool] = []

    def fake_remove(_runner: Any, _root: str, _path: str, *, force: bool = False) -> Any:
        seen.append(force)
        return _result(True, "Removed the worktree at C:/repo-feature.")

    monkeypatch.setattr("quill.core.git_worktree.remove_worktree", fake_remove)
    message = host._worktree_remove("C:/repo", LINKED)
    assert seen == [False]
    assert message.startswith("Removed the worktree")


def test_remove_with_uncommitted_changes_asks_again_before_forcing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host()
    host.confirmations = [True, True]
    seen: list[bool] = []

    def fake_remove(_runner: Any, _root: str, _path: str, *, force: bool = False) -> Any:
        seen.append(force)
        if force:
            return _result(True, "Removed the worktree at C:/repo-feature.")
        return _result(False, "C:/repo-feature still has changes that are not committed.")

    monkeypatch.setattr("quill.core.git_worktree.remove_worktree", fake_remove)
    host._worktree_remove("C:/repo", LINKED)
    assert seen == [False, True]
    assert host.confirm_titles == ["Remove Worktree", "Discard Changes"]


def test_remove_with_uncommitted_changes_respects_a_no(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host.confirmations = [True, False]
    seen: list[bool] = []

    def fake_remove(_runner: Any, _root: str, _path: str, *, force: bool = False) -> Any:
        seen.append(force)
        return _result(False, "C:/repo-feature still has changes that are not committed.")

    monkeypatch.setattr("quill.core.git_worktree.remove_worktree", fake_remove)
    assert host._worktree_remove("C:/repo", LINKED) == "Worktree kept, with its changes."
    assert seen == [False]


# ---------------------------------------------------------------------------
# Lock / unlock / prune
# ---------------------------------------------------------------------------


def test_lock_toggle_unlocks_a_locked_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    monkeypatch.setattr(
        "quill.core.git_worktree.unlock_worktree", lambda *_a, **_k: _result(True, "Unlocked.")
    )
    assert host._worktree_lock_toggle("C:/repo", LOCKED) == "Unlocked."


def test_lock_toggle_prompts_for_a_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._worktree_prompt = lambda *_a, **_k: "on a USB drive"  # type: ignore[method-assign]
    seen: list[str] = []

    def fake_lock(_runner: Any, _root: str, _path: str, *, reason: str = "") -> Any:
        seen.append(reason)
        return _result(True, "Locked.")

    monkeypatch.setattr("quill.core.git_worktree.lock_worktree", fake_lock)
    assert host._worktree_lock_toggle("C:/repo", LINKED) == "Locked."
    assert seen == ["on a USB drive"]


def test_lock_cancelled_at_the_reason_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._worktree_prompt = lambda *_a, **_k: None  # type: ignore[method-assign]
    assert host._worktree_lock_toggle("C:/repo", LINKED) == "Lock cancelled."


def test_prune_reports_the_engine_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    monkeypatch.setattr(
        "quill.core.git_worktree.prune_worktrees",
        lambda *_a, **_k: _result(True, "Nothing to tidy up: every worktree is still on disk."),
    )
    assert host._worktree_prune("C:/repo").startswith("Nothing to tidy up")


# ---------------------------------------------------------------------------
# Open in QUILL
# ---------------------------------------------------------------------------


def _two_worktrees(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "notes").mkdir()
    (repo / "notes" / "a.md").write_text("main copy", encoding="utf-8")
    other = tmp_path / "repo-feature"
    (other / "notes").mkdir(parents=True)
    return repo, other


def test_open_opens_the_counterpart_document(tmp_path: Path) -> None:
    repo, other = _two_worktrees(tmp_path)
    (other / "notes" / "a.md").write_text("feature copy", encoding="utf-8")
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "notes" / "a.md"))
    entry = WorktreeEntry(path=str(other), branch="feature/x")
    message, opened = host._worktree_open(entry)
    assert opened is True
    assert host.opened == [other / "notes" / "a.md"]
    assert "a.md" in message


def test_open_without_a_counterpart_offers_a_picker(tmp_path: Path) -> None:
    repo, other = _two_worktrees(tmp_path)
    host = _Host()
    host.document = SimpleNamespace(path=str(repo / "notes" / "a.md"))
    host._worktree_pick_file = lambda _p: None  # type: ignore[method-assign]
    entry = WorktreeEntry(path=str(other), branch="feature/x")
    message, opened = host._worktree_open(entry)
    assert opened is False
    assert "Nothing opened" in message
    assert host.opened == []


def test_open_uses_the_picked_file_when_there_is_no_counterpart(tmp_path: Path) -> None:
    _repo, other = _two_worktrees(tmp_path)
    picked = other / "notes" / "b.md"
    picked.write_text("other", encoding="utf-8")
    host = _Host()
    host._worktree_pick_file = lambda _p: picked  # type: ignore[method-assign]
    entry = WorktreeEntry(path=str(other), branch="feature/x")
    message, opened = host._worktree_open(entry)
    assert opened is True
    assert host.opened == [picked]
    assert "b.md" in message


def test_counterpart_is_none_without_an_open_document(tmp_path: Path) -> None:
    _repo, other = _two_worktrees(tmp_path)
    host = _Host()
    assert host._worktree_counterpart(str(other)) is None


# ---------------------------------------------------------------------------
# Command palette registration
# ---------------------------------------------------------------------------


def test_register_worktree_commands() -> None:
    host = _Host()
    host._register_worktree_commands()
    ids = {entry[0] for entry in host.commands.registered}
    assert ids == {"localgit.worktrees", "localgit.new_worktree"}
