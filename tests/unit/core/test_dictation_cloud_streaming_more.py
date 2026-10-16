"""ElevenLabs Scribe, Gladia and Rev.ai over recorded fakes: no network, no real store."""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import numpy as np
import pytest
from cloud_speech_fakes import FakeSocket, MemoryBackend, http_error, install

from quill.core.windows_dictation.cloud import credentials, streaming_more
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudSpeechError,
    said,
)
from quill.core.windows_dictation.cloud.streaming_more import ElevenLabsScribe, Gladia, RevAI

SECRET = "sk-very-secret-123"


def _samples() -> Any:
    return np.zeros(1600, dtype=np.float32)


def _query(url: str) -> list[tuple[str, str]]:
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)


def _run(session: Any) -> str:
    session.open()
    try:
        session.append(_samples())
        return str(session.commit(timeout=2.0))
    finally:
        session.close()


# -- ElevenLabs Scribe ------------------------------------------------------------- #


def _eleven_react(message: Any) -> list[Any]:
    event = json.loads(message)
    if event.get("commit"):
        return [{"message_type": "committed_transcript", "text": "Hello world."}]
    return [{"message_type": "partial_transcript", "text": "hello"}]


def test_elevenlabs_url_header_and_keyterms(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(_eleven_react)
    terms = ["Quill", "a" * 21, *[f"w{i}" for i in range(60)]]
    deltas: list[str] = []
    session = ElevenLabsScribe().live(
        {"key": SECRET}, language="en-US", terms=terms, on_delta=deltas.append
    )
    assert wire.calls == 0  # nothing is sent before open()
    assert _run(session) == "Hello world."

    url, headers, socket = wire.sockets[0]
    assert url.startswith("wss://api.elevenlabs.io/v1/speech-to-text/realtime?")
    assert SECRET not in url
    assert headers == {"xi-api-key": SECRET}
    query = _query(url)
    assert ("model_id", "scribe_v2_realtime") in query
    assert ("audio_format", "pcm_16000") in query
    assert ("language_code", "en") in query
    assert ("commit_strategy", "manual") in query
    keyterms = [value for name, value in query if name == "keyterms"]
    assert keyterms[0] == "Quill"
    assert "a" * 21 not in keyterms  # too long
    assert len(keyterms) == 50

    sent = socket.text_sent()
    chunk = sent[0]
    assert chunk["message_type"] == "input_audio_chunk"
    assert chunk["sample_rate"] == 16000
    assert len(base64.b64decode(chunk["audio_base_64"])) == 3200
    assert "commit" not in chunk
    commit = sent[1]
    assert commit["commit"] is True and commit["audio_base_64"] == ""
    assert "hello" in deltas
    assert deltas[-1] == "Hello world."
    assert socket.closed


def test_elevenlabs_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(
        lambda _m: [{"message_type": "auth_error", "error": "quota exceeded"}]
    )
    session = ElevenLabsScribe().live({"key": SECRET}, language="en", terms=[])
    with pytest.raises(CloudSpeechError) as caught:
        _run(session)
    assert said(caught.value) == "ElevenLabs reported a problem: quota exceeded."


def test_elevenlabs_test_success_and_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"subscription": {}})
    assert ElevenLabsScribe().test({"key": SECRET}) == "ElevenLabs answered: ready."
    request = wire.requests[0]
    assert request.full_url == "https://api.elevenlabs.io/v1/user"
    assert request.get_method() == "GET"
    assert request.get_header("Xi-api-key") == SECRET

    wire.answer(http_error("https://api.elevenlabs.io/v1/user", 401))
    with pytest.raises(CloudAuthError) as caught:
        ElevenLabsScribe().test({"key": SECRET})
    assert said(caught.value) == "The key was refused. Check Key."
    assert caught.value.field == "Key"
    assert SECRET not in str(caught.value)


def test_elevenlabs_uses_the_voices_key_when_none_is_saved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    store = MemoryBackend(tmp_path).install(monkeypatch)
    monkeypatch.setattr(streaming_more, "_shared_elevenlabs_key", lambda: "shared-voice-key")
    provider = ElevenLabsScribe()
    assert credentials.values_for(provider, {})["key"] == "shared-voice-key"
    assert provider.problem(credentials.values_for(provider, {})) is None

    store.secrets[credentials.secret_target("elevenlabs", "key")] = "own-key"
    assert credentials.values_for(provider, {})["key"] == "own-key"
    assert provider.fallback_secret("other") == ""


def test_elevenlabs_missing_key_names_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    MemoryBackend(tmp_path).install(monkeypatch)
    monkeypatch.setattr(streaming_more, "_shared_elevenlabs_key", lambda: "")
    provider = ElevenLabsScribe()
    problem = provider.problem(credentials.values_for(provider, {}))
    assert isinstance(problem, CloudFieldError)
    assert problem.field == "Key"
    assert "Key" in said(problem)
    assert "voices" in provider.fields()[0].help
    caps = provider.capabilities()
    assert (caps.streaming, caps.biasing_limit, caps.biasing_name) == (True, 50, "keyterms")


