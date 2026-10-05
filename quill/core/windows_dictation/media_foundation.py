"""Reading a recording with Windows Media Foundation, which every Windows has.

Transcribe a Recording (:mod:`~quill.core.windows_dictation.audio_file`) has to
read MP3, M4A and AAC, WAV, Ogg and Opus, FLAC and WMA in QUILL Lite too, and
QUILL Lite ships without ffmpeg. libsndfile (``soundfile``, already in the shared
runtime) reads WAV, FLAC, Ogg, Opus and MP3; Media Foundation is the part of
Windows that plays music in Windows' own players, and it reads MP3, AAC in M4A
and MP4, WMA, WAV and FLAC with the decoders Windows already has. Between the
two every format above is covered with nothing added to the installers.

This is the Source Reader, called through ``ctypes`` rather than a COM package:
open the file, ask for the first audio stream as 32-bit float, read it a
sample at a time. Resampling and mixing down to one channel happen in
:mod:`~quill.core.windows_dictation.audio_file`, which does it the same way for
every decoder.

Windows-only by nature; :func:`available` says ``False`` anywhere else, and the
caller falls through to the next decoder. wx-free.
"""

from __future__ import annotations

import ctypes
import sys
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from quill.core.error_codes import CodedError

__all__ = ["MediaFoundationError", "MediaFoundationReader", "available"]

_MF_VERSION = 0x00020070
_MFSTARTUP_NOSOCKET = 0x1
_COINIT_MULTITHREADED = 0x0
_RPC_E_CHANGED_MODE = -2147417850  # 0x80010106: COM already set up another way
_FIRST_AUDIO_STREAM = 0xFFFFFFFD
_ALL_STREAMS = 0xFFFFFFFE
_MEDIA_SOURCE = 0xFFFFFFFF
_READERF_ERROR = 0x1
_READERF_ENDOFSTREAM = 0x2
_READERF_CURRENTMEDIATYPECHANGED = 0x20

# vtable slots (IUnknown is 0-2; IMFAttributes 3-32; see mfobjects.h, mfreadwrite.h)
_RELEASE = 2
_ATTR_GET_UINT32 = 7
_ATTR_SET_GUID = 24
_READER_SET_STREAM_SELECTION = 4
_READER_GET_CURRENT_MEDIA_TYPE = 6
_READER_SET_CURRENT_MEDIA_TYPE = 7
_READER_READ_SAMPLE = 9
_READER_GET_PRESENTATION_ATTRIBUTE = 12
_SAMPLE_CONVERT_TO_CONTIGUOUS = 41
_BUFFER_LOCK = 3
_BUFFER_UNLOCK = 4


class MediaFoundationError(CodedError):
    """Windows could not read the recording."""

    code = "QUILL-DICTATION-FILE-MEDIAFOUNDATION"


class _GUID(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.c_ulong),
        ("data2", ctypes.c_ushort),
        ("data3", ctypes.c_ushort),
        ("data4", ctypes.c_ubyte * 8),
    ]


def _guid(text: str) -> _GUID:
    return _GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


_MT_MAJOR_TYPE = _guid("48eba18e-f8c9-4687-bf11-0a74c9f96a8f")
_MT_SUBTYPE = _guid("f7e34c9a-42e8-4714-b74b-cb29d72c35e5")
_MEDIATYPE_AUDIO = _guid("73647561-0000-0010-8000-00aa00389b71")
_AUDIOFORMAT_FLOAT = _guid("00000003-0000-0010-8000-00aa00389b71")
_MT_AUDIO_NUM_CHANNELS = _guid("37e48bf5-645e-4c5b-89de-ada9e29b696a")
_MT_AUDIO_SAMPLES_PER_SECOND = _guid("5faeeae7-0290-4c31-9e8a-c534f68d9dba")
_PD_DURATION = _guid("6c990d33-bb8e-477a-8598-0d5d96fcd88a")


