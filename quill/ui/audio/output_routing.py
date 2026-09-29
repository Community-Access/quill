"""Which sound cards the family can offer, and whether it can route to one.

One list for every engine: libmpv's ``wasapi/{guid}`` names, which the modern
Windows Media engine (:mod:`quill.ui.audio.winrt_engine`) understands too, so
a device saved under one engine is honoured by the other. mpv enumerates when
it is present; otherwise Windows does, in the same naming. wx-free.
"""

from __future__ import annotations

__all__ = ["list_output_devices", "output_device_routing_available"]


def output_device_routing_available() -> bool:
    """Whether *some* engine on this machine can be pointed at a device."""
    from quill.ui.audio.winrt_engine import winrt_media_available
    from quill.ui.radio.mpv_radio_engine import mpv_output_device_available

    return mpv_output_device_available() or winrt_media_available()


def list_output_devices() -> list[tuple[str, str]]:
    """``[(name, description)]``: mpv's list when libmpv is present, else Windows'."""
    from quill.ui.radio.mpv_radio_engine import list_audio_devices, mpv_output_device_available

    if mpv_output_device_available():
        devices = list_audio_devices()
        if devices:
            return devices
    from quill.ui.audio.winrt_engine import list_audio_devices as windows_devices

    return windows_devices()