def test_shared_elevenlabs_key_reads_the_voices_target(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.platform.windows import credential_manager

    seen: list[str] = []

    def fake_load(target: str) -> Any:
        seen.append(target)
        return credential_manager.StoredCredential(target, "", "voice-key")

    monkeypatch.setattr(credential_manager, "load_generic_credential", fake_load)
    assert streaming_more._shared_elevenlabs_key() == "voice-key"
    assert seen == ["ElevenLabs API key"]

    def broken(_target: str) -> Any:
        raise OSError("no store")

    monkeypatch.setattr(credential_manager, "load_generic_credential", broken)
    assert streaming_more._shared_elevenlabs_key() == ""
    monkeypatch.setattr(credential_manager, "load_generic_credential", lambda _t: None)
    assert streaming_more._shared_elevenlabs_key() == ""


# -- Gladia ------------------------------------------------------------------------ #


def _gladia_react(message: Any) -> list[Any]:
    if isinstance(message, bytes):
        return [
            {"type": "transcript", "data": {"is_final": False, "utterance": {"text": "hel"}}},
            {"type": "transcript", "data": {"is_final": True, "utterance": {"text": "Hello."}}},
        ]
    return []


def test_gladia_init_post_then_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"id": "abc", "url": "wss://api.gladia.io/v2/live?token=session-xyz"})
    wire.socket_factory = lambda _url, _headers: FakeSocket(_gladia_react)
    deltas: list[str] = []
    session = Gladia().live(
        {"key": SECRET, "region": "us-west"},
        language="es-ES",
        terms=["Quill", "Bishop"],
        on_delta=deltas.append,
    )
    assert wire.calls == 0  # the init POST waits for open()
    assert _run(session) == "Hello."

    request = wire.requests[0]
    assert request.get_method() == "POST"
    assert request.full_url == "https://api.gladia.io/v2/live?region=us-west"
    assert request.get_header("X-gladia-key") == SECRET
    body = json.loads(request.data)
    assert body["encoding"] == "wav/pcm"
    assert (body["sample_rate"], body["bit_depth"], body["channels"]) == (16000, 16, 1)
    assert body["language_config"] == {"languages": ["es"], "code_switching": False}
    assert body["messages_config"] == {"receive_partial_transcripts": True}
    vocabulary = body["realtime_processing"]["custom_vocabulary_config"]["vocabulary"]
    assert vocabulary == [
        {"value": "Quill", "intensity": 0.5},
        {"value": "Bishop", "intensity": 0.5},
    ]
    assert body["realtime_processing"]["custom_vocabulary"] is True

    url, headers, socket = wire.sockets[0]
    assert url == "wss://api.gladia.io/v2/live?token=session-xyz"
    assert headers == {}
    assert len(socket.binary_sent()[0]) == 3200
    assert socket.text_sent()[-1] == {"type": "stop_recording"}
    assert "hel" in deltas
    assert Gladia().where({"region": "us-west"}) == "the United States"
    assert Gladia().where({}) == "the European Union"


def test_gladia_without_terms_sends_no_vocabulary(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"id": "abc", "url": "wss://api.gladia.io/v2/live?token=t"})
    wire.socket_factory = lambda _url, _headers: FakeSocket(_gladia_react)
    _run(Gladia().live({"key": SECRET}, language="en", terms=[]))
    body = json.loads(wire.requests[0].data)
    assert "realtime_processing" not in body
    assert wire.requests[0].full_url.endswith("region=eu-west")


@pytest.mark.parametrize(
    "url",
    [
        "wss://evil.example.com/v2/live",
        "ws://api.gladia.io/v2/live",
        "wss://gladia.io.evil.com/live",
        "",
    ],
)
def test_gladia_refuses_a_foreign_socket_url(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    wire = install(monkeypatch)
    wire.answer({"id": "abc", "url": url})
    session = Gladia().live({"key": SECRET}, language="en", terms=[])
    with pytest.raises(CloudSpeechError) as caught:
        session.open()
    assert "not Gladia's own" in said(caught.value)
    assert wire.sockets == []


def test_gladia_init_refused_and_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://api.gladia.io/v2/live", 401))
    with pytest.raises(CloudAuthError) as caught:
        Gladia().live({"key": SECRET}, language="en", terms=[]).open()
    assert said(caught.value) == "The key was refused. Check Key."
    assert SECRET not in str(caught.value)

    wire.answer({"url": "wss://api.gladia.io/x"})
    wire.socket_factory = lambda _url, _headers: FakeSocket(
        lambda _m: [{"type": "error", "error": {"message": "bad audio"}}]
    )
    with pytest.raises(CloudSpeechError) as caught:
        _run(Gladia().live({"key": SECRET}, language="en", terms=[]))
    assert said(caught.value) == "Gladia reported a problem: bad audio."


def test_gladia_test_success_and_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"items": []})
    assert Gladia().test({"key": SECRET}) == "Gladia answered: ready."
    request = wire.requests[0]
    assert request.full_url == "https://api.gladia.io/v2/live?limit=1"
    assert request.get_method() == "GET"
    assert request.get_header("X-gladia-key") == SECRET

    wire.answer(http_error(request.full_url, 403))
    with pytest.raises(CloudAuthError) as caught:
        Gladia().test({"key": SECRET})
    assert said(caught.value) == "The key was refused. Check Key."
    assert SECRET not in str(caught.value)
    caps = Gladia().capabilities()
    assert (caps.streaming, caps.biasing_limit, caps.biasing_name) == (
        True,
        100,
        "custom vocabulary",
    )


