"""Microphone capture for offline dictation (#617, Speech S3).

Records 16 kHz mono PCM-16 audio (what whisper.cpp expects) to a temporary WAV
file via the optional ``sounddevice`` (PortAudio) dependency, imported lazily so
QUILL runs fine without it. The WAV writer is pure and unit-tested; the live
capture loop is a thin wrapper around a ``sounddevice.RawInputStream``.
"""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Any

SAMPLE_RATE = 16_000
CHANNELS = 1
_SAMPLE_WIDTH = 2  # int16


class CaptureUnavailableError(RuntimeError):
    """Raised when microphone capture support is not installed."""


def capture_available() -> bool:
    """True when the optional audio-capture dependency is importable."""
    try:
        import sounddevice  # noqa: F401
    except Exception:  # noqa: BLE001 - any import/runtime error means unavailable
        return False
    return True


def list_input_devices() -> list[tuple[int, str]]:
    """Return ``(index, name)`` for each available microphone input device.

    Empty when capture support is not installed or enumeration fails — callers
    fall back to the system default device (index ``-1``).
    """
    try:
        import sounddevice
    except Exception:  # noqa: BLE001
        return []
    devices: list[tuple[int, str]] = []
    try:
        for index, info in enumerate(sounddevice.query_devices()):
            if int(info.get("max_input_channels", 0)) > 0:
                devices.append((index, str(info.get("name", f"Device {index}"))))
    except Exception:  # noqa: BLE001
        return []
    return devices


def write_wav_pcm16(
    path: Path, frames: bytes, *, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS
) -> None:
    """Write raw little-endian PCM-16 ``frames`` to a valid WAV file (pure)."""
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(_SAMPLE_WIDTH)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)


class MicRecorder:
    """Start/stop microphone recording, producing a temp WAV on stop.

    Integration component (needs sounddevice + a real microphone); all failures
    surface as :class:`CaptureUnavailableError` with a clear message.
    """

    def __init__(self) -> None:
        self._stream: object | None = None
        self._chunks: list[bytes] = []
        self._paused = False

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    @property
    def is_paused(self) -> bool:
        return self._paused

    def captured_frames(self) -> bytes:
        """A snapshot of the PCM-16 frames captured so far.

        Non-destructive: the recorder keeps accumulating. For repeated polling
        prefer :meth:`frames_since`, which does not re-join the whole recording
        on every call.
        """
        return b"".join(self._chunks)

    def frames_since(self, chunk_index: int) -> tuple[bytes, int]:
        """New PCM-16 bytes appended since ``chunk_index``, plus the next index.

        Voice conversation mode polls this to watch microphone energy: each
        poll joins only the newly arrived chunks (O(new)), where re-joining the
        whole recording per poll grew O(n^2) over a long turn (#795 review).
        """
        chunks = self._chunks[chunk_index:]
        return b"".join(chunks), chunk_index + len(chunks)

    def pause(self) -> None:
        """Stop adding microphone samples without closing the stream.

        Used by Locked Dictation's pause/resume: the device stays open (so resume
        is instant) but incoming frames are dropped while paused, so the captured
        audio simply skips the paused span.
        """
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def start(self, device_index: int | None = None) -> None:
        """Begin recording. ``device_index`` < 0 or None uses the system default."""
        if self._stream is not None:
            return
        try:
            import sounddevice
        except Exception as exc:  # noqa: BLE001
            raise CaptureUnavailableError(
                "Microphone capture support is not installed. Install the optional "
                "'sounddevice' package, or use Windows dictation instead."
            ) from exc
        self._chunks = []
        self._paused = False

        def _callback(indata: Any, _frames: int, _time: object, _status: object) -> None:
            if self._paused:
                return  # drop frames while paused (Locked Dictation pause/resume)
            self._chunks.append(bytes(indata))

        device = device_index if (device_index is not None and device_index >= 0) else None
        try:
            stream = sounddevice.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                device=device,
                callback=_callback,
            )
            stream.start()
        except Exception as exc:  # noqa: BLE001
            raise CaptureUnavailableError(f"Could not start the microphone: {exc}") from exc
        self._stream = stream

    def stop(self) -> Path:
        """Stop recording and return the path to the captured WAV file."""
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()  # type: ignore[attr-defined]
                stream.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - cleanup must not raise over the result
                pass
        frames = b"".join(self._chunks)
        self._chunks = []
        fd, raw = tempfile.mkstemp(prefix="quill-dictation-", suffix=".wav")
        import os

        os.close(fd)
        path = Path(raw)
        write_wav_pcm16(path, frames)
        return path
