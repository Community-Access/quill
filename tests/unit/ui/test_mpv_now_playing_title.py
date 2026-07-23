"""#1215: the mpv now-playing fallback must read the parsed metadata map, not
only ``media-title``. Some stations (HLS, and a few ICY hosts another player
still shows a song for) leave ``media-title`` as the URL while exposing the
current track in ``metadata/icy-title`` or ``metadata/title``."""

from __future__ import annotations

from quill.ui.radio.mpv_radio_engine import _pick_mpv_title

_URL = "https://stream.example.com/awesome98"


def _mpv(mapping: dict[str, str]):
    return lambda prop: mapping.get(prop)


def test_media_title_wins_when_present() -> None:
    got = _pick_mpv_title(_mpv({"media-title": "SONG by Artist"}), _URL)
    assert got == "SONG by Artist"


def test_falls_back_to_icy_title_when_media_title_is_the_url() -> None:
    # The regression: media-title stayed the URL, but the ICY title is in the
    # metadata map -- previously this returned "".
    got = _pick_mpv_title(
        _mpv({"media-title": _URL, "metadata/icy-title": "Now Playing Track"}), _URL
    )
    assert got == "Now Playing Track"


def test_falls_back_to_metadata_title_for_hls() -> None:
    got = _pick_mpv_title(_mpv({"media-title": "", "metadata/title": "HLS Timed Title"}), _URL)
    assert got == "HLS Timed Title"


def test_returns_empty_when_nothing_but_the_url_is_known() -> None:
    assert _pick_mpv_title(_mpv({"media-title": _URL}), _URL) == ""
    assert _pick_mpv_title(_mpv({}), _URL) == ""


def test_whitespace_only_values_are_ignored() -> None:
    got = _pick_mpv_title(
        _mpv({"media-title": "   ", "metadata/icy-title": "  Real Title  "}), _URL
    )
    assert got == "Real Title"
