"""An own key for Google Gemini: an explicit, consented provider choice (qc.md X-07).

The provider is the saved choice and nothing else: no inference from a model
name, no fallback to whichever key happens to exist. The request path is
exercised against a loopback server that answers the way Gemini does, with a
synthetic key; nothing leaves the machine.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from quill.core import assistant_ai
from quill.core.ai import own_key, own_key_gemini, own_key_models

GOOD_KEY = "synthetic-gemini-key"


class _GeminiLike(BaseHTTPRequestHandler):
    paths: list[str] = []
    bodies: list[dict] = []

    def log_message(self, *_args: object) -> None:
        pass

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        type(self).paths.append(self.path)
        if self.headers.get("x-goog-api-key") != GOOD_KEY:
            self._send(403, {"error": {"message": "API key not valid"}})
            return
        self._send(
            200,
            {
                "models": [
                    {"name": "models/gemini-2.5-pro"},
                    {"name": "models/gemini-2.5-flash"},
                    {"name": "models/gemini-2.5-flash-lite"},
                    {"name": "models/text-embedding-004"},
                    {"name": "models/imagen-4"},
                ]
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        type(self).paths.append(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        type(self).bodies.append(body)
        if self.headers.get("x-goog-api-key") != GOOD_KEY:
            self._send(403, {"error": {"message": "API key not valid"}})
            return
        payload = {"candidates": [{"content": {"parts": [{"text": "A summary from Gemini."}]}}]}
        body = f"data: {json.dumps(payload)}\r\n\r\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def gemini_host(monkeypatch) -> Iterator[str]:
    _GeminiLike.paths = []
    _GeminiLike.bodies = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GeminiLike)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(assistant_ai, "_validate_endpoint_security", lambda *_a: None)
    monkeypatch.setattr(assistant_ai, "default_host_for_provider", lambda p: host)
    monkeypatch.setattr(own_key_gemini, "GEMINI_HOST", host)
    monkeypatch.setattr(
        assistant_ai, "load_provider_api_key", lambda p: GOOD_KEY if p == "gemini" else ""
    )
    try:
        yield host
    finally:
        server.shutdown()
        server.server_close()


# -- the choice -------------------------------------------------------------------------


def test_the_provider_is_the_saved_choice_and_nothing_else() -> None:
    assert own_key.normalize_provider("gemini") == "gemini"
    assert own_key.normalize_provider("OpenAI ") == "openai"
    assert own_key.normalize_provider("anthropic") == "openai"  # not an own-key provider
    assert own_key.provider_for(SimpleNamespace(ai_own_key_provider="gemini")) == "gemini"
    assert own_key.provider_for(SimpleNamespace()) == "openai"
    assert own_key.provider_for(None) == "openai"
    assert own_key.load_settings_fields({"ai_own_key_provider": "GEMINI"}) == {
        "ai_own_key_model": "",
        "ai_own_key_provider": "gemini",
    }


def test_a_key_for_the_other_provider_never_counts(monkeypatch) -> None:
    """A saved Gemini key with OpenAI chosen is a key that is not used -- said, not guessed."""
    monkeypatch.setattr(
        assistant_ai, "load_provider_api_key", lambda p: "k" if p == "gemini" else ""
    )
    # The suite hides the developer's real keys by replacing has_own_key; this
    # test is about has_own_key itself, so it is put back over the fake store.
    monkeypatch.setattr(
        own_key,
        "has_own_key",
        lambda provider="openai": bool(
            assistant_ai.load_provider_api_key(own_key.normalize_provider(provider))
        ),
    )
    assert own_key.has_own_key("gemini") is True
    assert own_key.has_own_key("openai") is False
    assert own_key.own_key_active(SimpleNamespace(ai_own_key_provider="gemini")) is True
    assert own_key.own_key_active(SimpleNamespace(ai_own_key_provider="openai")) is False
    assert own_key.own_key_active(None) is False


def test_asking_openai_with_only_a_gemini_key_says_so_rather_than_switching(monkeypatch) -> None:
    monkeypatch.setattr(
        assistant_ai, "load_provider_api_key", lambda p: "k" if p == "gemini" else ""
    )
    with pytest.raises(own_key.OwnKeyError) as caught:
        own_key.ask_with_own_key("summarize", "text", provider="openai")
    assert "No OpenAI key" in str(caught.value)


def test_names_and_addresses_follow_the_provider() -> None:
    assert own_key.provider_name("gemini") == "Google Gemini"
    assert "aistudio.google.com" in own_key.key_url("gemini")
    assert own_key.usage_url("gemini").startswith("https://aistudio.google.com")
    assert own_key.default_model("gemini").startswith("gemini")
    warning = own_key.size_warning(
        "some words", "gemini-2.5-flash", free_limit_tokens=10, provider="gemini"
    )
    assert "Google Gemini account" in warning and "OpenAI" not in warning


# -- the request, at a real boundary --------------------------------------------------------


def test_a_gemini_request_reaches_generatecontent_with_the_key_and_the_instructions(
    gemini_host: str,
) -> None:
    answer = own_key.ask_with_own_key(
        "summarize", "The passage.", model="gemini-2.5-flash", provider="gemini"
    )

    assert answer == "A summary from Gemini."
    assert any(
        path.startswith("/v1beta/models/gemini-2.5-flash:streamGenerateContent")
        for path in _GeminiLike.paths
    ), _GeminiLike.paths
    assert not any("models/models/" in path for path in _GeminiLike.paths)
    sent = json.dumps(_GeminiLike.bodies[-1])
    assert "The passage." in sent
    assert own_key.INSTRUCTIONS["summarize"][:40] in sent


def test_a_model_from_geminis_own_list_is_usable_without_the_models_prefix(
    gemini_host: str,
) -> None:
    models, error = own_key_models.list_models(GOOD_KEY, "gemini")

    assert error == ""
    assert models[:3] == ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]
    assert "text-embedding-004" not in models and "imagen-4" not in models
    own_key.ask_with_own_key("summarize", "x", model=models[0], provider="gemini")
    assert _GeminiLike.paths[-1].startswith("/v1beta/models/gemini-2.5-flash:streamGenerateContent")


def test_a_bad_key_is_a_sentence_with_the_providers_name(gemini_host: str, monkeypatch) -> None:
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: "wrong-key")
    with pytest.raises(own_key.OwnKeyError) as caught:
        own_key.ask_with_own_key("summarize", "x", model="gemini-2.5-flash", provider="gemini")
    assert "Google Gemini did not accept the saved key" in str(caught.value)
    assert caught.value.code == "QUILL-AI-OWN-KEY-REJECTED"


# -- the model list, by provider ---------------------------------------------------------------


def test_gemini_models_are_ordered_flash_then_pro_and_priced_by_their_tier() -> None:
    names = ["gemini-1.5-pro", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    assert own_key_models.ordered(names, "gemini") == [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
        "gemini-1.5-pro",
    ]
    assert own_key_models.estimate_for("gemini-2.5-flash-lite", "gemini").tier == "smallest"
    assert own_key_models.estimate_for("gemini-2.5-flash", "gemini").tier == "small"
    assert own_key_models.estimate_for("gemini-2.5-pro", "gemini").tier == "premium"
    assert "Google's real prices" in own_key_models.estimate_note("gemini")
    assert "ai.google.dev" in own_key_models.estimate_note("gemini")
    assert "OpenAI's real prices" in own_key_models.estimate_note("openai")
    # OpenAI's ordering is untouched.
    assert own_key_models.ordered(["gpt-4o", "gpt-6-luna", "gpt-6"], "openai")[0] == "gpt-6-luna"


# -- pictures, on a Gemini key -------------------------------------------------------------


def test_a_gemini_key_describes_an_image_through_the_vision_client(monkeypatch, tmp_path) -> None:
    from quill.core.ai import vision

    seen: list[tuple[str, str, str]] = []

    def fake_describe(settings, api_key, image_path, *, prompt, **_kw):
        seen.append((settings.provider, settings.model, prompt))
        return "A red door.", ""

    monkeypatch.setattr(vision, "describe_image", fake_describe)
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: GOOD_KEY)
    picture = tmp_path / "door.png"
    picture.write_bytes(b"png")

    said = own_key.describe_image_with_own_key(picture, "What colour?", provider="gemini")

    assert said == "A red door."
    assert seen == [("gemini", "gemini-2.5-flash", "What colour?")]
