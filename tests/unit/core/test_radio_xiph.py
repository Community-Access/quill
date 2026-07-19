# ruff: noqa: E501 - HTML fixtures below have long, unbreakable stream-URL lines
from __future__ import annotations

import pytest

import quill.core.radio.xiph as xiph
from quill.core.radio.xiph import (
    CATEGORY_LABEL,
    XiphError,
    fetch_genre_stations,
    fetch_genres,
    genre_display,
    parse_genres,
    parse_stations,
    refuse_in_safe_mode,
)

_GENRES_HTML = """
<a href="/genres/Jazz">Jazz</a>
<a href="/genres/jazz" class="badge">jazz</a>
<a href="/genres/80s">80s</a>
<a href="/genres/Pop">Pop</a>
"""

_GENRE_PAGE = """
<h2>Streams</h2>
<div class="card shadow-sm mt-3">
    <div class="card-body">
        <h5 class="card-title">SatinJazz</h5>
        <h6 class="card-subtitle mb-2 text-muted">On Air: Clare Teal</h6>
        <p class="card-text">Great women jazz vocalists</p>
    </div>
    <div class="card-footer d-block text-muted">
        31 Listeners &mdash;
        <a href="/genres/jazz" class="badge badge-secondary">jazz</a> &mdash;
        <a href="/codecs/MP3" class="badge badge-primary">MP3</a>
        <div class="d-inline-block float-right">
            <a href="http://quincy.torontocast.com:2720/stream" class="btn btn-sm btn-primary">Play</a>
        </div>
    </div>
</div>
<div class="card shadow-sm mt-3">
    <div class="card-body">
        <h5 class="card-title">Mother Earth &amp; Radio</h5>
    </div>
    <div class="card-footer">
        <a href="/codecs/OGG" class="badge badge-primary">OGG</a>
        <a href="https://stream.motherearthradio.de/listen/x/radio.ogg" class="btn btn-sm btn-primary">Play</a>
    </div>
</div>
"""


def test_parse_genres_dedups_case_insensitively_and_sorts() -> None:
    assert parse_genres(_GENRES_HTML) == ["80s", "Jazz", "Pop"]  # jazz/Jazz collapsed


def test_genre_display() -> None:
    assert genre_display("jazz") == "Jazz"
    assert genre_display("80s") == "80s"  # digits left alone
    assert genre_display("MP3") == "MP3"


def test_parse_stations_extracts_title_url_codec_and_unescapes() -> None:
    stations = parse_stations(_GENRE_PAGE)
    assert [s.name for s in stations] == ["SatinJazz", "Mother Earth & Radio"]
    assert stations[0].stream_url == "http://quincy.torontocast.com:2720/stream"
    assert stations[0].codec == "MP3"
    assert stations[0].source == CATEGORY_LABEL and CATEGORY_LABEL in stations[0].tags
    assert stations[1].stream_url.endswith("radio.ogg")


def test_parse_stations_tolerates_junk() -> None:
    assert parse_stations("<html>no cards here</html>") == []


def test_fetch_genre_stations_uses_fetch(monkeypatch) -> None:
    monkeypatch.setattr(xiph, "_fetch", lambda url: _GENRE_PAGE)
    stations = fetch_genre_stations("jazz")
    assert len(stations) == 2


def test_fetch_genres_returns_empty_on_error(monkeypatch) -> None:
    def boom(url):
        raise XiphError("offline")

    monkeypatch.setattr(xiph, "_fetch", boom)
    assert fetch_genres() == []


def test_fetch_genre_stations_empty_genre() -> None:
    assert fetch_genre_stations("   ") == []


def test_safe_mode_refuses() -> None:
    with pytest.raises(XiphError):
        refuse_in_safe_mode(True)
    with pytest.raises(XiphError):
        fetch_genres(safe_mode=True)
    with pytest.raises(XiphError):
        fetch_genre_stations("jazz", safe_mode=True)
