"""Play an earcon on a chosen sound card, through Windows' waveOut API.

``winsound`` -- the earcon backend almost every Windows install runs on -- has
one destination: the system default device. So a listener who sends Quill
Radio to a broadcast card heard the radio there and every confirmation sound
on their desk speakers, which is backwards for the person who most needs them:
someone checking by ear that the station is on air (Rick Lewis, QUILLVille,
October 2026, Radio 3.2.0).

waveOut is the oldest audio API Windows has, which is the point: it ships with
every version, needs nothing installed, mixes (each sound opens its own handle
and Windows mixes them), has a volume control ``winsound`` never had, and can
open *any* output device by index.

**The part that makes this exact rather than a guess.** A waveOut device is an
index into a list that reshuffles whenever a headset is plugged in, and its
name is cut to 31 characters -- "Speakers (Realtek High Definiti" -- so neither
can be matched against the ``wasapi/{guid}`` names libmpv and the Windows Media
engine use for the radio. But since Vista every waveOut device answers
``DRV_QUERYFUNCTIONINSTANCEID`` with its endpoint id,
``{0.0.0.00000000}.{guid}``, and that GUID is the same one inside mpv's name.
Confirmed on real hardware: both lists named the Logi headset
``ca86f65f-6b12-449a-ae6d-e99036afdb13``. So a device saved for the radio finds
its waveOut index by identity, whatever order Windows lists them in today.

Windows only, ctypes only, never raises into a caller: a sound that cannot play
on the chosen card returns False, and the caller plays it on the default
device instead -- the listener hears a sound in the wrong place rather than no
sound at all.
"""

from __future__ import annotations

import ctypes
import io
import logging
import queue
import re
import sys
import threading
import time
import wave
from dataclasses import dataclass

__all__ = [
    "WaveOutDevice",
    "WaveOutPlayer",
    "device_guid",
    "find_device_index",
    "list_devices",
    "wave_out_available",
]

logger = logging.getLogger(__name__)

_CALLBACK_NULL = 0
_WHDR_DONE = 0x00000001
_MMSYSERR_NOERROR = 0
# DRV_RESERVED (0x0800) + 18 and + 17, from mmddk.h.
_DRV_QUERYFUNCTIONINSTANCEIDSIZE = 0x0812
_DRV_QUERYFUNCTIONINSTANCEID = 0x0811

#: The most sounds allowed to be in the air at once. Earcons are tens of
#: milliseconds long; more than a few overlapping means something is firing far
#: too often, and dropping the excess beats opening handles without bound.
_MAX_ACTIVE = 8

_GUID = re.compile(
    r"\{?([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\}?$"
)


def device_guid(name: str) -> str:
    """The endpoint GUID inside a device name, lower-case, or "" if none.

    Accepts every spelling the family stores or Windows reports:
    ``wasapi/{guid}`` (libmpv), ``{0.0.0.00000000}.{guid}`` (an endpoint id),
    or a bare ``{guid}``.
    """
    match = _GUID.search(str(name or "").strip())
    return match.group(1).lower() if match else ""


@dataclass(frozen=True)
class WaveOutDevice:
    """One output device as waveOut sees it today."""

    index: int
    name: str
    guid: str


def wave_out_available() -> bool:
    """Whether this machine has waveOut at all (Windows, winmm present)."""
    return _winmm() is not None


_WINMM: object | None = None
_WINMM_TRIED = False


def _winmm() -> object | None:
    global _WINMM, _WINMM_TRIED
    if _WINMM_TRIED:
        return _WINMM
    _WINMM_TRIED = True
    if sys.platform != "win32":
        return None
    try:
        _WINMM = ctypes.WinDLL("winmm")  # type: ignore[attr-defined]
    except OSError:
        _WINMM = None
    return _WINMM


def _structures() -> tuple[type, type, type]:
    """The three structs, built lazily so importing this module costs nothing."""
    from ctypes import wintypes

    class WAVEOUTCAPSW(ctypes.Structure):
        _fields_ = [
            ("wMid", wintypes.WORD),
            ("wPid", wintypes.WORD),
            ("vDriverVersion", wintypes.UINT),
            ("szPname", wintypes.WCHAR * 32),
            ("dwFormats", wintypes.DWORD),
            ("wChannels", wintypes.WORD),
            ("wReserved1", wintypes.WORD),
            ("dwSupport", wintypes.DWORD),
        ]

    class WAVEFORMATEX(ctypes.Structure):
        _pack_ = 1  # mmeapi.h declares it under pshpack1
        _fields_ = [
            ("wFormatTag", wintypes.WORD),
            ("nChannels", wintypes.WORD),
            ("nSamplesPerSec", wintypes.DWORD),
            ("nAvgBytesPerSec", wintypes.DWORD),
            ("nBlockAlign", wintypes.WORD),
            ("wBitsPerSample", wintypes.WORD),
            ("cbSize", wintypes.WORD),
        ]

    class WAVEHDR(ctypes.Structure):
        pass

    WAVEHDR._fields_ = [
        ("lpData", ctypes.c_void_p),
        ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD),
        ("dwUser", ctypes.c_size_t),
        ("dwFlags", wintypes.DWORD),
        ("dwLoops", wintypes.DWORD),
        ("lpNext", ctypes.POINTER(WAVEHDR)),
        ("reserved", ctypes.c_size_t),
    ]
    return WAVEOUTCAPSW, WAVEFORMATEX, WAVEHDR


