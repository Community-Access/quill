"""Where Is the Sound? in Quill Radio: what is playing or recording, and where it goes.

FUX-03 (``docs/design/fux-03-adoption.md``). Radio could already say what is
playing (What's Playing?, Ctrl+T) and change the sound card (Output Device...,
Ctrl+Shift+D), but nothing said which card the sound was on, whether that card
was still connected, what the second player was doing, or that a recording
takes the stream itself rather than what comes out of the speakers. A listener
who heard nothing had no way to tell a muted station from a headset that had
gone to sleep.

One command answers, said once and only when asked (Audio > Where Is the
Sound?, Alt+Shift+A). In order, and only the parts that are true now:

1. The main player: what it is doing, and the device it is on -- by name, with
   "the system default" followed by the device that is the default today, and
   "not connected" when Windows does not list it. On the classic Windows Media
   control, which cannot be pointed at a device, it says that the device is the
   one Windows gives Quill Radio.
2. A chosen device that would not open earlier this session, so the radio went
   back to another one (``output_device_guard``, rule 2): which one, and that
   Output Device sends it back. Nothing moves by itself when the device returns;
   choosing it again is the deliberate recovery.
3. The second player: a background station or a mirror, and its device.
4. Recordings: how many, and that they save the stream, so the output device,
   volume and mute do not change what is recorded.
5. Another family app listening on the microphone (Radio's Dictate Here asks
   QUILL Transcribe to listen).

wx-free; the host is the Radio mixin (QUILL or Quill Radio).
"""

from __future__ import annotations

from typing import Any

from quill.ui.audio import sound_route

__all__ = ["compose", "forget_lost_device", "remember_lost_device", "say"]

_CONNECTING = ("CONNECTING", "BUFFERING", "RECONNECTING")


def remember_lost_device(controller: Any, device: str, label: str) -> None:
    """``output_device_guard`` gave *device* back: keep it for this session."""
    controller._lost_output_device = (device, label)


def forget_lost_device(controller: Any) -> None:
    """The listener chose a device again; the old story is over."""
    controller._lost_output_device = None


def _classic(controller: Any) -> bool:
    """The classic Windows Media control is playing, which cannot route."""
    from quill.ui.audio.output_routing import engine_routes_devices

    engine = getattr(controller, "_engine", None)
    return engine is not None and not engine_routes_devices(engine)


def _main_player(controller: Any, where: str) -> str:
    state = controller.state
    name = state.state.name if state.state is not None else "STOPPED"
    station = state.station.display_name if state.station is not None else ""
    if not station or name in ("STOPPED", "ERROR"):
        return f"Nothing is playing. The radio plays {where}."
    if name == "PAUSED":
        return f"{station} is paused, {where}."
    if name in _CONNECTING:
        return f"Connecting to {station}, to play {where}."
    # Mute first: it is the usual answer to "why can't I hear it".
    return f"Muted. Playing {station} {where}." if state.muted else f"Playing {station} {where}."


def _cached_label(device: str) -> str:
    """The description the device picker last saw, without enumerating again."""
    if not device:
        return ""
    from quill.ui.audio.output_routing import cached_output_devices

    return next((d for n, d in cached_output_devices() or [] if n == device), "")


def _windows_choice(app_output: Any) -> str:
    """The device Windows has given this program in Volume mixer, or "" (default)."""
    import os

    try:
        if app_output is None:
            from quill.platform.windows.audio_routing import app_output as windows_app_output

            app_output = windows_app_output
        return str(app_output(os.getpid()) or "")
    except Exception:  # noqa: BLE001 - no answer means Windows' default
        return ""


def _where(controller: Any, lister: Any, app_output: Any = None) -> str:
    if _classic(controller):
        # The classic control cannot be pointed at a device: Windows chooses.
        device = sound_route.output_device(_windows_choice(app_output), lister=lister)
        return f"{sound_route.on_device(device)}, chosen by Windows"
    chosen = str(getattr(controller, "output_device", "") or "")
    device = sound_route.output_device(chosen, lister=lister, fallback=_cached_label(chosen))
    return sound_route.on_device(device)


def _lost(controller: Any, lister: Any) -> str:
    lost = getattr(controller, "_lost_output_device", None)
    if not lost:
        return ""
    device, label = lost
    back = sound_route.output_device(device, lister=lister, fallback=label)
    if back.known and back.connected and not back.default:
        again = "It is connected again; Output Device, Ctrl+Shift+D, can choose it."
    else:
        again = "Output Device, Ctrl+Shift+D, can choose it again once it is connected."
    return f"Earlier, {label} would not open, so the radio switched back. {again}"


def _second(host: Any) -> str:
    second = getattr(host, "_second_output", None)
    if second is None or not getattr(second, "active", False):
        return ""
    from quill.core.radio import second_output as rule

    where = second.device_label or "another device"
    if second.mode == rule.BACKGROUND:
        station = getattr(second.station, "display_name", "")
        named = f"Background station {station}" if station else "A background station"
        verb = "is paused" if second.paused else "plays"
        return f"{named} {verb} on {where}."
    return f"A mirror of the main player plays on {where}."


def _recordings(host: Any) -> str:
    recorder = getattr(host, "_radio_recorder", None)
    try:
        count = int(getattr(recorder, "active_count", 0) or 0) if recorder is not None else 0
    except Exception:  # noqa: BLE001 - a recorder mid-teardown has nothing to say
        count = 0
    if not count:
        return ""
    what = "Recording 1 station" if count == 1 else f"Recording {count} stations"
    return f"{what}; volume and mute do not affect recordings."


def compose(host: Any, *, lister: Any = None, holder: Any = None, app_output: Any = None) -> str:
    """The whole answer, as one string. The keyword arguments are for tests."""
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return "The radio player has not started yet."
    where = _where(controller, lister, app_output)
    return sound_route.join([
        _main_player(controller, where),
        _lost(controller, lister),
        _second(host),
        _recordings(host),
        sound_route.microphone_note("radio", holder=holder),
    ])


def say(host: Any) -> None:
    """Alt+Shift+A: speak (and braille) the answer once."""
    host._announce(compose(host))