# -- Rev.ai ------------------------------------------------------------------------ #

_REV_FINAL = {
    "type": "final",
    "elements": [
        {"type": "text", "value": "Hello"},
        {"type": "punct", "value": " "},
        {"type": "text", "value": "world"},
        {"type": "punct", "value": "."},
    ],
}


def _rev_react(message: Any) -> list[Any]:
    if isinstance(message, bytes):
        return [
            {
                "type": "partial",
                "elements": [
                    {"type": "text", "value": "hello"},
                    {"type": "text", "value": "world"},
                ],
            },
            _REV_FINAL,
        ]
    return []


def test_revai_url_token_in_query_and_vocabulary(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(_rev_react)
    deltas: list[str] = []
    session = RevAI().live(
        {"token": SECRET, "vocabulary": "cv-123"},
        language="en",
        terms=["ignored"],
        on_delta=deltas.append,
    )
    session.open()
    socket = wire.sockets[0][2]
    socket.push({"type": "connected", "id": "s1"})
    session.append(_samples())
    assert session.commit(timeout=2.0) == "Hello world."
    session.close()

    url, headers, _socket = wire.sockets[0]
    assert headers == {}
    assert url.startswith("wss://api.rev.ai/speechtotext/v1/stream?")
    assert f"access_token={SECRET}" in url
    assert "content_type=audio/x-raw;layout=interleaved;rate=16000;format=S16LE;channels=1" in url
    assert ("custom_vocabulary_id", "cv-123") in _query(url)
    assert "ignored" not in url
    assert "hello world" in deltas
    assert socket.sent[-1] == "EOS"


def test_revai_without_vocabulary(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(_rev_react)
    _run(RevAI().live({"token": SECRET}, language="en", terms=[]))
    assert "custom_vocabulary_id" not in wire.sockets[0][0]


def test_revai_element_joining() -> None:
    adapter = streaming_more._RevAdapter()
    heard = adapter.hear(json.dumps(_REV_FINAL))
    assert heard.final == "Hello world."
    bare = {
        "type": "final",
        "elements": [
            {"type": "text", "value": "Yes"},
            {"type": "punct", "value": ","},
            {"type": "text", "value": "please"},
            {"type": "punct", "value": "!"},
        ],
    }
    assert adapter.hear(json.dumps(bare)).final == "Yes, please!"
    partial = {"type": "partial", "elements": [{"value": "one"}, {"value": "two"}]}
    assert adapter.hear(json.dumps(partial)).partial == "one two"
    connected = adapter.hear(json.dumps({"type": "connected", "id": "x"}))
    assert connected.partial is None and connected.final is None and not connected.error
    assert adapter.hear(json.dumps({"type": "error", "message": "nope"})).error == (
        "Rev.ai reported a problem: nope."
    )


def test_revai_test_success_and_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"email": "x", "balance_seconds": 10})
    assert RevAI().test({"token": SECRET}) == "Rev.ai answered: ready."
    request = wire.requests[0]
    assert request.full_url == "https://api.rev.ai/speechtotext/v1/account"
    assert request.get_header("Authorization") == f"Bearer {SECRET}"

    wire.answer(http_error(request.full_url, 401))
    with pytest.raises(CloudAuthError) as caught:
        RevAI().test({"token": SECRET})
    assert said(caught.value) == "The access token was refused. Check Access token."
    assert caught.value.field == "Access token"
    assert SECRET not in str(caught.value)


def test_revai_fields_and_capabilities() -> None:
    provider = RevAI()
    token, vocabulary = provider.fields()
    assert (token.key, token.label, token.kind) == ("token", "Access token", "secret")
    assert (vocabulary.key, vocabulary.required) == ("vocabulary", False)
    assert "does not create" in vocabulary.help
    problem = provider.problem({})
    assert problem is not None and problem.field == "Access token"
    caps = provider.capabilities()
    assert (caps.streaming, caps.biasing_limit, caps.biasing_name) == (
        True,
        0,
        "custom vocabulary",
    )
