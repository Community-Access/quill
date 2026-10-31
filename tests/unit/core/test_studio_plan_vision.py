"""Studio reads pictures on its own ChatGPT plan sign-in: what is sent, and what is said."""

import pytest
from PIL import Image

from quill.core.ai.chatgpt_account import ChatGptAccount
from quill.core.ai.chatgpt_errors import (
    ChatGptLimitError,
    ChatGptSignedOutError,
    ChatGptUnavailableError,
    ChatGptUnsupportedError,
)
from quill.core.ai.chatgpt_state import ChatGptState, load_state, save_state, slug_for
from quill.core.studio_capture import verify_capture
from quill.core.studio_plan_vision import (
    PLAN_PROVIDER,
    STUDIO_AGENT,
    find_plan,
    plan_failure,
    plan_ready_image,
    siblings_signed_in,
)


class Secrets:
    def __init__(self):
        self.values = {}

    def get(self, ref):
        return self.values.get((ref.namespace, ref.name))

    def set(self, ref, value):
        self.values[(ref.namespace, ref.name)] = value

    def delete(self, ref):
        return self.values.pop((ref.namespace, ref.name), None) is not None


def _sign_in(data_dir, secrets, agent, model="gpt-plan"):
    slug = slug_for(agent)
    state = ChatGptState(
        client_id="client", subject="sub", email="me@example.org", model=model, agent_name=agent
    )
    save_state(data_dir, state, slug)
    secrets.values[("chatgpt", f"{slug}-refresh")] = f"refresh-{slug}"


def _studio(data_dir, secrets):
    return ChatGptAccount(data_dir, agent_name=STUDIO_AGENT, secrets_manager=secrets)


def test_no_studio_sign_in_finds_no_plan(tmp_path):
    assert find_plan(_studio(tmp_path, Secrets())) is None


def test_a_sibling_sign_in_is_never_used_only_mentioned(tmp_path):
    # Plan usage stays with the app the person connected.
    secrets = Secrets()
    _sign_in(tmp_path, secrets, "QUILL")
    _sign_in(tmp_path, secrets, "QUILL Lite")
    studio = _studio(tmp_path, secrets)
    assert find_plan(studio) is None
    assert sorted(siblings_signed_in(studio)) == ["QUILL", "QUILL Lite"]


def test_studios_own_sign_in_is_the_plan(tmp_path):
    secrets = Secrets()
    _sign_in(tmp_path, secrets, STUDIO_AGENT)
    plan = find_plan(_studio(tmp_path, secrets))
    assert plan is not None and plan.provider == PLAN_PROVIDER and plan.model == "gpt-plan"
    assert plan.label() == "your ChatGPT plan (me@example.org)"


def test_a_fitting_png_is_sent_as_it_is(tmp_path):
    path = tmp_path / "shot.png"
    Image.new("RGB", (40, 30), "white").save(path)
    assert plan_ready_image(path, tmp_path) == path


def test_a_format_the_plan_refuses_is_converted(tmp_path):
    path = tmp_path / "shot.bmp"
    Image.new("RGB", (40, 30), "white").save(path)
    ready = plan_ready_image(path, tmp_path)
    assert ready != path
    with Image.open(ready) as image:
        assert image.format == "PNG" and image.size == (40, 30)


def test_a_picture_too_large_is_scaled_down(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("RGB", (8000, 100), "white").save(path)
    with Image.open(plan_ready_image(path, tmp_path)) as image:
        assert max(image.size) <= 4096


def test_a_picture_too_heavy_is_shrunk_under_the_cap(tmp_path, monkeypatch):
    import os

    from quill.core import studio_plan_vision

    monkeypatch.setattr(studio_plan_vision, "_PLAN_IMAGE_LIMIT", 20_000)
    path = tmp_path / "noise.png"
    Image.frombytes("RGB", (400, 400), os.urandom(400 * 400 * 3)).save(path)
    assert plan_ready_image(path, tmp_path).stat().st_size <= 20_000


def test_not_a_picture_is_a_sentence(tmp_path):
    path = tmp_path / "notes.png"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="not a picture"):
        plan_ready_image(path, tmp_path)


