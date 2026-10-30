"""Hear one program's audio and nothing else: Windows process loopback capture.

Windows 10 2004 and later can capture the sound a single process tree plays
(``ActivateAudioInterfaceAsync`` on ``VAD\\Process_Loopback`` with
``AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK``). QUILL uses it to know,
to within a tenth of a second, when the screen reader is talking, so dictation
can stop listening to the microphone while it does
(:mod:`quill.core.windows_dictation.reader_gate`). Measured on JAWS
2026-10-12: silence reads 1, speech 2,000-8,800 RMS.

The sources are the screen readers -- JAWS (``jfw.exe``, whose voice runs in
the ``fsSynth32.exe`` it starts, so the tree is captured), NVDA and Narrator --
and QUILL itself, for its own tones and self-voiced read-back. A scan every few
seconds starts a capture for a reader that has just started and drops one that
has quit. Each capture is its own thread in the multithreaded apartment,
because the activation completes on a Windows worker thread.

Never raises into the app: a capture that cannot start is logged once and left
out, and the gate simply hears everything, as before. Windows-only.
"""

from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from ctypes import (
    HRESULT,
    POINTER,
    Structure,
    byref,
    c_int64,
    c_uint32,
    c_uint64,
    c_void_p,
    wintypes,
)
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["READER_PROCESSES", "PcmLoopback", "start_reader_capture"]

#: Executables whose sound means "the screen reader is talking", lower-case.
READER_PROCESSES = frozenset({"jfw.exe", "nvda.exe", "narrator.exe"})
_SCAN_S = 5.0
_POLL_S = 0.01
_RATE = 16_000
_LOOPBACK_PATH = "VAD\\Process_Loopback"
_PROCESS_LOOPBACK = 1  # AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK
_INCLUDE_TREE = 0  # PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE
_EXCLUDE_TREE = 1  # PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE
_VT_BLOB = 65
_LOOPBACK_FLAGS = 0x00020000 | 0x80000000 | 0x08000000  # loopback, auto-convert, SRC quality
_SILENT_FLAG = 0x2  # AUDCLNT_BUFFERFLAGS_SILENT


class _WAVEFORMATEX(Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class _ACTIVATION_PARAMS(Structure):
    _fields_ = [("type", wintypes.DWORD), ("pid", wintypes.DWORD), ("mode", wintypes.DWORD)]


class _BLOB(Structure):
    _fields_ = [("cb", wintypes.ULONG), ("data", c_void_p)]


class _PROPVARIANT(Structure):
    _fields_ = [
        ("vt", wintypes.WORD),
        ("r1", wintypes.WORD),
        ("r2", wintypes.WORD),
        ("r3", wintypes.WORD),
        ("blob", _BLOB),
        ("pad", c_uint64),
    ]


def _interfaces() -> dict[str, Any]:
    """The COM interfaces, built on first use so importing this costs nothing."""
    from comtypes import COMMETHOD, GUID, COMObject, IUnknown

    class IActivateAudioInterfaceAsyncOperation(IUnknown):
        _iid_ = GUID("{72A22D78-CDE4-431D-B8CC-843A71199B6D}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "GetActivateResult",
                (["out"], POINTER(HRESULT), "result"),
                (["out"], POINTER(POINTER(IUnknown)), "interface"),
            )
        ]

    class IActivateAudioInterfaceCompletionHandler(IUnknown):
        _iid_ = GUID("{41D949AB-9862-444A-80F6-C261334DA5EB}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "ActivateCompleted",
                (["in"], POINTER(IActivateAudioInterfaceAsyncOperation), "operation"),
            )
        ]

    class IAgileObject(IUnknown):
        _iid_ = GUID("{94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90}")
        _methods_: list[Any] = []

    class IAudioCaptureClient(IUnknown):
        _iid_ = GUID("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "GetBuffer",
                (["out"], POINTER(POINTER(ctypes.c_ubyte)), "data"),
                (["out"], POINTER(c_uint32), "frames"),
                (["out"], POINTER(wintypes.DWORD), "flags"),
                (["out"], POINTER(c_uint64), "position"),
                (["out"], POINTER(c_uint64), "counter"),
            ),
            COMMETHOD([], HRESULT, "ReleaseBuffer", (["in"], c_uint32, "frames")),
            COMMETHOD([], HRESULT, "GetNextPacketSize", (["out"], POINTER(c_uint32), "frames")),
        ]

    class IAudioClient(IUnknown):
        _iid_ = GUID("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "Initialize",
                (["in"], ctypes.c_int, "mode"),
                (["in"], wintypes.DWORD, "flags"),
                (["in"], c_int64, "buffer"),
                (["in"], c_int64, "period"),
                (["in"], POINTER(_WAVEFORMATEX), "format"),
                (["in"], POINTER(GUID), "session"),
            ),
            COMMETHOD([], HRESULT, "GetBufferSize", (["out"], POINTER(c_uint32), "n")),
            COMMETHOD([], HRESULT, "GetStreamLatency", (["out"], POINTER(c_int64), "n")),
            COMMETHOD([], HRESULT, "GetCurrentPadding", (["out"], POINTER(c_uint32), "n")),
            COMMETHOD(
                [],
                HRESULT,
                "IsFormatSupported",
                (["in"], ctypes.c_int, "mode"),
                (["in"], POINTER(_WAVEFORMATEX), "format"),
                (["out"], POINTER(POINTER(_WAVEFORMATEX)), "closest"),
            ),
            COMMETHOD([], HRESULT, "GetMixFormat", (["out"], POINTER(POINTER(_WAVEFORMATEX)), "f")),
            COMMETHOD(
                [],
                HRESULT,
                "GetDevicePeriod",
                (["out"], POINTER(c_int64), "default"),
                (["out"], POINTER(c_int64), "minimum"),
            ),
            COMMETHOD([], HRESULT, "Start"),
            COMMETHOD([], HRESULT, "Stop"),
            COMMETHOD([], HRESULT, "Reset"),
            COMMETHOD([], HRESULT, "SetEventHandle", (["in"], c_void_p, "event")),
            COMMETHOD(
                [],
                HRESULT,
                "GetService",
                (["in"], POINTER(GUID), "iid"),
                (["out"], POINTER(c_void_p), "service"),
            ),
        ]

    class CompletionHandler(COMObject):  # type: ignore[misc]
        _com_interfaces_ = [IActivateAudioInterfaceCompletionHandler, IAgileObject]

        def __init__(self) -> None:
            super().__init__()
            self.done = threading.Event()

        def ActivateCompleted(self, _operation: Any) -> int:  # noqa: N802 - COM name
            self.done.set()
            return 0

    return {
        "operation": IActivateAudioInterfaceAsyncOperation,
        "handler_iface": IActivateAudioInterfaceCompletionHandler,
        "capture": IAudioCaptureClient,
        "client": IAudioClient,
        "handler": CompletionHandler,
    }


