"""The one retry ladder for AI provider calls, and each route that climbs it.

Every route is driven with fakes: no socket opens and no real second passes
(``time.sleep`` is replaced and records the waits it was asked for).
"""

from __future__ import annotations

import email.message
import io
import json
import urllib.error

import pytest

from quill.core.ai import retry_ladder
from quill.core.ai.retry_ladder import (
    LONGEST_WAIT_SECONDS,
    retry_after_seconds,
    wait_after_failure,
    wait_before_retry,
)


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    seen: list[float] = []
    monkeypatch.setattr(retry_ladder.time, "sleep", seen.append)
    return seen


def _headers(**values: str) -> email.message.Message:
    message = email.message.Message()
    for name, value in values.items():
        message[name.replace("_", "-")] = value
    return message


def _http_error(code: int, payload: object = None, **headers: str) -> urllib.error.HTTPError:
    body = io.BytesIO(json.dumps(payload or {}).encode())
    return urllib.error.HTTPError("https://x/", code, "busy", _headers(**headers), body)


# -- the policy ----------------------------------------------------------------- #


@pytest.mark.parametrize("status", [408, 409, 429, 500, 502, 503, 504])
def test_the_busy_statuses_climb_one_then_two_seconds(status: int) -> None:
    assert wait_before_retry(status, None, 1) == 1.0
    assert wait_before_retry(status, None, 2) == 2.0
    assert wait_before_retry(status, None, 3) is None  # three attempts in all


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 501])
def test_a_request_that_is_itself_wrong_is_never_asked_again(status: int) -> None:
    assert wait_before_retry(status, None, 1) is None


def test_retry_after_is_honoured_in_seconds_and_as_a_date() -> None:
    assert wait_before_retry(429, _headers(Retry_After="4"), 1) == 4.0
    date = "Wed, 21 Oct 2026 07:28:05 GMT"
    now = email.utils.parsedate_to_datetime(date).timestamp() - 6
    assert retry_after_seconds(date, now=now) == pytest.approx(6.0)
    assert retry_after_seconds("not a time") is None


def test_a_wait_too_long_to_sit_through_is_reported_now() -> None:
    too_long = str(int(LONGEST_WAIT_SECONDS) + 1)
    assert wait_before_retry(503, _headers(Retry_After=too_long), 1) is None


def test_the_api_saying_no_is_final_whatever_the_status() -> None:
    assert wait_before_retry(500, _headers(X_Should_Retry="false"), 1) is None
    assert wait_before_retry(500, {"X-Should-Retry": "false"}, 1) is None
    assert wait_before_retry(503, None, 1, final=True) is None


def test_a_lost_request_climbs_the_same_steps_and_a_refused_one_does_not() -> None:
    assert wait_after_failure(None, None, 1, lost=True) == 1.0
    assert wait_after_failure(None, None, 3, lost=True) is None
    assert wait_after_failure(None, None, 1, lost=False) is None


# -- QUILL's hosted service ------------------------------------------------------- #


def test_the_hosted_service_is_asked_again_silently_then_answers(monkeypatch, waits) -> None:
    from quill.core.ai import gateway_client as mod

    replies: list[object] = [_http_error(503, {"message": "busy"}), _http_error(502)]

    class _Ok:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

        def read(self):
            return b'{"text": "Answer."}'

    def fake_urlopen(*_a, **_k):
        if replies:
            raise replies.pop(0)
        return _Ok()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    assert mod._urlopen_json("https://ai.example.org/v1/chat", body={}) == {"text": "Answer."}
    assert waits == [1.0, 2.0]


def test_a_used_up_allowance_is_said_at_once(monkeypatch, waits) -> None:
    from quill.core.ai import gateway_client as mod
    from quill.core.ai.gateway_errors import GatewayQuotaError

    calls: list[int] = []

    def fake_urlopen(*_a, **_k):
        calls.append(1)
        raise _http_error(429, {"message": "Used up for today.", "scope": "daily"})

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(GatewayQuotaError, match="Used up for today"):
        mod._urlopen_json("https://ai.example.org/v1/chat", body={})
    assert calls == [1] and waits == []


def test_a_reply_that_says_it_was_charged_is_never_repeated(monkeypatch, waits) -> None:
    from quill.core.ai import gateway_client as mod
    from quill.core.ai.gateway_errors import GatewayServiceError

    calls: list[int] = []

    def fake_urlopen(*_a, **_k):
        calls.append(1)
        raise _http_error(500, {"message": "Failed after counting.", "charged": True})

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(GatewayServiceError, match="Failed after counting"):
        mod._urlopen_json("https://ai.example.org/v1/chat", body={})
    assert calls == [1] and waits == []


