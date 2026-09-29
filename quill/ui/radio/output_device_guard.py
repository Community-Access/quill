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
2. **A device that will not open is given back.** The load is retried once,
   still on mpv, on the device that was in use before the choice (the system
   default when there was none); the listener is told which device could not
   be opened and what the setting is now; and the setting itself goes back
   (Jeff, 2026-09-29: "if it can't work the sound card option should revert
   back to its original setting"). A choice that silently stayed while the
   sound went elsewhere is what made the switch look broken.
3. **The same on the way in.** A saved device that will not open when the app
   starts is handled the same way, so a copy is never stuck with a setting it
   cannot honour.
4. **Windows Media cannot take a device from us, and says so.** The wx.media
   control plays on the device Windows gives this app; nothing in it takes a
   device name. So a device chosen while the engine preference is Windows Media
   (classic) is given back with a sentence that names the route that works
   under that engine -- Windows' own per-app output device, in Sound settings
   under Volume mixer, the same answer QUILL Cast gives (``ui/media/
   output_device``) -- and the cross-engine rescue that lands on Windows Media
   with a device chosen says where the audio is. The engine preference itself
   is never changed for the listener (Jeff, 2026-09-29: "why is it forcing
   automatic mode and mpv when switching if windows media is selected, that
   should not be necessary at all"). Jeff's test on the C:/qr portable the same
   day: "the fix works for mpv but not for windows media" -- the sound sat on
   the default while the setting said speakers.

Every decision is logged at INFO or WARNING, because "nothing in quill.log
records which of these happened" was the other half of the report.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.ui.radio.mpv_radio_engine import list_audio_devices
from quill.ui.radio.playback_state import RESTARTABLE_STATES, RadioPlayerState

__all__ = [
    "change_device",
    "device_label",
    "note_windows_media_fallback",
    "rescue_on_load_error",
    "revert_for_windows_media",
]

_log = logging.getLogger(__name__)


def device_label(device: str) -> str:
    """What the listener calls *device*: its description, or the id itself."""
    if not device:
        return "System default"
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
    host._previous_output_device = host._output_device
    host._output_device = device
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
    """A load failed with a device chosen: give the device back, retry on mpv.

    ``True`` when a retry began. ``False`` hands the failure on to the
    cross-engine rescue, which is right for a stream mpv cannot play at all.
    """
    device = host._output_device
    station = host._state.station
    if (
        not device
        or station is None
        or host._device_rescued
        or not host._is_mpv_active()
        or host._mpv_engine is None
    ):
        return False
    host._device_rescued = True
    previous = getattr(host, "_previous_output_device", "")
    if previous == device:
        previous = ""
    label = device_label(device)
    back_to = device_label(previous)
    _log.warning(
        "Output device %s (%s) would not open; the setting is back to %s (%s)",
        label,
        device,
        back_to,
        previous or "auto",
    )
    host._output_device = previous
    host._previous_output_device = previous
    host._mpv_engine.set_audio_device(previous)
    reverted = getattr(host, "on_output_device_reverted", None)
    if reverted is not None:
        try:
            reverted(previous)  # the host persists the setting
        except Exception:  # noqa: BLE001 - a save that fails must not stop playback
            _log.exception("output device revert could not be saved")
    _say(host, f"{label} could not be opened, so the output device is back to {back_to}.")
    host._set_state(RadioPlayerState.CONNECTING, message="")
    url = host._resolve_playback_url(station)
    return bool(host._engine.load(url))


def revert_for_windows_media(host: Any) -> bool:
    """A device is chosen but the engine preference is Windows Media (classic),
    which cannot route: give the device back, persist that, and say why.
    ``True`` when there was something to give back."""
    device = host._output_device
    if not device or host._playback_engine != "wx":
        return False
    label = device_label(device)
    _log.warning(
        "Windows Media (classic) cannot use %s (%s); the setting is back to default", label, device
    )
    host._output_device = ""
    host._previous_output_device = ""
    reverted = getattr(host, "on_output_device_reverted", None)
    if reverted is not None:
        try:
            reverted("")
        except Exception:  # noqa: BLE001 - a save that fails must not stop playback
            _log.exception("output device revert could not be saved")
    _say(
        host,
        f"Windows Media (classic) plays on the device Windows gives Quill Radio, so the output "
        f"device is back to System default. To send it to {label}, choose Quill Radio's output "
        "device in Windows' Sound settings, under Volume mixer.",
    )
    return True


def note_windows_media_fallback(host: Any) -> None:
    """The cross-engine rescue is moving to Windows Media with a device chosen."""
    if not host._output_device:
        return
    _log.warning(
        "Windows Media is playing; the chosen output device %s is not in use",
        host._output_device,
    )
    _say(
        host,
        "Windows Media is playing this station, and it cannot use the chosen "
        "output device; the audio is on the device Windows gives Quill Radio.",
    )
