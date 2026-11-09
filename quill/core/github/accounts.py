"""Account-scoped GitHub credentials and metadata.

Tokens stay in QUILL's OS-backed Secrets Manager. This file stores only the
GitHub.com login, host, and the id of the active account. QUILL Lite gets its
own registry because ``app_data_dir`` is product-scoped.

Since 2026-11-08 it also remembers two non-secret things about each account:
**how it was added** (``added_by``: Sign In with GitHub, a pasted token, or
``unknown`` for every account saved before anybody asked), and a little
**state** (:class:`GitHubAccountState`): whether Manage GitHub Accounts has
already suggested signing in instead of using a token, when GitHub said the
token expires, and the day the expiry was last mentioned. Each of those is said
at most once -- per account, or per day -- so the record of having said it has
to outlive the window that said it. It lives here, beside the account it is
about, so removing an account removes it too.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir
from quill.core.secrets import SecretRef, default_secrets_manager
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github-accounts.json"
_SCHEMA_VERSION = 1
_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_ACCOUNT_ID_RE = re.compile(r"^[0-9a-f]{32}$")

#: How an account was added. ``unknown`` is every account saved before 2026-11-08.
ADDED_BY_SIGN_IN = "sign_in"
ADDED_BY_TOKEN = "token"
ADDED_BY_UNKNOWN = "unknown"
_ADDED_BY = frozenset({ADDED_BY_SIGN_IN, ADDED_BY_TOKEN, ADDED_BY_UNKNOWN})


class GitHubAccountError(CodedError, ValueError):
    """An account record is invalid or uses an unsupported GitHub host."""

    code = "QUILL-GITHUB-ACCOUNTS-INVALID"


@dataclass(frozen=True, slots=True)
class GitHubAccount:
    """Non-secret metadata for one GitHub.com account."""

    id: str
    login: str
    host: str = "github.com"
    #: :data:`ADDED_BY_SIGN_IN`, :data:`ADDED_BY_TOKEN` or :data:`ADDED_BY_UNKNOWN`.
    added_by: str = ADDED_BY_UNKNOWN

    @property
    def display_name(self) -> str:
        return f"{self.login} ({self.host})"


@dataclass(frozen=True, slots=True)
class GitHubAccountState:
    """What QUILL has already told somebody about one account, and when.

    ``expires_at`` is GitHub's own ``GitHub-Authentication-Token-Expiration``
    value, as sent; ``expiry_warned_on`` is an ISO date (``2026-11-08``).
    """

    nudge_shown: bool = False
    expires_at: str = ""
    expiry_warned_on: str = ""


def accounts_path() -> Path:
    """Path to the account registry for the active QUILL product."""
    return app_data_dir() / _FILENAME


def _account_id(host: str, login: str) -> str:
    value = f"{host.casefold()}\0{login.casefold()}".encode()
    return hashlib.sha256(value).hexdigest()[:32]


def _account_secret(account_id: str) -> SecretRef:
    if not _ACCOUNT_ID_RE.fullmatch(account_id):
        raise GitHubAccountError("The saved GitHub account id is invalid.")
    return SecretRef("github", f"account-{account_id}")


def _validated_host(host: str) -> str:
    value = host.strip().casefold().rstrip(".")
    if value != "github.com":
        raise GitHubAccountError(
            "GitHub Enterprise hosts are not supported yet. Connect a GitHub.com account."
        )
    return value


def _read_registry() -> dict[str, object]:
    raw = read_json(accounts_path(), default={})
    return raw if isinstance(raw, dict) else {}


def has_account_registry() -> bool:
    """Whether the account registry is authoritative, even when empty."""
    raw = _read_registry()
    return raw.get("schema_version") == _SCHEMA_VERSION and isinstance(raw.get("accounts"), list)


def list_github_accounts() -> list[GitHubAccount]:
    raw = _read_registry()
    entries = raw.get("accounts", [])
    if not isinstance(entries, list):
        return []
    result: list[GitHubAccount] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        login = entry.get("login")
        host = entry.get("host", "github.com")
        account_id = entry.get("id")
        if (
            not isinstance(login, str)
            or not _LOGIN_RE.fullmatch(login)
            or not isinstance(host, str)
            or not isinstance(account_id, str)
            or not _ACCOUNT_ID_RE.fullmatch(account_id)
        ):
            continue
        try:
            normalized_host = _validated_host(host)
        except GitHubAccountError:
            continue
        expected_id = _account_id(normalized_host, login)
        if account_id != expected_id or account_id in seen:
            continue
        seen.add(account_id)
        added_by = entry.get("added_by", ADDED_BY_UNKNOWN)
        if added_by not in _ADDED_BY:
            added_by = ADDED_BY_UNKNOWN
        result.append(GitHubAccount(account_id, login, normalized_host, str(added_by)))
    return result


def active_github_account_id() -> str | None:
    raw = _read_registry()
    accounts = list_github_accounts()
    ids = {account.id for account in accounts}
    value = raw.get("active_id")
    if isinstance(value, str) and value in ids:
        return value
    return accounts[0].id if accounts else None


def active_github_account() -> GitHubAccount | None:
    active_id = active_github_account_id()
    return next((account for account in list_github_accounts() if account.id == active_id), None)


def _raw_states() -> dict[str, dict[str, object]]:
    raw = _read_registry().get("account_state", {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, dict) and _ACCOUNT_ID_RE.fullmatch(str(key))
    }


def _persist(
    accounts: list[GitHubAccount],
    active_id: str | None,
    states: dict[str, dict[str, object]] | None = None,
) -> None:
    ids = {account.id for account in accounts}
    kept = _raw_states() if states is None else states
    write_json_atomic(
        accounts_path(),
        {
            "schema_version": _SCHEMA_VERSION,
            "accounts": [
                {
                    "id": account.id,
                    "login": account.login,
                    "host": account.host,
                    "added_by": account.added_by,
                }
                for account in accounts
            ],
            "active_id": active_id,
            # Only for accounts that still exist: removing one forgets it.
            "account_state": {key: value for key, value in kept.items() if key in ids},
        },
    )


def account_state(account_id: str) -> GitHubAccountState:
    """What has already been said about *account_id*; all empty when nothing has."""
    raw = _raw_states().get(account_id, {})
    return GitHubAccountState(
        nudge_shown=raw.get("nudge_shown") is True,
        expires_at=str(raw.get("expires_at", "") or ""),
        expiry_warned_on=str(raw.get("expiry_warned_on", "") or ""),
    )


def update_account_state(
    account_id: str,
    *,
    nudge_shown: bool | None = None,
    expires_at: str | None = None,
    expiry_warned_on: str | None = None,
) -> bool:
    """Change part of an account's state. False when there is no such account."""
    accounts = list_github_accounts()
    if not any(account.id == account_id for account in accounts):
        return False
    current = account_state(account_id)
    changes: dict[str, object] = {}
    if nudge_shown is not None:
        changes["nudge_shown"] = nudge_shown
    if expires_at is not None:
        changes["expires_at"] = expires_at
    if expiry_warned_on is not None:
        changes["expiry_warned_on"] = expiry_warned_on
    updated = replace(current, **changes)  # type: ignore[arg-type]
    if updated == current:
        return True
    states = _raw_states()
    states[account_id] = {
        "nudge_shown": updated.nudge_shown,
        "expires_at": updated.expires_at,
        "expiry_warned_on": updated.expiry_warned_on,
    }
    _persist(accounts, active_github_account_id(), states)
    return True


