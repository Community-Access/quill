"""Live365 link normalization (#1277 follow-up).

A Live365 player/station link (or bare station id) must resolve to the one
canonical playable stream URL, purely from the string -- no network. Anything
that isn't a Live365 reference must pass through untouched.
"""

from __future__ import annotations

import pytest

from quill.core.radio.live365 import (
    live365_station_id,
    live365_stream_url,
    normalize_live365,
)

_CANON = "https://streaming.live365.com/a25891"


@pytest.mark.parametrize(
    "given",
    [
        "https://streaming.live365.com/a25891",  # already the stream (idempotent)
        "http://streaming.live365.com/a25891",  # http -> https
        "http://streaming.live365.com/a25891#.mp3",  # player-hint fragment dropped
        "https://player.live365.com/a25891",  # the web player *page*
        "https://live365.com/station/KHYI-95-3-The-Range-a25891",  # station page slug
        "a25891",  # bare id
        "  https://player.live365.com/a25891  ",  # surrounding whitespace
    ],
)
def test_live365_links_resolve_to_the_canonical_stream(given: str) -> None:
    assert live365_stream_url(given) == _CANON
    assert normalize_live365(given) == _CANON


def test_slug_with_a_digit_run_picks_the_trailing_id() -> None:
    # A name slug that itself contains an a-digit token must not fool the parser;
    # the real id is the trailing one.
    url = "https://live365.com/station/Area-a1970s-Classics-a30553"
    assert live365_station_id(url) == "a30553"
    assert live365_stream_url(url) == "https://streaming.live365.com/a30553"


def test_uppercase_and_varied_length_ids() -> None:
    assert live365_stream_url("https://player.live365.com/A1820") == (
        "https://streaming.live365.com/A1820"
    )
    assert live365_stream_url("https://streaming.live365.com/a551803") == (
        "https://streaming.live365.com/a551803"
    )


@pytest.mark.parametrize(
    "given",
    [
        "https://example.com/stream.mp3",  # unrelated stream
        "https://streaming.example.com/a25891",  # a-id token but not Live365
        "http://tektite.streamguys1.com:5210/live",  # a real non-Live365 custom URL
        "KHYI 95.3 The Range",  # a name, not a link
        "",
        "a12",  # too short to be a station id
    ],
)
def test_non_live365_input_passes_through_untouched(given: str) -> None:
    assert live365_stream_url(given) is None
    assert normalize_live365(given) == given


def test_bare_id_only_expands_when_it_is_the_whole_string() -> None:
    # A bare id is a convenience; an a-id embedded in unrelated prose is not one.
    assert live365_stream_url("a30553") == "https://streaming.live365.com/a30553"
    assert live365_stream_url("call a30553 later") is None
