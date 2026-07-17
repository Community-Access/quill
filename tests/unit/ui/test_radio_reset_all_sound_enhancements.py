"""Quill Radio Preferences: "Reset All Stations' Sound Enhancements..."

Bulk counterpart to the per-station Reset to Default button -- clears
every favorite's override at once, confirms first (it's not undoable),
and skips the confirm entirely when there's nothing to reset.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

import quill.ui.app_preferences_dialog as app_preferences_dialog_module
from quill.apps.radio import RadioAppFrame
from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.radio.player_controller import RadioPlayerState


def _station(key_suffix: str = "1") -> RadioStation:
    return RadioStation(
        name=f"Station {key_suffix}", stream_url=f"https://example.com/{key_suffix}"
    )


def _frame(*, playing: RadioStation | None = None) -> Any:
    calls: list[tuple[str, dict]] = []
    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame.frame = object()
    frame._announce = lambda _msg: None
    frame._radio_history = SimpleNamespace(
        eq_bass_db=1.0,
        eq_mid_db=2.0,
        eq_treble_db=3.0,
        compressor_enabled=True,
        now_playing_template="{title}[ by {artist}]",
    )
    frame._radio_favorites = RadioFavoritesStore()
    frame._radio_controller = SimpleNamespace(
        state=SimpleNamespace(station=playing, state=RadioPlayerState.PLAYING),
        set_enhancement=lambda **kw: calls.append(("set_enhancement", kw)),
    )
    saved: list[bool] = []
    frame._save_radio_favorites = lambda: saved.append(True)
    frame._calls = calls  # type: ignore[attr-defined]
    frame._saved = saved  # type: ignore[attr-defined]
    return frame


def test_reset_all_announces_and_skips_confirm_when_nothing_overridden() -> None:
    frame = _frame()
    announced: list[str] = []
    frame._announce = lambda msg: announced.append(msg)
    message_box_calls: list[tuple] = []
    frame._show_message_box = lambda *a, **k: message_box_calls.append((a, k)) or wx.YES

    RadioAppFrame._reset_all_sound_enhancements(frame)

    assert message_box_calls == [], "nothing to reset -- must not pop a confirm dialog"
    assert announced == ["No stations have their own Sound Enhancements to reset."]
    assert frame._saved == []


def test_reset_all_confirms_before_resetting_and_declining_changes_nothing() -> None:
    frame = _frame()
    favorite = FavoriteStation(station=_station(), has_sound_enhancement_override=True)
    frame._radio_favorites.favorites.append(favorite)
    frame._show_message_box = lambda *a, **k: wx.NO

    RadioAppFrame._reset_all_sound_enhancements(frame)

    assert favorite.has_sound_enhancement_override is True
    assert frame._saved == []


def test_reset_all_clears_every_overridden_favorite_on_confirm() -> None:
    frame = _frame()
    fav1 = FavoriteStation(station=_station("1"), has_sound_enhancement_override=True)
    fav2 = FavoriteStation(station=_station("2"), has_sound_enhancement_override=True)
    fav3 = FavoriteStation(station=_station("3"), has_sound_enhancement_override=False)
    frame._radio_favorites.favorites.extend([fav1, fav2, fav3])
    frame._show_message_box = lambda *a, **k: wx.YES

    RadioAppFrame._reset_all_sound_enhancements(frame)

    assert fav1.has_sound_enhancement_override is False
    assert fav2.has_sound_enhancement_override is False
    assert fav3.has_sound_enhancement_override is False  # was already off
    assert frame._saved == [True], "must save once, not once per favorite"


def test_reset_all_live_updates_when_playing_station_was_reset() -> None:
    station = _station()
    frame = _frame(playing=station)
    favorite = FavoriteStation(station=station, has_sound_enhancement_override=True)
    frame._radio_favorites.favorites.append(favorite)
    frame._show_message_box = lambda *a, **k: wx.YES

    RadioAppFrame._reset_all_sound_enhancements(frame)

    assert frame._calls == [
        (
            "set_enhancement",
            {"bass_db": 1.0, "mid_db": 2.0, "treble_db": 3.0, "compressor_enabled": True},
        )
    ]


def test_reset_all_no_live_update_when_playing_station_had_no_override() -> None:
    playing = _station("playing")
    frame = _frame(playing=playing)
    other = FavoriteStation(station=_station("other"), has_sound_enhancement_override=True)
    frame._radio_favorites.favorites.append(other)
    frame._show_message_box = lambda *a, **k: wx.YES

    RadioAppFrame._reset_all_sound_enhancements(frame)

    assert frame._calls == []


def test_reset_all_announces_the_count() -> None:
    frame = _frame()
    fav1 = FavoriteStation(station=_station("1"), has_sound_enhancement_override=True)
    fav2 = FavoriteStation(station=_station("2"), has_sound_enhancement_override=True)
    frame._radio_favorites.favorites.extend([fav1, fav2])
    frame._show_message_box = lambda *a, **k: wx.YES
    announced: list[str] = []
    frame._announce = lambda msg: announced.append(msg)

    RadioAppFrame._reset_all_sound_enhancements(frame)

    assert announced == ["Reset 2 stations to the shared default."]


class _FakePreferencesDialog:
    instances: list[_FakePreferencesDialog] = []

    def __init__(self, parent: object, **kwargs: Any) -> None:
        self.kwargs = kwargs
        _FakePreferencesDialog.instances.append(self)

    def show(self):
        return None  # Cancel -- we only care what the dialog was constructed with.


def test_open_preferences_passes_a_reset_all_action(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakePreferencesDialog.instances = []
    monkeypatch.setattr(app_preferences_dialog_module, "PreferencesDialog", _FakePreferencesDialog)
    frame = _frame()
    frame._radio_history.close_action = "ask"
    frame._radio_history.resume_on_launch = False
    frame._radio_history.check_updates_on_startup = False
    frame._radio_history.announce_dialog_transitions = False
    frame._radio_history.recover_from_website = True

    RadioAppFrame._open_preferences(frame)

    actions = _FakePreferencesDialog.instances[0].kwargs["actions"]
    assert len(actions) == 1
    assert actions[0].on_click == frame._reset_all_sound_enhancements
