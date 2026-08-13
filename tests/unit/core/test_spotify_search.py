"""Tests for blending Spotify results into Find Stations.

The point of these rows is that they work for *every* account tier: Spotify's
search API is open to free accounts, and the row's homepage link opens the
track in Spotify's own app, where a free account plays it normally. So the
tests below care about two things -- that a row carries something playable
(the ``spotify:`` URI) *and* something openable (the web link).
"""

from quill.core.radio.models import RadioStation
from quill.core.radio.spotify_search import (
    SOURCE,
    is_spotify_station,
    open_link_label,
    spotify_search_stations,
    stations_from_results,
    track_to_station,
    web_url,
)
from quill.core.spotify.models import (
    SearchResults,
    SpotifyEpisode,
    SpotifyShow,
    SpotifyTrack,
)


def _track(name: str = "Blackbird", artist: str = "The Beatles") -> SpotifyTrack:
    return SpotifyTrack(
        id="t1", uri="spotify:track:t1", name=name, artist=artist, album="White Album"
    )


class _FakeClient:
    def __init__(self, results: SearchResults | None = None, error: bool = False) -> None:
        self._results = results or SearchResults(tracks=[_track()])
        self._error = error
        self.queries: list[str] = []

    def search(self, query: str, *, limit: int = 20) -> SearchResults:
        self.queries.append(query)
        if self._error:
            raise RuntimeError("Spotify is down")
        return self._results


# -- web links ---------------------------------------------------------------


def test_a_uri_becomes_an_open_spotify_link() -> None:
    assert web_url("spotify:track:abc123") == "https://open.spotify.com/track/abc123"
    assert web_url("spotify:show:xyz") == "https://open.spotify.com/show/xyz"


def test_a_malformed_uri_yields_no_link_rather_than_a_broken_one() -> None:
    for bad in ("", "spotify:track", "http://example.com", "spotify::abc", "spotify:track:"):
        assert web_url(bad) == ""


# -- conversion --------------------------------------------------------------


def test_a_track_row_is_playable_and_openable() -> None:
    """Both halves matter: the URI for Premium, the link for everyone else."""
    station = track_to_station(_track())
    assert station is not None
    assert station.stream_url == "spotify:track:t1"
    assert station.homepage == "https://open.spotify.com/track/t1"
    assert station.source == SOURCE


def test_a_track_row_names_the_artist() -> None:
    """A list of bare song titles is unusable when several results share one."""
    station = track_to_station(_track(name="Yesterday"))
    assert station is not None
    assert station.name == "Yesterday - The Beatles"


def test_a_track_with_no_artist_keeps_a_clean_name() -> None:
    station = track_to_station(_track(name="Untitled", artist=""))
    assert station is not None
    assert station.name == "Untitled"


def test_a_row_with_nothing_to_play_is_dropped() -> None:
    assert track_to_station(SpotifyTrack(id="", uri="", name="Ghost")) is None
    assert track_to_station(SpotifyTrack(id="x", uri="spotify:track:x", name="  ")) is None


def test_a_show_prefers_its_own_homepage() -> None:
    """Spotify hands shows a real external_urls page; use it over a rebuild."""
    show = SpotifyShow(
        id="s1",
        uri="spotify:show:s1",
        name="Radiolab",
        publisher="WNYC",
        homepage="https://open.spotify.com/show/canonical",
    )
    from quill.core.radio.spotify_search import show_to_station

    station = show_to_station(show)
    assert station is not None
    assert station.homepage == "https://open.spotify.com/show/canonical"
    assert station.name == "Radiolab - WNYC"


# -- blending ----------------------------------------------------------------


def test_types_are_interleaved_so_one_kind_cannot_crowd_out_the_others() -> None:
    """A band-name search should still surface that band's podcast interview."""
    results = SearchResults(
        tracks=[
            SpotifyTrack(id=f"t{i}", uri=f"spotify:track:t{i}", name=f"Song {i}") for i in range(20)
        ],
        shows=[SpotifyShow(id="s1", uri="spotify:show:s1", name="A Show")],
        episodes=[SpotifyEpisode(id="e1", uri="spotify:episode:e1", name="An Episode")],
    )
    rows = stations_from_results(results, cap=6)
    assert len(rows) <= 6
    names = [r.name for r in rows]
    assert "A Show" in names
    assert "An Episode" in names


def test_the_cap_is_respected() -> None:
    results = SearchResults(
        tracks=[
            SpotifyTrack(id=f"t{i}", uri=f"spotify:track:t{i}", name=f"Song {i}") for i in range(50)
        ]
    )
    assert len(stations_from_results(results, cap=3)) <= 3
    assert stations_from_results(results, cap=0) == []


# -- the search entry point --------------------------------------------------


def test_searching_returns_station_rows() -> None:
    client = _FakeClient()
    rows = spotify_search_stations("beatles", client=client)
    assert client.queries == ["beatles"]
    assert [r.source for r in rows] == [SOURCE]


def test_no_client_means_no_rows_rather_than_an_error() -> None:
    """Nobody signed in to Spotify is the common case, not a failure."""
    assert spotify_search_stations("beatles", client=None) == []


def test_safe_mode_skips_spotify_entirely() -> None:
    client = _FakeClient()
    assert spotify_search_stations("beatles", client=client, safe_mode=True) == []
    assert client.queries == []


def test_a_blank_query_never_reaches_the_network() -> None:
    client = _FakeClient()
    assert spotify_search_stations("   ", client=client) == []
    assert client.queries == []


def test_a_down_spotify_never_blanks_the_surrounding_results() -> None:
    """Find Stations concatenates several sources; one failure must not win."""
    assert spotify_search_stations("beatles", client=_FakeClient(error=True)) == []


# -- the open action ---------------------------------------------------------


def test_a_spotify_row_labels_its_link_as_open_in_spotify() -> None:
    """For a free account that link is how the track plays -- don't bury it
    under the word "website"."""
    station = track_to_station(_track())
    assert station is not None
    assert is_spotify_station(station)
    assert open_link_label(station) == "Open in &Spotify"


def test_an_ordinary_station_keeps_the_website_label() -> None:
    station = RadioStation(name="WNYC", stream_url="http://x/s", source="RadioBrowser")
    assert not is_spotify_station(station)
    assert open_link_label(station) == "Open &Website"
