"""The speed commands, and the import that used to make them all crash.

``quill/ui/podcasts/speed.py`` imported ``SPEED_STEP`` from
``models_settings``, which defined ``SPEED_MIN`` and ``SPEED_MAX`` and not the
step -- the step lived in ``main_frame_podcast_session.py``. So every one of
Speed Up (Ctrl+Shift+Up), Speed Down (Ctrl+Shift+Down), Reset Speed and their
three palette rows raised ImportError on use: a crash on a keypress, not a
silent no-op, and nothing in the suite imported the module to notice.

The first test here is therefore the important one, and it is the boring one:
import the module. Everything below it tests behaviour that could not run at
all before.
"""

from __future__ import annotations

from typing import Any


def test_the_module_imports() -> None:
    """The regression. Every command in the module was unreachable without it."""
    import quill.ui.podcasts.speed as speed

    assert speed.speed_up and speed.speed_down and speed.speed_reset


def test_the_step_lives_with_the_range_it_must_stay_inside() -> None:
    from quill.core.podcasts import models_settings

    assert models_settings.SPEED_STEP == 0.05
    assert models_settings.SPEED_MIN < models_settings.SPEED_STEP + 1 < models_settings.SPEED_MAX


def test_the_stray_definition_is_gone() -> None:
    """Two definitions of one constant is how the first one went missing."""
    import quill.ui.main_frame_podcast_session as session

    assert not hasattr(session, "SPEED_STEP")


class _Show:
    def __init__(self, title: str) -> None:
        self.title = title


class _Settings:
    def __init__(self, speed: float) -> None:
        self.speed = speed


class _Library:
    def __init__(self, speed: float, show: _Show | None) -> None:
        self.settings = _Settings(speed)
        self._show = show
        self.overrides: list[tuple[str, float]] = []

    def find_show(self, show_id: str | None) -> _Show | None:
        return self._show if show_id else None

    def effective_settings(self, _show: _Show) -> _Settings:
        return self.settings

    def apply_show_override(self, show: _Show, *, speed: float) -> None:
        self.overrides.append((show.title, speed))
        self.settings.speed = speed


class _State:
    def __init__(self, show_id: str | None) -> None:
        self.show_id = show_id


class _Controller:
    def __init__(self, show_id: str | None) -> None:
        self.state = _State(show_id)
        self.rates: list[float] = []

    def set_rate(self, rate: float) -> None:
        self.rates.append(rate)


class _Host:
    """The five things the speed commands ask of their host, and nothing else."""

    def __init__(self, *, speed: float = 1.0, playing: str | None = None) -> None:
        show = _Show(playing) if playing else None
        self._podcast_library = _Library(speed, show)
        self._podcast_controller = _Controller("id" if playing else None)
        self.said: list[str] = []
        self.saves = 0

    def _save_podcast_library(self) -> None:
        self.saves += 1

    def _announce(self, text: str) -> None:
        self.said.append(text)

    @property
    def speed(self) -> float:
        return self._podcast_library.settings.speed


def _speed() -> Any:
    import quill.ui.podcasts.speed as module

    return module


def test_speed_up_steps_by_the_step_and_says_the_scope() -> None:
    host = _Host(speed=1.0)
    _speed().speed_up(host)
    assert host.speed == 1.05
    assert host.said == ["Speed 1.05x for every podcast"]
    assert host.saves == 1


def test_speed_down_steps_the_other_way() -> None:
    host = _Host(speed=1.0)
    _speed().speed_down(host)
    assert host.speed == 0.95
    assert host.said == ["Speed 0.95x for every podcast"]


def test_reset_returns_to_one() -> None:
    host = _Host(speed=2.5)
    _speed().speed_reset(host)
    assert host.speed == 1.0
    assert host.said == ["Speed 1x for every podcast"]


def test_a_playing_show_gets_its_own_override_and_is_named() -> None:
    """The scope is the whole point: "faster" must say what it made faster."""
    host = _Host(speed=1.0, playing="The Daily")
    _speed().speed_up(host)
    assert host._podcast_library.overrides == [("The Daily", 1.05)]
    assert host.said == ["Speed 1.05x for The Daily"]
    assert host._podcast_controller.rates == [1.05]


def test_the_ends_of_the_range_are_announced_rather_than_silently_clamped() -> None:
    """A key that stops doing anything is indistinguishable from a broken key."""
    fastest = _Host(speed=5.0)
    _speed().speed_up(fastest)
    assert fastest.speed == 5.0
    assert fastest.said == ["Already at the fastest speed, 5x"]

    slowest = _Host(speed=0.5)
    _speed().speed_down(slowest)
    assert slowest.speed == 0.5
    assert slowest.said == ["Already at the slowest speed, 0.5x"]


def test_repeated_presses_never_drift_off_the_step() -> None:
    """Ten presses of a 0.05 step must land on 1.5, not 1.5000000000000002.

    A drifted speed reads back correctly and then fails to match the same
    number in a settings list or a preset, which is the kind of bug that gets
    reported as "the speed list forgets my choice".
    """
    host = _Host(speed=1.0)
    for _ in range(10):
        _speed().speed_up(host)
    assert host.speed == 1.5
    for _ in range(10):
        _speed().speed_down(host)
    assert host.speed == 1.0


def test_clamp_snaps_a_value_from_anywhere_onto_the_step() -> None:
    from quill.core.podcasts.models_settings import clamp_speed

    assert clamp_speed(1.37) == 1.35
    assert clamp_speed(1.38) == 1.40
    assert clamp_speed(99) == 5.0
    assert clamp_speed(-1) == 0.5
