"""Tests for exporting radio favorites to an M3U playlist (#1249)."""

from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.models import RadioStation
from quill.core.radio.playlist_export import export_m3u
from quill.core.radio.playlist_import import parse_m3u


def _fav(name: str, url: str, *, custom_name: str = "") -> FavoriteStation:
    return FavoriteStation(station=RadioStation(name=name, stream_url=url), custom_name=custom_name)


def test_export_m3u_emits_extinf_and_url_per_station() -> None:
    text = export_m3u([_fav("Jazz FM", "https://example.com/jazz")])
    assert text == "#EXTM3U\n#EXTINF:-1,Jazz FM\nhttps://example.com/jazz\n"


def test_export_m3u_honors_custom_name() -> None:
    text = export_m3u([_fav("noisy-directory-name", "https://x/1", custom_name="My Station")])
    assert "#EXTINF:-1,My Station" in text


def test_export_m3u_skips_stations_without_a_stream_url() -> None:
    favorites = [_fav("Good", "https://x/1"), _fav("Bad", "")]
    text = export_m3u(favorites)
    assert "Good" in text
    assert "Bad" not in text


def test_export_m3u_round_trips_through_parse_m3u() -> None:
    favorites = [_fav("One", "https://x/1"), _fav("Two", "https://x/2")]
    stations = parse_m3u(export_m3u(favorites))
    assert [(s.name, s.stream_url) for s in stations] == [
        ("One", "https://x/1"),
        ("Two", "https://x/2"),
    ]


def test_export_m3u_flattens_multiline_labels() -> None:
    text = export_m3u([_fav("Line one\nline two", "https://x/1")])
    # The EXTINF line must stay single-line so the playlist parses correctly.
    assert "#EXTINF:-1,Line one line two" in text
