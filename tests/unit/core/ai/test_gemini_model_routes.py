"""Gemini model names from Gemini's own list reach a real endpoint (qc.md X-07).

Gemini's ``GET /v1beta/models`` answers ``"name": "models/gemini-2.5-flash"``.
QUILL put that name straight into ``/v1beta/models/{model}:generateContent`` and
asked for ``/v1beta/models/models/gemini-2.5-flash``, which Gemini answers 404 --
so a model chosen from QUILL's own list could not be used. Reported in PR #1615;
the fix reviewed into ``quill/core/ai/endpoints.gemini_model_id``.

These run the shipped client against a real HTTP server on 127.0.0.1 that
answers the way Gemini does, so the request path the client actually builds is
what is asserted -- not a string the test assembles itself. Synthetic keys
only; nothing leaves the machine. The endpoint-security check (which refuses
plain http for a cloud provider) is bypassed for the loopback server and is
tested on its own elsewhere.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from quill.core import assistant_ai
from quill.core.ai.endpoints import chat_endpoint, gemini_model_id, stream_chat_endpoint

GOOD_KEY = "synthetic-test-key-123"


class _GeminiLike(BaseHTTPRequestHandler):
    paths: list[str] = []

    def log_message(self, *_args: object) -> None:  # keep test output quiet
        pass

    def _key_ok(self) -> bool:
        return self.headers.get("x-goog-api-key") == GOOD_KEY

    def _send(self, code: int, payload: object, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        _GeminiLike.paths.append(self.path)
        if not self._key_ok():
            self._send(
                400, {"error": {"message": "API key not valid. Please pass a valid API key."}}
            )
            return
        if self.path.startswith("/v1beta/models"):
            self._send(
                200,
                {
                    "models": [
                        {"name": "models/gemini-2.5-flash"},
                        {"name": "models/gemini-2.5-pro"},
                    ]
                },
            )
            return
        self._send(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802
        _GeminiLike.paths.append(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        self.rfile.read(length)
        if not self._key_ok():
            self._send(
                400, {"error": {"message": "API key not valid. Please pass a valid API key."}}
            )
            return
        if "/models/models/" in self.path:
            self._send(404, {"error": {"message": "models/models/... is not found"}})
            return
        if self.path.startswith("/v1beta/models/gemini-2.5-flash:streamGenerateContent"):
            chunk = {"candidates": [{"content": {"parts": [{"text": "streamed hello"}]}}]}
            self._send(200, f"data: {json.dumps(chunk)}\n\n".encode(), "text/event-stream")
            return
        if self.path.startswith("/v1beta/models/gemini-2.5-flash:generateContent"):
            self._send(200, {"candidates": [{"content": {"parts": [{"text": "hello back"}]}}]})
            return
        self._send(404, {"error": {"message": "not found"}})


@pytest.fixture
def gemini_host(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    _GeminiLike.paths = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GeminiLike)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(assistant_ai, "_validate_endpoint_security", lambda *_a: None)
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: False)
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _settings(host: str, model: str) -> assistant_ai.AssistantConnectionSettings:
    return assistant_ai.AssistantConnectionSettings(provider="gemini", host=host, model=model)


# -- pure ------------------------------------------------------------------------------ #


def test_the_prefix_is_stripped_once_and_only_the_prefix() -> None:
    assert gemini_model_id("models/gemini-2.5-flash") == "gemini-2.5-flash"
    assert gemini_model_id("gemini-2.5-flash") == "gemini-2.5-flash"
    assert gemini_model_id("  models/gemini-2.5-pro ") == "gemini-2.5-pro"
    assert gemini_model_id("tunedModels/my-model") == "tunedModels/my-model"


def test_no_builder_can_produce_a_doubled_models_segment() -> None:
    for model in ("models/gemini-2.5-flash", "gemini-2.5-flash"):
        for url in (
            chat_endpoint("gemini", "https://g.example/", model),
            stream_chat_endpoint("gemini", "https://g.example", model),
        ):
            assert "/models/models/" not in url
            assert "/v1beta/models/gemini-2.5-flash:" in url


def test_other_providers_are_untouched() -> None:
    assert chat_endpoint("openai", "https://api.openai.com", "models/x").endswith(
        "/v1/chat/completions"
    )


# -- the real boundary ------------------------------------------------------------------ #


def test_the_model_list_gives_names_a_request_can_use(gemini_host: str) -> None:
    names, error = assistant_ai.list_assistant_models(
        _settings(gemini_host, "gemini-2.5-flash"), GOOD_KEY, max_attempts=1
    )
    assert error is None
    assert names[:2] == ["gemini-2.5-flash", "gemini-2.5-pro"]


def test_a_model_name_with_the_prefix_still_generates(gemini_host: str) -> None:
    text, error = assistant_ai.generate_assistant_response(
        _settings(gemini_host, "models/gemini-2.5-flash"), GOOD_KEY, "hello", max_attempts=1
    )
    assert error is None
    assert text == "hello back"
    posted = [p for p in _GeminiLike.paths if ":generateContent" in p]
    assert posted == ["/v1beta/models/gemini-2.5-flash:generateContent"]


def test_a_model_name_with_the_prefix_still_streams(gemini_host: str) -> None:
    deltas: list[str] = []
    text, error = assistant_ai.generate_assistant_response_stream(
        _settings(gemini_host, "models/gemini-2.5-flash"),
        GOOD_KEY,
        "hello",
        deltas.append,
        max_attempts=1,
    )
    assert error is None
    assert text == "streamed hello"
    assert deltas == ["streamed hello"]
    assert any(
        p.startswith("/v1beta/models/gemini-2.5-flash:streamGenerateContent")
        for p in _GeminiLike.paths
    )


def test_a_wrong_key_is_a_safe_error_that_never_repeats_the_key(gemini_host: str) -> None:
    wrong = "synthetic-WRONG-key-999"
    text, error = assistant_ai.generate_assistant_response(
        _settings(gemini_host, "gemini-2.5-flash"), wrong, "hello", max_attempts=1
    )
    assert text is None
    assert error
    assert wrong not in error
    assert GOOD_KEY not in error


def test_a_missing_key_is_refused_before_anything_is_sent() -> None:
    """Pure: the real Gemini host with a blank key is refused up front. (A
    loopback host is exempt by design, for local OpenAI-compatible servers.)"""
    host = "https://generativelanguage.googleapis.com"
    assert assistant_ai.missing_required_api_key("gemini", host, "") is True
    assert assistant_ai.missing_required_api_key("gemini", host, GOOD_KEY) is False
