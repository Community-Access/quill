"""Google Cloud Speech-to-Text v2: the service-account sign-in, Test Connection, one phrase.

Nothing here touches the network: ``cloud_speech_fakes.install`` replaces both openers.
The RSA key is made fresh for the test run; it is nobody's key.
"""

from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs

import pytest
from cloud_speech_fakes import http_error, install
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from quill.core.windows_dictation.cloud import google
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    said,
)
from quill.core.windows_dictation.cloud.google import GoogleSpeech

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PEM = _KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()


def _account(**extra: str) -> str:
    data = {
        "type": "service_account",
        "project_id": "quill-test-project",
        "private_key_id": "kid-0123456789",
        "private_key": _PEM,
        "client_email": "dictation@quill-test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "token_uri": "https://evil.example/token",  # never used: the token URL is fixed
    }
    data.update(extra)
    return json.dumps(data)


def _values(**extra: str) -> dict[str, str]:
    values = {
        "service_account": _account(),
        "location": "us",
        "recognizer": "_",
        "model": "chirp_3",
    }
    values.update(extra)
    return values


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


TOKEN = {"access_token": "ya29.test-access-token", "expires_in": 3599, "token_type": "Bearer"}


# -- the JWT --------------------------------------------------------------------- #


def test_jwt_header_claims_and_signature() -> None:
    account = google.ServiceAccount(_account())
    jwt = google.make_jwt(account, now=1_700_000_000)
    head, body, sig = jwt.split(".")
    assert json.loads(_unb64(head)) == {"alg": "RS256", "typ": "JWT", "kid": "kid-0123456789"}
    assert json.loads(_unb64(body)) == {
        "iss": "dictation@quill-test-project.iam.gserviceaccount.com",
        "scope": "https://www.googleapis.com/auth/cloud-platform",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": 1_700_000_000,
        "exp": 1_700_003_600,
    }
    # Verifies with the public key (raises when it does not).
    _KEY.public_key().verify(
        _unb64(sig), f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    assert "PRIVATE KEY" not in jwt


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        "[1, 2]",
        json.dumps({"type": "authorized_user", "client_email": "a@b", "private_key": _PEM}),
        _account(private_key="-----BEGIN PRIVATE KEY-----\nbroken\n-----END PRIVATE KEY-----\n"),
        _account(client_email=""),
    ],
    # Stable ids: the generated key differs per process, and pytest-xdist
    # needs every worker to collect the same names.
    ids=["empty", "not-json", "a-list", "not-a-service-account", "broken-key", "no-email"],
)
def test_bad_service_account_file_is_refused_before_any_request(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    wire = install(monkeypatch)
    provider = GoogleSpeech()
    with pytest.raises(CloudFieldError) as caught:
        provider.test(_values(service_account=text))
    assert caught.value.field == "Service account file"
    with pytest.raises(CloudFieldError):
        provider.phrase(_values(service_account=text), [0.0] * 160, language="en", terms=[])
    assert provider.problem(_values(service_account=text)) is not None
    assert wire.calls == 0
    assert "PRIVATE" not in said(caught.value)


def test_no_project_anywhere_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    found = GoogleSpeech().problem(_values(service_account=_account(project_id="")))
    assert found is not None and found.field == "Project"
    assert wire.calls == 0


# -- Test Connection ------------------------------------------------------------- #


def test_test_connection_exchanges_the_token_then_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(TOKEN, {"recognizers": []})
    sentence = GoogleSpeech().test(_values())
    assert sentence == "Google answered: ready, project quill-test-project, location us."
    token_request, list_request = wire.requests
    assert token_request.full_url == "https://oauth2.googleapis.com/token"
    assert token_request.get_method() == "POST"
    form = parse_qs(token_request.data.decode())
    assert form["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
    assert form["assertion"][0].count(".") == 2
    assert "PRIVATE" not in token_request.data.decode()
    assert list_request.full_url == (
        "https://us-speech.googleapis.com/v2/projects/quill-test-project/locations/us"
        "/recognizers?pageSize=1"
    )
    assert list_request.get_header("Authorization") == "Bearer ya29.test-access-token"


def test_global_location_uses_the_plain_host(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(TOKEN, {})
    GoogleSpeech().test(_values(location="global", project="other-project"))
    assert wire.requests[1].full_url.startswith(
        "https://speech.googleapis.com/v2/projects/other-project/locations/global/"
    )


def test_refused_service_account(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(
        http_error("https://oauth2.googleapis.com/token", 400, b'{"error":"invalid_grant"}')
    )
    with pytest.raises(CloudAuthError) as caught:
        GoogleSpeech().test(_values())
    assert caught.value.field == "Service account file"
    assert "PRIVATE" not in said(caught.value)


def test_api_not_enabled_names_project(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    body = b'{"error":{"status":"PERMISSION_DENIED","details":[{"reason":"SERVICE_DISABLED"}]}}'
    wire.answer(TOKEN, http_error("https://us-speech.googleapis.com/", 403, body))
    with pytest.raises(CloudFieldError) as caught:
        GoogleSpeech().test(_values())
    assert caught.value.field == "Project"


def test_missing_role_names_service_account(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(TOKEN, http_error("https://us-speech.googleapis.com/", 403, b"{}"))
    with pytest.raises(CloudAuthError) as caught:
        GoogleSpeech().test(_values())
    assert caught.value.field == "Service account file"
    assert "ya29" not in said(caught.value)


# -- one phrase ------------------------------------------------------------------ #


def test_phrase_carries_the_adaptation_phrases(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(
        TOKEN,
        {
            "results": [
                {"alternatives": [{"transcript": "Hello Quill"}], "languageCode": "en-us"},
                {"alternatives": [{"transcript": " and Jeff."}]},
                {"alternatives": []},
            ]
        },
    )
    text = GoogleSpeech().phrase(_values(), [0.0] * 1600, language="en", terms=["QUILL", "Bishop"])
    assert text == "Hello Quill and Jeff."
    request = wire.requests[1]
    assert request.full_url == (
        "https://us-speech.googleapis.com/v2/projects/quill-test-project/locations/us"
        "/recognizers/_:recognize"
    )
    assert request.get_header("Authorization") == "Bearer ya29.test-access-token"
    body = json.loads(request.data)
    config = body["config"]
    assert config["autoDecodingConfig"] == {}
    assert config["languageCodes"] == ["en-US"]
    assert config["model"] == "chirp_3"
    assert config["features"] == {"enableAutomaticPunctuation": True}
    assert config["adaptation"] == {
        "phraseSets": [
            {
                "inlinePhraseSet": {
                    "phrases": [{"value": "QUILL", "boost": 10}, {"value": "Bishop", "boost": 10}]
                }
            }
        ]
    }
    audio = base64.b64decode(body["content"])
    assert audio[:4] == b"RIFF" and audio[8:12] == b"WAVE"


def test_phrase_without_terms_has_no_adaptation(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(TOKEN, {"results": []})
    assert (
        GoogleSpeech().phrase(_values(language="en-GB"), [0.0] * 160, language="en", terms=[]) == ""
    )
    config = json.loads(wire.requests[1].data)["config"]
    assert "adaptation" not in config
    assert config["languageCodes"] == ["en-GB"]


def test_token_is_kept_until_shortly_before_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(TOKEN, {"results": []}, {"results": []})
    provider = GoogleSpeech()
    provider.phrase(_values(), [0.0] * 160, language="en", terms=[])
    provider.phrase(_values(), [0.0] * 160, language="en", terms=[])
    urls = [request.full_url for request in wire.requests]
    assert urls.count("https://oauth2.googleapis.com/token") == 1
    # A token Google says is nearly spent is fetched again next time.
    wire.answer({"access_token": "ya29.short", "expires_in": 30}, {}, TOKEN, {})
    other = GoogleSpeech()
    other.test(_values())
    other.test(_values())
    urls = [request.full_url for request in wire.requests[3:]]
    assert urls.count("https://oauth2.googleapis.com/token") == 2


def test_refused_phrase_forgets_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(TOKEN, http_error("https://us-speech.googleapis.com/", 401), TOKEN, {})
    provider = GoogleSpeech()
    with pytest.raises(CloudAuthError):
        provider.phrase(_values(), [0.0] * 160, language="en", terms=[])
    provider.phrase(_values(), [0.0] * 160, language="en", terms=[])
    urls = [request.full_url for request in wire.requests]
    assert urls.count("https://oauth2.googleapis.com/token") == 2


# -- facts ----------------------------------------------------------------------- #


def test_facts_and_capabilities() -> None:
    provider = GoogleSpeech()
    assert (provider.id, provider.short_name, provider.company) == ("google", "Google", "Google")
    caps = provider.capabilities()
    assert not caps.streaming
    assert caps.biasing_limit == 1000 and caps.biasing_name == "adaptation phrases"
    keys = {spec.key: spec for spec in provider.fields()}
    assert keys["service_account"].kind == "file" and keys["service_account"].required
    assert not keys["project"].required
    assert keys["location"].default == "us"
    assert keys["recognizer"].default == "_" and keys["model"].default == "chirp_3"
    assert provider.where({"location": "eu"}) == "eu"
    assert {"eu-speech.googleapis.com", "oauth2.googleapis.com"} <= set(provider.hosts)
    assert all(spec.help for spec in provider.fields())


def test_streaming_pack_problem_is_a_sentence_or_empty() -> None:
    sentence = google.streaming_pack_problem()
    assert sentence in (
        "",
        "Live words from Google need the optional Google streaming pack, which is not "
        "installed in this copy of QUILL. Google works a phrase at a time.",
    )


def test_streaming_pack_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real = builtins.__import__

    def refuse(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name.startswith(("google.cloud", "grpc")):
            raise ImportError(name)
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse)
    assert google.streaming_pack_problem().startswith("Live words from Google need")
