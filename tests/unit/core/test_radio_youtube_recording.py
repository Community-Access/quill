"""Recording a YouTube station (#1268): the capture URL is resolved, not stored.

YouTube's media addresses expire within hours, so a recording -- especially a
scheduled one that fires days later -- must resolve at the moment of capture.
The job keeps the durable page URL for identity and reconnects; only ffmpeg
sees the short-lived one.
"""

from __future__ import annotations

import pytest

from quill.core.radio.recording import RecordingError, _resolve_capture_url
from quill.core.radio.youtube import YouTubeError, YouTubeStream

_YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_an_ordinary_stream_url_is_captured_as_given() -> None:
    # Ordinary radio pays nothing for this: no resolve, no network, no delay.
    assert _resolve_capture_url("http://example.test/live.mp3") == "http://example.test/live.mp3"


def test_a_youtube_link_is_resolved_at_capture_time(monkeypatch) -> None:
    seen: list[str] = []

    def fake_resolve(url: str, **_kwargs: object) -> YouTubeStream:
        seen.append(url)
        return YouTubeStream(stream_url="https://media.test/audio.m4a", page_url=url)

    monkeypatch.setattr("quill.core.radio.youtube.resolve_youtube_stream", fake_resolve)

    assert _resolve_capture_url(_YOUTUBE) == "https://media.test/audio.m4a"
    assert seen == [_YOUTUBE]


def test_a_resolve_failure_becomes_a_recording_error_with_the_reason(monkeypatch) -> None:
    # Handing ffmpeg an HTML page would produce a corrupt file and a confusing
    # "recording started" announcement, so the start is refused instead.
    def fake_resolve(url: str, **_kwargs: object) -> YouTubeStream:
        raise YouTubeError("That video is private.")

    monkeypatch.setattr("quill.core.radio.youtube.resolve_youtube_stream", fake_resolve)

    with pytest.raises(RecordingError) as excinfo:
        _resolve_capture_url(_YOUTUBE)
    assert "private" in str(excinfo.value)
