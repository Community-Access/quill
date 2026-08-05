"""Unit tests for ``quill.core.media.controller.MediaController`` with a fake engine."""

from __future__ import annotations

import pytest

from quill.core.media import (
    CHAPTER_CHANGED,
    ENDED,
    LOADED,
    STATE_CHANGED,
    EngineUnavailableError,
    InvalidTimecodeError,
    MediaChapter,
    MediaController,
    MediaItem,
    NoMediaLoadedError,
    PlayerState,
    clamp_position,
)


@pytest.mark.parametrize(
    ("ms", "duration", "expected"),
    [
        (-5, 10_000, 0),
        (5_000, 10_000, 5_000),
        (999_999, 10_000, 10_000),
        (5_000, 0, 5_000),  # unknown duration -> no upper clamp
    ],
)
def test_clamp_position(ms: int, duration: int, expected: int) -> None:
    assert clamp_position(ms, duration) == expected


class FakeEngine:
    def __init__(self, *, length_ms: int = 180_000, load_ok: bool = True) -> None:
        self._pos = 0
        self._len = length_ms
        self._playing = False
        self._load_ok = load_ok
        self.loaded: str | None = None
        self.rate = 1.0
        self.vol = 100
        self.seeks: list[int] = []

    def load(self, path: str) -> bool:
        self.loaded = path
        return self._load_ok

    def play(self) -> None:
        self._playing = True

    def pause(self) -> None:
        self._playing = False

    def stop(self) -> None:
        self._playing = False
        self._pos = 0

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        self._pos = ms
        self.seeks.append(ms)

    def position_ms(self) -> int:
        return self._pos

    def length_ms(self) -> int:
        return self._len

    def is_playing(self) -> bool:
        return self._playing

    def set_volume(self, percent: int) -> None:
        self.vol = percent

    def set_rate(self, rate: float) -> None:
        self.rate = rate


def _item() -> MediaItem:
    return MediaItem(
        path="book.m4b",
        title="A Book",
        duration_ms=180_000,
        chapters=(
            MediaChapter(0, "One", 0),
            MediaChapter(1, "Two", 60_000),
            MediaChapter(2, "Three", 120_000),
        ),
    )


def _loaded() -> tuple[MediaController, FakeEngine]:
    engine = FakeEngine()
    controller = MediaController(engine)
    controller.load(_item())
    return controller, engine


# -- loading -----------------------------------------------------------------


def test_load_sets_paused_and_applies_prefs() -> None:
    engine = FakeEngine()
    controller = MediaController(engine)
    controller.set_volume(40)
    controller.set_speed(1.5)
    controller.load(_item())
    assert controller.state() is PlayerState.PAUSED
    assert engine.loaded == "book.m4b"
    assert engine.vol == 40
    assert engine.rate == 1.5


def test_load_failure_raises() -> None:
    controller = MediaController(FakeEngine(load_ok=False))
    with pytest.raises(EngineUnavailableError):
        controller.load(_item())


def test_load_resume_seeks() -> None:
    engine = FakeEngine()
    controller = MediaController(engine)
    controller.load(_item(), resume_ms=90_000)
    assert engine.position_ms() == 90_000


def test_load_autoplay() -> None:
    controller = MediaController(FakeEngine())
    controller.load(_item(), autoplay=True)
    assert controller.state() is PlayerState.PLAYING


def test_load_emits_events() -> None:
    engine = FakeEngine()
    controller = MediaController(engine)
    events = []
    controller.subscribe(events.append)
    controller.load(_item())
    kinds = [e.kind for e in events]
    assert kinds == [LOADED, STATE_CHANGED, CHAPTER_CHANGED]


# -- transport ---------------------------------------------------------------


def test_transport_without_media_raises() -> None:
    controller = MediaController(FakeEngine())
    with pytest.raises(NoMediaLoadedError):
        controller.play()


