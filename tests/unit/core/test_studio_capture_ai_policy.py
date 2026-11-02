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


def _evidence(tmp_path, size=(3000, 2000)):
    from PIL import Image

    from quill.core.studio_capture import verify_capture

    path = tmp_path / "review.png"
    Image.new("RGB", size, "white").save(path)
    return verify_capture(path, "Test window")


def test_a_connection_that_cannot_see_gets_nothing_prepared(tmp_path):
    """The capability registry is asked first (GATE-CAPS), before the file is read."""
    from quill.core.ai.connection_caps import CapabilityMissing, record_for
    from quill.core.studio_capture_ai import prepare_inspection

    evidence = _evidence(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    with pytest.raises(CapabilityMissing):
        prepare_inspection(evidence, record=record_for("free"), folder=folder)
    assert list(folder.iterdir()) == []


def test_the_screenshot_is_fitted_to_the_connection_with_the_question(tmp_path):
    from PIL import Image

    from quill.core.ai.connection_caps import record_for
    from quill.core.ai.picture_prep import longest_side_for
    from quill.core.studio_capture_ai import prepare_inspection

    request = prepare_inspection(
        _evidence(tmp_path),
        record=record_for("chatgpt"),
        folder=tmp_path,
        instructions="My instructions",
        question="My question",
        history="Earlier answer",
    )
    with Image.open(request.path) as fitted:
        assert max(fitted.size) <= longest_side_for("chatgpt")
    assert "My instructions" in request.prompt and "My question" in request.prompt
    assert "Earlier answer" in request.prompt
    assert request.prepared.inspected.startswith("Looked at 1 picture")


def test_a_changed_screenshot_is_refused(tmp_path):
    from PIL import Image

    from quill.core.ai.connection_caps import record_for
    from quill.core.studio_capture_ai import prepare_inspection

    evidence = _evidence(tmp_path, (20, 30))
    Image.new("RGB", (20, 30), "red").save(evidence.path)
    with pytest.raises(ValueError, match="changed"):
        prepare_inspection(evidence, record=record_for("chatgpt"), folder=tmp_path)


def test_a_withdrawn_permission_stops_before_anything_is_written(tmp_path):
    from quill.core.ai.connection_caps import record_for
    from quill.core.studio_capture_ai import prepare_inspection

    folder = tmp_path / "out"
    folder.mkdir()
    with pytest.raises(RuntimeError, match="permission changed"):
        prepare_inspection(
            _evidence(tmp_path),
            record=record_for("chatgpt"),
            folder=folder,
            can_send=lambda: False,
        )
    assert list(folder.iterdir()) == []


def test_a_picture_route_is_its_own_identity():
    from quill.core.studio_capture_ai import PictureRoute

    route = PictureRoute("chatgpt", "gpt-x", "OpenAI on your ChatGPT plan", "My ChatGPT plan")
    prefs = {"auto_ai_enabled": True, "approved_connection": connection_identity(route)}
    assert auto_ai_allowed(prefs, route, ai_enabled=True, safe_mode=False)
    assert not auto_ai_allowed(prefs, PictureRoute("off"), ai_enabled=True, safe_mode=False)
    other = PictureRoute("copilot", "gpt-x", "GitHub on your Copilot plan", "My GitHub Copilot")
    assert not auto_ai_allowed(prefs, other, ai_enabled=True, safe_mode=False)
