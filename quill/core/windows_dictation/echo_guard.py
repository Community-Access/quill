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

Pure and wx-free; the controller supplies the clock.
"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from difflib import SequenceMatcher

from quill.core.windows_dictation.readback import mark_names

__all__ = ["ECHO_WINDOW_S", "EchoGuard"]

#: How long after writing a phrase its echo is expected. A screen reader starts
#: within a second; a long phrase read at a slow rate takes several more.
ECHO_WINDOW_S = 8.0
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

    def wrote(self, text: str) -> None:
        """Dictation has just written *text*."""
        words = _words(text)
        if words:
            self._written.append((self._clock(), words))

    def clear(self) -> None:
        self._written.clear()

    def is_echo(self, heard: str) -> bool:
        """True when *heard* is what was just written, heard again."""
        words = _words(heard)
        if not words:
            return False
        now = self._clock()
        recent = [written for when, written in self._written if now - when <= ECHO_WINDOW_S]
        if not recent:
            return False
        content = [word for word in words if word not in self._marks] or words
        if len(content) == 1:
            return any(content == written for written in recent)
        pool = [word for written in recent for word in written]
        blocks = SequenceMatcher(None, content, pool, autojunk=False).get_matching_blocks()
        return sum(block.size for block in blocks) / len(content) >= _SIMILAR
