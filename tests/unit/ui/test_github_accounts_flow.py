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
        f"{_FLOW}.save_github_account", lambda login, _t, **_k: SimpleNamespace(login=login)
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


def test_sign_in_with_github_is_checked_and_saved_like_a_pasted_token(host, monkeypatch) -> None:
    saved: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        f"{_FLOW}.save_github_account",
        lambda login, token, added_by="", host="github.com": (
            saved.append((login, token, added_by)) or SimpleNamespace(login=login)
        ),
    )
    monkeypatch.setattr(f"{_FLOW}.delete_legacy_github_token", lambda: False)
    asked: list[dict] = []

    def sign_in_with_github(parent, app_name, announce, **kwargs):
        asked.append({"parent": parent, "app": app_name, **kwargs})
        return "gho_new"

    monkeypatch.setattr("quill.ui.github_device_sign_in.sign_in_with_github", sign_in_with_github)

    class _Provider:
        last_auth_error = ""

        def __init__(self, *, token=None) -> None:
            assert token == "gho_new"

        def get_identity(self):
            return SimpleNamespace(login="octocat")

        def close(self) -> None:
            pass

    monkeypatch.setattr(f"{_FLOW}.GitHubRemoteProvider", _Provider)
    submitted: list[object] = []
    host.host.submit = lambda *a, **k: submitted.append(a)
    host.host.app_name = "QUILL Lite"
    _Dialog.answer = "sign_in"

    GitHubAccountsFlow(host.host).show_manage_dialog(None, False, [], None, "")

    assert asked[0]["parent"] == "frame" and asked[0]["app"] == "QUILL Lite"
    assert asked[0]["submit"] is host.host.submit  # the host's task submitter, not a thread
    assert host.quiet == ["Checking the GitHub account..."]
    # Saved as signed in, which is what keeps the token suggestion away from it.
    assert saved == [("octocat", "gho_new", "sign_in")]
    assert host.said == ["Added and switched to GitHub account octocat"]


def test_a_sign_in_that_returns_no_token_saves_nothing(host, monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.ui.github_device_sign_in.sign_in_with_github", lambda *_a, **_k: None
    )
    monkeypatch.setattr(f"{_FLOW}.save_github_account", lambda *_a: pytest.fail("nothing to save"))

    GitHubAccountsFlow(host.host).sign_in()

    assert host.quiet == [] and host.said == []


def test_quill_waits_for_github_on_its_task_manager() -> None:
    from quill.ui.main_frame_github_accounts import GitHubAccountsMixin

    manager = SimpleNamespace(submit=lambda *_a, **_k: None)
    frame = GitHubAccountsMixin()
    frame.frame = "frame"
    frame._set_status = frame._set_status_quiet = lambda _m: None
    frame._show_message_box = lambda *_a: None
    frame._wx = SimpleNamespace(CallAfter=lambda fn, *a, **k: fn(*a, **k))
    frame._task_manager = manager

    host = frame._github_accounts_flow().host

    assert host.app_name == "QUILL"
    assert host.submit == manager.submit


def _gh_flow(host, monkeypatch, *, answer: object, identity: str = "octocat"):
    import wx

    saved: list[tuple] = []
    monkeypatch.setattr(
        f"{_FLOW}.save_github_account",
        lambda login, token, added_by="", host="github.com": (
            saved.append((login, token, added_by, host))
            or SimpleNamespace(id="a" * 32, login=login, host=host)
        ),
    )
    monkeypatch.setattr(f"{_FLOW}.delete_legacy_github_token", lambda: False)
    monkeypatch.setattr(f"{_FLOW}.remember_server", lambda *_a: None)
    monkeypatch.setattr(
        "quill.core.github.gh_sign_in.read_gh_token", lambda server: "gho_" + "c" * 36
    )

    class _Provider:
        last_auth_error = ""

        def __init__(self, *, token=None) -> None:
            pass

        def get_identity(self):
            return SimpleNamespace(login=identity)

        def close(self) -> None:
            pass

    monkeypatch.setattr(f"{_FLOW}.GitHubRemoteProvider", _Provider)
    asked: list[str] = []
    host.host.message_box = lambda message, _c, _s: asked.append(message) or answer
    flow = GitHubAccountsFlow(host.host)
    monkeypatch.setattr(flow, "ask_gh_host", lambda: "ghe.example.com")
    return flow, saved, asked, wx


def test_the_gh_sign_in_is_saved_only_after_the_person_says_yes(host, monkeypatch) -> None:
    import wx

    from quill.core.github import hosts

    hosts.forget_bindings()
    flow, saved, asked, _wx = _gh_flow(host, monkeypatch, answer=wx.YES)
    flow.reuse_gh_sign_in()
    assert "signed in to ghe.example.com as octocat" in asked[0]
    assert saved == [("octocat", "gho_" + "c" * 36, "gh_cli", "ghe.example.com")]
    assert hosts.host_for_token("gho_" + "c" * 36) == "ghe.example.com"  # checked there
    assert host.said == ["Added and switched to GitHub account octocat on ghe.example.com"]
    hosts.forget_bindings()


def test_no_to_the_gh_sign_in_saves_nothing(host, monkeypatch) -> None:
    import wx

    flow, saved, _asked, _wx = _gh_flow(host, monkeypatch, answer=wx.NO)
    flow.reuse_gh_sign_in()
    assert saved == [] and host.said == ["Nothing was added."]


def test_gh_not_signed_in_is_said_and_nothing_is_saved(host, monkeypatch) -> None:
    from quill.core.github.gh_sign_in import GhSignInError

    flow, saved, asked, _wx = _gh_flow(host, monkeypatch, answer=None)

    def refuse(server):
        raise GhSignInError(f"The GitHub CLI is not signed in to {server}.")

    monkeypatch.setattr("quill.core.github.gh_sign_in.read_gh_token", refuse)
    flow.reuse_gh_sign_in()
    assert saved == [] and asked == ["The GitHub CLI is not signed in to ghe.example.com."]
