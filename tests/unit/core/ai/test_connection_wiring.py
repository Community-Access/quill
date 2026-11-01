"""The connection layer's wiring into the clients: the local ChatGPT count, the
503 retry, a 429 that is not the plan's limit, a revoked refresh, and the own
key's rate-limit headers (codex.md 10A.5, 10A.11, decisions 13 and 24)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai import chatgpt_ai_help, chatgpt_http, connection_usage, own_key
from quill.core.ai.chatgpt_client import ChatGptAnswer
from quill.core.ai.chatgpt_errors import (
    ChatGptBusyError,
    ChatGptLimitError,
    ChatGptUsageUnavailableError,
)
from quill.core.ai.chatgpt_usage import local_count
from quill.core.ai.text_only import FAMILY_INSTRUCTION


def test_every_plan_request_is_counted_locally_with_its_tokens(tmp_path, monkeypatch) -> None:
    sent: list[dict[str, Any]] = []

    def respond(token: str, **kwargs: Any) -> ChatGptAnswer:
        sent.append(kwargs)
        return ChatGptAnswer(text="ok", input_tokens=12, output_tokens=5)

    monkeypatch.setattr(chatgpt_ai_help, "respond", respond)
    account = SimpleNamespace(
        data_dir=tmp_path,
        slug="quill-lite",
        model="gpt-6",
        web_search=False,
        access_token=lambda: "tok",
    )
    chatgpt_ai_help.ask_with_chatgpt(account, "summarize", "Some text")  # type: ignore[arg-type]
    chatgpt_ai_help.converse_with_chatgpt(account, "Hi", None, [])  # type: ignore[arg-type]
    count = local_count(tmp_path, "quill-lite")
    assert count.requests_today == 2
    assert (count.input_tokens_today, count.output_tokens_today) == (24, 10)
    assert all(call["instructions"].endswith(FAMILY_INSTRUCTION) for call in sent)
    assert local_count(tmp_path, "quill").requests_today == 0  # another app's count


def _body(code: str) -> bytes:
    return json.dumps({"error": {"code": code, "message": ""}}).encode()


def test_usage_unavailable_gets_the_bounded_retry_and_a_limit_does_not(monkeypatch) -> None:
    monkeypatch.setattr(chatgpt_http, "pause", lambda _s: None)
    url = "https://api.openai.com/v1/responses"

    def opener_failing(status: int, code: str, times: int):
        calls = {"n": 0}

        def run(_request: Any):
            calls["n"] += 1
            raise chatgpt_http._http_failure(status, _body(code), url, {})

        return run, calls

    run, calls = opener_failing(503, "subscription_sharing_usage_unavailable", 99)
    with pytest.raises(ChatGptUsageUnavailableError):
        chatgpt_http.stream_sse(url, {}, token="t", on_event=lambda *_a: None, opener=run)
    assert calls["n"] == 3  # the shared ladder's three attempts, then the sentence

    run, calls = opener_failing(429, "subscription_sharing_usage_limit_exceeded", 99)
    with pytest.raises(ChatGptLimitError) as raised:
        chatgpt_http.stream_sse(url, {}, token="t", on_event=lambda *_a: None, opener=run)
    assert calls["n"] == 1 and not isinstance(raised.value, ChatGptBusyError)


def test_a_plain_429_is_busy_not_the_plans_limit() -> None:
    error = chatgpt_http._error_for_status(429, b"", "https://api.openai.com/v1/responses")
    assert isinstance(error, ChatGptBusyError) and isinstance(error, ChatGptLimitError)


def test_a_dead_refresh_marks_the_sign_in_ended_by_openai(tmp_path) -> None:
    from quill.core.ai.chatgpt_account import ChatGptAccount
    from quill.core.ai.chatgpt_errors import ChatGptSignedOutError
    from quill.core.ai.chatgpt_state import ChatGptState, save_state

    class Store:
        def __init__(self) -> None:
            self.values = {"x": "refresh"}

        def get(self, _ref: Any) -> str:
            return self.values.get("x", "")

        def set(self, _ref: Any, value: str) -> None:
            self.values["x"] = value

        def delete(self, _ref: Any) -> None:
            self.values.pop("x", None)

    save_state(tmp_path, ChatGptState(client_id="c", subject="s"), "quill")
    account = ChatGptAccount(
        tmp_path,
        agent_name="QUILL",
        secrets_manager=Store(),  # type: ignore[arg-type]
        poster=lambda _u, _f: {"error": "invalid_grant"},
    )
    assert account.signed_in and not account.ended_by_openai
    with pytest.raises(ChatGptSignedOutError):
        account.access_token()
    assert not account.signed_in and account.ended_by_openai
    reloaded = ChatGptAccount(tmp_path, agent_name="QUILL", secrets_manager=Store())  # type: ignore[arg-type]
    assert reloaded.state.ended_by_openai


def test_the_own_key_keeps_openais_rate_limit_headers_from_its_answer(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    connection_usage.clear_rate_limits()
    seen: dict[str, Any] = {}

    def fake(connection: Any, key: str, prompt: str, **kwargs: Any):
        seen.update(kwargs)
        kwargs["on_headers"]({"x-ratelimit-remaining-requests": "480"})
        return "An answer.", None

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _p: "sk-test")
    monkeypatch.setattr(assistant_ai, "generate_assistant_response", fake)
    assert own_key.ask_with_own_key("ask", "Why?") == "An answer."
    snapshot = connection_usage.last_rate_limits("openai")
    assert snapshot is not None and snapshot.remaining_requests == 480
    assert str(seen["system_prompt"]).endswith(FAMILY_INSTRUCTION)
    # The template itself is untouched: the line is appended, never edited in.
    assert FAMILY_INSTRUCTION not in own_key.INSTRUCTIONS["ask"]
    connection_usage.clear_rate_limits()
