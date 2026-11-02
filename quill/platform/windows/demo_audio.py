"""Sound sources for Record a Demonstration: each to its own timestamped WAV.

Every source -- one program's sound, the system mix (optionally without the
screen reader), the screen reader alone, a whole sound card, the microphone
-- is captured on its own thread into a 48 kHz WAV per segment. Each packet
is placed by the capture API's own position against the monotonic clock
(REC-022), mapped once per segment onto the clock the picture is stamped
with, so the finished mix aligns sources by measurement (REC-008) and a
system clock that jumps moves nothing.

A source's timeline has holes filled only where sound really stopped
arriving: Windows sends nothing from a loopback while a program is silent,
so a packet that starts well after the last one ended is preceded by the
silence between them. A device clock that runs slightly fast or slow is
*drift*, not an outage, and is never patched with silence; it is measured
instead, and :meth:`WavStream.timing` reports each source's sample count
against the monotonic span it covered, as ``drift_ratio``, for the mix to
correct.

A source that dies is filled with silence, reported once through
``on_event``, and reopened *as the same source*, never replaced by a
different one (MX-181, REC-015): a program that quits is noticed within two
seconds and found again by its executable (REC-019); an excluded screen
reader that restarts is muted at once and excluded again under its new
process (MX-184); a lost sound card is reopened by its endpoint ID
(REC-020). The microphone is :mod:`quill.platform.windows.demo_microphone`.

Windows-only at runtime; the WAV and level arithmetic is plain Python/numpy.
"""

from __future__ import annotations

import logging
import threading
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from quill.core.demo_recording import DIGITAL_SILENCE_SECONDS, SoundSource
from quill.core.demo_recording_verify import SourceLevel
from quill.platform.windows.capture_health import (
    ALIVE_POLL_S,
    EXCLUDED_POLL_S,
    GlitchCounter,
    alive,
    one_sided,
)
from quill.platform.windows.demo_devices import (  # noqa: F401 - re-exported
    Microphone,
    list_microphones,
    resolve_microphone,
)

logger = logging.getLogger(__name__)

RATE = 48_000
GAP_FILL_S = 0.05
FLUSH_S = 0.5
RESCAN_S = 3.0
Event = Callable[[str, bool], None]  # (sentence, is_failure)


