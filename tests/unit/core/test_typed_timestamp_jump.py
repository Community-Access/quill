"""11.8: type a timestamp and land there, the same way in both players.

Scrubbing by keystroke is fine for seconds and useless for "the bit forty
minutes in". Both apps could already parse a time -- with two parsers that
did not agree, and a surface in Cast that only existed if the Winamp letter
keys were on. One parser now, reachable from a menu in both.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.media.errors import InvalidTimecodeError
from quill.core.media.timecode import parse_timecode
from quill.ui.radio.winamp_keys import parse_time_to_ms

REPO = Path(__file__).resolve().parents[3]

#: The three forms item 11.8 names, plus the unit form the shared parser has
#: always taken. All of them are 1 hour, 2 minutes, 3 seconds.
_THREE_FORMS = ("1:02:03", "62:03", "3723", "1h2m3s")


@pytest.mark.parametrize("text", _THREE_FORMS)
def test_all_three_named_forms_mean_the_same_moment(text: str) -> None:
    assert parse_timecode(text) == 3_723_000


@pytest.mark.parametrize("text", _THREE_FORMS)
def test_both_players_read_them_identically(text: str) -> None:
    """One parser, not two: the Winamp key delegates to the shared one."""
    assert parse_time_to_ms(text) == parse_timecode(text)


def test_minutes_past_the_hour_mark_are_minutes_not_an_error() -> None:
    """ "62:03" is 62 minutes, which is what somebody reading a show note types."""
    assert parse_timecode("62:03") == parse_timecode("1:02:03")
    assert parse_timecode("83:45") == 5_025_000


def test_seconds_over_59_are_still_refused() -> None:
    """The last segment is seconds; 1:75 is a typo, not 2:15."""
    with pytest.raises(InvalidTimecodeError):
        parse_timecode("1:75")


@pytest.mark.parametrize("text", ["", "   ", "abc", "1:2:3:4", "-5"])
def test_the_winamp_key_answers_none_rather_than_seeking_to_zero(text: str) -> None:
    assert parse_time_to_ms(text) is None


def test_both_apps_reach_it_from_a_menu_and_not_only_a_letter_key() -> None:
    """The gap 11.8 closed in Cast: no menu item, no command, no palette row."""
    cast_menu = (REPO / "quill" / "apps" / "podcasts_menu.py").read_text(encoding="utf-8")
    radio_menu = (REPO / "quill" / "apps" / "radio_video_menu.py").read_text(encoding="utf-8")
    palette = (REPO / "quill" / "ui" / "podcasts" / "palette_commands.py").read_text(
        encoding="utf-8"
    )
    assert "podcasts.go_to_position" in cast_menu
    assert "Go to Position" in radio_menu
    assert "podcasts.go_to_position" in palette


def test_the_same_key_reaches_it_in_both_apps() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS

    assert APP_KEYMAPS["cast"]["podcasts.go_to_position"] == "Ctrl+Alt+J"
    radio_menu = (REPO / "quill" / "apps" / "radio_video_menu.py").read_text(encoding="utf-8")
    assert "Ctrl+Alt+J" in radio_menu
