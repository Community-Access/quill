"""Type-ahead buffer for custom list surfaces (hardening pass).

Native wx list controls have first-letter navigation; QUILL's custom and
virtual list surfaces need their own, and the details are exactly what ad hoc
implementations forget (the reference timings, assessment item 12):

- keystrokes still in flight from *opening* the window must not select a
  random item — suppress type-ahead for 800 ms after the surface appears;
- the multi-character buffer times out after 1.2 s (use a longer timeout for
  long names like files);
- when a multi-character buffer stops matching, retry with just the last
  character before declaring failure — the user has started a new search;
- matching wraps from the current selection so repeated presses cycle;
- total failure must be *audible*: the caller speaks "No match for X".

Pure state machine over injected timestamps: no timers, no wx, strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["TypeAheadBuffer", "TypeAheadResult", "find_match"]

OPEN_SUPPRESSION_SECONDS = 0.8
BUFFER_TIMEOUT_SECONDS = 1.2


def find_match(names: Sequence[str], query: str, start_index: int) -> int:
    """Index of the first name starting with *query*, scanning forward from
    just after *start_index* and wrapping; -1 when nothing matches.

    Wrapping from the current selection is what makes repeated presses of the
    same letter cycle through matches instead of sticking on the first.
    """
    if not names or not query:
        return -1
    folded = query.casefold()
    total = len(names)
    for offset in range(1, total + 1):
        index = (start_index + offset) % total
        if names[index].casefold().startswith(folded):
            return index
    return -1


@dataclass(frozen=True, slots=True)
class TypeAheadResult:
    """The outcome of one keystroke: where to move, or what failed."""

    index: int  # -1 = no movement
    query: str  # the buffer that produced this result
    failed: bool = False  # True: speak "No match for {query}"


class TypeAheadBuffer:
    """Accumulates typed characters and resolves them against a name list."""

    def __init__(
        self,
        *,
        buffer_timeout: float = BUFFER_TIMEOUT_SECONDS,
        open_suppression: float = OPEN_SUPPRESSION_SECONDS,
    ) -> None:
        self._buffer_timeout = buffer_timeout
        self._open_suppression = open_suppression
        self._buffer = ""
        self._last_press_at = 0.0
        self._opened_at: float | None = None

    def surface_opened(self, now: float) -> None:
        """Call when the list surface appears; starts the suppression window."""
        self._opened_at = now
        self._buffer = ""

    def press(
        self,
        character: str,
        names: Sequence[str],
        current_index: int,
        now: float,
    ) -> TypeAheadResult:
        """Feed one printable character; returns where the selection should go."""
        if self._opened_at is not None and (now - self._opened_at) < self._open_suppression:
            # A keystroke still in flight from before the window opened must
            # not land on a random item.
            return TypeAheadResult(index=-1, query="")
        if now - self._last_press_at > self._buffer_timeout:
            self._buffer = ""
        self._last_press_at = now
        self._buffer += character
        match = find_match(names, self._buffer, current_index)
        if match >= 0:
            return TypeAheadResult(index=match, query=self._buffer)
        if len(self._buffer) > 1:
            # The old buffer stopped matching: the user has started a new
            # search — retry with just the last character before failing.
            retry = character
            retry_match = find_match(names, retry, current_index)
            if retry_match >= 0:
                self._buffer = retry
                return TypeAheadResult(index=retry_match, query=retry)
        failed_query = self._buffer
        self._buffer = ""
        return TypeAheadResult(index=-1, query=failed_query, failed=True)
