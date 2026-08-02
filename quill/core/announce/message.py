"""What an announcement *is*, independent of how it is delivered (#1290).

Before this, "an announcement" meant "a string passed to ``_announce``", and
everything else about it -- how urgent, which channels should carry it, whether
it earns an earcon -- was either implicit or a single ``force_speech`` boolean.
That is why an error and a routine confirmation were indistinguishable, and why
braille, sound, and notifications could not be reasoned about at all.

An :class:`Announcement` is a plain value: no wx, no ctypes, no platform. The
service fans it out to sinks; the sinks own the delivery.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """How urgent an announcement is -- the axis ``force_speech`` could not express.

    ``ROUTINE`` is the default confirmation ("Saved"): polite, throttled, easy to
    miss on purpose. ``INFO`` is worth hearing but not worth interrupting for.
    ``WARNING`` and ``ERROR`` interrupt, and ``ERROR`` is never suppressed by any
    profile, mode, or throttle -- a user must not be able to configure away the
    message that says something went wrong.
    """

    ROUTINE = "routine"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def interrupts(self) -> bool:
        """True when this severity should cut across whatever is being spoken."""
        return self in (Severity.WARNING, Severity.ERROR)

    @property
    def is_problem(self) -> bool:
        """True for the severities that also belong in the notification list."""
        return self in (Severity.WARNING, Severity.ERROR)


class Channel(Enum):
    """Where an announcement can go. One sink family per channel."""

    SPEECH = "speech"
    BRAILLE = "braille"
    SOUND = "sound"
    VISUAL = "visual"
    NOTIFICATION = "notification"
    ECHO = "echo"
    HISTORY = "history"
    TRANSCRIPT = "transcript"


#: Every channel, for an announcement that names none of its own.
ALL_CHANNELS: frozenset[Channel] = frozenset(Channel)


@dataclass(frozen=True, slots=True)
class Announcement:
    """One thing to tell the user, on whichever channels are appropriate.

    ``text`` is the spoken/visual string. ``braille_text`` is the display form
    when it should differ (the compact renderer, or a sticky error); empty means
    "use ``text``", so no caller loses information by not thinking about braille.

    ``channels`` restricts delivery when a caller genuinely knows better -- a
    visual-only status line, say. Left as ``None`` it means "every channel the
    policy allows", which is what almost every call site wants.

    ``dedupe_key`` groups messages that should collapse even when their text
    differs slightly ("Downloading 3 of 40" ...); it defaults to the text.
    """

    text: str
    braille_text: str = ""
    severity: Severity = Severity.ROUTINE
    channels: frozenset[Channel] | None = None
    sound_event: str = ""
    region: str = ""
    dedupe_key: str = ""
    context: dict[str, object] = field(default_factory=dict)

    @property
    def force_speech(self) -> bool:
        """Compatibility alias for the boolean this severity replaced.

        ``AnnouncementEngine.announce(..., force_speech=)`` still speaks this
        language, and the speech sink still has to.
        """
        return self.severity.interrupts

    @property
    def braille(self) -> str:
        """The braille form: the explicit one, else the spoken text."""
        return self.braille_text or self.text

    @property
    def key(self) -> str:
        """The identity used for de-duplication and throttling."""
        return self.dedupe_key or self.text

    def wants(self, channel: Channel) -> bool:
        """True when the caller has not excluded *channel*."""
        return self.channels is None or channel in self.channels


def routine(text: str, **kwargs: object) -> Announcement:
    """A routine confirmation -- the default for ordinary status."""
    return Announcement(text=text, severity=Severity.ROUTINE, **kwargs)  # type: ignore[arg-type]


def info(text: str, **kwargs: object) -> Announcement:
    """Worth hearing, not worth interrupting for."""
    return Announcement(text=text, severity=Severity.INFO, **kwargs)  # type: ignore[arg-type]


def warning(text: str, **kwargs: object) -> Announcement:
    """Something the user should act on; interrupts, and is recorded."""
    return Announcement(text=text, severity=Severity.WARNING, **kwargs)  # type: ignore[arg-type]


def error(text: str, **kwargs: object) -> Announcement:
    """Something went wrong; interrupts, is recorded, and is never suppressed."""
    return Announcement(text=text, severity=Severity.ERROR, **kwargs)  # type: ignore[arg-type]
