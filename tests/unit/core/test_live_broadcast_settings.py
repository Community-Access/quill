"""Live streaming settings, checks and commands (roadmap section 6)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from quill.core.streaming import (
    StreamingError,
    StreamSettings,
    StreamSource,
    credential_name,
    encode_args,
    metadata_request,
    preflight,
    settings_from_dict,
    settings_to_dict,
    shoutcast_handshake,
    shoutcast_source_port,
    stream_command,
    summary,
    validate,
)

MIC = StreamSource("microphone", "Microphone", on=True)


def _settings(**changes) -> StreamSettings:
    base = StreamSettings(host="radio.example.org", port=8000, mount="/live", sources=(MIC,))
    return replace(base, **changes)


def _value(command, flag):
    return command[command.index(flag) + 1]


def test_presets_in_plain_words_set_the_technical_values():
    assert _settings(quality="speech").effective.bitrate == 64
    assert _settings(quality="speech").effective.channels == 1
    custom = _settings(quality="custom", format="opus", bitrate=48, channels=1, sample_rate=48000)
    assert custom.effective.format == "opus" and custom.effective.bitrate == 48


@pytest.mark.parametrize(
    "changes",
    [
        {"host": ""},
        {"host": "http://x/"},
        {"port": 0},
        {"mount": "live"},
        {"kind": "shoutcast", "quality": "custom", "format": "opus"},
        {"quality": "custom", "bitrate": 100},
    ],
)
def test_validate_refuses_bad_settings(changes):
    with pytest.raises(StreamingError):
        validate(_settings(**changes))


def test_preflight_stops_and_warns():
    texts = lambda findings, kind: [f.text for f in findings if f.severity == kind]  # noqa: E731
    clean = preflight(_settings(archive=True, archive_folder="C:\\shows"), password="p")
    assert texts(clean, "Stop") == [] and texts(clean, "Warn") == []
    no_password = preflight(_settings(), password="")
    assert any("No password" in t for t in texts(no_password, "Stop"))
    silent = preflight(_settings(sources=()), password="p")
    assert any("silence" in t for t in texts(silent, "Stop"))
    reader = StreamSource("screen-reader", "JAWS speech", on=True, is_screen_reader=True)
    warned = preflight(_settings(sources=(reader,)), password="p", measured_kbps=100)
    warns = texts(warned, "Warn")
    assert any("microphone is not in the stream" in t for t in warns)
    assert any("listeners hear everything" in t for t in warns)
    assert any("Choose a lower quality" in t for t in warns)
    assert any("No copy of the show" in t for t in warns)


def test_summary_says_where_what_and_how():
    text = summary(_settings(title="Morning show", public=True), [])
    assert "Going live on Icecast at radio.example.org:8000/live." in text
    assert "Morning show, listed publicly." in text and "Microphone (+0 dB)" in text


def test_icecast_command_keeps_the_password_out_of_the_url():
    command = stream_command("ffmpeg", _settings(secure=True, quality="music"), "s3cret")
    assert command[-1] == "icecast://source@radio.example.org:8000/live"
    assert _value(command, "-password") == "s3cret" and _value(command, "-tls") == "1"
    assert _value(command, "-b:a") == "192k"
    assert command[len(command) - 1 - command[::-1].index("-f") + 1] == "mp3"
    assert "s3cret" not in command[-1]


def test_loudness_and_archive_and_shoutcast_pipe():
    args = encode_args(_settings(loudness="talk"))
    assert args[1].startswith("loudnorm=I=-16.0")
    command = stream_command("ffmpeg", _settings(kind="shoutcast"), "p", archive_path="C:/a.flac")
    assert "pipe:1" in command and command[-1] == "C:/a.flac"


def test_shoutcast_handshake_and_port():
    login, headers = shoutcast_handshake(
        _settings(kind="shoutcast", stream_id=3, title="Show"), "pw"
    )
    assert login == b"pw:#3\r\n"
    assert b"icy-name:Show\r\n" in headers and headers.endswith(b"\r\n\r\n")
    assert shoutcast_source_port(_settings(kind="shoutcast")) == 8001


def test_metadata_requests():
    url, headers = metadata_request(_settings(), "pw", "Song & Artist")
    assert url.startswith("http://radio.example.org:8000/admin/metadata?mount=%2Flive&mode=updinfo")
    assert "song=Song+%26+Artist" in url and headers["Authorization"].startswith("Basic ")
    url, headers = metadata_request(_settings(kind="shoutcast", stream_id=2), "pw", "Now")
    assert "/admin.cgi?" in url and "sid=2" in url and headers == {}


def test_password_lives_apart_and_settings_round_trip():
    settings = _settings(title="Show")
    assert credential_name(settings) == "QUILL Studio stream radio.example.org:8000 /live"
    data = settings_to_dict(settings)
    assert "password" not in str(data).lower() or "password" not in data
    assert settings_from_dict(data) == settings
