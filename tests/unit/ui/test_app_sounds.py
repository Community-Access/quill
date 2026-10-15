"""The family's App Sounds: routing, Alt+Shift+M, and following an app's audio."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import app_sound_route as route
from quill.core import app_sounds_store as store
from quill.ui import app_sounds, sound_manager

_CARD = "wasapi/{ca86f65f-6b12-449a-ae6d-e99036afdb13}"


class _Host:
    def __init__(self, app: str = "weather", name: str = "Quill Weather", **extra: Any) -> None:
        self._app_sounds_id = app
        self._app_sounds_name = name
        self.said: list[str] = []
        for key, value in extra.items():
            setattr(self, key, value)

    def _announce(self, text: str, **_kwargs: Any) -> None:
        self.said.append(text)


@pytest.fixture
def data_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(app_sounds, "_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        app_sounds, "device_label", lambda d: "the headset" if d else "the system default device"
    )
    return tmp_path


@pytest.fixture
def routed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(
        sound_manager,
        "set_output_device",
        lambda device, on_route=None: calls.append(device) or True,
    )
    return calls


@pytest.fixture
def cues(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from quill.ui import companion_cues

    played: list[str] = []
    monkeypatch.setattr(companion_cues, "post_cue", played.append)
    return played


def test_an_app_without_audio_starts_on_the_system_default(data_dir, routed) -> None:  # type: ignore[no-untyped-def]
    app_sounds.apply(_Host())
    assert routed == [""]


def test_radio_sounds_follow_the_radio_card(data_dir, routed) -> None:  # type: ignore[no-untyped-def]
    host = _Host("radio", "Quill Radio", _radio_history=SimpleNamespace(output_device=_CARD))
    app_sounds.apply(host)
    assert routed == [_CARD]


def test_quill_hosting_the_radio_keeps_its_own_sounds_put(data_dir, routed) -> None:  # type: ignore[no-untyped-def]
    host = _Host("quill", "QUILL", _radio_history=SimpleNamespace(output_device=_CARD))
    app_sounds.apply(host)
    assert routed == [""]  # the editor's sounds never follow a station


def test_alt_shift_m_turns_this_app_off_and_back(data_dir, routed, cues) -> None:  # type: ignore[no-untyped-def]
    store.save(data_dir, "weather", store.AppSoundChoice(_CARD))
    host = _Host()
    app_sounds.toggle(host)
    assert routed[-1] == route.NONE
    assert host.said[-1] == "Quill Weather's sounds off."
    assert cues == ["sound_off"]  # the last sound, where they were
    app_sounds.toggle(host)
    assert routed[-1] == _CARD
    assert host.said[-1] == "Quill Weather's sounds on, playing on the headset."
    assert cues == ["sound_off", "sound_on"]


def test_one_app_off_leaves_the_others_alone(data_dir, routed, cues) -> None:  # type: ignore[no-untyped-def]
    app_sounds.toggle(_Host())
    assert store.load(data_dir, "weather", has_own_audio=False).choice == route.NONE
    assert store.load(data_dir, "quill", has_own_audio=False).choice == ""


def test_sharing_apps_keep_in_step(data_dir, routed, cues) -> None:  # type: ignore[no-untyped-def]
    from quill.core import family_preferences

    for app in ("weather", "inkwell"):
        family_preferences.set_sharing(data_dir, app, True, SimpleNamespace())
    app_sounds.toggle(_Host())
    assert store.load(data_dir, "inkwell", has_own_audio=False).choice == route.NONE
    assert store.load(data_dir, "converter", has_own_audio=False).choice == ""  # not sharing


def test_moving_the_radio_moves_following_sounds_and_says_so_once(data_dir, routed, cues) -> None:  # type: ignore[no-untyped-def]
    history = SimpleNamespace(output_device="")
    host = _Host("radio", "Quill Radio", _radio_history=history)
    history.output_device = _CARD
    assert app_sounds.own_device_changed(host) is True
    assert routed[-1] == _CARD
    assert cues == ["sound_on"]  # you hear where they went


def test_a_card_of_their_own_does_not_follow(data_dir, routed, cues) -> None:  # type: ignore[no-untyped-def]
    store.save(data_dir, "radio", store.AppSoundChoice(""))
    host = _Host("radio", "Quill Radio", _radio_history=SimpleNamespace(output_device=_CARD))
    assert app_sounds.own_device_changed(host) is False
    assert routed == []


def test_an_unplugged_card_is_said_once_and_its_return_once() -> None:
    host = _Host()
    host._app_sound_target = _CARD
    for routed_now in (False, False, True, True):
        app_sounds._route_changed(host, _CARD, routed_now)
    assert len(host.said) == 2
    assert "playing on the system default device until it is back" in host.said[0]
    assert host.said[1].startswith("Quill Weather's sounds are back on")


def test_reaching_the_card_from_the_start_says_nothing() -> None:
    host = _Host()
    host._app_sound_target = _CARD
    app_sounds._route_changed(host, _CARD, True)
    assert host.said == []  # GATE-13: only what the listener could not know


def test_a_host_with_no_id_is_left_alone(routed) -> None:  # type: ignore[no-untyped-def]
    host = _Host(app="")
    app_sounds.apply(host)
    app_sounds.toggle(host)
    assert routed == []
    assert host.said == []


def test_the_help_names_the_app_and_the_key() -> None:
    radio = _Host("radio", "Quill Radio", _radio_history=SimpleNamespace(output_device=""))
    assert "Quill Radio's own sounds" in app_sounds.help_text(radio)
    assert "Same as its audio" in app_sounds.help_text(radio)
    assert "Same as" not in app_sounds.help_text(_Host())
    assert "Alt+Shift+M" in app_sounds.help_text(_Host())