def save_github_account(
    login: str,
    token: str,
    *,
    host: str = "github.com",
    added_by: str = ADDED_BY_UNKNOWN,
) -> GitHubAccount:
    """Save a verified account token and make it active.

    Callers must verify ``login`` with GitHub before passing it here. A
    replacement for the same host/login retains its stable account id. A new
    token is a new expiry, so the expiry state is cleared; whether the sign-in
    suggestion was shown is kept, because it is said once per account.
    """
    normalized_host = _validated_host(host)
    normalized_login = login.strip()
    if not _LOGIN_RE.fullmatch(normalized_login):
        raise GitHubAccountError("GitHub returned an invalid account name.")
    token_value = token.strip()
    if not token_value:
        raise GitHubAccountError("Enter a GitHub token.")
    if added_by not in _ADDED_BY:
        raise GitHubAccountError("Unknown way of adding a GitHub account.")
    account = GitHubAccount(
        _account_id(normalized_host, normalized_login),
        normalized_login,
        normalized_host,
        added_by,
    )
    accounts = list_github_accounts()
    previous = next((item for item in accounts if item.id == account.id), None)
    if previous is None:
        accounts.append(account)
    else:
        accounts = [account if item.id == account.id else item for item in accounts]

    manager = default_secrets_manager()
    ref = _account_secret(account.id)
    old_token = manager.get(ref)
    manager.set(ref, token_value)
    states = _raw_states()
    if account.id in states:
        states[account.id] = {
            "nudge_shown": states[account.id].get("nudge_shown") is True,
            "expires_at": "",
            "expiry_warned_on": "",
        }
    try:
        _persist(accounts, account.id, states)
    except Exception:
        if old_token:
            manager.set(ref, old_token)
        else:
            manager.delete(ref)
        raise
    return account


def load_github_account_token(account_id: str) -> str | None:
    return default_secrets_manager().get(_account_secret(account_id))


def set_active_github_account(account_id: str) -> bool:
    accounts = list_github_accounts()
    if not any(account.id == account_id for account in accounts):
        return False
    _persist(accounts, account_id)
    return True


def remove_github_account(account_id: str) -> bool:
    accounts = list_github_accounts()
    if not any(account.id == account_id for account in accounts):
        return False
    remaining = [account for account in accounts if account.id != account_id]
    current = active_github_account_id()
    active_id = remaining[0].id if current == account_id and remaining else current
    if active_id == account_id:
        active_id = None
    _persist(remaining, active_id)
    default_secrets_manager().delete(_account_secret(account_id))
    return True


__all__ = [
    "ADDED_BY_SIGN_IN",
    "ADDED_BY_TOKEN",
    "ADDED_BY_UNKNOWN",
    "GitHubAccount",
    "GitHubAccountError",
    "GitHubAccountState",
    "account_state",
    "accounts_path",
    "active_github_account",
    "active_github_account_id",
    "has_account_registry",
    "list_github_accounts",
    "load_github_account_token",
    "remove_github_account",
    "save_github_account",
    "set_active_github_account",
    "update_account_state",
]
