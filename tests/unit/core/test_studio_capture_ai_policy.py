"""Auto AI must be opt-in, connection-specific, and blocked by AI Off/Safe Mode."""

from types import SimpleNamespace

import pytest

from quill.core.studio_capture_ai import (
    SCREENSHOT_PROMPTS,
    auto_ai_allowed,
    capture_prompt,
    connection_identity,
    prompt_choices,
)


@pytest.fixture
def connection():
    return SimpleNamespace(provider="openai", model="vision-model", host="https://example.org")


def test_auto_is_off_without_recorded_approval(connection):
    assert not auto_ai_allowed({}, connection, ai_enabled=True, safe_mode=False)
    assert not auto_ai_allowed(
        {"auto_ai_enabled": True}, connection, ai_enabled=True, safe_mode=False
    )


@pytest.mark.parametrize("enabled,safe", [(False, False), (True, True), (False, True)])
def test_ai_off_and_safe_mode_override_persisted_consent(connection, enabled, safe):
    prefs = {"auto_ai_enabled": True, "approved_connection": connection_identity(connection)}
    assert not auto_ai_allowed(prefs, connection, ai_enabled=enabled, safe_mode=safe)


@pytest.mark.parametrize(
    "field,value",
    [("provider", "gemini"), ("model", "other-model"), ("host", "https://other.example")],
)
def test_connection_changes_pause_auto_analysis(connection, field, value):
    prefs = {"auto_ai_enabled": True, "approved_connection": connection_identity(connection)}
    assert auto_ai_allowed(prefs, connection, ai_enabled=True, safe_mode=False)
    setattr(connection, field, value)
    assert not auto_ai_allowed(prefs, connection, ai_enabled=True, safe_mode=False)


def test_custom_and_shared_prompts_are_available():
    settings = SimpleNamespace(
        vision_disabled_builtin_styles=[],
        vision_builtin_overrides={},
        vision_custom_prompts=[
            {"id": "my-prompt", "title": "My review", "prompt": "Find the warning"}
        ],
    )
    ids = {choice["id"] for choice in prompt_choices(settings)}
    assert set(SCREENSHOT_PROMPTS) <= ids
    assert "accessibility" in ids and "my-prompt" in ids
    assert capture_prompt("my-prompt", settings) == "Find the warning"
    assert "Do not invent shortcuts" in capture_prompt("screen-controls", settings)


@pytest.mark.parametrize(
    "provider", ["openai", "gemini", "claude", "openrouter", "custom", "ollama", "ollama_cloud"]
)
def test_screenshots_reuse_shared_provider_transport_and_credentials(
    tmp_path, monkeypatch, provider
):
    from PIL import Image

    from quill.core.assistant_ai import AssistantConnectionSettings
    from quill.core.studio_capture import verify_capture
    from quill.core.studio_capture_ai import inspect_screenshot

    path = tmp_path / "review.png"
    Image.new("RGB", (3, 2), "white").save(path)
    evidence = verify_capture(path, "Test window")
    connection = AssistantConnectionSettings(
        provider, "https://configured.example", "configured-model"
    )
    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: True)
    requested_keys = []

    def shared_key(selected):
        requested_keys.append(selected)
        return "provider-specific-test-key"

    monkeypatch.setattr("quill.core.assistant_ai.load_keyed_provider_api_key", shared_key)

    def shared_vision(settings, key, image, **kwargs):
        assert settings is connection
        assert key == "provider-specific-test-key"
        assert image.read_bytes() == path.read_bytes()
        assert "My instructions" in kwargs["prompt"]
        assert "My question" in kwargs["prompt"]
        return "Shared vision response", None

    monkeypatch.setattr("quill.core.ai.vision.describe_image", shared_vision)
    result = inspect_screenshot(
        evidence, connection=connection, instructions="My instructions", question="My question"
    )
    assert requested_keys == [provider]
    assert f"AI ({provider}, configured-model)" in result
    assert "Shared vision response" in result
