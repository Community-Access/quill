"""Build the announcement service for a shell (#1298-#1300).

Phase A gave every channel a sink; this is where the shells actually get them.
One factory serves all three hosts -- ``MainFrame``, ``AppShellFrame`` (Quill
Radio, Cast, Audio Studio, Converter, Weather, Podcasts) and QuillBeacon -- so a
channel added here appears in every app at once, which is the whole reason the
service exists.

Wiring is **duck-typed and optional**: a host that has no notification store, no
earcon player, or no echo history simply does not get that sink, and the channel
probe reports "no sink installed" rather than pretending. That keeps the factory
usable from a stub frame in a test, and keeps a companion app from needing every
mechanism QUILL has before it can announce anything.

One deliberate hand-off: the P0 braille dispatch (#1289) lives inside
``AnnouncementEngine.announce``, so the factory switches that off and installs a
:class:`BrailleSink` over the engine's public ``braille()`` instead. Same code
doing the writing; the policy now decides *whether* to write, which is what buys
dedupe, sticky errors, and the compact style.
"""

from __future__ import annotations

from typing import Any

from quill.core.announce import (
    AnnouncementPolicy,
    AnnouncementService,
    PolicyModes,
)
from quill.core.announce.adapters import (
    BrailleSink,
    EchoSink,
    HistorySink,
    NotificationSink,
    SoundSink,
    SpeechSink,
    TranscriptSink,
    VisualSink,
)


def policy_modes_from_settings(settings: Any) -> PolicyModes:
    """Read the accessibility settings block into policy modes (#1301).

    Quiet and Meeting are deliberately left off here: the shells run their
    announcements through the verbosity controller first, which already applies
    those modes, and applying them twice would suppress messages the controller
    had decided to allow.
    """
    return PolicyModes(
        speech_enabled=True,
        braille_enabled=bool(getattr(settings, "announcement_braille", True)),
        sound_enabled=bool(getattr(settings, "announcement_sounds_in_apps", True)),
        sound_instead_of_speech_when_quiet=bool(
            getattr(settings, "announcement_sound_instead_of_speech_when_quiet", True)
        ),
        braille_style=str(getattr(settings, "announcement_braille_style", "speech")),
    )


def build_announcement_service(host: Any) -> AnnouncementService:
    """Assemble the service for *host* from whatever mechanisms it has.

    Sink order is the delivery order, and it is not arbitrary: the earcon leads
    (a cue arriving after the speech is noise, not confirmation), speech and
    braille follow, and the recording channels come last so a capture failure
    can never delay what the user is waiting to hear.
    """
    settings = getattr(host, "settings", None)
    modes = policy_modes_from_settings(settings)
    dedupe = None
    seconds = getattr(settings, "announcement_braille_dedupe_seconds", None)
    if seconds is not None:
        from quill.core.announce.message import Channel
        from quill.core.announce.policy import DEDUPE_SECONDS

        dedupe = dict(DEDUPE_SECONDS)
        dedupe[Channel.BRAILLE] = float(seconds)
    service = AnnouncementService(policy=AnnouncementPolicy(modes, dedupe_seconds=dedupe))

    engine = getattr(host, "_announcement_engine", None)
    if engine is not None:
        _install_speech_and_braille(service, engine, settings)
    _install_optional(service, host)
    return service


def _install_speech_and_braille(service: AnnouncementService, engine: Any, settings: Any) -> None:
    """Speech through the engine, braille through the engine's own dispatch."""
    # The engine keeps owning backend selection, the no-double-talk rule and the
    # Prism context lifetime; this is an adapter, not a replacement.
    service.add_sink(
        SpeechSink(
            lambda text, force: engine.announce(text, force_speech=force),
            backend_name=lambda: str(getattr(engine.state(), "active_backend", "")),
        )
    )
    braille = getattr(engine, "braille", None)
    if not callable(braille):
        return
    # Hand braille policy to the service: the engine stops brailling on its own
    # so the message is not written twice.
    set_enabled = getattr(engine, "set_braille_enabled", None)
    if callable(set_enabled):
        set_enabled(False)
    sticky = bool(getattr(settings, "announcement_braille_sticky_errors", True))
    service.add_sink(
        BrailleSink(
            braille,
            supports_braille=getattr(engine, "braille_supported", None),
            backend_name=lambda: str(getattr(engine.state(), "backend_name", "")),
            hold=braille if sticky else None,
        )
    )


def _install_optional(service: AnnouncementService, host: Any) -> None:
    """Install every other channel the host can actually serve."""
    play = _sound_player(host)
    if play is not None:
        service.add_sink(SoundSink(play, is_enabled=_sound_enabled_check(host)))

    show = getattr(host, "_set_status", None)
    if callable(show):
        service.add_sink(VisualSink(show))

    record_notification = getattr(host, "_record_notification", None)
    if callable(record_notification):
        service.add_sink(NotificationSink(record_notification))

    record_spoken = getattr(host, "_record_spoken", None)
    if callable(record_spoken):
        service.add_sink(EchoSink(record_spoken))

    history = _history_recorder(host)
    if history is not None:
        service.add_sink(HistorySink(history))

    service.add_sink(TranscriptSink(_transcript_writer()))


def _sound_player(host: Any) -> Any | None:
    """The host's earcon player, or None when this app has no sound."""
    if not bool(getattr(getattr(host, "settings", None), "announcement_sounds_in_apps", True)):
        return None
    try:
        from quill.ui.sound_manager import post_sound
    except Exception:  # noqa: BLE001 - a missing sound stack is not an error
        return None
    return post_sound


def _sound_enabled_check(host: Any) -> Any:
    """Honour settings.sound_events_disabled without the sink knowing it exists."""
    settings = getattr(host, "settings", None)

    def _enabled(event: str) -> bool:
        raw = str(getattr(settings, "sound_events_disabled", "") or "")
        disabled = {item.strip() for item in raw.split(",") if item.strip()}
        return event not in disabled

    return _enabled


def _history_recorder(host: Any) -> Any | None:
    """Feed the verbosity announcement history when the shell has one."""
    controller = getattr(host, "_verbosity_controller", None)
    history = getattr(controller, "history", None)
    record = getattr(history, "record_text", None) or getattr(history, "record", None)
    if not callable(record):
        return None

    def _record(text: str, severity: str) -> None:
        try:
            record(text)  # type: ignore[misc]
        except TypeError:
            # The richer history API takes a rendered announcement; a plain
            # string is not worth adapting here, so skip rather than guess.
            return

    return _record


def _transcript_writer() -> Any:
    """The headless capture the UIA regression suite asserts against."""

    def _write(text: str) -> None:
        try:
            from quill.platform.sr_announce import announce as capture
        except Exception:  # noqa: BLE001 - capture is best-effort
            return
        capture(text)

    return _write
