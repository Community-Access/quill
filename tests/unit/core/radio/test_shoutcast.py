"""Tests for the SHOUTcast directory source -- pure parsers, no network.

Every fixture here is trimmed from a real reply captured on 2026-08-26, which
is why the odd-looking cases are in it: names that collide while ids do not, a
row whose ``Listeners`` is 0 among rows that have an audience, a ``StreamUrl``
of ``null`` and an empty ``IceUrl``, and a non-ASCII station name that a
locale-default decode would mangle.
"""

from __future__ import annotations

import json

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio import shoutcast

# Trimmed from a live /Home/BrowseByGenre reply. Two stations share a name and
# do not share an id, which is why de-duplication is by id.
_GENRE_JSON = json.dumps([
    {
        "ID": 1528122,
        "Name": "JAZZGROOVE.org - The Jazz Groove (East)",
        "Format": "audio/mpeg",
        "Bitrate": 128,
        "Genre": "Jazz",
        "CurrentTrack": "Randy Sandke - Star Crossed Lovers",
        "Listeners": 100,
        "IsRadionomy": False,
        "IceUrl": "",
        "StreamUrl": None,
    },
    {
        "ID": 1528123,
        "Name": "JAZZGROOVE.org - The Jazz Groove (East)",
        "Format": "audio/aacp",
        "Bitrate": 64,
        "Genre": "Jazz",
        "CurrentTrack": "",
        "Listeners": 0,
        "StreamUrl": None,
    },
    {
        "ID": 99999,
        "Name": "Rádio Café Jazz",
        "Format": "audio/mpeg",
        "Bitrate": 192,
        "Genre": "Jazz",
        "CurrentTrack": "Ao vivo",
        "Listeners": 4200,
    },
    # No ID: not a station this app can offer, because the id is the only
    # route to audio here.
    {"Name": "Broken", "Format": "audio/mpeg", "Listeners": 9999},
])

_GENRE_INDEX_HTML = """
<ul>
  <li><a id="genre-90" href="/Genre?name=Adult"
     onclick="loadStationsByGenre('Adult', 90, 89);">Adult</a></li>
  <li><a href="/Genre?name=Hip%20Hop">Hip Hop</a></li>
  <li><a href="/Genre?name=Jazz">Jazz</a></li>
  <li><a href="/Genre?name=jazz">jazz</a></li>
  <li><a href="/Genre?name=R%26B">R&amp;B</a></li>
  <li><a href="/Genre?name=">(nothing)</a></li>
  <li><a href="/Search">Search</a></li>
</ul>
"""


# --- parsing ------------------------------------------------------------------


def test_stations_are_deduped_by_id_not_by_name() -> None:
    stations = shoutcast.parse_stations(_GENRE_JSON)
    # Three usable rows: two share a name, the fourth has no id.
    assert len(stations) == 3
    assert len({station.stream_url for station in stations}) == 3


def test_the_row_with_an_audience_comes_first() -> None:
    """The sort is the point: a genre reply is mostly parked mounts."""
    stations = shoutcast.parse_stations(_GENRE_JSON)
    assert [station.listeners for station in stations] == [4200, 100, 0]


def test_a_non_ascii_name_survives() -> None:
    names = [station.name for station in shoutcast.parse_stations(_GENRE_JSON)]
    assert "Rádio Café Jazz" in names


def test_the_stream_url_is_the_public_tune_in_playlist() -> None:
    station = shoutcast.parse_stations(_GENRE_JSON)[1]
    assert station.stream_url == ("https://yp.shoutcast.com/sbin/tunein-station.pls?id=1528122")


def test_no_station_carries_a_radio_browser_uuid() -> None:
    """station_uuid is Radio Browser's namespace, and register_click() posts
    whatever is in it to Radio Browser."""
    assert all(station.station_uuid == "" for station in shoutcast.parse_stations(_GENRE_JSON))


