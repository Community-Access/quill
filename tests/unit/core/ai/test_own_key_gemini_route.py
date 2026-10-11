"""Own-key AI help on Google Gemini, chosen explicitly, against a real HTTP boundary.

qc.md X-07, second half. The own-key route had one provider (OpenAI); it now
has two, and the person picks one in Use My Own API Key. These tests run the
shipped request code against one ``ThreadingHTTPServer`` on 127.0.0.1 that
answers the way both providers do -- OpenAI's ``/v1/chat/completions`` with a
Bearer key, Gemini's ``:streamGenerateContent?alt=sse`` with ``x-goog-api-key``
-- and assert what actually arrived at the server: which provider was asked,
with which key, on which path, with what body.

What PR #1615 proposed and these tests forbid: inferring the provider from a
model's name, and falling back to whichever key happens to be stored. Every
request here goes only where ``ai_own_key_provider`` says.

Synthetic keys only; nothing leaves the machine.
"""

from __future__ import annotations

import itertools
import json
import logging
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import assistant_ai
from quill.core.ai import own_key, own_key_gemini
from quill.core.ai.own_key_models import list_models, ordered

OPENAI_KEY = "sk-synthetic-openai-0001"
GEMINI_KEY = "AIzaSynthetic-gemini-0002"
WRONG_KEY = "AIzaSynthetic-WRONG-9999"


class _Recorder:
    """What the fake providers saw, shared with the handler."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.gemini_status: int = 200
        self.gemini_error: dict[str, Any] | None = None
        self.chunks: list[str] = ["Short ", "and ", "clear."]
        self.release = threading.Event()  # hold the stream open until set
        self.hold = False
        self.closed_early = threading.Event()
        self.models: list[str] = []


class _Providers(BaseHTTPRequestHandler):
    recorder: _Recorder

    def log_message(self, *_args: object) -> None:  # quiet
        pass

    def _send_json(self, code: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self, body: bytes = b"") -> None:
        self.recorder.requests.append({
            "path": self.path,
            "goog": self.headers.get("x-goog-api-key", ""),
            "bearer": self.headers.get("Authorization", ""),
            "body": json.loads(body) if body else None,
        })

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self._record()
        if self.path.startswith("/v1beta/models") or self.path.startswith("/v1/models"):
            if self.headers.get("x-goog-api-key") != GEMINI_KEY:
                self._send_json(400, {"error": {"message": "API key not valid."}})
                return
            self._send_json(200, {"models": [{"name": name} for name in self.recorder.models]})
            return
        self._send_json(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or 0)
        self._record(self.rfile.read(length))
        if self.path == "/v1/chat/completions":
            if self.headers.get("Authorization") != f"Bearer {OPENAI_KEY}":
                self._send_json(401, {"error": {"message": "Incorrect API key provided."}})
                return
            self._send_json(200, {"choices": [{"message": {"content": "From OpenAI."}}]})
            return
        if ":streamGenerateContent" in self.path:
            self._gemini_stream()
            return
        self._send_json(404, {"error": {"message": "not found"}})

    def _gemini_stream(self) -> None:
        rec = self.recorder
        if self.headers.get("x-goog-api-key") != GEMINI_KEY:
            self._send_json(
                400,
                {
                    "error": {
                        "code": 400,
                        "message": "API key not valid. Please pass a valid API key.",
                        "status": "INVALID_ARGUMENT",
                        "details": [{"reason": "API_KEY_INVALID"}],
                    }
                },
            )
            return
        if rec.gemini_status != 200:
            self._send_json(rec.gemini_status, rec.gemini_error or {"error": {"message": "x"}})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for index, text in enumerate(rec.chunks):
                event = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
                self.wfile.write(f"data: {json.dumps(event)}\r\n\r\n".encode())
                self.wfile.flush()
                if rec.hold and index == 0:
                    rec.release.wait(5)
                    time.sleep(0.2)  # let the client close first
        except (ConnectionError, OSError):
            rec.closed_early.set()


@pytest.fixture
def providers(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, _Recorder]]:
    recorder = _Recorder()
    handler = type("Handler", (_Providers,), {"recorder": recorder})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    host = f"http://127.0.0.1:{server.server_address[1]}"
    # Both providers live at the loopback server. The OpenAI route's cloud
    # HTTPS check is bypassed for loopback; the Gemini route allows loopback
    # http by design (and refuses any other http -- tested below).
    monkeypatch.setattr(assistant_ai, "default_host_for_provider", lambda _p: host)
    monkeypatch.setattr(assistant_ai, "_validate_endpoint_security", lambda *_a: None)
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: False)
    monkeypatch.setattr(own_key_gemini, "GEMINI_HOST", host)
    try:
        yield host, recorder
    finally:
        recorder.release.set()
        server.shutdown()
        server.server_close()


def _keys(monkeypatch: pytest.MonkeyPatch, **stored: str) -> None:
    """Store synthetic keys per provider, as the credential store would."""
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: stored.get(p, ""))
    monkeypatch.setattr(own_key, "has_own_key", lambda p="openai": bool(stored.get(p)))


def _ask(settings: Any, **kwargs: Any) -> str:
    return own_key.ask_with_own_key(
        "summarize",
        "A long passage.",
        provider=own_key.chosen_provider(settings),
        model=own_key.chosen_model(settings),
        **kwargs,
    )


# -- provider selection: the choice, and only the choice ------------------------------- #


def test_choosing_gemini_sends_only_to_gemini_with_only_the_gemini_key(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY, gemini=GEMINI_KEY)
    settings = SimpleNamespace(ai_own_key_provider="gemini", ai_own_key_model="")

    assert _ask(settings) == "Short and clear."

    assert len(rec.requests) == 1
    sent = rec.requests[0]
    assert sent["path"] == "/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse"
    assert sent["goog"] == GEMINI_KEY
    assert sent["bearer"] == ""  # the OpenAI key never travels with it
    assert OPENAI_KEY not in json.dumps(sent)


def test_choosing_openai_sends_only_to_openai_with_only_the_openai_key(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY, gemini=GEMINI_KEY)
    settings = SimpleNamespace(ai_own_key_provider="openai", ai_own_key_model="gpt-test")

    assert _ask(settings) == "From OpenAI."

    assert [r["path"] for r in rec.requests] == ["/v1/chat/completions"]
    assert rec.requests[0]["bearer"] == f"Bearer {OPENAI_KEY}"
    assert rec.requests[0]["goog"] == ""


def test_an_empty_choice_is_openai_so_earlier_consent_is_kept(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY, gemini=GEMINI_KEY)
    settings = SimpleNamespace(ai_own_key_provider="", ai_own_key_model="")
    assert own_key.chosen_provider(settings) == "openai"
    assert _ask(settings) == "From OpenAI."
    assert rec.requests[0]["path"] == "/v1/chat/completions"


def test_a_gemini_looking_model_name_never_changes_the_provider(providers, monkeypatch):
    """PR #1615 inferred Gemini from "gemini" in a model name. Not taken."""
    _host, rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY, gemini=GEMINI_KEY)
    settings = SimpleNamespace(ai_own_key_provider="openai", ai_own_key_model="gemini-2.5-flash")
    _ask(settings)
    assert [r["path"] for r in rec.requests] == ["/v1/chat/completions"]


