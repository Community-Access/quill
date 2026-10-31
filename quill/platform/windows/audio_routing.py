"""Sound cards and where each program plays: the Devices and Programs tabs of the Mixer.

Three things Windows Settings does, done here with the same user-mode
interfaces it uses, so no driver is involved:

- **List playback and recording devices**, with their friendly names and
  which is the default (``IMMDeviceEnumerator``, ``IPropertyStore``).
- **Set the default and communications device** (``IPolicyConfig``, the
  interface the Sound control panel uses; undocumented but stable since
  Windows 7).
- **Move one program to another sound card**, as Settings, App volume and
  device preferences does (``IAudioPolicyConfigFactory``, Windows 10 1803 and
  later; undocumented, so every change is read back and a refusal is said
  plainly).
- **Recording level and mute** of an input device (``IAudioEndpointVolume``).

All calls are vtable calls over raw COM pointers, the pattern
:mod:`quill.platform.windows.face_detect` uses; nothing here imports wx.
Windows-only.
"""

from __future__ import annotations

import ctypes
from ctypes import POINTER, Structure, byref, c_float, c_int32, c_uint32, c_void_p, wintypes
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.platform.windows.face_detect import _GUID, _method, _release

__all__ = [
    "AudioDevice",
    "AudioRoutingError",
    "app_output",
    "input_level",
    "list_devices",
    "set_app_output",
    "set_default_device",
    "set_input_level",
    "set_input_mute",
]

RENDER, CAPTURE = 0, 1
CONSOLE, MULTIMEDIA, COMMUNICATIONS = 0, 1, 2
_ACTIVE = 1
_CLSCTX_ALL = 23
_STGM_READ = 0
_VT_LPWSTR = 31

_CLSID_ENUMERATOR = _GUID.parse("BCDE0395-E52F-467C-8E3D-C4579291692E")
_IID_ENUMERATOR = _GUID.parse("A95664D2-9614-4F35-A746-DE8DB63617E6")
_CLSID_POLICY = _GUID.parse("870af99c-171d-4f9e-af0d-e63df40c2bc9")
_IID_POLICY = _GUID.parse("f8679f50-850a-41cf-9c72-430f290290c8")
_IID_ENDPOINT_VOLUME = _GUID.parse("5CDF2C82-841E-4546-9722-0CF74078229A")
#: IAudioPolicyConfigFactory changed IID in Windows 10 21H2; try the new one first.
_IID_APP_POLICY = (
    _GUID.parse("ab3d4648-e242-459f-b02f-541c70306324"),
    _GUID.parse("2a59116d-6c4f-45e0-a74f-707e3fef9258"),
)
_RENDER_SUFFIX = "#{e6327cad-dcec-4949-ae8a-991e976a79d2}"
_CAPTURE_SUFFIX = "#{2eef81be-33fa-4800-9670-1cd474972c3f}"
_MMDEVAPI_PREFIX = "\\\\?\\SWD#MMDEVAPI#"


class AudioRoutingError(CodedError):
    """A sound device or a program's output could not be read or changed."""

    code = "QUILL-STUDIO-ROUTING-FAILED"


class _PropertyKey(Structure):
    _fields_ = [("fmtid", _GUID), ("pid", wintypes.DWORD)]


class _PropVariant(Structure):
    _fields_ = [
        ("vt", wintypes.WORD),
        ("r1", wintypes.WORD),
        ("r2", wintypes.WORD),
        ("r3", wintypes.WORD),
        ("value", c_void_p),
        ("pad", c_void_p),
    ]


_FRIENDLY_NAME = _PropertyKey(_GUID.parse("a45c254e-df1c-4efd-8020-67d146a850e0"), 14)


@dataclass(frozen=True)
class AudioDevice:
    device_id: str
    name: str
    flow: int
    is_default: bool = False
    is_communications: bool = False

    @property
    def spoken(self) -> str:
        roles = []
        if self.is_default:
            roles.append("default")
        if self.is_communications:
            roles.append("communications")
        return self.name + (f" ({' and '.join(roles)})" if roles else "")


def _init() -> None:
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # apartment-threaded, like wx
    except OSError:
        pass


