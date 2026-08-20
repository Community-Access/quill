"""Ctrl+E in full QUILL follows whatever is playing.

Both standalone apps put Sound Enhancements on Ctrl+E and mean it literally --
each has only one kind of player. Full QUILL has both, which is why the key was
never wired here: two commands wanted it and neither could have it, and giving
it to one would have made Ctrl+E mean something different depending on which
app you were in.

The rule is that the sound you adjust is the sound you can hear. These tests
pin that rule, and the announcement that goes with it: a single key with two
possible destinations must never leave a listener guessing which they got.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.media.sound_enhancements_route import (
    SURFACE_PODCAST,
    SURFACE_RADIO,
    choose_surface,
    open_for_whats_playing,
)
from quill.ui.podcasts.player_controller import PodcastPlayerState
from quill.ui.radio.playback_state import RadioPlayerState

# -- the rule ----------------------------------------------------------------


def test_a_playing_podcast_wins() -> None:
    """The more specific thing to be listening to, and its settings are
    per-show rather than per-station."""
    assert choose_surface(podcast_active=True, radio_active=False) == SURFACE_PODCAST
    assert choose_surface(podcast_active=True, radio_active=True) == SURFACE_PODCAST


def test_radio_answers_when_it_is_the_one_playing() -> None:
    assert choose_surface(podcast_active=False, radio_active=True) == SURFACE_RADIO


def test_nothing_playing_opens_radios() -> None:
    """A real choice, not a coin toss: radio's enhancements double as the
    shared default a station with no override inherits."""
    assert choose_surface(podcast_active=False, radio_active=False) == SURFACE_RADIO


# -- the wiring --------------------------------------------------------------


class _State:
    def __init__(self, state: object) -> None:
        self.state = state


class _Controller:
    def __init__(self, state: object) -> None:
        self.state = _State(state)


class _Host:
    def __init__(self, podcast: object, radio: object) -> None:
        self._podcast_controller = _Controller(podcast)
        self._radio_controller = _Controller(radio)
        self.announced: list[str] = []
        self.opened: list[str] = []

    def _announce(self, text: str) -> None:
        self.announced.append(text)

    def open_podcast_sound_enhancements(self) -> None:
        self.opened.append("podcast")

    def open_sound_enhancements(self) -> None:
        self.opened.append("radio")


def test_a_playing_podcast_opens_the_podcast_dialog() -> None:
    host = _Host(PodcastPlayerState.PLAYING, RadioPlayerState.STOPPED)
    assert open_for_whats_playing(host) == SURFACE_PODCAST
    assert host.opened == ["podcast"]


def test_a_playing_station_opens_the_radio_dialog() -> None:
    host = _Host(PodcastPlayerState.STOPPED, RadioPlayerState.PLAYING)
    assert open_for_whats_playing(host) == SURFACE_RADIO
    assert host.opened == ["radio"]


@pytest.mark.parametrize(
    ("podcast_state", "expected"),
    [(PodcastPlayerState.PLAYING, "podcast"), (PodcastPlayerState.PAUSED, "podcast")],
)
def test_a_paused_podcast_still_counts_as_what_you_are_listening_to(
    podcast_state: Any, expected: str
) -> None:
    """Pausing to fix the sound is exactly when this dialog gets opened."""
    host = _Host(podcast_state, RadioPlayerState.STOPPED)
    open_for_whats_playing(host)
    assert host.opened == [expected]


def test_a_paused_station_counts_too() -> None:
    host = _Host(PodcastPlayerState.STOPPED, RadioPlayerState.PAUSED)
    open_for_whats_playing(host)
    assert host.opened == ["radio"]


def test_a_connecting_station_is_not_yet_what_you_can_hear() -> None:
    """It resolves to radio anyway (the nothing-playing fallback), but through
    the fallback rather than by claiming it is active."""
    from quill.ui.media.sound_enhancements_route import radio_is_active

    host = _Host(PodcastPlayerState.STOPPED, RadioPlayerState.CONNECTING)
    assert radio_is_active(host) is False
    assert open_for_whats_playing(host) == SURFACE_RADIO


def test_every_route_says_which_one_it_opened() -> None:
    """One key, two destinations -- never leave the listener guessing."""
    podcast_host = _Host(PodcastPlayerState.PLAYING, RadioPlayerState.STOPPED)
    open_for_whats_playing(podcast_host)
    assert "podcast" in podcast_host.announced[0].casefold()

    radio_host = _Host(PodcastPlayerState.STOPPED, RadioPlayerState.PLAYING)
    open_for_whats_playing(radio_host)
    assert "radio" in radio_host.announced[0].casefold()

    assert podcast_host.announced[0] != radio_host.announced[0]


def test_a_host_with_no_players_still_answers() -> None:
    """Podcasts and radio are both optional features; the key must not raise
    when one of them is turned off."""

    class _Bare:
        announced: list[str] = []
        opened: list[str] = []

        def _announce(self, text: str) -> None:
            self.announced.append(text)

        def open_sound_enhancements(self) -> None:
            self.opened.append("radio")

        def open_podcast_sound_enhancements(self) -> None:
            self.opened.append("podcast")

    host = _Bare()
    assert open_for_whats_playing(host) == SURFACE_RADIO


# -- the rebindability gap this also closed ----------------------------------


def test_all_three_commands_are_in_the_keymap() -> None:
    """The two per-player commands were registered but absent from
    DEFAULT_KEYMAP, so the Keyboard Shortcuts editor had nothing to offer and
    they could not be bound at all -- against x.md's own cross-cutting rule."""
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["media.sound_enhancements"] == "Ctrl+E"
    assert DEFAULT_KEYMAP["radio.sound_enhancements"] == ""
    assert DEFAULT_KEYMAP["podcasts.sound_enhancements"] == ""


def test_ctrl_e_does_not_collide_with_an_existing_binding() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    owners = [cmd for cmd, chord in DEFAULT_KEYMAP.items() if chord == "Ctrl+E"]
    assert owners == ["media.sound_enhancements"]
