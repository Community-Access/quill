"""Tests for seeking, speed, and chapter navigation on a finished video.

A radio station is live: it has no end, so seeking and speed are meaningless
and the engine has always said so by making them no-ops. A finished YouTube
video is the opposite -- it has a timeline, published chapters, and every
reason to be scrubbed.

The awkward part is *when* the difference is known. The engine has to exist
before playback starts, but whether a YouTube link is a finished video or a
live broadcast is only known once yt-dlp answers. So the engine is told what
it is holding immediately after the load, and everything below is about that
declaration being made, honoured, and -- just as importantly -- undone when
the next station is an ordinary broadcast.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from quill.ui.radio.player_controller import RadioPlayerController


@dataclass
class _Chapter:
    title: str
    start_ms: int


@dataclass
class _Stream:
    stream_url: str = "https://example.invalid/audio"
    duration_ms: int = 600_000
    chapters: tuple[_Chapter, ...] = ()


@dataclass
class _FakeEngine:
    """Stands in for MpvRadioEngine's bounded-source surface."""

    bounded: bool = False
    loaded: bool = True
    position: int = 0
    duration: int = 600_000
    rate: float = 1.0
    seeks: list[int] = field(default_factory=list)

    def set_bounded(self, bounded: bool) -> None:
        self.bounded = bool(bounded)

    def is_bounded(self) -> bool:
        return self.bounded and self.loaded

    def length_ms(self) -> int:
        return self.duration if self.bounded else 0

    def position_ms(self) -> int:
        return self.position

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        self.seeks.append(int(ms))
        self.position = int(ms)

    def set_rate(self, rate: float) -> None:
        self.rate = float(rate)


def _controller(engine: _FakeEngine, stream: _Stream | None) -> RadioPlayerController:
    """A controller wired to *engine*, as though *stream* had just resolved."""
    controller = RadioPlayerController.__new__(RadioPlayerController)
    controller._engine = engine
    controller._youtube_stream = stream
    controller._playback_rate = 1.0
    return controller


# -- declaring what was loaded -----------------------------------------------


def test_a_finished_video_is_declared_bounded() -> None:
    engine = _FakeEngine()
    controller = _controller(engine, _Stream(duration_ms=600_000))
    controller._declare_source_shape()
    assert engine.bounded is True
    assert controller.is_seekable() is True


def test_a_live_youtube_stream_is_not_seekable() -> None:
    """A live broadcast reports no duration, and that is the honest answer."""
    engine = _FakeEngine()
    controller = _controller(engine, _Stream(duration_ms=0))
    controller._declare_source_shape()
    assert engine.bounded is False
    assert controller.is_seekable() is False


def test_an_ordinary_station_is_never_bounded() -> None:
    engine = _FakeEngine()
    controller = _controller(engine, None)
    controller._declare_source_shape()
    assert engine.bounded is False
    assert controller.duration_ms() == 0


def test_an_engine_without_the_capability_is_left_alone() -> None:
    """The wx.media engine has no set_bounded; it must not be called."""

    class _Plain:
        def length_ms(self) -> int:
            return 0

    controller = _controller(_Plain(), _Stream())  # type: ignore[arg-type]
    controller._declare_source_shape()  # must not raise
    assert controller.is_seekable() is False


def test_a_chosen_speed_is_reapplied_after_a_bounded_load() -> None:
    """load() resets mpv's speed, so the controller has to put it back."""
    engine = _FakeEngine()
    controller = _controller(engine, _Stream())
    controller._playback_rate = 1.5
    controller._declare_source_shape()
    assert engine.rate == pytest.approx(1.5)


# -- seeking -----------------------------------------------------------------


def test_seeking_is_refused_on_a_live_stream() -> None:
    engine = _FakeEngine(bounded=False)
    controller = _controller(engine, None)
    assert controller.seek_to(5000) is False
    assert controller.skip_by(30_000) is False
    assert engine.seeks == []


def test_seeking_clamps_to_the_timeline() -> None:
    engine = _FakeEngine(bounded=True, duration=600_000)
    controller = _controller(engine, _Stream())
    controller.seek_to(999_999_999)
    controller.seek_to(-5000)
    assert engine.seeks == [600_000, 0]


