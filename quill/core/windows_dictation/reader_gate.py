"""Do not hear the screen reader: when it talks, the microphone is not listened to.

A headset's microphone hears the headset. JAWS reading back what was just
dictated, NVDA announcing a menu, Narrator saying "Dictation on" -- each was
recognised as a phrase and written (reported with a Logi USB headset,
2026-10-12). The echo guard (``echo_guard.py``) catches only a repeat of what
was written; this catches the reader saying anything at all.

Windows can capture the audio of one process tree and nothing else (process
loopback, ``quill/platform/windows/process_loopback.py``). QUILL captures the
running screen reader's -- and its own, for its tones and read-back -- and
this gate keeps the moments that audio was loud. Then:

* the built-in models never hear the microphone while the gate is open: the
  audio is replaced with silence before the voice detector sees it
  (:meth:`ReaderGate.speaking`), so no phrase starts on the reader's voice;
* an engine that records the microphone itself (Windows speech recognition)
  has a phrase dropped when the reader was talking for most of it
  (:meth:`ReaderGate.mostly_reader`).

The cost is said plainly in the help: words spoken *while* the reader talks are
not heard. Wait for it to finish, or silence it with Ctrl.

Pure and wx-free: the platform side calls :meth:`ReaderGate.heard` with a
loudness, and everything here is arithmetic on a clock the caller supplies.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from collections.abc import Callable

__all__ = ["LOUD_RMS", "TAIL_S", "ReaderGate", "reader_gate", "started_gate"]

#: 16-bit RMS above which the reader is talking. Measured 2026-10-12: JAWS's
#: silence reads 1, its speech 2,000-8,800.
LOUD_RMS = 120.0
#: How long after the reader stops before the microphone is listened to again:
#: the room, the headset and the last syllable all ring a little.
TAIL_S = 0.35
#: How much of a phrase must be the reader for :meth:`ReaderGate.mostly_reader`.
_MOSTLY = 0.5
#: How far back the gate remembers.
_KEEP_S = 30.0


class ReaderGate:
    """When the screen reader (or QUILL itself) was making sound."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        #: Loud spans, oldest first, as [start, end] (end moves while it lasts).
        self._spans: deque[list[float]] = deque()
        self.active = False  # True once a source is being captured

    def heard(self, rms: float, at: float | None = None) -> None:
        """One block of the reader's audio, *rms* loud, ending at *at*."""
        if rms < LOUD_RMS:
            return
        now = self._clock() if at is None else at
        with self._lock:
            if self._spans and now - self._spans[-1][1] <= TAIL_S:
                self._spans[-1][1] = now
            else:
                self._spans.append([now, now])
            while self._spans and now - self._spans[0][1] > _KEEP_S:
                self._spans.popleft()

    def speaking(self, now: float | None = None) -> bool:
        """True while the reader is talking, or stopped less than TAIL_S ago."""
        now = self._clock() if now is None else now
        with self._lock:
            return bool(self._spans) and now - self._spans[-1][1] <= TAIL_S

    def mostly_reader(self, start: float, end: float | None = None) -> bool:
        """True when the reader was talking for most of ``[start, end]``."""
        end = self._clock() if end is None else end
        if end <= start:
            return self.speaking(end)
        with self._lock:
            covered = sum(
                max(0.0, min(end, high + TAIL_S) - max(start, low)) for low, high in self._spans
            )
        return covered / (end - start) >= _MOSTLY


_GATE: ReaderGate | None = None
_GATE_LOCK = threading.Lock()


def started_gate() -> ReaderGate | None:
    """The gate, only if a recogniser has started it; never starts capture.

    What the controller asks, so building a controller (in a test, say) never
    opens an audio capture as a side effect.
    """
    return _GATE


def reader_gate() -> ReaderGate:
    """The process's one gate, with its capture started on first use (Windows).

    Never raises: where capture cannot start, the gate stays inactive and
    dictation hears everything, exactly as before. ``QUILL_READER_GATE=0``
    switches it off the same way, so a listener can compare with and without.
    """
    global _GATE
    with _GATE_LOCK:
        if _GATE is None:
            _GATE = ReaderGate()
            if os.environ.get("QUILL_READER_GATE", "").strip() == "0":
                return _GATE  # switched off: hear everything (support and A/B tests)
            try:
                from quill.platform.windows.process_loopback import start_reader_capture

                start_reader_capture(_GATE)
            except Exception:  # noqa: BLE001 - no capture means no gate, never no dictation
                pass
        return _GATE
