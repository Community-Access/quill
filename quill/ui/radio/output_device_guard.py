"""The output device is a promise the radio keeps, or says out loud that it cannot.

Reported 2026-09-28: "changing the sound card in the Audio menu is not
switching to a different card." libmpv switches WASAPI devices at runtime and
on reload -- probed on a real machine that day, with the AO log lines to show
it -- and the controller hands the chosen device to it before every load. So
the sound stays on the old card in exactly one situation: the mpv engine
cannot *open* the chosen device (a Bluetooth or USB headset that has gone to
sleep, a device whose id changed, one another program holds), the load fails,
and the app quietly rescues the station on Windows Media, which can only play
on the system default. Nothing was said and nothing was logged
(``testkspn.md`` had already named this as the top suspect for a reconnect
loop, since a device that dies mid-stream ends the file the same way).

Four rules, all here so the controller (at its GATE-11 ceiling) delegates:

1. **A playing mpv station switches device live.** mpv re-opens its audio
   output on the property change; there is nothing to reconnect and no gap.
2. **A load that fails with a device chosen is retried once on the system
   default, still on mpv**, and the listener is told which device could not
   be opened. Only if that fails too is it a stream problem, and the old
   cross-engine rescue takes over.
3. **The device is watched for.** While playing on the default in its place,
   the device list is checked every few seconds; the moment the chosen device
   is offered again, playback moves back to it, live, and says so.
4. **Windows Media with a device chosen is said.** WMP cannot route, so the
   fallback that used to be silent now tells the listener where the audio is.

Every decision is logged at INFO, because "nothing in quill.log records
which of these happened" was the other half of the report.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.ui.radio.mpv_radio_engine import list_audio_devices
from quill.ui.radio.playback_state import RESTARTABLE_STATES, RadioPlayerState

__all__ = [
    "WATCH_MS",
    "change_device",
    "device_label",
    "note_windows_media_fallback",
    "rescue_on_load_error",
]

_log = logging.getLogger(__name__)

#: How often a lost device is looked for. Each look opens a short-lived libmpv
#: handle to enumerate devices, so every few seconds, not every poll tick.
WATCH_MS = 10_000


def device_label(device: str) -> str:
    """What the listener calls *device*: its description, or the id itself."""
    if not device:
        return "the system default"
    for name, description in list_audio_devices():
        if name == device:
            return description
    return device


def _say(host: Any, message: str) -> None:
    notify = getattr(host, "_on_output_device_error", None)
    if notify is not None:
        notify(message)


def change_device(host: Any, device: str) -> None:
    """The listener chose *device* ("" = system default): apply it now."""
    device = device.strip()
    if device == host._output_device:
        return
    host._output_device = device
    host._device_fallback_active = False
    host._device_watch_token += 1
    label = device_label(device)
    _log.info("Output device chosen: %s (%s)", label, device or "auto")
    station = host._state.station
    if station is None or host._state.state not in RESTARTABLE_STATES:
        return
    if host._is_mpv_active() and host._mpv_engine is not None:
        # Live: mpv re-opens its audio output on the property change.
        host._mpv_engine.set_audio_device(device)
        _log.info("Output device applied live on mpv: %s", label)
        return
    # Windows Media cannot route; the reconnect goes through engine
    # selection, which brings mpv in for a chosen device.
    host.play_station(station)


def rescue_on_load_error(host: Any) -> bool:
    """A load failed with a device chosen: try the system default on mpv, once.

    ``True`` when a retry began. ``False`` hands the failure on to the
    cross-engine rescue, which is right for a stream mpv cannot play at all.
    """
    device = host._output_device
    station = host._state.station
    if (
        not device
        or station is None
        or host._device_rescued
        or host._device_fallback_active
        or not host._is_mpv_active()
        or host._mpv_engine is None
    ):
        return False
    host._device_rescued = True
    host._device_fallback_active = True
    host._mpv_engine.set_audio_device("")
    label = device_label(device)
    _log.warning(
        "Output device %s (%s) could not be opened; retrying on the default", label, device
    )
    _say(
        host,
        f"{label} could not be opened. Playing on the system default until it is available again.",
    )
    host._set_state(RadioPlayerState.CONNECTING, message="")
    url = host._resolve_playback_url(station)
    began = bool(host._engine.load(url))
    _watch(host, device)
    return began


def note_windows_media_fallback(host: Any) -> None:
    """The cross-engine rescue is moving to Windows Media with a device chosen."""
    if not host._output_device:
        return
    host._device_fallback_active = False
    host._device_watch_token += 1  # the watch belongs to the mpv engine
    _log.warning(
        "Windows Media is playing; the chosen output device %s is not in use",
        host._output_device,
    )
    _say(
        host,
        "Windows Media is playing this station, and it cannot use the chosen "
        "output device; the audio is on the system default.",
    )


def _watch(host: Any, device: str) -> None:
    token = host._device_watch_token

    def check() -> None:
        if token != host._device_watch_token or not host._device_fallback_active:
            return  # the listener chose again, or playback moved on
        if not host._is_mpv_active() or host._mpv_engine is None:
            return
        if device not in {name for name, _description in list_audio_devices()}:
            host._schedule_later(WATCH_MS, check)
            return
        host._mpv_engine.set_audio_device(device)
        host._device_fallback_active = False
        name = device_label(device)  # it is listed again, so it has its name back
        _log.info("Output device %s is back; playing on it again", name)
        _say(host, f"{name} is available again. Playing on it.")

    host._schedule_later(WATCH_MS, check)
