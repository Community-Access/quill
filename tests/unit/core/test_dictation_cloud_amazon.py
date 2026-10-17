"""Amazon Transcribe: SigV4, the event-stream framing, the live session, Test Connection.

Nothing here touches the network: ``cloud_speech_fakes.install`` replaces both openers.
"""

from __future__ import annotations

import hashlib
import json
import struct
import time
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlsplit

import pytest
from cloud_speech_fakes import FakeSocket, http_error, install

from quill.core.windows_dictation.cloud import amazon, amazon_eventstream, amazon_sigv4
from quill.core.windows_dictation.cloud.amazon import AmazonTranscribe
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudSpeechError,
    said,
)

# AWS's published example credentials (documentation only, not a real account).
ACCESS = "AKIDEXAMPLE"
SECRET = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
WHEN = datetime(2015, 8, 30, 12, 36, 0, tzinfo=UTC)


def _values(**extra: str) -> dict[str, str]:
    values = {"access_key": ACCESS, "secret_key": SECRET, "region": "us-east-1"}
    values.update(extra)
    return values


# -- SigV4 ----------------------------------------------------------------------- #


def _iam_request() -> str:
    return amazon_sigv4.canonical_request(
        "GET",
        "/",
        [("Action", "ListUsers"), ("Version", "2010-05-08")],
        {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Host": "iam.amazonaws.com",
            "X-Amz-Date": "20150830T123600Z",
        },
        amazon_sigv4.EMPTY_SHA256,
    )


def test_sigv4_matches_the_published_iam_example() -> None:
    request = _iam_request()
    assert (
        hashlib.sha256(request.encode()).hexdigest()
        == "f536975d06c0309214f805bb90ccff089219ecd68b2577efef23edd43b7e1a59"
    )
    key = amazon_sigv4.signing_key(SECRET, "20150830", "us-east-1", "iam")
    assert key.hex() == "c4afb1cc5771d871763a393e44b703571b55cc28424d1a5e86da6ed3c154a4b9"
    assert (
        amazon_sigv4.signature(SECRET, "20150830T123600Z", "us-east-1", "iam", request)
        == "5d672d79c15b13162d9279b0855cfba6789a8edb4c82c400e06b5924a6f2b5d7"
    )


def test_sign_headers_builds_the_authorization_header() -> None:
    headers = amazon_sigv4.sign_headers(
        method="GET",
        host="iam.amazonaws.com",
        path="/",
        params=[("Action", "ListUsers"), ("Version", "2010-05-08")],
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        body=b"",
        access_key=ACCESS,
        secret_key=SECRET,
        region="us-east-1",
        service="iam",
        when=WHEN,
    )
    assert headers["Authorization"] == (
        "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/iam/aws4_request, "
        "SignedHeaders=content-type;host;x-amz-date, "
        "Signature=5d672d79c15b13162d9279b0855cfba6789a8edb4c82c400e06b5924a6f2b5d7"
    )
    assert headers["X-Amz-Date"] == "20150830T123600Z"
    assert SECRET not in json.dumps(headers)


def test_presigned_url_has_the_query_and_never_the_secret() -> None:
    url = amazon_sigv4.presign_url(
        scheme="wss",
        host="transcribestreaming.us-east-1.amazonaws.com:8443",
        path="/stream-transcription-websocket",
        params=[("language-code", "en-US"), ("media-encoding", "pcm"), ("sample-rate", "16000")],
        access_key=ACCESS,
        secret_key=SECRET,
        session_token="TOKEN/with+slash=",
        region="us-east-1",
        service="transcribe",
        when=WHEN,
    )
    parts = urlsplit(url)
    assert parts.scheme == "wss"
    assert parts.netloc == "transcribestreaming.us-east-1.amazonaws.com:8443"
    assert parts.path == "/stream-transcription-websocket"
    query = dict(parse_qsl(parts.query))
    assert query["X-Amz-Algorithm"] == "AWS4-HMAC-SHA256"
    assert query["X-Amz-Credential"] == "AKIDEXAMPLE/20150830/us-east-1/transcribe/aws4_request"
    assert query["X-Amz-Date"] == "20150830T123600Z"
    assert query["X-Amz-Expires"] == "300"
    assert query["X-Amz-SignedHeaders"] == "host"
    assert query["X-Amz-Security-Token"] == "TOKEN/with+slash="
    assert query["language-code"] == "en-US"
    assert query["sample-rate"] == "16000"
    assert len(query["X-Amz-Signature"]) == 64
    assert SECRET not in url
    assert "EXAMPLEKEY" not in url
    # The signature covers the query: re-signing what was sent gives the same value.
    rest = [(k, v) for k, v in parse_qsl(parts.query) if k != "X-Amz-Signature"]
    request = amazon_sigv4.canonical_request(
        "GET", parts.path, rest, {"host": parts.netloc}, amazon_sigv4.EMPTY_SHA256
    )
    assert query["X-Amz-Signature"] == amazon_sigv4.signature(
        SECRET, "20150830T123600Z", "us-east-1", "transcribe", request
    )


