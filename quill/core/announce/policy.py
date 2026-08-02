"""Which channels carry an announcement, and how loudly (#1291).

Quiet Mode, Meeting Mode, profile suppression, repetition collapse and the
announcement budget all existed -- wired into ``MainFrame`` alone. Six companion
apps and Beacon could mute nothing, and severity was a single boolean, so an
error and a routine confirmation were treated identically.

The policy is pure: settings and modes in, a per-channel :class:`Decision` out.
No wx, no I/O, and an injectable clock so the throttle and dedupe windows are
deterministic under test.

The severity matrix it implements:

===========  =====================  =========================  ===========  ==========================
Severity     Speech                 Braille                    Sound        Visual
===========  =====================  =========================  ===========  ==========================
ROUTINE      polite, throttled      flash, deduped             soft cue     status
INFO         polite                 flash                      cue          status
WARNING      interrupts             flash                      cue          status + notification
ERROR        interrupts, never      sticky                     error cue    status + notification
             suppressed
===========  =====================  =========================  ===========  ==========================

One behaviour deserves calling out because it is impossible today: **Quiet and
Meeting Mode drop speech only and keep braille.** A braille user in a meeting
wants exactly that -- silence in the room, and the message still under their
fingers.

wx-free, strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from quill.core.announce.message import ALL_CHANNELS, Announcement, Channel, Severity

#: Per-channel suppression windows for an identical announcement, in seconds.
#: Braille is the shortest because a flash physically replaces what the reader is
#: touching; speech relies on the existing verbosity throttle for its own rules.
DEDUPE_SECONDS: dict[Channel, float] = {
    Channel.BRAILLE: 2.0,
    Channel.SOUND: 1.0,
    Channel.SPEECH: 0.0,
    Channel.VISUAL: 0.0,
}


@dataclass(frozen=True, slots=True)
class Decision:
    """What the policy decided for one announcement."""

    channels: frozenset[Channel]
    interrupt: bool = False
    sticky: bool = False
    braille_text: str = ""
    reason: str = ""

    def allows(self, channel: Channel) -> bool:
        return channel in self.channels


@dataclass
class PolicyModes:
    """The live mute state a shell hands the policy.

    ``quiet`` and ``meeting`` mirror the verbosity modes; ``braille_enabled``,
    ``sound_enabled`` and ``speech_enabled`` mirror the user's settings. Keeping
    them in one value object means a companion app can honour all of it without
    importing the verbosity system.
    """

    quiet: bool = False
    meeting: bool = False
    speech_enabled: bool = True
    braille_enabled: bool = True
    sound_enabled: bool = True
    #: Play the cue even when speech is muted, so a Quiet-Mode action still
    #: confirms itself audibly (announcement_sound_instead_of_speech_when_quiet).
    sound_instead_of_speech_when_quiet: bool = False
    #: "compact" renders the short braille labels (#425); "speech" sends the
    #: spoken string so nobody loses information by default.
    braille_style: str = "speech"


class AnnouncementPolicy:
    """Resolve settings + modes + severity into a per-channel decision."""

    def __init__(
        self,
        modes: PolicyModes | None = None,
        *,
        clock: Callable[[], float] | None = None,
        dedupe_seconds: dict[Channel, float] | None = None,
    ) -> None:
        self._modes = modes or PolicyModes()
        self._clock = clock or time.monotonic
        self._dedupe = dict(DEDUPE_SECONDS if dedupe_seconds is None else dedupe_seconds)
        self._last: dict[tuple[Channel, str], float] = {}

    @property
    def modes(self) -> PolicyModes:
        return self._modes

    def set_modes(self, modes: PolicyModes) -> None:
        self._modes = modes

    def decide(self, announcement: Announcement) -> Decision:
        """Which channels carry *announcement*, and how."""
        severity = announcement.severity
        modes = self._modes
        allowed: set[Channel] = set(ALL_CHANNELS)
        reason = ""

        # ERROR is never suppressed by any mode, setting or throttle. A user must
        # not be able to configure away the message that says something broke.
        if severity is not Severity.ERROR:
            if not modes.speech_enabled:
                allowed.discard(Channel.SPEECH)
                reason = "speech disabled"
            if modes.quiet or modes.meeting:
                allowed.discard(Channel.SPEECH)
                reason = "quiet mode" if modes.quiet else "meeting mode"
                if not modes.sound_instead_of_speech_when_quiet:
                    allowed.discard(Channel.SOUND)
            if not modes.braille_enabled:
                allowed.discard(Channel.BRAILLE)
            if not modes.sound_enabled:
                allowed.discard(Channel.SOUND)
            if not announcement.sound_event:
                allowed.discard(Channel.SOUND)
            allowed = self._apply_dedupe(announcement, allowed)

        # WARNING and ERROR earn a notification entry; nothing else does, or the
        # list becomes a log nobody reads.
        if not severity.is_problem:
            allowed.discard(Channel.NOTIFICATION)

        return Decision(
            channels=frozenset(allowed),
            interrupt=severity.interrupts,
            sticky=severity is Severity.ERROR,
            braille_text=self._braille_text(announcement),
            reason=reason,
        )

    def _apply_dedupe(self, announcement: Announcement, allowed: set[Channel]) -> set[Channel]:
        """Drop channels whose identical message is still on screen/under hand."""
        now = self._clock()
        for channel in (Channel.BRAILLE, Channel.SOUND, Channel.SPEECH, Channel.VISUAL):
            window = self._dedupe.get(channel, 0.0)
            if window <= 0 or channel not in allowed:
                continue
            key = (channel, announcement.key)
            last = self._last.get(key)
            if last is not None and (now - last) < window:
                allowed.discard(channel)
                continue
            self._last[key] = now
        return allowed

    def _braille_text(self, announcement: Announcement) -> str:
        """The display form for this announcement under the current style."""
        if announcement.braille_text:
            return announcement.braille_text
        if self._modes.braille_style != "compact":
            return ""
        return compact_braille(announcement)


#: Short labels for the compact braille style (#425): position before prose.
_COMPACT_LABELS: tuple[tuple[str, str], ...] = (
    ("page", "p"),
    ("line", "l"),
    ("column", "c"),
    ("selection", "sel"),
)


def compact_braille(announcement: Announcement) -> str:
    """Render the compact braille form: ``p7/87 l14 c3 mod`` (#425).

    Position first, prose last -- a 40-cell display is a scarce resource, and a
    reader checking where they are should not have to pan past a sentence to
    find out. Falls back to the spoken text when the announcement carries no
    position context, because a compact render of prose is just the prose.
    """
    context = announcement.context
    parts: list[str] = []
    page = context.get("page")
    pages = context.get("pages")
    if page is not None:
        parts.append(f"p{page}/{pages}" if pages is not None else f"p{page}")
    for key, label in _COMPACT_LABELS[1:]:
        value = context.get(key)
        if value is not None:
            parts.append(f"{label}{value}")
    if context.get("modified"):
        parts.append("mod")
    if not parts:
        return announcement.text
    return " ".join(parts)
