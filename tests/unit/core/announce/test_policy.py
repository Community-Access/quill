"""The severity matrix and the mute rules (#1291).

The policy is pure, so these assert the decisions directly: which channels carry
which severity, what Quiet Mode does and does not silence, and that an error can
never be configured away.
"""

from __future__ import annotations

import pytest

from quill.core.announce import (
    Announcement,
    AnnouncementPolicy,
    Channel,
    PolicyModes,
    Severity,
    compact_braille,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _policy(modes: PolicyModes | None = None, clock: _Clock | None = None) -> AnnouncementPolicy:
    return AnnouncementPolicy(modes or PolicyModes(), clock=clock or _Clock())


# -- the severity matrix -------------------------------------------------------


@pytest.mark.parametrize("severity", list(Severity))
def test_every_severity_speaks_brailles_and_shows_by_default(severity) -> None:
    decision = _policy().decide(Announcement(text="Saved", severity=severity))

    assert decision.allows(Channel.SPEECH)
    assert decision.allows(Channel.BRAILLE)
    assert decision.allows(Channel.VISUAL)


@pytest.mark.parametrize(
    ("severity", "interrupts"),
    [
        (Severity.ROUTINE, False),
        (Severity.INFO, False),
        (Severity.WARNING, True),
        (Severity.ERROR, True),
    ],
)
def test_warnings_and_errors_interrupt(severity, interrupts) -> None:
    decision = _policy().decide(Announcement(text="Careful", severity=severity))
    assert decision.interrupt is interrupts


def test_an_error_is_sticky_on_the_display() -> None:
    # Holding the display beats flashing past the one message the reader most
    # needs to catch.
    assert _policy().decide(Announcement(text="Failed", severity=Severity.ERROR)).sticky is True
    assert _policy().decide(Announcement(text="Saved")).sticky is False


def test_sound_only_when_the_announcement_carries_an_event() -> None:
    assert not _policy().decide(Announcement(text="Saved")).allows(Channel.SOUND)
    assert (
        _policy()
        .decide(Announcement(text="Saved", sound_event="document_saved"))
        .allows(Channel.SOUND)
    )


# -- Quiet and Meeting Mode -----------------------------------------------------


def test_quiet_mode_silences_speech_but_keeps_braille() -> None:
    # The behaviour that is impossible today, and exactly what a braille user in
    # a meeting wants: silence in the room, message still under their fingers.
    decision = _policy(PolicyModes(quiet=True)).decide(Announcement(text="Saved"))

    assert not decision.allows(Channel.SPEECH)
    assert decision.allows(Channel.BRAILLE)
    assert decision.reason == "quiet mode"


def test_meeting_mode_behaves_the_same_way() -> None:
    decision = _policy(PolicyModes(meeting=True)).decide(Announcement(text="Saved"))

    assert not decision.allows(Channel.SPEECH)
    assert decision.allows(Channel.BRAILLE)
    assert decision.reason == "meeting mode"


def test_quiet_mode_drops_the_cue_unless_the_setting_asks_for_it() -> None:
    quiet = Announcement(text="Saved", sound_event="document_saved")
    assert not _policy(PolicyModes(quiet=True)).decide(quiet).allows(Channel.SOUND)

    modes = PolicyModes(quiet=True, sound_instead_of_speech_when_quiet=True)
    assert _policy(modes).decide(quiet).allows(Channel.SOUND)


@pytest.mark.parametrize(
    "modes",
    [
        PolicyModes(quiet=True),
        PolicyModes(meeting=True),
        PolicyModes(speech_enabled=False),
        PolicyModes(braille_enabled=False, speech_enabled=False, sound_enabled=False),
    ],
)
def test_an_error_survives_every_mute(modes) -> None:
    decision = _policy(modes).decide(Announcement(text="Disk full", severity=Severity.ERROR))

    assert decision.allows(Channel.SPEECH)
    assert decision.allows(Channel.BRAILLE)
    assert decision.allows(Channel.NOTIFICATION)


def test_turning_a_channel_off_removes_only_that_channel() -> None:
    decision = _policy(PolicyModes(braille_enabled=False)).decide(Announcement(text="Saved"))

    assert decision.allows(Channel.SPEECH)
    assert not decision.allows(Channel.BRAILLE)


# -- de-duplication --------------------------------------------------------------


def test_an_identical_message_does_not_flash_braille_twice() -> None:
    clock = _Clock()
    policy = _policy(clock=clock)
    first = policy.decide(Announcement(text="Now playing: A Song"))
    clock.advance(0.5)
    second = policy.decide(Announcement(text="Now playing: A Song"))

    assert first.allows(Channel.BRAILLE)
    assert not second.allows(Channel.BRAILLE)


def test_the_dedupe_window_expires() -> None:
    clock = _Clock()
    policy = _policy(clock=clock)
    policy.decide(Announcement(text="Now playing: A Song"))
    clock.advance(5.0)

    assert policy.decide(Announcement(text="Now playing: A Song")).allows(Channel.BRAILLE)


def test_a_dedupe_key_collapses_messages_whose_text_differs() -> None:
    clock = _Clock()
    policy = _policy(clock=clock)
    first = Announcement(text="Downloading 1 of 40", dedupe_key="download-progress")
    second = Announcement(text="Downloading 2 of 40", dedupe_key="download-progress")

    assert policy.decide(first).allows(Channel.BRAILLE)
    clock.advance(0.2)
    assert not policy.decide(second).allows(Channel.BRAILLE)


# -- the compact braille style (#425) ---------------------------------------------


def test_compact_braille_puts_position_before_prose() -> None:
    announcement = Announcement(
        text="Page 7 of 87, line 14, column 3, modified",
        context={"page": 7, "pages": 87, "line": 14, "column": 3, "modified": True},
    )
    assert compact_braille(announcement) == "p7/87 l14 c3 mod"


def test_compact_braille_falls_back_to_the_spoken_text_without_position() -> None:
    # A compact render of prose is just the prose; inventing an abbreviation
    # would cost the reader information for no gain.
    assert compact_braille(Announcement(text="Saved note.md")) == "Saved note.md"


def test_the_compact_style_is_opt_in() -> None:
    announcement = Announcement(text="Position", context={"line": 14, "column": 3})

    assert _policy().decide(announcement).braille_text == ""
    compact = _policy(PolicyModes(braille_style="compact")).decide(announcement)
    assert compact.braille_text == "l14 c3"


def test_an_explicit_braille_text_always_wins() -> None:
    announcement = Announcement(text="Long spoken form", braille_text="short")
    assert _policy().decide(announcement).braille_text == "short"
