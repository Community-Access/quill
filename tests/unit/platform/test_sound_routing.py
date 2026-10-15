"""Routed earcons: on the chosen card when it is there, never silent when it is not."""

from __future__ import annotations

import pytest

from quill.core.sound_pack import SoundPack
from quill.platform import sound_routing
from quill.platform.sound_player import SoundPlayer
from quill.platform.sound_routing import RoutedBackend

_DEVICE = "wasapi/{ca86f65f-6b12-449a-ae6d-e99036afdb13}"


class _Default:
    """The detected backend: the system default device."""

    def __init__(self) -> None:
        self.played: list[bytes] = []
        self.volume: float | None = None
        self.shut = 0

    def play_wav(self, wav: bytes) -> None:
        self.played.append(wav)

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def shutdown(self, timeout: float = 2.0) -> None:
        self.shut += 1


class _Card:
    """A WaveOutPlayer stand-in: the chosen card."""

    instances: list[_Card] = []

    def __init__(self, index: int) -> None:
        self.device_index = index
        self.played: list[bytes] = []
        self.volume: float | None = None
        self.shut = False
        self.accepts = True
        _Card.instances.append(self)

    def play_wav(self, wav: bytes) -> bool:
        if self.accepts:
            self.played.append(wav)
        return self.accepts

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        return self.play_wav(wav)

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def shutdown(self, timeout: float = 2.0) -> None:
        self.shut = True


@pytest.fixture
def plugged(monkeypatch: pytest.MonkeyPatch) -> dict[str, int | None]:
    """Where the card is right now; set ``["index"]`` to None to unplug it."""
    from quill.platform.windows import wave_out

    state: dict[str, int | None] = {"index": 2}
    _Card.instances = []
    monkeypatch.setattr(wave_out, "find_device_index", lambda _name: state["index"])
    monkeypatch.setattr(wave_out, "WaveOutPlayer", _Card)
    monkeypatch.setattr(sound_routing, "_RESOLVE_SECONDS", 0.0)  # look every time
    return state


def test_sounds_go_to_the_chosen_card(plugged: dict[str, int | None]) -> None:
    default, heard = _Default(), []
    routed = RoutedBackend(_DEVICE, default, heard.append)
    routed.play_wav(b"A")
    assert _Card.instances[0].played == [b"A"]
    assert default.played == []
    assert heard == [True]


def test_an_unplugged_card_plays_on_the_default_device_and_says_so_once(
    plugged: dict[str, int | None],
) -> None:
    plugged["index"] = None
    default, heard = _Default(), []
    routed = RoutedBackend(_DEVICE, default, heard.append)
    for _ in range(3):
        routed.play_wav(b"A")
    assert default.played == [b"A", b"A", b"A"]  # never silent
    assert heard == [False]  # a change of state, not a report per sound


def test_a_card_plugged_back_in_is_found_without_touching_a_setting(
    plugged: dict[str, int | None],
) -> None:
    plugged["index"] = None
    default, heard = _Default(), []
    routed = RoutedBackend(_DEVICE, default, heard.append)
    routed.play_wav(b"A")
    plugged["index"] = 0  # back, and at a different position than before
    routed.play_wav(b"B")
    assert default.played == [b"A"]
    assert _Card.instances[-1].played == [b"B"]
    assert _Card.instances[-1].device_index == 0
    assert heard == [False, True]


def test_a_card_that_refuses_a_sound_falls_back_for_that_sound(
    plugged: dict[str, int | None],
) -> None:
    default = _Default()
    routed = RoutedBackend(_DEVICE, default)
    routed.play_wav(b"A")
    _Card.instances[0].accepts = False  # a clip waveOut cannot take, or a busy card
    routed.play_wav(b"B")
    assert default.played == [b"B"]


def test_volume_reaches_both_and_shutdown_leaves_the_default_to_its_owner(
    plugged: dict[str, int | None],
) -> None:
    default = _Default()
    routed = RoutedBackend(_DEVICE, default)
    routed.play_wav(b"A")
    routed.set_volume(0.4)
    assert default.volume == 0.4
    assert _Card.instances[0].volume == 0.4
    routed.shutdown()
    assert _Card.instances[0].shut is True
    assert default.shut == 0


def _player() -> tuple[SoundPlayer, _Default]:
    default = _Default()
    player = SoundPlayer(backend=default)
    player.load_pack(
        SoundPack(name="T", author="", description="", license="", events={"e": b"E", "f": b"F"})
    )
    return player, default


def test_the_player_routes_and_comes_back_to_the_default(plugged: dict[str, int | None]) -> None:
    player, default = _player()
    player.set_volume(0.5)
    assert player.set_output_device(_DEVICE) is True
    assert player.output_device == _DEVICE
    player.play("e")
    assert _Card.instances[-1].played == [b"E"]
    assert _Card.instances[-1].volume == 0.5  # the volume set before routing carries over
    assert player.set_output_device("") is True
    assert player.output_device == ""
    player.play("f")  # another event: the same one again would be inside its cooldown
    assert default.played == [b"F"]
    assert _Card.instances[0].shut is True  # the card is let go when routing ends


def test_the_player_says_when_the_card_is_not_there(plugged: dict[str, int | None]) -> None:
    plugged["index"] = None
    player, default = _player()
    assert player.set_output_device(_DEVICE) is False
    player.play("e")
    assert default.played == [b"E"]


def test_shutdown_releases_the_card_and_the_default_once_each(
    plugged: dict[str, int | None],
) -> None:
    player, default = _player()
    player.set_output_device(_DEVICE)
    player.play("e")
    player.shutdown()
    assert _Card.instances[-1].shut is True
    assert default.shut == 1


def test_mute_still_means_quiet_on_the_card(plugged: dict[str, int | None]) -> None:
    player, _default = _player()
    player.set_output_device(_DEVICE)
    player.set_muted(True)
    player.play("e")
    assert all(not card.played for card in _Card.instances)
