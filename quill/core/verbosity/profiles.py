"""Verbosity profiles (verbosity §6) and the announcement-verbosity bridge.

Four built-in profiles set the overall talkativeness ladder:

- **Beginner** — full context for every verb, all channels, friendly chimes.
- **Normal** — informative but not chatty; the default for a new install.
- **Expert** — routine confirmations suppressed; errors still speak; sound is
  error-only.
- **Quiet** — minimal: speech and earcons off, the braille + visual floor only.
  Suitable for a meeting room.

:class:`CustomProfile` is a user-defined profile (a base plus a channel mix and
per-verb / per-chord / template / data-order overrides) that round-trips to JSON.

This module also carries the *read-side contract* for the legacy
``announcement_verbosity`` setting (verbosity §1.1 wiring):
:func:`profile_for_announcement_verbosity` and :func:`active_profile` map the
existing ``minimal`` / ``normal`` / ``verbose`` knob onto the profile ladder, so
the setting finally has a real consumer. The routing engine that acts on the
resolved profile arrives in sub-PR 1.2.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.verbosity.channels import DEFAULT_CHANNELS, Channel

__all__ = [
    "SoundPolicy",
    "VerbosityProfile",
    "CustomProfile",
    "BEGINNER",
    "NORMAL",
    "EXPERT",
    "QUIET",
    "BUILTIN_PROFILES",
    "DEFAULT_PROFILE",
    "profile_for_announcement_verbosity",
    "active_profile",
]


class SoundPolicy:
    """Allowed values for a profile's earcon policy."""

    ALL = "all"
    ERRORS_ONLY = "errors_only"
    OFF = "off"


@dataclass(frozen=True, slots=True)
class VerbosityProfile:
    """A built-in talkativeness preset."""

    name: str
    channels: Channel
    sound_policy: str
    suppress_routine: bool
    description: str


BEGINNER = VerbosityProfile(
    name="Beginner",
    channels=DEFAULT_CHANNELS,
    sound_policy=SoundPolicy.ALL,
    suppress_routine=False,
    description="Full context for every action, all channels, friendly chimes.",
)
NORMAL = VerbosityProfile(
    name="Normal",
    channels=DEFAULT_CHANNELS,
    sound_policy=SoundPolicy.ALL,
    suppress_routine=False,
    description="Informative but not chatty. The default.",
)
EXPERT = VerbosityProfile(
    name="Expert",
    channels=Channel.SPEECH | Channel.BRAILLE | Channel.SOUND | Channel.VISUAL,
    sound_policy=SoundPolicy.ERRORS_ONLY,
    suppress_routine=True,
    description="Routine confirmations suppressed; errors still speak; subtle clicks.",
)
QUIET = VerbosityProfile(
    name="Quiet",
    channels=Channel.BRAILLE | Channel.VISUAL,
    sound_policy=SoundPolicy.OFF,
    suppress_routine=True,
    description="Minimal: braille and visual only. Suitable for meeting rooms.",
)

#: Built-in profiles keyed by name.
BUILTIN_PROFILES: dict[str, VerbosityProfile] = {
    profile.name: profile for profile in (BEGINNER, NORMAL, EXPERT, QUIET)
}

#: The profile a fresh install starts on.
DEFAULT_PROFILE = NORMAL


@dataclass(frozen=True, slots=True)
class CustomProfile:
    """A user-defined profile: a base preset plus overrides, JSON round-trippable.

    The dataclass is frozen (no attribute reassignment) but its mapping fields
    are ordinary dicts; treat instances as values and build a new one to change
    them. :meth:`to_dict` / :meth:`from_dict` give a stable JSON shape with the
    channel mix serialized as channel names.
    """

    name: str
    base: str = "Normal"
    channels: Channel = DEFAULT_CHANNELS
    per_verb_overrides: dict[str, str] = field(default_factory=dict)
    per_chord_overrides: dict[str, str] = field(default_factory=dict)
    templates: dict[str, str] = field(default_factory=dict)
    data_order: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        channel_names = [
            channel.name
            for channel in Channel
            if channel.value and channel in self.channels and channel.name is not None
        ]
        return {
            "name": self.name,
            "base": self.base,
            "channels": channel_names,
            "per_verb_overrides": dict(self.per_verb_overrides),
            "per_chord_overrides": dict(self.per_chord_overrides),
            "templates": dict(self.templates),
            "data_order": {key: list(value) for key, value in self.data_order.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomProfile:
        channels = Channel.NONE
        for channel_name in data.get("channels", ()):
            channels |= Channel[str(channel_name)]
        if channels == Channel.NONE:
            channels = DEFAULT_CHANNELS
        return cls(
            name=str(data["name"]),
            base=str(data.get("base", "Normal")),
            channels=channels,
            per_verb_overrides=dict(data.get("per_verb_overrides", {})),
            per_chord_overrides=dict(data.get("per_chord_overrides", {})),
            templates=dict(data.get("templates", {})),
            data_order={
                str(key): [str(item) for item in value]
                for key, value in data.get("data_order", {}).items()
            },
        )


# The legacy 'minimal'/'normal'/'verbose' knob maps onto the profile ladder.
_VERBOSITY_LADDER: dict[str, VerbosityProfile] = {
    "minimal": EXPERT,
    "normal": NORMAL,
    "verbose": BEGINNER,
}


def profile_for_announcement_verbosity(value: str) -> VerbosityProfile:
    """Map the legacy ``announcement_verbosity`` knob onto a built-in profile.

    ``minimal`` -> Expert, ``normal`` -> Normal, ``verbose`` -> Beginner.
    Anything unrecognized falls back to :data:`DEFAULT_PROFILE`.
    """
    return _VERBOSITY_LADDER.get(value.strip().lower(), DEFAULT_PROFILE)


class _HasAnnouncementVerbosity(Protocol):
    announcement_verbosity: str


def active_profile(settings: _HasAnnouncementVerbosity) -> VerbosityProfile:
    """Resolve the active profile from a settings object's verbosity knob.

    This is the real consumer of ``settings.announcement_verbosity`` that the
    setting previously lacked; the engine in sub-PR 1.2 builds on it.
    """
    return profile_for_announcement_verbosity(getattr(settings, "announcement_verbosity", "normal"))
