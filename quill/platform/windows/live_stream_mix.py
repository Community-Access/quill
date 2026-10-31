"""The live stream's mixer and its two writers (Studio PRD MX-186 and BCAST-026).

**Nothing waits on anything else.** Capture threads push into one queue per
source; the mixing thread sums a 20 ms block and *puts* it, without waiting,
into two bounded writer queues, one for the stream encoder and one for the
saved copy. Each writer has its own thread, so a slow network ingest can stall
only the stream's writer: the mix and the saved copy keep going. When the
stream's queue is full, the oldest stream audio is dropped -- only there --
counted, and said once.

**Priming.** A source's queue fills to 100 ms before the mixer reads it, and
again after it runs dry, so a source whose packets arrive in bursts (loopback
polled every 10 ms against 20 ms blocks) is not zero-filled into tiny gaps,
which are heard as a change in pitch. A source that ran dry and came back
within a second is counted as a gap; one that simply went quiet is not.

**Latency trim.** A source that runs ahead (its clock is faster than the
mix's) would otherwise drift to seconds of delay before anything dropped.
When a queue passes 300 ms it is trimmed back to the 100 ms target, and the
trim is counted.

**The clock (a choice, and why).** The mix is paced by the performance
counter, and that timer is *corrected against the samples one source actually
delivers*: the reference source, the microphone when one is in the stream.
Clocking purely from received audio is not possible here, because WASAPI
loopback delivers no packets at all while nothing is playing -- a mix clocked
by loopback would stop whenever the room went quiet. A bare timer, on the
other hand, is a second clock that drifts against the sound card. So the
timer's period is nudged (at most half a percent) to hold the reference
queue at its target depth, which makes the mix run at the microphone's own
rate; every other source is held in line by priming and the trim.

The lessons are Tony Gebhard's, from TG Drop Deck (``streamout.py`` and
``mixer.py``); the code is QUILL's own.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

RATE = 48_000
BLOCK = 960  # frames in 20 ms
CHANNELS = 2
#: Interleaved samples a source's queue holds before it is read (100 ms).
PRIME = RATE * CHANNELS // 10
#: A queue deeper than this (300 ms) is running ahead and is trimmed to PRIME.
TRIM_ABOVE = PRIME * 3
#: A source that comes back within this long of running dry had a gap.
GAP_WINDOW = 1.0
#: The most the reference source may speed up or slow down the mix.
MAX_STEER = 0.005


class _Source:
    __slots__ = ("chunks", "size", "primed", "dry_at", "gaps", "trims", "trimmed")

    def __init__(self) -> None:
        self.chunks: deque[Any] = deque()
        self.size = 0  # interleaved samples queued
        self.primed = False
        self.dry_at: float | None = None
        self.gaps = 0
        self.trims = 0
        self.trimmed = 0  # interleaved samples trimmed


class StreamMixer:
    """Sum the stream's sources, at their levels, into one stereo PCM stream."""

    def __init__(
        self,
        levels: dict[str, float],
        outputs: list[Callable[[bytes], None]],
        *,
        reference: str = "",
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        import numpy as np

        self._np = np
        self.gains = {key: 10 ** (db / 20) for key, db in levels.items()}
        self.outputs = outputs
        self.sources = {key: _Source() for key in levels}
        self.reference = reference if reference in self.sources else ""
        self.public_muted = False
        self._clock = clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="stream-mixer")
        self.blocks = 0

    # -- counts for the status line --------------------------------------------------

    @property
    def gaps(self) -> int:
        return sum(source.gaps for source in self.sources.values())

    @property
    def trims(self) -> int:
        return sum(source.trims for source in self.sources.values())

    # -- capture side ----------------------------------------------------------------

    def push(self, source_id: str, payload: bytes, channels: int) -> None:
        np = self._np
        samples = np.frombuffer(payload, dtype=np.int16).astype(np.float32)
        if channels == 1:
            samples = np.repeat(samples, 2)
        with self._lock:
            source = self.sources.get(source_id)
            if source is None:
                return
            if source.dry_at is not None:
                if self._clock() - source.dry_at < GAP_WINDOW:
                    source.gaps += 1
                source.dry_at = None
            source.chunks.append(samples)
            source.size += len(samples)
            if source.size > TRIM_ABOVE:
                self._trim(source, source.size - PRIME)

    def _trim(self, source: _Source, excess: int) -> None:
        """Drop *excess* of the oldest samples (kept whole frames)."""
        excess -= excess % CHANNELS
        source.trims += 1
        source.trimmed += excess
        while excess > 0 and source.chunks:
            chunk = source.chunks[0]
            if len(chunk) <= excess:
                source.chunks.popleft()
                excess -= len(chunk)
                source.size -= len(chunk)
            else:
                source.chunks[0] = chunk[excess:]
                source.size -= excess
                excess = 0

    # -- mix side --------------------------------------------------------------------

    def _take(self, source: _Source, count: int) -> Any:
        np = self._np
        out = np.zeros(count, dtype=np.float32)
        if not source.primed:
            if source.size < PRIME:
                return out  # still filling: silence, not a gap
            source.primed = True
        filled = 0
        while filled < count and source.chunks:
            chunk = source.chunks[0]
            take = min(count - filled, len(chunk))
            out[filled : filled + take] = chunk[:take]
            filled += take
            if take == len(chunk):
                source.chunks.popleft()
            else:
                source.chunks[0] = chunk[take:]
        source.size -= filled
        if source.size <= 0:
            # Ran dry: fill again before reading, and count it if it comes back soon.
            source.size = 0
            source.primed = False
            source.dry_at = self._clock()
        return out

    def mix_block(self) -> bytes:
        np = self._np
        count = BLOCK * CHANNELS
        total = np.zeros(count, dtype=np.float32)
        with self._lock:
            for source_id, gain in self.gains.items():
                total += self._take(self.sources[source_id], count) * gain
        if self.public_muted:
            total[:] = 0
        return np.clip(total, -32768, 32767).astype(np.int16).tobytes()

    def period(self) -> float:
        """The next block's length in seconds, steered by the reference source."""
        nominal = BLOCK / RATE
        source = self.sources.get(self.reference) if self.reference else None
        if source is None or not source.primed:
            return nominal
        # Deeper than the target: the reference runs fast, so mix a little faster.
        error = (source.size - PRIME) / (RATE * CHANNELS)  # seconds
        steer = max(-MAX_STEER, min(MAX_STEER, error * 0.05))
        return nominal * (1.0 - steer)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        next_at = self._clock()
        while not self._stop.is_set():
            block = self.mix_block()
            for output in list(self.outputs):
                try:
                    output(block)  # a writer's put: never blocks
                except Exception:  # noqa: BLE001 - one broken output never stops the others
                    logger.debug("Stream output failed", exc_info=True)
            self.blocks += 1
            next_at += self.period()
            delay = next_at - self._clock()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.5:
                next_at = self._clock()  # the machine stalled; do not race to catch up

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(2)