@pytest.mark.parametrize(
    ("error", "words", "offers_usage"),
    [
        (ChatGptLimitError("x"), "usage limit has been reached", True),
        (ChatGptUnavailableError("x"), "could not check your ChatGPT plan's usage", False),
        (ChatGptUnsupportedError("no tools"), "not retried", False),
        (ChatGptSignedOutError("x"), "sign in again", False),
    ],
)
def test_the_plans_refusals_are_said_plainly(error, words, offers_usage):
    failure = plan_failure(error)
    assert words in str(failure)
    assert bool(failure.usage_url) is offers_usage


def test_unsupported_capability_is_its_own_final_error():
    from quill.core.ai.chatgpt_client import _failure
    from quill.core.ai.chatgpt_http import _http_failure

    payload = {"error": {"code": "subscription_sharing_unsupported_capability", "message": "m"}}
    assert isinstance(_failure(payload), ChatGptUnsupportedError)
    raw = b'{"error": {"code": "subscription_sharing_unsupported_capability"}}'
    error = _http_failure(400, raw, "https://api.openai.com/v1/responses", {})
    assert isinstance(error, ChatGptUnsupportedError) and error.retry_final


@pytest.fixture
def plan_and_capture(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    from quill.core.ai import model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)
    secrets = Secrets()
    _sign_in(tmp_path, secrets, STUDIO_AGENT)
    plan = find_plan(_studio(tmp_path, secrets))
    plan.account._access_token = "token"
    plan.account._access_expires_at = 10**12
    path = tmp_path / "screen.png"
    Image.new("RGB", (20, 30), "white").save(path)
    return plan, verify_capture(path, "screen")


def test_inspection_on_the_plan_sends_one_picture_and_no_key(plan_and_capture, monkeypatch):
    from quill.core.ai import chatgpt_client, vision
    from quill.core.studio_capture_ai import inspect_screenshot

    plan, evidence = plan_and_capture
    sent = {}

    def respond(token, **kwargs):
        sent.update(kwargs, token=token)
        return chatgpt_client.ChatGptAnswer(text="A white page.")

    monkeypatch.setattr(chatgpt_client, "respond", respond)
    monkeypatch.setattr(vision, "describe_image", lambda *a, **k: pytest.fail("API-key route"))
    text = inspect_screenshot(evidence, connection=plan, question="What is this?")
    assert "A white page." in text and "ChatGPT plan" in text
    assert sent["token"] == "token" and sent["model"] == "gpt-plan"
    content = sent["items"][0]["content"]
    assert [part["type"] for part in content] == ["input_text", "input_image"]
    assert "What is this?" in content[0]["text"]
    # The preview rejects these; none may be sent.
    assert not {"temperature", "max_output_tokens"} & set(sent)
    assert all(item["role"] == "user" for item in sent["items"])


def test_a_used_up_plan_stops_and_never_falls_back_to_a_key(plan_and_capture, monkeypatch):
    from quill.core.ai import chatgpt_client, vision
    from quill.core.studio_capture_ai import inspect_screenshot

    plan, evidence = plan_and_capture
    calls = []

    def respond(*_a, **_k):
        calls.append(1)
        raise ChatGptLimitError("limit")

    monkeypatch.setattr(chatgpt_client, "respond", respond)
    monkeypatch.setattr(vision, "describe_image", lambda *a, **k: pytest.fail("fell back"))
    with pytest.raises(RuntimeError, match="usage limit has been reached") as raised:
        inspect_screenshot(evidence, connection=plan)
    assert raised.value.usage_url.startswith("https://chatgpt.com/")
    assert calls == [1]


def test_a_plan_with_no_model_chosen_uses_and_keeps_its_first(
    plan_and_capture, monkeypatch, tmp_path
):
    from quill.core.ai import chatgpt_client
    from quill.core.studio_capture_ai import inspect_screenshot

    plan, evidence = plan_and_capture
    save_state(tmp_path, ChatGptState(client_id="c", subject="s"), "quill-studio")
    plan.account._state = None
    monkeypatch.setattr(
        chatgpt_client,
        "list_models",
        lambda _token: [chatgpt_client.ChatGptModel("first", "First")],
    )
    used = []
    monkeypatch.setattr(
        chatgpt_client,
        "respond",
        lambda _t, **k: used.append(k["model"]) or chatgpt_client.ChatGptAnswer(text="ok"),
    )
    inspect_screenshot(evidence, connection=plan)
    assert used == ["first"]
    assert load_state(tmp_path, "quill-studio").model == "first"
