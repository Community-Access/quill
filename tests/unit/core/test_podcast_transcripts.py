"""Tests for podcast transcripts: parsing plain/VTT/SRT/Podcasting-2.0-JSON
transcript bodies and the Safe Mode gate (no real network)."""

from __future__ import annotations

import json

import pytest

from quill.core.podcasts.transcripts import (
    TranscriptError,
    fetch_and_parse_transcript,
    parse_transcript,
    refuse_in_safe_mode,
)


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(TranscriptError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_parse_transcript_plain_text() -> None:
    text = parse_transcript(b"  Hello, this is the show.  ", "text/plain")
    assert text == "Hello, this is the show."


def test_parse_transcript_unrecognized_type_falls_back_to_plain_text() -> None:
    text = parse_transcript(b"Some readable content", "application/x-mystery")
    assert text == "Some readable content"


def test_parse_transcript_vtt_strips_header_timing_and_blanks() -> None:
    vtt = (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:02.000\n"
        "Hello there.\n\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "Welcome to the show.\n"
    )
    text = parse_transcript(vtt.encode(), "text/vtt")
    assert text == "Hello there.\nWelcome to the show."


def test_parse_transcript_srt_strips_index_and_timing() -> None:
    srt = (
        "1\n"
        "00:00:00,000 --> 00:00:02,000\n"
        "Hello there.\n\n"
        "2\n"
        "00:00:02,000 --> 00:00:04,000\n"
        "Welcome to the show.\n"
    )
    text = parse_transcript(srt.encode(), "application/srt")
    assert text == "Hello there.\nWelcome to the show."


def test_parse_transcript_podcast_json_with_speakers() -> None:
    data = {
        "segments": [
            {"speaker": "Host", "body": "Welcome back."},
            {"speaker": "", "body": "No speaker on this one."},
            {"body": "Missing speaker key entirely."},
        ]
    }
    text = parse_transcript(json.dumps(data).encode(), "application/json")
    assert text == ("Host: Welcome back.\nNo speaker on this one.\nMissing speaker key entirely.")


def test_parse_transcript_podcast_json_ignores_blank_segments() -> None:
    data = {"segments": [{"speaker": "Host", "body": "   "}, {"speaker": "Host", "body": "Real."}]}
    text = parse_transcript(json.dumps(data).encode(), "application/json")
    assert text == "Host: Real."


def test_parse_transcript_malformed_json_raises() -> None:
    with pytest.raises(TranscriptError):
        parse_transcript(b"not json", "application/json")


def test_parse_transcript_json_without_segments_returns_empty() -> None:
    assert parse_transcript(b'{"other": true}', "application/json") == ""


def test_fetch_and_parse_transcript_blank_url_returns_empty() -> None:
    assert fetch_and_parse_transcript("", "text/plain") == ""


def test_fetch_and_parse_transcript_refuses_in_safe_mode() -> None:
    with pytest.raises(TranscriptError):
        fetch_and_parse_transcript("https://example.com/t.vtt", "text/vtt", safe_mode=True)


class TestTranscriptCache:
    def test_save_load_round_trip(self, tmp_path, monkeypatch) -> None:
        from quill.core.podcasts import transcripts as t

        monkeypatch.setattr(t, "_cache_dir", lambda: tmp_path / "cache")
        t.save_cached_transcript("show-1", "guid-1", "Hello transcript world.")
        assert t.load_cached_transcript("show-1", "guid-1") == "Hello transcript world."
        assert t.load_cached_transcript("show-1", "other") == ""

    def test_iter_cached_transcripts(self, tmp_path, monkeypatch) -> None:
        from quill.core.podcasts import transcripts as t

        monkeypatch.setattr(t, "_cache_dir", lambda: tmp_path / "cache")
        t.save_cached_transcript("s1", "g1", "alpha")
        t.save_cached_transcript("s2", "g2", "beta")
        entries = sorted(t.iter_cached_transcripts())
        assert ("s1", "g1", "alpha") in entries
        assert ("s2", "g2", "beta") in entries

    def test_empty_text_is_not_cached(self, tmp_path, monkeypatch) -> None:
        from quill.core.podcasts import transcripts as t

        monkeypatch.setattr(t, "_cache_dir", lambda: tmp_path / "cache")
        t.save_cached_transcript("s1", "g1", "   ")
        assert t.iter_cached_transcripts() == []
