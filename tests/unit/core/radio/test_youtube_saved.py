"""Saved YouTube playlists and videos: the pasted link's way in (QA item).

Isolation: each test hands the store its own tmp directory.
"""

from __future__ import annotations

import pytest

from quill.core.radio import youtube_saved
from quill.core.radio.youtube_saved import (
    PLAYLIST,
    VIDEO,
    SavedStore,
    classify_link,
    normalize_playlist_url,
    normalize_video_url,
)

# --- URL reading ----------------------------------------------------------------


def test_a_playlist_link_normalizes_to_its_canonical_form() -> None:
    wanted = "https://www.youtube.com/playlist?list=PL123abc"
    assert normalize_playlist_url("https://www.youtube.com/playlist?list=PL123abc") == wanted
    assert normalize_playlist_url("http://m.youtube.com/playlist?list=PL123abc&si=xyz") == wanted
    # Saving a playlist is explicit, so a watch link carrying list= means the
    # playlist here (unlike playback, where it means the video).
    assert (
        normalize_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123abc")
        == wanted
    )


def test_non_playlists_are_refused() -> None:
    assert normalize_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == ""
    assert normalize_playlist_url("https://example.com/playlist?list=PL1") == ""
    assert normalize_playlist_url("not a url") == ""


def test_a_video_link_normalizes_to_a_watch_url() -> None:
    wanted = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert normalize_video_url("https://youtu.be/dQw4w9WgXcQ?t=42") == wanted
    assert normalize_video_url("https://www.youtube.com/shorts/dQw4w9WgXcQ") == wanted
    assert normalize_video_url("https://www.youtube.com/@name") == ""  # a channel, not a video


def test_classify_link_places_each_shape() -> None:
    assert classify_link("https://www.youtube.com/playlist?list=PL1x")[0] == PLAYLIST
    assert classify_link("https://youtu.be/dQw4w9WgXcQ")[0] == VIDEO
    assert classify_link("https://www.youtube.com/@name") == (
        "channel",
        "https://www.youtube.com/@name",
    )
    # @name/live names the broadcast, not the channel.
    assert classify_link("https://www.youtube.com/@name/live")[0] == VIDEO
    assert classify_link("https://example.com/") == ("", "")


# --- the store ------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    return SavedStore(tmp_path)


def test_add_normalizes_dedupes_and_persists(store) -> None:
    first = store.add(VIDEO, "https://youtu.be/dQw4w9WgXcQ")
    again = store.add(VIDEO, "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=9")
    assert first is not None
    assert again == first  # same canonical URL: stored once
    assert [i.url for i in store.all(VIDEO)] == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]


def test_add_refuses_a_link_of_the_wrong_kind(store) -> None:
    assert store.add(PLAYLIST, "https://youtu.be/dQw4w9WgXcQ") is None
    assert store.all() == []


def test_remove_by_url(store) -> None:
    store.add(PLAYLIST, "https://www.youtube.com/playlist?list=PL1x")
    store.remove("https://www.youtube.com/playlist?list=PL1x")
    assert store.all() == []


def test_kinds_list_separately(store) -> None:
    store.add(PLAYLIST, "https://www.youtube.com/playlist?list=PL1x")
    store.add(VIDEO, "https://youtu.be/dQw4w9WgXcQ")
    assert len(store.all()) == 2
    assert [i.kind for i in store.all(PLAYLIST)] == [PLAYLIST]
    assert [i.kind for i in store.all(VIDEO)] == [VIDEO]


# --- a saved row carries the video's facts, not its address --------------------


class _Stream:
    """Stands in for a resolved YouTubeStream."""

    def __init__(self, **facts: object) -> None:
        self.title = facts.get("title", "")
        self.uploader = facts.get("uploader", "")
        self.description = facts.get("description", "")
        self.duration_ms = facts.get("duration_ms", 0)
        self.is_live = facts.get("is_live", False)


