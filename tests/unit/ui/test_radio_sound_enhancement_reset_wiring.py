"""open_sound_enhancements' on_reset wiring: passes the Sound Enhancements
dialog a reset callback only when there's an override to clear, and that
callback clears the override, saves, live-updates playback if the reset
station is the one currently playing, and announces.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import quill.ui.main_frame_radio as main_frame_radio_module
import quill.ui.sound_enhance_dialog as sound_enhance_dialog_module
from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.radio.player_controller import RadioPlayerState


class _FakeSoundEnhanceDialog:
    instances: list[_FakeSoundEnhanceDialog] = []

    def __init__(self, parent: object, **kwargs: Any) -> None:
        self.kwargs = kwargs
        _FakeSoundEnhanceDialog.instances.append(self)

    def show(self) -> None:
        return None  # Cancel-equivalent -- on_reset (if any) already ran.


def _frame(monkeypatch: pytest.MonkeyPatch, *, playing: RadioStation | None) -> Any:
    _FakeSoundEnhanceDialog.instances = []
    monkeypatch.setattr(sound_enhance_dialog_module, "SoundEnhanceDialog", _FakeSoundEnhanceDialog)
    monkeypatch.setattr(main_frame_radio_module, "app_data_dir", lambda: "FAKE_DIR")

    saved: list[str] = []
    frame = RadioMixin.__new__(RadioMixin)
    frame.frame = object()
    frame._announce = lambda _msg: None
    frame._radio_history = SimpleNamespace(
        eq_bass_db=1.0, eq_mid_db=2.0, eq_treble_db=3.0, compressor_enabled=True
    )
    frame._radio_favorites = RadioFavoritesStore()
    frame._radio_controller = SimpleNamespace(
        state=SimpleNamespace(station=playing, state=RadioPlayerState.PLAYING),
        set_enhancement=lambda **kw: calls.append(("set_enhancement", kw)),
    )
    frame._save_radio_favorites = lambda: saved.append(True)
    calls: list[tuple[str, dict]] = []
    frame._calls = calls  # type: ignore[attr-defined]
    frame._saved = saved  # type: ignore[attr-defined]
    return frame


def _station(key_suffix: str = "1") -> RadioStation:
    return RadioStation(
        name=f"Station {key_suffix}", stream_url=f"https://example.com/{key_suffix}"
    )


def test_no_on_reset_when_favorite_has_no_override(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(monkeypatch, playing=None)
    station = _station()
    favorite = FavoriteStation(station=station, has_sound_enhancement_override=False)
    frame._radio_favorites.favorites.append(favorite)
    frame._radio_controller.state.station = station

    RadioMixin.open_sound_enhancements(frame)

    assert _FakeSoundEnhanceDialog.instances[0].kwargs["on_reset"] is None


def test_no_on_reset_when_editing_shared_default(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(monkeypatch, playing=None)

    RadioMixin.open_sound_enhancements(frame)

    assert _FakeSoundEnhanceDialog.instances[0].kwargs["on_reset"] is None


def test_on_reset_present_when_favorite_has_override(monkeypatch: pytest.MonkeyPatch) -> None:
    station = _station()
    favorite = FavoriteStation(station=station, has_sound_enhancement_override=True)
    frame = _frame(monkeypatch, playing=station)
    frame._radio_favorites.favorites.append(favorite)

    RadioMixin.open_sound_enhancements(frame)

    assert callable(_FakeSoundEnhanceDialog.instances[0].kwargs["on_reset"])


def test_on_reset_clears_override_and_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    station = _station()
    favorite = FavoriteStation(station=station, has_sound_enhancement_override=True)
    frame = _frame(monkeypatch, playing=station)
    frame._radio_favorites.favorites.append(favorite)

    RadioMixin.open_sound_enhancements(frame)
    on_reset = _FakeSoundEnhanceDialog.instances[0].kwargs["on_reset"]
    on_reset()

    assert favorite.has_sound_enhancement_override is False
    assert frame._saved == [True]


def test_on_reset_pushes_live_update_when_that_station_is_playing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    station = _station()
    favorite = FavoriteStation(station=station, has_sound_enhancement_override=True)
    frame = _frame(monkeypatch, playing=station)
    frame._radio_favorites.favorites.append(favorite)

    RadioMixin.open_sound_enhancements(frame)
    on_reset = _FakeSoundEnhanceDialog.instances[0].kwargs["on_reset"]
    on_reset()

    assert frame._calls == [
        (
            "set_enhancement",
            {"bass_db": 1.0, "mid_db": 2.0, "treble_db": 3.0, "compressor_enabled": True},
        )
    ]


def test_on_reset_does_not_push_live_update_when_a_different_station_is_playing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The dialog only ever offers Reset for the currently playing favorite,
    # so this only matters if playback changes between capturing the
    # callback and it actually running (e.g. some future async path) --
    # exercise the defensive guard directly rather than relying on
    # open_sound_enhancements' own resolution (which can't produce this
    # combination through its normal call path).
    station = _station("1")
    other_playing = _station("2")
    favorite = FavoriteStation(station=station, has_sound_enhancement_override=True)
    frame = _frame(monkeypatch, playing=station)
    frame._radio_favorites.favorites.append(favorite)

    RadioMixin.open_sound_enhancements(frame)
    on_reset = _FakeSoundEnhanceDialog.instances[0].kwargs["on_reset"]
    frame._radio_controller.state.station = other_playing
    on_reset()

    assert frame._calls == []
