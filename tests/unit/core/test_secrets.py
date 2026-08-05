"""Unit tests for the QUILL Secrets Manager (``quill.core.secrets``).

Exercised through an in-memory fake backend so nothing touches the real OS
credential vault. The fake mirrors the ``credential_store`` contract: an empty
value on ``save`` is a delete, ``load`` returns ``""`` when absent, ``delete``
reports whether an entry existed.
"""

from __future__ import annotations

import json

import pytest

from quill.core.secrets import SecretRef, SecretsError, SecretsManager


class FakeBackend:
    """In-memory stand-in for the OS vault."""

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
def manager() -> SecretsManager:
    return SecretsManager(backend=FakeBackend())


# -- SecretRef ---------------------------------------------------------------


def test_cred_name_format() -> None:
    assert SecretRef("bard", "patron-tokens").cred_name == "quill-bard-patron-tokens"


@pytest.mark.parametrize(
    ("namespace", "name"),
    [
        ("", "x"),
        ("bard", ""),
        ("Bard", "x"),  # uppercase rejected
        ("bard", "-leading"),  # must start alphanumeric
        ("bard", "has space"),
        ("bard", "__index__"),  # reserved
    ],
)
def test_invalid_refs_rejected(namespace: str, name: str) -> None:
    with pytest.raises(SecretsError):
        SecretRef(namespace, name)


# -- get / set / delete ------------------------------------------------------


def test_set_get_roundtrip(manager: SecretsManager) -> None:
    ref = SecretRef("bard", "token")
    assert manager.get(ref) is None
    manager.set(ref, "abc123")
    assert manager.get(ref) == "abc123"


def test_set_empty_deletes(manager: SecretsManager) -> None:
    ref = SecretRef("bard", "token")
    manager.set(ref, "abc123")
    manager.set(ref, "")
    assert manager.get(ref) is None


def test_delete_reports_existence(manager: SecretsManager) -> None:
    ref = SecretRef("bard", "token")
    assert manager.delete(ref) is False
    manager.set(ref, "v")
    assert manager.delete(ref) is True
    assert manager.get(ref) is None


# -- JSON bundles ------------------------------------------------------------


def test_json_roundtrip(manager: SecretsManager) -> None:
    ref = SecretRef("bard", "patron-tokens")
    bundle = {"access_token": "a", "refresh_token": "r", "expires_at": 123.0}
    manager.set_json(ref, bundle)
    assert manager.get_json(ref) == bundle


def test_get_json_absent_is_none(manager: SecretsManager) -> None:
    assert manager.get_json(SecretRef("bard", "missing")) is None


def test_get_json_malformed_is_none(manager: SecretsManager) -> None:
    ref = SecretRef("bard", "corrupt")
    manager.set(ref, "not-json{{{")
    assert manager.get_json(ref) is None


def test_get_json_non_object_is_none(manager: SecretsManager) -> None:
    ref = SecretRef("bard", "listy")
    manager.set(ref, json.dumps([1, 2, 3]))
    assert manager.get_json(ref) is None


# -- wipe_namespace ----------------------------------------------------------


def test_wipe_namespace_clears_all_and_counts(manager: SecretsManager) -> None:
    manager.set(SecretRef("bard", "token"), "t")
    manager.set(SecretRef("bard", "client-id"), "c")
    manager.set_json(SecretRef("bard", "patron-tokens"), {"access_token": "x"})

    removed = manager.wipe_namespace("bard")

    assert removed == 3
    assert manager.get(SecretRef("bard", "token")) is None
    assert manager.get(SecretRef("bard", "client-id")) is None
    assert manager.get_json(SecretRef("bard", "patron-tokens")) is None


def test_wipe_namespace_leaves_other_namespaces(manager: SecretsManager) -> None:
    manager.set(SecretRef("bard", "token"), "t")
    manager.set(SecretRef("radio", "token"), "keep-me")

    manager.wipe_namespace("bard")

    assert manager.get(SecretRef("radio", "token")) == "keep-me"


def test_wipe_namespace_empty_is_zero(manager: SecretsManager) -> None:
    assert manager.wipe_namespace("bard") == 0


def test_index_prunes_on_delete(manager: SecretsManager) -> None:
    # After deleting the only secret, a later wipe should find nothing to remove.
    ref = SecretRef("bard", "token")
    manager.set(ref, "t")
    manager.delete(ref)
    assert manager.wipe_namespace("bard") == 0


def test_no_secret_value_in_index(manager: SecretsManager) -> None:
    # The index tracks names only -- never the secret value itself.
    backend = manager._backend  # type: ignore[attr-defined]
    manager.set(SecretRef("bard", "token"), "super-secret-value")
    index_raw = backend.store["quill-bard-__index__"]  # type: ignore[attr-defined]
    assert "super-secret-value" not in index_raw
    assert "token" in index_raw
