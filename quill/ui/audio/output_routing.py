"""Which sound cards the family can offer, and whether it can route to one.

One list for every engine: libmpv's ``wasapi/{guid}`` names, which the modern
Windows Media engine (:mod:`quill.ui.audio.winrt_engine`) understands too, so
a device saved under one engine is honoured by the other. mpv enumerates when
it is present; otherwise Windows does, in the same naming. wx-free.
"""

from __future__ import annotations

__all__ = [
    "engine_routes_devices",
    "forget_output_devices",
    "list_output_devices",
    "output_device_routing_available",
    "set_engine_output_device",
]

#: How long a device list stays fresh. Enumerating through libmpv builds and
#: tears down a handle on a 115 MB DLL -- about 2.5 seconds cold -- and every
#: Preferences window and device picker paid it again. Sound cards do not come
#: and go on that timescale, and a listener who has just plugged a headset in
#: waits a few seconds rather than forever; :func:`forget_output_devices` is
#: the explicit way to say "look again now".
_CACHE_SECONDS = 20.0
_cached: tuple[float, list[tuple[str, str]]] | None = None


def output_device_routing_available() -> bool:
    """Whether *some* engine on this machine can be pointed at a device."""
    from quill.ui.audio.winrt_engine import winrt_media_available
    from quill.ui.radio.mpv_radio_engine import mpv_output_device_available

    return mpv_output_device_available() or winrt_media_available()


def forget_output_devices() -> None:
    """Drop the cached device list, so the next ask enumerates for real.

    For the moments when the hardware really may have changed under us: a
    device that would not open, or a picker the listener has deliberately
    reopened to find something they just plugged in.
    """
    global _cached
    _cached = None


def _enumerate_output_devices() -> list[tuple[str, str]]:
    """``[(name, description)]``: mpv's list when libmpv is present, else Windows'."""
    from quill.ui.radio.mpv_radio_engine import list_audio_devices, mpv_output_device_available

    if mpv_output_device_available():
        devices = list_audio_devices()
        if devices:
            return devices
    from quill.ui.audio.winrt_engine import list_audio_devices as windows_devices

    return windows_devices()


def list_output_devices() -> list[tuple[str, str]]:
    """The sound cards this machine offers, in libmpv's ``wasapi/{guid}`` naming.

    Cached for :data:`_CACHE_SECONDS`, because the honest cost of asking is
    high: through libmpv it builds and tears down a handle on a 115 MB DLL, and
    opening Preferences paid that every single time. An empty answer is never
    cached -- that is the shape a failed or timed-out query takes, and caching
    it would turn one bad moment into twenty seconds of "no devices".
    """
    global _cached
    import time

    now = time.monotonic()
    if _cached is not None and now - _cached[0] < _CACHE_SECONDS:
        return list(_cached[1])
    devices = _enumerate_output_devices()
    if devices:
        _cached = (now, list(devices))
    return devices


def engine_routes_devices(engine: object) -> bool:
    """Whether *engine* can be pointed at a sound card.

    An engine says so by having ``set_audio_device``: libmpv's engines and the
    modern Windows Media engine do, the classic ``wx.media`` control does not.
    Asked of the object rather than of the machine, because which engine is
    playing is the thing that decides -- a machine with libmpv installed can
    still be playing on the classic control.
    """
    return callable(getattr(engine, "set_audio_device", None))


def set_engine_output_device(engine: object, name: str) -> bool:
    """Point *engine* at device *name* ("" = system default). Did it take?

    False when the engine has no device API, or refused the name. Never
    raises: a device that will not open is the caller's to explain, and an
    engine mid-teardown must not cost the caller anything.
    """
    setter = getattr(engine, "set_audio_device", None)
    if not callable(setter):
        return False
    try:
        setter(name)
    except Exception:  # noqa: BLE001 - a refused device is not a crash
        return False
    reader = getattr(engine, "audio_device", None)
    if not callable(reader):
        return True  # no readback to check against; the call did not fail
    try:
        return str(reader()) == name.strip()
    except Exception:  # noqa: BLE001 - no readback is not a failure
        return True
