"""File > Manage GitHub Accounts in QUILL Lite, and the Workbench's sign-in offer.

The flow is QUILL's (``quill/ui/github_accounts_flow.py``); these tests reach it
through QUILL Lite's own handlers, with the dialogs answered by ``lite_dialogs``
and the network replaced at the flow's module.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

_FLOW = "quill.ui.github_accounts_flow"


class _InlineThread:
    """``threading.Thread`` that runs its target at ``start()``, on this thread."""

    def __init__(self, *, target, daemon=False, **_kwargs) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


@pytest.fixture
def no_account(monkeypatch):
    monkeypatch.setattr(f"{_FLOW}.load_github_token", lambda: "")
    monkeypatch.setattr(f"{_FLOW}.list_github_accounts", lambda: [])
    monkeypatch.setattr(f"{_FLOW}.active_github_account_id", lambda: None)
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: "")


@pytest.fixture
def github_says(monkeypatch, wx_call_after):
    """``github_says("octocat")``: the identity GitHub reports for any token."""
    monkeypatch.setattr(
        "quill.apps.lite_github_accounts.threading", SimpleNamespace(Thread=_InlineThread)
    )
    wx_call_after()
    saved: list[tuple[str, str]] = []

    def save(login: str, token: str, **_kwargs: object) -> SimpleNamespace:
        saved.append((login, token))
        return SimpleNamespace(login=login, id=login)

    monkeypatch.setattr(f"{_FLOW}.save_github_account", save)
    monkeypatch.setattr(f"{_FLOW}.delete_legacy_github_token", lambda: False)

    def install(login: str | None, error: str = "") -> list[tuple[str, str]]:
        class _Provider:
            last_auth_error = error

            def __init__(self, *, token=None) -> None:
                self.token = token

            def get_identity(self):
                return SimpleNamespace(login=login) if login else None

            def close(self) -> None:
                pass

        monkeypatch.setattr(f"{_FLOW}.GitHubRemoteProvider", _Provider)
        return saved

    return install


def test_manage_accounts_opens_quills_window_with_no_account(
    lite_window, lite_dialogs, no_account
) -> None:
    win = lite_window("")

    win.cmd_github_manage_accounts()

    assert lite_dialogs.names() == ["GitHubManageAccountsDialog"]
    assert lite_dialogs.args_for("GitHubManageAccountsDialog") == (win,)
    assert lite_dialogs.kwargs_for("GitHubManageAccountsDialog")["has_token"] is False
    # Done (or Escape) changes nothing and says nothing.
    assert win.announcements == []


def test_add_account_verifies_with_github_then_saves(
    lite_window, lite_dialogs, no_account, github_says
) -> None:
    saved = github_says("octocat")
    lite_dialogs.answer("GitHubManageAccountsDialog", "add")
    lite_dialogs.answer("GitHubSignInDialog", SimpleNamespace(token="ghp_test"))
    win = lite_window("")

    win.cmd_github_manage_accounts()

    assert lite_dialogs.names() == ["GitHubManageAccountsDialog", "GitHubSignInDialog"]
    assert saved == [("octocat", "ghp_test")]
    assert win.announcements[-1] == "Added and switched to GitHub account octocat"


def test_sign_in_with_github_is_quill_lites_default_road_too(
    lite_window, lite_dialogs, no_account, github_says
) -> None:
    saved = github_says("octocat")
    lite_dialogs.answer("GitHubManageAccountsDialog", "sign_in")
    lite_dialogs.answer("sign_in_with_github", "gho_test")
    win = lite_window("")

    win.cmd_github_manage_accounts()

    assert lite_dialogs.names() == ["GitHubManageAccountsDialog", "sign_in_with_github"]
    args = lite_dialogs.args_for("sign_in_with_github")
    assert args[:2] == (win, "QUILL Lite")  # GitHub's page names QUILL Lite, not QUILL
    assert saved == [("octocat", "gho_test")]
    assert win.announcements[-1] == "Added and switched to GitHub account octocat"


def test_a_cancelled_sign_in_with_github_saves_nothing(
    lite_window, lite_dialogs, no_account, github_says
) -> None:
    saved = github_says("octocat")
    lite_dialogs.answer("GitHubManageAccountsDialog", "sign_in")
    win = lite_window("")

    win.cmd_github_manage_accounts()  # the step answers None: cancelled

    assert saved == []
    assert win.announcements == []


def test_a_token_github_does_not_confirm_is_never_saved(
    lite_window, lite_dialogs, no_account, github_says, monkeypatch
) -> None:
    saved = github_says(None, error="GitHub rejected that token.")
    boxes: list[str] = []
    monkeypatch.setattr(
        "quill.apps.lite_github_accounts.show_message_box",
        lambda message, *_args, **_kwargs: boxes.append(message),
    )
    lite_dialogs.answer("GitHubManageAccountsDialog", "add")
    lite_dialogs.answer("GitHubSignInDialog", SimpleNamespace(token="ghp_bad"))
    win = lite_window("")

    win.cmd_github_manage_accounts()

    assert saved == []
    assert boxes == ["GitHub rejected that token."]


@pytest.fixture
def workbench(monkeypatch):
    """The Workbench's gates passed and its viewer recorded."""
    # These pin the classic windows (Workbench Options, Use the classic GitHub
    # windows); the Workbench, the default since Phase 6, is tested elsewhere.
    monkeypatch.setenv("QUILL_GITHUB_WORKBENCH_WINDOW", "0")
    opened: list[object] = []

    class _Provider:
        def __init__(self, *, token=None) -> None:
            opened.append(("provider", token))

        def close(self) -> None:
            pass

    class _Viewer:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def show(self) -> None:
            opened.append("viewer")

    monkeypatch.setattr("quill.core.github.github_provider.require_pygithub", lambda: None)
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _path: "")
    monkeypatch.setattr("quill.core.github.items_provider.GitHubItemsProvider", _Provider)
    monkeypatch.setattr("quill.ui.github_items_dialog.GitHubItemsDialog", _Viewer)
    return opened


