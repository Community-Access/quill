"""Multi-account storage for Mastodon posting.

Non-secret account metadata (a friendly nickname, the instance, the resolved
``@handle``, and the OAuth client id) lives in ``mastodon-accounts.json`` under
the data dir. The two secrets -- the access token and the app client secret --
are stored via :mod:`quill.platform.windows.credential_store` (Windows
Credential Manager / DPAPI, env-var overridable), never in the JSON file.

No ``wx`` imports: pure model code.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.platform.windows.credential_store import (
    delete_secret,
    load_secret,
    save_secret,
)

_ACCOUNTS_FILENAME = "mastodon-accounts.json"
#: On-disk schema version (per the persistence contract). Bump + migrate in
#: list_accounts() if the stored shape ever changes incompatibly.
_ACCOUNTS_SCHEMA_VERSION = 1


def _token_cred(account_id: str) -> str:
    return f"mastodon-token-{account_id}"


def _secret_cred(account_id: str) -> str:
    return f"mastodon-clientsecret-{account_id}"


@dataclass(frozen=True, slots=True)
class MastodonAccount:
    """One signed-in account. Secrets are NOT stored on this object."""

    id: str
    nickname: str
    instance_url: str
    handle: str  # e.g. "@user@mastodon.social", for display
    client_id: str
    # When True, posting through this account first opens the F7 spelling review
    # on the post text so the user can fix misspellings before it is sent. Off by
    # default; accounts saved before this field existed load as False, so the
    # feature is purely opt-in and existing accounts are unaffected (#post-spellcheck).
    spell_check_before_post: bool = False

    @property
    def display_name(self) -> str:
        """The label shown in pickers: nickname plus the handle when known."""
        if self.handle and self.handle not in self.nickname:
            return f"{self.nickname} ({self.handle})"
        return self.nickname


def accounts_path() -> Path:
    return app_data_dir() / _ACCOUNTS_FILENAME


def _read_raw() -> dict[str, object]:
    raw = read_json(accounts_path(), default={})
    return raw if isinstance(raw, dict) else {}


def list_accounts() -> list[MastodonAccount]:
    raw = _read_raw()
    entries = raw.get("accounts", [])
    if not isinstance(entries, list):
        return []
    accounts: list[MastodonAccount] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            accounts.append(
                MastodonAccount(
                    id=str(entry["id"]),
                    nickname=str(entry.get("nickname", "")),
                    instance_url=str(entry.get("instance_url", "")),
                    handle=str(entry.get("handle", "")),
                    client_id=str(entry.get("client_id", "")),
                    # Missing on accounts saved before the field existed -> False
                    # (opt-in migration: existing accounts stay off).
                    spell_check_before_post=bool(entry.get("spell_check_before_post", False)),
                )
            )
        except KeyError:
            continue
    return accounts


def default_account_id() -> str | None:
    raw = _read_raw()
    value = raw.get("default_id")
    accounts = list_accounts()
    ids = {account.id for account in accounts}
    if isinstance(value, str) and value in ids:
        return value
    return accounts[0].id if accounts else None


def get_account(account_id: str) -> MastodonAccount | None:
    return next((a for a in list_accounts() if a.id == account_id), None)


def _persist(accounts: list[MastodonAccount], default_id: str | None) -> None:
    write_json_atomic(
        accounts_path(),
        {
            "schema_version": _ACCOUNTS_SCHEMA_VERSION,
            "accounts": [
                {
                    "id": a.id,
                    "nickname": a.nickname,
                    "instance_url": a.instance_url,
                    "handle": a.handle,
                    "client_id": a.client_id,
                    "spell_check_before_post": a.spell_check_before_post,
                }
                for a in accounts
            ],
            "default_id": default_id,
        },
    )


def add_account(
    *,
    nickname: str,
    instance_url: str,
    handle: str,
    client_id: str,
    client_secret: str,
    access_token: str,
    spell_check_before_post: bool = False,
) -> MastodonAccount:
    """Store a new account's metadata + secrets; return it. Becomes default if first."""
    account = MastodonAccount(
        id=uuid.uuid4().hex[:12],
        nickname=nickname.strip() or handle or instance_url,
        instance_url=instance_url,
        handle=handle,
        client_id=client_id,
        spell_check_before_post=spell_check_before_post,
    )
    save_secret(_token_cred(account.id), access_token)
    save_secret(_secret_cred(account.id), client_secret)
    existing = list_accounts()
    existing.append(account)
    new_default = default_account_id() or account.id
    _persist(existing, new_default)
    return account


def remove_account(account_id: str) -> None:
    """Delete an account's metadata and its stored secrets."""
    remaining = [a for a in list_accounts() if a.id != account_id]
    delete_secret(_token_cred(account_id))
    delete_secret(_secret_cred(account_id))
    current_default = default_account_id()
    new_default = current_default if current_default != account_id else None
    if new_default is None and remaining:
        new_default = remaining[0].id
    _persist(remaining, new_default)


def set_default_account(account_id: str) -> None:
    accounts = list_accounts()
    if any(a.id == account_id for a in accounts):
        _persist(accounts, account_id)


def set_spell_check_before_post(account_id: str, enabled: bool) -> None:
    """Turn the pre-post spelling review on/off for one account (off by default)."""
    from dataclasses import replace

    accounts = list_accounts()
    if not any(a.id == account_id for a in accounts):
        return
    updated = [
        replace(a, spell_check_before_post=bool(enabled)) if a.id == account_id else a
        for a in accounts
    ]
    _persist(updated, default_account_id())


def access_token_for(account_id: str) -> str:
    """Return the stored access token for *account_id* (``""`` when missing)."""
    return load_secret(_token_cred(account_id))


__all__ = [
    "MastodonAccount",
    "access_token_for",
    "accounts_path",
    "add_account",
    "default_account_id",
    "get_account",
    "list_accounts",
    "remove_account",
    "set_default_account",
    "set_spell_check_before_post",
]
