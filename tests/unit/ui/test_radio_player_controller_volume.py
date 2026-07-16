"""RadioPlayerController's volume across a station switch: a memorized
per-station volume (from RadioFavoritesStore) should apply when one exists;
otherwise whatever volume the user already had set must survive starting a
new stream -- it must never be silently reset to a hardcoded default."""

from __future__ import annotations

import pytest
import wx

from quill.core.radio.models import RadioStation
from quill.ui.radio.player_controller import RadioPlayerController


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self) -> None:
        self.volume_calls: list[int] = []
        self.loaded = False

    def load(self, _source: str) -> bool:
        self.loaded = True
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_volume(self, percent: int) -> None:
        self.volume_calls.append(percent)


def _make_controller(*, resolve_volume=None) -> tuple[RadioPlayerController, _FakeEngine]:
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, resolve_volume=resolve_volume)
    fake = _FakeEngine()
    controller._engine = fake
    return controller, fake


def _station(name: str = "Station A") -> RadioStation:
    return RadioStation(name=name, stream_url=f"http://example.test/{name}")


def test_manual_volume_survives_starting_a_stream_with_no_memorized_volume() -> None:
    controller, fake = _make_controller(resolve_volume=lambda _station: -1)
    controller.set_volume(40)
    controller.play_station(_station())
    controller._on_loaded(0)
    assert controller.state.volume_percent == 40
    assert fake.volume_calls[-1] == 40


def test_memorized_volume_applies_when_starting_a_stream() -> None:
    controller, fake = _make_controller(resolve_volume=lambda _station: 65)
    controller.set_volume(40)
    controller.play_station(_station())
    controller._on_loaded(0)
    assert controller.state.volume_percent == 65
    assert fake.volume_calls[-1] == 65


def test_pause_and_resume_does_not_change_the_volume() -> None:
    controller, fake = _make_controller()
    controller.play_station(_station())
    controller._on_loaded(0)
    controller.set_volume(40)
    controller.toggle_play_pause()  # pause
    assert controller.state.volume_percent == 40
    controller.toggle_play_pause()  # resume
    assert controller.state.volume_percent == 40


def test_default_volume_with_no_resolver_and_no_prior_setting() -> None:
    controller, fake = _make_controller()
    controller.play_station(_station())
    controller._on_loaded(0)
    assert controller.state.volume_percent == 100
    assert fake.volume_calls[-1] == 100