def _question(fake_wx_dialog, answer):
    return fake_wx_dialog("MessageDialog", answer, SetYesNoCancelLabels=lambda *_a: True)


def test_workbench_with_no_account_can_still_open_as_a_guest(
    lite_window, lite_dialogs, fake_wx_dialog, no_account, workbench
) -> None:
    asked = _question(fake_wx_dialog, wx.ID_NO)
    win = lite_window("")

    win.cmd_github_workbench()

    assert len(asked.constructed) == 1
    assert "not signed in" in asked.constructed[0][0][1]
    assert workbench == [("provider", None), "viewer"]
    assert lite_dialogs.names() == []


def test_workbench_with_no_account_offers_manage_accounts_first(
    lite_window, lite_dialogs, fake_wx_dialog, no_account, workbench
) -> None:
    _question(fake_wx_dialog, wx.ID_YES)
    win = lite_window("")

    win.cmd_github_workbench()

    assert lite_dialogs.names() == ["GitHubManageAccountsDialog"]
    assert workbench == []  # cancelled in Manage: the Workbench stays closed


def test_signing_in_from_the_workbench_offer_opens_it_signed_in(
    lite_window, lite_dialogs, fake_wx_dialog, no_account, workbench, github_says, monkeypatch
) -> None:
    github_says("octocat")
    _question(fake_wx_dialog, wx.ID_YES)
    lite_dialogs.answer("GitHubManageAccountsDialog", "add")
    lite_dialogs.answer("GitHubSignInDialog", SimpleNamespace(token="ghp_test"))
    win = lite_window("")

    def signed_in_token() -> str:
        return "ghp_test" if lite_dialogs.names()[-1:] == ["GitHubSignInDialog"] else ""

    # Once the account is saved, the reopened Workbench finds its token.
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", signed_in_token)

    win.cmd_github_workbench()

    assert workbench == [("provider", "ghp_test"), "viewer"]


def test_cancel_at_the_workbench_offer_opens_nothing(
    lite_window, lite_dialogs, fake_wx_dialog, no_account, workbench
) -> None:
    _question(fake_wx_dialog, wx.ID_CANCEL)
    win = lite_window("")

    win.cmd_github_workbench()

    assert workbench == []
    assert lite_dialogs.names() == []


def test_the_empty_window_reaches_manage_accounts(wx_session_app, lite_dialogs, no_account) -> None:
    from quill.apps.lite_shell_menu import ShellMenuMixin

    class _Shell(ShellMenuMixin):
        def __init__(self) -> None:
            self.said: list[str] = []
            self.app = SimpleNamespace(
                voice=SimpleNamespace(speak=lambda m, interrupt=True: self.said.append(m))
            )

    shell = _Shell()

    shell.run_shell_command("cmd_github_manage_accounts")

    assert lite_dialogs.names() == ["GitHubManageAccountsDialog"]
    assert lite_dialogs.args_for("GitHubManageAccountsDialog") == (shell,)
