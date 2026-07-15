"""PodcastPlayerController's volume boost: a live-playback gain, distinct
from download-time loudness normalization, applied only to what reaches
the engine (never to the user-facing volume_percent the Sleep Timer
reads/restores)."""

from __future__ import annotations

import pytest
import wx

from quill.ui.podcasts.player_controller import PodcastPlayerController


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self) -> None:
        self.volume_calls: list[int] = []

    def load(self, _source: str) -> bool:
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        pass

    def seek(self, ms: int, *, resume: bool = False) -> None:
        pass

    def set_rate(self, _rate: float) -> None:
        pass

    def set_volume(self, percent: int) -> None:
        self.volume_calls.append(percent)

    def position_ms(self) -> int:
        return 0

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return True


def _make_controller() -> tuple[PodcastPlayerController, _FakeEngine]:
    frame = wx.Frame(None)
    controller = PodcastPlayerController(frame)
    fake = _FakeEngine()
    controller._engine = fake
    return controller, fake


def test_default_boost_sends_volume_unchanged() -> None:
    controller, fake = _make_controller()
    controller.set_volume(60)
    assert fake.volume_calls[-1] == 60


def test_boost_scales_the_engine_volume() -> None:
    controller, fake = _make_controller()
    controller.set_volume(40)
    controller.set_volume_boost(1.5)
    assert fake.volume_calls[-1] == 60


def test_boost_caps_at_100_even_when_scaled_higher() -> None:
    controller, fake = _make_controller()
    controller.set_volume(80)
    controller.set_volume_boost(2.0)
    assert fake.volume_calls[-1] == 100


def test_volume_percent_stays_unboosted_for_sleep_timer() -> None:
    controller, _fake = _make_controller()
    controller.set_volume(40)
    controller.set_volume_boost(2.0)
    assert controller.volume_percent == 40


def test_set_volume_boost_clamps_to_valid_range() -> None:
    controller, fake = _make_controller()
    controller.set_volume(50)
    controller.set_volume_boost(10.0)  # way above the 3.0 cap
    assert fake.volume_calls[-1] == 100  # 50 * 3.0 clamped to 100
    controller.set_volume_boost(0.1)  # below the 0.5 floor
    assert fake.volume_calls[-1] == 25  # 50 * 0.5


def test_toggle_mute_silences_then_restores_the_level() -> None:
    controller, fake = _make_controller()
    controller.set_volume(70)
    controller.toggle_mute()
    assert controller.muted is True
    assert fake.volume_calls[-1] == 0
    controller.toggle_mute()
    assert controller.muted is False
    assert fake.volume_calls[-1] == 70


def test_set_volume_while_muted_clears_mute() -> None:
    controller, fake = _make_controller()
    controller.set_volume(70)
    controller.toggle_mute()
    controller.set_volume(30)
    assert controller.muted is False
    assert fake.volume_calls[-1] == 30