def test_only_the_last_failure_reaches_the_caller(monkeypatch, waits) -> None:
    from quill.core.ai import gateway_client as mod
    from quill.core.ai.gateway_errors import GatewayPausedError

    calls: list[int] = []

    def fake_urlopen(*_a, **_k):
        calls.append(1)
        raise _http_error(503, {"message": f"Paused ({len(calls)})."})

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(GatewayPausedError, match=r"Paused \(3\)"):
        mod._urlopen_json("https://ai.example.org/v1/chat", body={})
    assert len(calls) == 3 and waits == [1.0, 2.0]


# -- a ChatGPT plan --------------------------------------------------------------- #


def test_a_chatgpt_read_is_asked_again_with_retry_after(waits) -> None:
    from quill.core.ai.chatgpt_http import get_json

    replies = [(429, b"{}", _headers(Retry_After="3")), (200, b'{"models": []}', None)]
    assert get_json("https://chatgpt.example/models", opener=lambda _r: replies.pop(0)) == {
        "models": []
    }
    assert waits == [3.0]


def test_a_chatgpt_sign_in_post_is_never_repeated(waits) -> None:
    from quill.core.ai.chatgpt_errors import ChatGptError
    from quill.core.ai.chatgpt_http import post_json

    calls: list[int] = []

    def opener(_request):
        calls.append(1)
        return (503, b"{}")

    with pytest.raises(ChatGptError):
        post_json("https://auth.example/token", {"code": "once"}, opener=opener)
    assert calls == [1] and waits == []


def test_a_chatgpt_stream_refused_before_it_began_is_asked_again(waits) -> None:
    from quill.core.ai.chatgpt_http import _http_failure, stream_sse

    attempts: list[int] = []

    def opener(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise _http_failure(502, b"{}", request.full_url, None)
        yield b'data: {"type": "response.output_text.delta", "delta": "Hi"}'
        yield b""

    events: list[str] = []
    stream_sse(
        "https://chatgpt.example/r",
        {},
        token="t",
        on_event=lambda t, _p: events.append(t),
        opener=opener,
    )
    assert events == ["response.output_text.delta"]
    assert waits == [1.0]


def test_a_used_up_chatgpt_plan_is_final(waits) -> None:
    from quill.core.ai.chatgpt_errors import ChatGptLimitError
    from quill.core.ai.chatgpt_http import _http_failure, stream_sse

    raw = json.dumps({
        "error": {"code": "subscription_sharing_usage_limit_exceeded", "message": "Limit."}
    }).encode()

    def opener(request):
        raise _http_failure(429, raw, request.full_url, None)
        yield b""  # pragma: no cover - makes this a generator

    with pytest.raises(ChatGptLimitError):
        stream_sse(
            "https://chatgpt.example/r", {}, token="t", on_event=lambda *_a: None, opener=opener
        )
    assert waits == []


# -- the person's own key ----------------------------------------------------------- #


def test_an_own_key_chat_honours_retry_after_and_409(monkeypatch, waits) -> None:
    from quill.core import assistant_ai

    replies: list[object] = [
        assistant_ai.HTTPError("https://api.openai.com/v1", 409, "x", _headers(), None),
        assistant_ai.HTTPError(
            "https://api.openai.com/v1", 429, "x", _headers(Retry_After="5"), None
        ),
    ]

    class _Ok:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "Done."}}]}).encode()

    def fake_urlopen(*_a, **_k):
        if replies:
            raise replies.pop(0)
        return _Ok()

    monkeypatch.setattr(assistant_ai, "urlopen", fake_urlopen)
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: False)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = assistant_ai.generate_assistant_response(settings, "sk-test", "Hi")
    assert (text, error) == ("Done.", None)
    assert waits == [1.0, 5.0]


def test_an_own_key_chat_the_provider_forbids_repeating_is_said_once(monkeypatch, waits) -> None:
    from quill.core import assistant_ai

    calls: list[int] = []

    def fake_urlopen(*_a, **_k):
        calls.append(1)
        raise assistant_ai.HTTPError(
            "https://api.openai.com/v1", 500, "x", _headers(X_Should_Retry="false"), None
        )

    monkeypatch.setattr(assistant_ai, "urlopen", fake_urlopen)
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: False)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = assistant_ai.generate_assistant_response(settings, "sk-test", "Hi")
    assert text is None and error == "The AI provider is warming up. Try again in a moment."
    assert calls == [1] and waits == []