def list_devices() -> list[WaveOutDevice]:
    """Every waveOut output device, with the endpoint GUID that names it.

    Empty off Windows or when winmm will not answer. A device whose driver
    does not report an endpoint id is listed with ``guid=""`` -- it can still be
    seen, it just cannot be matched to a saved choice.
    """
    winmm = _winmm()
    if winmm is None:
        return []
    caps_type, _fmt, _hdr = _structures()
    devices: list[WaveOutDevice] = []
    try:
        count = int(winmm.waveOutGetNumDevs())  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - no answer is no devices
        return []
    for index in range(count):
        caps = caps_type()
        try:
            if winmm.waveOutGetDevCapsW(  # type: ignore[attr-defined]
                ctypes.c_size_t(index), ctypes.byref(caps), ctypes.sizeof(caps)
            ):
                continue
        except Exception:  # noqa: BLE001
            continue
        devices.append(WaveOutDevice(index, str(caps.szPname), _endpoint_guid(winmm, index)))
    return devices


def _endpoint_guid(winmm: object, index: int) -> str:
    from ctypes import wintypes

    try:
        size = wintypes.ULONG(0)
        if winmm.waveOutMessage(  # type: ignore[attr-defined]
            ctypes.c_void_p(index), _DRV_QUERYFUNCTIONINSTANCEIDSIZE, ctypes.byref(size), 0
        ):
            return ""
        buffer = ctypes.create_unicode_buffer(max(1, size.value // 2 + 1))
        if winmm.waveOutMessage(  # type: ignore[attr-defined]
            ctypes.c_void_p(index),
            _DRV_QUERYFUNCTIONINSTANCEID,
            buffer,
            ctypes.c_size_t(size.value),
        ):
            return ""
        return device_guid(buffer.value)
    except Exception:  # noqa: BLE001 - an old driver that cannot say is not an error
        return ""


def find_device_index(name: str, devices: list[WaveOutDevice] | None = None) -> int | None:
    """The waveOut index of saved device *name* right now, or None.

    By GUID, never by position or display name: positions move when hardware
    does, and display names are truncated and can repeat.
    """
    guid = device_guid(name)
    if not guid:
        return None
    for device in devices if devices is not None else list_devices():
        if device.guid == guid:
            return device.index
    return None


@dataclass
class _Clip:
    channels: int
    rate: int
    width: int
    frames: bytes


def _read_clip(wav: bytes) -> _Clip | None:
    """PCM samples out of a WAV, or None when ``wave`` cannot read it.

    The bundled packs are PCM. A pack with an unusual encoding is played on the
    default device by the caller's fallback rather than refused.
    """
    try:
        with wave.open(io.BytesIO(wav), "rb") as handle:
            clip = _Clip(
                handle.getnchannels(),
                handle.getframerate(),
                handle.getsampwidth(),
                handle.readframes(handle.getnframes()),
            )
    except Exception:  # noqa: BLE001 - unreadable is "not for this backend"
        return None
    if clip.channels < 1 or clip.rate < 1 or clip.width not in (1, 2, 3, 4) or not clip.frames:
        return None
    return clip


class _Playing:
    """One sound in the air: its handle, header and the buffer they point at."""

    def __init__(self, handle: object, header: object, buffer: object, deadline: float) -> None:
        self.handle = handle
        self.header = header
        self.buffer = buffer
        self.deadline = deadline


class WaveOutPlayer:
    """Plays WAV bytes on one waveOut device, mixing overlapping sounds.

    One daemon thread owns every handle: it opens each sound, watches for it to
    finish, and closes it, so a caller -- usually the UI thread -- only ever
    hands over bytes and returns.
    """

    def __init__(self, device_index: int) -> None:
        self._index = int(device_index)
        self._volume = 1.0
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=_MAX_ACTIVE)
        self._thread = threading.Thread(
            target=self._worker, name="QuillSoundPlayer-waveout", daemon=True
        )
        self._thread.start()

    @property
    def device_index(self) -> int:
        return self._index

    def set_volume(self, volume: float) -> None:
        try:
            self._volume = max(0.0, min(1.0, float(volume)))
        except (TypeError, ValueError):
            pass

    def play_wav(self, wav: bytes) -> bool:
        """Queue *wav* for this device. False when it cannot be played here."""
        if _winmm() is None or _read_clip(wav) is None:
            return False
        try:
            self._queue.put_nowait(wav)
        except queue.Full:
            pass  # a burst of earcons; dropping one is the right answer
        return True

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        """Play *wav* on the calling thread and return once the device is done."""
        playing = self._open(wav, time.monotonic() + max(0.0, timeout))
        if playing is None:
            return False
        try:
            while time.monotonic() < playing.deadline and not self._done(playing):
                time.sleep(0.01)
        finally:
            self._close(playing)
        return True

    def shutdown(self, timeout: float = 2.0) -> None:
        try:
            self._queue.put(None, timeout=timeout)
        except queue.Full:
            pass
        self._thread.join(timeout=timeout)

    # -- the worker --------------------------------------------------------

    def _worker(self) -> None:
        active: list[_Playing] = []
        while True:
            try:
                item = self._queue.get(timeout=0.01 if active else None)
            except queue.Empty:
                item = b""
            if item is None:
                for playing in active:
                    self._close(playing)
                return
            if item:
                playing = self._open(item, time.monotonic() + 15.0)
                if playing is not None:
                    active.append(playing)
            still: list[_Playing] = []
            for playing in active:
                if self._done(playing) or time.monotonic() >= playing.deadline:
                    self._close(playing)
                else:
                    still.append(playing)
            active = still

    def _open(self, wav: bytes, deadline: float) -> _Playing | None:
        winmm = _winmm()
        clip = _read_clip(wav)
        if winmm is None or clip is None:
            return None
        from ctypes import wintypes

        _caps, fmt_type, hdr_type = _structures()
        fmt = fmt_type()
        fmt.wFormatTag = 1  # WAVE_FORMAT_PCM
        fmt.nChannels = clip.channels
        fmt.nSamplesPerSec = clip.rate
        fmt.wBitsPerSample = clip.width * 8
        fmt.nBlockAlign = clip.channels * clip.width
        fmt.nAvgBytesPerSec = clip.rate * fmt.nBlockAlign
        fmt.cbSize = 0
        handle = wintypes.HANDLE()
        try:
            result = winmm.waveOutOpen(  # type: ignore[attr-defined]
                ctypes.byref(handle),
                ctypes.c_size_t(self._index),
                ctypes.byref(fmt),
                ctypes.c_size_t(0),
                ctypes.c_size_t(0),
                _CALLBACK_NULL,
            )
        except Exception:  # noqa: BLE001
            return None
        if result != _MMSYSERR_NOERROR:
            logger.debug("waveOutOpen(%d) failed: %d", self._index, result)
            return None
        level = int(round(self._volume * 0xFFFF))
        try:
            winmm.waveOutSetVolume(handle, wintypes.DWORD(level | (level << 16)))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a fixed volume is not a failure
            pass
        buffer = ctypes.create_string_buffer(clip.frames, len(clip.frames))
        header = hdr_type()
        header.lpData = ctypes.cast(buffer, ctypes.c_void_p)
        header.dwBufferLength = len(clip.frames)
        try:
            if winmm.waveOutPrepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header)):  # type: ignore[attr-defined]
                winmm.waveOutClose(handle)  # type: ignore[attr-defined]
                return None
            if winmm.waveOutWrite(handle, ctypes.byref(header), ctypes.sizeof(header)):  # type: ignore[attr-defined]
                winmm.waveOutUnprepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header))  # type: ignore[attr-defined]
                winmm.waveOutClose(handle)  # type: ignore[attr-defined]
                return None
        except Exception:  # noqa: BLE001
            return None
        return _Playing(handle, header, buffer, deadline)

    @staticmethod
    def _done(playing: _Playing) -> bool:
        return bool(getattr(playing.header, "dwFlags", _WHDR_DONE) & _WHDR_DONE)

    @staticmethod
    def _close(playing: _Playing) -> None:
        winmm = _winmm()
        if winmm is None:
            return
        try:
            if not WaveOutPlayer._done(playing):
                winmm.waveOutReset(playing.handle)  # type: ignore[attr-defined]
            winmm.waveOutUnprepareHeader(  # type: ignore[attr-defined]
                playing.handle, ctypes.byref(playing.header), ctypes.sizeof(playing.header)
            )
            winmm.waveOutClose(playing.handle)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - closing a dead handle is not news
            pass