def test_codec_and_bitrate_are_read_from_the_row() -> None:
    stations = shoutcast.parse_stations(_GENRE_JSON)
    assert shoutcast.codec_of("audio/mpeg") == "MP3"
    assert shoutcast.codec_of("audio/aacp") == "AAC+"
    # An unknown MIME still says something rather than nothing.
    assert shoutcast.codec_of("audio/flac") == "FLAC"
    assert shoutcast.codec_of("") == ""
    assert any(station.bitrate_kbps == 192 for station in stations)


def test_the_current_track_is_a_note_and_never_the_name() -> None:
    station = shoutcast.parse_stations(_GENRE_JSON)[0]
    assert station.notes.startswith("Was playing:")
    assert "Ao vivo" in station.notes
    assert "Ao vivo" not in station.name


def test_garbage_yields_no_stations_rather_than_an_exception() -> None:
    for payload in ("", "not json", "{}", "[1, 2, 3]", "null"):
        assert shoutcast.parse_stations(payload) == []


def test_genres_are_decoded_deduped_and_sorted() -> None:
    genres = shoutcast.parse_genres(_GENRE_INDEX_HTML)
    assert genres == ["Adult", "Hip Hop", "Jazz", "R&B"]


def test_an_empty_index_yields_no_genres() -> None:
    assert shoutcast.parse_genres("<html></html>") == []


# --- Safe Mode ----------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: shoutcast.fetch_genres(safe_mode=True),
        lambda: shoutcast.fetch_genre_stations("Jazz", safe_mode=True),
        lambda: shoutcast.top_stations(safe_mode=True),
    ],
)
def test_safe_mode_refuses_every_network_entry_point(call) -> None:
    with pytest.raises(shoutcast.ShoutcastError):
        call()


def test_search_returns_nothing_in_safe_mode_rather_than_raising() -> None:
    """Search rides along inside a fan-out, so it must never raise into it."""
    assert shoutcast.search_stations("jazz", safe_mode=True) == []


