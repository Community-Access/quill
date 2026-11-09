"""Manage GitHub Accounts suggests Sign In with GitHub once, for a broad classic token.

One sentence, then an offer that No really declines: the window opens as usual,
the token keeps working, and the suggestion is never made again for that
account. The shared flow is driven over a recorded host, with the real account
registry in a temporary folder and GitHub's reply stood in for.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.github import accounts
from quill.core.secrets import SecretsManager
from quill.ui.github_accounts_flow import (
    SUGGEST_SIGN_IN_QUESTION,
    GitHubAccountsFlow,
    GitHubAccountsHost,
)

wx = pytest.importorskip("wx")

_FLOW = "quill.ui.github_accounts_flow"


class _Backend:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.values.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> bool:
        return self.values.pop(name, None) is not None


class _Dialog:
    opened: list[dict] = []

    def __init__(self, parent, **kwargs) -> None:
        type(self).opened.append(kwargs)

    def show(self) -> str:
        return "done"


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, wx_session_app):
    """A registry, a token GitHub answers for, and a host that records."""
    manager = SecretsManager(backend=_Backend())
    monkeypatch.setattr(accounts, "default_secrets_manager", lambda: manager)
    monkeypatch.setattr(accounts, "accounts_path", lambda: tmp_path / "github-accounts.json")
    # Never the machine's own credential store.
    monkeypatch.setattr(f"{_FLOW}.delete_legacy_github_token", lambda: False)
    _Dialog.opened = []
    monkeypatch.setattr("quill.ui.github_dialogs.GitHubManageAccountsDialog", _Dialog)
    reply = SimpleNamespace(scopes="repo, workflow", expiry="")

    class _Provider:
        last_auth_error = ""

        def __init__(self, *, token=None) -> None:
            self.token = token
            self.last_scopes_header = reply.scopes
            self.last_expiration_header = reply.expiry

        def get_identity(self):
            return SimpleNamespace(login="octocat")

        def close(self) -> None:
            pass

    monkeypatch.setattr(f"{_FLOW}.GitHubRemoteProvider", _Provider)
    answers: list[int] = []
    boxes: list[str] = []
    signed_in: list[str] = []

    def message_box(message: str, _caption: str, _style: int) -> int:
        boxes.append(message)
        return answers.pop(0) if answers else wx.NO

    host = GitHubAccountsHost(
        parent="frame",
        set_status=lambda _m: None,
        set_status_quiet=lambda _m: None,
        message_box=message_box,
        run_in_background=lambda work: work(),
        call_after=lambda fn, *a, **k: fn(*a, **k),
    )
    flow = GitHubAccountsFlow(host)
    monkeypatch.setattr(flow, "sign_in", lambda: signed_in.append("sign_in"))
    return SimpleNamespace(
        flow=flow, reply=reply, answers=answers, boxes=boxes, signed_in=signed_in
    )


def _save(token: str, added_by: str) -> accounts.GitHubAccount:
    return accounts.save_github_account("octocat", token, added_by=added_by)


def test_a_broad_classic_token_hears_one_sentence_and_an_offer(world) -> None:
    _save("ghp_classic", accounts.ADDED_BY_TOKEN)

    world.flow.manage()

    assert world.boxes == [SUGGEST_SIGN_IN_QUESTION]
    assert world.boxes[0].startswith(
        "This account uses a token. Sign In with GitHub is easier to keep up to date."
    )
    # No: the window opens as it always did, and nothing else happens.
    assert len(_Dialog.opened) == 1
    assert world.signed_in == []


def test_it_is_never_said_twice_for_the_same_account(world) -> None:
    account = _save("ghp_classic", accounts.ADDED_BY_TOKEN)

    world.flow.manage()
    world.flow.manage()

    assert len(world.boxes) == 1
    assert len(_Dialog.opened) == 2
    assert accounts.account_state(account.id).nudge_shown is True


def test_yes_goes_straight_to_sign_in_with_github(world) -> None:
    _save("ghp_classic", accounts.ADDED_BY_TOKEN)
    world.answers.append(wx.YES)

    world.flow.manage()

    assert world.signed_in == ["sign_in"]
    assert _Dialog.opened == []  # sign-in instead of the list


def test_an_account_saved_before_now_with_a_ghp_token_is_still_offered(world) -> None:
    _save("ghp_classic", accounts.ADDED_BY_UNKNOWN)

    world.flow.manage()

    assert world.boxes == [SUGGEST_SIGN_IN_QUESTION]


@pytest.mark.parametrize(
    ("token", "added_by", "scopes"),
    [
        ("gho_signed", accounts.ADDED_BY_SIGN_IN, "repo"),
        ("github_pat_fine", accounts.ADDED_BY_TOKEN, None),
        ("ghp_narrow", accounts.ADDED_BY_TOKEN, "read:org"),
    ],
)
def test_no_suggestion_for_sign_in_fine_grained_or_narrow(world, token, added_by, scopes) -> None:
    _save(token, added_by)
    world.reply.scopes = scopes

    world.flow.manage()

    assert world.boxes == []
    assert len(_Dialog.opened) == 1


def test_the_check_files_the_expiry_github_reported(world) -> None:
    account = _save("gho_signed", accounts.ADDED_BY_SIGN_IN)
    world.reply.expiry = "2026-11-11 12:00:00 UTC"

    world.flow.manage()

    assert accounts.account_state(account.id).expires_at == "2026-11-11 12:00:00 UTC"


def test_a_pasted_token_is_saved_as_a_token(world, monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.ui.github_dialogs.GitHubSignInDialog",
        lambda _parent: SimpleNamespace(show=lambda: SimpleNamespace(token="ghp_pasted")),
    )

    world.flow.add_token()

    assert [account.added_by for account in accounts.list_github_accounts()] == ["token"]
