"""Sound sources for Record a Demonstration: each to its own timestamped WAV.

Every source -- one program's sound, the system mix (optionally without the
screen reader), the screen reader alone, the microphone -- is captured on its
own thread into a 48 kHz WAV per segment, stamped with the wall time of its
first sample, so the finished mix aligns sources by measurement (REC-008).

A source's timeline never has holes: Windows sends nothing from a loopback
while a program is silent, so a late packet is preceded by the silence it
implies, and :meth:`WavStream.finish` pads to the moment recording stopped.
A source that dies (the program quits, the microphone is unplugged) is filled
with silence, reported once through ``on_event``, and reopened *as the same
source* -- the same executable name, the same device name -- never replaced
by a different one (MX-181, REC-015).

Windows-only at runtime; the WAV and level arithmetic is plain Python/numpy.
"""

from __future__ import annotations

import logging
import threading
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.demo_recording import DIGITAL_SILENCE_SECONDS, SoundSource
from quill.core.demo_recording_verify import SourceLevel

logger = logging.getLogger(__name__)

RATE = 48_000
GAP_FILL_S = 0.05
FLUSH_S = 0.5
_MAPPERS = frozenset({"Microsoft Sound Mapper - Input", "Primary Sound Capture Driver"})
#: MME names are cut to 31 characters, and the cut can leave a trailing space.
_TRUNCATED = 30
RESCAN_S = 3.0
Event = Callable[[str, bool], None]  # (sentence, is_failure)


class WavStream:
    """16-bit PCM to a WAV file, with silence filling gaps in the timeline."""

    def __init__(
        self, path: Path, *, rate: int = RATE, channels: int = 2, start_hint: float | None = None
    ) -> None:
        self.path = path
        self.start_hint = start_hint
        self.rate = rate
        self.channels = channels
        self.block = channels * 2
        self._lock = threading.Lock()
        # The raw file is ours so it can be flushed: a crash then leaves a WAV
        # whose header matches its data up to the last flush.
        self._raw = path.open("wb")
        self._file: Any = wave.open(self._raw, "wb")
        self._flushed = 0.0
        self._file.setnchannels(channels)
        self._file.setsampwidth(2)
        self._file.setframerate(rate)
        self.first_time: float | None = None
        self.frames = 0
        self.muted = False
        self.peak = 0
        self._sum_squares = 0.0
        self._samples = 0
        self.nonzero = False
        self.closed = False

    def _expected_time(self) -> float:
        assert self.first_time is not None
        return self.first_time + self.frames / self.rate

    def _silence(self, frames: int) -> None:
        chunk = 48_000
        while frames > 0:
            count = min(chunk, frames)
            self._file.writeframes(bytes(count * self.block))
            self.frames += count
            frames -= count

    def write(self, payload: bytes, captured_at: float) -> None:
        import numpy as np

        with self._lock:
            if self.closed or not payload:
                return
            if self.first_time is None:
                self.first_time = captured_at
            else:
                gap = captured_at - self._expected_time()
                if gap > GAP_FILL_S:
                    self._silence(int(gap * self.rate))
            frames = len(payload) // self.block
            samples = np.frombuffer(payload[: frames * self.block], dtype=np.int16)
            if samples.size:
                if np.any(samples):
                    self.nonzero = True
                peak = int(np.max(np.abs(samples.astype(np.int32))))
                self.peak = max(self.peak, peak)
                self._sum_squares += float(np.sum(samples.astype(np.float64) ** 2))
                self._samples += int(samples.size)
            # writeframes (not raw) keeps the header true, so a crash leaves a readable WAV.
            self._file.writeframes(bytes(len(payload)) if self.muted else payload)
            self.frames += frames
            now = time.monotonic()
            if now - self._flushed >= FLUSH_S:
                self._raw.flush()
                self._flushed = now

    def finish(self, end_time: float | None = None) -> None:
        with self._lock:
            if self.closed:
                return
            if self.first_time is None:
                # Nothing arrived: the whole segment was silence from its start.
                self.first_time = self.start_hint if self.start_hint is not None else end_time
            if end_time is not None and self.first_time is not None:
                remaining = end_time - self._expected_time()
                if remaining > 0:
                    self._silence(int(remaining * self.rate))
            self._file.close()
            self._raw.close()
            self.closed = True

    def level(self, label: str) -> SourceLevel:
        return level_of(
            label,
            self.peak,
            self._sum_squares,
            self._samples,
            self.nonzero,
            self.frames / self.rate,
        )


def level_of(
    label: str, peak: int, sum_squares: float, samples: int, nonzero: bool, seconds: float
) -> SourceLevel:
    import math

    def dbfs(value: float) -> float:
        return 20 * math.log10(value / 32768) if value > 0 else -120.0

    rms = math.sqrt(sum_squares / samples) if samples else 0.0
    return SourceLevel(label, dbfs(peak), dbfs(rms), not nonzero, seconds)