@pytest.mark.smoke
def test_play_pause_toggle() -> None:
    controller, engine = _loaded()
    controller.play()
    assert controller.state() is PlayerState.PLAYING and engine.is_playing()
    controller.toggle()
    assert controller.state() is PlayerState.PAUSED and not engine.is_playing()
    controller.toggle()
    assert controller.state() is PlayerState.PLAYING


def test_mark_ended() -> None:
    controller, _ = _loaded()
    events = []
    controller.subscribe(events.append)
    controller.mark_ended()
    assert controller.state() is PlayerState.ENDED
    assert ENDED in [e.kind for e in events]


# -- seeking -----------------------------------------------------------------


def test_seek_clamps_low_and_high() -> None:
    controller, engine = _loaded()
    controller.seek_to(-5_000)
    assert engine.position_ms() == 0
    controller.seek_to(999_999_999)
    assert engine.position_ms() == 180_000


def test_skip() -> None:
    controller, engine = _loaded()
    controller.seek_to(50_000)
    controller.skip(30_000)
    assert engine.position_ms() == 80_000
    controller.skip(-100_000)
    assert engine.position_ms() == 0


@pytest.mark.smoke
def test_go_to_timecode() -> None:
    controller, engine = _loaded()
    landed = controller.go_to_timecode("1:00")
    assert landed == 60_000
    assert engine.position_ms() == 60_000


def test_go_to_timecode_clamped() -> None:
    controller, _ = _loaded()
    assert controller.go_to_timecode("99:00:00") == 180_000  # beyond end -> clamped


def test_go_to_timecode_invalid() -> None:
    controller, _ = _loaded()
    with pytest.raises(InvalidTimecodeError):
        controller.go_to_timecode("nonsense")


def test_go_to_percent() -> None:
    controller, engine = _loaded()
    assert controller.go_to_percent(50) == 90_000
    assert engine.position_ms() == 90_000


# -- chapters ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("pos", "index"),
    [(0, 0), (59_999, 0), (60_000, 1), (130_000, 2)],
)
def test_current_chapter_index(pos: int, index: int) -> None:
    controller, engine = _loaded()
    controller.seek_to(pos)
    assert controller.current_chapter_index() == index


def test_next_chapter() -> None:
    controller, engine = _loaded()
    controller.seek_to(30_000)
    controller.next_chapter()
    assert engine.position_ms() == 60_000


def test_next_chapter_at_last_is_noop() -> None:
    controller, engine = _loaded()
    controller.seek_to(150_000)
    controller.next_chapter()
    assert engine.position_ms() == 150_000


def test_prev_chapter_restarts_current_when_past_threshold() -> None:
    controller, engine = _loaded()
    controller.seek_to(65_000)  # 5s into chapter 2 (> 3s threshold)
    controller.prev_chapter()
    assert engine.position_ms() == 60_000


def test_prev_chapter_goes_back_when_near_start() -> None:
    controller, engine = _loaded()
    controller.seek_to(61_000)  # 1s into chapter 2 (< 3s threshold)
    controller.prev_chapter()
    assert engine.position_ms() == 0


def test_go_to_chapter_clamps() -> None:
    controller, engine = _loaded()
    controller.go_to_chapter(99)
    assert engine.position_ms() == 120_000


def test_chapter_changed_emitted_on_cross() -> None:
    controller, _ = _loaded()
    events = []
    controller.subscribe(events.append)
    controller.seek_to(70_000)  # into chapter 2
    chapter_events = [e for e in events if e.kind == CHAPTER_CHANGED]
    assert chapter_events and chapter_events[-1].value == 1


# -- rate & volume -----------------------------------------------------------


def test_speed_clamped() -> None:
    controller, _ = _loaded()
    assert controller.set_speed(10.0) == 4.0
    assert controller.set_speed(0.1) == 0.5


def test_volume_clamped() -> None:
    controller, _ = _loaded()
    assert controller.set_volume(500) == 100
    assert controller.set_volume(-5) == 0


def test_unsubscribe() -> None:
    controller, _ = _loaded()
    events = []
    unsub = controller.subscribe(events.append)
    unsub()
    controller.play()
    assert events == []
