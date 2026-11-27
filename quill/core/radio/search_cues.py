"""Sounds and words while Find Streams works: the pure half.

Three ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift,
MIT), written in QUILL's own code:

* **A different sound when a search finds nothing, and another when it cannot
  finish.** An empty list and a failed search used to sound the same (nothing).
  Now each has its own cue, so a listener who has stopped listening for words
  still knows which it was.
* **A gentle cue every two seconds during a long scan**, so a quiet screen
  reader does not read as a frozen program. It stops the moment the scan ends.
* **The name a stream reports while it is checked.** Links are checked a few at a
  time; as each stream says its name (its ``icy-name``) the status line shows
  it, and it is spoken, but at most once every :data:`SPEAK_GAP_SECONDS`, so a
  scan of fifty links is not fifty sentences. The names are shown, not spoken,
  in between.

One switch, **Play sounds while Find Streams searches** (Preferences), turns the
three cues off. It does not touch the words: an outcome is always said. The
global per-event list in Sound Scheme still applies on top, as it does to every
cue.

wx-free, network-free, strict-typed; the clock is injected so the rate limit is
testable without waiting.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from quill.core.sound_events import SoundEvent

__all__ = [
    "CUE_INTERVAL_MS",
    "SPEAK_GAP_SECONDS",
    "TitleAnnouncer",
    "checking_sentence",
    "outcome_cue",
]

#: The working cue repeats at this interval while a scan runs.
CUE_INTERVAL_MS = 2000
#: A reported name is spoken at most this often; every one is shown.
SPEAK_GAP_SECONDS = 2.0
_MAX_NAME = 80


def checking_sentence(name: str) -> str:
    """ "Checking KEXP." -- the status line and the spoken sentence."""
    text = " ".join(name.split())
    if len(text) > _MAX_NAME:
        text = text[: _MAX_NAME - 1].rstrip() + "…"
    return f"Checking {text}."


def outcome_cue(*, failed: bool, found: int, enabled: bool) -> str:
    """The cue that goes with how a scan ended, or ``""`` for none.

    A scan that found streams gets no new cue: the list itself, focused, is the
    answer, and the list-filled sentence is what the listener came for.
    """
    if not enabled:
        return ""
    if failed:
        return str(SoundEvent.RADIO_SEARCH_FAILED)
    if found == 0:
        return str(SoundEvent.RADIO_SEARCH_EMPTY)
    return ""


class TitleAnnouncer:
    """Decides which reported names are spoken: the first, then one per gap."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._last_spoken = -1e9
        self._seen: set[str] = set()

    def reset(self) -> None:
        self._last_spoken = -1e9
        self._seen.clear()

    def report(self, name: str) -> tuple[str, bool]:
        """``(sentence, speak)`` for a name a stream just reported, or ``("", False)``.

        A name already shown this scan is not shown again (two mirrors of one
        station report the same name), and a blank one is ignored.
        """
        text = " ".join(name.split())
        key = text.casefold()
        if not text or key in self._seen:
            return "", False
        self._seen.add(key)
        now = self._clock()
        speak = now - self._last_spoken >= SPEAK_GAP_SECONDS
        if speak:
            self._last_spoken = now
        return checking_sentence(text), speak
