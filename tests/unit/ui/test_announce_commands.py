"""Repeat Last Announcement, the self-test, and the visual channel (#1303-#1305)."""

from __future__ import annotations

from quill.core.announce import Announcement, AnnouncementService, Channel, Severity
from quill.core.announce.adapters import BrailleSink, SpeechSink, VisualSink
from quill.ui.announce_commands import (
    NOTHING_TO_REPEAT,
    SELF_TEST_PHRASE,
    AnnounceCommandsMixin,
    format_self_test_report,
    summarise_self_test,
)


class _Host(AnnounceCommandsMixin):
    def __init__(self, service: AnnouncementService | None) -> None:
        self._service = service
        self._status_message = ""
        self.announced: list[tuple[str, bool]] = []
        self.status: list[str] = []
        self.reports: list[tuple[str, str]] = []

    # -- the surface the mixin uses ---------------------------------------
    def _announce_service(self):
        return self._service

    def _announce(self, message: str, *, force: bool = False) -> None:
        self.announced.append((message, force))

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def show_text_report(self, title: str, text: str) -> None:
        self.reports.append((title, text))


def _service(*, braille_fails: bool = False, supports_braille: bool = True):
    spoken: list[str] = []
    brailled: list[str] = []
    shown: list[str] = []
    service = AnnouncementService([
        SpeechSink(lambda text, _f: spoken.append(text) or None, backend_name=lambda: "JAWS"),
        BrailleSink(
            (lambda text: "display disconnected")
            if braille_fails
            else (lambda text: brailled.append(text) or ""),
            supports_braille=lambda: supports_braille,
            backend_name=lambda: "JAWS",
        ),
        VisualSink(shown.append),
    ])
    return service, spoken, brailled, shown


# -- Repeat Last Announcement (#1304) -----------------------------------------


def test_repeat_says_the_last_announcement_again() -> None:
    service, spoken, _brailled, _shown = _service()
    host = _Host(service)
    service.announce(Announcement(text="Now playing: A Song"))

    host.repeat_last_announcement()

    assert spoken == ["Now playing: A Song", "Now playing: A Song"]


def test_repeat_interrupts_because_the_user_asked_for_it() -> None:
    service, _spoken, _brailled, _shown = _service()
    host = _Host(service)
    service.announce(Announcement(text="Saved"))
    seen: list[Severity] = []

    class _Recorder:
        channel = Channel.TRANSCRIPT

        def deliver(self, announcement: Announcement) -> None:
            seen.append(announcement.severity)

        def probe(self):
            from quill.core.announce import SinkStatus

            return SinkStatus(channel=self.channel, available=True)

    service.add_sink(_Recorder())
    host.repeat_last_announcement()

    assert seen == [Severity.WARNING]


def test_repeat_says_so_when_there_is_nothing_to_repeat() -> None:
    # Silence is the symptom this command exists to diagnose, so it must not be
    # the answer this command gives.
    service, _spoken, _brailled, _shown = _service()
    host = _Host(service)

    host.repeat_last_announcement()

    assert host.announced == [(NOTHING_TO_REPEAT, False)]


# -- the visual channel (#1303) ------------------------------------------------


def test_the_message_slot_survives_a_standing_status_refresh() -> None:
    service, _spoken, _brailled, shown = _service()
    host = _Host(service)

    service.announce(Announcement(text="Recording started"))
    shown.append("Words: 412")  # a standing-status refresh writing over the bar

    assert host.last_announcement() == "Recording started"


def test_a_visual_only_announcement_does_not_speak() -> None:
    service, spoken, _brailled, shown = _service()
    host = _Host(service)

    host.announce_visually("Converting 3 of 40")

    assert spoken == []
    assert shown == ["Converting 3 of 40"]


# -- the self-test (#1305) ------------------------------------------------------


def test_the_self_test_announces_and_reports_what_delivered() -> None:
    service, spoken, brailled, _shown = _service()
    host = _Host(service)

    host.run_announcement_self_test()

    assert spoken == [SELF_TEST_PHRASE]
    assert brailled == [SELF_TEST_PHRASE]
    title, text = host.reports[0]
    assert title == "Announcement Self-Test"
    assert "Speech: delivered, through JAWS." in text
    assert "Braille: delivered, through JAWS." in text


def test_the_report_says_why_a_channel_did_not_deliver() -> None:
    # "no display connected" is a different answer from "braille is broken", and
    # the difference is the whole point of the command.
    service, _spoken, _brailled, _shown = _service(supports_braille=False)
    host = _Host(service)

    host.run_announcement_self_test()

    _title, text = host.reports[0]
    assert "Braille: not delivered. no braille display connected." in text


def test_the_report_names_a_failure() -> None:
    service, _spoken, _brailled, _shown = _service(braille_fails=True)
    host = _Host(service)

    host.run_announcement_self_test()

    _title, text = host.reports[0]
    assert "Braille: failed." in text
    assert "display disconnected" in text


def test_a_channel_with_no_sink_is_reported_as_such() -> None:
    service, _spoken, _brailled, _shown = _service()
    host = _Host(service)

    host.run_announcement_self_test()

    _title, text = host.reports[0]
    assert "Sound: not delivered. no sink installed for this channel." in text


def test_the_spoken_summary_counts_the_channels() -> None:
    service, _spoken, _brailled, _shown = _service()
    report = service.announce(Announcement(text=SELF_TEST_PHRASE))

    summary = summarise_self_test(report)

    assert summary.startswith("The self-test reached 3 channels")


def test_the_report_is_plain_text_a_screen_reader_can_read() -> None:
    service, _spoken, _brailled, _shown = _service()
    report = service.announce(Announcement(text=SELF_TEST_PHRASE))

    text = format_self_test_report(service, report)

    assert text.startswith("Announcement self-test")
    assert "\t" not in text  # nothing that depends on visual alignment
