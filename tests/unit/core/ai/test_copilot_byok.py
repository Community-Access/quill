"""The SDK 2 BYOK route is explicit, validated, and never borrows env keys."""

from __future__ import annotations

import pytest

from quill.core.ai import copilot_byok


def test_openai_connection_uses_the_selected_model_and_provider_key() -> None:
    connection = copilot_byok.make_connection(
        "openai", "gpt-test", "https://api.openai.com/v1", "sk-test"
    )

    assert connection.provider_type == "openai"
    assert connection.model == "gpt-test"
    assert connection.base_url == "https://api.openai.com/v1"
    assert connection.inference_options() == {
        "default_provider": "quill_user",
        "providers": [
            {
                "name": "quill_user",
                "type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test",
            }
        ],
    }
    assert "sk-test" not in repr(connection)


@pytest.mark.parametrize(
    ("provider", "host", "expected_type", "expected_url"),
    [
        ("gemini", "https://generativelanguage.googleapis.com", "google", "/v1beta"),
        ("openrouter", "https://openrouter.ai/api", "openai", "/api/v1"),
        ("ollama_cloud", "https://ollama.com", "openai", "/v1"),
        ("custom", "https://ai.example.test", "openai", "/v1"),
    ],
)
def test_compatible_provider_endpoints_are_normalized(
    provider: str, host: str, expected_type: str, expected_url: str
) -> None:
    connection = copilot_byok.make_connection(provider, "model-test", host, "key-test")

    assert connection.provider_type == expected_type
    assert connection.base_url.endswith(expected_url)


def test_loopback_endpoint_can_be_used_without_a_key() -> None:
    connection = copilot_byok.make_connection("custom", "local-model", "http://127.0.0.1:8080", "")

    assert connection.local_only
    assert "api_key" not in connection.inference_options()["providers"][0]


@pytest.mark.parametrize(
    "host",
    [
        "http://remote.example.test",
        "https://user:password@ai.example.test",
        "https://ai.example.test?token=secret",
        "file:///tmp/provider",
    ],
)
def test_unsafe_remote_or_credential_bearing_endpoint_is_rejected(host: str) -> None:
    with pytest.raises(ValueError):
        copilot_byok.make_connection("custom", "model-test", host, "key-test")


def test_missing_model_or_remote_key_is_reported() -> None:
    with pytest.raises(ValueError, match="Choose a model"):
        copilot_byok.make_connection("openai", "", "https://api.openai.com", "key-test")
    with pytest.raises(ValueError, match="Save this provider"):
        copilot_byok.make_connection("openai", "model-test", "https://api.openai.com", "")


def test_selected_connection_never_uses_an_environment_key(monkeypatch) -> None:
    from quill.core import assistant_ai
    from quill.core.ai import own_key_providers

    monkeypatch.setattr(
        own_key_providers, "host_for", lambda _provider: "https://api.openai.com/v1"
    )
    monkeypatch.setattr(assistant_ai, "stored_provider_api_key", lambda _provider: "")
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-test-key")

    with pytest.raises(ValueError, match="Save this provider"):
        copilot_byok.load_selected_connection("openai", "gpt-test")
