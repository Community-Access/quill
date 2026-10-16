"""Azure AI Speech over recorded fakes: no network, no real store."""

from __future__ import annotations

import json
import struct
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import numpy as np
import pytest
from cloud_speech_fakes import FakeSocket, http_error, install

from quill.core.windows_dictation.cloud.azure import (
    AzureSpeech,
    split_message,
    wav_header,
)
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudSpeechError,
    said,
)
from quill.core.windows_dictation.cloud.types import CloudProvider

SECRET = "az-very-secret-123"
VALUES = {"key": SECRET, "region": "westeurope"}


def _samples() -> Any:
    return np.zeros(1600, dtype=np.float32)


def _query(url: str) -> list[tuple[str, str]]:
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)


def _server(path: str, payload: dict[str, Any]) -> str:
    return (
        f"X-RequestId: ABC\r\nPath: {path}\r\nContent-Type: application/json; charset=utf-8"
        f"\r\n\r\n{json.dumps(payload)}"
    )


def _audio_parts(message: bytes) -> tuple[dict[str, str], bytes]:
    (length,) = struct.unpack(">H", message[:2])
    head = message[2 : 2 + length].decode("ascii")
    headers, _ = split_message(head + "\r\n")
    return headers, message[2 + length :]


def _sent_texts(socket: FakeSocket) -> list[tuple[dict[str, str], Any]]:
    out = []
    for message in socket.sent:
        if isinstance(message, str):
            headers, body = split_message(message)
            out.append((headers, json.loads(body)))
    return out


# -- facts and fields ---------------------------------------------------------------- #


def test_facts_and_capabilities() -> None:
    provider = AzureSpeech()
    assert isinstance(provider, CloudProvider)
    assert (provider.id, provider.name, provider.short_name, provider.company) == (
        "azure",
        "Azure AI Speech",
        "Azure",
        "Microsoft",
    )
    caps = provider.capabilities()
    assert caps.streaming and caps.biasing_limit == 500 and caps.biasing_name == "phrase list"
    assert not caps.diarization and caps.timestamps
    keys = [spec.key for spec in provider.fields()]
    assert keys == ["key", "region", "endpoint", "endpoint_id", "language"]
    assert provider.fields()[0].kind == "secret"
    regions = dict(provider.fields()[1].choices)
    assert "westeurope" in regions and "swedencentral" in regions
    assert all(spec.help for spec in provider.fields())
    assert provider.where(VALUES) == "westeurope"


