"""The token expiry warning: seven days, already expired, once a day, and the notice.

Driven through :func:`quill.ui.github_token_expiry.watch_token_expiry` the way
both editors' Workbench gates call it, with the real account registry and
notifications file in a temporary folder, a private tracker standing in for
GitHub's replies, and a clock the test sets. The last tests reach QUILL's end:
its gate's host and the notice's way back. QUILL Lite's end is in
``tests/unit/apps/test_lite_github_tokens_and_readout.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.github import accounts
from quill.core.github.token_health import TokenExpiryTracker
from quill.core.notifications import load_notifications
from quill.core.secrets import SecretsManager
from quill.ui.github_token_expiry import (
    GITHUB_ACCOUNTS_TARGET,
    NOTICE_BODY,
    ExpiryHost,
    watch_token_expiry,
)

_EXPIRY = "github-authentication-token-expiration"


class _Backend:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.values.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> bool:
        return self.values.pop(name, None) is not None


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    manager = SecretsManager(backend=_Backend())
    monkeypatch.setattr(accounts, "default_secrets_manager", lambda: manager)
    monkeypatch.setattr(accounts, "accounts_path", lambda: tmp_path / "github-accounts.json")
    account = accounts.save_github_account("octocat", "ghp_tok", added_by="token")
    said: list[str] = []
    clock = SimpleNamespace(now=datetime(2026, 11, 8, 12, 0, tzinfo=UTC), day="2026-11-08")
    notices = tmp_path / "notifications.json"
    refreshed: list[str] = []
    host = ExpiryHost(
        say=said.append,
        call_after=lambda fn, *a: fn(*a),
        app_name="QUILL",
        notice_path=notices,
        after_notice=lambda: refreshed.append("refresh"),
        now=lambda: clock.now,
        today=lambda: clock.day,
    )
    return SimpleNamespace(
        account=account,
        host=host,
        said=said,
        clock=clock,
        notices=notices,
        refreshed=refreshed,
        tracker=TokenExpiryTracker(),
    )


def _reply(world, expiry: str) -> None:
    """GitHub answers the Workbench's first request."""
    world.tracker.observe("ghp_tok", {_EXPIRY: expiry} if expiry else {})


def test_a_token_expiring_within_seven_days_is_said_and_noted(world) -> None:
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)
    assert world.said == []  # nothing until GitHub has answered

    _reply(world, "2026-11-11 12:00:00 UTC")

    assert world.said == ["Your GitHub token for octocat expires in 3 days."]
    [notice] = load_notifications(path=world.notices)
    assert notice.title == world.said[0]
    assert notice.body == NOTICE_BODY
    assert notice.target == GITHUB_ACCOUNTS_TARGET
    assert notice.app == "QUILL"
    assert world.refreshed == ["refresh"]
    assert accounts.account_state(world.account.id).expires_at == "2026-11-11 12:00:00 UTC"


def test_more_than_seven_days_away_says_nothing(world) -> None:
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)
    _reply(world, "2026-11-20 12:00:00 UTC")

    assert world.said == []
    assert load_notifications(path=world.notices) == []


def test_a_token_that_never_expires_says_nothing(world) -> None:
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)
    _reply(world, "")

    assert world.said == []


def test_it_is_said_at_most_once_a_day(world) -> None:
    _reply(world, "2026-11-11 12:00:00 UTC")
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)
    assert len(world.said) == 1

    world.clock.day = "2026-11-09"
    world.clock.now = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)

    assert world.said[-1] == "Your GitHub token for octocat expires in 2 days."
    assert len(world.said) == 2
    assert len(load_notifications(path=world.notices)) == 2


def test_an_expired_token_gets_one_plain_sentence_and_the_same_notice(world) -> None:
    # An earlier reply filed the expiry; a dead token's replies carry none.
    accounts.update_account_state(world.account.id, expires_at="2026-11-07 09:00:00 UTC")

    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)

    assert world.said == ["Your GitHub token for octocat has expired."]
    [notice] = load_notifications(path=world.notices)
    assert notice.target == GITHUB_ACCOUNTS_TARGET


def test_no_account_or_no_token_does_nothing(world) -> None:
    watch_token_expiry(world.host, "", tracker=world.tracker)
    accounts.remove_github_account(world.account.id)
    watch_token_expiry(world.host, "ghp_tok", tracker=world.tracker)
    _reply(world, "2026-11-09 12:00:00 UTC")

    assert world.said == []


# -- the editors' ends ------------------------------------------------------ #


def test_the_quill_notice_opens_manage_github_accounts() -> None:
    from quill.ui.main_frame_github_accounts import GitHubAccountsMixin
    from quill.ui.windows_dictation_transcribe import DictationTranscribeMixin

    class _Frame(GitHubAccountsMixin, DictationTranscribeMixin):
        opened: list[str] = []

        def manage_github_accounts(self) -> None:
            self.opened.append("manage")

    frame = _Frame()
    frame.open_notification_target(GITHUB_ACCOUNTS_TARGET)

    assert frame.opened == ["manage"]


def test_quills_watch_speaks_through_the_frame_and_refreshes_its_bar(
    monkeypatch, wx_session_app
) -> None:
    from quill.ui.main_frame_github_accounts import GitHubAccountsMixin

    hosts: list[ExpiryHost] = []
    monkeypatch.setattr(
        "quill.ui.github_token_expiry.watch_token_expiry",
        lambda host, token: hosts.append(host),
    )
    monkeypatch.setattr("quill.core.notifications.load_notifications", lambda: ["one"])
    frame = GitHubAccountsMixin()
    said: list[str] = []
    refreshed: list[str] = []
    frame._announce = said.append
    frame._wx = SimpleNamespace(CallAfter=lambda fn, *a: fn(*a))
    frame._refresh_statusbar = lambda: refreshed.append("bar")

    frame._watch_github_token_expiry("ghp_tok")
    hosts[0].say("Your GitHub token for octocat has expired.")
    hosts[0].after_notice()

    assert hosts[0].app_name == "QUILL"
    assert said == ["Your GitHub token for octocat has expired."]
    assert frame._notifications == ["one"] and refreshed == ["bar"]
