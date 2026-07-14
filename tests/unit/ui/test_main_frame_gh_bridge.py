"""Tests for GhBridgeMixin: Codespaces and Copilot CLI command handlers.

Mirrors test_main_frame_local_git.py's convention: quill.core.git_binaries
and quill.core.github.gh_bridge are monkeypatched at their defining module,
_run_background_task runs synchronously, and wx dialog helpers are
monkeypatched per test. The host inherits GitHubAdminMixin too, since
github_create_codespace reuses its _gh_admin_prompt_repo helper -- the same
sibling-mixin-sharing-self pattern used throughout this codebase.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui.main_frame_gh_bridge import GhBridgeMixin
from quill.ui.main_frame_github_admin import GitHubAdminMixin


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _Host(GitHubAdminMixin, GhBridgeMixin):
    def __init__(self) -> None:
        self._wx = SimpleNamespace(ICON_INFORMATION=1, OK=1)
        self.frame = object()
        self.commands = _FakeCommands()
        self.settings = SimpleNamespace(git_sync_last_folder="")
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.background_tasks: list[tuple[str, Any]] = []
        self.message_boxes: list[tuple[str, str]] = []
        self._ready = True

    def _binding_for(self, _command_id: str) -> str:
        return ""

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _show_modal_dialog(self, _dialog: object, _title: str) -> int:  # pragma: no cover
        raise AssertionError("wx dialogs must be short-circuited by per-test patches")

    def _show_message_box(self, message: str, title: str, _style: int) -> int:
        self.message_boxes.append((message, title))
        return 0

    def _run_background_task(self, label: str, work: Any, on_success: Any, **_kw: Any) -> None:
        self.background_tasks.append((label, work))
        on_success(work(lambda *_a: None))

    def _ensure_github_ready(self) -> bool:
        return self._ready

    def _github_items_initial_repo(self) -> str:
        return "owner/repo"


@pytest.fixture(autouse=True)
def _clear_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


@pytest.fixture(autouse=True)
def _gh_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.resolve_gh", lambda: "/usr/bin/gh")


class _FakeChoiceDialog:
    def __init__(self, choice_index: int = 0) -> None:
        self._choice_index = choice_index
        self.result = "OK"

    def GetSelection(self) -> int:
        return self._choice_index

    def __enter__(self) -> _FakeChoiceDialog:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------


def test_safe_mode_blocks_every_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    host = _Host()
    host.github_list_codespaces()
    assert host.statuses == ["GitHub CLI commands are disabled in Safe Mode"]
    assert host.background_tasks == []


def test_missing_gh_shows_a_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.resolve_gh", lambda: None)
    host = _Host()
    host.github_list_codespaces()
    assert host.background_tasks == []
    assert host.message_boxes  # a "not found" message was shown


# ---------------------------------------------------------------------------
# Codespaces list / stop / delete
# ---------------------------------------------------------------------------


def test_list_codespaces_none_present(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    monkeypatch.setattr("quill.core.github.gh_bridge.list_codespaces", lambda gh_path, runner: [])
    host.github_list_codespaces()
    assert "No codespaces" in host.statuses[-1]


def test_list_codespaces_stop_via_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    codespace = SimpleNamespace(
        name="cs1", display_name="cs1", repository="owner/repo", state="Available"
    )
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.list_codespaces", lambda gh_path, runner: [codespace]
    )
    stopped: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.stop_codespace",
        lambda name, gh_path, runner: stopped.append(name),
    )
    host._wx = SimpleNamespace(
        ICON_INFORMATION=1,
        OK=1,
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog(0),
        ID_OK="OK",
        Menu=object,
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    host._gh_bridge_stop_codespace("cs1")
    assert stopped == ["cs1"]
    assert host.statuses == ["Stopped cs1"]


def test_delete_codespace_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_bridge_confirm = lambda message, title: False
    deleted: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.delete_codespace",
        lambda name, gh_path, runner: deleted.append(name),
    )
    host._gh_bridge_delete_codespace("cs1")
    assert deleted == []
    assert host.statuses == ["Delete cancelled"]


def test_delete_codespace_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_bridge_confirm = lambda message, title: True
    deleted: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.delete_codespace",
        lambda name, gh_path, runner: deleted.append(name),
    )
    host._gh_bridge_delete_codespace("cs1")
    assert deleted == ["cs1"]
    assert host.statuses == ["Deleted cs1"]


# ---------------------------------------------------------------------------
# Create codespace (cost-aware confirmation)
# ---------------------------------------------------------------------------


def test_create_codespace_declined(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    host._gh_bridge_prompt_single = lambda title, label, value="": ""
    seen_messages: list[str] = []
    host._gh_bridge_confirm = lambda message, title: seen_messages.append(message) or False
    created: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.create_codespace",
        lambda repo, branch, gh_path, runner: created.append(repo),
    )
    host.github_create_codespace()
    assert created == []
    assert host.statuses == ["Codespace creation cancelled"]
    assert "cost" in seen_messages[0].lower()


def test_create_codespace_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    host._gh_bridge_prompt_single = lambda title, label, value="": "feature"
    host._gh_bridge_confirm = lambda message, title: True
    info = SimpleNamespace(display_name="cs1", state="Provisioning")
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.create_codespace",
        lambda repo, branch, gh_path, runner: calls.append((repo, branch)) or info,
    )
    host.github_create_codespace()
    assert calls == [("owner/repo", "feature")]
    assert "Created codespace cs1" in host.statuses[-1]


# ---------------------------------------------------------------------------
# Copilot suggest / explain
# ---------------------------------------------------------------------------


def test_copilot_suggest_shows_result(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_bridge_prompt_single = lambda title, label, value="": "undo last commit"
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.copilot_suggest",
        lambda query, gh_path, runner: "git reset --soft HEAD~1",
    )
    host.github_copilot_suggest()
    assert host.message_boxes[0][0] == "git reset --soft HEAD~1"
    assert host.message_boxes[0][1] == "Copilot Suggestion"


def test_copilot_suggest_cancelled_at_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_bridge_prompt_single = lambda title, label, value="": None
    host.github_copilot_suggest()
    assert host.message_boxes == []
    assert host.background_tasks == []


def test_copilot_explain_shows_result(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    host._gh_bridge_prompt_single = lambda title, label, value="": "git rebase -i HEAD~3"
    monkeypatch.setattr(
        "quill.core.github.gh_bridge.copilot_explain",
        lambda command, gh_path, runner: "This starts an interactive rebase...",
    )
    host.github_copilot_explain()
    assert "interactive rebase" in host.message_boxes[0][0]
    assert host.message_boxes[0][1] == "Copilot Explanation"


# ---------------------------------------------------------------------------
# Command palette registration
# ---------------------------------------------------------------------------


def test_register_gh_bridge_commands() -> None:
    host = _Host()
    host._register_gh_bridge_commands()
    ids = {entry[0] for entry in host.commands.registered}
    assert ids == {
        "github.list_codespaces",
        "github.create_codespace",
        "github.copilot_suggest",
        "github.copilot_explain",
    }
