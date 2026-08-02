"""Each sink drives its existing mechanism faithfully (#1292-#1297).

These are adapters over things that already work, so the tests assert the
adaptation: the right call, with the right arguments, under the right severity
-- and the failure behaviour that makes the whole fan-out safe.
"""

from __future__ import annotations

from quill.core.announce import (
    Announcement,
    AnnouncementPolicy,
    AnnouncementService,
    Channel,
    PolicyModes,
    Severity,
    error,
    routine,
    warning,
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


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


# -- SpeechSink (#1292) --------------------------------------------------------


def test_speech_maps_severity_onto_the_engine_interrupt_flag() -> None:
    calls: list[tuple[str, bool]] = []
    sink = SpeechSink(lambda text, force: calls.append((text, force)) or None)

    sink.deliver(routine("Saved"))
    sink.deliver(error("Disk full"))

    assert calls == [("Saved", False), ("Disk full", True)]


def test_speech_reports_an_engine_error_instead_of_swallowing_it() -> None:
    sink = SpeechSink(lambda _t, _f: "Prism announcement failed: boom")

    try:
        sink.deliver(routine("Saved"))
    except RuntimeError as exc:
        assert "boom" in str(exc)
    else:  # pragma: no cover - the raise is the contract
        raise AssertionError("a failed speech call must surface")

    assert "boom" in sink.probe().last_error


def test_speech_probe_is_honest_about_a_status_only_backend() -> None:
    sink = SpeechSink(lambda _t, _f: None, backend_name=lambda: "status_only")
    assert sink.probe().available is False
    assert "no speech backend" in sink.probe().detail


# -- BrailleSink (#1293) -------------------------------------------------------


def test_braille_sends_the_braille_form() -> None:
    sent: list[str] = []
    sink = BrailleSink(lambda text: sent.append(text) or "")

    sink.deliver(Announcement(text="Long spoken form", braille_text="short"))

    assert sent == ["short"]


def test_braille_falls_back_to_the_spoken_text() -> None:
    # Nobody loses information by not thinking about braille at the call site.
    sent: list[str] = []
    sink = BrailleSink(lambda text: sent.append(text) or "")

    sink.deliver(routine("Now playing: A Song"))

    assert sent == ["Now playing: A Song"]


def test_an_error_holds_the_display_rather_than_flashing_past() -> None:
    held: list[str] = []
    flashed: list[str] = []
    sink = BrailleSink(lambda text: flashed.append(text) or "", hold=held.append)

    sink.deliver(error("Could not save"))

    assert held == ["Could not save"] and flashed == []


def test_braille_probe_says_when_no_display_is_connected() -> None:
    sink = BrailleSink(lambda _t: "", supports_braille=lambda: False)
    status = sink.probe()
    assert status.available is False
    assert "no braille display" in status.detail


def test_braille_failure_never_costs_the_user_their_speech() -> None:
    # The property that made #1283 worth routing separately, asserted end to end
    # through the service rather than on the sink alone.
    spoken: list[str] = []
    service = AnnouncementService([
        BrailleSink(lambda _t: "display disconnected"),
        SpeechSink(lambda text, _f: spoken.append(text) or None),
    ])

    report = service.announce(routine("Recording started"))

    assert spoken == ["Recording started"]
    assert Channel.BRAILLE in report.failed


# -- SoundSink (#1294) ---------------------------------------------------------


def test_sound_plays_the_announcement_event() -> None:
    played: list[str] = []
    sink = SoundSink(played.append)

    sink.deliver(Announcement(text="Saved", sound_event="document_saved"))

    assert played == ["document_saved"]


def test_sound_honours_a_disabled_event() -> None:
    played: list[str] = []
    sink = SoundSink(played.append, is_enabled=lambda event: event != "document_saved")

    sink.deliver(Announcement(text="Saved", sound_event="document_saved"))

    assert played == []


def test_the_cue_leads_the_message() -> None:
    # Installation order is the mechanism: an earcon that arrives after the
    # speech is not a confirmation, it is noise.
    order: list[str] = []
    service = AnnouncementService([
        SoundSink(lambda event: order.append(f"sound:{event}")),
        SpeechSink(lambda text, _f: order.append(f"speech:{text}") or None),
    ])

    service.announce(Announcement(text="Saved", sound_event="document_saved"))

    assert order == ["sound:document_saved", "speech:Saved"]


def test_quiet_mode_can_confirm_with_a_cue_instead_of_speech() -> None:
    order: list[str] = []
    modes = PolicyModes(quiet=True, sound_instead_of_speech_when_quiet=True)
    service = AnnouncementService(
        [
            SoundSink(lambda event: order.append(f"sound:{event}")),
            SpeechSink(lambda text, _f: order.append(f"speech:{text}") or None),
        ],
        policy=AnnouncementPolicy(modes),
    )

    service.announce(Announcement(text="Saved", sound_event="document_saved"))

    assert order == ["sound:document_saved"]


# -- VisualSink and NotificationSink (#1295) ----------------------------------


def test_the_message_slot_survives_a_standing_status_refresh() -> None:
    clock = _Clock()
    shown: list[str] = []
    sink = VisualSink(shown.append, clock=clock, persistence_seconds=5.0)

    sink.deliver(routine("Saved note.md"))
    clock.now = 2.0

    assert sink.last_message() == "Saved note.md"


def test_the_message_slot_expires() -> None:
    clock = _Clock()
    sink = VisualSink(lambda _t: None, clock=clock, persistence_seconds=5.0)

    sink.deliver(routine("Saved note.md"))
    clock.now = 6.0

    assert sink.last_message() == ""


def test_only_warnings_and_errors_are_recorded_as_notifications() -> None:
    recorded: list[tuple[str, str]] = []
    sink = NotificationSink(lambda text, category: recorded.append((text, category)))

    sink.deliver(routine("Saved"))
    sink.deliver(warning("Low disk space"))
    sink.deliver(error("Save failed"))

    assert recorded == [("Low disk space", "warning"), ("Save failed", "error")]


# -- capture sinks (#1296) -----------------------------------------------------


def test_echo_history_and_transcript_all_see_the_message() -> None:
    echo: list[str] = []
    history: list[tuple[str, str]] = []
    transcript: list[str] = []
    service = AnnouncementService([
        EchoSink(echo.append),
        HistorySink(lambda text, severity: history.append((text, severity))),
        TranscriptSink(transcript.append),
    ])

    service.announce(warning("Low disk space"))

    assert echo == ["Low disk space"]
    assert history == [("Low disk space", "warning")]
    assert transcript == ["Low disk space"]


def test_the_transcript_works_with_nothing_attached() -> None:
    # CI has no screen reader, and the UIA suite proves "QUILL said X" by
    # reading this.
    captured: list[str] = []
    service = AnnouncementService([TranscriptSink(captured.append)])

    service.announce(routine("Saved"))

    assert captured == ["Saved"]


# -- the probe (#1297) ---------------------------------------------------------


def test_the_probe_reports_every_channel_with_its_backend() -> None:
    service = AnnouncementService([
        SpeechSink(lambda _t, _f: None, backend_name=lambda: "JAWS"),
        BrailleSink(lambda _t: "", supports_braille=lambda: False, backend_name=lambda: "JAWS"),
    ])

    statuses = {status.channel: status for status in service.probe()}

    assert statuses[Channel.SPEECH].available is True
    assert statuses[Channel.SPEECH].backend == "JAWS"
    assert statuses[Channel.BRAILLE].available is False
    assert "no braille display" in statuses[Channel.BRAILLE].detail
    assert statuses[Channel.SOUND].available is False  # no sink installed


def test_a_delivery_failure_shows_up_in_the_probe() -> None:
    service = AnnouncementService([BrailleSink(lambda _t: "display disconnected")])

    service.announce(routine("Saved"))
    statuses = {status.channel: status for status in service.probe()}

    assert "display disconnected" in statuses[Channel.BRAILLE].last_error


def test_the_probe_is_serialisable_for_the_support_bundle() -> None:
    service = AnnouncementService([SpeechSink(lambda _t, _f: None, backend_name=lambda: "NVDA")])

    payload = service.diagnostics()

    assert payload["announce_channels"] == ["speech"]
    entries = payload["announce_sinks"]
    assert isinstance(entries, list)
    speech = next(entry for entry in entries if entry["channel"] == "speech")
    assert speech["backend"] == "NVDA"
    assert set(speech) == {"channel", "available", "backend", "detail", "last_error"}


def test_severity_survives_the_whole_trip() -> None:
    seen: list[Severity] = []

    class _Recorder(TranscriptSink):
        def deliver(self, announcement: Announcement) -> None:
            seen.append(announcement.severity)

    service = AnnouncementService([_Recorder(lambda _t: None)])
    service.announce(error("Disk full"))

    assert seen == [Severity.ERROR]
