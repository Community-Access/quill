"""waveOut device lookup: by endpoint GUID, never by position or display name."""

from __future__ import annotations

import io
import sys
import wave

import pytest

from quill.platform.windows import wave_out
from quill.platform.windows.wave_out import WaveOutDevice, device_guid, find_device_index

_GUID = "ca86f65f-6b12-449a-ae6d-e99036afdb13"


def _wav(frames: bytes = b"\0" * 400, *, width: int = 2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(width)
        handle.setframerate(8000)
        handle.writeframes(frames)
    return buf.getvalue()


@pytest.mark.parametrize(
    "spelling",
    [
        f"wasapi/{{{_GUID}}}",  # libmpv, and what RadioHistory.output_device stores
        f"{{0.0.0.00000000}}.{{{_GUID}}}",  # what waveOut's endpoint query returns
        f"{{{_GUID.upper()}}}",
        _GUID,
    ],
)
def test_every_spelling_the_family_stores_names_the_same_card(spelling: str) -> None:
    assert device_guid(spelling) == _GUID


@pytest.mark.parametrize("value", ["", "auto", "System default", "wasapi/", None])
def test_a_name_without_a_guid_names_no_card(value: object) -> None:
    assert device_guid(value) == ""  # type: ignore[arg-type]


def test_the_card_is_found_by_identity_whatever_position_windows_gives_it() -> None:
    # The same headset, listed second today because something else was
    # plugged in first: position would pick the wrong card, the GUID does not.
    devices = [
        WaveOutDevice(0, "Speakers (Realtek High Definiti", "e633b0f5-6fbf-4e42-8b91-2dbc39479395"),
        WaveOutDevice(1, "Speakers (Logi USB Headset)", _GUID),
    ]
    assert find_device_index(f"wasapi/{{{_GUID}}}", devices) == 1


def test_an_unplugged_card_is_not_found_rather_than_guessed() -> None:
    devices = [WaveOutDevice(0, "Speakers", "e633b0f5-6fbf-4e42-8b91-2dbc39479395")]
    assert find_device_index(f"wasapi/{{{_GUID}}}", devices) is None
    assert find_device_index("", devices) is None


def test_a_pcm_clip_is_readable_and_rubbish_is_not() -> None:
    assert wave_out._read_clip(_wav()) is not None
    assert wave_out._read_clip(b"not a wav") is None
    assert wave_out._read_clip(_wav(b"")) is None  # nothing to play is not a sound


@pytest.mark.machine_global
@pytest.mark.skipif(sys.platform != "win32", reason="waveOut is Windows")
def test_a_silent_clip_really_plays_on_a_real_card() -> None:
    devices = wave_out.list_devices()
    if not devices:
        pytest.skip("this machine has no output device")
    assert all(device.guid for device in devices), "every Vista+ driver reports an endpoint"
    player = wave_out.WaveOutPlayer(devices[0].index)
    try:
        assert player.play_wav_blocking(_wav(), timeout=2.0) is True
        assert player.play_wav(_wav()) is True
        assert player.play_wav(b"not a wav") is False  # the caller falls back
    finally:
        player.shutdown()
