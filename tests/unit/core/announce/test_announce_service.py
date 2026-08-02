"""The announcement service fans out and isolates failures (#1290).

The service is the single place an announcement enters, so the properties that
matter are structural: every allowed channel gets it, a broken channel takes
only itself down, and the report says what actually happened.
"""

from __future__ import annotations

import pytest

from quill.core.announce import (
    Announcement,
    AnnouncementPolicy,
    AnnouncementService,
    Channel,
    PolicyModes,
    Severity,
    SinkStatus,
    error,
    routine,
)


class _FakeSink:
    def __init__(self, channel: Channel, *, raises: str = "", available: bool = True) -> None:
        self.channel = channel
        self.received: list[Announcement] = []
        self._raises = raises
        self._available = available

    def deliver(self, announcement: Announcement) -> None:
        if self._raises:
            raise RuntimeError(self._raises)
        self.received.append(announcement)

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel,
            available=self._available,
            backend="fake",
            detail="" if self._available else "not connected",
        )


def _service(*sinks, modes: PolicyModes | None = None) -> AnnouncementService:
    return AnnouncementService(sinks, policy=AnnouncementPolicy(modes or PolicyModes()))


def test_an_announcement_reaches_every_allowed_channel() -> None:
    speech = _FakeSink(Channel.SPEECH)
    braille = _FakeSink(Channel.BRAILLE)
    visual = _FakeSink(Channel.VISUAL)
    service = _service(speech, braille, visual)

    report = service.announce(routine("Saved note.md"))

    assert [s.received[0].text for s in (speech, braille, visual)] == ["Saved note.md"] * 3
    assert report.spoke and report.brailled


def test_a_failing_sink_never_takes_the_others_with_it() -> None:
    # The whole reason channels are routed separately: an unplugged display must
    # not cost the user their speech.
    braille = _FakeSink(Channel.BRAILLE, raises="display disconnected")
    speech = _FakeSink(Channel.SPEECH)
    service = _service(braille, speech)

    report = service.announce(routine("Recording started"))

    assert speech.received[0].text == "Recording started"
    assert Channel.BRAILLE in report.failed
    assert "display disconnected" in report.failed[Channel.BRAILLE]
    assert report.spoke


def test_the_first_failure_per_channel_is_remembered_not_repeated() -> None:
    braille = _FakeSink(Channel.BRAILLE, raises="boom")
    service = _service(braille)

    for _ in range(5):
        service.announce(routine("Saved"))

    statuses = {status.channel: status for status in service.probe()}
    assert "boom" in statuses[Channel.BRAILLE].last_error


def test_a_channel_the_caller_excluded_is_skipped() -> None:
    speech = _FakeSink(Channel.SPEECH)
    visual = _FakeSink(Channel.VISUAL)
    service = _service(speech, visual)

    service.announce(Announcement(text="Status only", channels=frozenset({Channel.VISUAL})))

    assert visual.received and not speech.received


def test_sinks_receive_announcements_in_installation_order() -> None:
    order: list[str] = []

    class _Recorder(_FakeSink):
        def __init__(self, channel: Channel, label: str) -> None:
            super().__init__(channel)
            self._label = label

        def deliver(self, announcement: Announcement) -> None:
            order.append(self._label)
            super().deliver(announcement)

    service = _service(_Recorder(Channel.SOUND, "sound"), _Recorder(Channel.SPEECH, "speech"))
    service.announce(Announcement(text="Saved", sound_event="document_saved"))

    assert order == ["sound", "speech"]


def test_probe_reports_channels_with_no_sink_at_all() -> None:
    service = _service(_FakeSink(Channel.SPEECH))

    statuses = {status.channel: status for status in service.probe()}

    assert statuses[Channel.SPEECH].available is True
    assert statuses[Channel.BRAILLE].available is False
    assert "no sink installed" in statuses[Channel.BRAILLE].detail


def test_probe_survives_a_sink_that_raises() -> None:
    class _BadProbe(_FakeSink):
        def probe(self) -> SinkStatus:
            raise RuntimeError("probe exploded")

    service = _service(_BadProbe(Channel.SOUND))

    statuses = {status.channel: status for status in service.probe()}

    assert statuses[Channel.SOUND].available is False
    assert "probe exploded" in statuses[Channel.SOUND].detail


def test_diagnostics_are_support_bundle_shaped() -> None:
    service = _service(_FakeSink(Channel.SPEECH))

    diagnostics = service.diagnostics()

    assert diagnostics["announce_channels"] == ["speech"]
    assert isinstance(diagnostics["announce_sinks"], list)
    assert all(isinstance(entry, dict) for entry in diagnostics["announce_sinks"])


def test_removing_a_channel_stops_its_deliveries() -> None:
    speech = _FakeSink(Channel.SPEECH)
    service = _service(speech)

    service.remove_channel(Channel.SPEECH)
    service.announce(routine("Saved"))

    assert speech.received == []


@pytest.mark.parametrize(
    ("severity", "should_notify"),
    [
        (Severity.ROUTINE, False),
        (Severity.INFO, False),
        (Severity.WARNING, True),
        (Severity.ERROR, True),
    ],
)
def test_only_problems_reach_the_notification_channel(severity, should_notify) -> None:
    notifications = _FakeSink(Channel.NOTIFICATION)
    service = _service(notifications)

    service.announce(Announcement(text="Something", severity=severity))

    assert bool(notifications.received) is should_notify


def test_an_error_is_delivered_even_in_quiet_mode() -> None:
    # A user must not be able to configure away the message that says something
    # went wrong.
    speech = _FakeSink(Channel.SPEECH)
    service = _service(speech, modes=PolicyModes(quiet=True))

    service.announce(error("Could not save note.md"))

    assert speech.received[0].text == "Could not save note.md"
