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


def test_an_enterprise_server_account_is_its_own_account_bound_to_its_host(
    store: FakeBackend,
) -> None:
    from quill.core.github import hosts

    hosts.forget_bindings()
    dotcom = accounts.save_github_account("Alice", "dotcom-token")
    ghes = accounts.save_github_account(
        "Alice", "enterprise-token", host="https://GitHub.Example.com/api/v3"
    )

    assert ghes.host == "github.example.com"
    assert ghes.id != dotcom.id  # the same login on two hosts is two accounts
    assert ghes.level_key == "Alice@github.example.com"
    assert dotcom.level_key == "Alice"
    assert accounts.load_github_account_token(ghes.id) == "enterprise-token"
    assert hosts.host_for_token("enterprise-token") == "github.example.com"
    assert accounts.load_github_account_token(dotcom.id) == "dotcom-token"
    assert hosts.host_for_token("dotcom-token") == "github.com"
    hosts.forget_bindings()


def test_a_host_that_is_not_a_server_name_is_refused_before_a_token_is_stored(
    store: FakeBackend,
) -> None:
    for bad in ("http://ghe.example.com", "ghe.example.com/some/path", "user@ghe.example.com"):
        with pytest.raises(accounts.GitHubAccountError):
            accounts.save_github_account("Alice", "enterprise-token", host=bad)

    assert not store.values


def test_an_enterprise_servers_version_is_kept_with_its_account(store: FakeBackend) -> None:
    from quill.core.github import api_coverage, hosts

    hosts.forget_bindings()
    ghes = accounts.save_github_account("Alice", "enterprise-token", host="ghe.example.com")
    assert accounts.update_account_state(ghes.id, server_version="3.12.4")
    assert api_coverage.server_version_for_host("ghe.example.com") is None  # not loaded yet
    accounts.load_github_account_token(ghes.id)
    assert api_coverage.server_version_for_host("ghe.example.com") == "3.12.4"
    assert api_coverage.server_version_for_host("github.com") is None
    hosts.forget_bindings()


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
