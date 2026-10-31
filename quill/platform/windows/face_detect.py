"""Find faces in a camera frame with Windows' own on-device face detector.

``Windows.Media.FaceAnalysis.FaceDetector`` ships with Windows 10 and later,
runs entirely on this machine and needs no model download, so camera framing
help adds no package, no network call and no AI consent. QUILL ships no
pywinrt projection for this namespace, so it is reached through the WinRT ABI
directly: activation factories, vtable calls and a polled ``IAsyncInfo``.

Frames are 8-bit grey (``Gray8``), which the detector supports natively and
the camera pipeline already produces for this purpose. One
:class:`FaceDetector` belongs to one thread (it initialises the Windows
Runtime in the multithreaded apartment there); create it on the worker that
feeds it. Windows-only.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import POINTER, Structure, byref, c_int32, c_uint32, c_void_p, wintypes
from typing import Any

from quill.core.error_codes import CodedError

__all__ = ["FaceDetectionError", "FaceDetector"]

_GRAY8 = 62  # BitmapPixelFormat.Gray8
_WRITE = 2  # BitmapBufferAccessMode.Write
_STARTED = 0
_COMPLETED = 1
_TIMEOUT_S = 5.0


class FaceDetectionError(CodedError):
    """The Windows face detector is unavailable or failed on a frame."""

    code = "QUILL-STUDIO-FACE-UNAVAILABLE"


class _GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, text: str) -> _GUID:
        import uuid

        value = uuid.UUID(text)
        guid = cls()
        guid.Data1, guid.Data2, guid.Data3 = value.fields[0], value.fields[1], value.fields[2]
        tail = value.bytes[8:]
        for index in range(8):
            guid.Data4[index] = tail[index]
        return guid


class _BitmapBounds(Structure):
    _fields_ = [("X", c_uint32), ("Y", c_uint32), ("Width", c_uint32), ("Height", c_uint32)]


class _PlaneDescription(Structure):
    _fields_ = [
        ("StartIndex", c_int32),
        ("Width", c_int32),
        ("Height", c_int32),
        ("Stride", c_int32),
    ]


_IID_FACE_STATICS = _GUID.parse("BC042D67-9047-33F6-881B-6746C1B218B8")
_IID_BITMAP_FACTORY = _GUID.parse("C99FEB69-2D62-4D47-A6B3-4FDB6A07FDF8")
_IID_ASYNC_INFO = _GUID.parse("00000036-0000-0000-C000-000000000046")
_IID_MEMORY_BUFFER = _GUID.parse("FBC4DD2A-245B-11E4-AF98-689423260CF8")
_IID_BYTE_ACCESS = _GUID.parse("5B0D3235-4DBA-4D44-865E-8F1D0E4FD04D")
_IID_DETECTED_FACE = _GUID.parse("8200D454-66BC-34DF-9410-E89400195414")
_IID_CLOSABLE = _GUID.parse("30D5A829-7FA4-4026-83BB-D75BAE4EA99E")


def _method(pointer: c_void_p, index: int, *argtypes: Any) -> Any:
    """The COM method at vtable slot *index* of *pointer*, ready to call."""
    vtable = ctypes.cast(pointer, POINTER(POINTER(c_void_p))).contents
    prototype = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *argtypes)
    function = prototype(vtable[index])
    return lambda *args: function(pointer, *args)


def _release(pointer: c_void_p | None) -> None:
    if pointer:
        vtable = ctypes.cast(pointer, POINTER(POINTER(c_void_p))).contents
        ctypes.WINFUNCTYPE(c_uint32, c_void_p)(vtable[2])(pointer)


def _query(pointer: c_void_p, iid: _GUID) -> c_void_p:
    result = c_void_p()
    _method(pointer, 0, POINTER(_GUID), POINTER(c_void_p))(byref(iid), byref(result))
    return result


class _Runtime:
    def __init__(self) -> None:
        self.combase = ctypes.windll.combase
        self.combase.RoInitialize.argtypes = [ctypes.c_int]
        self.combase.WindowsCreateString.argtypes = [
            wintypes.LPCWSTR,
            c_uint32,
            POINTER(c_void_p),
        ]
        self.combase.WindowsDeleteString.argtypes = [c_void_p]
        self.combase.RoGetActivationFactory.argtypes = [
            c_void_p,
            POINTER(_GUID),
            POINTER(c_void_p),
        ]
        try:
            self.combase.RoInitialize(1)  # RO_INIT_MULTITHREADED
        except OSError:
            pass  # already initialised on this thread (S_FALSE or a mode change)

    def factory(self, class_name: str, iid: _GUID) -> c_void_p:
        hstring = c_void_p()
        self.combase.WindowsCreateString(class_name, len(class_name), byref(hstring))
        try:
            result = c_void_p()
            self.combase.RoGetActivationFactory(hstring, byref(iid), byref(result))
            return result
        finally:
            self.combase.WindowsDeleteString(hstring)


def _wait(operation: c_void_p) -> c_void_p:
    """Block until an ``IAsyncOperation<T>`` finishes, then return its result."""
    info = _query(operation, _IID_ASYNC_INFO)
    try:
        status = c_int32(_STARTED)
        get_status = _method(info, 7, POINTER(c_int32))
        deadline = time.monotonic() + _TIMEOUT_S
        while True:
            get_status(byref(status))
            if status.value != _STARTED:
                break
            if time.monotonic() > deadline:
                _method(info, 9)()  # Cancel
                raise FaceDetectionError("The face detector did not answer in time.")
            time.sleep(0.003)
        if status.value != _COMPLETED:
            code = c_int32(0)
            _method(info, 8, POINTER(c_int32))(byref(code))
            raise FaceDetectionError(f"The face detector failed: {code.value & 0xFFFFFFFF:#010x}")
    finally:
        _release(info)
    result = c_void_p()
    _method(operation, 8, POINTER(c_void_p))(byref(result))  # GetResults
    return result


class FaceDetector:
    """Detect faces in grey frames on the calling thread."""

    def __init__(self) -> None:
        try:
            self._runtime = _Runtime()
            statics = self._runtime.factory(
                "Windows.Media.FaceAnalysis.FaceDetector", _IID_FACE_STATICS
            )
        except OSError as error:
            raise FaceDetectionError(
                f"Windows face detection is not available on this computer: {error}"
            ) from error
        try:
            supported = ctypes.c_bool(False)
            _method(statics, 9, POINTER(ctypes.c_bool))(byref(supported))
            if not supported.value:
                raise FaceDetectionError("Windows reports face detection is not supported here.")
            operation = c_void_p()
            _method(statics, 6, POINTER(c_void_p))(byref(operation))
            try:
                self._detector = _wait(operation)
            finally:
                _release(operation)
        except OSError as error:
            raise FaceDetectionError(f"Could not start the face detector: {error}") from error
        finally:
            _release(statics)
        self._bitmaps = self._runtime.factory(
            "Windows.Graphics.Imaging.SoftwareBitmap", _IID_BITMAP_FACTORY
        )

    def close(self) -> None:
        _release(getattr(self, "_detector", None))
        _release(getattr(self, "_bitmaps", None))
        self._detector = c_void_p()
        self._bitmaps = c_void_p()

    def __enter__(self) -> FaceDetector:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _bitmap(self, pixels: bytes, width: int, height: int) -> c_void_p:
        bitmap = c_void_p()
        _method(self._bitmaps, 6, c_int32, c_int32, c_int32, POINTER(c_void_p))(
            _GRAY8, width, height, byref(bitmap)
        )
        buffer = c_void_p()
        _method(bitmap, 15, c_int32, POINTER(c_void_p))(_WRITE, byref(buffer))  # LockBuffer
        try:
            plane = _PlaneDescription()
            _method(buffer, 7, c_int32, POINTER(_PlaneDescription))(0, byref(plane))
            memory = _query(buffer, _IID_MEMORY_BUFFER)
            reference = c_void_p()
            try:
                _method(memory, 6, POINTER(c_void_p))(byref(reference))  # CreateReference
            finally:
                _release(memory)
            try:
                access = _query(reference, _IID_BYTE_ACCESS)
                try:
                    data = POINTER(ctypes.c_ubyte)()
                    capacity = c_uint32(0)
                    _method(access, 3, POINTER(POINTER(ctypes.c_ubyte)), POINTER(c_uint32))(
                        byref(data), byref(capacity)
                    )
                    base = ctypes.addressof(data.contents) + plane.StartIndex
                    for row in range(height):
                        ctypes.memmove(
                            base + row * plane.Stride,
                            pixels[row * width : (row + 1) * width],
                            width,
                        )
                finally:
                    _release(access)
                closable = _query(reference, _IID_CLOSABLE)
                _method(closable, 6)()
                _release(closable)
            finally:
                _release(reference)
        finally:
            closable = _query(buffer, _IID_CLOSABLE)
            _method(closable, 6)()
            _release(closable)
            _release(buffer)
        return bitmap

    def detect(self, pixels: bytes, width: int, height: int) -> list[tuple[int, int, int, int]]:
        """Boxes ``(x, y, width, height)`` of every face in a Gray8 frame."""
        if len(pixels) < width * height:
            raise FaceDetectionError("The camera frame is shorter than its size says.")
        if not getattr(self, "_detector", None):
            raise FaceDetectionError("The face detector is closed.")
        try:
            bitmap = self._bitmap(pixels, width, height)
            try:
                operation = c_void_p()
                _method(self._detector, 6, c_void_p, POINTER(c_void_p))(bitmap, byref(operation))
                try:
                    vector = _wait(operation)
                finally:
                    _release(operation)
            finally:
                _release(bitmap)
            try:
                size = c_uint32(0)
                _method(vector, 7, POINTER(c_uint32))(byref(size))
                boxes = []
                for index in range(size.value):
                    face = c_void_p()
                    _method(vector, 6, c_uint32, POINTER(c_void_p))(index, byref(face))
                    try:
                        bounds = _BitmapBounds()
                        _method(face, 6, POINTER(_BitmapBounds))(byref(bounds))
                        boxes.append((bounds.X, bounds.Y, bounds.Width, bounds.Height))
                    finally:
                        _release(face)
                return boxes
            finally:
                _release(vector)
        except OSError as error:
            raise FaceDetectionError(f"Face detection failed on a frame: {error}") from error