def test_no_fallback_gemini_chosen_with_only_an_openai_key_sends_nothing(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY)
    settings = SimpleNamespace(ai_own_key_provider="gemini", ai_own_key_model="")

    assert own_key.own_key_active(settings) is False  # the route is not even live
    with pytest.raises(own_key.OwnKeyError) as caught:
        _ask(settings)

    assert rec.requests == []
    assert "No Google Gemini key is saved" in str(caught.value)
    assert OPENAI_KEY not in str(caught.value)


def test_an_unknown_saved_provider_is_no_provider_and_sends_nothing(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY, gemini=GEMINI_KEY)
    settings = SimpleNamespace(ai_own_key_provider="claude", ai_own_key_model="")
    assert own_key.chosen_provider(settings) == ""
    assert own_key.own_key_active(settings) is False
    with pytest.raises(own_key.OwnKeyError, match="No provider is chosen"):
        own_key.ask_with_own_key("summarize", "x", provider="claude")
    assert rec.requests == []


# -- the streaming route ------------------------------------------------------------- #


def test_the_gemini_request_carries_the_shared_instructions_and_streams(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    rec.chunks = ["One, ", "two, ", "three."]
    pieces: list[str] = []

    text = own_key_gemini.stream_answer(
        GEMINI_KEY,
        "models/gemini-2.5-pro",  # the prefix Gemini's own list gives is harmless
        own_key.INSTRUCTIONS["summarize"],
        "A long passage.",
        on_delta=pieces.append,
    )

    assert text == "One, two, three."
    assert pieces == ["One, ", "two, ", "three."]
    sent = rec.requests[0]
    assert sent["path"] == "/v1beta/models/gemini-2.5-pro:streamGenerateContent?alt=sse"
    assert sent["body"]["systemInstruction"] == {
        "parts": [{"text": own_key.INSTRUCTIONS["summarize"]}]
    }
    assert sent["body"]["contents"] == [{"role": "user", "parts": [{"text": "A long passage."}]}]
    assert GEMINI_KEY not in sent["path"]  # the key is a header, never in the URL


def test_a_conversation_turn_goes_to_gemini_with_its_history(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    reply = own_key.ask_with_own_key(
        "chat", "And now?", None, history=history, provider="gemini", model="gemini-2.5-flash"
    )
    assert reply == "Short and clear."
    user_text = rec.requests[0]["body"]["contents"][0]["parts"][0]["text"]
    assert "Hello" in user_text and "And now?" in user_text


# -- missing and invalid keys: safe, actionable, never the key --------------------------- #


def test_a_missing_gemini_key_is_refused_before_anything_is_sent(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch)
    with pytest.raises(own_key.OwnKeyError) as caught:
        own_key.ask_with_own_key("summarize", "x", provider="gemini")
    assert rec.requests == []
    assert "Use My Own API Key" in str(caught.value)


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_by_status_is_a_rejected_key(providers, monkeypatch, status):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    rec.gemini_status = status
    rec.gemini_error = {"error": {"message": "Permission denied.", "status": "PERMISSION_DENIED"}}
    with pytest.raises(own_key.OwnKeyRejected) as caught:
        own_key.ask_with_own_key("summarize", "x", provider="gemini")
    assert "did not accept the saved key" in str(caught.value)
    assert caught.value.code == "QUILL-AI-OWN-KEY-REJECTED"


def test_geminis_400_api_key_invalid_is_recognised_and_never_repeats_the_key(
    providers, monkeypatch, caplog
):
    """Gemini answers a wrong key with 400, not 401 -- read from the body."""
    _host, rec = providers
    _keys(monkeypatch, gemini=WRONG_KEY)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(own_key.OwnKeyRejected) as caught:
        own_key.ask_with_own_key("summarize", "x", provider="gemini")
    sentence = f"{caught.value} {caught.value.user_hint}"
    assert WRONG_KEY not in sentence and GEMINI_KEY not in sentence
    assert WRONG_KEY not in caplog.text and GEMINI_KEY not in caplog.text
    assert rec.requests[0]["goog"] == WRONG_KEY  # it was the key that was sent


def test_a_reply_that_quotes_the_key_is_scrubbed(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    rec.gemini_status = 400
    rec.gemini_error = {"error": {"message": f"Bad request for {GEMINI_KEY} here."}}
    with pytest.raises(own_key.OwnKeyError) as caught:
        own_key.ask_with_own_key("summarize", "x", provider="gemini")
    assert GEMINI_KEY not in str(caught.value)
    assert "[your key]" in str(caught.value)


@pytest.mark.parametrize(
    ("status", "words"),
    [
        (404, "does not offer the model gemini-2.5-flash"),
        (429, "rate limit or quota"),
        (503, "busy or not answering"),
    ],
)
def test_each_failure_is_one_plain_sentence(providers, monkeypatch, status, words):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    rec.gemini_status = status
    with pytest.raises(own_key.OwnKeyError) as caught:
        own_key.ask_with_own_key("summarize", "x", provider="gemini")
    assert words in str(caught.value)
    assert "http://" not in str(caught.value)  # no address read out at a listener
    if status == 503:
        assert len(rec.requests) == 2  # one more try, then a sentence


def test_an_unreachable_gemini_is_a_sentence_not_a_traceback(monkeypatch):
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: False)
    with pytest.raises(own_key.OwnKeyError, match="could not be reached"):
        own_key_gemini.stream_answer(
            GEMINI_KEY, "gemini-2.5-flash", "s", "u", host="http://127.0.0.1:9", timeout=2
        )


def test_plain_http_to_anywhere_but_loopback_is_refused_before_sending(monkeypatch):
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: False)
    with pytest.raises(own_key.OwnKeyError, match="only be reached over HTTPS"):
        own_key_gemini.stream_answer(
            GEMINI_KEY, "gemini-2.5-flash", "s", "u", host="http://generativelanguage.example"
        )


def test_safe_mode_sends_nothing(monkeypatch):
    monkeypatch.setattr(assistant_ai, "_safe_mode_active", lambda: True)
    with pytest.raises(own_key.OwnKeyError, match="Safe Mode"):
        own_key_gemini.stream_answer(GEMINI_KEY, "gemini-2.5-flash", "s", "u")


# -- cancellation --------------------------------------------------------------------- #


def test_stop_before_sending_sends_nothing(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    stop = threading.Event()
    stop.set()
    with pytest.raises(own_key.OwnKeyCancelled):
        own_key.ask_with_own_key("summarize", "x", provider="gemini", cancel=stop)
    assert rec.requests == []


def test_stop_part_way_closes_the_stream_and_returns_nothing(providers, monkeypatch):
    _host, rec = providers
    _keys(monkeypatch, gemini=GEMINI_KEY)
    rec.hold = True
    rec.chunks = ["First piece. ", "Never read. ", "Never read either."]
    stop = threading.Event()
    seen: list[str] = []

    def first_piece_then_stop(piece: str) -> None:
        seen.append(piece)
        stop.set()
        rec.release.set()

    with pytest.raises(own_key.OwnKeyCancelled):
        own_key_gemini.stream_answer(
            GEMINI_KEY, "gemini-2.5-flash", "s", "u", cancel=stop, on_delta=first_piece_then_stop
        )
    assert seen == ["First piece. "]


def test_stop_after_an_openai_answer_arrives_drops_it(providers, monkeypatch):
    """OpenAI is not streamed (it refuses streaming to unverified organisations
    for some models), so Stop drops its answer on arrival instead."""
    _host, _rec = providers
    _keys(monkeypatch, openai=OPENAI_KEY)
    stop = threading.Event()
    real = assistant_ai.generate_assistant_response

    def answer_then_stop(*args: Any, **kwargs: Any) -> Any:
        result = real(*args, **kwargs)
        stop.set()
        return result

    monkeypatch.setattr(assistant_ai, "generate_assistant_response", answer_then_stop)
    with pytest.raises(own_key.OwnKeyCancelled):
        own_key.ask_with_own_key("summarize", "x", provider="openai", cancel=stop)


# -- model ordering --------------------------------------------------------------------- #

_GEMINI_LISTING = [
    "models/gemini-2.5-pro",
    "models/text-embedding-004",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash-preview-05-20",
    "models/imagen-3.0-generate-002",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.0-flash-exp",
    "models/aqa",
    "models/gemini-2.5-flash-preview-tts",
    "models/gemma-3-27b-it",
    "models/gemini-2.5-flash",  # a repeat
]

_GEMINI_ORDER = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemma-3-27b-it",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.0-flash-exp",
]


def test_gemini_models_are_listed_in_a_fixed_order_through_the_real_list(providers, monkeypatch):
    _host, rec = providers
    rec.models = list(_GEMINI_LISTING)
    models, error = list_models(GEMINI_KEY, "gemini")
    assert error == ""
    assert models == _GEMINI_ORDER


def test_gemini_ordering_does_not_depend_on_the_order_google_sends(providers) -> None:
    for shuffled in itertools.islice(itertools.permutations(_GEMINI_LISTING[:7]), 200):
        assert ordered(shuffled, "gemini") == ordered(_GEMINI_LISTING[:7], "gemini")


def test_a_wrong_key_lists_nothing_and_never_repeats_the_key(providers, monkeypatch):
    _host, rec = providers
    rec.models = list(_GEMINI_LISTING)
    models, error = list_models(WRONG_KEY, "gemini")
    assert models == []
    assert error
    assert WRONG_KEY not in error


def test_openai_ordering_is_unchanged_by_the_second_provider() -> None:
    assert ordered(["gpt-4o", "gpt-6", "gpt-6-luna", "text-embedding-3-small"]) == [
        "gpt-6-luna",
        "gpt-6",
        "gpt-4o",
    ]


# -- the words around it ------------------------------------------------------------------ #


def test_the_cost_sentences_name_the_chosen_providers_account() -> None:
    gemini = own_key.size_warning(
        "word " * 50, "gemini-2.5-flash", free_limit_tokens=1500, provider="gemini"
    )
    assert "on your Google Gemini account with gemini-2.5-flash" in gemini
    assert "OpenAI" not in gemini
    assert "Google Gemini" in own_key.conversation_note("gemini")
    openai = own_key.size_warning("word " * 50, "gpt-6", free_limit_tokens=1500)
    assert "on your OpenAI account" in openai


def test_settings_load_the_choice_and_quill_and_lite_both_have_the_field() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    loaded = own_key.load_settings_fields({"ai_own_key_provider": "gemini"})
    assert loaded["ai_own_key_provider"] == "gemini"
    assert QuillSettings().ai_own_key_provider == "openai"
    assert LiteSettings().ai_own_key_provider == "openai"
