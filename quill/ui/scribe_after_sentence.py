"""Open a Scribe result's window after the sentence that names it (GATE-13).

When a result opens in a new window -- a QUILL Lite window, Quill Media
Player, QUILL handed an EPUB from QUILL Lite, the person's browser -- that
window comes to the
front and the screen reader says it as focus lands there, cutting off
whatever was being said. The result sentence is said once and must be heard,
so the opening waits for it.

A host *holds* the opening when it is asked to open a result, with the phrase
that names it (:meth:`AfterSentence.hold`), and *releases* it when it says a
sentence carrying that phrase (:meth:`AfterSentence.said`), after a delay from
that sentence's length: 1.5 to 6 seconds. If no such sentence comes within a
second, it opens anyway. Nothing is said twice: the sentence is the only one,
and the new window's title names the document.

**Not over somebody's work.** If, by the time it would open, the person has
gone to another program (the app is no longer in front), it does not open, and
nothing is said: Open Result is still there. A second opening held before the
first was released replaces it; the person asked for the later one.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

#: How long a sentence takes to say, at a brisk screen-reader rate, and the
#: bounds on waiting for it before the window opens.
_MS_PER_CHARACTER = 60
_SHORTEST_WAIT_MS = 1_500
_LONGEST_WAIT_MS = 6_000
#: When no sentence follows the opening at all, it still happens, after this.
UNSAID_WAIT_MS = 1_000


def wait_for_sentence(text: str) -> int:
    """How long to let *text* be said before a window comes to the front."""
    return max(_SHORTEST_WAIT_MS, min(_LONGEST_WAIT_MS, len(text) * _MS_PER_CHARACTER))


class AfterSentence:
    """One held opening at a time; see the module notes."""

    def __init__(self, still_here: Callable[[], bool] | None = None) -> None:
        self._held: Callable[[], None] | None = None
        self._phrase = ""
        self._still_here = still_here

    def hold(self, opening: Callable[[], None], phrase: str = "") -> None:
        """Open after the sentence carrying *phrase* (or after a second)."""
        self._held = opening
        self._phrase = phrase
        self._later(UNSAID_WAIT_MS, opening, fallback=True)

    def said(self, text: str) -> None:
        """A sentence was just said: if it names the held result, let it go after it."""
        opening = self._held
        if opening is not None and (not self._phrase or self._phrase in text):
            self._held = None
            self._later(wait_for_sentence(text), opening, fallback=False)

    def _later(self, delay_ms: int, opening: Callable[[], None], *, fallback: bool) -> None:
        def go() -> None:
            if fallback:  # only if no sentence took it first
                if self._held is not opening:
                    return
                self._held = None
            if self._still_here is not None and not self._still_here():
                return  # the person went elsewhere: Open Result is still there
            opening()

        from quill.stability.wx_dispatch import call_later_safely

        call_later_safely(delay_ms, go, name="Open the Scribe result after its sentence")


def browser_opening(page: Path, announce: Callable[[str], None]) -> Callable[[], None]:
    """Show *page* in the person's browser; say so once if the browser would not start."""

    def show() -> None:
        from quill.ui import scribe_entry

        if not scribe_entry.open_in_browser(page):
            announce(f"Your browser could not be opened. {page.name} is saved in its folder.")

    return show


__all__ = ["UNSAID_WAIT_MS", "AfterSentence", "browser_opening", "wait_for_sentence"]
