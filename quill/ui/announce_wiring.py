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


class CoalescingBrailleWriter:
    """Collapse a burst of *different* braille messages into fewer writes.

    The dedupe layers only suppress an identical repeat; a burst of different
    messages (a status cascade, a rapid poll) still flashes across the display
    one on top of the next, faster than anyone can read cell one. A braille
    flash replaces whatever the user's fingers were on, so a burst must
    settle.

    Design: the first message in a quiet period writes through immediately
    (no added latency), which opens a short conflation window; messages
    arriving inside the window replace each other and only the newest is
    written when the window closes. A sustained burst therefore lands as one
    write per window instead of one per message.

    Sticky ERROR messages bypass this wrapper entirely (the sink's ``hold``
    hook is handed the raw writer), so nothing urgent is ever conflated.

    ``schedule(delay_ms, fn)`` must return a timer object with ``IsRunning()``;
    by default it is ``wx.CallLater`` on the UI thread. Anywhere a timer
    cannot exist (worker thread, headless test, no running app) every message
    writes straight through -- the pre-coalescing behaviour.
    """

    WINDOW_MS = 150

    def __init__(self, write: Any, schedule: Any = None) -> None:
        self._write = write
        self._schedule = schedule
        self._pending: str = ""
        self._timer: Any = None

    def _default_schedule(self, delay_ms: int, fn: Any) -> Any:
        import wx

        if wx.GetApp() is None or not wx.IsMainThread():
            return None
        return wx.CallLater(delay_ms, fn)

    def _arm(self) -> None:
        schedule = self._schedule or self._default_schedule
        try:
            self._timer = schedule(self.WINDOW_MS, self._flush)
        except Exception:  # noqa: BLE001 - no event loop: no window, write through
            self._timer = None

    def __call__(self, text: str) -> str:
        timer = self._timer
        if timer is not None and bool(getattr(timer, "IsRunning", lambda: False)()):
            self._pending = text
            return ""
        result = str(self._write(text) or "")
        self._arm()
        return result

    def _flush(self) -> None:
        text = self._pending
        self._pending = ""
        if text:
            # Errors are logged by the bridge itself; a deferred write has no
            # caller left to hand them to.
            self._write(text)
            self._arm()


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


def policy_from_settings(settings: Any) -> AnnouncementPolicy:
    """The announcement policy the current *settings* describe (pure)."""
    modes = policy_modes_from_settings(settings)
    dedupe = None
    seconds = getattr(settings, "announcement_braille_dedupe_seconds", None)
    if seconds is not None:
        from quill.core.announce.message import Channel
        from quill.core.announce.policy import DEDUPE_SECONDS

        dedupe = dict(DEDUPE_SECONDS)
        dedupe[Channel.BRAILLE] = float(seconds)
    return AnnouncementPolicy(modes, dedupe_seconds=dedupe)


def refresh_announcement_policy(host: Any) -> None:
    """Re-derive the cached service's policy from *host*'s current settings.

    The service is built lazily once and held for the life of the shell, with
    its policy snapshotted from settings at that moment — so until this hook
    existed, every announcement setting (braille style, dedupe hold-back,
    which severities interrupt) silently required a restart while the
    Preferences panel implied it applied (the config-snapshot staleness class,
    polish.md P0.3). Called from the settings-apply path; a host whose service
    was never built has nothing to refresh.
    """
    service = getattr(host, "_announcement_service", None)
    if service is None:
        return
    service.set_policy(policy_from_settings(getattr(host, "settings", None)))


def refresh_live_policies(host: Any) -> None:
    """Re-derive every long-lived policy snapshot from *host*'s settings.

    The P0.3 staleness class in one place: controllers built lazily snapshot
    their config and hold it for the life of the shell, so a Preferences change
    silently meant "after the next restart". The settings-apply path calls this
    once; each refresh is individually best-effort because a settings apply
    must never raise.
    """
    try:
        refresh_announcement_policy(host)
    except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
        pass
    try:
        ctrl = getattr(host, "_verbosity_controller", None)
        if ctrl is not None:
            ctrl.apply_settings(host.settings)
    except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
        pass
    try:
        watch = getattr(host, "_watch_service", None)
        if watch is not None:
            watch.refresh_policy(host.settings)
    except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
        pass
    # Model-lifecycle limits (Low-resource mode / Unload idle models after):
    # not a lazy snapshot like the three above, but the same contract — a
    # settings-derived runtime policy that must track the dialog.
    try:
        from quill.core import lifecycle_service
        from quill.core.speech.service import detect_total_ram_gb

        settings = getattr(host, "settings", None)
        lifecycle_service.configure(
            low_resource_mode=bool(getattr(settings, "low_resource_mode", False)),
            idle_unload_minutes=int(getattr(settings, "idle_unload_minutes", 10)),
            total_ram_gb=detect_total_ram_gb(),
        )
        sweep = getattr(host, "_start_lifecycle_sweep_timer", None)
        if callable(sweep):
            sweep()
    except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
        pass


def build_announcement_service(host: Any) -> AnnouncementService:
    """Assemble the service for *host* from whatever mechanisms it has.

    Sink order is the delivery order, and it is not arbitrary: the earcon leads
    (a cue arriving after the speech is noise, not confirmation), speech and
    braille follow, and the recording channels come last so a capture failure
    can never delay what the user is waiting to hear.
    """
    settings = getattr(host, "settings", None)
    service = AnnouncementService(policy=policy_from_settings(settings))

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
    # Normal messages go through the burst coalescer; the sticky-error hold
    # path keeps the raw writer so an ERROR is never delayed or conflated.
    service.add_sink(
        BrailleSink(
            CoalescingBrailleWriter(braille),
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

    # The status sink must be a QUIET status write. MainFrame._set_status
    # speaks (it routes back into sr_announce, whose handler is _announce),
    # so wiring it here closes an announce -> status -> announce cycle that
    # recursed until the UI heartbeat declared a hang (calculator, 2026-08-05
    # thread dump). Prefer the explicit quiet setter; the companion shells'
    # _set_status is already a bare SetStatusText and stays a valid fallback.
    show = getattr(host, "_set_status_quiet", None) or getattr(host, "_set_status", None)
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
