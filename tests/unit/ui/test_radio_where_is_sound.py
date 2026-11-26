"""Where Is the Sound? in Quill Radio (FUX-03): the player, its device, and the rest.

The device list Windows reports is injected, so these run anywhere; the
controller and the device rescue are the real ones (``test_radio_output_device_guard``
builds them the same way).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.radio import second_output as rule
from quill.ui.radio import output_device_guard as guard
from quill.ui.radio import where_is_sound
from tests.unit.ui.test_radio_output_device_guard import _make, _station

HEADSET_GUID = "0f3c7a1e-1111-4222-8333-944455556666"
SPEAKERS_GUID = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
HEADSET = "wasapi/{" + HEADSET_GUID + "}"
SPEAKERS = "wasapi/{" + SPEAKERS_GUID + "}"

#: Windows' active playback devices: (id, name, is default).
WINDOWS = [
    ("{0.0.0.00000000}.{" + SPEAKERS_GUID + "}", "Speakers (Realtek)", True),
    ("{0.0.0.00000000}.{" + HEADSET_GUID + "}", "Headphones (Logi USB Headset)", False),
]
WITHOUT_HEADSET = [WINDOWS[0]]


def _host(controller, **extra):
    return SimpleNamespace(_radio_controller=controller, **extra)


def _say(host, devices=WINDOWS, holder=None):
    return where_is_sound.compose(host, lister=lambda: devices, holder=lambda: holder)


@pytest.fixture
def radio(wx_session_app, monkeypatch: pytest.MonkeyPatch):
    made = _make(monkeypatch, output_device="")
    monkeypatch.setattr(
        guard,
        "list_audio_devices",
        lambda: [(HEADSET, "Headphones (Logi USB Headset)"), (SPEAKERS, "Speakers (Realtek)")],
    )
    made["controller"]._engine = made["mpv"]  # mpv is playing, and it routes
    return made


def test_stopped_names_the_system_default_device(radio) -> None:
    assert _say(_host(radio["controller"])) == (
        "Nothing is playing. The radio plays on Speakers (Realtek), the system default."
    )


def test_playing_names_the_chosen_device_by_its_windows_name(radio) -> None:
    c = radio["controller"]
    c.play_station(_station())
    radio["finish"]()
    c.set_output_device(HEADSET)
    assert _say(_host(c)) == "Playing KSPN on Headphones (Logi USB Headset)."


def test_a_chosen_device_windows_does_not_list_is_said_to_be_not_connected(radio) -> None:
    c = radio["controller"]
    c.play_station(_station())
    radio["finish"]()
    c.set_output_device(HEADSET)
    answer = _say(_host(c), devices=WITHOUT_HEADSET)
    assert answer == "Playing KSPN on the chosen device, not connected."


def test_muted_and_paused_are_said(radio) -> None:
    c = radio["controller"]
    c.play_station(_station())
    radio["finish"]()
    c.toggle_mute()
    assert _say(_host(c)) == "Muted. Playing KSPN on Speakers (Realtek), the system default."


def test_the_classic_windows_media_control_says_windows_decides(radio) -> None:
    c = radio["controller"]
    c.play_station(_station())
    radio["finish"]()
    c._engine = radio["wx"]  # the classic control has no set_audio_device
    headset = WINDOWS[1][0]
    answer = where_is_sound.compose(
        _host(c), lister=lambda: WINDOWS, holder=lambda: None, app_output=lambda _pid: headset
    )
    assert answer == "Playing KSPN on Headphones (Logi USB Headset), chosen by Windows."


def test_a_device_that_would_not_open_is_said_again_with_the_way_back(radio) -> None:
    """The guard gave the headset back; asking later says so, and that choosing it
    again is how to return, once Windows lists it."""
    c, mpv = radio["controller"], radio["mpv"]
    c.play_station(_station())
    radio["finish"]()
    mpv.fail_devices = {HEADSET}
    c.set_output_device(HEADSET)
    c.play_station(_station())
    radio["finish"]()  # fails on the headset, retried on the default
    radio["finish"]()  # ...which plays
    answer = _say(_host(c))
    assert (
        "Earlier, Headphones (Logi USB Headset) would not open, so the radio switched back. "
        "It is connected again; Output Device, Ctrl+Shift+D, can choose it." in answer
    )
    gone = _say(_host(c), devices=WITHOUT_HEADSET)
    assert "can choose it again once it is connected" in gone
    unknown = _say(_host(c), devices=None)  # Windows could not be asked: no false promise
    assert "It is connected again" not in unknown
    c.set_output_device(SPEAKERS)  # a deliberate choice ends the story
    assert "Earlier" not in _say(_host(c))


def test_second_player_recordings_and_microphone_are_each_one_sentence(radio) -> None:
    second = SimpleNamespace(
        active=True,
        mode=rule.BACKGROUND,
        device_label="USB Speakers",
        station=SimpleNamespace(display_name="KFI"),
        paused=False,
    )
    host = _host(
        radio["controller"],
        _second_output=second,
        _radio_recorder=SimpleNamespace(active_count=2),
    )
    answer = _say(host, holder="transcribe")
    assert "Background station KFI plays on USB Speakers." in answer
    assert "Recording 2 stations; volume and mute do not affect recordings." in answer
    assert answer.endswith("QUILL Transcribe is listening on the microphone.")
    second.mode = rule.MIRROR
    assert "A mirror of the main player plays on USB Speakers." in _say(host)


class _PaletteHost:
    """Records every palette registration; any other attribute is a no-op."""

    def __init__(self) -> None:
        self.registered: dict[str, object] = {}
        self.said: list[str] = []
        self.commands = SimpleNamespace(try_register=self._register, register=self._register)

    def _register(self, command_id, _title, handler, *_args, **_kwargs) -> None:
        self.registered[command_id] = handler

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def __getattr__(self, name: str):
        return lambda *_a, **_k: None


def test_the_command_is_on_the_palette_and_alt_shift_a(monkeypatch) -> None:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.ui.radio import palette_commands

    assert APP_KEYMAPS["radio"]["radio.where_is_sound"] == "Alt+Shift+A"
    host = _PaletteHost()
    try:
        palette_commands.register_radio_commands(host)
    except Exception:  # noqa: BLE001 - later rows need a real host; ours came first
        pass
    monkeypatch.setattr(where_is_sound, "compose", lambda _host: "answer")
    host.registered["radio.where_is_sound"]()
    assert host.said == ["answer"]
