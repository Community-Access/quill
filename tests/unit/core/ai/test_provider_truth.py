"""Phase 1 — one provider truth: key convergence, migration, policy filtering."""

from __future__ import annotations

import quill.core.assistant_ai as aai
from quill.core import ai_chat
from quill.core.ai.admin_policy import AdminPolicy
from quill.core.ai.key_migration import consolidate_provider_keys
from quill.core.ai.providers import ALL_PROVIDERS, allowed_providers


class FakeStore:
    """In-memory stand-in for the OS credential store."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.data.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.data[name] = value

    def delete(self, name: str) -> None:
        self.data.pop(name, None)


def _patch_store(monkeypatch) -> FakeStore:  # type: ignore[no-untyped-def]
    store = FakeStore()
    monkeypatch.setattr(aai, "_cs_load", store.load)
    monkeypatch.setattr(aai, "_cs_save", store.save)
    monkeypatch.setattr(aai, "_cs_delete", store.delete)
    return store


# -- ai_chat now reads the canonical per-provider credential targets ----------


def test_ai_chat_credential_names_are_canonical() -> None:
    assert ai_chat.PROVIDERS["openai"]["credential_name"] == aai.provider_credential_target(
        "openai"
    )
    assert ai_chat.PROVIDERS["openrouter"]["credential_name"] == aai.provider_credential_target(
        "openrouter"
    )
    assert ai_chat.PROVIDERS["ollama_cloud"]["credential_name"] == aai.provider_credential_target(
        "ollama_cloud"
    )
    # The local Ollama provider needs no key.
    assert ai_chat.PROVIDERS["ollama_local"]["credential_name"] is None


# -- reversible, non-destructive key migration --------------------------------


def test_migration_copies_legacy_into_canonical(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    store = _patch_store(monkeypatch)
    store.save("quill-openai-api-key", "sk-legacy-openai")
    store.save("quill-openrouter-api-key", "sk-legacy-or")
    # No active-provider global migration in this test.
    monkeypatch.setattr(
        aai, "load_assistant_connection_settings", lambda: type("S", (), {"provider": "off"})()
    )

    migrated = consolidate_provider_keys()

    assert set(migrated) == {"openai", "openrouter"}
    assert store.load(aai.provider_credential_target("openai")) == "sk-legacy-openai"
    assert store.load(aai.provider_credential_target("openrouter")) == "sk-legacy-or"
    # Legacy secret is preserved (reversible).
    assert store.load("quill-openai-api-key") == "sk-legacy-openai"


def test_migration_never_overwrites_a_set_canonical_slot(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    store = _patch_store(monkeypatch)
    store.save(aai.provider_credential_target("openai"), "sk-canonical")
    store.save("quill-openai-api-key", "sk-legacy")
    monkeypatch.setattr(
        aai, "load_assistant_connection_settings", lambda: type("S", (), {"provider": "off"})()
    )

    migrated = consolidate_provider_keys()

    assert "openai" not in migrated
    assert store.load(aai.provider_credential_target("openai")) == "sk-canonical"  # untouched


def test_migration_is_idempotent(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    store = _patch_store(monkeypatch)
    store.save("quill-openai-api-key", "sk-legacy")
    monkeypatch.setattr(
        aai, "load_assistant_connection_settings", lambda: type("S", (), {"provider": "off"})()
    )

    first = consolidate_provider_keys()
    second = consolidate_provider_keys()

    assert first == ["openai"]
    assert second == []  # nothing left to do


def test_migration_moves_global_active_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    store = _patch_store(monkeypatch)
    monkeypatch.setattr(
        aai, "load_assistant_connection_settings", lambda: type("S", (), {"provider": "claude"})()
    )
    monkeypatch.setattr(aai, "load_assistant_api_key", lambda: "sk-ant-global")

    migrated = consolidate_provider_keys()

    assert "claude" in migrated
    assert store.load(aai.provider_credential_target("claude")) == "sk-ant-global"


def test_migration_never_raises(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def boom(_name: str) -> str:
        raise RuntimeError("credential store down")

    monkeypatch.setattr(aai, "_cs_load", boom)
    monkeypatch.setattr(
        aai, "load_assistant_connection_settings", lambda: type("S", (), {"provider": "off"})()
    )
    # Must not raise even if the store is broken.
    assert consolidate_provider_keys() == []


# -- admin-policy provider filtering ------------------------------------------


def test_allowed_providers_default_is_all() -> None:
    assert allowed_providers() == list(ALL_PROVIDERS)
    assert allowed_providers(None) == list(ALL_PROVIDERS)


def test_allowed_providers_applies_policy() -> None:
    policy = AdminPolicy(
        allowed_providers=frozenset({"claude", "ollama"}),
        blocked_providers=frozenset({"openai"}),
    )
    result = allowed_providers(policy)
    assert "claude" in result
    assert "ollama" in result
    assert "openai" not in result
    assert "off" in result  # disabling AI is never policy-blocked
