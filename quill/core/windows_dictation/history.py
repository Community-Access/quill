"""Every inserted phrase, as a transaction "scratch that" can take back.

A phrase remembers exactly what it inserted and where. Scratching it removes
that range -- and only after checking that the range still holds that text. If
anything has been typed into it, over it or in front of it since, the positions
no longer mean what they meant, and removing them would delete somebody's
typing. So a stale transaction is refused out loud rather than applied
approximately: :meth:`PhraseHistory.pop` hands the phrase back and the caller
checks it against the document before touching anything.

Held in memory for one dictation session. It is never written to disk, because
it is what the user said.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

__all__ = ["DictatedPhrase", "PhraseHistory"]

#: How many phrases "scratch that" can walk back through. Enough for somebody
#: scratching a run of misrecognitions; small, because each one holds text.
_DEPTH = 20


@dataclass(frozen=True, slots=True)
class DictatedPhrase:
    """One committed phrase: what went in, and the range it occupies."""

    inserted: str
    start: int
    end: int
    #: It ended with a full stop the recogniser added, not one somebody said.
    auto_period: bool = False


class PhraseHistory:
    """The phrases committed this session, newest last."""

    def __init__(self, depth: int = _DEPTH) -> None:
        self._phrases: deque[DictatedPhrase] = deque(maxlen=max(1, depth))

    def __len__(self) -> int:
        return len(self._phrases)

    def push(self, phrase: DictatedPhrase) -> None:
        if phrase.inserted:
            self._phrases.append(phrase)

    def peek(self) -> DictatedPhrase | None:
        """The newest phrase, left where it is."""
        return self._phrases[-1] if self._phrases else None

    def replace_last(self, phrase: DictatedPhrase) -> None:
        """Swap the newest phrase for *phrase* -- it was changed in place."""
        if self._phrases:
            self._phrases[-1] = phrase

    def pop(self) -> DictatedPhrase | None:
        """The newest phrase, removed from the history, or ``None``."""
        return self._phrases.pop() if self._phrases else None

    def clear(self) -> None:
        self._phrases.clear()
