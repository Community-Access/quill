"""Search YouTube: videos, playlists and channels, each row saying which.

Recorded flat listings in the shape yt-dlp's YoutubeSearchURL extractor returns
(``_extract_video``, ``_extract_lockup_view_model``, ``_extract_channel_renderer``)
-- no network anywhere.
"""

from __future__ import annotations

import pytest

from quill.core.radio import youtube_search as ys
from quill.core.radio.browse_nodes import split_id
from quill.core.radio.youtube_requests import YouTubeRequestError

VIDEOS = {
    "entries": [
        {
            "_type": "url",
            "id": "abcdefghijk",
            "url": "https://www.youtube.com/watch?v=abcdefghijk",
            "title": "Bristol walking tour",
            "duration": 731,
            "channel": "Rick Steves",
            "uploader": "Rick Steves",
        },
        {
            "_type": "url",
            "id": "lmnopqrstuv",
            "url": "https://www.youtube.com/watch?v=lmnopqrstuv",
            "title": "Harbourside live cam",
            "live_status": "is_live",
            "uploader": "Bristol Live",
        },
        # A channel the video filter let through is not a video.
        {"_type": "url", "url": "https://www.youtube.com/channel/UCx", "title": "Odd"},
    ]
}
PLAYLISTS = {
    "entries": [
        {
            "_type": "url",
            "id": "PLabc",
            "url": "https://www.youtube.com/playlist?list=PLabc",
            "title": "Europe Through the Back Door",
            "channel": "Rick Steves",
        },
        {
            "_type": "url",
            "url": "https://www.youtube.com/playlist?list=PLdef",
            "title": "Counted",
            "playlist_count": 40,
            "uploader": "Rick Steves",
        },
    ]
}
CHANNELS = {
    "entries": [
        {
            "_type": "url",
            "id": "UCsteves",
            "url": "https://www.youtube.com/channel/UCsteves",
            "channel_url": "https://www.youtube.com/channel/UCsteves",
            "title": "Rick Steves' Europe",
            "uploader_url": "https://www.youtube.com/@RickSteves",
            "channel_follower_count": 1_234_567,
        }
    ]
}


def _fake(answers: dict[str, dict], seen: list | None = None):
    def fetch(target, options):
        if seen is not None:
            seen.append((target, dict(options)))
        for code, kind in ((ys.TYPE_FILTERS[k], k) for k in ys.TYPE_FILTERS):
            if code in target:
                return answers[kind]
        raise AssertionError(target)

    return fetch


def test_each_type_asks_youtube_with_its_own_filter() -> None:
    assert ys.results_url("bristol walk", ys.VIDEO).endswith(
        "search_query=bristol+walk&sp=EgIQAQ%3D%3D"
    )
    assert ys.results_url("x", ys.CHANNEL).endswith("sp=EgIQAg%3D%3D")
    assert ys.results_url("x", ys.PLAYLIST).endswith("sp=EgIQAw%3D%3D")


def test_videos_parse_with_length_channel_and_live() -> None:
    found = ys.parse_results(VIDEOS, ys.VIDEO)
    assert [r.title for r in found] == ["Bristol walking tour", "Harbourside live cam"]
    assert found[0].duration_ms == 731_000 and found[0].uploader == "Rick Steves"
    assert found[1].is_live


def test_playlists_parse_with_count_only_when_youtube_said() -> None:
    found = ys.parse_results(PLAYLISTS, ys.PLAYLIST)
    assert found[0].video_count == 0 and found[1].video_count == 40


def test_channels_parse_with_handle_and_followers() -> None:
    (channel,) = ys.parse_results(CHANNELS, ys.CHANNEL)
    assert channel.url == "https://www.youtube.com/channel/UCsteves"
    assert channel.handle_url == "https://www.youtube.com/@RickSteves"
    assert channel.followers == 1_234_567


