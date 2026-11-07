"""Multi-account GitHub credentials remain account-scoped and secret-safe."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.github import accounts
from quill.core.secrets import SecretsManager


class FakeBackend:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.values.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> bool:
        return self.values.pop(name, None) is not None


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeBackend:
    backend = FakeBackend()
    manager = SecretsManager(backend=backend)
    monkeypatch.setattr(accounts, "default_secrets_manager", lambda: manager)
    monkeypatch.setattr(accounts, "accounts_path", lambda: tmp_path / "github-accounts.json")
    return backend


def test_tokens_are_saved_separately_and_metadata_contains_no_secrets(store: FakeBackend) -> None:
    alice = accounts.save_github_account("Alice", "alice-token")
    bob = accounts.save_github_account("Bob", "bob-token")

    assert accounts.load_github_account_token(alice.id) == "alice-token"
    assert accounts.load_github_account_token(bob.id) == "bob-token"
    assert accounts.active_github_account_id() == bob.id
    raw = accounts.accounts_path().read_text(encoding="utf-8")
    assert "alice-token" not in raw
    assert "bob-token" not in raw
    assert "github.com" in raw


def test_switch_and_remove_only_change_the_selected_account(store: FakeBackend) -> None:
    alice = accounts.save_github_account("Alice", "alice-token")
    bob = accounts.save_github_account("Bob", "bob-token")

    assert accounts.set_active_github_account(alice.id)
    assert accounts.remove_github_account(alice.id)
    assert accounts.active_github_account_id() == bob.id
    assert accounts.load_github_account_token(alice.id) is None
    assert accounts.load_github_account_token(bob.id) == "bob-token"


def test_empty_registry_stays_authoritative_after_last_account_is_removed(
    store: FakeBackend,
) -> None:
    account = accounts.save_github_account("Alice", "alice-token")

    assert accounts.remove_github_account(account.id)
    assert accounts.has_account_registry()
    assert accounts.active_github_account_id() is None
    assert accounts.list_github_accounts() == []


def test_enterprise_hosts_are_rejected_before_a_token_is_stored(store: FakeBackend) -> None:
    with pytest.raises(accounts.GitHubAccountError, match="Enterprise"):
        accounts.save_github_account("Alice", "enterprise-token", host="github.example.com")

    assert not store.values


def test_invalid_registry_entries_are_ignored(store: FakeBackend) -> None:
    accounts.accounts_path().write_text(
        json.dumps({
            "schema_version": 1,
            "active_id": "bad",
            "accounts": [
                {"id": "bad", "login": "Alice", "host": "github.com"},
                {"id": "0" * 32, "login": "Alice", "host": "github.com"},
            ],
        }),
        encoding="utf-8",
    )

    assert accounts.list_github_accounts() == []
