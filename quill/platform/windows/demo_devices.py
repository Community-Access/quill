"""Microphones for Record a Demonstration: listed one at a time, found by identity.

**One device at a time (MX-187).** ``sounddevice.query_devices()`` decodes
every WASAPI and WDM-KS name in one pass, so a single name it cannot decode
-- a Bluetooth headset named after a phone, "Tony's ..." -- raised for the
whole list, and the microphone list came back empty. Each index is asked
about on its own here, and only the one that cannot be described is left out
and logged.

**The same device, never another one (MX-181, MX-114).** A microphone is
saved with its Windows endpoint ID as well as its name, and found by the ID
first. When the ID is gone and only the name matches, it is used and *said*
-- Quill Radio's rule in ``quill/ui/radio/output_device_guard.py``: a device
is given back out loud, never silently substituted. MME cuts names to 31
characters, so a cut name matches only when exactly one full name begins
with it. A device that will not open under its own Windows audio API is
tried as the same device under the next one (WASAPI, then DirectSound, then
MME), found by that same name rule.

The per-device enumeration is adapted from TG Drop Deck, Copyright (c) 2026
Tony Gebhard, MIT licence (https://github.com/tonygeb23/tg-drop-deck,
``dropdeck/mixer.py`` ``all_devices()``):

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to permit
    persons to whom the Software is furnished to do so, subject to the
    following conditions:

    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
    NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
    OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
    USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "FALLBACK_APIS",
    "Microphone",
    "all_input_devices",
    "endpoint_id_for",
    "list_microphones",
    "resolve_microphone",
    "resolve_saved_microphone",
    "same_device",
]

_MAPPERS = frozenset({"Microsoft Sound Mapper - Input", "Primary Sound Capture Driver"})
#: MME names are cut to 31 characters, and the cut can leave a trailing space.
_TRUNCATED = 30
_PREFERENCE = {"ASIO": 0, "Windows WASAPI": 1, "MME": 2, "Windows DirectSound": 3}
#: The order the same microphone is tried in when its own API will not open it.
FALLBACK_APIS = ("Windows WASAPI", "Windows DirectSound", "MME")


@dataclass
class Microphone:
    index: int
    name: str
    host_api: str
    channels: int
    #: The rate the device itself reports, tried after 48 and 44.1 kHz.
    default_rate: float = 48_000.0
    #: The Windows capture endpoint ID, when one is known for this name.
    endpoint_id: str = ""


def _sd() -> Any:
    import sounddevice as sd

    return sd


def _device_count(sd: Any) -> int:
    """How many devices PortAudio knows, without describing any of them."""
    lib = getattr(sd, "_lib", None)
    if lib is not None and hasattr(lib, "Pa_GetDeviceCount"):
        return max(0, int(lib.Pa_GetDeviceCount()))
    return len(sd.query_devices())


def all_input_devices() -> list[Microphone]:
    """Every input device PortAudio can describe, each asked about on its own."""
    sd = _sd()
    try:
        apis = {index: str(api["name"]) for index, api in enumerate(sd.query_hostapis())}
    except Exception:  # noqa: BLE001 - no host APIs means no devices
        logger.warning("Sound host APIs could not be listed", exc_info=True)
        return []
    found: list[Microphone] = []
    for index in range(_device_count(sd)):
        try:
            device = sd.query_devices(index)
            inputs = int(device.get("max_input_channels", 0))
            if inputs <= 0:
                continue
            found.append(
                Microphone(
                    index,
                    str(device["name"]).strip(),
                    apis.get(int(device["hostapi"]), ""),
                    inputs,
                    float(device.get("default_samplerate") or 48_000.0),
                )
            )
        except Exception as error:  # noqa: BLE001 - one bad name never empties the list
            logger.warning(
                "Sound device %d could not be described and is left out: %s", index, error
            )
    return found


def _capture_endpoints() -> dict[str, str]:
    """Active capture endpoints, friendly name to endpoint ID (names used once only)."""
    try:
        from quill.platform.windows.audio_routing import CAPTURE, list_devices

        devices = list_devices(CAPTURE)
    except Exception:  # noqa: BLE001 - no IDs is still a usable list
        return {}
    by_name: dict[str, list[str]] = {}
    for device in devices:
        by_name.setdefault(device.name, []).append(device.device_id)
    return {name: ids[0] for name, ids in by_name.items() if len(ids) == 1}


def list_microphones(*, with_ids: bool = False) -> list[Microphone]:
    """Input devices, one per name, preferring WASAPI's full names over MME's."""
    best: dict[str, Microphone] = {}
    for device in all_input_devices():
        api = device.host_api
        if api not in _PREFERENCE:
            continue
        name = device.name
        if api == "ASIO":
            # One ASIO driver often carries the same name as its WASAPI twin.
            name = f"{name} (ASIO)"
        candidate = replace(device, name=name)
        current = best.get(name)
        if current is None or _PREFERENCE[api] < _PREFERENCE[current.host_api]:
            best[name] = candidate
    # Drop MME's truncations (31 characters less any trailing space) when the
    # full name is also present, and the two mappers that are not devices.
    names = list(best)
    for name in names:
        mic = best[name]
        if name in _MAPPERS:
            best.pop(name, None)
        elif mic.host_api == "MME" and any(o != name and o.startswith(name) for o in names):
            best.pop(name, None)
    microphones = sorted(best.values(), key=lambda mic: mic.name.casefold())
    if with_ids:
        endpoints = _capture_endpoints()
        microphones = [replace(mic, endpoint_id=endpoints.get(mic.name, "")) for mic in microphones]
    return microphones


def endpoint_id_for(name: str) -> str:
    """The Windows endpoint ID of the microphone named *name*, or ``""``."""
    mic = resolve_microphone(name, list_microphones(with_ids=True)) if name else None
    return mic.endpoint_id if mic is not None else ""


def _matches(saved: str, candidates: list[Microphone]) -> Microphone | None:
    exact = [mic for mic in candidates if mic.name == saved]
    if exact:
        return exact[0]
    prefixed = [
        mic for mic in candidates if mic.name.startswith(saved) or saved.startswith(mic.name)
    ]
    if len(prefixed) == 1 and min(len(saved), len(prefixed[0].name)) >= _TRUNCATED:
        return prefixed[0]
    return None


def resolve_microphone(name: str, microphones: list[Microphone] | None = None) -> Microphone | None:
    """The device *name* names, never a different one (MX-181).

    An MME name truncated to 31 characters matches only when exactly one full
    name begins with it, so two headsets sharing their first 31 characters
    are never confused.
    """
    if microphones is None:
        microphones = list_microphones()
    if not name:
        sd = _sd()
        try:
            default = int(sd.default.device[0])
            info = sd.query_devices(default) if default >= 0 else None
        except Exception:  # noqa: BLE001 - no default is "the first one"
            info = None
        if info is not None:
            return resolve_microphone(str(info["name"]).strip(), microphones) or (
                microphones[0] if microphones else None
            )
        return microphones[0] if microphones else None
    return _matches(name, microphones)


def resolve_saved_microphone(name: str, endpoint_id: str = "") -> tuple[Microphone | None, str]:
    """The saved microphone, by endpoint ID first and name second, and what to say.

    The sentence is empty when the device was found as itself. It is said
    when the ID is gone and a device of the same name stands in, because
    that is a different device as far as Windows knows (MX-114).
    """
    microphones = list_microphones(with_ids=bool(endpoint_id))
    if endpoint_id:
        by_id = [mic for mic in microphones if mic.endpoint_id == endpoint_id]
        if by_id:
            return by_id[0], ""
        mic = resolve_microphone(name, microphones)
        if mic is not None:
            return mic, (
                f"The saved microphone was not found by its Windows identity, so Studio is "
                f"recording {mic.name}, the device with the same name."
            )
        return None, ""
    return resolve_microphone(name, microphones), ""


def same_device(mic: Microphone, devices: list[Microphone] | None = None) -> list[Microphone]:
    """*mic* under its own API, then under each fallback API, as the same device."""
    if devices is None:
        devices = all_input_devices()
    order = [mic]
    if mic.host_api == "ASIO":
        return order
    for api in FALLBACK_APIS:
        if api == mic.host_api:
            continue
        twin = _matches(mic.name, [d for d in devices if d.host_api == api])
        if twin is not None:
            order.append(replace(twin, endpoint_id=mic.endpoint_id))
    return order
