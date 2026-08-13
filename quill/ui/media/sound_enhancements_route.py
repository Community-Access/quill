"""Ctrl+E in full QUILL: Sound Enhancements for whatever is playing.

Both standalone apps put Sound Enhancements on **Ctrl+E** and mean it
literally -- Quill Radio has only stations, QUILL Cast has only episodes, so
in each the key has exactly one destination. Full QUILL has both players at
once, which is why the key was never wired here at all: two commands wanted
it and neither could have it.

Giving it to one of them would have made Ctrl+E mean something different
depending on which app you were in, which is worse than not having it. So the
key resolves the same way a listener already thinks about it: **the sound you
are adjusting is the sound you can hear.** A podcast playing wins, because it
is the more specific thing to be listening to and its settings are per-show;
otherwise it is radio's, whose settings are per-station.

With nothing playing it opens radio's, and says so. That is a real choice
rather than a coin toss: radio's enhancements double as the shared default
that a station with no override inherits, so it is the one worth reaching when
there is nothing particular to adjust.

Every route announces which one it opened, because a single key with two
possible destinations must never leave you guessing which you got.

The pure part -- which surface a given pair of states resolves to -- is
:func:`choose_surface`, so the rule is testable without a player.
"""

from __future__ import annotations

from typing import Any

SURFACE_PODCAST = "podcast"
SURFACE_RADIO = "radio"


def choose_surface(*, podcast_active: bool, radio_active: bool) -> str:
    """Which player's Sound Enhancements Ctrl+E opens.

    "Active" means playing **or paused**: a paused podcast is still the thing
    you are listening to, and pausing to fix the sound is exactly when this
    dialog gets opened.
    """
    if podcast_active:
        return SURFACE_PODCAST
    if radio_active:
        return SURFACE_RADIO
    return SURFACE_RADIO


def _is_active(controller: Any, playing: Any, paused: Any) -> bool:
    state = getattr(controller, "state", None)
    current = getattr(state, "state", None)
    return current is playing or current is paused


def podcast_is_active(host: Any) -> bool:
    from quill.ui.podcasts.player_controller import PodcastPlayerState

    return _is_active(
        getattr(host, "_podcast_controller", None),
        PodcastPlayerState.PLAYING,
        PodcastPlayerState.PAUSED,
    )


def radio_is_active(host: Any) -> bool:
    from quill.ui.radio.player_controller import RadioPlayerState

    return _is_active(
        getattr(host, "_radio_controller", None),
        RadioPlayerState.PLAYING,
        RadioPlayerState.PAUSED,
    )


def open_for_whats_playing(host: Any) -> str:
    """Open the right Sound Enhancements and say which. Returns the surface."""
    surface = choose_surface(
        podcast_active=podcast_is_active(host),
        radio_active=radio_is_active(host),
    )
    if surface == SURFACE_PODCAST:
        host._announce("Sound Enhancements for the playing podcast")
        host.open_podcast_sound_enhancements()
    else:
        host._announce("Sound Enhancements for radio")
        host.open_sound_enhancements()
    return surface


__all__ = [
    "SURFACE_PODCAST",
    "SURFACE_RADIO",
    "choose_surface",
    "open_for_whats_playing",
    "podcast_is_active",
    "radio_is_active",
]
