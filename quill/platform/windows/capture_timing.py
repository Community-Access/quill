"""When a captured sample was heard, and turning a device's rate into 48 kHz.

**Time comes from the sound (REC-022, REC-008).** Each packet is placed by
the capture API's own position -- the performance-counter position WASAPI's
``GetBuffer`` returns, PortAudio's ``inputBufferAdcTime`` -- measured
against :func:`time.monotonic`, never :func:`time.time`. The wall clock jumps
when Windows syncs it, and a machine that stalls makes a wall-clock timeline
shorter than the sound it holds. A packet's age is how long ago the API says
its first sample was captured; ``monotonic() - age`` is then on the one clock
nothing adjusts.

**Resampling is stateful (MX-181).** A device that opens only at 44.1 kHz
(an ASIO interface, an exclusive-mode device) is converted to 48 kHz by one
:class:`StreamResampler` for the life of the stream. Resampling each block on
its own clicks at every block edge, because each block's filter starts from
silence; this keeps the filter's history between blocks. It is a windowed
sinc in numpy (no new dependency; soxr is LGPL and would need review), and it
runs on the source's own worker thread, never inside the real-time callback
and never under a lock the callback takes.
"""

from __future__ import annotations

import ctypes
import time
from typing import Any

__all__ = [
    "OUTPUT_RATE",
    "StreamResampler",
    "adc_monotonic",
    "packet_monotonic",
    "qpc_now_100ns",
]

OUTPUT_RATE = 48_000
_HALF_TAPS = 16


def qpc_now_100ns() -> int:
    """The performance counter now, in the 100-nanosecond units ``GetBuffer`` uses."""
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    counter = ctypes.c_int64(0)
    frequency = ctypes.c_int64(0)
    kernel32.QueryPerformanceCounter(ctypes.byref(counter))
    kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
    if frequency.value <= 0:
        return 0
    return counter.value * 10_000_000 // frequency.value


def packet_monotonic(
    position_100ns: int,
    *,
    frames: int,
    rate: int,
    qpc_now: int | None = None,
    now: float | None = None,
) -> float:
    """The monotonic time a WASAPI packet's first sample was captured.

    *position_100ns* is ``GetBuffer``'s performance-counter position for the
    packet's first frame. When Windows gives none (0), the packet is taken to
    have just finished arriving, which is the best that is known.
    """
    current = time.monotonic() if now is None else now
    if position_100ns > 0:
        reference = qpc_now_100ns() if qpc_now is None else qpc_now
        if reference > 0:
            age = (reference - position_100ns) / 10_000_000
            if 0.0 <= age < 5.0:
                return current - age
    return current - frames / rate


def adc_monotonic(time_info: Any, *, frames: int, rate: int, now: float | None = None) -> float:
    """The monotonic time a PortAudio input block's first sample was captured.

    ``inputBufferAdcTime`` and ``currentTime`` share the stream's own clock,
    so their difference is the block's age. Some host APIs report 0 for both;
    the block is then taken to have just finished arriving.
    """
    current = time.monotonic() if now is None else now
    try:
        adc = float(time_info.inputBufferAdcTime)
        stream_now = float(time_info.currentTime)
    except (AttributeError, TypeError, ValueError):
        adc = stream_now = 0.0
    if adc > 0 and stream_now > 0:
        age = stream_now - adc
        if 0.0 <= age < 5.0:
            return current - age
    return current - frames / rate


class StreamResampler:
    """Stateful windowed-sinc conversion from *in_rate* to *out_rate*.

    Feed it consecutive blocks of one stream (int16 or float, shape
    ``(frames, channels)``); it returns int16 at the output rate, carrying the
    filter history and the fractional read position from block to block, so
    a stream converted in pieces is the same as one converted whole.
    """

    def __init__(
        self,
        in_rate: int,
        out_rate: int = OUTPUT_RATE,
        *,
        channels: int = 1,
        half_taps: int = _HALF_TAPS,
    ) -> None:
        import numpy as np

        self.in_rate = int(in_rate)
        self.out_rate = int(out_rate)
        self.channels = channels
        self.passthrough = self.in_rate == self.out_rate
        self._step = self.in_rate / self.out_rate
        self._half = half_taps
        self._cutoff = min(1.0, self.out_rate / self.in_rate)
        self._offsets = np.arange(-half_taps + 1, half_taps + 1)
        self._buffer = np.zeros((half_taps, channels), dtype=np.float64)
        self._position = float(half_taps)

    def process(self, block: Any) -> Any:
        import numpy as np

        samples = np.asarray(block)
        if samples.ndim == 1:
            samples = samples.reshape(-1, self.channels)
        if self.passthrough:
            return samples.astype(np.int16)
        buffer = np.concatenate([self._buffer, samples.astype(np.float64)])
        last = len(buffer) - self._half - 1
        if self._position > last:
            self._buffer = buffer
            return np.zeros((0, self.channels), dtype=np.int16)
        count = int(np.floor((last - self._position) / self._step)) + 1
        positions = self._position + self._step * np.arange(count)
        base = np.floor(positions).astype(np.int64)
        fraction = positions - base
        distance = fraction[:, None] - self._offsets[None, :]
        window = (
            0.42
            + 0.5 * np.cos(np.pi * distance / self._half)
            + 0.08 * np.cos(2 * np.pi * distance / self._half)
        )
        kernel = self._cutoff * np.sinc(self._cutoff * distance) * window
        kernel /= kernel.sum(axis=1, keepdims=True)
        taps = buffer[base[:, None] + self._offsets[None, :]]
        out = np.einsum("nk,nkc->nc", kernel, taps)
        position = self._position + self._step * count
        keep = max(0, int(np.floor(position)) - self._half + 1)
        self._buffer = buffer[keep:]
        self._position = position - keep
        return np.clip(np.rint(out), -32768, 32767).astype(np.int16)
