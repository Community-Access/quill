"""Tests for what Quill Radio *says* when you scrub, speed up, or change chapter.

The wording is the feature here. A transport command that silently does nothing
on a live stream is indistinguishable from a broken one, so every command has to
explain itself -- and durations have to be spoken as words, because a
colon-separated time read aloud is ambiguous unless you already know it is a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from quill.ui.radio import bounded_playback_ui as ui


@dataclass
class _Chapter:
    title: str
    start_ms: int


@dataclass
class _Controller:
    seekable: bool = True
    position: int = 0
    duration: int = 1_120_000
    rate: float = 1.0
    chapter_list: tuple[_Chapter, ...] = ()
    current: int = 0
    jumped: list[int] = field(default_factory=list)
    station: object = "a station"

    class _Engine:
        def __init__(self, outer: _Controller) -> None:
            self._outer = outer

        def position_ms(self) -> int:
            return self._outer.position

    def __post_init__(self) -> None:
        self._engine = _Controller._Engine(self)

    @property
    def state(self):  # noqa: ANN201 - test double
        return type("S", (), {"station": self.station})()

    def is_seekable(self) -> bool:
        return self.seekable

    def duration_ms(self) -> int:
        return self.duration if self.seekable else 0

    def chapters(self) -> list[_Chapter]:
        return list(self.chapter_list) if self.seekable else []

    def current_chapter_index(self) -> int:
        return self.current if self.chapter_list else -1

    def skip_by(self, ms: int) -> bool:
        self.position = max(0, min(self.position + ms, self.duration))
        return True

    def playback_rate(self) -> float:
        return self.rate

    def set_playback_rate(self, rate: float) -> float:
        self.rate = max(0.25, min(4.0, rate))
        return self.rate

    def go_to_adjacent_chapter(self, delta: int) -> int:
        if not self.chapter_list:
            return -1
        self.current = max(0, min(self.current + delta, len(self.chapter_list) - 1))
        self.jumped.append(self.current)
        return self.current


class _Host:
    def __init__(self, controller: _Controller) -> None:
        self._radio_controller = controller
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def _host(**kwargs) -> tuple[_Host, _Controller]:
    controller = _Controller(**kwargs)
    return _Host(controller), controller


# -- spoken durations --------------------------------------------------------


def test_durations_are_spoken_as_words_not_punctuation() -> None:
    assert ui.spoken_duration(331_000) == "5 minutes 31 seconds"
    assert ui.spoken_duration(3_600_000) == "1 hour"
    assert ui.spoken_duration(3_661_000) == "1 hour 1 minute 1 second"
    assert ui.spoken_duration(0) == "0 seconds"
    assert ui.spoken_duration(-5) == "0 seconds"


def test_a_chapter_row_reads_as_a_whole_sentence() -> None:
    row = ui.describe_chapter(1, _Chapter("The problem", 60_000))
    assert row == "2. The problem, starts at 1 minute"


def test_the_playing_chapter_says_so_in_its_own_label() -> None:
    """Otherwise the list gives no clue where playback actually is."""
    row = ui.describe_chapter(0, _Chapter("Intro", 0), current=True)
    assert row.endswith("playing now")


def test_a_chapter_with_no_title_still_reads() -> None:
    assert "Untitled chapter" in ui.describe_chapter(0, _Chapter("  ", 0))


# -- refusing, out loud ------------------------------------------------------


def test_a_live_stream_is_told_why_it_cannot_seek() -> None:
    """Silence here is indistinguishable from a broken key."""
    host, _ = _host(seekable=False)
    ui.skip_forward(host)
    assert host.said == [ui.LIVE_REFUSAL]


def test_nothing_playing_says_nothing_is_playing() -> None:
    host, _ = _host(seekable=False, station=None)
    ui.next_chapter(host)
    assert host.said == ["Nothing is playing."]


def test_a_video_without_chapters_says_so() -> None:
    host, _ = _host(chapter_list=())
    ui.next_chapter(host)
    assert host.said == [ui.NO_CHAPTERS]


# -- seeking -----------------------------------------------------------------


def test_skipping_forward_reports_the_new_position() -> None:
    host, controller = _host(position=100_000)
    ui.skip_forward(host)
    assert controller.position == 130_000
    assert host.said == ["2 minutes 10 seconds of 18 minutes 40 seconds"]


def test_the_position_names_the_chapter_you_are_in() -> None:
    host, _ = _host(
        position=70_000,
        chapter_list=(_Chapter("Intro", 0), _Chapter("The problem", 60_000)),
        current=1,
    )
    ui.announce_position(host)
    assert host.said[0].endswith("in The problem")


# -- speed -------------------------------------------------------------------


def test_speed_steps_land_on_round_numbers() -> None:
    host, controller = _host()
    ui.speed_up(host)
    assert controller.rate == pytest.approx(1.25)
    assert host.said == ["1.25 times speed."]
    ui.slow_down(host)
    assert controller.rate == pytest.approx(1.0)


def test_speed_stops_at_the_ends_rather_than_pretending() -> None:
    host, _ = _host()
    host._radio_controller.rate = 4.0
    ui.speed_up(host)
    assert host.said == ["Already at 4 times speed."]


def test_speed_on_live_radio_is_remembered_for_videos() -> None:
    """The key did something -- say what, instead of looking broken."""
    host, controller = _host(seekable=False)
    ui.speed_up(host)
    assert controller.rate == pytest.approx(1.25)
    assert "for videos" in host.said[0]


# -- chapters ----------------------------------------------------------------


def test_moving_chapter_announces_where_you_landed() -> None:
    host, controller = _host(
        chapter_list=(_Chapter("Intro", 0), _Chapter("The problem", 60_000)),
        current=0,
    )
    ui.next_chapter(host)
    assert controller.jumped == [1]
    assert host.said == ["The problem, chapter 2 of 2."]


def test_previous_chapter_announces_too() -> None:
    host, _ = _host(
        chapter_list=(_Chapter("Intro", 0), _Chapter("The problem", 60_000)),
        current=1,
    )
    ui.previous_chapter(host)
    assert host.said == ["Intro, chapter 1 of 2."]
