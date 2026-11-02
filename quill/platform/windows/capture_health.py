"""Is a captured program still there, and is its sound still arriving whole?

Three things Windows does not say on its own, each learned the hard way by
TG Drop Deck:

- **A process-loopback capture of a process that has gone keeps running,
  silently** (and Windows activates one for a process that never existed).
  Neither raises, so a recorded program that quits, or a screen reader that
  restarts under a new process ID, is noticed only by asking whether the
  process is alive. :func:`alive` asks, with ``GetExitCodeProcess``
  (REC-019, MX-184).
- **A stream that reports itself active is not proof that sound is
  arriving.** :class:`GlitchCounter` counts discontinuities, input overflows
  and stalls of more than half a second, and says the first of each kind
  while the recording is still going, rather than as an epitaph at the end
  (REC-023).
- **A level meter cannot show that a source is in one ear.**
  :func:`one_sided` says which side carries the sound when the other is more
  than 30 dB below it (REC-021).

Adapted from TG Drop Deck, Copyright (c) 2026 Tony Gebhard, MIT licence
(https://github.com/tonygeb23/tg-drop-deck, ``dropdeck/proccapture.py``
``alive()``):

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to permit
    persons to whom the Software is furnished to do so, subject to the
    following conditions:

    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
    NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
    OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
    USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import ctypes
import logging
import math
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ALIVE_POLL_S",
    "EXCLUDED_POLL_S",
    "STALL_S",
    "GlitchCounter",
    "alive",
    "one_sided",
]

#: How often a captured program is asked whether it is still running (REC-019).
ALIVE_POLL_S = 2.0
#: An excluded screen reader is asked twice as often: until its restart is
#: noticed, the capture would carry the new process's speech (MX-184).
EXCLUDED_POLL_S = 1.0
#: No callback for this long is a stall, even while the stream says it is active.
STALL_S = 0.5
#: One channel this far below the other is "only in one ear" (REC-021).
ONE_EAR_DB = 30.0
#: Below this RMS the source is too quiet to judge its balance.
_BALANCE_FLOOR_DBFS = -60.0

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5


def _kernel32() -> Any:
    try:
        return ctypes.windll.kernel32  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None


def alive(pid: int) -> bool:
    """Whether process *pid* is still running.

    A process this account may not open (a protected or elevated one) is
    reported alive: it exists, and guessing otherwise would end a source that
    is fine. Off Windows every pid is assumed alive.
    """
    if pid <= 0:
        return False
    kernel32 = _kernel32()
    if kernel32 is None:
        return True
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return int(kernel32.GetLastError()) == _ERROR_ACCESS_DENIED
    try:
        code = ctypes.c_ulong(0)
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True
        return int(code.value) == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


_SENTENCES = {
    "discontinuity": "{label} is losing audio: Windows reported a gap in the sound.",
    "overflow": "{label} is losing audio: the input overflowed.",
    "stall": "{label} is losing audio: no sound arrived for over half a second.",
}


class GlitchCounter:
    """Counts of each kind of lost audio for one source; the first of each is said."""

    KINDS = tuple(_SENTENCES)

    def __init__(self, label: str, on_event: Callable[[str, bool], None]) -> None:
        self.label = label
        self.on_event = on_event
        self.counts = dict.fromkeys(self.KINDS, 0)
        self._lock = threading.Lock()

    def count(self, kind: str, number: int = 1) -> None:
        if number <= 0:
            return
        with self._lock:
            first = self.counts[kind] == 0
            self.counts[kind] += number
        if first:
            logger.info("%s: first %s", self.label, kind)
            self.on_event(_SENTENCES[kind].format(label=self.label), True)

    def as_dict(self) -> dict[str, int]:
        with self._lock:
            return {f"{kind}_count": value for kind, value in self.counts.items()}


def _dbfs(sum_squares: float, samples: int) -> float:
    if samples <= 0 or sum_squares <= 0:
        return -120.0
    return 20 * math.log10(math.sqrt(sum_squares / samples) / 32768)


def one_sided(left: float, right: float, samples_per_channel: int) -> str:
    """``"left"`` or ``"right"``: the only side with sound; ``""`` when balanced.

    *left* and *right* are each channel's sum of squared 16-bit samples.
    """
    left_db = _dbfs(left, samples_per_channel)
    right_db = _dbfs(right, samples_per_channel)
    if max(left_db, right_db) < _BALANCE_FLOOR_DBFS:
        return ""
    if left_db - right_db > ONE_EAR_DB:
        return "left"
    if right_db - left_db > ONE_EAR_DB:
        return "right"
    return ""
