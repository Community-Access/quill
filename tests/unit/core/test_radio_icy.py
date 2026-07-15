"""Tests for ICY stream-title parsing (pure parts; no network)."""

from __future__ import annotations

from quill.core.radio.icy import parse_stream_title, read_stream_title


def test_parse_stream_title_extracts_the_quoted_value() -> None:
    block = b"StreamTitle='Artist - Song Name';StreamUrl='';\x00\x00"
    assert parse_stream_title(block) == "Artist - Song Name"


def test_parse_stream_title_handles_empty_and_missing() -> None:
    assert parse_stream_title(b"StreamTitle='';") == ""
    assert parse_stream_title(b"nonsense") == ""
    assert parse_stream_title(b"") == ""


def test_parse_stream_title_survives_bad_bytes() -> None:
    assert parse_stream_title(b"StreamTitle='Caf\xe9 Jazz';") != ""


def test_read_stream_title_refuses_non_http_sources() -> None:
    assert read_stream_title("C:/recordings/show.mp3") == ""
    assert read_stream_title("file:///x.mp3") == ""
