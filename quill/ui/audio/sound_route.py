"""Where is the sound? The words every app uses to answer for itself (FUX-03).

"Something is playing. Which app is it? Is the screen reader going into my
recording?" Each QUILL app answers that about itself, on request, with one
command, **Where Is the Sound?** (Alt+Shift+A where it is free). There is no
family mixer and no shared panel (``docs/design/fux-03-adoption.md``); this
module only keeps the wording and the device lookup the same, so two apps do
not describe the same headset in two ways.

Three facts a route needs, and where they come from:

* **The device's name.** Saved choices are ``wasapi/{guid}`` (the spelling the
  audio engines use) or, for microphones, a friendly name. Windows' own list of
  active endpoints (:mod:`quill.platform.windows.audio_routing`) turns either
  into the name Sound settings shows, without starting an audio engine.
* **Whether it is connected now.** A device Windows does not list as active is
  said to be not connected, because a configured route is not proof that sound
  reaches it (the FUX-03 acceptance list).
* **What "system default" means today.** "The system default" alone does not
  say where the sound goes, so it is followed by the name of the device that is
  the default right now.

When Windows cannot be asked (another platform, a COM failure), the answer
falls back to the words the app already had and claims nothing about the
connection. wx-free; never raises.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "COMMAND_LABEL",
    "DEFAULT_KEY",
    "Device",
    "input_device",
    "join",
    "microphone_note",
    "on_device",
    "output_device",
]

_log = logging.getLogger(__name__)

#: The menu item, the same in every app that has it.
COMMAND_LABEL = "&Where Is the Sound?"
#: Its key, the same in every app where it is free (family rule 2). Checked
#: against every media app's menus and keymaps on 2026-11-24.
DEFAULT_KEY = "Alt+Shift+A"

#: ``(device_id, name, is_default)`` for each active device, or None when
#: Windows could not be asked.
Lister = Callable[[], Sequence[tuple[str, str, bool]] | None]


@dataclass(frozen=True)
class Device:
    """One route's end, as it would be said."""

    #: What to call it: the device's name, or a plain phrase when unknown.
    label: str
    #: Nothing was chosen, so Windows decides (the system default).
    default: bool
    #: Windows lists it as active now. True when Windows could not be asked:
    #: an unanswered question is not reported as a missing device.
    connected: bool = True
    #: Windows answered, so ``connected`` is a fact and not a courtesy. Only a
    #: known connection may be offered as the way back to a device.
    known: bool = True


def _windows_devices(flow: int) -> list[tuple[str, str, bool]] | None:
    try:
        from quill.platform.windows import audio_routing

        return [(d.device_id, d.name, d.is_default) for d in audio_routing.list_devices(flow)]
    except Exception:  # noqa: BLE001 - not Windows, or COM said no: fall back
        _log.debug("Windows audio devices could not be listed", exc_info=True)
        return None


def _render_lister() -> Sequence[tuple[str, str, bool]] | None:
    return _windows_devices(0)


def _capture_lister() -> Sequence[tuple[str, str, bool]] | None:
    return _windows_devices(1)


def _guid(name: str) -> str:
    from quill.platform.windows.wave_out import device_guid

    return device_guid(name)


def _default(devices: Sequence[tuple[str, str, bool]] | None) -> Device:
    for _id, name, is_default in devices or ():
        if is_default:
            return Device(f"{name}, the system default", default=True)
    return Device("the system default device", default=True, known=devices is not None)


def output_device(device: str, *, lister: Lister | None = None, fallback: str = "") -> Device:
    """The playback device saved as *device* ("" = system default).

    *fallback* is the app's own name for it, used when Windows does not list it
    (the app's cached description, say) so the answer still names something
    the person chose.
    """
    devices = (lister or _render_lister)()
    device = str(device or "").strip()
    if not device:
        return _default(devices)
    guid = _guid(device)
    for device_id, name, _is_default in devices or ():
        if guid and _guid(device_id) == guid:
            return Device(name, default=False)
    label = fallback.strip() or "the chosen device"
    return Device(label, default=False, connected=devices is None, known=devices is not None)


def input_device(name: str, *, lister: Lister | None = None) -> Device:
    """The microphone saved by its friendly *name* ("" = system default)."""
    devices = (lister or _capture_lister)()
    name = str(name or "").strip()
    if not name:
        return _default(devices)
    wanted = name.casefold()
    names = [found for _id, found, _is_default in devices or ()]
    exact = [found for found in names if found.casefold() == wanted]
    # A saved name the driver has since lengthened ("USB Mic" -> "USB Mic (2)")
    # counts only when one device answers to it; two would be a guess.
    prefix = [found for found in names if found.casefold().startswith(wanted)]
    match = exact or (prefix if len(prefix) == 1 else [])
    if match:
        return Device(match[0], default=False)
    if len(prefix) > 1:
        return Device(name, default=False, connected=True, known=False)
    return Device(name, default=False, connected=devices is None, known=devices is not None)


def on_device(device: Device) -> str:
    """The device after a verb: "on Headphones (WH-1000)"."""
    if device.connected:
        return f"on {device.label}"
    return f"on {device.label}, not connected"


def microphone_note(asker: str, *, holder: Callable[[], str | None] | None = None) -> str:
    """One sentence when another family app holds the microphone, else "".

    *asker* is the asking app's id in :mod:`quill.core.dictation_owner`; it
    answers for its own microphone itself, so its own hold is not repeated.
    """
    from quill.core import dictation_owner

    try:
        held = (holder or dictation_owner.microphone_holder)()
    except Exception:  # noqa: BLE001 - an unreadable lock is no news
        return ""
    if held is None or held == asker:
        return ""
    name = dictation_owner.APP_NAMES.get(held, "")
    if not name:
        return "Another QUILL program is listening on the microphone."
    return f"{name} is listening on the microphone."


def join(sentences: Sequence[Any]) -> str:
    """The non-empty sentences, in order, as one answer."""
    return " ".join(str(s).strip() for s in sentences if str(s or "").strip())