def test_presigned_url_without_a_session_token_has_none() -> None:
    url = amazon_sigv4.presign_url(
        scheme="wss",
        host="h.example:8443",
        path="/x",
        params=[],
        access_key=ACCESS,
        secret_key=SECRET,
        region="us-east-1",
        service="transcribe",
        when=WHEN,
    )
    assert "X-Amz-Security-Token" not in url


# -- event stream ---------------------------------------------------------------- #


def test_audio_event_round_trip() -> None:
    frame = amazon_eventstream.decode(amazon_eventstream.audio_event(b"\x01\x02\x03\x04"))
    assert frame.headers == {
        ":content-type": "application/octet-stream",
        ":event-type": "AudioEvent",
        ":message-type": "event",
    }
    assert frame.payload == b"\x01\x02\x03\x04"


def test_audio_event_layout_is_big_endian_with_both_crcs() -> None:
    data = amazon_eventstream.audio_event(b"abc")
    total, header_length, prelude_crc = struct.unpack_from(">III", data)
    assert total == len(data)
    assert prelude_crc == amazon_eventstream._crc(data[:8])
    assert struct.unpack(">I", data[-4:])[0] == amazon_eventstream._crc(data[:-4])
    assert data[12 + header_length : -4] == b"abc"
    # The first header: name length, name, type 7, a two-byte length, the value.
    assert data[12] == len(":content-type")
    assert data[13 : 13 + 13] == b":content-type"
    assert data[26] == 7


def test_empty_audio_event_ends_the_stream() -> None:
    frame = amazon_eventstream.decode(amazon_eventstream.audio_event(b""))
    assert frame.payload == b"" and frame.event_type == "AudioEvent"


@pytest.mark.parametrize("where", [5, 14, -2])
def test_damaged_frame_is_refused(where: int) -> None:
    data = bytearray(amazon_eventstream.audio_event(b"payload"))
    data[where] ^= 0xFF
    with pytest.raises(amazon_eventstream.EventStreamError):
        amazon_eventstream.decode(bytes(data))


def test_short_frame_is_refused() -> None:
    with pytest.raises(amazon_eventstream.EventStreamError):
        amazon_eventstream.decode(b"\x00\x00")


def _transcript_frame(text: str, partial: bool) -> bytes:
    body = {
        "Transcript": {
            "Results": [
                {
                    "Alternatives": [{"Transcript": text}],
                    "IsPartial": partial,
                    "ResultId": "r1",
                }
            ]
        }
    }
    return amazon_eventstream.encode(
        {
            ":content-type": "application/json",
            ":event-type": "TranscriptEvent",
            ":message-type": "event",
        },
        json.dumps(body).encode(),
    )


def _exception_frame(kind: str) -> bytes:
    return amazon_eventstream.encode(
        {
            ":content-type": "application/json",
            ":exception-type": kind,
            ":message-type": "exception",
        },
        json.dumps({"Message": "secret-free detail"}).encode(),
    )


# -- the live session ------------------------------------------------------------ #


def _wait_for(predicate, seconds: float = 2.0) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not predicate():
        time.sleep(0.01)