def _open(
    pid: int, *, exclude: bool = False, rate: int = _RATE, channels: int = 1
) -> tuple[Any, Any]:
    """An audio client capturing *pid*'s tree, started, and its capture client.

    *exclude* captures everything the system plays **except** that tree --
    how Studio records "system sound without the screen reader".
    """
    com = _interfaces()
    params = _ACTIVATION_PARAMS(_PROCESS_LOOPBACK, pid, _EXCLUDE_TREE if exclude else _INCLUDE_TREE)
    variant = _PROPVARIANT(
        vt=_VT_BLOB, blob=_BLOB(ctypes.sizeof(params), ctypes.cast(byref(params), c_void_p))
    )
    handler = com["handler"]()
    operation = POINTER(com["operation"])()
    activate = ctypes.windll.mmdevapi.ActivateAudioInterfaceAsync
    activate.argtypes = [
        wintypes.LPCWSTR,
        c_void_p,
        POINTER(_PROPVARIANT),
        c_void_p,
        POINTER(POINTER(com["operation"])),
    ]
    activate.restype = HRESULT
    sink = handler.QueryInterface(com["handler_iface"])
    activate(
        _LOOPBACK_PATH,
        byref(com["client"]._iid_),
        byref(variant),
        ctypes.cast(sink, c_void_p),
        byref(operation),
    )
    if not handler.done.wait(5.0):
        raise TimeoutError("process loopback activation did not complete")
    result, unknown = operation.GetActivateResult()
    if result != 0:
        raise OSError(f"process loopback activation failed: {result & 0xFFFFFFFF:#x}")
    client = unknown.QueryInterface(com["client"])
    block = channels * 2
    fmt = _WAVEFORMATEX(1, channels, rate, rate * block, block, 16, 0)
    client.Initialize(0, _LOOPBACK_FLAGS, 2_000_000, 0, byref(fmt), None)
    capture = ctypes.cast(client.GetService(byref(com["capture"]._iid_)), POINTER(com["capture"]))
    client.Start()
    return client, capture


def _rms(data: Any, frames: int) -> float:
    import numpy as np

    samples = np.frombuffer(ctypes.string_at(data, frames * 2), dtype=np.int16)
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) if frames else 0.0