def _create(clsid: _GUID, iid: _GUID) -> c_void_p:
    _init()
    pointer = c_void_p()
    status = ctypes.windll.ole32.CoCreateInstance(
        byref(clsid), None, _CLSCTX_ALL, byref(iid), byref(pointer)
    )
    if status != 0 or not pointer:
        raise AudioRoutingError(f"Windows audio is unavailable ({status & 0xFFFFFFFF:#010x}).")
    return pointer


def _string(pointer: c_void_p) -> str:
    text = ctypes.wstring_at(pointer) if pointer else ""
    ctypes.windll.ole32.CoTaskMemFree(pointer)
    return text


def _device_id(device: c_void_p) -> str:
    raw = c_void_p()
    _method(device, 5, POINTER(c_void_p))(byref(raw))  # IMMDevice::GetId
    return _string(raw)


def _friendly_name(device: c_void_p) -> str:
    store = c_void_p()
    _method(device, 4, wintypes.DWORD, POINTER(c_void_p))(_STGM_READ, byref(store))
    try:
        value = _PropVariant()
        _method(store, 5, POINTER(_PropertyKey), POINTER(_PropVariant))(
            byref(_FRIENDLY_NAME), byref(value)
        )
        name = ctypes.wstring_at(value.value) if value.vt == _VT_LPWSTR and value.value else ""
        ctypes.windll.ole32.PropVariantClear(byref(value))
        return name
    finally:
        _release(store)


def _default_id(enumerator: c_void_p, flow: int, role: int) -> str:
    device = c_void_p()
    try:
        _method(enumerator, 4, c_int32, c_int32, POINTER(c_void_p))(flow, role, byref(device))
    except OSError:
        return ""  # no device of that kind at all
    try:
        return _device_id(device)
    finally:
        _release(device)


def list_devices(flow: int = RENDER) -> list[AudioDevice]:
    """Active playback (``RENDER``) or recording (``CAPTURE``) devices, by name."""
    enumerator = _create(_CLSID_ENUMERATOR, _IID_ENUMERATOR)
    try:
        default = _default_id(enumerator, flow, CONSOLE)
        communications = _default_id(enumerator, flow, COMMUNICATIONS)
        collection = c_void_p()
        _method(enumerator, 3, c_int32, wintypes.DWORD, POINTER(c_void_p))(
            flow, _ACTIVE, byref(collection)
        )
        try:
            count = c_uint32(0)
            _method(collection, 3, POINTER(c_uint32))(byref(count))
            devices = []
            for index in range(count.value):
                device = c_void_p()
                _method(collection, 4, c_uint32, POINTER(c_void_p))(index, byref(device))
                try:
                    device_id = _device_id(device)
                    devices.append(
                        AudioDevice(
                            device_id,
                            _friendly_name(device) or device_id,
                            flow,
                            device_id == default,
                            device_id == communications,
                        )
                    )
                finally:
                    _release(device)
            return sorted(devices, key=lambda d: d.name.casefold())
        finally:
            _release(collection)
    except OSError as error:
        raise AudioRoutingError(f"Sound devices could not be listed: {error}") from error
    finally:
        _release(enumerator)


def set_default_device(device_id: str, *, communications: bool = False) -> None:
    """Make *device_id* the Windows default (or communications) device."""
    policy = _create(_CLSID_POLICY, _IID_POLICY)
    try:
        roles = (COMMUNICATIONS,) if communications else (CONSOLE, MULTIMEDIA)
        for role in roles:
            _method(policy, 13, wintypes.LPCWSTR, c_int32)(device_id, role)
    except OSError as error:
        raise AudioRoutingError(f"Windows did not change the default device: {error}") from error
    finally:
        _release(policy)


# -- one program's sound card ------------------------------------------------------


def _app_policy() -> c_void_p:
    from quill.platform.windows.face_detect import _Runtime

    runtime = _Runtime()
    for iid in _IID_APP_POLICY:
        try:
            factory = runtime.factory("Windows.Media.Internal.AudioPolicyConfig", iid)
        except OSError:
            continue
        if factory:
            return factory
    raise AudioRoutingError(
        "This version of Windows does not let programs choose a sound card per program."
    )


def _hstring(text: str) -> c_void_p:
    handle = c_void_p()
    if text:
        ctypes.windll.combase.WindowsCreateString(text, len(text), byref(handle))
    return handle