def test_live_session_partial_then_final(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("numpy")  # the live-dictation extra, not in every CI leg
    wire = install(monkeypatch)
    replies = iter([
        [_transcript_frame("hello", True)],
        [_transcript_frame("hello wor", True)],
        [_transcript_frame("Hello world.", False)],
    ])
    wire.socket_factory = lambda _url, _headers: FakeSocket(lambda _m: next(replies, []))
    deltas: list[str] = []
    session = AmazonTranscribe().live(
        _values(vocabulary="my-words"), language="en", terms=["ignored"], on_delta=deltas.append
    )
    assert wire.calls == 0  # nothing is sent until the session opens
    session.open()
    url, headers, socket = wire.sockets[0]
    query = dict(parse_qsl(urlsplit(url).query))
    assert url.startswith(
        "wss://transcribestreaming.us-east-1.amazonaws.com:8443/stream-transcription-websocket?"
    )
    assert query["language-code"] == "en-US"
    assert query["media-encoding"] == "pcm"
    assert query["sample-rate"] == "16000"
    assert query["vocabulary-name"] == "my-words"
    assert "ignored" not in url
    assert SECRET not in url and headers == {}
    for _ in range(3):
        session.append([0.0] * 1600)
    _wait_for(lambda: "Hello world." in deltas)
    assert deltas[:2] == ["hello", "hello wor"]
    assert session.commit() == "Hello world."
    frames = [amazon_eventstream.decode(m) for m in socket.binary_sent()]
    assert all(f.event_type == "AudioEvent" for f in frames)
    assert len(frames[0].payload) == 3200  # 100 ms of 16-bit audio
    session.close()
    last = amazon_eventstream.decode(socket.sent[-1])
    assert last.event_type == "AudioEvent" and last.payload == b""
    assert socket.closed


def test_live_session_exception_frame_is_a_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("numpy")  # the live-dictation extra, not in every CI leg
    wire = install(monkeypatch)
    wire.socket_factory = lambda _url, _headers: FakeSocket(
        lambda _m: [_exception_frame("BadRequestException")]
    )
    session = AmazonTranscribe().live(_values(), language="en", terms=[])
    session.open()
    session.append([0.0] * 1600)
    with pytest.raises(CloudSpeechError) as caught:
        session.commit(timeout=1.0)
    assert "Check Language" in said(caught.value)
    assert "secret-free detail" not in said(caught.value)
    session.close()


def test_adapter_reads_other_frames_as_nothing() -> None:
    adapter = amazon._AmazonAdapter()
    assert adapter.hear(b"not a frame") == amazon.Heard()
    other = amazon_eventstream.encode({":message-type": "event", ":event-type": "Other"}, b"{}")
    assert adapter.hear(other) == amazon.Heard()
    assert "over its limit" in adapter.hear(_exception_frame("LimitExceededException")).error


def test_live_refuses_without_keys_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    with pytest.raises(CloudFieldError) as caught:
        AmazonTranscribe().live({"region": "us-east-1"}, language="en", terms=[])
    assert caught.value.field == "Access key ID"
    assert wire.calls == 0


# -- fields and the profile file ------------------------------------------------- #


def test_facts_and_capabilities() -> None:
    provider = AmazonTranscribe()
    assert (provider.id, provider.short_name, provider.company) == (
        "amazon",
        "Amazon",
        "Amazon Web Services",
    )
    caps = provider.capabilities()
    assert caps.streaming and caps.timestamps and caps.biasing_limit == 0
    assert provider.where({"region": "eu-west-1"}) == "eu-west-1"
    keys = {spec.key: spec for spec in provider.fields()}
    assert keys["access_key"].secret and keys["secret_key"].secret
    assert keys["session_token"].secret and not keys["session_token"].required
    assert "does not create" in keys["vocabulary"].help
    assert all(spec.help for spec in provider.fields())


def test_problem_names_the_missing_key() -> None:
    provider = AmazonTranscribe()
    assert provider.problem(_values()) is None
    assert provider.problem({"access_key": ACCESS}).field == "Secret access key"  # type: ignore[union-attr]
    assert provider.problem({"secret_key": SECRET}).field == "Access key ID"  # type: ignore[union-attr]
    bad = provider.problem(_values(region="us-east-1.evil.example/"))
    assert bad is not None and bad.field == "Region"
    assert provider.problem(_values(vocabulary="no spaces")).field == "Vocabulary name"  # type: ignore[union-attr]


def _credentials_file(tmp_path, monkeypatch: pytest.MonkeyPatch, text: str):  # type: ignore[no-untyped-def]
    path = tmp_path / "credentials"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(amazon, "credentials_file", lambda: path)
    return path


def test_profile_is_read_only_when_named(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    _credentials_file(
        tmp_path,
        monkeypatch,
        "[default]\naws_access_key_id = AKIADEFAULT00000\n"
        "aws_secret_access_key = d%efault/Secret\n\n"
        "[work]\naws_access_key_id = AKIAWORK00000000\naws_secret_access_key = workSecret/abc\n"
        "aws_session_token = workToken123\n",
    )
    provider = AmazonTranscribe()
    assert provider.problem({"profile": "work"}) is None
    access, secret, token, field = provider._keys({"profile": "work"})
    assert (access, secret, token, field) == (
        "AKIAWORK00000000",
        "workSecret/abc",
        "workToken123",
        "Profile name",
    )
    assert amazon.read_profile("default")[1] == "d%efault/Secret"  # no interpolation
    # Keys from the page win over the profile.
    assert provider._keys(_values(profile="work"))[:2] == (ACCESS, SECRET)
    missing = provider.problem({"profile": "nobody"})
    assert missing is not None and missing.field == "Profile name"
    assert "workSecret" not in said(missing)


def test_profile_without_a_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(amazon, "credentials_file", lambda: tmp_path / "absent")
    found = AmazonTranscribe().problem({"profile": "work"})
    assert found is not None and found.field == "Profile name"


def test_profile_keys_sign_the_live_url(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    _credentials_file(
        tmp_path,
        monkeypatch,
        "[work]\naws_access_key_id = AKIAWORK00000000\naws_secret_access_key = workSecret/abc\n"
        "aws_session_token = workToken123\n",
    )
    wire = install(monkeypatch)
    session = AmazonTranscribe().live(
        {"profile": "work", "region": "eu-west-1"}, language="en", terms=[]
    )
    session.open()
    url = wire.sockets[0][0]
    query = dict(parse_qsl(urlsplit(url).query))
    assert query["X-Amz-Credential"].startswith("AKIAWORK00000000/")
    assert "/eu-west-1/transcribe/aws4_request" in query["X-Amz-Credential"]
    assert query["X-Amz-Security-Token"] == "workToken123"
    assert "workSecret" not in url
    session.close()


# -- Test Connection ------------------------------------------------------------- #


def test_test_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"Vocabularies": []})
    assert AmazonTranscribe().test(_values()) == "Amazon answered: ready, region us-east-1."
    (request,) = wire.requests
    assert request.full_url == "https://transcribe.us-east-1.amazonaws.com/"
    assert request.get_method() == "POST"
    assert json.loads(request.data) == {"MaxResults": 1}
    headers = {k.lower(): v for k, v in request.header_items()}
    assert headers["x-amz-target"] == "Transcribe.ListVocabularies"
    assert headers["content-type"] == "application/x-amz-json-1.1"
    assert headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/")
    assert "/us-east-1/transcribe/aws4_request" in headers["authorization"]
    assert "x-amz-target" in headers["authorization"]
    assert SECRET not in json.dumps(headers)


@pytest.mark.parametrize("status", [401, 403])
def test_test_connection_refused(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://transcribe.us-east-1.amazonaws.com/", status))
    with pytest.raises(CloudAuthError) as caught:
        AmazonTranscribe().test(_values())
    assert caught.value.field == "Secret access key"
    assert said(caught.value) == "The secret access key was refused. Check Secret access key."
    assert SECRET not in said(caught.value) and ACCESS not in said(caught.value)


def test_test_connection_unknown_key_is_400_from_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    body = json.dumps({"__type": "UnrecognizedClientException", "message": ACCESS}).encode()
    wire.answer(http_error("https://transcribe.us-east-1.amazonaws.com/", 400, body))
    with pytest.raises(CloudAuthError) as caught:
        AmazonTranscribe().test(_values())
    assert caught.value.field == "Secret access key"
    assert ACCESS not in said(caught.value)


def test_test_connection_missing_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    body = json.dumps({"__type": "AccessDeniedException"}).encode()
    wire.answer(http_error("https://transcribe.us-east-1.amazonaws.com/", 400, body))
    with pytest.raises(CloudAuthError) as caught:
        AmazonTranscribe().test(_values())
    assert "permissions" in said(caught.value)


def test_test_connection_expired_session_token(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    body = json.dumps({"__type": "ExpiredTokenException"}).encode()
    wire.answer(http_error("https://transcribe.us-east-1.amazonaws.com/", 400, body))
    with pytest.raises(CloudAuthError) as caught:
        AmazonTranscribe().test(_values(session_token="tok-12345678"))
    assert caught.value.field == "Session token"


def test_test_connection_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    wire.answer(OSError("no route"))
    with pytest.raises(CloudSpeechError) as caught:
        AmazonTranscribe().test(_values())
    assert "could not be reached" in said(caught.value)


def test_test_connection_refuses_before_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = install(monkeypatch)
    with pytest.raises(CloudFieldError):
        AmazonTranscribe().test({"region": "us-east-1"})
    assert wire.calls == 0