def test_skipping_moves_relative_to_the_playhead() -> None:
    engine = _FakeEngine(bounded=True, position=100_000)
    controller = _controller(engine, _Stream())
    controller.skip_by(30_000)
    assert engine.seeks == [130_000]
    controller.skip_by(-10_000)
    assert engine.seeks[-1] == 120_000


# -- speed -------------------------------------------------------------------


def test_speed_is_clamped_to_what_mpv_can_do() -> None:
    engine = _FakeEngine(bounded=True)
    controller = _controller(engine, _Stream())
    assert controller.set_playback_rate(99.0) == pytest.approx(4.0)
    assert controller.set_playback_rate(0.01) == pytest.approx(0.25)


def test_speed_is_remembered_even_when_nothing_seekable_is_playing() -> None:
    """Someone who prefers 1.5x keeps it across stations."""
    engine = _FakeEngine(bounded=False)
    controller = _controller(engine, None)
    controller.set_playback_rate(1.5)
    assert controller.playback_rate() == pytest.approx(1.5)
    assert engine.rate == pytest.approx(1.0)  # live radio is untouched


# -- chapters ----------------------------------------------------------------


_CHAPTERS = (
    _Chapter("Introduction", 0),
    _Chapter("The problem", 60_000),
    _Chapter("A solution", 300_000),
)


def _chaptered(position: int = 0) -> tuple[RadioPlayerController, _FakeEngine]:
    engine = _FakeEngine(bounded=True, position=position)
    return _controller(engine, _Stream(chapters=_CHAPTERS)), engine


def test_chapters_are_only_offered_for_something_seekable() -> None:
    engine = _FakeEngine(bounded=False)
    controller = _controller(engine, _Stream(chapters=_CHAPTERS))
    assert controller.chapters() == []
    assert controller.current_chapter_index() == -1


def test_the_current_chapter_follows_the_playhead() -> None:
    controller, engine = _chaptered(position=0)
    assert controller.current_chapter_index() == 0
    engine.position = 59_999
    assert controller.current_chapter_index() == 0
    engine.position = 60_000
    assert controller.current_chapter_index() == 1
    engine.position = 5_000_000
    assert controller.current_chapter_index() == 2


def test_going_to_a_chapter_seeks_to_its_start() -> None:
    controller, engine = _chaptered()
    assert controller.go_to_chapter(2) is True
    assert engine.seeks == [300_000]


def test_a_chapter_index_that_does_not_exist_is_refused() -> None:
    controller, engine = _chaptered()
    assert controller.go_to_chapter(99) is False
    assert controller.go_to_chapter(-1) is False
    assert engine.seeks == []


def test_next_chapter_advances_one() -> None:
    controller, engine = _chaptered(position=0)
    assert controller.go_to_adjacent_chapter(1) == 1
    assert engine.seeks == [60_000]


def test_previous_restarts_the_chapter_when_well_inside_it() -> None:
    """What every other player does, and what pressing it once means."""
    controller, engine = _chaptered(position=120_000)  # 60s into chapter 1
    assert controller.go_to_adjacent_chapter(-1) == 1
    assert engine.seeks == [60_000]


def test_previous_steps_back_when_just_inside_a_chapter() -> None:
    """Pressed again right after a restart, it should actually go back."""
    controller, engine = _chaptered(position=61_000)  # 1s into chapter 1
    assert controller.go_to_adjacent_chapter(-1) == 0
    assert engine.seeks == [0]


def test_chapter_navigation_stops_at_the_ends() -> None:
    controller, engine = _chaptered(position=0)
    assert controller.go_to_adjacent_chapter(-1) == 0
    engine.position = 300_000
    assert controller.go_to_adjacent_chapter(1) == 2


def test_navigation_is_refused_when_there_are_no_chapters() -> None:
    engine = _FakeEngine(bounded=True)
    controller = _controller(engine, _Stream(chapters=()))
    assert controller.go_to_adjacent_chapter(1) == -1
    assert engine.seeks == []
