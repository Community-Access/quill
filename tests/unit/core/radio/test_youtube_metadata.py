"""Tests for the YouTube metadata that was previously fetched and discarded.

Every field here comes out of the *same* yt-dlp response that already produced
the stream URL, so capturing it costs no extra network call. The parsers are
pure, so these tests never touch YouTube.
"""

# pick_caption_track moved to core/radio/captions.py under GATE-11; the
# decision it makes is unchanged.
from quill.core.radio.captions import pick_caption_track
from quill.core.radio.youtube import (
    YouTubeChapter,
    is_youtube_playlist_url,
    parse_chapters,
    playlist_entries_from_info,
    stream_from_info,
)

VIDEO_INFO: dict[str, object] = {
    "url": "https://media.example/audio.m4a",
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "A Talk About Gardening",
    "is_live": False,
    "duration": 3725.4,
    "uploader": "Garden Channel",
    "description": "All about compost.",
    "chapters": [
        {"start_time": 0, "title": "Intro"},
        {"start_time": 600.5, "title": "Composting"},
    ],
    "subtitles": {"en": [{"ext": "vtt", "url": "https://captions.example/en.vtt"}]},
}

LIVE_INFO: dict[str, object] = {
    "url": "https://media.example/live.m3u8",
    "webpage_url": "https://www.youtube.com/watch?v=live1234567",
    "title": "Live Right Now",
    "is_live": True,
}


# -- duration ------------------------------------------------------------------


def test_a_finished_video_reports_its_duration() -> None:
    """Duration is what makes a video seekable rather than a live station."""
    assert stream_from_info(VIDEO_INFO, "").duration_ms == 3_725_400


def test_a_live_broadcast_reports_no_duration() -> None:
    """0 is honest: a live stream has no timeline to scrub."""
    stream = stream_from_info(LIVE_INFO, "")
    assert stream.is_live is True
    assert stream.duration_ms == 0


def test_a_nonsense_duration_is_treated_as_none() -> None:
    for value in (None, "abc", -5, True):
        assert stream_from_info({**VIDEO_INFO, "duration": value}, "").duration_ms == 0


# -- chapters ------------------------------------------------------------------


def test_youtube_chapters_are_captured_in_order() -> None:
    chapters = parse_chapters(VIDEO_INFO)
    assert chapters == (
        YouTubeChapter(0, "Intro"),
        YouTubeChapter(600_500, "Composting"),
    )


def test_chapters_are_sorted_even_if_the_feed_is_not() -> None:
    info = {
        "chapters": [{"start_time": 90, "title": "Second"}, {"start_time": 5, "title": "First"}]
    }
    assert [c.title for c in parse_chapters(info)] == ["First", "Second"]


def test_untitled_or_negative_chapters_are_dropped() -> None:
    info = {
        "chapters": [
            {"start_time": 10, "title": ""},
            {"start_time": -3, "title": "Before the start"},
            {"start_time": 20, "title": "Keep"},
        ]
    }
    assert [c.title for c in parse_chapters(info)] == ["Keep"]


def test_a_video_without_chapters_yields_none() -> None:
    assert parse_chapters({}) == ()
    assert parse_chapters({"chapters": "nonsense"}) == ()


# -- captions ------------------------------------------------------------------


def test_a_human_written_track_is_preferred_over_an_automatic_one() -> None:
    info = {
        "subtitles": {"en": [{"ext": "vtt", "url": "https://c.example/human.vtt"}]},
        "automatic_captions": {"en": [{"ext": "vtt", "url": "https://c.example/auto.vtt"}]},
    }
    url, automatic = pick_caption_track(info)
    assert url == "https://c.example/human.vtt"
    assert automatic is False


def test_automatic_captions_are_used_when_there_is_nothing_else() -> None:
    info = {"automatic_captions": {"en": [{"ext": "vtt", "url": "https://c.example/auto.vtt"}]}}
    url, automatic = pick_caption_track(info)
    assert url == "https://c.example/auto.vtt"
    assert automatic is True


def test_only_timed_caption_formats_are_accepted() -> None:
    """A plain-text dump has no positions, so it is useless for seeking."""
    info = {"subtitles": {"en": [{"ext": "txt", "url": "https://c.example/plain.txt"}]}}
    assert pick_caption_track(info) == ("", False)


def test_a_non_https_caption_url_is_refused() -> None:
    info = {"subtitles": {"en": [{"ext": "vtt", "url": "http://c.example/insecure.vtt"}]}}
    assert pick_caption_track(info) == ("", False)


