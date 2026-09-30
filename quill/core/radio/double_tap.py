"""Double Tap Live: the blind tech show's round-the-clock channel, in Browse.

Double Tap is the daily show "where blind people talk tech" -- Steven Scott and
Shaun Preece, from Accessible Media Inc. -- and on 30 September 2026 it became a
radio station too: **Double Tap Live**, "talk, tech, music and the best of the
Double Tap podcast, on air around the clock." It is exactly the audience Quill
Radio is built for, which is why it sits as its own branch directly under ACB
Media rather than somewhere in a directory's search results (Jeff, 2026-09-29).

The stream is the station's own Radio.co mount, read from the player on
doubletaponair.com/live: ``https://s2.radio.co/s1eb3875b8/listen``. Radio.co
serves MP3 with ICY titles, so What's Playing reads the segment or the song the
way it does for any other station. Bundled and static like ACB Media and NFB
Radio: seeing the branch needs no network. wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.radio.models import RadioStation

__all__ = ["CATEGORY_LABEL", "HOMEPAGE", "STREAM_URL", "double_tap_stations"]

CATEGORY_LABEL = "Double Tap Live"
HOMEPAGE = "https://doubletaponair.com/live/"
STREAM_URL = "https://s2.radio.co/s1eb3875b8/listen"

_NOTES = (
    "Double Tap's own 24-hour channel: talk, tech, music and the best of the "
    "Double Tap podcast, from the daily show where blind people talk tech "
    "(Steven Scott and Shaun Preece, Accessible Media Inc.). On air around the "
    "clock since 30 September 2026; the schedule is at doubletaponair.com/live."
)


def double_tap_stations() -> list[RadioStation]:
    """The one station in the branch."""
    return [
        RadioStation(
            name="Double Tap Live",
            stream_url=STREAM_URL,
            homepage=HOMEPAGE,
            country="Canada",
            language="English",
            tags=(CATEGORY_LABEL, "Technology", "Accessibility", "Talk", "Podcast"),
            codec="MP3",
            source=CATEGORY_LABEL,
            notes=_NOTES,
        )
    ]
