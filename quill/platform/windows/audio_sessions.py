"""Programs that are playing sound, and muting what *you* hear from each.

Windows keeps an audio session per program per playback device; this lists
them (process id, executable, peak level right now, muted or not) and sets
the session's own mute and volume -- exactly what the Windows Volume Mixer
does. That is a different thing from leaving a program out of a recording
(MX-121 keeps them separately named): muting a session here silences it for
the listener *and* for every recording, while leaving it out of a Studio
recording changes nothing anyone hears.

Pure comtypes over the Core Audio interfaces; no extra package. A session
that vanishes mid-call is skipped, never raised. Windows-only.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import HRESULT, POINTER, c_float, c_int, c_uint32, c_void_p, wintypes
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "AudioSession",
    "AudioSessionError",
    "list_sessions",
    "set_process_mute",
    "set_process_volume",
]

_RENDER = 0
_ACTIVE = 1
_CLSCTX_ALL = 23


class AudioSessionError(CodedError):
    """The Windows audio session list could not be read or changed."""

    code = "QUILL-STUDIO-SESSION-FAILED"


@dataclass(frozen=True)
class AudioSession:
    process_id: int
    name: str
    muted: bool
    volume: float
    peak: float
    devices: int = 1
    system_sounds: bool = False

    @property
    def spoken(self) -> str:
        state = "muted for you" if self.muted else f"volume {round(self.volume * 100)} percent"
        playing = "playing sound now" if self.peak > 0.001 else "quiet"
        return f"{self.name}: {state}, {playing}"


def _interfaces() -> dict[str, Any]:
    from comtypes import COMMETHOD, GUID, IUnknown

    class ISimpleAudioVolume(IUnknown):
        _iid_ = GUID("{87CE5498-68D6-44E5-9215-6DA47EF883D8}")
        _methods_ = [
            COMMETHOD([], HRESULT, "SetMasterVolume", (["in"], c_float), (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "GetMasterVolume", (["out"], POINTER(c_float))),
            COMMETHOD([], HRESULT, "SetMute", (["in"], wintypes.BOOL), (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "GetMute", (["out"], POINTER(wintypes.BOOL))),
        ]

    class IAudioMeterInformation(IUnknown):
        _iid_ = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
        _methods_ = [COMMETHOD([], HRESULT, "GetPeakValue", (["out"], POINTER(c_float)))]

    class IAudioSessionControl2(IUnknown):
        _iid_ = GUID("{bfb7ff88-7239-4fc9-8fa2-07c950be9c6d}")
        _methods_ = [
            COMMETHOD([], HRESULT, "GetState", (["out"], POINTER(c_int))),
            COMMETHOD([], HRESULT, "GetDisplayName", (["out"], POINTER(c_void_p))),
            COMMETHOD([], HRESULT, "SetDisplayName", (["in"], c_void_p), (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "GetIconPath", (["out"], POINTER(c_void_p))),
            COMMETHOD([], HRESULT, "SetIconPath", (["in"], c_void_p), (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "GetGroupingParam", (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "SetGroupingParam", (["in"], c_void_p), (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "RegisterAudioSessionNotification", (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "UnregisterAudioSessionNotification", (["in"], c_void_p)),
            COMMETHOD([], HRESULT, "GetSessionIdentifier", (["out"], POINTER(c_void_p))),
            COMMETHOD([], HRESULT, "GetSessionInstanceIdentifier", (["out"], POINTER(c_void_p))),
            COMMETHOD([], HRESULT, "GetProcessId", (["out"], POINTER(wintypes.DWORD))),
            COMMETHOD([], HRESULT, "IsSystemSoundsSession"),
        ]

    class IAudioSessionEnumerator(IUnknown):
        _iid_ = GUID("{E2F5BB11-0570-40CA-ACDD-3AA01277DEE8}")
        _methods_ = [
            COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(c_int))),
            COMMETHOD(
                [], HRESULT, "GetSession", (["in"], c_int), (["out"], POINTER(POINTER(IUnknown)))
            ),
        ]

    class IAudioSessionManager2(IUnknown):
        _iid_ = GUID("{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "GetAudioSessionControl",
                (["in"], c_void_p),
                (["in"], wintypes.DWORD),
                (["out"], POINTER(c_void_p)),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetSimpleAudioVolume",
                (["in"], c_void_p),
                (["in"], wintypes.DWORD),
                (["out"], POINTER(c_void_p)),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetSessionEnumerator",
                (["out"], POINTER(POINTER(IAudioSessionEnumerator))),
            ),
        ]

    class IMMDevice(IUnknown):
        _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "Activate",
                (["in"], POINTER(GUID)),
                (["in"], wintypes.DWORD),
                (["in"], c_void_p),
                (["out"], POINTER(POINTER(IUnknown))),
            ),
        ]

    class IMMDeviceCollection(IUnknown):
        _iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC5392387B5E}")
        _methods_ = [
            COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(c_uint32))),
            COMMETHOD(
                [], HRESULT, "Item", (["in"], c_uint32), (["out"], POINTER(POINTER(IMMDevice)))
            ),
        ]

    class IMMDeviceEnumerator(IUnknown):
        _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "EnumAudioEndpoints",
                (["in"], c_int),
                (["in"], wintypes.DWORD),
                (["out"], POINTER(POINTER(IMMDeviceCollection))),
            ),
        ]

    return {
        "volume": ISimpleAudioVolume,
        "meter": IAudioMeterInformation,
        "control2": IAudioSessionControl2,
        "manager": IAudioSessionManager2,
        "enumerator": IMMDeviceEnumerator,
        "clsid": GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}"),
    }


def _process_name(pid: int) -> str:
    if pid == 0:
        return "System sounds"
    try:
        import psutil

        return str(psutil.Process(pid).name())
    except Exception:  # noqa: BLE001 - the process ended between calls
        return f"Process {pid}"


def _each_session() -> list[tuple[int, Any, Any, Any]]:
    """``(pid, control2, volume, meter)`` for every session on every active output."""
    import comtypes
    from comtypes.client import CreateObject

    try:
        comtypes.CoInitialize()
    except OSError:
        pass
    com = _interfaces()
    try:
        enumerator = CreateObject(com["clsid"], interface=com["enumerator"], clsctx=_CLSCTX_ALL)
        devices = enumerator.EnumAudioEndpoints(_RENDER, _ACTIVE)
    except (OSError, comtypes.COMError) as error:
        raise AudioSessionError(f"Windows audio devices could not be listed: {error}") from error
    found = []
    for index in range(devices.GetCount()):
        try:
            device = devices.Item(index)
            manager = device.Activate(com["manager"]._iid_, _CLSCTX_ALL, None).QueryInterface(
                com["manager"]
            )
            sessions = manager.GetSessionEnumerator()
        except (OSError, comtypes.COMError):
            continue
        for number in range(sessions.GetCount()):
            try:
                unknown = sessions.GetSession(number)
                control = unknown.QueryInterface(com["control2"])
                pid = int(control.GetProcessId())
                volume = unknown.QueryInterface(com["volume"])
                meter = unknown.QueryInterface(com["meter"])
                found.append((pid, control, volume, meter))
            except (OSError, comtypes.COMError, ValueError):
                continue
    return found


def list_sessions(*, include_own: bool = False) -> list[AudioSession]:
    """One row per program, merged across playback devices, by name."""
    own = os.getpid()
    rows: dict[int, AudioSession] = {}
    for pid, control, volume, meter in _each_session():
        if pid == own and not include_own:
            continue
        try:
            muted = bool(volume.GetMute())
            level = float(volume.GetMasterVolume())
            peak = float(meter.GetPeakValue())
            system = control.IsSystemSoundsSession() == 0
        except Exception:  # noqa: BLE001 - the session closed while being read
            continue
        if pid in rows:
            previous = rows[pid]
            rows[pid] = AudioSession(
                pid,
                previous.name,
                previous.muted and muted,
                max(previous.volume, level),
                max(previous.peak, peak),
                previous.devices + 1,
                previous.system_sounds,
            )
        else:
            rows[pid] = AudioSession(pid, _process_name(pid), muted, level, peak, 1, system)
    return sorted(rows.values(), key=lambda s: (s.system_sounds, s.name.casefold()))


def set_process_mute(pid: int, muted: bool) -> int:
    """Mute or unmute every session of *pid*; the count of sessions changed."""
    changed = 0
    for found, _control, volume, _meter in _each_session():
        if found == pid:
            try:
                volume.SetMute(1 if muted else 0, None)
                changed += 1
            except Exception:  # noqa: BLE001 - closed while being changed
                continue
    if not changed:
        raise AudioSessionError("That program has no sound session now. Refresh the list.")
    return changed


def set_process_volume(pid: int, volume_level: float) -> int:
    """Set every session of *pid* to *volume_level* (0.0 to 1.0)."""
    level = min(1.0, max(0.0, volume_level))
    changed = 0
    for found, _control, volume, _meter in _each_session():
        if found == pid:
            try:
                volume.SetMasterVolume(ctypes.c_float(level), None)
                changed += 1
            except Exception:  # noqa: BLE001
                continue
    if not changed:
        raise AudioSessionError("That program has no sound session now. Refresh the list.")
    return changed
