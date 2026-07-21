"""Tests for quill_radio_mac.core.now_playing.

Covers the key="value" broadcast-automation form (RCS/GSelector-style
StreamTitle), the plain "Artist - Title" convention, the bare-string
fallback, template rendering with optional [...] segments, and the
empty-input edge case. Pure functions; no network.
"""

from __future__ import annotations

from quill_radio_mac.core.now_playing import (
    DEFAULT_TEMPLATE,
    NowPlaying,
    format_now_playing,
    parse_now_playing,
    render_now_playing,
)


def test_parse_now_playing_empty_string_yields_empty_record():
    result = parse_now_playing("")
    assert result == NowPlaying()


def test_parse_now_playing_plain_artist_title():
    result = parse_now_playing("Elton John - Your Song")
    assert result.artist == "Elton John"
    assert result.title == "Your Song"
    assert result.raw == "Elton John - Your Song"


def test_parse_now_playing_keeps_hyphen_in_title():
    result = parse_now_playing("Dolly Parton - 9 to 5 - Live")
    assert result.artist == "Dolly Parton"
    assert result.title == "9 to 5 - Live"


def test_parse_now_playing_broadcast_key_value_form():
    raw = (
        'title="YOUR SONG",artist="Elton John",url="song_spot="F" '
        'MediaBaseId="0" itunesTrackId="0" amgTrackId="-1" amgArtistId="0" '
        'TAID="0" TPID="638642"'
    )
    result = parse_now_playing(raw)
    assert result.title == "YOUR SONG"
    assert result.artist == "Elton John"
    assert result.raw == raw
    assert "mediabaseid" in result.extras


def test_parse_now_playing_bare_string_becomes_title():
    result = parse_now_playing("Just A Programme Name")
    assert result.title == "Just A Programme Name"
    assert result.artist == ""
    assert result.raw == "Just A Programme Name"


def test_parse_now_playing_key_value_with_no_title_or_artist_falls_back_to_raw():
    raw = 'foo="bar",baz="qux"'
    result = parse_now_playing(raw)
    assert result.title == raw
    assert result.artist == ""


def test_format_now_playing_default_template_with_artist():
    now_playing = NowPlaying(title="Your Song", artist="Elton John", raw="Elton John - Your Song")
    assert format_now_playing(now_playing) == "Your Song by Elton John"


def test_format_now_playing_default_template_without_artist_drops_by():
    now_playing = NowPlaying(title="Just A Programme Name", raw="Just A Programme Name")
    assert format_now_playing(now_playing) == "Just A Programme Name"
    assert "by" not in format_now_playing(now_playing)


def test_format_now_playing_raw_token():
    now_playing = NowPlaying(title="Your Song", artist="Elton John", raw="raw text")
    assert format_now_playing(now_playing, "{raw}") == "raw text"


def test_format_now_playing_unknown_token_left_as_is():
    # An unknown token *inside* an optional [...] segment counts as empty and
    # drops the whole segment; only a bare (non-bracketed) unknown token is
    # left as literal text, per format_now_playing's docstring.
    now_playing = NowPlaying(title="Your Song")
    assert format_now_playing(now_playing, "{title} {album}") == "Your Song {album}"


def test_format_now_playing_empty_falls_back_to_title_then_raw():
    now_playing = NowPlaying(raw="only raw text")
    assert format_now_playing(now_playing, "[{artist}]") == "only raw text"


def test_render_now_playing_parses_and_formats_in_one_call():
    assert render_now_playing("Elton John - Your Song") == "Your Song by Elton John"
    assert render_now_playing("") == ""


def test_default_template_constant_value():
    assert DEFAULT_TEMPLATE == "{title}[ by {artist}]"
