"""IBM Watson Speech to Text over recorded fakes: no network, no real store."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import numpy as np
import pytest
from cloud_speech_fakes import FakeSocket, http_error, install

from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudSpeechError,
    said,
)
from quill.core.windows_dictation.cloud.ibm import WatsonSpeech, region_of
from quill.core.windows_dictation.cloud.types import CloudProvider

SECRET = "ibm-very-secret-123"
TOKEN = "eyJ-short-lived-token"
SERVICE = "https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/abc-123"
VALUES = {"key": SECRET, "service_url": SERVICE}


def _samples() -> Any:
    return np.zeros(1600, dtype=np.float32)


def _query(url: str) -> list[tuple[str, str]]:
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)


# -- facts and fields ---------------------------------------------------------------- #


def test_facts_and_capabilities() -> None:
    provider = WatsonSpeech()
    assert isinstance(provider, CloudProvider)
    assert (provider.id, provider.name, provider.short_name, provider.company) == (
        "ibm",
        "IBM Watson Speech to Text",
        "IBM Watson",
        "IBM",
    )
    caps = provider.capabilities()
    assert caps.streaming and caps.biasing_limit == 0 and not caps.biasing and caps.timestamps
    assert [spec.key for spec in provider.fields()] == [
        "key",
        "service_url",
        "model",
        "customization_id",
    ]
    assert provider.fields()[0].kind == "secret"
    custom_help = provider.fields()[3].help
    assert "does not create" in custom_help
    assert provider.where(VALUES) == "us-south"


def test_region_of() -> None:
    assert region_of(SERVICE) == "us-south"
    assert region_of("https://api.private.eu-de.speech-to-text.watson.cloud.ibm.com/i/x") == "eu-de"
    assert region_of("") == ""


def test_missing_key_names_key(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    with pytest.raises(CloudFieldError) as caught:
        WatsonSpeech().test({"service_url": SERVICE})
    assert caught.value.field == "Key"
    assert wire.calls == 0


@pytest.mark.parametrize(
    "service_url",
    [
        "",
        "http://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/x",
        "https://api.us-south.speech-to-text.watson.cloud.ibm.com.evil.example/x",
        "https://evil.example/speech-to-text.watson.cloud.ibm.com",
    ],
)
def test_bad_service_url_refused_before_anything_is_sent(
    monkeypatch: pytest.MonkeyPatch, service_url: str
) -> None:
    wire = install(monkeypatch)
    values = {"key": SECRET, "service_url": service_url}
    with pytest.raises(CloudFieldError) as caught:
        WatsonSpeech().test(values)
    assert caught.value.field == "Service URL"
    with pytest.raises(CloudFieldError):
        WatsonSpeech().live(values, language="en", terms=[])
    assert wire.calls == 0


def test_bad_model_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    with pytest.raises(CloudFieldError) as caught:
        WatsonSpeech().test({**VALUES, "model": "en-US&x=1"})
    assert caught.value.field == "Model"
    assert wire.calls == 0


# -- token and Test Connection -------------------------------------------------------- #


def test_test_connection_exchanges_the_key_then_lists_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire = install(monkeypatch)
    wire.answer({"access_token": TOKEN, "expires_in": 3600}, {"models": [{}, {}]})
    assert WatsonSpeech().test(VALUES) == "IBM Watson answered: ready, 2 models, us-south."

    token_request, models_request = wire.requests
    assert token_request.full_url == "https://iam.cloud.ibm.com/identity/token"
    assert token_request.get_method() == "POST"
    assert token_request.get_header("Content-type") == "application/x-www-form-urlencoded"
    assert token_request.get_header("Accept") == "application/json"
    form = dict(parse_qsl(token_request.data.decode("ascii")))
    assert form == {"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": SECRET}

    assert models_request.full_url == SERVICE + "/v1/models"
    assert models_request.get_method() == "GET"
    assert models_request.get_header("Authorization") == f"Bearer {TOKEN}"
    assert SECRET not in models_request.full_url


@pytest.mark.parametrize("status", [400, 401])
def test_refused_key_names_key_without_the_key(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://iam.cloud.ibm.com/identity/token", status))
    with pytest.raises(CloudAuthError) as caught:
        WatsonSpeech().test(VALUES)
    assert said(caught.value) == "The key was refused. Check Key."
    assert caught.value.field == "Key"
    assert SECRET not in str(caught.value)
    assert len(wire.requests) == 1


def test_token_answer_without_a_token_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"errorMessage": "nope"})
    with pytest.raises(CloudAuthError):
        WatsonSpeech().test(VALUES)


def test_models_not_found_points_at_service_url(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"access_token": TOKEN}, http_error(SERVICE, 404))
    with pytest.raises(CloudFieldError) as caught:
        WatsonSpeech().test(VALUES)
    assert caught.value.field == "Service URL"


# -- live ----------------------------------------------------------------------------- #


def _react(message: Any) -> list[Any]:
    if isinstance(message, str):
        event = json.loads(message)
        if event.get("action") == "start":
            return [{"state": "listening"}]
        return []
    return [
        {
            "results": [{"alternatives": [{"transcript": "hello "}], "final": False}],
            "result_index": 0,
        },
        {
            "results": [{"alternatives": [{"transcript": "hello Quill "}], "final": True}],
            "result_index": 0,
        },
    ]


def test_live_url_start_audio_and_results(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"access_token": TOKEN})
    wire.socket_factory = lambda _url, _headers: FakeSocket(_react)
    deltas: list[str] = []
    values = {**VALUES, "customization_id": "cust-1"}
    session = WatsonSpeech().live(values, language="en", terms=["ignored"], on_delta=deltas.append)
    assert wire.calls == 0  # nothing before open(), not even the token
    session.open()
    try:
        session.append(_samples())
        assert session.commit(timeout=2.0) == "hello Quill"
    finally:
        session.close()
    assert deltas[0] == "hello"
    assert deltas[-1] == "hello Quill"

    assert wire.requests[0].full_url == "https://iam.cloud.ibm.com/identity/token"
    url, headers, socket = wire.sockets[0]
    assert url.startswith(
        "wss://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/abc-123/v1/recognize?"
    )
    assert SECRET not in url and SECRET not in json.dumps(headers)
    query = _query(url)
    assert ("access_token", TOKEN) in query
    assert ("model", "en-US_Multimedia") in query
    assert ("language_customization_id", "cust-1") in query

    sent = socket.text_sent()
    assert sent[0] == {
        "action": "start",
        "content-type": "audio/l16;rate=16000;endianness=little-endian",
        "interim_results": True,
        "smart_formatting": True,
        "inactivity_timeout": -1,
    }
    assert sent[-1] == {"action": "stop"}
    assert "ignored" not in json.dumps(sent)
    assert socket.binary_sent()[0] == bytes(3200)
    assert socket.closed


def test_live_spanish_model_and_chosen_model(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"access_token": TOKEN}, {"access_token": TOKEN})
    for values, language, expected in (
        (VALUES, "es", "es-ES_Multimedia"),
        ({**VALUES, "model": "en-GB_Multimedia"}, "es", "en-GB_Multimedia"),
    ):
        session = WatsonSpeech().live(values, language=language, terms=[])
        session.open()
        session.close()
        assert ("model", expected) in _query(wire.sockets[-1][0])
        assert all(name != "language_customization_id" for name, _ in _query(wire.sockets[-1][0]))


def test_live_error_message_becomes_a_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"access_token": TOKEN})

    def react(message: Any) -> list[Any]:
        if isinstance(message, bytes):
            return [{"error": "Model en-XX_Foo not found"}]
        return []

    wire.socket_factory = lambda _url, _headers: FakeSocket(react)
    session = WatsonSpeech().live(VALUES, language="en", terms=[])
    session._adapter.settle_seconds = 0.5  # type: ignore[attr-defined]
    session.open()
    try:
        session.append(_samples())
        with pytest.raises(CloudSpeechError) as caught:
            session.commit(timeout=1.0)
    finally:
        session.close()
    assert said(caught.value) == "IBM Watson reported a problem: Model en-XX_Foo not found."


def test_live_refused_key_at_open(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://iam.cloud.ibm.com/identity/token", 400))
    session = WatsonSpeech().live(VALUES, language="en", terms=[])
    with pytest.raises(CloudAuthError) as caught:
        session.open()
    assert said(caught.value) == "The key was refused. Check Key."
    assert not wire.sockets


def test_live_refused_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"access_token": TOKEN})

    def refuse(_url: str, _headers: dict[str, str]) -> FakeSocket:
        raise http_error("wss://x", 401)

    wire.socket_factory = refuse
    session = WatsonSpeech().live(VALUES, language="en", terms=[])
    with pytest.raises(CloudAuthError) as caught:
        session.open()
    assert SECRET not in str(caught.value) and TOKEN not in str(caught.value)


def test_phrase_is_not_offered() -> None:
    with pytest.raises(CloudSpeechError):
        WatsonSpeech().phrase(VALUES, _samples(), language="en", terms=[])


def test_registry_finds_ibm() -> None:
    from quill.core.windows_dictation.cloud import registry

    assert any(isinstance(provider, WatsonSpeech) for provider in registry.providers())
