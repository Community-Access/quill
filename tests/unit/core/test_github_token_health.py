"""What a GitHub token says about itself, and what the account registry remembers.

The sign-in suggestion and the expiry warning are each said at most once (per
account, or per day), so both the decision and the record of having said it
are tested here, against the real registry in a temporary folder.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.github import accounts
from quill.core.github import token_health as health
from quill.core.secrets import SecretsManager


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
def registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    manager = SecretsManager(backend=_Backend())
    monkeypatch.setattr(accounts, "default_secrets_manager", lambda: manager)
    path = tmp_path / "github-accounts.json"
    monkeypatch.setattr(accounts, "accounts_path", lambda: path)
    return path


# -- classic or not, broad or not ------------------------------------------ #


@pytest.mark.parametrize(
    ("token", "scopes", "added_by", "expected"),
    [
        ("ghp_abc", "repo, workflow", "token", True),
        ("ghp_abc", "repo", "unknown", True),  # ghp_ is classic whoever saved it
        ("ghp_abc", "read:org", "token", False),  # classic, but narrow
        ("ghp_abc", "", "token", False),  # classic with no scopes at all
        ("github_pat_abc", None, "token", False),  # fine-grained: chosen on purpose
        ("gho_abc", "repo", "sign_in", False),  # signed in
        ("gho_abc", "repo", "unknown", False),  # OAuth, though saved before anyone asked
        ("opaque", "repo, admin:org", "token", True),  # pasted, and GitHub reports scopes
        ("opaque", "repo", "unknown", False),  # header alone proves nothing for unknown
    ],
)
def test_the_suggestion_is_for_broad_classic_tokens_only(token, scopes, added_by, expected) -> None:
    assert (
        health.should_suggest_sign_in(
            token=token, scopes_header=scopes, added_by=added_by, already_shown=False
        )
        is expected
    )


def test_the_suggestion_is_never_made_twice() -> None:
    assert not health.should_suggest_sign_in(
        token="ghp_abc", scopes_header="repo", added_by="token", already_shown=True
    )


def test_an_admin_scope_is_broad_even_when_not_listed() -> None:
    assert health.has_broad_scopes(("admin:something_new",))
    assert not health.has_broad_scopes(("read:user", "gist"))
    assert not health.has_broad_scopes(None)


def test_header_value_tells_absent_from_empty() -> None:
    assert health.header_value({"x-oauth-scopes": ""}, health.SCOPES_HEADER) == ""
    assert health.header_value({}, health.SCOPES_HEADER) is None
    assert health.header_value(None, health.SCOPES_HEADER) is None


# -- expiry ---------------------------------------------------------------- #

_NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "value",
    ["2026-11-11 12:00:00 UTC", "2026-11-11 05:00:00 -0700", "2026-11-11T12:00:00+00:00"],
)
def test_githubs_expiry_header_is_read_in_each_form(value: str) -> None:
    assert health.parse_expiration(value) == datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def test_an_unreadable_or_missing_expiry_is_none() -> None:
    assert health.parse_expiration("") is None
    assert health.parse_expiration(None) is None
    assert health.parse_expiration("next Tuesday") is None


def test_seven_days_is_soon_and_eight_is_not() -> None:
    assert health.expiry_state(_NOW + timedelta(days=7), _NOW) == "soon"
    assert health.expiry_state(_NOW + timedelta(days=8), _NOW) == "ok"
    assert health.expiry_state(_NOW - timedelta(minutes=1), _NOW) == "expired"
    assert health.expiry_state(None, _NOW) == "ok"


def test_the_sentence_says_how_long_in_plain_words() -> None:
    say = health.expiry_sentence
    assert say("octocat", _NOW + timedelta(days=3, hours=2), _NOW) == (
        "Your GitHub token for octocat expires in 3 days."
    )
    assert say("octocat", _NOW + timedelta(days=1, hours=1), _NOW).endswith("expires tomorrow.")
    assert say("octocat", _NOW + timedelta(hours=5), _NOW).endswith("in less than a day.")
    assert say("octocat", _NOW - timedelta(days=1), _NOW) == (
        "Your GitHub token for octocat has expired."
    )


def test_a_waiter_hears_the_first_reply_once() -> None:
    tracker = health.TokenExpiryTracker()
    heard: list[str] = []
    tracker.when_seen("tok", heard.append)
    assert heard == []  # no reply yet

    tracker.observe("tok", {"github-authentication-token-expiration": "2026-11-11 12:00:00 UTC"})
    tracker.observe("tok", {"github-authentication-token-expiration": "2026-11-11 12:00:00 UTC"})
    assert heard == ["2026-11-11 12:00:00 UTC"]

    tracker.when_seen("tok", heard.append)  # already known: at once
    assert heard[-1] == "2026-11-11 12:00:00 UTC" and len(heard) == 2


def test_a_reply_without_the_header_says_no_expiry_and_other_tokens_wait() -> None:
    tracker = health.TokenExpiryTracker()
    heard: list[str] = []
    tracker.when_seen("mine", heard.append)
    tracker.observe("someone-else", {"github-authentication-token-expiration": "x"})
    assert heard == []
    tracker.observe("mine", {})
    assert heard == [""]


def test_the_tracker_keeps_no_token() -> None:
    tracker = health.TokenExpiryTracker()
    tracker.observe("ghp_secret_value", {})
    assert "ghp_secret_value" not in repr(tracker.__dict__)


def test_the_rest_transport_reports_every_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github import rest_transport
    from quill.core.github.rate_limits import RateLimitTracker

    class _Reply:
        status = 200
        headers = {"GitHub-Authentication-Token-Expiration": "2026-11-11 12:00:00 UTC"}

        def read(self, _limit: int) -> bytes:
            return b"{}"

        def __enter__(self) -> _Reply:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    class _Opener:
        def open(self, _request: object, timeout: int) -> _Reply:
            return _Reply()

    tracker = health.TokenExpiryTracker()
    monkeypatch.setattr(rest_transport, "TOKEN_EXPIRY", tracker)
    rest_transport.request_json("tok", "GET", "/user", opener=_Opener(), tracker=RateLimitTracker())
    assert tracker.seen("tok") == "2026-11-11 12:00:00 UTC"


# -- the registry ---------------------------------------------------------- #


def test_how_an_account_was_added_is_saved_and_older_ones_are_unknown(registry: Path) -> None:
    signed = accounts.save_github_account("Alice", "gho_a", added_by=accounts.ADDED_BY_SIGN_IN)
    pasted = accounts.save_github_account("Bob", "ghp_b", added_by=accounts.ADDED_BY_TOKEN)
    by_id = {account.id: account for account in accounts.list_github_accounts()}
    assert by_id[signed.id].added_by == "sign_in"
    assert by_id[pasted.id].added_by == "token"

    # An account saved before 2026-11-08 has no added_by at all.
    raw = json.loads(registry.read_text(encoding="utf-8"))
    for entry in raw["accounts"]:
        entry.pop("added_by")
    registry.write_text(json.dumps(raw), encoding="utf-8")
    assert {account.added_by for account in accounts.list_github_accounts()} == {"unknown"}


def test_state_is_kept_across_switching_and_goes_with_the_account(registry: Path) -> None:
    alice = accounts.save_github_account("Alice", "ghp_a", added_by="token")
    bob = accounts.save_github_account("Bob", "ghp_b", added_by="token")
    assert accounts.account_state(alice.id) == accounts.GitHubAccountState()

    assert accounts.update_account_state(alice.id, nudge_shown=True, expiry_warned_on="2026-11-08")
    accounts.set_active_github_account(alice.id)
    assert accounts.account_state(alice.id).nudge_shown is True
    assert accounts.account_state(bob.id).nudge_shown is False

    accounts.remove_github_account(alice.id)
    raw = json.loads(registry.read_text(encoding="utf-8"))
    assert alice.id not in raw["account_state"]
    assert not accounts.update_account_state(alice.id, nudge_shown=True)


def test_a_new_token_clears_the_expiry_but_not_the_suggestion(registry: Path) -> None:
    alice = accounts.save_github_account("Alice", "ghp_a", added_by="token")
    accounts.update_account_state(
        alice.id,
        nudge_shown=True,
        expires_at="2026-11-11 12:00:00 UTC",
        expiry_warned_on="2026-11-08",
    )

    accounts.save_github_account("Alice", "ghp_new", added_by="token")

    assert accounts.account_state(alice.id) == accounts.GitHubAccountState(nudge_shown=True)


def test_the_registry_never_holds_a_token(registry: Path) -> None:
    alice = accounts.save_github_account("Alice", "ghp_secret", added_by="token")
    accounts.update_account_state(alice.id, expires_at="2026-11-11 12:00:00 UTC")
    assert "ghp_secret" not in registry.read_text(encoding="utf-8")
