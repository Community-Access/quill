"""Saved YouTube playlists and videos: the pasted link's way in (QA item).

Isolation: each test hands the store its own tmp directory.
"""

from __future__ import annotations

import pytest

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