class _PropVariant(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("reserved1", ctypes.c_ushort),
        ("reserved2", ctypes.c_ushort),
        ("reserved3", ctypes.c_ushort),
        ("value", ctypes.c_ulonglong),
        ("extra", ctypes.c_ulonglong),
    ]


def available() -> bool:
    """Whether Media Foundation can be asked at all (Windows, with its DLLs)."""
    if sys.platform != "win32":
        return False
    try:
        ctypes.WinDLL("mfplat.dll")
        ctypes.WinDLL("mfreadwrite.dll")
    except OSError:
        return False
    return True


def _method(pointer: ctypes.c_void_p, index: int, *argtypes: Any) -> Callable[..., int]:
    """COM method *index* of the object at *pointer*, ready to call."""
    table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    prototype = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)
    function = prototype(table[index])

    def call(*args: Any) -> int:
        return int(function(pointer, *args))

    return call


def _release(pointer: ctypes.c_void_p) -> None:
    if pointer and pointer.value:
        table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[_RELEASE])(pointer)


def _check(result: int, what: str) -> None:
    if result < 0:
        raise MediaFoundationError(f"Windows could not {what} (error 0x{result & 0xFFFFFFFF:08X}).")


class MediaFoundationReader:
    """One recording, read by Windows as float samples at its own rate.

    Use as a context manager on the thread that reads it: Media Foundation and
    COM are started on entry and shut down on exit. :attr:`rate`,
    :attr:`channels` and :attr:`duration` are known once it is open;
    :meth:`blocks` yields ``(frames, channels)`` float32 arrays.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._reader = ctypes.c_void_p()
        self._com = False
        self._started = False
        self.rate = 0
        self.channels = 0
        self.duration = 0.0

    def __enter__(self) -> MediaFoundationReader:
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _open(self) -> None:
        ole32 = ctypes.WinDLL("ole32.dll")
        mfplat = ctypes.WinDLL("mfplat.dll")
        mfreadwrite = ctypes.WinDLL("mfreadwrite.dll")
        result = int(ole32.CoInitializeEx(None, _COINIT_MULTITHREADED))
        self._com = result >= 0  # S_OK or S_FALSE: ours to undo
        if result < 0 and result != _RPC_E_CHANGED_MODE:
            _check(result, "start its media components")
        _check(int(mfplat.MFStartup(_MF_VERSION, _MFSTARTUP_NOSOCKET)), "start Media Foundation")
        self._started = True
        mfreadwrite.MFCreateSourceReaderFromURL.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        _check(
            int(
                mfreadwrite.MFCreateSourceReaderFromURL(
                    self._path, None, ctypes.byref(self._reader)
                )
            ),
            "open the recording",
        )
        select = _method(self._reader, _READER_SET_STREAM_SELECTION, ctypes.c_ulong, ctypes.c_int)
        select(_ALL_STREAMS, 0)
        _check(select(_FIRST_AUDIO_STREAM, 1), "find any sound in the file")
        wanted = ctypes.c_void_p()
        _check(int(mfplat.MFCreateMediaType(ctypes.byref(wanted))), "prepare to decode")
        try:
            set_guid = _method(wanted, _ATTR_SET_GUID, ctypes.c_void_p, ctypes.c_void_p)
            set_guid(ctypes.byref(_MT_MAJOR_TYPE), ctypes.byref(_MEDIATYPE_AUDIO))
            set_guid(ctypes.byref(_MT_SUBTYPE), ctypes.byref(_AUDIOFORMAT_FLOAT))
            set_type = _method(
                self._reader,
                _READER_SET_CURRENT_MEDIA_TYPE,
                ctypes.c_ulong,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )
            _check(set_type(_FIRST_AUDIO_STREAM, None, wanted), "decode this kind of sound")
        finally:
            _release(wanted)
        self._read_format()
        self.duration = self._read_duration()

    def _read_format(self) -> None:
        current = ctypes.c_void_p()
        get_type = _method(
            self._reader,
            _READER_GET_CURRENT_MEDIA_TYPE,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_void_p),
        )
        _check(get_type(_FIRST_AUDIO_STREAM, ctypes.byref(current)), "read the sound's format")
        try:
            get_uint32 = _method(
                current, _ATTR_GET_UINT32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)
            )
            value = ctypes.c_uint32()
            _check(
                get_uint32(ctypes.byref(_MT_AUDIO_NUM_CHANNELS), ctypes.byref(value)),
                "count the channels",
            )
            self.channels = int(value.value) or 1
            _check(
                get_uint32(ctypes.byref(_MT_AUDIO_SAMPLES_PER_SECOND), ctypes.byref(value)),
                "read the sample rate",
            )
            self.rate = int(value.value)
        finally:
            _release(current)

    def _read_duration(self) -> float:
        variant = _PropVariant()
        get_attribute = _method(
            self._reader,
            _READER_GET_PRESENTATION_ATTRIBUTE,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        if get_attribute(_MEDIA_SOURCE, ctypes.byref(_PD_DURATION), ctypes.byref(variant)) < 0:
            return 0.0
        return float(variant.value) / 10_000_000  # 100-nanosecond units

    def blocks(self) -> Iterator[Any]:
        """The recording, decoded: ``(frames, channels)`` float32 arrays."""
        import numpy as np

        read = _method(
            self._reader,
            _READER_READ_SAMPLE,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_longlong),
            ctypes.POINTER(ctypes.c_void_p),
        )
        while True:
            actual, flags = ctypes.c_ulong(), ctypes.c_ulong()
            stamp, sample = ctypes.c_longlong(), ctypes.c_void_p()
            _check(
                read(
                    _FIRST_AUDIO_STREAM,
                    0,
                    ctypes.byref(actual),
                    ctypes.byref(flags),
                    ctypes.byref(stamp),
                    ctypes.byref(sample),
                ),
                "decode the recording",
            )
            if flags.value & _READERF_ERROR:
                raise MediaFoundationError("Windows stopped part way through the recording.")
            if flags.value & _READERF_CURRENTMEDIATYPECHANGED:
                self._read_format()
            if sample.value:
                try:
                    data = self._sample_bytes(sample)
                finally:
                    _release(sample)
                if data:
                    frames = np.frombuffer(data, dtype=np.float32)
                    usable = frames.size - frames.size % self.channels
                    yield frames[:usable].reshape(-1, self.channels)
            if flags.value & _READERF_ENDOFSTREAM:
                return

    @staticmethod
    def _sample_bytes(sample: ctypes.c_void_p) -> bytes:
        buffer = ctypes.c_void_p()
        convert = _method(sample, _SAMPLE_CONVERT_TO_CONTIGUOUS, ctypes.POINTER(ctypes.c_void_p))
        _check(convert(ctypes.byref(buffer)), "read decoded sound")
        try:
            data = ctypes.POINTER(ctypes.c_ubyte)()
            most, length = ctypes.c_ulong(), ctypes.c_ulong()
            lock = _method(
                buffer,
                _BUFFER_LOCK,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_ulong),
            )
            _check(
                lock(ctypes.byref(data), ctypes.byref(most), ctypes.byref(length)),
                "read decoded sound",
            )
            try:
                return ctypes.string_at(data, length.value)
            finally:
                _method(buffer, _BUFFER_UNLOCK)()
        finally:
            _release(buffer)

    def close(self) -> None:
        """Let go of the file, Media Foundation and COM. Idempotent."""
        _release(self._reader)
        self._reader = ctypes.c_void_p()
        if self._started:
            self._started = False
            try:
                ctypes.WinDLL("mfplat.dll").MFShutdown()
            except OSError:
                pass
        if self._com:
            self._com = False
            try:
                ctypes.WinDLL("ole32.dll").CoUninitialize()
            except OSError:
                pass
