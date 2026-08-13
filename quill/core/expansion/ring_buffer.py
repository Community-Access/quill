"""The bounded memory of recently typed characters.

This is the one piece of Quill Inkwell that people are right to ask hard
questions about, so its limits are deliberate and small:

- It holds at most :data:`MAX_LENGTH` characters, in memory only. Nothing is
  ever written to disk, logged, or sent anywhere.
- It is cleared on every event that means "the previous word is finished or
  gone": a successful expansion, Escape, any navigation or editing key, a
  change of foreground window, and pausing expansion.
- It only ever receives characters the user typed into a normal editable
  surface. Nothing decides what to keep based on *content*, so no rule about
  passwords can be got wrong here -- the window-level check in
  :mod:`quill.core.expansion.targets` refuses first.

Pure, wx-free, and platform-free so it can be tested directly.
"""

from __future__ import annotations

import collections

#: Longer than any sensible abbreviation plus the word it sits in, short enough
#: that the buffer can never accumulate a sentence, let alone a password.
MAX_LENGTH = 64


class RingBuffer:
    """A fixed-size FIFO of recently typed characters."""

    __slots__ = ("_buf",)

    def __init__(self, maxlen: int = MAX_LENGTH) -> None:
        self._buf: collections.deque[str] = collections.deque(maxlen=maxlen)

    def push(self, char: str) -> None:
        """Append one typed character (extra characters are ignored)."""
        if len(char) == 1:
            self._buf.append(char)

    def backspace(self) -> None:
        """Forget the most recent character, as Backspace just removed it."""
        if self._buf:
            self._buf.pop()

    def clear(self) -> None:
        self._buf.clear()

    def text(self) -> str:
        return "".join(self._buf)

    def __len__(self) -> int:
        return len(self._buf)
