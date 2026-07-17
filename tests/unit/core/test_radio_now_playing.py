"""Tests for the What's Playing parser/formatter (issue #1068)."""

from __future__ import annotations

import pytest

from quill.core.radio.now_playing import (
    DEFAULT_TEMPLATE,
    NowPlaying,
    format_now_playing,
    parse_now_playing,
    render_now_playing,
)

# The exact raw StreamTitle reported in issue #1068 -- broadcast automation
# packing key="value" pairs into the field a listener wanted read aloud.
_REPORTED = (
    'title="YOUR SONG",artist="Elton John",url="song_spot="F" MediaBaseId="0" '
    'itunesTrackId="0" amgTrackId="-1" amgArtistId="0" TAID="0" TPID="638642"'
)


def test_reported_structured_metadata_becomes_clean_title_and_artist() -> None:
    now = parse_now_playing(_REPORTED)
    assert now.title == "YOUR SONG"
    assert now.artist == "Elton John"
    # The noise is retained in extras, never spoken by the default template.
    assert now.raw == _REPORTED
    assert "mediabaseid" in now.extras


def test_reported_metadata_default_render_is_delightful() -> None:
    assert render_now_playing(_REPORTED) == "YOUR SONG by Elton John"


def test_plain_artist_dash_title_convention() -> None:
    now = parse_now_playing("Elton John - Your Song")
    assert now.artist == "Elton John"
    assert now.title == "Your Song"
    assert render_now_playing("Elton John - Your Song") == "Your Song by Elton John"


def test_title_with_its_own_hyphen_splits_only_on_the_first() -> None:
    now = parse_now_playing("Dolly Parton - 9 to 5 - Live")
    assert now.artist == "Dolly Parton"
    assert now.title == "9 to 5 - Live"


def test_structured_title_only_drops_the_by_segment() -> None:
    assert render_now_playing('title="News at Nine"') == "News at Nine"


def test_bare_string_is_taken_as_the_title() -> None:
    now = parse_now_playing("BBC World Service")
    assert now.title == "BBC World Service"
    assert now.artist == ""
    assert render_now_playing("BBC World Service") == "BBC World Service"


def test_empty_input_is_empty_everywhere() -> None:
    assert parse_now_playing("") == NowPlaying()
    assert render_now_playing("") == ""
    assert render_now_playing("   ") == ""


def test_structured_noise_without_title_or_artist_falls_back_to_raw() -> None:
    # Pairs present, but none of them are a title/artist -> treat as a title.
    raw = 'MediaBaseId="0" TPID="638642"'
    now = parse_now_playing(raw)
    assert now.title == raw
    assert now.artist == ""


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{artist}: {title}", "Elton John: YOUR SONG"),
        ("{title}", "YOUR SONG"),
        ("Now spinning {title} from {artist}", "Now spinning YOUR SONG from Elton John"),
        ("{raw}", _REPORTED),
        # An optional segment whose token is empty vanishes entirely.
        ("{title}[ (from the album {album})]", "YOUR SONG"),
    ],
)
def test_custom_templates(template: str, expected: str) -> None:
    assert render_now_playing(_REPORTED, template) == expected


def test_unknown_token_is_left_visible_not_eaten() -> None:
    # A typo'd token should be obvious to the user, not silently dropped.
    assert format_now_playing(NowPlaying(title="X"), "{titel}") == "{titel}"


def test_render_never_empty_when_a_title_exists() -> None:
    # A template that resolves to nothing still yields the title, so the
    # listener always hears something real.
    assert format_now_playing(NowPlaying(title="Song", raw="Song"), "[{artist}]") == "Song"


def test_default_template_constant_matches_behaviour() -> None:
    assert DEFAULT_TEMPLATE == "{title}[ by {artist}]"
    assert render_now_playing(_REPORTED, DEFAULT_TEMPLATE) == "YOUR SONG by Elton John"
