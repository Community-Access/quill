"""Tests for GitSyncMixin: the "Sync Folder with GitHub" command flow.

The three wx-dialog helpers (_choose_git_sync_folder / _git_sync_prompt_single
/ _git_sync_confirm) are monkeypatched directly per test rather than faking
wx.Dialog machinery -- what matters here is the orchestration: Safe Mode
gating, the ready/not-ready branch, the init-then-sync sequence, and conflict
reporting. _run_background_task is faked to run synchronously so the async
worker/on_success shape is exercised without real threads.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.git_sync import GitRepoStatus
from quill.core.vault.sync import SyncResult
from quill.ui.main_frame_git_sync import GitSyncMixin


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _Host(GitSyncMixin):
    def __init__(self) -> None:
        self._wx = SimpleNamespace()  # never touched: dialog helpers are patched per test
        self.frame = object()
        self.settings = SimpleNamespace(git_sync_last_folder="")
        self.document = SimpleNamespace(path=None)
        self.commands = _FakeCommands()
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
        raise AssertionError("wx dialogs must be short-circuited by the per-test patches")

    def _run_background_task(self, label: str, work: Any, on_success: Any, **_kw: Any) -> None:
        self.background_tasks.append((label, work))
        on_success(work(lambda *_a: None))


@pytest.fixture(autouse=True)
def _clear_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


def test_safe_mode_blocks_the_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    host = _Host()
    host.sync_folder_with_github()
    assert host.statuses == ["Folder sync is disabled in Safe Mode"]
    assert host.background_tasks == []


def test_cancelled_when_no_folder_is_chosen() -> None:
    host = _Host()
    host._choose_git_sync_folder = lambda: None
    host.sync_folder_with_github()
    assert host.statuses == ["Folder sync cancelled"]
    assert host.background_tasks == []


def test_chosen_folder_is_remembered_in_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._choose_git_sync_folder = lambda: "/my/folder"
    monkeypatch.setattr("quill.core.settings.save_settings", lambda _s: None)
    # Ready status so the flow completes without needing more patches.
    monkeypatch.setattr(
        "quill.core.git_sync.check_repo_status",
        lambda root, runner: GitRepoStatus(True, True, "https://x", "main"),
    )
    monkeypatch.setattr(
        "quill.core.git_sync.sync_folder_via_git",
        lambda root, runner: SyncResult(True, "Folder synced.", ()),
    )
    host.sync_folder_with_github()
    assert host.settings.git_sync_last_folder == "/my/folder"
    assert host.statuses[-1] == "Folder synced."


def test_ready_status_runs_sync_directly(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    monkeypatch.setattr(
        "quill.core.git_sync.sync_folder_via_git",
        lambda root, runner: SyncResult(True, "Folder synced.", ()),
    )
    host._on_git_sync_status_checked("/folder", GitRepoStatus(True, True, "https://x", "main"))
    # _set_status alone (it already speaks) -- no separate _announce, or this
    # would speak the same line twice (the #728 double-announce pattern).
    assert host.statuses == ["Folder synced."]
    assert host.announcements == []


def test_not_ready_status_goes_to_setup_flow() -> None:
    host = _Host()
    prepared: list[str] = []
    host._prepare_git_sync_folder = lambda folder, status: prepared.append(folder)
    host._on_git_sync_status_checked("/folder", GitRepoStatus(False, False))
    assert prepared == ["/folder"]


def test_prepare_declines_without_confirmation() -> None:
    host = _Host()
    host._git_sync_confirm = lambda message, title: False
    host._prepare_git_sync_folder("/folder", GitRepoStatus(False, False))
    assert host.statuses == ["Folder sync cancelled"]
    assert host.background_tasks == []


def test_prepare_declines_without_a_remote_url() -> None:
    host = _Host()
    host._git_sync_confirm = lambda message, title: True
    host._git_sync_prompt_single = lambda title, label: None
    host._prepare_git_sync_folder("/folder", GitRepoStatus(True, False))
    assert host.statuses == ["Folder sync cancelled — no repository URL given"]
    assert host.background_tasks == []


def test_prepare_message_distinguishes_no_repo_from_no_remote() -> None:
    host = _Host()
    seen: list[str] = []
    host._git_sync_confirm = lambda message, title: seen.append(message) or False

    host._prepare_git_sync_folder("/folder", GitRepoStatus(False, False))
    assert "not a git repository yet" in seen[0]

    host._prepare_git_sync_folder("/folder", GitRepoStatus(True, False))
    assert "has no remote configured" in seen[1]


def test_prepare_inits_then_syncs_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._git_sync_confirm = lambda message, title: True
    host._git_sync_prompt_single = lambda title, label: "https://github.com/o/r.git"
    init_calls: list[tuple[str, str]] = []

    def fake_init(root: str, remote_url: str, *, runner: Any) -> SyncResult:
        init_calls.append((root, remote_url))
        return SyncResult(True, "Folder is ready to sync.", ())

    monkeypatch.setattr("quill.core.git_sync.init_repo_with_remote", fake_init)
    synced: list[str] = []
    host._run_git_folder_sync = lambda folder: synced.append(folder)

    host._prepare_git_sync_folder("/folder", GitRepoStatus(False, False))

    assert init_calls == [("/folder", "https://github.com/o/r.git")]
    assert synced == ["/folder"]


def test_prepare_stops_and_reports_when_init_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._git_sync_confirm = lambda message, title: True
    host._git_sync_prompt_single = lambda title, label: "https://github.com/o/r.git"
    monkeypatch.setattr(
        "quill.core.git_sync.init_repo_with_remote",
        lambda root, remote_url, *, runner: SyncResult(
            False, "Could not set the remote repository.", ()
        ),
    )
    host._run_git_folder_sync = lambda folder: pytest.fail("must not sync after a failed init")

    host._prepare_git_sync_folder("/folder", GitRepoStatus(True, False))

    # _set_status alone (it already speaks) -- no separate _announce.
    assert host.statuses == ["Could not set the remote repository."]
    assert host.announcements == []


def test_sync_done_success_sets_status_once_not_twice() -> None:
    host = _Host()
    host._on_git_folder_sync_done(SyncResult(True, "Folder synced.", ()))
    # _set_status alone (it already speaks) -- calling _announce too would be
    # the #728 double-announce pattern the repo gate catches.
    assert host.statuses == ["Folder synced."]
    assert host.announcements == []


def test_sync_done_lists_conflicts_without_auto_resolving(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    calls: list[tuple[Any, str, Any]] = []
    monkeypatch.setattr(
        "quill.ui.vault_dialogs.show_vault_list_modal",
        lambda frame, heading, items, on_activate=None: calls.append((frame, heading, items)),
    )
    result = SyncResult(False, "2 file(s) changed in both places.", ("a.md", "b.md"))
    host._on_git_folder_sync_done(result)
    assert len(calls) == 1
    _frame, heading, items = calls[0]
    assert heading == "Sync conflicts — resolve, then sync again"
    assert items == [("a.md", None), ("b.md", None)]
    assert host.statuses == ["2 file(s) changed in both places."]


def test_register_git_sync_commands() -> None:
    host = _Host()
    host._register_git_sync_commands()
    ids = [entry[0] for entry in host.commands.registered]
    assert "sync.sync_folder" in ids
    entry = next(e for e in host.commands.registered if e[0] == "sync.sync_folder")
    assert entry[2] == host.sync_folder_with_github
