"""Provider chat generation, backend, and routing (AI-13, AI-15, AI-16, AI-17)."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError

import pytest

import quill.core.assistant_ai as assistant_ai
from quill.core.assistant_ai import (
    AssistantConnectionSettings,
    build_chat_body,
    build_chat_headers,
    chat_endpoint,
    generate_assistant_response,
    parse_chat_response,
)


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._data


def _capture_urlopen(monkeypatch: pytest.MonkeyPatch, payload: object) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float | None = None, context: object = None):
        captured["url"] = request.full_url  # type: ignore[attr-defined]
        captured["body"] = request.data  # type: ignore[attr-defined]
        captured["method"] = request.get_method()  # type: ignore[attr-defined]
        return _FakeResponse(payload)

    monkeypatch.setattr(assistant_ai, "urlopen", fake_urlopen)
    return captured


# --- pure request/response contract (AI-15, AI-16) -------------------------


def test_chat_endpoint_per_provider() -> None:
    assert chat_endpoint("openai", "https://api.openai.com", "gpt-4o-mini").endswith(
        "/v1/chat/completions"
    )
    assert chat_endpoint("claude", "https://api.anthropic.com", "x").endswith("/v1/messages")
    assert ":generateContent" in chat_endpoint("gemini", "https://g.example", "gemini-2.0-flash")
    assert chat_endpoint("ollama", "http://localhost:11434", "llama3").endswith("/api/chat")


def test_build_chat_body_claude_requires_max_tokens() -> None:
    body = build_chat_body("claude", "claude-3-5-sonnet-latest", "hi", max_tokens=256)
    assert body["max_tokens"] == 256
    assert body["messages"] == [{"role": "user", "content": "hi"}]


def test_build_chat_body_gemini_uses_contents() -> None:
    body = build_chat_body("gemini", "gemini-2.0-flash", "hi")
    assert "contents" in body


def test_build_chat_body_ollama_sets_stream_false() -> None:
    body = build_chat_body("ollama", "llama3", "hi")
    assert body["stream"] is False


def test_build_chat_headers_openrouter_attribution() -> None:
    headers = build_chat_headers("openrouter", "https://openrouter.ai/api", "key")
    assert headers["HTTP-Referer"]
    assert headers["X-Title"] == "QUILL"
    assert headers["Authorization"] == "Bearer key"


def test_parse_chat_response_openai_compatible() -> None:
    payload = {"choices": [{"message": {"content": "hello"}}]}
    assert parse_chat_response("openai", payload) == "hello"


def test_parse_chat_response_claude() -> None:
    payload = {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
    assert parse_chat_response("claude", payload) == "ab"


def test_parse_chat_response_gemini() -> None:
    payload = {"candidates": [{"content": {"parts": [{"text": "g"}]}}]}
    assert parse_chat_response("gemini", payload) == "g"


def test_parse_chat_response_ollama() -> None:
    assert parse_chat_response("ollama", {"message": {"content": "o"}}) == "o"


def test_parse_chat_response_handles_garbage() -> None:
    assert parse_chat_response("openai", {"unexpected": 1}) is None
    assert parse_chat_response("openai", "not a dict") is None


# --- end-to-end generation with mocked network (AI-13) ---------------------


def test_generate_openai_returns_text_and_targets_chat_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch, {"choices": [{"message": {"content": "the answer"}}]})
    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = generate_assistant_response(settings, "sk-test", "question")
    assert error is None
    assert text == "the answer"
    assert str(captured["url"]).endswith("/v1/chat/completions")
    assert b"gpt-4o-mini" in bytes(captured["body"])  # type: ignore[arg-type]
    assert captured["method"] == "POST"


def test_generate_claude_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    _capture_urlopen(monkeypatch, {"content": [{"type": "text", "text": "claude reply"}]})
    settings = AssistantConnectionSettings(
        provider="claude", host="https://api.anthropic.com", model="claude-3-5-sonnet-latest"
    )
    text, error = generate_assistant_response(settings, "sk-test", "hi")
    assert error is None
    assert text == "claude reply"


def test_generate_ollama_local_uses_api_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_urlopen(monkeypatch, {"message": {"content": "local reply"}})
    settings = AssistantConnectionSettings(
        provider="ollama", host="http://localhost:11434", model="llama3.2:1b"
    )
    text, error = generate_assistant_response(settings, "", "hi")
    assert error is None
    assert text == "local reply"
    assert str(captured["url"]).endswith("/api/chat")


def test_generate_rejects_http_cloud_endpoint() -> None:
    settings = AssistantConnectionSettings(
        provider="openai", host="http://api.openai.com", model="gpt-4o-mini"
    )
    text, error = generate_assistant_response(settings, "sk-test", "hi")
    assert text is None
    assert error is not None and "HTTPS" in error


def test_generate_off_provider_reports_off() -> None:
    settings = AssistantConnectionSettings(provider="off", host="", model="")
    text, error = generate_assistant_response(settings, "", "hi")
    assert text is None
    assert error is not None and "Off" in error


def test_generate_maps_401_to_auth_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_401(request: object, timeout: float | None = None, context: object = None):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)  # type: ignore[attr-defined]

    monkeypatch.setattr(assistant_ai, "urlopen", raise_401)
    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = generate_assistant_response(settings, "bad", "hi", max_attempts=1)
    assert text is None
    assert error == "Authentication failed. Check your API key."


def test_generate_blank_required_key_short_circuits_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A cloud provider with no key set must not reach the network and come back
    # with a confusing 401; it should report the actionable "key required"
    # message up front (#123).
    def fail_if_called(*_args: object, **_kwargs: object):
        raise AssertionError("urlopen must not be called for a blank required key")

    monkeypatch.setattr(assistant_ai, "urlopen", fail_if_called)
    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = generate_assistant_response(settings, "", "hi", max_attempts=1)
    assert text is None
    assert error is not None and "API key is required" in error


def test_generate_stream_blank_required_key_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*_args: object, **_kwargs: object):
        raise AssertionError("urlopen must not be called for a blank required key")

    monkeypatch.setattr(assistant_ai, "urlopen", fail_if_called)
    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    deltas: list[str] = []
    text, error = assistant_ai.generate_assistant_response_stream(
        settings, "", "hi", deltas.append, max_attempts=1
    )
    assert text is None
    assert error is not None and "API key is required" in error
    assert deltas == []


def test_generate_retries_then_reports_warming_up(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def raise_503(request: object, timeout: float | None = None, context: object = None):
        calls["n"] += 1
        raise HTTPError(request.full_url, 503, "Service Unavailable", {}, None)  # type: ignore[attr-defined]

    monkeypatch.setattr(assistant_ai, "urlopen", raise_503)
    monkeypatch.setattr(assistant_ai.time, "sleep", lambda _seconds: None)
    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = generate_assistant_response(settings, "k", "hi", max_attempts=3)
    assert text is None
    assert error is not None and "warming up" in error
    assert calls["n"] == 3


def test_generate_unreachable_reports_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_urlerror(request: object, timeout: float | None = None, context: object = None):
        raise URLError("name or service not known")

    monkeypatch.setattr(assistant_ai, "urlopen", raise_urlerror)
    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )
    text, error = generate_assistant_response(settings, "k", "hi", max_attempts=1)
    assert text is None
    assert error is not None


# --- ProviderChatBackend (AI-13) -------------------------------------------


def test_provider_backend_unavailable_when_off() -> None:
    from quill.core.ai.provider_backend import ProviderChatBackend

    backend = ProviderChatBackend(
        AssistantConnectionSettings(provider="off", host="", model=""), api_key=""
    )
    available, reason = backend.is_available()
    assert available is False
    assert reason is not None


def test_provider_backend_requires_key_for_cloud() -> None:
    from quill.core.ai.provider_backend import ProviderChatBackend

    backend = ProviderChatBackend(
        AssistantConnectionSettings(
            provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
        ),
        api_key="",
    )
    available, reason = backend.is_available()
    assert available is False
    assert reason is not None and "key" in reason.lower()


def test_provider_backend_local_ollama_available_without_key() -> None:
    from quill.core.ai.provider_backend import ProviderChatBackend

    backend = ProviderChatBackend(
        AssistantConnectionSettings(
            provider="ollama", host="http://localhost:11434", model="llama3"
        ),
        api_key="",
    )
    assert backend.is_available()[0] is True


def test_provider_backend_respond_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import provider_backend

    monkeypatch.setattr(
        provider_backend, "generate_assistant_response", lambda *a, **k: (None, "boom")
    )
    backend = provider_backend.ProviderChatBackend(
        AssistantConnectionSettings(
            provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
        ),
        api_key="k",
    )
    with pytest.raises(RuntimeError, match="boom"):
        backend.respond("hi")


def test_provider_backend_respond_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import provider_backend

    monkeypatch.setattr(
        provider_backend, "generate_assistant_response", lambda *a, **k: ("done", None)
    )
    backend = provider_backend.ProviderChatBackend(
        AssistantConnectionSettings(
            provider="ollama", host="http://localhost:11434", model="llama3"
        ),
        api_key="",
    )
    assert backend.respond("hi") == "done"


# --- routing in make_default_backend (AI-13) -------------------------------


def test_make_default_backend_uses_configured_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from quill.core.ai import provider_backend
    from quill.core.ai.assistant import make_default_backend
    from quill.core.ai.provider_backend import ProviderChatBackend

    conn = tmp_path / "assistant-connection.json"
    conn.write_text(
        json.dumps({
            "provider": "openai",
            "host": "https://api.openai.com",
            "model": "gpt-4o-mini",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(assistant_ai, "assistant_connection_path", lambda: conn)
    monkeypatch.setattr(provider_backend, "load_assistant_api_key", lambda: "sk-test")
    backend = make_default_backend()
    assert isinstance(backend, ProviderChatBackend)


def test_make_default_backend_falls_back_without_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from quill.core.ai.assistant import make_default_backend
    from quill.core.ai.llama_cpp_backend import LlamaCppBackend

    missing = tmp_path / "nope.json"
    monkeypatch.setattr(assistant_ai, "assistant_connection_path", lambda: missing)
    backend = make_default_backend()
    assert isinstance(backend, LlamaCppBackend)
