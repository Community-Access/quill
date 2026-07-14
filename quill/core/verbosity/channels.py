"""Verbosity output channels (verbosity §7).

A verbosity announcement can reach the user over four channels: SPEECH (the
screen reader / TTS), BRAILLE (a braille display), SOUND (earcons), and VISUAL
(the status bar). VISUAL is the accessibility floor — it is always on and can
never be turned off, so the user never loses the on-screen status of an action
even when every other channel is muted.

Pure and wx-free so the engine, the prefs UI, and tests all reason about the
same routing rules.
"""

from __future__ import annotations

import enum

__all__ = [
    "Channel",
    "DEFAULT_CHANNELS",
    "ALWAYS_ON_CHANNELS",
    "VISUAL_ALWAYS_ON_NAME",
    "route_channels",
]


class Channel(enum.Flag):
    """The output channels a verbosity announcement can travel over."""

    NONE = 0
    SPEECH = enum.auto()
    BRAILLE = enum.auto()
    SOUND = enum.auto()
    VISUAL = enum.auto()


#: The default channel mix for a fresh install: everything on.
DEFAULT_CHANNELS = Channel.SPEECH | Channel.BRAILLE | Channel.SOUND | Channel.VISUAL

#: Channels that can never be disabled — the accessibility floor.
ALWAYS_ON_CHANNELS = Channel.VISUAL

#: Accessible name for the always-on Visual checkbox in the prefs panel. The
#: checkbox is rendered checked-but-disabled so the floor is visible yet fixed.
VISUAL_ALWAYS_ON_NAME = "Visual status bar, always on, cannot be disabled"


def route_channels(requested: Channel) -> Channel:
    """Resolve the channels that actually fire for a request.

    The VISUAL floor is always folded in, so no profile, mode, or per-verb
    override can ever silence the status bar. Every other requested channel is
    honored unchanged.
    """
    return requested | ALWAYS_ON_CHANNELS