class WavStream:
    """16-bit PCM to a WAV file, with silence filling real gaps in the timeline."""

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
        #: When the last packet's last sample was captured, on the same clock.
        self._last_end: float | None = None
        self.frames = 0
        #: Frames of silence written for real outages (not for drift).
        self.filled_frames = 0
        self._measured: dict[str, float] = {}
        self.muted = False
        self.peak = 0
        self._sum_squares = 0.0
        self._samples = 0
        self._channel_squares = [0.0, 0.0]
        self.nonzero = False
        self.closed = False

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
            frames = len(payload) // self.block
            if self.first_time is None:
                self.first_time = captured_at
            elif self._last_end is not None:
                # Packet against packet, not against the sample count: a device
                # clock a little off never looks like an outage.
                gap = captured_at - self._last_end
                if gap > GAP_FILL_S:
                    fill = int(gap * self.rate)
                    self._silence(fill)
                    self.filled_frames += fill
            self._last_end = captured_at + frames / self.rate
            samples = np.frombuffer(payload[: frames * self.block], dtype=np.int16)
            if samples.size:
                if np.any(samples):
                    self.nonzero = True
                peak = int(np.max(np.abs(samples.astype(np.int32))))
                self.peak = max(self.peak, peak)
                squares = samples.astype(np.float64) ** 2
                self._sum_squares += float(np.sum(squares))
                self._samples += int(samples.size)
                if self.channels == 2:
                    pairs = squares.reshape(-1, 2)
                    self._channel_squares[0] += float(pairs[:, 0].sum())
                    self._channel_squares[1] += float(pairs[:, 1].sum())
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
                self._last_end = self.first_time
            self._measure()
            if end_time is not None and self._last_end is not None:
                remaining = end_time - self._last_end
                if remaining > 0:
                    self._silence(int(remaining * self.rate))
            self._file.close()
            self._raw.close()
            self.closed = True

    def _measure(self) -> None:
        """The source's own sample count against the monotonic span it covered."""
        span = 0.0
        if self.first_time is not None and self._last_end is not None:
            span = max(0.0, self._last_end - self.first_time)
        expected = span * self.rate
        measured = self.frames
        self._measured = {
            "rate": float(self.rate),
            "measured_frames": float(measured),
            "expected_frames": round(expected, 1),
            "monotonic_seconds": round(span, 6),
            "drift_ms": round((measured - expected) / self.rate * 1000, 3),
            "drift_ratio": round(measured / expected, 9) if expected > 0 and measured else 1.0,
            "filled_frames": float(self.filled_frames),
        }

    def timing(self) -> dict[str, float]:
        """REC-022's measurement, for the session record and the report.

        ``drift_ratio`` above 1 means the source delivered more samples than
        the time it covered holds at 48 kHz (its clock runs fast), so it must
        be slowed by that factor to stay in step with the picture.
        """
        with self._lock:
            if not self._measured:
                self._measure()
            return dict(self._measured)

    def one_ear(self) -> str:
        """``"left"`` or ``"right"`` when the other channel is over 30 dB below (REC-021)."""
        if self.channels != 2:
            return ""
        return one_sided(self._channel_squares[0], self._channel_squares[1], self._samples // 2)

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


def live_pid(name: str, pid: int) -> int:
    """*pid* while it runs, else the pid now running *name*, else *pid* (MX-184)."""
    if alive(pid) or not name:
        return pid
    return find_process(name) or pid


class _Source:
    """Shared lifecycle: a WAV per segment, failure events, mute, glitch counts."""

    def __init__(self, source: SoundSource, on_event: Event) -> None:
        self.source = source
        self.on_event = on_event
        self.stream: Any = None
        self._muted = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.failed_once = False
        self.error = ""
        self.glitches = GlitchCounter(source.label, on_event)
        # Capture times are monotonic; one reading per segment maps them onto
        # the clock the picture is stamped with. Swapped whole, never in part.
        self._anchor = (time.time(), time.monotonic())

    @property
    def label(self) -> str:
        return self.source.label

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if self.stream is not None:
            self.stream.muted = muted

    def _to_wall(self, captured_monotonic: float) -> float:
        wall, mono = self._anchor
        return wall + (captured_monotonic - mono)

    def _sink(self, payload: bytes, captured_monotonic: float) -> None:
        stream = self.stream
        if stream is not None:
            stream.write(payload, self._to_wall(captured_monotonic))

    def begin_segment(self, path: Path, channels: int = 2) -> None:
        self._anchor = (time.time(), time.monotonic())
        self.stream = WavStream(path, channels=channels, start_hint=self._anchor[0])
        self.stream.muted = self._muted

    def end_segment(self, end_time: float) -> WavStream | None:
        stream, self.stream = self.stream, None
        if stream is not None:
            stream.finish(end_time)
        return stream

    def statistics(self, stream: WavStream | None) -> dict[str, float]:
        """Timing and glitch counts for one segment's session record (REC-022, REC-023)."""
        timing: dict[str, float] = stream.timing() if stream is not None else {}
        return {**timing, **{k: float(v) for k, v in self.glitches.as_dict().items()}}

    def _fail(self, sentence: str) -> None:
        if not self.failed_once:
            self.failed_once = True
        self.on_event(sentence, True)


def _render_device_name(device_id: str) -> str:
    try:
        from quill.platform.windows.audio_routing import RENDER, list_devices

        return next((d.name for d in list_devices(RENDER) if d.device_id == device_id), "")
    except Exception:  # noqa: BLE001 - the label still names it
        return ""


class LoopbackSource(_Source):
    """One process tree, the system mix less one tree, or one sound card."""

    def __init__(self, source: SoundSource, on_event: Event, *, studio_pid: int) -> None:
        super().__init__(source, on_event)
        self.studio_pid = studio_pid
        self._capture: Any = None
        self._device_name = ""

    def _target(self) -> tuple[int, bool]:
        if self.source.kind == "device":
            return (0, False)
        if self.source.kind == "system":
            # Exclude mode needs a live pid; Studio's own excludes Studio's sounds.
            return (self.source.exclude_process_id or self.studio_pid, True)
        return (self.source.process_id, False)

    def _watched_name(self) -> str:
        """The executable this source follows across restarts (MX-114)."""
        if self.source.kind == "system":
            return self.source.exclude_name if self.source.exclude_process_id else ""
        return self.source.process_name

    def _retarget(self, pid: int) -> None:
        if self.source.kind == "system":
            self.source = replace(self.source, exclude_process_id=pid)
        else:
            self.source = replace(self.source, process_id=pid)

    def open(self, timeout: float = 5.0) -> str:
        """Start capturing; ``""`` once open, else why it could not."""
        from quill.platform.windows.process_loopback import PcmLoopback

        pid, exclude = self._target()
        if self.source.kind == "device":
            if not self.source.device:
                return "no sound card was chosen"
        elif not pid:
            return f"{self.source.process_name or 'the program'} is not running"
        elif pid != self.studio_pid and not alive(pid):
            # Checked before opening: Windows would open a capture of a process
            # that is gone and record silence from it (REC-019).
            name = self._watched_name()
            found = find_process(name, avoid=self.studio_pid) if name else 0
            if not found:
                return f"{name or 'the program'} is not running"
            self._retarget(found)
            pid, exclude = self._target()
        if not exclude and pid == self.studio_pid:
            return "Studio's own sounds are never recorded"
        capture = PcmLoopback(
            pid,
            self._sink,
            exclude=exclude,
            device_id=self.source.device if self.source.kind == "device" else "",
            alive_every=EXCLUDED_POLL_S if exclude else ALIVE_POLL_S,
            on_glitch=self.glitches.count,
        )
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
        if self._stop.is_set() or not capture.started:
            return  # asked to stop, or never opened: the caller has the error
        if self.source.kind == "device":
            self._reopen_device()
            return
        name = self._watched_name()
        if self.source.kind == "system" and capture.ended == "gone":
            reader = name.removesuffix(".exe") or "the left-out program"
            self._fail(
                f"{self.label} muted: {reader} closed, so its speech is kept out until "
                "Studio finds it again."
            )
            back = f"{self.label} back, still without {reader}."
        else:
            reason = "quit" if capture.ended == "gone" else "stopped sending sound"
            self._fail(f"{self.label} stopped: {name or 'the program'} {reason}.")
            back = f"{self.label} found again and recording."
        while not self._stop.wait(RESCAN_S):
            pid, _exclude = self._target()
            if not (pid and alive(pid)):
                pid = find_process(name, avoid=self.studio_pid) if name else 0
                if not pid:
                    continue
                self._retarget(pid)
            if self.open() == "":
                self.on_event(back, False)
                return

    def _reopen_device(self) -> None:
        """A lost or changed sound card, reopened by its endpoint ID (REC-020)."""
        if not self._device_name:
            self._device_name = _render_device_name(self.source.device) or self.label
        name = self._device_name
        self._fail(f"{self.label} stopped: the sound card {name} was lost or changed.")
        while not self._stop.wait(RESCAN_S):
            if self.open() == "":
                self.on_event(f"{self.label}: {name} is back and recording.", False)
                return

    def close(self) -> None:
        self._stop.set()
        if self._capture is not None:
            self._capture.stop()


def make_source(source: SoundSource, on_event: Event, *, studio_pid: int) -> Any:
    if source.kind == "microphone":
        from quill.platform.windows.demo_microphone import MicrophoneSource

        return MicrophoneSource(source, on_event)
    return LoopbackSource(source, on_event, studio_pid=studio_pid)


@dataclass
class ProbeResult:
    error: str = ""
    digital_silence: bool = False
    quiet: bool = False
    peak_dbfs: float = -120.0
    #: REC-021: a sentence when one channel is over 30 dB below the other.
    one_ear: str = ""


def _one_ear_sentence(source: SoundSource, capture: Any, stream: WavStream) -> str:
    if source.kind == "microphone":
        side = capture.input_balance()
        if not side:
            return ""
        return (
            f"{source.label} has sound on input {side} only. It is recorded in both ears; "
            f"choose input {side} under Microphone channels to record it at full level."
        )
    side = stream.one_ear()
    return f"{source.label} is only in the {side} ear." if side else ""


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
            capture.end_segment(time.time())
            try:
                path.unlink()
            except OSError:
                pass
            return ProbeResult(error=error)
        time.sleep(seconds)
        stream = capture.end_segment(time.time())
    finally:
        capture.close()
    try:
        if stream is None:
            return ProbeResult(error="no sound arrived")
        level = stream.level(source.label)
        one_ear = _one_ear_sentence(source, capture, stream)
    finally:
        try:
            path.unlink()
        except OSError:
            pass
    if source.kind == "microphone" and level.digital_silence:
        return ProbeResult(digital_silence=True, peak_dbfs=level.peak_dbfs)
    return ProbeResult(quiet=level.peak_dbfs < -50.0, peak_dbfs=level.peak_dbfs, one_ear=one_ear)
