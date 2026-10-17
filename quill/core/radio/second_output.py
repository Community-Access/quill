"""A second output device: a background station, or a mirror (xradio2 4.6, 4.7).

Todo P3 "Radio extras" 3 and 4. Both are a second player on a second sound
device, beside the main one; they differ only in what that player plays and
how it follows the main one.

* **Background station** ("obligato" in FreeRadio): a favourite looping quietly
  on its own device at its own volume, underneath whatever the main player is
  doing. Two linkage rules, copied exactly because they clearly came from use:
  its volume **scales with the main volume** (its own level times the main
  level), and it **pauses when the main player pauses** -- but a full Stop, or
  changing station, does not touch it. It is stopped only by asking.
* **Mirror**: the same station as the main player, on another device -- a guest
  on headphones, a room speaker as well as the built-in one. It follows
  everything: station changes, pause, stop and volume.

Two independent players drift apart by a little; that is stated in help rather
than engineered away (xradio2 4.7).

This module is the decision only -- given what the main player just did, what
should the second one do -- so it is testable without audio. The player itself
is :mod:`quill.ui.radio.second_output_ui`.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BACKGROUND",
    "DEFAULT_BACKGROUND_VOLUME",
    "MIRROR",
    "OFF",
    "Step",
    "follow",
    "scaled_volume",
]

OFF = "off"
BACKGROUND = "background"
MIRROR = "mirror"

#: A background station starts at this share of the main volume: underneath,
#: not competing.
DEFAULT_BACKGROUND_VOLUME = 40

#: The main player's states that mean "sound is (about to be) coming out".
_RUNNING = frozenset({"CONNECTING", "PLAYING", "BUFFERING", "RECONNECTING"})


@dataclass(frozen=True, slots=True)
class Step:
    """What the second player should do now. Every field is optional."""

    load: str = ""
    pause: bool = False
    resume: bool = False
    close: bool = False
    volume: int | None = None


def scaled_volume(own_percent: int, main_percent: int, *, main_muted: bool = False) -> int:
    """The background station's level: its own share of the main volume."""
    if main_muted:
        return 0
    own = max(0, min(100, own_percent))
    main = max(0, min(100, main_percent))
    return round(own * main / 100)


def follow(
    mode: str,
    *,
    main_state: str,
    main_url: str,
    main_volume: int,
    main_muted: bool = False,
    own_volume: int = DEFAULT_BACKGROUND_VOLUME,
    playing_url: str = "",
    paused: bool = False,
) -> Step:
    """What the second player does after the main one changed.

    *playing_url* is what the second player has loaded ("" for nothing) and
    *paused* whether it is paused by an earlier :func:`follow`.
    """
    if mode == BACKGROUND:
        volume = scaled_volume(own_volume, main_volume, main_muted=main_muted)
        if main_state == "PAUSED" and not paused:
            return Step(pause=True, volume=volume)
        if main_state != "PAUSED" and paused:
            # Pause follows; nothing else does. A stop, an error or a station
            # change on the main player leaves the background playing.
            return Step(resume=True, volume=volume)
        return Step(volume=volume)
    if mode == MIRROR:
        volume = 0 if main_muted else max(0, min(100, main_volume))
        if main_state in _RUNNING and main_url:
            if main_url != playing_url:
                return Step(load=main_url, volume=volume)
            if paused:
                return Step(resume=True, volume=volume)
            return Step(volume=volume)
        if main_state == "PAUSED":
            return Step(pause=not paused, volume=volume)
        if playing_url:
            return Step(close=True)
        return Step()
    return Step(close=bool(playing_url))
