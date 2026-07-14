"""Tests for GitHubExtrasMixin: Organizations, Releases, Workflow dispatch,
Notifications, and Security alerts.

The test host inherits both GitHubAdminMixin and GitHubExtrasMixin, mirroring
MainFrame's real MRO -- GitHubExtrasMixin calls the shared gating helpers
(_gh_admin_ready, _gh_admin_prompt_repo, etc.) defined on GitHubAdminMixin via
self, exactly as the two mixins do in production.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.models import RemoteRepository
from quill.ui.main_frame_github_admin import GitHubAdminMixin
from quill.ui.main_frame_github_extras import GitHubExtrasMixin


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _Host(GitHubAdminMixin, GitHubExtrasMixin):
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


def _fake_token_store(monkeypatch: pytest.MonkeyPatch, token: str | None) -> None:
    monkeypatch.setattr("quill.ui.main_frame_github_admin.load_github_token", lambda: token)
    monkeypatch.setattr("quill.ui.main_frame_github_extras.load_github_token", lambda: token)


@pytest.fixture(autouse=True)
def _clear_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


class _FakeChoiceDialog:
    def __init__(self, choice: str) -> None:
        self._choice = choice
        self.result = "OK"

    def GetStringSelection(self) -> str:
        return self._choice

    def GetSelection(self) -> int:
        return 0

    def __enter__(self) -> _FakeChoiceDialog:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


def test_browse_organization_no_orgs(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    monkeypatch.setattr(
        "quill.ui.main_frame_github_extras.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(list_organizations=lambda: [], close=lambda: None),
    )
    host.github_browse_organization()
    assert host.statuses == ["This account belongs to no organizations"]


def test_browse_organization_picks_org_then_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    monkeypatch.setattr(
        "quill.ui.main_frame_github_extras.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            list_organizations=lambda: ["acme"],
            list_org_repositories=lambda org: [
                RemoteRepository(provider="github", full_name="acme/widgets")
            ],
            close=lambda: None,
        ),
    )
    host._wx = SimpleNamespace(
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog(a[3][0]), ID_OK="OK"
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    opened: list[str] = []
    host.open_github_items_viewer_for = lambda full_name: opened.append(full_name)
    host.github_browse_organization()
    assert opened == ["acme/widgets"]


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------


def test_create_release_generated_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    prompts = iter(["v1.0.0", "Version 1"])
    host._gh_admin_prompt_single = lambda title, label, value="": next(prompts, None)
    host._gh_admin_confirm = lambda message, title: True  # generate notes, then draft=True
    created = SimpleNamespace(
        tag="v1.0.0", name="Version 1", html_url="https://x", draft=True, prerelease=False
    )
    calls: list[dict] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_github_extras.GitHubRepoAdminProvider",
        lambda token: SimpleNamespace(
            create_release=lambda full, tag, **kw: (
                calls.append({"full": full, "tag": tag, **kw}) or created
            ),
            close=lambda: None,
        ),
    )
    host.github_create_release()
    assert calls[0]["tag"] == "v1.0.0"
    assert calls[0]["generate_notes"] is True
    assert "Created draft release v1.0.0" in host.statuses[-1]


# ---------------------------------------------------------------------------
# Workflow dispatch
# ---------------------------------------------------------------------------


def test_dispatch_workflow_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    prompts = iter(["ci.yml", "main"])
    host._gh_admin_prompt_single = lambda title, label, value="": next(prompts, None)
    host._gh_admin_confirm = lambda message, title: True
    dispatched: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        "quill.core.github.items_provider.GitHubItemsProvider",
        lambda token: SimpleNamespace(
            dispatch_workflow=lambda full, wf, ref: dispatched.append((full, wf, ref)),
            close=lambda: None,
        ),
    )
    host.github_dispatch_workflow()
    assert dispatched == [("owner/repo", "ci.yml", "main")]
    assert "Dispatched ci.yml" in host.statuses[-1]


def test_dispatch_workflow_declined(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    host._gh_admin_prompt_repo = lambda title: "owner/repo"
    prompts = iter(["ci.yml", "main"])
    host._gh_admin_prompt_single = lambda title, label, value="": next(prompts, None)
    host._gh_admin_confirm = lambda message, title: False
    host.github_dispatch_workflow()
    assert host.statuses == ["Dispatch cancelled"]


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def test_notifications_none() -> None:
    host = _Host()
    host._on_github_notifications_loaded([])
    assert host.statuses == ["No notifications"]


def test_notifications_selection_marks_read(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_token_store(monkeypatch, "tok")
    host = _Host()
    notification = SimpleNamespace(
        id="1",
        repository="owner/repo",
        subject_title="Bug",
        reason="mention",
        unread=True,
        url="x",
    )
    host._wx = SimpleNamespace(
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog(a[3][0]), ID_OK="OK"
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    monkeypatch.setattr("webbrowser.open", lambda url: None)
    marked: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.items_provider.GitHubItemsProvider",
        lambda token: SimpleNamespace(
            mark_notification_read=lambda nid: marked.append(nid), close=lambda: None
        ),
    )
    host._on_github_notifications_loaded([notification])
    assert marked == ["1"]


# ---------------------------------------------------------------------------
# Security alerts
# ---------------------------------------------------------------------------


def test_security_alerts_none() -> None:
    host = _Host()
    host._on_github_security_alerts_loaded([])
    assert host.statuses == ["No open security alerts"]


def test_security_alerts_opens_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host()
    alert = SimpleNamespace(
        number=1, severity="high", package="left-pad", summary="Bad", html_url="https://x"
    )
    host._wx = SimpleNamespace(
        SingleChoiceDialog=lambda *a, **k: _FakeChoiceDialog(a[3][0]), ID_OK="OK"
    )
    host._show_modal_dialog = lambda dialog, title: dialog.result
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    host._on_github_security_alerts_loaded([alert])
    assert opened == ["https://x"]


# ---------------------------------------------------------------------------
# Command palette registration
# ---------------------------------------------------------------------------


def test_register_github_extras_commands() -> None:
    host = _Host()
    host._register_github_extras_commands()
    ids = {entry[0] for entry in host.commands.registered}
    assert ids == {
        "github.browse_organization",
        "github.create_release",
        "github.dispatch_workflow",
        "github.view_notifications",
        "github.view_security_alerts",
    }