def test_an_empty_query_makes_no_request(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("an empty query must not reach the network")

    monkeypatch.setattr(shoutcast, "_request", _boom)
    assert shoutcast.search_stations("   ") == []


# --- through the browse tree --------------------------------------------------


def test_the_genre_branch_lists_folders_then_stations(monkeypatch) -> None:
    monkeypatch.setattr(shoutcast, "fetch_genres", lambda **_kw: ["Jazz", "Hip Hop"])
    monkeypatch.setattr(
        shoutcast,
        "fetch_genre_stations",
        lambda genre, **_kw: shoutcast.parse_stations(_GENRE_JSON) if genre == "Jazz" else [],
    )
    roots = bs.browse("shoutcast")
    # One SHOUTcast branch, with the live leaderboard pinned above the genres.
    assert [node.label for node in roots] == [
        "Top 500 (most listeners right now)",
        "Jazz",
        "Hip Hop",
    ]
    assert all(node.is_folder for node in roots)
    stations = bs.browse("shoutcast:Jazz")
    assert len(stations) == 3
    assert not stations[0].is_folder


def test_the_top_500_is_a_folder_inside_shoutcast_not_a_second_root(monkeypatch) -> None:
    """Asked for 2026-08-26: one SHOUTcast category, not two."""
    roots = dict(bs.ROOT_SOURCES)
    assert "shoutcasttop" not in roots
    assert roots["shoutcast"] == "SHOUTcast Directory"


def test_the_top_500_branch_is_flat(monkeypatch) -> None:
    monkeypatch.setattr(
        shoutcast, "top_stations", lambda **_kw: shoutcast.parse_stations(_GENRE_JSON)
    )
    nodes = bs.browse("shoutcasttop")
    assert len(nodes) == 3
    assert not any(node.is_folder for node in nodes)


def test_a_failing_directory_is_an_empty_branch_not_an_exception(monkeypatch) -> None:
    def _fail(**_kw):
        raise shoutcast.ShoutcastError("down")

    monkeypatch.setattr(shoutcast, "fetch_genres", _fail)
    assert bs.browse("shoutcast") == []


# --- a station is a playlist, so it is resolved before it is played ----------
# Reported 2026-08-26: "many of the stations from the shoutcast directory are
# not playing", on a station with 293 listeners that was plainly on the air.

_TUNEIN_PLS = (
    "[playlist]\n"
    "numberofentries=1\n"
    "File1=http://stream.antenne.de:80/80er-kulthits\n"
    "Title1=(#1 - 357/500000) ANTENNE BAYERN 80er Hits\n"
    "Length1=-1\n"
    "Version=2\n"
)


def test_a_browse_row_carries_its_id_and_not_a_playlist_url(monkeypatch) -> None:
    monkeypatch.setattr(
        shoutcast, "fetch_genre_stations", lambda _g, **_kw: shoutcast.parse_stations(_GENRE_JSON)
    )
    rows = bs.browse("shoutcast:Jazz")
    assert rows and all(row.resolve_lazily for row in rows)
    assert all(row.node_id.startswith("shoutcaststation:") for row in rows)
    # The listener count and what was playing ride along in the note, so the
    # row still says what the directory knew about it.
    assert any("listening" in (row.note or "") for row in rows)


def test_the_row_resolves_to_the_real_stream_when_it_is_played(monkeypatch) -> None:
    monkeypatch.setattr(shoutcast, "_request", lambda _url, _fields=None: _TUNEIN_PLS)
    station = bs.resolve("shoutcaststation:99497948")
    assert station is not None
    assert station.stream_url == "http://stream.antenne.de:80/80er-kulthits"
    assert station.source == "SHOUTcast"


def test_a_station_that_will_not_resolve_is_reported_not_played(monkeypatch) -> None:
    monkeypatch.setattr(shoutcast, "_request", lambda _url, _fields=None: "[playlist]\n")
    assert bs.resolve("shoutcaststation:1") is None


def test_resolving_never_raises_into_the_caller(monkeypatch) -> None:
    def _boom(_url, _fields=None):
        raise shoutcast.ShoutcastError("down")

    monkeypatch.setattr(shoutcast, "_request", _boom)
    assert shoutcast.resolve_stream("1") == ""
    assert shoutcast.resolve_stream("", safe_mode=True) == ""


def test_search_results_are_resolved_because_search_has_no_second_chance(monkeypatch) -> None:
    """Find Stations hands a row straight to the player; it cannot resolve later."""
    calls: list[str] = []

    def _request(url, fields=None):
        calls.append(url)
        return _GENRE_JSON if fields is not None else _TUNEIN_PLS

    monkeypatch.setattr(shoutcast, "_request", _request)
    rows = shoutcast.search_stations("jazz")
    assert rows and all(row.stream_url.startswith("http://stream.antenne.de") for row in rows)
    # One search request, then one per row -- and never a request per row for a
    # page nobody asked to play.
    assert calls[0] == shoutcast._SEARCH_URL


def test_search_resolution_is_capped(monkeypatch) -> None:
    many = [
        {"ID": i, "Name": f"Station {i}", "Format": "audio/mpeg", "Listeners": i}
        for i in range(1, 60)
    ]
    import json as _json

    def _request(url, fields=None):
        return _json.dumps(many) if fields is not None else _TUNEIN_PLS

    monkeypatch.setattr(shoutcast, "_request", _request)
    assert len(shoutcast.search_stations("many")) == 12
    # ...and the tree, which resolves a row when it is played, pays for none of
    # it: one request for the search and nothing per row.
    assert len(shoutcast.search_stations("many", resolve=False)) == len(many)


def test_the_station_id_is_read_back_out_of_the_row() -> None:
    station = shoutcast.parse_stations(_GENRE_JSON)[0]
    assert shoutcast.station_id_of(station).isdigit()
    from quill.core.radio.models import RadioStation

    assert shoutcast.station_id_of(RadioStation(name="x", stream_url="https://a/b")) == ""
