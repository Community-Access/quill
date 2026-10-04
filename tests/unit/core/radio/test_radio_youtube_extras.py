"""Filtered search and YouTube Music, SponsorBlock, video details, Shorts/History, row verbs."""

from __future__ import annotations

import json
import urllib.parse

import pytest

from quill.core.radio import browse_youtube_extra as extra
from quill.core.radio import browse_youtube_more as more
from quill.core.radio import youtube_search_filters as sf
from quill.core.radio import youtube_sponsorblock as sb
from quill.core.radio import youtube_video_info as vi

# -- search filters ----------------------------------------------------------------


def test_filter_encoder_matches_youtubes_own_values() -> None:
    assert sf.sp_value(sf.Filters()) == "EgIQAQ%3D%3D"  # videos, as Search YouTube uses
    assert sf.sp_value(sf.Filters(kind="channel")) == "EgIQAg%3D%3D"
    assert sf.sp_value(sf.Filters(kind="playlist")) == "EgIQAw%3D%3D"
    assert sf.sp_value(sf.Filters(sort=2)) == "CAISAhAB"  # upload date, videos


def test_combined_filters_decode_to_the_right_fields() -> None:
    import base64

    value = urllib.parse.unquote(sf.sp_value(sf.Filters(sort=3, upload_date=3, duration=2)))
    raw = base64.b64decode(value)
    assert raw == bytes([0x08, 3, 0x12, 6, 0x08, 3, 0x10, 1, 0x18, 2])


def test_live_now_sets_the_live_feature() -> None:
    value = urllib.parse.unquote(sf.sp_value(sf.Filters(kind=sf.LIVE)))
    import base64

    assert base64.b64decode(value).endswith(b"\x40\x01")


def test_music_search_uses_youtube_music_songs() -> None:
    url = sf.search_url("blue in green", sf.Filters(source=sf.MUSIC))
    assert url == "https://music.youtube.com/search?q=blue+in+green#songs"


def test_filtered_search_asks_one_flat_request() -> None:
    asked: list = []

    def fetch(target, options):
        asked.append((target, dict(options)))
        return {"entries": [{"id": "abcdefghijk", "title": "A", "duration": 125}]}

    found = sf.search("walks", sf.Filters(upload_date=2), fetch=fetch)
    assert len(asked) == 1 and "sp=" in asked[0][0]
    assert asked[0][1]["extract_flat"] == "in_playlist"
    assert found[0].title == "A"
    assert sf.summary(1, sf.Filters(upload_date=2)) == "1 video found, videos, today."


# -- SponsorBlock -------------------------------------------------------------------


def test_request_carries_only_a_hash_prefix() -> None:
    url = sb.request_url("dQw4w9WgXcQ", ("sponsor",))
    assert "dQw4w9WgXcQ" not in url
    assert url.startswith(f"{sb.API_URL}/{sb.hash_prefix('dQw4w9WgXcQ')}?")
    assert len(sb.hash_prefix("dQw4w9WgXcQ")) == 4


def test_segments_for_the_right_video_only() -> None:
    payload = [
        {"videoID": "other", "segments": [{"segment": [1, 20], "category": "sponsor"}]},
        {
            "videoID": "mine",
            "segments": [
                {"segment": [30.0, 60.0], "category": "sponsor", "actionType": "skip"},
                {"segment": [5.0, 5.4], "category": "intro"},  # too short to matter
            ],
        },
    ]
    assert sb.parse_segments(payload, "mine") == [sb.Segment(30.0, 60.0, "sponsor")]


def test_fetch_treats_404_as_nothing_marked() -> None:
    assert sb.fetch_segments("vid", ("sponsor",), getter=lambda _u: (404, b"")) == []
    body = json.dumps([{"videoID": "vid", "segments": [{"segment": [0, 10], "category": "intro"}]}])
    got = sb.fetch_segments("vid", ("intro",), getter=lambda _u: (200, body.encode()))
    assert got == [sb.Segment(0.0, 10.0, "intro")]


def test_each_segment_is_skipped_once() -> None:
    skipper = sb.Skipper([sb.Segment(10.0, 20.0, "sponsor")])
    assert skipper.check(5.0) is None
    hit = skipper.check(12.0)
    assert hit is not None and sb.spoken(hit) == "Skipped a sponsor segment."
    assert skipper.check(12.0) is None  # going back in on purpose is respected


def test_settings_are_off_by_default_and_round_trip(tmp_path) -> None:
    assert sb.load(tmp_path) == sb.SkipSettings()
    assert not sb.load(tmp_path).enabled
    sb.save(sb.SkipSettings(True, ("intro",)), tmp_path)
    assert sb.load(tmp_path) == sb.SkipSettings(True, ("intro",))


