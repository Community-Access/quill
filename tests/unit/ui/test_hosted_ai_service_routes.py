"""Which way a request travels: a ChatGPT sign-in, an own key, or the free service."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.ai import own_key
from quill.ui.hosted_ai_service import AiService


class _App:
    ai_agent_name = "QUILL Lite"

    def __init__(self, data_dir) -> None:
        self.data_dir = data_dir
        self.settings = SimpleNamespace(ai_own_key_model="gpt-own")


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = AiService(_App(tmp_path))
    monkeypatch.setattr(own_key, "has_own_key", lambda *_a: False)
    return svc


def _signed_in(service, monkeypatch, *, model="gpt-6", web=False):
    account = SimpleNamespace(signed_in=True, model=model, web_search=web, agent_name="QUILL Lite")
    monkeypatch.setattr(service, "_chatgpt", account, raising=False)
    return account


def test_the_account_is_built_once_with_the_apps_agent_name(service) -> None:
    account = service.chatgpt
    assert account.agent_name == "QUILL Lite"
    assert account is service.chatgpt
    assert not service.chatgpt_active
    assert service.route == "free"
    assert not service.direct


def test_a_sign_in_outranks_a_saved_key(service, monkeypatch) -> None:
    monkeypatch.setattr(own_key, "has_own_key", lambda *_a: True)
    assert service.route == "own_key"
    assert service.route_label == "your own OpenAI key"
    assert service.direct_model == "gpt-own"
    _signed_in(service, monkeypatch)
    assert service.route == "chatgpt"
    assert service.route_label == "your ChatGPT subscription"
    assert service.direct_model == "gpt-6"
    assert service.direct


def test_the_plan_lifts_every_limit_and_needs_no_connection(service, monkeypatch) -> None:
    _signed_in(service, monkeypatch)
    assert service.limits.max_input_tokens > 50_000
    assert service.limits.feature_available("image")
    assert service.unavailable_reason("chat") == ""
    # A limits refresh asks QUILL's service nothing on a direct route.
    called = []
    monkeypatch.setattr("quill.ui.hosted_ai_service._submit", lambda *a, **k: called.append(a))
    service.refresh_limits()
    assert called == []


def test_the_size_note_matches_the_route(service, monkeypatch) -> None:
    assert service.size_note("words") == ""
    monkeypatch.setattr(own_key, "has_own_key", lambda *_a: True)
    assert "on your OpenAI account" in service.size_note("some words")
    _signed_in(service, monkeypatch)
    note = service.size_note("some words")
    assert "ChatGPT subscription" in note
    assert "$" not in note


def test_the_conversation_note_matches_the_route(service, monkeypatch) -> None:
    assert "free requests" in service.conversation_note()
    monkeypatch.setattr(own_key, "has_own_key", lambda *_a: True)
    assert "own OpenAI key" in service.conversation_note()
    _signed_in(service, monkeypatch)
    assert "ChatGPT subscription" in service.conversation_note()


def test_ask_and_converse_go_to_the_plan_when_signed_in(service, monkeypatch) -> None:
    account = _signed_in(service, monkeypatch)
    import quill.ui.hosted_ai_service as module

    ran = []

    def run_now(name, work, *, on_success, on_failure):
        ran.append(name)
        on_success(name, work())

    monkeypatch.setattr(module, "_submit", run_now)
    monkeypatch.setattr(module, "_call_after", lambda fn, *a: fn(*a))
    sent = {}

    def fake_ask(acct, feature, prompt, chunks, *, language):
        sent.update(acct=acct, feature=feature, prompt=prompt, language=language)
        return "Summary."

    def fake_converse(acct, prompt, chunks, history):
        sent.update(history=history)
        return "Reply."

    monkeypatch.setattr("quill.core.ai.chatgpt_ai_help.ask_with_chatgpt", fake_ask)
    monkeypatch.setattr("quill.core.ai.chatgpt_ai_help.converse_with_chatgpt", fake_converse)
    answers = []
    service.ask(
        "summarize",
        "text",
        None,
        on_done=lambda t, q: answers.append((t, q)),
        on_error=answers.append,
    )
    assert answers == [("Summary.", None)]
    assert sent["acct"] is account and sent["language"] == "English"
    service.converse(
        "hi",
        None,
        [{"role": "user", "content": "x"}],
        on_done=lambda *a: answers.append(a),
        on_error=answers.append,
    )
    assert answers[-1] == ("Reply.", None, 0)
    assert ran == ["quill-ai-ask", "quill-ai-converse"]


def test_describe_image_reports_a_bad_file_as_its_own_sentence(service, monkeypatch) -> None:
    _signed_in(service, monkeypatch)
    import quill.ui.hosted_ai_service as module

    def run_now(name, work, *, on_success, on_failure):
        try:
            on_success(name, work())
        except Exception as error:  # noqa: BLE001 - the harness stands in for the thread
            on_failure(name, error)

    monkeypatch.setattr(module, "_submit", run_now)
    monkeypatch.setattr(module, "_call_after", lambda fn, *a: fn(*a))
    heard = []
    service.describe_image("nowhere.png", "", on_done=heard.append, on_error=heard.append)
    assert heard == ["There is no file at nowhere.png."]


def test_cancelling_one_window_does_not_cancel_another_request(service, monkeypatch) -> None:
    """A service is shared by windows; Stop owns only the request returned to it."""
    import quill.ui.hosted_ai_service as module

    submitted = []

    def hold(_name, work, *, on_success, on_failure):
        submitted.append((work, on_success, on_failure))

    monkeypatch.setattr(module, "_submit", hold)
    monkeypatch.setattr(module, "_call_after", lambda fn, *args: fn(*args))
    first, second = [], []
    request_one = service.ask(
        "summarize",
        "first",
        None,
        on_done=lambda text, _quota: first.append(text),
        on_error=first.append,
    )
    request_two = service.ask(
        "summarize",
        "second",
        None,
        on_done=lambda text, _quota: second.append(text),
        on_error=second.append,
    )

    assert service.cancel(request_one)
    assert not request_two.is_set()
    submitted[0][1]("quill-ai-ask", ("first answer", None))
    submitted[1][1]("quill-ai-ask", ("second answer", None))

    assert first == []
    assert second == ["second answer"]
