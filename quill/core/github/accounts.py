"""Account-scoped GitHub credentials and metadata.

Tokens stay in QUILL's OS-backed Secrets Manager. This file stores only the
GitHub.com login, host, and the id of the active account. QUILL Lite gets its
own registry because ``app_data_dir`` is product-scoped.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir
from quill.core.secrets import SecretRef, default_secrets_manager
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github-accounts.json"
_SCHEMA_VERSION = 1
_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_ACCOUNT_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class GitHubAccountError(CodedError, ValueError):
    """An account record is invalid or uses an unsupported GitHub host."""

    code = "QUILL-GITHUB-ACCOUNTS-INVALID"


@dataclass(frozen=True, slots=True)
class GitHubAccount:
    """Non-secret metadata for one GitHub.com account."""

    id: str
    login: str
    host: str = "github.com"

    @property
    def display_name(self) -> str:
        return f"{self.login} ({self.host})"


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
        result.append(GitHubAccount(account_id, login, normalized_host))
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


def _persist(accounts: list[GitHubAccount], active_id: str | None) -> None:
    write_json_atomic(
        accounts_path(),
        {
            "schema_version": _SCHEMA_VERSION,
            "accounts": [
                {"id": account.id, "login": account.login, "host": account.host}
                for account in accounts
            ],
            "active_id": active_id,
        },
    )


def save_github_account(login: str, token: str, *, host: str = "github.com") -> GitHubAccount:
    """Save a verified account token and make it active.

    Callers must verify ``login`` with GitHub before passing it here. A
    replacement for the same host/login retains its stable account id.
    """
    normalized_host = _validated_host(host)
    normalized_login = login.strip()
    if not _LOGIN_RE.fullmatch(normalized_login):
        raise GitHubAccountError("GitHub returned an invalid account name.")
    token_value = token.strip()
    if not token_value:
        raise GitHubAccountError("Enter a GitHub token.")
    account = GitHubAccount(
        _account_id(normalized_host, normalized_login), normalized_login, normalized_host
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
    try:
        _persist(accounts, account.id)
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
    "GitHubAccount",
    "GitHubAccountError",
    "accounts_path",
    "active_github_account",
    "active_github_account_id",
    "has_account_registry",
    "list_github_accounts",
    "load_github_account_token",
    "remove_github_account",
    "save_github_account",
    "set_active_github_account",
]