def test_a_video_with_no_captions_reports_none_rather_than_failing() -> None:
    assert pick_caption_track({}) == ("", False)
    assert pick_caption_track({"subtitles": {}}) == ("", False)


def test_the_stream_carries_the_caption_track_it_picked() -> None:
    stream = stream_from_info(VIDEO_INFO, "")
    assert stream.caption_url == "https://captions.example/en.vtt"
    assert stream.caption_is_automatic is False


# -- the rest of the metadata --------------------------------------------------


def test_uploader_and_description_are_captured() -> None:
    stream = stream_from_info(VIDEO_INFO, "")
    assert stream.uploader == "Garden Channel"
    assert stream.description == "All about compost."


def test_channel_is_used_when_there_is_no_uploader() -> None:
    stream = stream_from_info({**VIDEO_INFO, "uploader": None, "channel": "The Channel"}, "")
    assert stream.uploader == "The Channel"


# -- playlists -----------------------------------------------------------------


def test_a_playlist_link_is_recognised() -> None:
    assert is_youtube_playlist_url("https://www.youtube.com/playlist?list=PL123") is True


def test_a_watch_link_carrying_a_list_is_not_treated_as_a_playlist() -> None:
    """The listener asked for that video; expanding it into fifty would surprise."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123"
    assert is_youtube_playlist_url(url) is False


def test_non_youtube_and_malformed_links_are_not_playlists() -> None:
    assert is_youtube_playlist_url("https://example.com/playlist?list=PL1") is False
    assert is_youtube_playlist_url("not a url") is False
    assert is_youtube_playlist_url("") is False


def test_playlist_entries_keep_the_uploaders_running_order() -> None:
    info = {
        "entries": [
            {"id": "aaaaaaaaaaa", "title": "First", "duration": 60},
            {"id": "bbbbbbbbbbb", "title": "Second", "duration": 120},
        ]
    }
    entries = playlist_entries_from_info(info)
    assert [e.title for e in entries] == ["First", "Second"]
    assert entries[0].page_url == "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    assert entries[1].duration_ms == 120_000


def test_playlist_entries_prefer_an_explicit_page_url() -> None:
    info = {"entries": [{"id": "aaaaaaaaaaa", "webpage_url": "https://youtu.be/aaaaaaaaaaa"}]}
    assert playlist_entries_from_info(info)[0].page_url == "https://youtu.be/aaaaaaaaaaa"


def test_playlist_entries_without_a_usable_link_are_dropped() -> None:
    """Better to omit an item than offer one that cannot play."""
    info = {"entries": [{"title": "No link at all"}, {"id": "bbbbbbbbbbb", "title": "Fine"}]}
    entries = playlist_entries_from_info(info)
    assert [e.title for e in entries] == ["Fine"]


def test_a_non_playlist_result_yields_no_entries() -> None:
    assert playlist_entries_from_info({}) == ()
    assert playlist_entries_from_info({"entries": "nonsense"}) == ()


def test_playlist_title_comes_back_with_the_entries() -> None:
    # The playlist's own name rides along in the same flat listing, so heading
    # the picker with it costs nothing -- and the raw "playlist?list=PL..."
    # address tells a listener nothing about what they are looking at.
    from quill.core.radio.youtube import (
        resolve_youtube_playlist_details,
    )

    info = {
        "title": "Essence of linear algebra",
        "entries": [
            {"id": "aaaaaaaaaaa", "title": "Vectors", "duration": 600, "uploader": "3Blue1Brown"}
        ],
    }
    title, entries = resolve_youtube_playlist_details(
        "https://www.youtube.com/playlist?list=PL123", resolver=lambda _u: info
    )
    assert title == "Essence of linear algebra"
    assert [e.title for e in entries] == ["Vectors"]


def test_playlist_title_falls_back_and_then_gives_up() -> None:
    from quill.core.radio.youtube import playlist_title_from_info

    assert playlist_title_from_info({"playlist_title": "Mixes"}) == "Mixes"
    assert playlist_title_from_info({"channel": "3Blue1Brown"}) == "3Blue1Brown"
    assert playlist_title_from_info({"title": "   "}) == ""
    assert playlist_title_from_info({}) == ""


def test_resolve_youtube_playlist_still_returns_entries_only() -> None:
    # The narrower name is kept for callers that do not want the title.
    from quill.core.radio.youtube import resolve_youtube_playlist

    entries = resolve_youtube_playlist(
        "https://www.youtube.com/playlist?list=PL123",
        resolver=lambda _u: {"title": "x", "entries": [{"id": "bbbbbbbbbbb", "title": "One"}]},
    )
    assert [e.title for e in entries] == ["One"]
