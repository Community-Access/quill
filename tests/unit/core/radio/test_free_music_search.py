"""Searching Audius, Mixcloud and ccMixter -- which all three could do all along.

These three were listed as *unsearchable* through a whole release: the browse
tree offered trending, categories and tags, and the code recorded that as "this
source cannot be searched". All three publish a keyword search, verified against
the live services on 2026-08-14. The browse shelves were good shelves, not a
limit -- and saying "this cannot be searched" about somebody else's product,
in the release notes and in the app, was a confident wrong answer.

Parsing is unchanged: a search result and a trending result are the same object
from the same service, which is why this was one URL away.
"""

from __future__ import annotations

import json

import pytest

from quill.core.radio import free_music
from quill.core.radio.free_music import (
    FreeMusicError,
    audius_search,
    ccmixter_search,
    mixcloud_search,
)

_AUDIUS = json.dumps({
    "data": [
        {
            "id": "abc123",
            "title": "Breaking Jazz",
            "user": {"name": "Ljazz"},
            "permalink": "/ljazz/breaking-jazz",
            "is_streamable": True,
        }
    ]
})

_CCMIXTER = json.dumps([
    {
        "upload_name": "Xtended Chords",
        "user_name": "Javolenus",
        "license_name": "Attribution Noncommercial (4.0)",
        "file_page_url": "https://ccmixter.org/files/Javolenus/1",
        "files": [{"download_url": "https://ccmixter.org/content/x.mp3"}],
    }
])

_MIXCLOUD = json.dumps({
    "data": [{"name": "Smooth Jazz Mix", "url": "https://www.mixcloud.com/dj/smooth-jazz/"}]
})


@pytest.fixture
def offline(monkeypatch):
    """Serve a canned payload and record the URL, so no test touches the network."""
    seen: list[str] = []

    def _fake(url: str) -> str:
        seen.append(url)
        if "audius" in url:
            return _AUDIUS
        if "ccmixter" in url:
            return _CCMIXTER
        return _MIXCLOUD

    monkeypatch.setattr(free_music, "_fetch", _fake)
    # The directory cache would answer from disk and never call the fetch.
    monkeypatch.setattr(free_music, "_cached", lambda _key, build, **_kw: build())
    return seen


def test_audius_can_be_searched(offline) -> None:
    rows = audius_search("jazz")
    assert [row.name for row in rows] == ["Breaking Jazz -- Ljazz"]
    assert rows[0].source == "Audius"
    # A track resolves to a real stream, so it plays here rather than in a browser.
    assert rows[0].is_recording is True
    assert "/v1/tracks/search?" in offline[0]
    assert "query=jazz" in offline[0]


def test_ccmixter_can_be_searched_and_keeps_its_licence(offline) -> None:
    rows = ccmixter_search("jazz")
    assert rows[0].name == "Xtended Chords -- Javolenus"
    # For Creative Commons material, showing the terms is the whole courtesy.
    assert rows[0].tags == ("Attribution Noncommercial (4.0)",)
    assert "search=jazz" in offline[0]


def test_ccmixter_search_uses_the_same_endpoint_as_its_tag_folders(offline) -> None:
    # One parameter apart the whole time: `search` instead of `tags`.
    ccmixter_search("jazz")
    assert "/api/query?" in offline[0]
    assert "tags=" not in offline[0]


def test_ccmixters_page_ceiling_still_applies(offline) -> None:
    # Not a preference: ccMixter echoes the result into an HTTP header, and a
    # larger page produces a header line over the 64 KB the standard library
    # accepts, killing the request before the body is read.
    ccmixter_search("jazz", limit=500)
    assert f"limit={free_music.CCMIXTER_MAX_LIMIT}" in offline[0]


def test_mixcloud_can_be_searched_but_is_still_metadata_only(offline) -> None:
    rows = mixcloud_search("jazz")
    assert rows[0].name == "Smooth Jazz Mix"
    # Mode A is unchanged by search: no stream URL is ever extracted, so the row
    # is the show's page and opening it hands over to the browser. Searching
    # changes how a row is found, not what it is.
    assert rows[0].is_recording is False
    assert rows[0].stream_url.startswith("https://www.mixcloud.com/")
    assert "/search/?" in offline[0]
    assert "type=cloudcast" in offline[0]


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_an_empty_query_never_reaches_the_network(blank: str, offline) -> None:
    assert audius_search(blank) == []
    assert ccmixter_search(blank) == []
    assert mixcloud_search(blank) == []
    assert offline == []


@pytest.mark.parametrize("search", [audius_search, ccmixter_search, mixcloud_search])
def test_safe_mode_refuses_before_asking(search, offline) -> None:
    with pytest.raises(FreeMusicError):
        search("jazz", safe_mode=True)
    assert offline == []
