"""Accessible announcement helpers (PRD sections 17.6, 18.4).

QuillBeacon announces through the status bar (always visible, screen-reader
reachable) and an optional wx bell, never through color or transient popups.
``Announcer`` wraps a wx frame's status bar so the rest of the UI calls one
method and stays consistent. verbosity controls how much is spoken.
"""

from __future__ import annotations

from typing import Literal

Verbosity = Literal["minimal", "normal", "verbose"]

_VERBOSITY_ORDER = {"minimal": 0, "normal": 1, "verbose": 2}


def _post_sound(event: str) -> None:
    """Play an earcon; silent (never fatal) where there is no sound stack."""
    from quill.ui.companion_cues import post_cue

    post_cue(event)


class Announcer:
    """Status-bar announcer with configurable verbosity (PRD 18.4, 29.2)."""

    def __init__(self, frame, *, verbosity: Verbosity = "normal") -> None:
        self.frame = frame
        self.verbosity = verbosity

    def set_verbosity(self, v: Verbosity) -> None:
        self.verbosity = v

    def say(self, message: str, level: Verbosity = "normal", *, sound: str = "") -> None:
        """Announce ``message`` if verbosity permits (#1300).

        QuillBeacon had **no screen-reader speech at all**: this method set
        the status bar and, failing that, the window title -- and screen
        readers announce neither on their own. So "QuillBeacon ready",
        result counts, filter changes and undo confirmations were silent.
        The status bar still updates (the visual floor), and the message now
        also goes to the announcement service, which speaks it, brailles it
        and cues it.

        The two positional parameters are unchanged on purpose: Beacon's ~40
        call sites keep working untouched. ``sound`` is keyword-only and names
        a :class:`~quill.core.sound_events.SoundEvent` to lead with, for the
        two moments Beacon has an earcon for -- an item captured and a sync
        finishing (#1302).
        """
        if _VERBOSITY_ORDER[level] > _VERBOSITY_ORDER[self.verbosity]:
            return
        bar = self.frame.GetStatusBar() if hasattr(self.frame, "GetStatusBar") else None
        if bar is not None:
            self.frame.SetStatusText(message)
        else:
            self.frame.SetTitle(message)
        self._speak(message, level, sound)

    def _speak(self, message: str, level: Verbosity, sound: str = "") -> None:
        """Hand the message to the announcement service; never raises.

        Best-effort by design: an announcement failing must not break the
        action the user just took, and Beacon ran without any speech at all
        until now, so a silent fallback is no worse than the status quo.
        """
        try:
            from quill.core.announce import Announcement, Severity

            service = self._service()
            if service is None:
                return
            severity = Severity.INFO if level == "normal" else Severity.ROUTINE
            service.announce(Announcement(text=message, severity=severity, sound_event=sound))
        except Exception:  # noqa: BLE001 - announcing must never break Beacon
            return

    def _service(self):
        """Beacon's announcement service, built on first use."""
        service = getattr(self, "_announcement_service", None)
        if service is not None:
            return service
        host = getattr(self.frame, "_announcement_engine", None)
        from quill.core.announce import AnnouncementService
        from quill.core.announce.adapters import SoundSink, SpeechSink, VisualSink

        service = AnnouncementService()
        # The earcon sink leads, exactly as ``announce_wiring`` orders it for
        # the other apps: a cue arriving after the words is an echo, not a
        # confirmation. Beacon builds its own service (it is not an
        # AppShellFrame), so without this its two cues had nowhere to land
        # (#1302). ``post_sound`` honours settings.sound_events_disabled
        # through the player itself and no-ops when there is no sound stack.
        service.add_sink(SoundSink(_post_sound))
        if host is None:
            from quill.platform.windows.prism_bridge import AnnouncementEngine

            host = AnnouncementEngine()
            self.frame._announcement_engine = host
        service.add_sink(SpeechSink(lambda text, force: host.announce(text, force_speech=force)))
        braille = getattr(host, "braille", None)
        if callable(braille):
            from quill.core.announce.adapters import BrailleSink

            host.set_braille_enabled(False)
            service.add_sink(
                BrailleSink(braille, supports_braille=getattr(host, "braille_supported", None))
            )
        service.add_sink(VisualSink(lambda text: None))
        self._announcement_service = service
        return service

    def announce_count(self, count: int, filtered: bool = False) -> None:
        word = "results" if count != 1 else "result"
        if filtered:
            self.say(f"{count} {word} (filtered)")
        else:
            self.say(f"{count} {word}")

    def announce_filters(self, filters: list[str]) -> None:
        if not filters:
            self.say("No filters active", "minimal")
            return
        self.say("Filters: " + ", ".join(filters))

    def where_am_i(self, context: dict) -> str:
        """Build the 'Where Am I?' announcement string (PRD 17.6)."""
        parts = []
        if context.get("area"):
            parts.append(context["area"])
        if context.get("collection"):
            parts.append(f"collection {context['collection']}")
        if context.get("search"):
            parts.append(f"search '{context['search']}'")
        if context.get("filters"):
            parts.append("filters " + ", ".join(context["filters"]))
        if context.get("sort"):
            parts.append(f"sort {context['sort']}")
        if context.get("selected"):
            parts.append(f"selected {context['selected']}")
        if context.get("position") and context.get("count"):
            parts.append(f"{context['position']} of {context['count']}")
        if context.get("sync"):
            parts.append(f"sync {context['sync']}")
        return ". ".join(parts) if parts else "QuillBeacon"