def test_each_row_says_what_it_is_first() -> None:
    video, live = ys.parse_results(VIDEOS, ys.VIDEO)
    assert ys.note_for(video) == "video, 12 minutes, Rick Steves"
    assert ys.note_for(live) == "video, live now, Bristol Live"
    plain, counted = ys.parse_results(PLAYLISTS, ys.PLAYLIST)
    assert ys.note_for(plain) == "playlist, Rick Steves"
    assert ys.note_for(counted) == "playlist, 40 videos, Rick Steves"
    (channel,) = ys.parse_results(CHANNELS, ys.CHANNEL)
    assert ys.note_for(channel) == "channel, 1.2 million subscribers"


def test_short_durations_read_naturally() -> None:
    assert ys.short_duration(45_000) == "45 seconds"
    assert ys.short_duration(60_000) == "1 minute"
    assert ys.short_duration(3_900_000) == "1 hour 5 minutes"
    assert ys.short_duration(7_200_000) == "2 hours"


def test_rows_open_the_way_each_type_should() -> None:
    video = ys.to_node(ys.parse_results(VIDEOS, ys.VIDEO)[0])
    assert video.station is not None and video.station.is_recording
    assert video.station.stream_url.endswith("abcdefghijk")
    playlist = ys.to_node(ys.parse_results(PLAYLISTS, ys.PLAYLIST)[0])
    assert playlist.is_folder
    assert split_id(playlist.node_id) == (
        "youtubevideos",
        ["https://www.youtube.com/playlist?list=PLabc", "1"],
    )
    channel = ys.to_node(ys.parse_results(CHANNELS, ys.CHANNEL)[0])
    kind, args = split_id(channel.node_id)
    assert kind == "ytchannel" and args[1] == "https://www.youtube.com/@RickSteves"


def test_search_merges_the_three_answers_in_type_order() -> None:
    seen: list = []
    found = ys.search(
        "bristol",
        fetch=_fake({ys.VIDEO: VIDEOS, ys.PLAYLIST: PLAYLISTS, ys.CHANNEL: CHANNELS}, seen),
    )
    assert found.counts == {"Video": 2, "Playlist": 2, "Channel": 1}
    assert [n.note.split(",")[0] for n in found.rows] == [
        "video",
        "video",
        "playlist",
        "playlist",
        "channel",
    ]
    assert all(options["extract_flat"] == "in_playlist" for _t, options in seen)
    assert len(seen) == 3


def test_the_count_is_said_once_in_one_sentence() -> None:
    from quill.core.radio import federated_browse

    found = ys.search(
        "bristol", fetch=_fake({ys.VIDEO: VIDEOS, ys.PLAYLIST: PLAYLISTS, ys.CHANNEL: CHANNELS})
    )
    said = federated_browse.describe("bristol", found)
    assert said == "5 found for bristol: 2 videos, 2 playlists, 1 channel."


def test_one_type_failing_keeps_the_others_and_is_named() -> None:
    def fetch(target, options):
        if ys.TYPE_FILTERS[ys.PLAYLIST] in target:
            raise RuntimeError("HTTP Error 500")
        return CHANNELS if ys.TYPE_FILTERS[ys.CHANNEL] in target else VIDEOS

    found = ys.search("bristol", fetch=fetch)
    assert found.counts == {"Video": 2, "Channel": 1}
    assert [label for label, _why in found.failed] == ["YouTube playlists"]


def test_every_type_failing_is_an_error_with_a_plain_reason() -> None:
    def fetch(target, options):
        raise RuntimeError("Unable to download webpage: timed out")

    with pytest.raises(YouTubeRequestError, match="could not be reached"):
        ys.search("bristol", fetch=fetch)


def test_safe_mode_refuses_before_asking() -> None:
    with pytest.raises(YouTubeRequestError):
        ys.search("x", safe_mode=True, fetch=_fake({}))


def test_an_empty_query_asks_nothing() -> None:
    assert ys.search("   ", fetch=_fake({})).total == 0
