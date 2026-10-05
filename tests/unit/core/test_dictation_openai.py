"""OpenAI dictation, own key only -- with fakes; nothing here reaches the network.

The live check against OpenAI (both paths, real key, recorded speech) was run
by hand on 2026-10-05 from the scratchpad; the design note records the result.
"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from quill.core.windows_dictation import openai_models, openai_transcribe
from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.openai_models import (
    cloud_problem,
    is_live_model,
    model_problem,
    newest,
    transcription_models,
)
from quill.core.windows_dictation.openai_transcribe import (
    LiveTranscription,
    ModelGoneError,
    OpenAIDictationError,
    keywords_for,
)

_KEY = "sk-test-not-a-real-key-0123456789abcdef"

#: What /v1/models answered on 2026-10-05, the speech part of it.
_LISTED = [
    {"id": "gpt-4o-mini-transcribe", "created": 1742068596},
    {"id": "gpt-4o-mini-transcribe-2025-12-15", "created": 1765610407},
    {"id": "gpt-4o-transcribe", "created": 1742068463},
    {"id": "gpt-4o-transcribe-diarize", "created": 1750798887},
    {"id": "gpt-live-transcribe", "created": 1785168034},
    {"id": "gpt-realtime-2.1", "created": 1782254687},
    {"id": "gpt-realtime-whisper", "created": 1778012060},
    {"id": "gpt-transcribe", "created": 1785168027},
    {"id": "gpt-6-luna", "created": 1790000000},
    {"id": "tts-1", "created": 1700000000},
    {"id": "whisper-1", "created": 1677532384},
]


def test_only_current_transcription_models_are_offered_newest_first() -> None:
    assert transcription_models(_LISTED) == ["gpt-live-transcribe", "gpt-transcribe"]
    assert newest(transcription_models(_LISTED)) == "gpt-live-transcribe"


def test_a_model_openai_adds_appears_with_no_change_here() -> None:
    later = [*_LISTED, {"id": "gpt-transcribe-2", "created": 1800000000}]
    assert transcription_models(later)[0] == "gpt-transcribe-2"


def test_a_chosen_model_that_went_away_is_said_never_swapped() -> None:
    assert model_problem("gpt-transcribe", ["gpt-transcribe"]) == ""
    problem = model_problem("gpt-4o-transcribe", ["gpt-transcribe"])
    assert "gpt-4o-transcribe" in problem and "Choose another" in problem
    assert model_problem("", ["gpt-transcribe"]) == ""


def test_live_models_take_the_realtime_path() -> None:
    assert is_live_model("gpt-live-transcribe")
    assert not is_live_model("gpt-transcribe")


def test_no_key_safe_mode_and_no_consent_each_refuse(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(openai_models, "load_key", lambda: "")
    assert "own OpenAI key" in cloud_problem()
    monkeypatch.setattr(openai_models, "load_key", lambda: _KEY)
    assert cloud_problem() == ""
    assert "not switched on" in cloud_problem(consent=False)
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert "Safe Mode" in cloud_problem(consent=True)


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


def test_the_model_list_is_read_with_the_key_in_a_header_only(monkeypatch) -> None:
    import urllib.request

    seen: list[Any] = []

    def fake(request: Any, **_kwargs: Any) -> _Response:
        seen.append(request)
        return _Response(json.dumps({"data": _LISTED}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    models, error = openai_models.list_transcription_models(_KEY)
    assert (models, error) == (["gpt-live-transcribe", "gpt-transcribe"], "")
    assert seen[0].full_url == "https://api.openai.com/v1/models"
    assert seen[0].get_header("Authorization") == f"Bearer {_KEY}"


def test_a_refused_key_is_a_sentence_without_the_key(monkeypatch) -> None:
    import urllib.request
    from urllib.error import HTTPError

    def refuse(request: Any, **_kwargs: Any) -> Any:
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    models, error = openai_models.list_transcription_models(_KEY)
    assert models == [] and "did not accept" in error and _KEY not in error


def test_a_phrase_streams_its_words_and_sends_your_words_as_keywords(monkeypatch) -> None:
    pytest.importorskip("numpy")
    import urllib.request

    sent: list[Any] = []
    stream = b"".join(
        f"data: {json.dumps(event)}\n\n".encode()
        for event in (
            {"type": "transcript.text.delta", "delta": "Call Dr."},
            {"type": "transcript.text.delta", "delta": " Okonkwo."},
            {"type": "transcript.text.done", "text": "Call Dr. Okonkwo."},
        )
    )

    def fake(request: Any, **_kwargs: Any) -> _Response:
        sent.append(request)
        return _Response(stream)

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    deltas: list[str] = []
    text = openai_transcribe.transcribe_phrase(
        _KEY, "gpt-transcribe", [0.0] * 1600, keywords=["Okonkwo"], on_delta=deltas.append
    )
    assert text == "Call Dr. Okonkwo."
    assert deltas == ["Call Dr.", "Call Dr. Okonkwo."]
    body = sent[0].data
    assert b'name="keywords[]"' in body and b"Okonkwo" in body and b"RIFF" in body
    assert sent[0].full_url.endswith("/v1/audio/transcriptions")


def test_a_model_that_is_gone_is_its_own_error(monkeypatch) -> None:
    pytest.importorskip("numpy")
    import urllib.request
    from urllib.error import HTTPError

    def gone(request: Any, **_kwargs: Any) -> Any:
        raise HTTPError(
            request.full_url,
            404,
            "Not Found",
            {},
            io.BytesIO(b'{"error":{"code":"model_not_found"}}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", gone)
    with pytest.raises(ModelGoneError) as caught:
        openai_transcribe.transcribe_phrase(_KEY, "gpt-old", [0.0] * 160)
    assert _KEY not in str(caught.value)


def test_keywords_are_cleaned_and_capped() -> None:
    assert keywords_for(["<QUILL>", "QUILL", "  NVDA  ", ""]) == ["QUILL", "NVDA"]
    assert len(keywords_for([f"w{i}" for i in range(500)])) == 100


class _Socket:
    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.sent: list[dict[str, Any]] = []
        self.replies = replies
        self.closed = False

    def send(self, message: str) -> None:
        event = json.loads(message)
        self.sent.append(event)
        if event["type"] == "input_audio_buffer.commit":
            self._pending = list(self.replies)

    _pending: list[dict[str, Any]] = []

    def recv(self) -> str:
        import time

        while not self._pending:
            if self.closed:
                raise OSError("closed")
            time.sleep(0.005)
        return json.dumps(self._pending.pop(0))

    def close(self) -> None:
        self.closed = True


def test_live_transcription_configures_appends_and_commits() -> None:
    pytest.importorskip("numpy")
    socket = _Socket([
        {"type": "conversation.item.input_audio_transcription.delta", "delta": "Hello"},
        {"type": "conversation.item.input_audio_transcription.completed", "transcript": "Hello."},
    ])
    connected: list[tuple[str, str]] = []

    def connect(url: str, key: str) -> _Socket:
        connected.append((url, key))
        return socket

    deltas: list[str] = []
    live = LiveTranscription(
        _KEY, "gpt-live-transcribe", keywords=["QUILL"], on_delta=deltas.append, connect=connect
    )
    live.open()
    session = socket.sent[0]["session"]
    assert session["type"] == "transcription"
    assert session["audio"]["input"]["transcription"] == {
        "model": "gpt-live-transcribe",
        "language": "en",
        "keywords": ["QUILL"],
    }
    assert session["audio"]["input"]["turn_detection"] is None
    assert connected[0] == ("wss://api.openai.com/v1/realtime?intent=transcription", _KEY)
    live.append([0.0] * 1600)
    assert socket.sent[1]["type"] == "input_audio_buffer.append"
    assert live.commit(timeout=2) == "Hello."
    assert deltas == ["Hello"]
    live.close()


def test_a_connection_that_fails_says_so_without_the_key() -> None:
    def refuse(_url: str, _key: str) -> Any:
        raise OSError(f"cannot connect with {_KEY}")

    live = LiveTranscription(_KEY, "gpt-live-transcribe", connect=refuse)
    with pytest.raises(OpenAIDictationError) as caught:
        live.open()
    assert _KEY not in str(caught.value) and "could not be reached" in str(caught.value)


# -- the recogniser ------------------------------------------------------------ #


def _recogniser(**kwargs: Any) -> Any:
    from quill.core.windows_dictation.openai_recognizer import OpenAIDictationRecognizer

    class Listener:
        problems: list[tuple[str, bool]] = []

        def on_engine_problem(self, message: str, fatal: bool) -> None:
            self.problems.append((message, fatal))

    listener = Listener()
    defaults = {"model": "gpt-transcribe", "consent": True}
    defaults.update(kwargs)
    return (
        OpenAIDictationRecognizer(listener, post=lambda f, *a: f(*a), **defaults),
        listener,
    )


def test_it_refuses_to_start_without_consent_a_key_or_a_model(monkeypatch) -> None:
    from quill.core.windows_dictation import openai_recognizer

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(openai_models, "load_key", lambda: _KEY)
    monkeypatch.setattr(openai_recognizer, "load_key", lambda: _KEY)
    engine, _ = _recogniser(consent=False)
    with pytest.raises(DictationStartError, match="not switched on"):
        engine._prepare_engine()
    engine, _ = _recogniser(model="")
    with pytest.raises(DictationStartError, match="Choose an OpenAI model"):
        engine._prepare_engine()
    monkeypatch.setattr(openai_models, "load_key", lambda: "")
    engine, _ = _recogniser()
    with pytest.raises(DictationStartError, match="own OpenAI key"):
        engine._prepare_engine()
    monkeypatch.setattr(openai_models, "load_key", lambda: _KEY)
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    engine, _ = _recogniser()
    with pytest.raises(DictationStartError, match="Safe Mode"):
        engine._prepare_engine()


def test_a_gone_model_stops_dictation_and_a_network_hiccup_does_not(monkeypatch) -> None:
    from quill.core.windows_dictation import openai_recognizer

    engine, listener = _recogniser()
    listener.problems.clear()
    engine._running.set()

    def flaky(*_args: Any, **_kwargs: Any) -> str:
        raise OpenAIDictationError("OpenAI could not be reached. Check the internet connection.")

    monkeypatch.setattr(openai_recognizer, "transcribe_phrase", flaky)
    assert engine._transcribe_healing([0.0]) == ""
    assert listener.problems[-1][1] is False and engine._running.is_set()

    def gone(*_args: Any, **_kwargs: Any) -> str:
        raise ModelGoneError("The OpenAI model gpt-transcribe is no longer available to your key.")

    monkeypatch.setattr(openai_recognizer, "transcribe_phrase", gone)
    assert engine._transcribe_healing([0.0]) == ""
    assert listener.problems[-1][1] is True and not engine._running.is_set()


def test_the_key_is_scrubbed_from_any_log_line() -> None:
    from quill.stability.redaction import redact_source_tokens, redact_text_for_bundle

    assert _KEY not in redact_source_tokens(f"OpenAI said no to {_KEY}")
    assert _KEY not in redact_text_for_bundle(f"Authorization: Bearer {_KEY}")
