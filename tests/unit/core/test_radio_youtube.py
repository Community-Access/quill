"""YouTube stations for Quill Radio (#1268): recognition, canonical links, resolve."""

from __future__ import annotations

import pytest

from quill.core.radio.youtube import (
    YouTubeError,
    YouTubeStream,
    _best_audio_url,
    canonical_youtube_url,
    ensure_and_resolve,
    is_youtube_url,
    resolve_youtube_stream,
    youtube_video_id,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc&t=30",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/@nasa/live",
        "https://www.youtube.com/channel/UCabc123/live",
    ],
)
def test_recognizes_every_shape_a_listener_actually_has(url: str) -> None:
    assert is_youtube_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "http://example.test/stream.mp3",
        "https://streaming.live365.com/a25891",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch",  # no video id
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ",
    ],
)
def test_leaves_everything_else_alone(url: str) -> None:
    assert not is_youtube_url(url)


def test_video_id_is_read_from_every_id_carrying_shape() -> None:
    assert youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=9") == "dQw4w9WgXcQ"
    assert youtube_video_id("https://www.youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # A channel-live link has no id -- yt-dlp resolves whatever is live at play
    # time -- so "" is a normal answer, not a failure.
    assert youtube_video_id("https://www.youtube.com/@nasa/live") == ""


def test_canonical_url_drops_playlist_and_timestamp_noise() -> None:
    # What gets saved as a favorite should be the durable link, not the one that
    # happened to carry a playlist position and a tracking tag.
    assert (
        canonical_youtube_url("https://youtu.be/dQw4w9WgXcQ?t=42&si=xyz")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert (
        canonical_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_canonical_url_keeps_a_channel_live_link_and_passes_others_through() -> None:
    assert (
        canonical_youtube_url("https://m.youtube.com/@nasa/live")
        == "https://youtube.com/@nasa/live"
    )
    assert (
        canonical_youtube_url("http://example.test/stream.mp3") == "http://example.test/stream.mp3"
    )


def test_resolve_returns_the_stream_the_player_should_load() -> None:
    def fake(page_url: str) -> YouTubeStream:
        assert page_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        return YouTubeStream(
            stream_url="https://media.test/audio.m4a",
            page_url=page_url,
            title="A Broadcast",
            is_live=True,
        )

    stream = resolve_youtube_stream("https://youtu.be/dQw4w9WgXcQ?t=1", resolver=fake)

    assert stream.stream_url == "https://media.test/audio.m4a"
    assert stream.title == "A Broadcast"
    assert stream.is_live is True


def test_resolve_rejects_a_non_youtube_link() -> None:
    with pytest.raises(YouTubeError):
        resolve_youtube_stream(
            "http://example.test/stream.mp3", resolver=lambda _u: YouTubeStream("x", "y")
        )


def test_resolve_explains_an_unplayable_video_instead_of_returning_nothing() -> None:
    # Private, removed, region-blocked, or not-live-yet all land here.
    with pytest.raises(YouTubeError) as excinfo:
        resolve_youtube_stream(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            resolver=lambda url: YouTubeStream(stream_url="", page_url=url),
        )
    assert "private" in str(excinfo.value)


def test_resolve_is_refused_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(YouTubeError) as excinfo:
        resolve_youtube_stream(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            resolver=lambda url: YouTubeStream("https://media.test/a", url),
        )
    assert "Safe Mode" in str(excinfo.value)


def test_ensure_and_resolve_installs_only_when_yt_dlp_is_missing(monkeypatch) -> None:
    calls: list[str] = []

    def installer(_progress) -> None:
        calls.append("installed")

    monkeypatch.setattr("quill.core.radio.youtube.youtube_available", lambda: False)
    stream = ensure_and_resolve(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        installer=installer,
        resolver=lambda url: YouTubeStream("https://media.test/a", url),
    )
    assert stream.stream_url == "https://media.test/a"
    # An injected resolver means the real yt-dlp is not needed, so no install runs.
    assert calls == []


def test_ensure_and_resolve_reports_a_failed_install_clearly(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.radio.youtube.youtube_available", lambda: False)

    def installer(_progress) -> None:
        raise RuntimeError("pip said no")

    with pytest.raises(YouTubeError) as excinfo:
        ensure_and_resolve("https://www.youtube.com/watch?v=dQw4w9WgXcQ", installer=installer)
    assert "yt-dlp" in str(excinfo.value)


def test_best_audio_prefers_an_audio_only_format() -> None:
    info = {
        "formats": [
            {"url": "https://media.test/video", "vcodec": "avc1", "acodec": "mp4a", "tbr": 900},
            {"url": "https://media.test/audio-low", "vcodec": "none", "acodec": "opus", "abr": 64},
            {
                "url": "https://media.test/audio-high",
                "vcodec": "none",
                "acodec": "opus",
                "abr": 160,
            },
        ]
    }
    assert _best_audio_url(info) == "https://media.test/audio-high"


def test_best_audio_falls_back_to_a_combined_stream_for_live_hls() -> None:
    # A live broadcast is often one audio+video HLS manifest; refusing it would
    # mean live stations never play, which is the whole point of the feature.
    info = {
        "formats": [{"url": "https://media.test/live.m3u8", "vcodec": "avc1", "acodec": "mp4a"}]
    }
    assert _best_audio_url(info) == "https://media.test/live.m3u8"
