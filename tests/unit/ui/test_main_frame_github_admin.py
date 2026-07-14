"""Tests for GitHubAdminMixin: repository-lifecycle GitHub commands.

Mirrors test_main_frame_git_sync.py's convention: wx dialog helpers are
monkeypatched directly per test (never real wx), _run_background_task is
faked to run synchronously, and provider classes are monkeypatched at their
defining module so the mixin's local imports resolve to fakes.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.models import RemoteRepository
from quill.ui.main_frame_github_admin import GitHubAdminMixin


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _Host(GitHubAdminMixin):
    def __init__(self, *, token: str = "tok") -> None:
        self._wx = SimpleNamespace()
        self.frame = object()
        self.settings = SimpleNamespace(git_sync_last_folder="")
        self.commands = _FakeCommands()
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.background_tasks: list[tuple[str, Any]] = []
        self._token = token
        self._ready = True
        self._signin_offered_and_accepted = False

    # -- fakes standing in for methods contributed by other mixins/MainFrame --
    def _binding_for(self, _command_id: str) -> str:
        return ""

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _show_modal_dialog(self, _dialog: object, _title: str) -> int:  # pragma: no cover
        raise AssertionError("wx dialogs must be short-circuited by per-test patches")

    def _run_background_task(self, label: str, work: Any, on_success: Any, **_kw: Any) -> None:
        self.background_tasks.append((label, work))
        on_success(work(lambda *_a: None))

    def _ensure_github_ready(self) -> bool:
        return self._ready

    def _github_items_initial_repo(self) -> str:
        return "owner/repo"

    def _github_add_token(self) -> None:
        self._signin_offered_and_accepted = True
        self._token = "new-token"

    def _choose_git_sync_folder(self) -> str | None:
        return "/synced/folder"

    def _save_settings_quietly(self) -> None:
        pass

    def _run_git_folder_sync(self, folder: str) -> None:
        self.background_tasks.append((f"sync {folder}", None))


def _fake_token_store(monkeypatch: pytest.MonkeyPatch, token: str | None) -> None:
    monkeypatch.setattr("quill.ui.main_frame_github_admin.load_github_token", lambda: token)


@pytest.fixture(autouse=True)
def _clear_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


# ---------------------------------------------------------------------------
# Gating: Safe Mode, consent, token
# ---------------------------------------------------------------------------


def test_safe_mode_blocks_every_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    host = _Host()
    host.github_create_repository()
    assert host.statuses == ["GitHub repository actions are disabled in Safe Mode"]
    assert host.background_tasks == []


def test_missing_consent_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._ready = False
    host.github_create_repository()
    assert host.background_tasks == []


def test_missing_token_offers_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, None)
    host = _Host()
    host._gh_admin_confirm = lambda message, title: True
    host._gh_admin_prompt_repo = lambda title: None  # short-circuit after sign-in
    host.github_rename_repository()
    assert host._signin_offered_and_accepted is True


def test_declining_sign_in_stops_the_command(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, None)
    host = _Host()
    host._gh_admin_confirm = lambda message, title: False
    result = host._gh_admin_ready()
    assert result is None
    assert host._signin_offered_and_accepted is False


# ---------------------------------------------------------------------------
# Create repository (+ the offer to wire QUILL Sync locally)
# ---------------------------------------------------------------------------


def test_create_repository_cancelled_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.CreateRepositoryDialog",
        lambda parent: SimpleNamespace(show=lambda: None),
    )
    host.github_create_repository()
    assert host.statuses == ["Repository creation cancelled"]
    assert host.background_tasks == []


def test_create_repository_calls_provider_and_offers_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    create_result = SimpleNamespace(name="new-repo", description="d", private=True, org="")
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.CreateRepositoryDialog",
        lambda parent: SimpleNamespace(show=lambda: create_result),
    )
    created_repo = RemoteRepository(
        provider="github",
        full_name="me/new-repo",
        is_private=True,
        html_url="https://github.com/me/new-repo",
    )
    calls: list[tuple[str, bool, str, str]] = []

    class _FakeAdmin:
        def __init__(self, token: str) -> None:
            self.token = token

        def create_repository(self, name: str, *, private: bool, description: str, org: str):
            calls.append((name, private, description, org))
            return created_repo

        def close(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.main_frame_github_admin.GitHubRepoAdminProvider", _FakeAdmin)
    host._gh_admin_confirm = lambda message, title: True  # accept the "sync now?" offer
    monkeypatch.setattr(
        "quill.core.git_sync.init_repo_with_remote",
        lambda *a, **k: SimpleNamespace(ok=True, message="ready"),
    )

    host.github_create_repository()

    assert calls == [("new-repo", True, "d", "")]
    assert any("Created me/new-repo" in s for s in host.statuses)
    assert ("sync /synced/folder", None) in host.background_tasks


def test_create_repository_declines_local_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    create_result = SimpleNamespace(name="r", description="", private=False, org="")
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.CreateRepositoryDialog",
        lambda parent: SimpleNamespace(show=lambda: create_result),
    )
    created_repo = RemoteRepository(
        provider="github", full_name="me/r", html_url="https://github.com/me/r"
    )
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            create_repository=lambda *a, **k: created_repo, close=lambda: None
        ),
    )
    host._gh_admin_confirm = lambda message, title: False
    host.github_create_repository()
    # Only the repo-creation task ran; no follow-up local-sync task was queued.
    assert len(host.background_tasks) == 1
    assert host.background_tasks[0][0] == "Creating r"


# ---------------------------------------------------------------------------
# Rename repository (typed confirm)
# ---------------------------------------------------------------------------


def test_rename_requires_typed_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    host._gh_admin_prompt_single = lambda title, label, value="": "new-name"
    host._gh_admin_typed_confirm = lambda **kwargs: False
    host.github_rename_repository()
    assert host.statuses == ["Rename cancelled"]
    assert host.background_tasks == []


def test_rename_calls_provider_on_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    host._gh_admin_prompt_single = lambda title, label, value="": "new-name"
    host._gh_admin_typed_confirm = lambda **kwargs: True
    renamed = RemoteRepository(provider="github", full_name="owner/new-name")
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            rename_repository=lambda full, new: calls.append((full, new)) or renamed,
            close=lambda: None,
        ),
    )
    host.github_rename_repository()
    assert calls == [("owner/repo", "new-name")]
    assert host.statuses == ["Renamed to owner/new-name"]


# ---------------------------------------------------------------------------
# Visibility change (typed confirm)
# ---------------------------------------------------------------------------


def test_visibility_change_flips_and_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    current = RemoteRepository(provider="github", full_name="owner/repo", is_private=False)
    monkeypatch.setattr(
        "quill.core.github.github_provider.GitHubRemoteProvider",
        lambda token: SimpleNamespace(get_repository=lambda name: current, close=lambda: None),
    )
    seen_messages: list[str] = []
    host._gh_admin_typed_confirm = lambda **kwargs: seen_messages.append(kwargs["message"]) or True
    updated = RemoteRepository(provider="github", full_name="owner/repo", is_private=True)
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            set_visibility=lambda full, *, private: updated, close=lambda: None
        ),
    )
    host.github_change_repository_visibility()
    assert "currently public" in seen_messages[0]
    assert host.statuses == ["owner/repo is now private"]


def test_visibility_change_declined(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    current = RemoteRepository(provider="github", full_name="owner/repo", is_private=False)
    monkeypatch.setattr(
        "quill.core.github.github_provider.GitHubRemoteProvider",
        lambda token: SimpleNamespace(get_repository=lambda name: current, close=lambda: None),
    )
    host._gh_admin_typed_confirm = lambda **kwargs: False
    host.github_change_repository_visibility()
    assert host.statuses == ["Visibility change cancelled"]


# ---------------------------------------------------------------------------
# Delete branch (typed confirm, default branch excluded)
# ---------------------------------------------------------------------------


def test_delete_branch_excludes_default_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    repo_meta = RemoteRepository(provider="github", full_name="owner/repo", default_branch="main")
    monkeypatch.setattr(
        "quill.core.github.github_provider.GitHubRemoteProvider",
        lambda token: SimpleNamespace(get_repository=lambda name: repo_meta, close=lambda: None),
    )
    branches = [SimpleNamespace(name="main"), SimpleNamespace(name="feature-x")]
    monkeypatch.setattr(
        "quill.core.github.items_provider.GitHubItemsProvider",
        lambda token: SimpleNamespace(
            fetch_branches=lambda name, limit: branches, close=lambda: None
        ),
    )
    seen_names: list[list[str]] = []

    def fake_names(_token: str, _full_name: str, names: list[str]) -> None:
        seen_names.append(names)

    host._on_github_branches_for_delete = fake_names  # inspect the filtered list directly
    host.github_delete_branch()
    assert seen_names == [["feature-x"]]


def test_delete_branch_typed_confirm_and_call(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            delete_branch=lambda full, branch: deleted.append((full, branch)),
            close=lambda: None,
        ),
    )
    host._wx = SimpleNamespace(
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog("feature-x"),
        ID_OK="OK",
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    host._gh_admin_typed_confirm = lambda **kwargs: True
    host._on_github_branches_for_delete("tok", "owner/repo", ["feature-x"])
    assert deleted == [("owner/repo", "feature-x")]
    assert host.statuses == ["Deleted branch feature-x from owner/repo"]


class _FakeChoiceDialog:
    def __init__(self, choice: str) -> None:
        self._choice = choice
        self.result = "OK"  # matches the fake wx.ID_OK sentinel in the test

    def GetStringSelection(self) -> str:
        return self._choice

    def GetSelection(self) -> int:
        return 0

    def __enter__(self) -> _FakeChoiceDialog:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# ---------------------------------------------------------------------------
# Fork repository
# ---------------------------------------------------------------------------


def test_fork_repository_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    prompts = iter(["acme"])
    host._gh_admin_prompt_single = lambda title, label: next(prompts, None)
    forked = RemoteRepository(
        provider="github", full_name="acme/repo", html_url="https://github.com/acme/repo"
    )
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            fork_repository=lambda full, *, org: calls.append((full, org)) or forked,
            close=lambda: None,
        ),
    )
    host._gh_admin_confirm = lambda message, title: False  # decline the follow-up sync offer
    host.github_fork_repository()
    assert calls == [("owner/repo", "acme")]
    assert any("Created acme/repo" in s for s in host.statuses)


# ---------------------------------------------------------------------------
# Default branch change
# ---------------------------------------------------------------------------


def test_change_default_branch_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    calls: list[tuple[str, str]] = []
    updated = RemoteRepository(provider="github", full_name="owner/repo", default_branch="develop")
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            set_default_branch=lambda full, branch: calls.append((full, branch)) or updated,
            close=lambda: None,
        ),
    )
    host._wx = SimpleNamespace(
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog("develop"),
        ID_OK="OK",
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    host._on_github_branches_for_default("tok", "owner/repo", ["main", "develop"])
    assert calls == [("owner/repo", "develop")]
    assert host.statuses == ["owner/repo's default branch is now develop"]


# ---------------------------------------------------------------------------
# Branch protection
# ---------------------------------------------------------------------------


def test_branch_protection_applies_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    from quill.ui.github_repo_admin_dialogs import BranchProtectionResult

    result = BranchProtectionResult(
        branch="main",
        remove=False,
        required_approving_review_count=2,
        required_status_checks=("ci",),
        enforce_admins=True,
    )
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.BranchProtectionDialog",
        lambda parent, *, branches, default_branch: SimpleNamespace(show=lambda: result),
    )
    calls: list[tuple[str, str, int, tuple, bool]] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            set_branch_protection=lambda full, branch, **kw: calls.append((
                full,
                branch,
                kw["required_approving_review_count"],
                kw["required_status_checks"],
                kw["enforce_admins"],
            )),
            close=lambda: None,
        ),
    )
    host._gh_admin_confirm = lambda message, title: True
    host._on_github_branch_protection_loaded("tok", "owner/repo", ("main", ("main", "dev")))
    assert calls == [("owner/repo", "main", 2, ("ci",), True)]
    assert host.statuses == ["Protected main in owner/repo"]


def test_branch_protection_removal(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    from quill.ui.github_repo_admin_dialogs import BranchProtectionResult

    result = BranchProtectionResult(
        branch="main",
        remove=True,
        required_approving_review_count=None,
        required_status_checks=(),
        enforce_admins=False,
    )
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.BranchProtectionDialog",
        lambda parent, *, branches, default_branch: SimpleNamespace(show=lambda: result),
    )
    removed: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            remove_branch_protection=lambda full, branch: removed.append((full, branch)),
            close=lambda: None,
        ),
    )
    host._gh_admin_confirm = lambda message, title: True
    host._on_github_branch_protection_loaded("tok", "owner/repo", ("main", ("main",)))
    assert removed == [("owner/repo", "main")]
    assert host.statuses == ["Removed protection from main in owner/repo"]


# ---------------------------------------------------------------------------
# Multi-file commit
# ---------------------------------------------------------------------------


def test_commit_multiple_files_reads_and_commits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    _fake_token_store(monkeypatch, "tok")
    from pathlib import Path

    tmp_dir = Path(str(tmp_path))
    file_a = tmp_dir / "a.txt"
    file_a.write_text("hello", encoding="utf-8")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    host._wx = SimpleNamespace(
        FileDialog=lambda *a, **k: _FakeFileDialog([str(file_a)]),
        FD_OPEN=1,
        FD_MULTIPLE=2,
        FD_FILE_MUST_EXIST=4,
        ID_OK="OK",
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    prompts = iter(["main", "Add a.txt"])
    host._gh_admin_prompt_single = lambda title, label, value="": next(prompts, None)
    host._gh_admin_confirm = lambda message, title: True
    calls: list[tuple[str, str, list, str]] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_admin.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            commit_files=lambda full, branch, files, message: (
                calls.append((full, branch, files, message)) or "abcdef1234567890"
            ),
            close=lambda: None,
        ),
    )
    host.github_commit_multiple_files()
    assert len(calls) == 1
    full, branch, files, message = calls[0]
    assert full == "owner/repo" and branch == "main" and message == "Add a.txt"
    assert files == [("a.txt", b"hello")]
    assert host.statuses == ["Committed 1 file(s) to owner/repo (abcdef1)"]


class _FakeFileDialog:
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths
        self.result = "OK"

    def GetPaths(self) -> list[str]:
        return self._paths

    def __enter__(self) -> _FakeFileDialog:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# ---------------------------------------------------------------------------
# Command palette registration
# ---------------------------------------------------------------------------


def test_register_github_admin_commands() -> None:
    host = _Host()
    host._register_github_admin_commands()
    ids = {entry[0] for entry in host.commands.registered}
    assert ids == {
        "github.create_repository",
        "github.fork_repository",
        "github.rename_repository",
        "github.change_repository_visibility",
        "github.change_default_branch",
        "github.configure_branch_protection",
        "github.delete_branch",
        "github.commit_multiple_files",
    }
