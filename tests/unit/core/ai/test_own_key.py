"""AI help with the user's own OpenAI key."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from quill.core.ai import own_key

_REPO = Path(__file__).resolve().parents[4]


def _gateway_prompts():
    spec = importlib.util.spec_from_file_location(
        "gateway_prompts", _REPO / "quill-ai-gateway" / "app" / "prompts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_instructions_are_the_gateways_word_for_word() -> None:
    """A summary is the same summary whichever way the request travels."""
    gateway = _gateway_prompts()
    for feature in gateway.SHIPPED_FEATURES:
        system, user = own_key.request_for(feature, "PROMPT", ["ONE", "TWO"])
        assert gateway.build_prompt(feature, "PROMPT", ["ONE", "TWO"]) == system + "\n\n" + user


def test_every_shipped_feature_is_on_and_unlimited_by_an_allowance() -> None:
    gateway = _gateway_prompts()
    for feature in gateway.SHIPPED_FEATURES:
        assert own_key.OWN_KEY_LIMITS.feature_available(feature)
    assert own_key.OWN_KEY_LIMITS.max_input_tokens > 50_000


def test_a_saved_key_alone_lifts_the_limits_and_removing_it_restores_them(monkeypatch) -> None:
    monkeypatch.setattr(own_key, "has_own_key", lambda: True)
    assert own_key.own_key_active(object())
    monkeypatch.setattr(own_key, "has_own_key", lambda: False)
    assert not own_key.own_key_active(object())


def test_a_request_goes_to_openai_with_the_system_message(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    sent: dict[str, object] = {}

    def fake(connection, key, prompt, **kwargs):  # noqa: ANN001, ANN003
        sent.update(provider=connection.provider, model=connection.model, key=key, prompt=prompt)
        sent.update(kwargs)
        return "Short summary.", None

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _p: "sk-test")
    monkeypatch.setattr(assistant_ai, "generate_assistant_response", fake)
    answer = own_key.ask_with_own_key("summarize", "Long text", model="gpt-test")
    assert answer == "Short summary."
    assert sent["provider"] == "openai" and sent["model"] == "gpt-test"
    assert sent["prompt"] == "Long text"
    assert str(sent["system_prompt"]).startswith("Summarize the following text")


def test_a_failure_is_a_sentence_with_a_code(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _p: "sk-test")
    monkeypatch.setattr(
        assistant_ai, "generate_assistant_response", lambda *a, **k: (None, "Invalid API key.")
    )
    with pytest.raises(own_key.OwnKeyError) as caught:
        own_key.ask_with_own_key("rewrite", "text")
    assert "Invalid API key" in str(caught.value)
    assert caught.value.code == "QUILL-AI-OWN-KEY-FAILED"


def test_no_key_says_so(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _p: "")
    with pytest.raises(own_key.OwnKeyError, match="No OpenAI key"):
        own_key.ask_with_own_key("explain", "text")
