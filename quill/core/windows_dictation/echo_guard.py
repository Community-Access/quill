"""Drop a phrase that is the screen reader repeating what dictation just wrote.

Typing echo is how a screen-reader user checks what went in: write "hello
world" into Outlook and JAWS or NVDA says "hello world" -- through the same
headset whose microphone is still open. Unless the headset cancels it, the
recogniser hears the read-back as a new phrase and writes it again, and the
read-back of *that* is heard too (reported with a Logi USB headset,
2026-10-12). QUILL's own spoken read-back makes the same loop.

So a phrase is dropped when, within :data:`ECHO_WINDOW_S` of writing, it is
mostly words dictation has just written, in order: at least :data:`_SIMILAR`
of the heard words, matched against everything written in the window. Spoken
punctuation names ("comma", "period") do not count against it, because a
reader with punctuation on says them and the recogniser hears them. A single
heard word is dropped only when it was a whole phrase on its own, so a short
word said again on purpose ("the") is never mistaken for an echo.

An echo also *starts* soon after the write: the reader begins as the text goes
in. So when the controller knows when the phrase began, it is an echo only if
it began within :data:`ECHO_START_S` of a write (or of the end of an echo just
dropped, for a long read-back the recogniser heard as two phrases). Saying the
same words again on purpose, after the reader has finished, is written -- it
was dropped for the whole eight seconds until that was reported (2026-10-12).

Pure and wx-free; the controller supplies the clock.
"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from difflib import SequenceMatcher

from quill.core.windows_dictation.readback import mark_names

__all__ = ["ECHO_START_S", "ECHO_WINDOW_S", "EchoGuard"]

#: How long after writing a phrase its echo is expected. A screen reader starts
#: within a second; a long phrase read at a slow rate takes several more.
ECHO_WINDOW_S = 8.0
#: How soon after a write (or a dropped echo) an echo begins. The reader starts
#: speaking as the text is typed; a person repeating themselves starts later.
ECHO_START_S = 1.5
_SIMILAR = 0.8
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)


def _words(text: str) -> list[str]:
    return [word.lower() for word in _WORD.findall(text)]


def _punctuation_words() -> frozenset[str]:
    names: set[str] = set()
    for language in ("en", "es"):
        for name in mark_names(language).values():
            names.update(_words(name))
    return frozenset(names)


class EchoGuard:
    """Remembers what was written lately, and recognises it coming back."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._written: deque[tuple[float, list[str]]] = deque(maxlen=12)
        self._marks = _punctuation_words()
        self._last_echo = float("-inf")  # when the last dropped echo ended

    def wrote(self, text: str) -> None:
        """Dictation has just written *text*."""
        words = _words(text)
        if words:
            self._written.append((self._clock(), words))

    def clear(self) -> None:
        self._written.clear()
        self._last_echo = float("-inf")

    def is_echo(self, heard: str, started: float | None = None) -> bool:
        """True when *heard* is what was just written, heard again.

        *started* is when the phrase began, when the recogniser said; without
        it only the words decide.
        """
        words = _words(heard)
        if not words:
            return False
        now = self._clock()
        recent_writes = [
            (when, written) for when, written in self._written if now - when <= ECHO_WINDOW_S
        ]
        if not recent_writes:
            return False
        if started is not None:
            anchors = [when for when, _ in recent_writes] + [self._last_echo]
            if not any(0.0 <= started - anchor <= ECHO_START_S for anchor in anchors):
                return False  # began too late to be the reader: said again on purpose
        if self._matches(words, [written for _, written in recent_writes]):
            self._last_echo = now
            return True
        return False

    def _matches(self, words: list[str], recent: list[list[str]]) -> bool:
        content = [word for word in words if word not in self._marks] or words
        if len(content) == 1:
            return any(content == written for written in recent)
        pool = [word for written in recent for word in written]
        blocks = SequenceMatcher(None, content, pool, autojunk=False).get_matching_blocks()
        return sum(block.size for block in blocks) / len(content) >= _SIMILAR