def level_from_wav(path: Path, label: str) -> SourceLevel:
    """A WAV's own level, measured from the file (REC-014)."""
    import numpy as np

    peak, squares, count, nonzero = 0, 0.0, 0, False
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate() or RATE
        while True:
            block = handle.readframes(rate)
            if not block:
                break
            samples = np.frombuffer(block, dtype=np.int16)
            if samples.size:
                nonzero = nonzero or bool(np.any(samples))
                peak = max(peak, int(np.max(np.abs(samples.astype(np.int32)))))
                squares += float(np.sum(samples.astype(np.float64) ** 2))
                count += int(samples.size)
    return level_of(label, peak, squares, count, nonzero, frames / rate)


def find_process(name: str, *, avoid: int = 0) -> int:
    """The pid of a running *name* (case-insensitive), or 0."""
    import psutil

    wanted = name.lower()
    for process in psutil.process_iter(["pid", "name"]):
        if str(process.info.get("name") or "").lower() == wanted and process.info["pid"] != avoid:
            return int(process.info["pid"])
    return 0


@dataclass
class Microphone:
    index: int
    name: str
    host_api: str
    channels: int


def list_microphones() -> list[Microphone]:
    """Input devices, one per name, preferring WASAPI's full names over MME's."""
    import sounddevice as sd

    apis = {index: api["name"] for index, api in enumerate(sd.query_hostapis())}
    preference = {"ASIO": 0, "Windows WASAPI": 1, "MME": 2, "Windows DirectSound": 3}
    best: dict[str, Microphone] = {}
    for index, device in enumerate(sd.query_devices()):
        if int(device.get("max_input_channels", 0)) <= 0:
            continue
        api = apis.get(int(device["hostapi"]), "")
        if api not in preference:
            continue
        name = str(device["name"]).strip()
        if api == "ASIO":
            # One ASIO driver often carries the same name as its WASAPI twin.
            name = f"{name} (ASIO)"
        candidate = Microphone(index, name, api, int(device["max_input_channels"]))
        current = best.get(name)
        if current is None or preference[api] < preference[current.host_api]:
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
    return sorted(best.values(), key=lambda mic: mic.name.casefold())


def resolve_microphone(name: str) -> Microphone | None:
    """The device *name* names, never a different one (MX-181).

    An MME name truncated to 31 characters matches only when exactly one full
    name begins with it, so two headsets sharing their first 31 characters
    are never confused.
    """
    microphones = list_microphones()
    if not name:
        import sounddevice as sd

        try:
            default = int(sd.default.device[0])
        except (TypeError, ValueError, IndexError):
            return microphones[0] if microphones else None
        info = sd.query_devices(default) if default >= 0 else None
        if info is not None:
            return resolve_microphone(str(info["name"]).strip()) or (
                microphones[0] if microphones else None
            )
        return microphones[0] if microphones else None
    exact = [mic for mic in microphones if mic.name == name]
    if exact:
        return exact[0]
    prefixed = [
        mic for mic in microphones if mic.name.startswith(name) or name.startswith(mic.name)
    ]
    if len(prefixed) == 1 and min(len(name), len(prefixed[0].name)) >= _TRUNCATED:
        return prefixed[0]
    return None


class _Source:
    """Shared lifecycle: a WAV per segment, failure events, mute."""

    def __init__(self, source: SoundSource, on_event: Event) -> None:
        self.source = source
        self.on_event = on_event
        self.stream: WavStream | None = None
        self._muted = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.failed_once = False
        self.error = ""

    @property
    def label(self) -> str:
        return self.source.label

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if self.stream is not None:
            self.stream.muted = muted

    def _sink(self, payload: bytes, captured_at: float) -> None:
        stream = self.stream
        if stream is not None:
            stream.write(payload, captured_at)

    def begin_segment(self, path: Path, channels: int = 2) -> None:
        self.stream = WavStream(path, channels=channels, start_hint=time.time())
        self.stream.muted = self._muted

    def end_segment(self, end_time: float) -> WavStream | None:
        stream, self.stream = self.stream, None
        if stream is not None:
            stream.finish(end_time)
        return stream

    def _fail(self, sentence: str) -> None:
        if not self.failed_once:
            self.failed_once = True
        self.on_event(sentence, True)


