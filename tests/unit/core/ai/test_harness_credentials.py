"""Tests for quill.core.ai.harness_credentials (the API-key onboarding gap
found while fixing #915/the AI Setup Wizard stuck-active bug: OpenAI Agents SDK
and Claude Agent SDK read auth from env vars with no in-app way to set one)."""

from __future__ import annotations

from quill.core.ai import harness_credentials as hc


def test_env_var_names_known_packs() -> None:
    assert hc.env_var_names("openai_agents") == ("OPENAI_API_KEY",)
    assert hc.env_var_names("claude_agent_sdk") == ("ANTHROPIC_API_KEY",)


def test_env_var_names_unknown_pack_is_empty() -> None:
    assert hc.env_var_names("copilot") == ()
    assert hc.env_var_names("not_a_pack") == ()


def test_supported_pack_ids_are_exactly_the_two_env_var_backed_harnesses() -> None:
    assert set(hc.SUPPORTED_PACK_IDS) == {"openai_agents", "claude_agent_sdk"}


def test_persist_stored_apply_and_forget_round_trip(monkeypatch) -> None:
    store: dict[str, str] = {}

    def fake_save(provider: str, api_key: str) -> bool:
        store[provider] = api_key
        return True

    def fake_load(provider: str) -> str:
        return store.get(provider, "")

    def fake_clear(provider: str) -> None:
        store.pop(provider, None)

    monkeypatch.setattr("quill.core.assistant_ai.save_provider_api_key", fake_save)
    monkeypatch.setattr("quill.core.assistant_ai.load_provider_api_key", fake_load)
    monkeypatch.setattr("quill.core.assistant_ai.clear_provider_api_key", fake_clear)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert hc.stored_key("openai_agents") == ""
    assert hc.persist_key("openai_agents", "sk-test-123") is True
    assert hc.stored_key("openai_agents") == "sk-test-123"

    hc.apply_key_to_environment("openai_agents", "sk-test-123")
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-test-123"

    hc.forget_key("openai_agents")
    assert hc.stored_key("openai_agents") == ""
    assert "OPENAI_API_KEY" not in os.environ


def test_apply_all_stored_keys_applies_every_supported_pack(monkeypatch) -> None:
    store = {"openai_agents": "sk-a", "claude_agent_sdk": "sk-b"}
    monkeypatch.setattr("quill.core.assistant_ai.load_provider_api_key", lambda p: store.get(p, ""))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    hc.apply_all_stored_keys()

    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-a"
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-b"


def test_apply_all_stored_keys_skips_packs_with_no_saved_key(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.assistant_ai.load_provider_api_key", lambda p: "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    hc.apply_all_stored_keys()

    import os

    assert "OPENAI_API_KEY" not in os.environ
    assert "ANTHROPIC_API_KEY" not in os.environ