def _long_id(device_id: str, flow: int) -> str:
    suffix = _RENDER_SUFFIX if flow == RENDER else _CAPTURE_SUFFIX
    return f"{_MMDEVAPI_PREFIX}{device_id}{suffix}" if device_id else ""


def _short_id(long_id: str) -> str:
    text = long_id
    if text.startswith(_MMDEVAPI_PREFIX):
        text = text[len(_MMDEVAPI_PREFIX) :]
    for suffix in (_RENDER_SUFFIX, _CAPTURE_SUFFIX):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text


def app_output(process_id: int) -> str:
    """The sound card *process_id* is moved to, or ``""`` for the Windows default."""
    factory = _app_policy()
    try:
        handle = c_void_p()
        _method(factory, 26, c_uint32, c_int32, c_int32, POINTER(c_void_p))(
            process_id, RENDER, MULTIMEDIA, byref(handle)
        )
        if not handle:
            return ""
        raw = ctypes.windll.combase.WindowsGetStringRawBuffer
        raw.restype = c_void_p
        text = ctypes.wstring_at(raw(handle, None))
        ctypes.windll.combase.WindowsDeleteString(handle)
        return _short_id(text)
    except OSError as error:
        raise AudioRoutingError(f"Windows did not say where that program plays: {error}") from error
    finally:
        _release(factory)


def set_app_output(process_id: int, device_id: str) -> None:
    """Move *process_id*'s sound to *device_id*; ``""`` sends it back to the default.

    Windows remembers the choice for that program, as Settings does. The
    change is read back; if Windows kept the old one, this raises.
    """
    factory = _app_policy()
    try:
        long_id = _long_id(device_id, RENDER)
        call = _method(factory, 25, c_uint32, c_int32, c_int32, c_void_p)
        for role in (CONSOLE, MULTIMEDIA):
            handle = _hstring(long_id)
            try:
                call(process_id, RENDER, role, handle)
            finally:
                if handle:
                    ctypes.windll.combase.WindowsDeleteString(handle)
    except OSError as error:
        raise AudioRoutingError(f"Windows did not move that program: {error}") from error
    finally:
        _release(factory)
    if app_output(process_id) != device_id:
        raise AudioRoutingError("Windows did not keep the new sound card for that program.")


# -- recording level -----------------------------------------------------------------


def _endpoint_volume(device_id: str) -> c_void_p:
    enumerator = _create(_CLSID_ENUMERATOR, _IID_ENUMERATOR)
    try:
        device = c_void_p()
        _method(enumerator, 5, wintypes.LPCWSTR, POINTER(c_void_p))(device_id, byref(device))
        try:
            volume = c_void_p()
            _method(device, 3, POINTER(_GUID), wintypes.DWORD, c_void_p, POINTER(c_void_p))(
                byref(_IID_ENDPOINT_VOLUME), _CLSCTX_ALL, None, byref(volume)
            )
            return volume
        finally:
            _release(device)
    except OSError as error:
        raise AudioRoutingError(f"That device's level cannot be read: {error}") from error
    finally:
        _release(enumerator)


def input_level(device_id: str) -> tuple[float, bool]:
    """``(level 0.0 to 1.0, muted)`` of a recording device."""
    volume = _endpoint_volume(device_id)
    try:
        level = c_float(0)
        muted = wintypes.BOOL(0)
        _method(volume, 9, POINTER(c_float))(byref(level))
        _method(volume, 15, POINTER(wintypes.BOOL))(byref(muted))
        return float(level.value), bool(muted.value)
    finally:
        _release(volume)


def set_input_level(device_id: str, level: float) -> None:
    volume = _endpoint_volume(device_id)
    try:
        _method(volume, 7, c_float, c_void_p)(min(1.0, max(0.0, level)), None)
    except OSError as error:
        raise AudioRoutingError(f"Windows did not change the level: {error}") from error
    finally:
        _release(volume)


def set_input_mute(device_id: str, muted: bool) -> None:
    volume = _endpoint_volume(device_id)
    try:
        _method(volume, 14, wintypes.BOOL, c_void_p)(1 if muted else 0, None)
    except OSError as error:
        raise AudioRoutingError(f"Windows did not change the mute: {error}") from error
    finally:
        _release(volume)