def _capture(pid: int, name: str, gate: Any, stop: threading.Event) -> None:
    """One source, until it quits or *stop* is set. Its own MTA thread."""
    import comtypes

    try:
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
    except OSError:
        pass  # already initialised on this thread
    try:
        client, capture = _open(pid)
    except Exception as exc:  # noqa: BLE001 - a source we cannot hear is left out
        logger.info("Not capturing %s (pid %d) for the dictation gate: %s", name, pid, exc)
        return
    logger.info("Capturing %s (pid %d) so dictation does not hear it", name, pid)
    gate.active = True
    if name in READER_PROCESSES:
        gate.readers.add(name)
    try:
        while not stop.is_set():
            frames_waiting = capture.GetNextPacketSize()
            while frames_waiting:
                data, frames, flags, _position, _counter = capture.GetBuffer()
                if frames and not flags & _SILENT_FLAG:
                    gate.heard(_rms(data, frames))
                capture.ReleaseBuffer(frames)
                frames_waiting = capture.GetNextPacketSize()
            time.sleep(_POLL_S)
    except Exception as exc:  # noqa: BLE001 - the source went away
        logger.info("Stopped capturing %s (pid %d): %s", name, pid, exc)
    finally:
        gate.readers.discard(name)
        try:
            client.Stop()
        except Exception:  # noqa: BLE001
            pass


def _sources() -> dict[int, str]:
    """Running screen readers by pid, plus this process."""
    import psutil

    found = {os.getpid(): "QUILL"}
    for process in psutil.process_iter(["pid", "name"]):
        name = str(process.info.get("name") or "").lower()
        if name in READER_PROCESSES:
            found[int(process.info["pid"])] = name
    return found


def start_reader_capture(gate: Any) -> threading.Thread:
    """Watch for screen readers and capture each one into *gate*. Daemon thread."""

    def scan() -> None:
        running: dict[int, threading.Event] = {}
        while True:
            try:
                current = _sources()
            except Exception:  # noqa: BLE001 - try again next time round
                current = {}
            for pid, stop in list(running.items()):
                if pid not in current:
                    stop.set()
                    del running[pid]
            for pid, name in current.items():
                if pid not in running:
                    stop = threading.Event()
                    running[pid] = stop
                    threading.Thread(
                        target=_capture,
                        args=(pid, name, gate, stop),
                        name=f"reader-capture-{name}",
                        daemon=True,
                    ).start()
            time.sleep(_SCAN_S)

    thread = threading.Thread(target=scan, name="reader-capture-scan", daemon=True)
    thread.start()
    return thread


class PcmLoopback:
    """Timestamped 16-bit PCM from one process tree, for recording.

    Studio's demonstration recorder uses this beside the dictation gate, which
    is unchanged: the gate keeps its 16 kHz mono loudness capture above. This
    opens 48 kHz stereo and hands each packet, with the wall time its first
    sample was captured, to *sink* on the calling thread. Run :meth:`run` on
    a thread of its own; :meth:`stop` ends it. *exclude* inverts the capture
    (everything except that tree). Silent packets are delivered as zeros so a
    source's timeline never has holes.
    """

    def __init__(
        self,
        pid: int,
        sink: Any,
        *,
        exclude: bool = False,
        rate: int = 48_000,
        channels: int = 2,
    ) -> None:
        self.pid = pid
        self.sink = sink
        self.exclude = exclude
        self.rate = rate
        self.channels = channels
        self._stop = threading.Event()
        self.opened = threading.Event()
        self.error: str = ""

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        import comtypes

        try:
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        except OSError:
            pass
        try:
            client, capture = _open(
                self.pid, exclude=self.exclude, rate=self.rate, channels=self.channels
            )
        except Exception as exc:  # noqa: BLE001 - reported to the caller, never raised
            self.error = str(exc) or type(exc).__name__
            self.opened.set()
            return
        self.opened.set()
        block = self.channels * 2
        try:
            while not self._stop.is_set():
                frames_waiting = capture.GetNextPacketSize()
                while frames_waiting:
                    now = time.time()
                    data, frames, flags, _position, _counter = capture.GetBuffer()
                    if frames:
                        if flags & _SILENT_FLAG:
                            payload = bytes(frames * block)
                        else:
                            payload = ctypes.string_at(data, frames * block)
                        # The packet's first sample is *frames* old by now.
                        self.sink(payload, now - frames / self.rate)
                    capture.ReleaseBuffer(frames)
                    frames_waiting = capture.GetNextPacketSize()
                time.sleep(_POLL_S)
        except Exception as exc:  # noqa: BLE001 - the process went away
            self.error = str(exc) or type(exc).__name__
        finally:
            try:
                client.Stop()
            except Exception:  # noqa: BLE001
                pass