def test_safe_mode_refuses(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(sb.SponsorBlockError):
        sb.fetch_segments("vid", ("sponsor",), getter=lambda _u: (200, b"[]"))


# -- video details --------------------------------------------------------------------


def test_moments_come_out_of_the_description() -> None:
    found = vi.moments_in("Intro 0:00\n12:40 - The interview\n1:02:03 Q and A\nprice 3:5")
    assert [(m.seconds, m.label, m.clock) for m in found] == [
        (0, "Intro", "0:00"),
        (760, "The interview", "12:40"),
        (3723, "Q and A", "1:02:03"),
    ]


def test_premiere_countdown_and_states() -> None:
    assert vi.countdown(1000 + 7500, now=1000) == "Starts in 2 hours 5 minutes."
    assert vi.countdown(1030, now=1000) == "Starting any moment now."
    upcoming = vi.parse_info({"live_status": "is_upcoming", "release_timestamp": 4600})
    assert vi.state_sentence(upcoming, now=1000) == "Starts in 1 hour."
    assert vi.state_sentence(vi.parse_info({"live_status": "is_live"})) == "Live now."


def test_fetch_video_asks_for_details_only() -> None:
    asked: list = []

    def fetch(target, options):
        asked.append(dict(options))
        return {"id": "v", "title": "T", "channel": "C", "description": "0:30 Start"}

    info = vi.fetch_video("https://www.youtube.com/watch?v=abcdefghijk", fetch=fetch)
    assert info.channel == "C" and info.moments[0].seconds == 30
    assert asked[0]["noplaylist"] is True


def test_about_text() -> None:
    text = vi.about_text({
        "channel": "Rick",
        "channel_follower_count": 1_200_000,
        "uploader_id": "@rick",
    })
    assert text.splitlines()[:3] == ["Rick", "1.2 million subscribers.", "Handle: @rick"]


# -- Shorts and History -----------------------------------------------------------------


def test_channel_lists_shorts_and_shorts_open(monkeypatch) -> None:
    asked: list[str] = []

    def fetch(target, options):
        asked.append(target)
        return {
            "entries": [
                {
                    "id": "abcdefghijk",
                    "title": "A short",
                    "url": "https://www.youtube.com/shorts/abcdefghijk",
                }
            ]
        }

    monkeypatch.setattr(more, "FETCH", fetch)
    monkeypatch.setattr("quill.core.radio.youtube_channels.playlists", lambda *_a, **_k: [])
    labels = [
        node.label for node in more.browse_channel(["https://www.youtube.com/@x"], safe_mode=False)
    ]
    assert labels == ["Uploads", "Live", "Shorts"]
    rows = extra.browse_shorts(["https://www.youtube.com/@x"], safe_mode=False)
    assert asked[-1].endswith("/shorts") and rows[0].label == "A short"


def test_history_only_when_signed_in(monkeypatch) -> None:
    monkeypatch.setattr(more, "_signed_in", lambda _s: False)
    assert extra.browse_history([], safe_mode=False) == []
    asked: list[str] = []
    monkeypatch.setattr(more, "_signed_in", lambda _s: True)
    monkeypatch.setattr(more, "FETCH", lambda t, o: asked.append(t) or {"entries": []})
    assert extra.browse_history(["1"], safe_mode=False) == []
    assert asked == [":ythis"]
    assert "History" in [n.label for n in more.browse_my_youtube([], safe_mode=False)]


# -- row verbs ------------------------------------------------------------------------


def test_video_row_offers_chat_and_video_window_with_free_letters() -> None:
    from quill.core.radio import row_actions as ra
    from quill.core.radio.models import RadioStation

    station = RadioStation(name="x", stream_url="https://www.youtube.com/watch?v=abcdefghijk")
    actions = ra.actions_for(
        "ytvideo", station=station, playing=True, saved=True, can_download=True
    )
    labels = [a.label for a in actions]
    assert "Live C&hat..." in labels and "&YouTube Video..." in labels
    letters = [label[label.index("&") + 1].lower() for label in labels if "&" in label]
    assert letters.count("h") == 1 and letters.count("y") == 1


def test_channel_row_offers_about() -> None:
    from quill.core.radio import row_actions as ra

    labels = [
        a.label for a in ra.actions_for("ytchannel", is_folder=True, folder_state=ra.FolderState())
    ]
    assert "Abou&t This Channel..." in labels
    letters = [label[label.index("&") + 1].lower() for label in labels]
    assert len(letters) == len(set(letters))
