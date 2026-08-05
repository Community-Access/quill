"""The migrated GitHub token store round-trips through the Secrets Manager.

Confirms the Phase 4 migration keeps the credential name (``quill-github-token``)
and the public signatures, using an in-memory secrets backend so no OS vault is
touched.
"""

from __future__ import annotations

import pytest

import quill.core.github.token_store as token_store
from quill.core.secrets import SecretsManager


class FakeBackend:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def load(self, cred_name: str) -> str:
        return self.store.get(cred_name, "")

    def save(self, cred_name: str, value: str) -> None:
        if value:
            self.store[cred_name] = value
        else:
            self.store.pop(cred_name, None)

    def delete(self, cred_name: str) -> bool:
        return self.store.pop(cred_name, None) is not None


@pytest.fixture
def fake_manager(monkeypatch: pytest.MonkeyPatch) -> SecretsManager:
    manager = SecretsManager(backend=FakeBackend())
    monkeypatch.setattr(token_store, "default_secrets_manager", lambda: manager)
    return manager


def test_credential_name_preserved() -> None:
    assert token_store._REF.cred_name == "quill-github-token"


def test_roundtrip(fake_manager: SecretsManager) -> None:
    assert token_store.load_github_token() is None
    assert token_store.save_github_token("ghp_abc123") is True
    assert token_store.load_github_token() == "ghp_abc123"


def test_save_trims_whitespace(fake_manager: SecretsManager) -> None:
    token_store.save_github_token("  ghp_xyz  ")
    assert token_store.load_github_token() == "ghp_xyz"


def test_delete(fake_manager: SecretsManager) -> None:
    token_store.save_github_token("ghp_abc")
    assert token_store.delete_github_token() is True
    assert token_store.delete_github_token() is False
    assert token_store.load_github_token() is None