class BlockWriter:
    """A bounded queue and its own thread in front of one blocking sink.

    ``put`` never waits. When the queue is full the oldest block is dropped
    and counted, and ``on_overflow`` is called once. ``on_lag`` is called once
    when the backlog first passes ``lag_after`` seconds, because a slow link
    makes listeners late long before it loses any audio.
    """

    def __init__(
        self,
        name: str,
        sink: Callable[[bytes], None],
        *,
        capacity: int,
        on_overflow: Callable[[], None] | None = None,
        lag_after: float = 0.0,
        on_lag: Callable[[float], None] | None = None,
        block_seconds: float = BLOCK / RATE,
    ) -> None:
        self.name = name
        self.sink = sink
        self.capacity = capacity
        self.on_overflow = on_overflow
        self.lag_after = lag_after
        self.on_lag = on_lag
        self.block_seconds = block_seconds
        self.dropped = 0
        self.written = 0
        self._queue: deque[bytes] = deque()
        self._ready = threading.Condition()
        self._closing = False
        self._discard = False
        self._overflow_said = False
        self._lag_said = False
        self._thread = threading.Thread(target=self._run, daemon=True, name=name)
        self._thread.start()

    @property
    def backlog_seconds(self) -> float:
        return len(self._queue) * self.block_seconds

    def put(self, block: bytes) -> None:
        overflow = lag = False
        with self._ready:
            if self._closing:
                return
            if len(self._queue) >= self.capacity:
                self._queue.popleft()
                self.dropped += 1
                overflow = not self._overflow_said
                self._overflow_said = True
            self._queue.append(block)
            backlog = len(self._queue) * self.block_seconds
            if self.lag_after and backlog >= self.lag_after and not self._lag_said:
                self._lag_said = lag = True
            self._ready.notify()
        if overflow and self.on_overflow is not None:
            self.on_overflow()
        if lag and self.on_lag is not None:
            self.on_lag(backlog)

    def clear(self) -> None:
        """Throw away the backlog, as when the connection it was for has gone."""
        with self._ready:
            self._queue.clear()

    def _run(self) -> None:
        while True:
            with self._ready:
                while not self._queue and not self._closing:
                    self._ready.wait()
                if self._discard or (self._closing and not self._queue):
                    return
                block = self._queue.popleft()
            try:
                self.sink(block)
                self.written += 1
            except Exception:  # noqa: BLE001 - a dead pipe is the connection's problem, not ours
                logger.debug("%s could not write", self.name, exc_info=True)

    def close(self, *, drain: bool, timeout: float) -> bool:
        """Stop taking blocks; ``True`` when the thread finished within *timeout*."""
        with self._ready:
            self._closing = True
            self._discard = not drain
            self._ready.notify()
        self._thread.join(timeout)
        return not self._thread.is_alive()