def test_missing_key_names_key(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    problem = AzureSpeech().problem({"region": "westeurope"})
    assert problem is not None and problem.field == "Key"
    with pytest.raises(CloudFieldError) as caught:
        AzureSpeech().test({"region": "westeurope"})
    assert caught.value.field == "Key"
    assert wire.calls == 0


def test_region_or_endpoint_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    problem = AzureSpeech().problem({"key": SECRET})
    assert problem is not None and problem.field == "Region"
    with pytest.raises(CloudFieldError):
        AzureSpeech().live({"key": SECRET}, language="en", terms=[])
    assert (
        AzureSpeech().problem({"key": SECRET, "endpoint": "https://me.cognitiveservices.azure.com"})
        is None
    )
    assert wire.calls == 0


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://me.cognitiveservices.azure.com",
        "https://me.cognitiveservices.azure.com.evil.example",
        "https://evil.example/cognitiveservices.azure.com",
    ],
)
def test_bad_endpoint_refused_before_anything_is_sent(
    monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    wire = install(monkeypatch)
    values = {**VALUES, "endpoint": endpoint}
    with pytest.raises(CloudFieldError) as caught:
        AzureSpeech().test(values)
    assert caught.value.field == "Endpoint"
    with pytest.raises(CloudFieldError):
        AzureSpeech().phrase(values, _samples(), language="en", terms=[])
    assert wire.calls == 0


def test_bad_region_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    with pytest.raises(CloudFieldError) as caught:
        AzureSpeech().test({"key": SECRET, "region": "evil.example/x"})
    assert caught.value.field == "Region"
    assert wire.calls == 0


# -- Test Connection ------------------------------------------------------------------ #


def test_test_connection_posts_issue_token(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(b"eyJ.token")
    assert AzureSpeech().test(VALUES) == "Azure answered: ready, region westeurope."
    request = wire.requests[0]
    assert request.full_url == "https://westeurope.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    assert request.get_method() == "POST"
    assert request.data == b""
    assert request.get_header("Ocp-apim-subscription-key") == SECRET


def test_test_connection_with_endpoint_only(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(b"eyJ.token")
    values = {"key": SECRET, "endpoint": "https://me.cognitiveservices.azure.com/"}
    assert AzureSpeech().test(values) == "Azure answered: ready, me.cognitiveservices.azure.com."
    assert wire.requests[0].full_url == "https://me.cognitiveservices.azure.com/sts/v1.0/issueToken"


def test_refused_key_names_key_without_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://westeurope.api.cognitive.microsoft.com", 401))
    with pytest.raises(CloudAuthError) as caught:
        AzureSpeech().test(VALUES)
    assert said(caught.value) == "The key was refused. Check Key."
    assert caught.value.field == "Key"
    assert SECRET not in str(caught.value)


def test_not_found_points_at_region(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://x", 404))
    with pytest.raises(CloudFieldError) as caught:
        AzureSpeech().test(VALUES)
    assert caught.value.field == "Region"


# -- live ----------------------------------------------------------------------------- #


def _react(message: Any) -> list[Any]:
    if isinstance(message, bytes) and len(message) > 300:
        return [
            _server("turn.start", {"context": {"serviceTag": "x"}}),
            _server("speech.hypothesis", {"Text": "hello", "Offset": 0, "Duration": 1}),
            _server(
                "speech.phrase",
                {
                    "RecognitionStatus": "Success",
                    "DisplayText": "Hello, Quill.",
                    "NBest": [{"Display": "Hello, Quill."}],
                },
            ),
        ]
    return []


def test_live_socket_url_headers_and_framing(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(_react)
    deltas: list[str] = []
    values = {**VALUES, "endpoint_id": "1234-abcd"}
    session = AzureSpeech().live(
        values, language="en", terms=["Quill", "Bishop"], on_delta=deltas.append
    )
    assert wire.calls == 0  # nothing before open()
    session.open()
    try:
        session.append(_samples())
        assert session.commit(timeout=2.0) == "Hello, Quill."
        session.append(_samples())  # a second block: no WAV header this time
    finally:
        session.close()
    assert deltas[0] == "hello"
    assert deltas[-1] == "Hello, Quill."

    url, headers, socket = wire.sockets[0]
    assert url.startswith(
        "wss://westeurope.stt.speech.microsoft.com/speech/recognition/conversation/"
        "cognitiveservices/v1?"
    )
    assert SECRET not in url
    query = _query(url)
    assert ("language", "en-US") in query
    assert ("format", "detailed") in query
    assert ("cid", "1234-abcd") in query
    assert headers["Ocp-Apim-Subscription-Key"] == SECRET
    assert len(headers["X-ConnectionId"]) == 32

    texts = _sent_texts(socket)
    assert texts[0][0]["path"] == "speech.config"
    assert texts[0][1]["context"]["audio"]["source"]["samplerate"] == 16000
    assert texts[1][0]["path"] == "speech.context"
    items = texts[1][1]["dgi"]["Groups"][0]["Items"]
    assert texts[1][1]["dgi"]["Groups"][0]["Type"] == "Generic"
    assert items == [{"Text": "Quill"}, {"Text": "Bishop"}]
    request_id = texts[0][0]["x-requestid"]
    assert len(request_id) == 32
    assert texts[1][0]["x-requestid"] == request_id
    assert texts[0][0]["content-type"] == "application/json"
    assert texts[0][0]["x-timestamp"].endswith("Z")

    audio = socket.binary_sent()
    first_headers, first = _audio_parts(audio[0])
    assert first_headers["path"] == "audio"
    assert first_headers["x-requestid"] == request_id
    assert first_headers["content-type"] == "audio/x-wav"
    assert first[:44] == wav_header()
    assert first[:4] == b"RIFF" and first[8:16] == b"WAVEfmt "
    assert len(first) == 44 + 3200
    _second_headers, second = _audio_parts(audio[1])
    assert len(second) == 3200 and second[:4] != b"RIFF"
    _last_headers, last = _audio_parts(audio[-1])
    assert last == b""  # the end of the stream
    assert socket.closed


def test_live_without_terms_sends_no_context(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(_react)
    session = AzureSpeech().live({**VALUES, "language": "es-MX"}, language="es", terms=[])
    session.open()
    session.close()
    url, _headers, socket = wire.sockets[0]
    assert ("language", "es-MX") in _query(url)
    assert [headers["path"] for headers, _ in _sent_texts(socket)] == ["speech.config"]


def test_live_endpoint_only_uses_the_resource_host(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    values = {"key": SECRET, "endpoint": "https://me.cognitiveservices.azure.com"}
    session = AzureSpeech().live(values, language="en", terms=[])
    session.open()
    session.close()
    assert wire.sockets[0][0].startswith(
        "wss://me.cognitiveservices.azure.com/stt/speech/recognition/conversation/"
    )


def _say(*replies: str) -> Any:
    def react(message: Any) -> list[Any]:
        if isinstance(message, bytes) and len(message) > 300:
            return list(replies)
        return []

    return react


def test_live_no_match_is_an_empty_phrase(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _u, _h: FakeSocket(
        _say(_server("speech.phrase", {"RecognitionStatus": "NoMatch"}), _server("turn.end", {}))
    )
    session = AzureSpeech().live(VALUES, language="en", terms=[])
    session._adapter.settle_seconds = 0.3  # type: ignore[attr-defined]
    session.open()
    try:
        session.append(_samples())
        assert session.commit(timeout=1.0) == ""
    finally:
        session.close()


def test_live_error_status_becomes_a_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _u, _h: FakeSocket(
        _say(_server("speech.phrase", {"RecognitionStatus": "Error"}))
    )
    session = AzureSpeech().live(VALUES, language="en", terms=[])
    session._adapter.settle_seconds = 0.5  # type: ignore[attr-defined]
    session.open()
    try:
        session.append(_samples())
        with pytest.raises(CloudSpeechError) as caught:
            session.commit(timeout=1.0)
    finally:
        session.close()
    assert said(caught.value) == "Azure reported a problem: Error."


def test_live_detailed_phrase_without_display_text(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.socket_factory = lambda _u, _h: FakeSocket(
        _say(
            _server(
                "speech.phrase",
                {"RecognitionStatus": "Success", "NBest": [{"Display": "From the list."}]},
            )
        )
    )
    session = AzureSpeech().live(VALUES, language="en", terms=[])
    session.open()
    try:
        session.append(_samples())
        assert session.commit(timeout=1.0) == "From the list."
    finally:
        session.close()


def test_refused_handshake_names_key(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)

    def refuse(_url: str, _headers: dict[str, str]) -> FakeSocket:
        raise http_error("wss://x", 401)

    wire.socket_factory = refuse
    session = AzureSpeech().live(VALUES, language="en", terms=[])
    with pytest.raises(CloudAuthError) as caught:
        session.open()
    assert said(caught.value) == "The key was refused. Check Key."
    assert SECRET not in str(caught.value)


# -- one phrase ----------------------------------------------------------------------- #


def test_phrase_fast_transcription_with_phrase_list(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"combinedPhrases": [{"text": "Hello, Quill."}], "phrases": []})
    text = AzureSpeech().phrase(VALUES, _samples(), language="es", terms=["Quill", "Bishop"])
    assert text == "Hello, Quill."
    request = wire.requests[0]
    assert request.full_url == (
        "https://westeurope.api.cognitive.microsoft.com/speechtotext/"
        "transcriptions:transcribe?api-version=2024-11-15"
    )
    assert request.get_method() == "POST"
    assert request.get_header("Ocp-apim-subscription-key") == SECRET
    assert request.get_header("Content-type").startswith("multipart/form-data; boundary=")
    body = request.data
    assert b'name="audio"; filename="phrase.wav"' in body
    assert b"RIFF" in body
    marker = b'name="definition"\r\nContent-Type: application/json\r\n\r\n'
    start = body.index(marker) + len(marker)
    definition = json.loads(body[start : body.index(b"\r\n", start)])
    assert definition == {"locales": ["es-ES"], "phraseList": {"phrases": ["Quill", "Bishop"]}}


def test_phrase_uses_the_endpoint_when_given(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"combinedPhrases": []})
    values = {**VALUES, "endpoint": "https://me.cognitiveservices.azure.com"}
    assert AzureSpeech().phrase(values, _samples(), language="en", terms=[]) == ""
    assert wire.requests[0].full_url.startswith(
        "https://me.cognitiveservices.azure.com/speechtotext/transcriptions:transcribe?"
    )
    assert b"phraseList" not in wire.requests[0].data


def test_phrase_refused_key(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://x", 403))
    with pytest.raises(CloudAuthError) as caught:
        AzureSpeech().phrase(VALUES, _samples(), language="en", terms=[])
    assert SECRET not in str(caught.value)


def test_registry_finds_azure() -> None:
    from quill.core.windows_dictation.cloud import registry

    assert any(isinstance(provider, AzureSpeech) for provider in registry.providers())