def test_details_from_a_resolved_stream_are_what_the_row_shows() -> None:
    item = youtube_saved.details_from_stream(
        "https://www.youtube.com/watch?v=iG9CE55wbtY",
        _Stream(
            title="Do schools kill creativity?",
            uploader="TED",
            duration_ms=1_203_000,
            description="Sir Ken Robinson makes an entertaining case...",
        ),
    )

    assert item.display_name == "Do schools kill creativity?"
    assert item.note == "TED, 20 minutes 3 seconds"
    assert item.description.startswith("Sir Ken Robinson")


def test_a_live_broadcast_reports_no_length_because_it_has_none() -> None:
    item = youtube_saved.details_from_stream(
        "https://www.youtube.com/@example/live",
        _Stream(title="Evening News", uploader="Example TV", is_live=True, duration_ms=9999),
    )

    assert item.is_live is True
    assert item.duration_ms == 0  # a broadcast has no timeline to claim
    assert item.note == "Example TV, live"


def test_a_description_is_tidied_and_capped() -> None:
    padded = "First line.\n\n\n\n   \nSecond line.   \n"
    assert youtube_saved.clean_description(padded) == "First line.\n\nSecond line."

    long_text = "x" * (youtube_saved.DESCRIPTION_LIMIT + 500)
    capped = youtube_saved.clean_description(long_text)
    assert len(capped) == youtube_saved.DESCRIPTION_LIMIT + 3
    assert capped.endswith("...")


def test_describe_fills_a_saved_row_in_place(tmp_path) -> None:
    store = youtube_saved.SavedStore(tmp_path)
    url = "https://www.youtube.com/watch?v=iG9CE55wbtY"
    store.add(youtube_saved.PLAYLIST, "https://www.youtube.com/playlist?list=PL1")
    store.add(youtube_saved.VIDEO, url)

    updated = store.describe(
        youtube_saved.SavedItem(
            kind=youtube_saved.VIDEO,
            url=url,
            name="Do schools kill creativity?",
            uploader="TED",
            duration_ms=1_203_000,
            description="notes",
        )
    )

    assert updated is not None and updated.name == "Do schools kill creativity?"
    stored = store.all(youtube_saved.VIDEO)
    assert [i.name for i in stored] == ["Do schools kill creativity?"]
    assert stored[0].description == "notes"
    # Order is preserved: the playlist added first is still first overall.
    assert [i.kind for i in store.all()] == [youtube_saved.PLAYLIST, youtube_saved.VIDEO]


def test_describing_a_row_that_was_removed_does_not_resurrect_it(tmp_path) -> None:
    store = youtube_saved.SavedStore(tmp_path)
    url = "https://www.youtube.com/watch?v=iG9CE55wbtY"

    assert (
        store.describe(youtube_saved.SavedItem(kind=youtube_saved.VIDEO, url=url, name="x")) is None
    )
    assert store.all() == []


def test_stored_facts_survive_a_round_trip(tmp_path) -> None:
    store = youtube_saved.SavedStore(tmp_path)
    url = "https://www.youtube.com/watch?v=iG9CE55wbtY"
    store.add(youtube_saved.VIDEO, url)
    store.describe(
        youtube_saved.SavedItem(
            kind=youtube_saved.VIDEO, url=url, name="Title", uploader="TED", duration_ms=60_000
        )
    )

    reread = youtube_saved.SavedStore(tmp_path).all(youtube_saved.VIDEO)[0]
    assert (reread.name, reread.uploader, reread.duration_ms) == ("Title", "TED", 60_000)


def test_a_row_written_before_the_facts_existed_still_reads(tmp_path) -> None:
    """Back-compat: the old file had only kind/url/name."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        tmp_path / "radio-youtube-saved.json",
        [{"kind": "video", "url": "https://youtu.be/abc", "name": ""}],
    )

    item = youtube_saved.SavedStore(tmp_path).all()[0]
    assert item.display_name == "https://youtu.be/abc"
    assert item.note == ""
