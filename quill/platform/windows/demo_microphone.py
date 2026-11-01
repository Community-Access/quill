"""The Microphone source of Record a Demonstration and the live stream.

Split from :mod:`quill.platform.windows.demo_audio` (GATE-11). One thread
owns the device for the source's whole life: it enters the multithreaded COM
apartment (MX-188), opens the stream, takes each block from the real-time
callback through a queue, picks or mixes the inputs, resamples, writes, and
watches for the device going away. The callback itself only stamps and
queues a block, so nothing slow and no lock the callback shares ever runs in
it (MX-181).

- **Channels (MX-185).** Input 1, input 2, or both mixed, recorded as one
  centred channel. Both mixed is the default, so a microphone on one leg of a
  two-input interface is never a left-only demonstration.
- **Rate and API (MX-181).** The device is opened at 48 kHz, then 44.1 kHz,
  then its own default rate, and anything but 48 kHz is resampled statefully
  to 48 kHz. A device that will not open under its own Windows API is tried
  as the same device under WASAPI, then DirectSound, then MME; a fallback
  that works says which API it used, and a failure names every attempt.
- **Timing (REC-022).** Each block is placed by PortAudio's own
  ``inputBufferAdcTime`` against the monotonic clock.
- **Glitches (REC-023).** Input overflows and stalls of more than half a
  second are counted and the first of each is said. A stream that reports
  itself active but has stopped calling back for 3 s is treated as lost.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from quill.core.demo_recording import SoundSource
from quill.platform.windows.capture_health import STALL_S, one_sided
from quill.platform.windows.capture_timing import OUTPUT_RATE, StreamResampler, adc_monotonic
from quill.platform.windows.com_apartment import mta
from quill.platform.windows.demo_audio import RESCAN_S, Event, _Source
from quill.platform.windows.demo_devices import (
    Microphone,
    resolve_saved_microphone,
    same_device,
)

logger = logging.getLogger(__name__)

__all__ = ["CHANNEL_MODES", "LOST_AFTER_S", "MicrophoneSource", "pick_channels"]

#: The microphone channel choice, as saved: both mixed, input 1 or input 2.
CHANNEL_MODES = ("mix", "1", "2")
#: A stream that has not called back for this long is lost, whatever it reports.
LOST_AFTER_S = 3.0
_OPEN_RATES = (48_000, 44_100)
_API_NAMES = {
    "Windows WASAPI": "WASAPI",
    "Windows DirectSound": "DirectSound",
    "MME": "MME",
    "ASIO": "ASIO",
}


def _sd() -> Any:
    import sounddevice as sd

    return sd


def pick_channels(samples: Any, mode: str) -> Any:
    """One channel of float samples from ``(frames, inputs)`` int16, per *mode*."""
    import numpy as np

    data = np.asarray(samples)
    if data.ndim == 1 or data.shape[1] == 1:
        return data.reshape(-1).astype(np.float64)
    if mode == "1":
        return data[:, 0].astype(np.float64)
    if mode == "2":
        return data[:, 1].astype(np.float64)
    return data[:, :2].astype(np.float64).mean(axis=1)


def _rates(device: Microphone) -> list[int]:
    rates = list(_OPEN_RATES)
    own = int(round(device.default_rate or 0))
    if own > 0 and own not in rates:
        rates.append(own)
    return rates


class MicrophoneSource(_Source):
    """The chosen input device through sounddevice, on a thread of its own."""

    def __init__(self, source: SoundSource, on_event: Event) -> None:
        super().__init__(source, on_event)
        self.device: Microphone | None = None
        #: Always one centred channel (MX-185).
        self.channels = 1
        self.api = ""
        self.rate = 0
        self._inputs = 1
        self._stream: Any = None
        self._generation = 0
        self._packets: queue.SimpleQueue[tuple[int, bytes, float, bool]] = queue.SimpleQueue()
        self._requests: queue.SimpleQueue[tuple[threading.Event, dict[str, str]]] = (
            queue.SimpleQueue()
        )
        self._resampler: StreamResampler | None = None
        self._last_callback = 0.0
        self._stalled = False
        self._lost = False
        self._squares = [0.0, 0.0]
        self._balance_samples = 0

    # -- the caller's side ----------------------------------------------------------

    def open(self, timeout: float = 15.0) -> str:
        """Open the device on the source's own thread; ``""`` once open, else why not."""
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._device_loop, daemon=True, name="demo-microphone"
            )
            self._thread.start()
        done = threading.Event()
        answer: dict[str, str] = {}
        self._requests.put((done, answer))
        if not done.wait(timeout):
            return "the microphone did not open in time"
        return answer.get("error", "")

    def begin_segment(self, path: Path, channels: int = 2) -> None:
        super().begin_segment(path, channels=self.channels)

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        if thread is None or not thread.is_alive():
            self._close_stream()

    def input_balance(self) -> str:
        """The input carrying the sound, ``"1"`` or ``"2"``, when the other is silent."""
        if self._inputs < 2 or self.source.channel_mode != "mix":
            return ""
        side = one_sided(self._squares[0], self._squares[1], self._balance_samples)
        return {"left": "1", "right": "2"}.get(side, "")

    # -- the device thread ----------------------------------------------------------

    def _device_loop(self) -> None:
        with mta():
            last_try = 0.0
            while not self._stop.is_set():
                self._serve_requests()
                self._drain(0.05)
                now = time.monotonic()
                self._check_health(now)
                if self._lost and now - last_try >= RESCAN_S:
                    last_try = now
                    if self._open_now() == "":
                        self._lost = False
                        self.on_event(f"{self.label} reconnected and recording.", False)
            self._serve_requests(closing=True)
            self._close_stream()

    def _serve_requests(self, *, closing: bool = False) -> None:
        while True:
            try:
                done, answer = self._requests.get_nowait()
            except queue.Empty:
                return
            answer["error"] = "the recording was closed" if closing else self._open_now()
            done.set()

    def _open_now(self) -> str:
        try:
            sd = _sd()
            mic, note = resolve_saved_microphone(self.source.device, self.source.endpoint_id)
        except Exception as error:  # noqa: BLE001 - no audio stack is a spoken failure
            return str(error) or type(error).__name__
        if mic is None:
            return f"the microphone {self.source.device or '(default)'} is not connected"
        self.device = mic
        if mic.endpoint_id and not self.source.endpoint_id:
            # Reconnects look for this device by its identity from now on.
            self.source = replace(self.source, endpoint_id=mic.endpoint_id)
        tried: list[str] = []
        error_text = ""
        for number, candidate in enumerate(same_device(mic)):
            for rate in _rates(candidate):
                inputs = max(1, min(2, candidate.channels))
                stream = None
                try:
                    stream = self._make_stream(sd, candidate, rate, inputs)
                    stream.start()
                except Exception as error:  # noqa: BLE001 - PortAudio raises several types
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:  # noqa: BLE001
                            pass
                    api = _API_NAMES.get(candidate.host_api, candidate.host_api)
                    tried.append(f"{api} at {rate} hertz")
                    error_text = str(error) or type(error).__name__
                    logger.info("Microphone did not open: %s at %d Hz: %s", api, rate, error_text)
                    continue
                self._stream = stream
                self._inputs = inputs
                self.rate = rate
                self.api = _API_NAMES.get(candidate.host_api, candidate.host_api)
                self._resampler = (
                    StreamResampler(rate, OUTPUT_RATE, channels=1) if rate != OUTPUT_RATE else None
                )
                self._last_callback = time.monotonic()
                self._stalled = False
                if note:
                    self.on_event(note, True)
                if number or rate != OUTPUT_RATE:
                    self.on_event(f"{self.label} opened through {self.api} at {rate} hertz.", False)
                return ""
        return (
            f"the microphone {mic.name} could not be opened (tried {', '.join(tried)}): "
            f"{error_text}"
        )

    def _make_stream(self, sd: Any, device: Microphone, rate: int, inputs: int) -> Any:
        self._generation += 1
        generation = self._generation
        packets = self._packets

        def callback(data: Any, frames: int, time_info: Any, status: Any) -> None:
            # Real-time thread: stamp, queue, nothing else.
            stamp = adc_monotonic(time_info, frames=frames, rate=rate)
            self._last_callback = time.monotonic()
            overflow = bool(status and getattr(status, "input_overflow", False))
            packets.put((generation, bytes(data), stamp, overflow))

        extra = None
        if device.host_api == "Windows WASAPI":
            # Shared mode runs at the device's own rate; let Windows convert.
            extra = sd.WasapiSettings(auto_convert=True)
        return sd.RawInputStream(
            samplerate=rate,
            channels=inputs,
            dtype="int16",
            device=device.index,
            callback=callback,
            blocksize=max(1, rate // 50),
            extra_settings=extra,
        )

    def _drain(self, timeout: float) -> None:
        try:
            item = self._packets.get(timeout=timeout)
        except queue.Empty:
            return
        while True:
            generation, payload, stamp, overflow = item
            if generation == self._generation:
                self._process(payload, stamp, overflow)
            try:
                item = self._packets.get_nowait()
            except queue.Empty:
                return

    def _process(self, payload: bytes, stamp: float, overflow: bool) -> None:
        import numpy as np

        if overflow:
            self.glitches.count("overflow")
        inputs = self._inputs
        frames = len(payload) // (2 * inputs)
        if not frames:
            return
        samples = np.frombuffer(payload[: frames * 2 * inputs], dtype=np.int16).reshape(
            frames, inputs
        )
        if inputs >= 2:
            squares = samples[:, :2].astype(np.float64) ** 2
            self._squares[0] += float(squares[:, 0].sum())
            self._squares[1] += float(squares[:, 1].sum())
            self._balance_samples += frames
        mono = pick_channels(samples, self.source.channel_mode)
        if self._resampler is not None:
            out = self._resampler.process(mono.reshape(-1, 1))
        else:
            out = np.clip(np.rint(mono), -32768, 32767).astype(np.int16)
        if out.size:
            self._sink(out.tobytes(), stamp)

    def _check_health(self, now: float) -> None:
        stream = self._stream
        if stream is None or self._lost:
            return
        quiet_for = now - self._last_callback
        if quiet_for > STALL_S:
            if not self._stalled:
                self._stalled = True
                self.glitches.count("stall")
        else:
            self._stalled = False
        try:
            active = bool(stream.active)
        except Exception:  # noqa: BLE001 - a stream that cannot answer is gone
            active = False
        if active and quiet_for <= LOST_AFTER_S:
            return
        self._fail(f"{self.label} stopped: the device was disconnected or blocked.")
        self._close_stream()
        self._lost = True

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        self._generation += 1
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:  # noqa: BLE001
            pass
