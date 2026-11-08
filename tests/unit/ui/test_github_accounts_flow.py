"""The shared Manage GitHub Accounts flow, over a recorded host.

Both editors drive this one module (QUILL through ``main_frame_github_accounts``,
QUILL Lite through ``quill/apps/lite_github_accounts.py``); a second copy is how
the two would start to disagree.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from quill.ui import github_accounts_flow
from quill.ui.github_accounts_flow import GitHubAccountsFlow, GitHubAccountsHost

_FLOW = "quill.ui.github_accounts_flow"


class _Dialog:
    answer: object = "done"
    opened: list[dict] = []

    def __init__(self, parent, **kwargs) -> None:
        type(self).opened.append({"parent": parent, **kwargs})

    def show(self):
        return type(self).answer


@pytest.fixture
def host(monkeypatch):
    said: list[str] = []
    quiet: list[str] = []
    boxes: list[str] = []
    host = GitHubAccountsHost(
        parent="frame",
        set_status=said.append,
        set_status_quiet=quiet.append,
        message_box=lambda message, _caption, _style: boxes.append(message),
        run_in_background=lambda work: work(),
        call_after=lambda fn, *a, **k: fn(*a, **k),
    )
    _Dialog.opened = []
    monkeypatch.setattr("quill.ui.github_dialogs.GitHubManageAccountsDialog", _Dialog)
    return SimpleNamespace(host=host, said=said, quiet=quiet, boxes=boxes)


def _account(account_id: str, login: str) -> SimpleNamespace:
    return SimpleNamespace(id=account_id, login=login, host="github.com")


def test_switch_sets_the_active_account_and_says_which(host, monkeypatch) -> None:
    accounts = [_account("a", "alice"), _account("b", "bob")]
    switched: list[str] = []
    monkeypatch.setattr(f"{_FLOW}.set_active_github_account", lambda i: switched.append(i) or True)
    _Dialog.answer = "switch:b"

    GitHubAccountsFlow(host.host).show_manage_dialog(None, True, accounts, "a", "")

    assert switched == ["b"]
    assert host.said == ["Switched to GitHub account bob"]
    assert _Dialog.opened[0]["parent"] == "frame"


def test_remove_names_the_account_left_active(host, monkeypatch) -> None:
    left = _account("a", "alice")
    monkeypatch.setattr(f"{_FLOW}.remove_github_account", lambda _i: True)
    monkeypatch.setattr(f"{_FLOW}.list_github_accounts", lambda: [left])
    monkeypatch.setattr(f"{_FLOW}.active_github_account_id", lambda: "a")
    _Dialog.answer = "remove:b"

    GitHubAccountsFlow(host.host).show_manage_dialog(None, True, [left], "a", "")

    assert host.said == ["Removed saved token. Active account: alice"]


def test_a_saved_token_is_checked_off_the_ui_thread_before_the_dialog(host, monkeypatch) -> None:
    monkeypatch.setattr(f"{_FLOW}.load_github_token", lambda: "tok")
    monkeypatch.setattr(f"{_FLOW}.list_github_accounts", lambda: [_account("a", "alice")])
    monkeypatch.setattr(f"{_FLOW}.active_github_account_id", lambda: "a")

    class _Provider:
        last_auth_error = ""

        def __init__(self, *, token=None) -> None:
            assert token == "tok"

        def get_identity(self):
            return SimpleNamespace(login="alice")

        def close(self) -> None:
            pass

    monkeypatch.setattr(f"{_FLOW}.GitHubRemoteProvider", _Provider)
    background: list[object] = []
    host.host.run_in_background = lambda work: (background.append(work), work())

    GitHubAccountsFlow(host.host).manage()

    assert len(background) == 1
    assert _Dialog.opened[0]["login"] == "alice"
    assert _Dialog.opened[0]["has_token"] is True


def test_a_signed_in_callback_runs_only_after_the_token_is_saved(host, monkeypatch) -> None:
    monkeypatch.setattr(
        f"{_FLOW}.save_github_account", lambda login, _t: SimpleNamespace(login=login)
    )
    monkeypatch.setattr(f"{_FLOW}.delete_legacy_github_token", lambda: False)
    calls: list[str] = []
    flow = GitHubAccountsFlow(host.host, on_signed_in=lambda: calls.append("reopen"))

    flow.add_token_done("tok", None, "")
    assert calls == []
    assert host.boxes == ["GitHub did not confirm an account for that token. Nothing was saved."]

    flow.add_token_done("tok", "octocat", "")
    assert calls == ["reopen"]
    assert host.said == ["Added and switched to GitHub account octocat"]


def test_the_flow_imports_no_window_of_its_own_at_module_scope() -> None:
    source = inspect.getsource(github_accounts_flow)
    header = source.split("class GitHubAccountsHost", 1)[0]
    assert "import wx" not in header
