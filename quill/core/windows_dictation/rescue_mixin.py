"""The controller's half of D-5: what it keeps on disk, and when it lets go.

The store is :mod:`~quill.core.windows_dictation.rescue`; the host hands it over
through the feedback port's optional ``rescue()``, as the library is
``library()``. A host without one (Quill Inkwell, tests) keeps everything in
memory, exactly as before.

* **Held words** -- every change to the phrases held while paused rewrites one
  entry for that pause (:meth:`RescueMixin._rescue_held`). Resume and Discard
  Held Words end it; stopping, failing and the app ending keep it, so the next
  start can offer it.
* **A phrase that was not written** -- the controller could not write it, or
  Windows stopped typing it part-way (:meth:`RescueMixin._rescue_unwritten`).
* **History** -- every phrase that reaches Recent Phrases is also offered to the
  opt-in history (:class:`RecentPhrases`, :meth:`RescueMixin._remember`), only
  while ``windows_dictation_history_days`` is more than 0.

wx-free.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.composer import compose

if TYPE_CHECKING:
    from quill.core.windows_dictation.parser import ParsedPhrase
    from quill.core.windows_dictation.preferences import DictationPreferences
    from quill.core.windows_dictation.rescue import DictationKeep

__all__ = ["KEPT_SENTENCE", "RecentPhrases", "RescueMixin", "held_text"]

#: Added when stopping leaves held words on disk.
KEPT_SENTENCE = "They are kept in Recent Phrases."


def held_text(held: Iterable[ParsedPhrase]) -> str:
    """The held phrases as they would have been written, one after another."""
    text = ""
    for parsed in held:
        text += compose(parsed.pieces, before=text, after="")
    return text.strip()


class RecentPhrases(deque[str]):
    """Recent Phrases' list, which also tells the history about each phrase."""

    def __init__(self, maxlen: int, on_add: Callable[[str], None] | None = None) -> None:
        super().__init__(maxlen=maxlen)
        self.on_add = on_add

    def appendleft(self, text: str) -> None:
        super().appendleft(text)
        if self.on_add is not None:
            try:
                self.on_add(text)
            except Exception:  # noqa: BLE001 - history is a convenience, never a failure
                pass


class RescueMixin:
    """Keep uncommitted words on disk through the host's store; let go on delivery."""

    _feedback: Any
    _preferences: Callable[[], DictationPreferences]
    #: The store entry for the words held during this pause.
    _held_kept_id = ""

    @property
    def held_on_disk(self) -> bool:
        """Whether the words held during this pause are kept on disk."""
        return bool(self._held_kept_id)

    def _kept_store(self) -> DictationKeep | None:
        provider = getattr(self._feedback, "rescue", None)
        try:
            return provider() if callable(provider) else None
        except Exception:  # noqa: BLE001 - no store is an answer
            return None

    def _remember(self, text: str) -> None:
        """A phrase went into Recent Phrases: into the history too, if it is on.
        Off, any history left from before is deleted (one missing-file check)."""
        days = int(getattr(self._preferences(), "history_days", 0) or 0)
        store = self._kept_store()
        if store is not None:
            store.remember(text, days)

    def _rescue_held(self, held: list[ParsedPhrase]) -> bool:
        """The held phrases changed: rewrite this pause's entry. ``True`` when
        they are on disk."""
        store = self._kept_store()
        if store is None:
            return False
        text = held_text(held)
        if not text:
            self._rescue_held_done()
            return False
        self._held_kept_id = store.keep("held", text, self._held_kept_id)
        return bool(self._held_kept_id)

    def _rescue_held_done(self) -> None:
        """The held words were written, discarded or taken into a review."""
        store = self._kept_store()
        if store is not None and self._held_kept_id:
            store.drop(self._held_kept_id)
        self._held_kept_id = ""

    def _rescue_held_left(self) -> bool:
        """Dictation ended with words held: they stay on disk for next time,
        and the next pause gets an entry of its own. ``True`` when kept."""
        kept, self._held_kept_id = bool(self._held_kept_id), ""
        return kept

    def _rescue_unwritten(self, text: str) -> None:
        """A phrase that was not written, or only partly: keep it."""
        store = self._kept_store()
        if store is not None and text.strip():
            store.keep("unwritten", text.strip())