class LoopbackSource(_Source):
    """One process tree, or the system mix less one tree, by process loopback."""

    def __init__(self, source: SoundSource, on_event: Event, *, studio_pid: int) -> None:
        super().__init__(source, on_event)
        self.studio_pid = studio_pid
        self._capture: Any = None

    def _target(self) -> tuple[int, bool]:
        if self.source.kind == "system":
            # Exclude mode needs a live pid; Studio's own excludes Studio's sounds.
            return (self.source.exclude_process_id or self.studio_pid, True)
        return (self.source.process_id, False)

    def open(self, timeout: float = 5.0) -> str:
        """Start capturing; ``""`` once open, else why it could not."""
        from quill.platform.windows.process_loopback import PcmLoopback

        pid, exclude = self._target()
        if not pid:
            return f"{self.source.process_name or 'the program'} is not running"
        if not exclude and pid == self.studio_pid:
            return "Studio's own sounds are never recorded"
        capture = PcmLoopback(pid, self._sink, exclude=exclude)
        self._capture = capture
        thread = threading.Thread(
            target=self._run,
            args=(capture,),
            daemon=True,
            name=f"demo-loopback-{self.source.source_id}",
        )
        self._thread = thread
        thread.start()
        if not capture.opened.wait(timeout):
            return "Windows did not open the capture in time"
        return capture.error

    def _run(self, capture: Any) -> None:
        capture.run()
        if self._stop.is_set():
            return
        # The process quit: fill with silence and look for the same program again.
        name = (
            self.source.exclude_name if self.source.kind == "system" else self.source.process_name
        )
        self._fail(f"{self.label} stopped: {name or 'the program'} quit or its sound ended.")
        while not self._stop.wait(RESCAN_S):
            pid = find_process(name, avoid=self.studio_pid) if name else 0
            if not pid:
                continue
            from dataclasses import replace

            if self.source.kind == "system":
                self.source = replace(self.source, exclude_process_id=pid)
            else:
                self.source = replace(self.source, process_id=pid)
            if self.open() == "":
                self.on_event(f"{self.label} found again and recording.", False)
            return

    def close(self) -> None:
        self._stop.set()
        if self._capture is not None:
            self._capture.stop()


class MicrophoneSource(_Source):
    """The chosen input device through sounddevice, held under the shared lock."""

    def __init__(self, source: SoundSource, on_event: Event) -> None:
        super().__init__(source, on_event)
        self._stream: Any = None
        self.device: Microphone | None = None
        self.channels = 1
        self._watch: threading.Thread | None = None

    def open(self) -> str:
        import sounddevice as sd

        device = resolve_microphone(self.source.device)
        if device is None:
            return f"the microphone {self.source.device or '(default)'} is not connected"
        self.device = device
        self.channels = max(1, min(2, device.channels))

        def callback(data: Any, frames: int, _time: Any, status: Any) -> None:
            self._sink(bytes(data), time.time() - frames / RATE)

        extra = None
        if device.host_api == "ASIO":
            self.channels = max(1, min(2, device.channels))
        elif device.host_api == "Windows WASAPI":
            # Shared mode runs at the device's own rate; let Windows convert to 48 kHz.
            extra = sd.WasapiSettings(auto_convert=True)
        try:
            stream = sd.RawInputStream(
                samplerate=RATE,
                channels=self.channels,
                dtype="int16",
                device=device.index,
                callback=callback,
                blocksize=960,
                extra_settings=extra,
            )
            stream.start()
        except Exception as error:  # noqa: BLE001 - PortAudio raises several types
            return str(error) or type(error).__name__
        self._stream = stream
        if self._watch is None:
            self._watch = threading.Thread(
                target=self._watch_device, daemon=True, name="demo-microphone-watch"
            )
            self._watch.start()
        return ""

    def begin_segment(self, path: Path, channels: int = 2) -> None:
        super().begin_segment(path, channels=self.channels)

    def _watch_device(self) -> None:
        while not self._stop.wait(1.0):
            stream = self._stream
            if stream is None or stream.active:
                continue
            self._fail(f"{self.label} stopped: the device was disconnected or blocked.")
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
            while not self._stop.wait(RESCAN_S):
                if self.open() == "":
                    self.on_event(f"{self.label} reconnected and recording.", False)
                    break

    def close(self) -> None:
        self._stop.set()
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:  # noqa: BLE001
                pass


def make_source(source: SoundSource, on_event: Event, *, studio_pid: int) -> Any:
    if source.kind == "microphone":
        return MicrophoneSource(source, on_event)
    return LoopbackSource(source, on_event, studio_pid=studio_pid)


@dataclass
class ProbeResult:
    error: str = ""
    digital_silence: bool = False
    quiet: bool = False
    peak_dbfs: float = -120.0


def probe_source(
    source: SoundSource, *, studio_pid: int, folder: Path, seconds: float = DIGITAL_SILENCE_SECONDS
) -> ProbeResult:
    """Open *source* briefly for the spoken check: can it open, is it blocked?"""
    events: list[str] = []
    capture = make_source(source, lambda text, _failure: events.append(text), studio_pid=studio_pid)
    path = folder / f"probe-{source.source_id}.wav"
    capture.begin_segment(path)
    try:
        error = capture.open()
        if error:
            return ProbeResult(error=error)
        time.sleep(seconds)
        stream = capture.end_segment(time.time())
    finally:
        capture.close()
    try:
        if stream is None:
            return ProbeResult(error="no sound arrived")
        level = stream.level(source.label)
    finally:
        try:
            path.unlink()
        except OSError:
            pass
    if source.kind == "microphone" and level.digital_silence:
        return ProbeResult(digital_silence=True, peak_dbfs=level.peak_dbfs)
    return ProbeResult(quiet=level.peak_dbfs < -50.0, peak_dbfs=level.peak_dbfs)
