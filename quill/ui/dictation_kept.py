"""Words kept on disk, offered in Recent Phrases: the window half of D-5.

The store is :mod:`quill.core.windows_dictation.rescue`. Every host that has
Recent Phrases (QUILL, QUILL Lite and QUILL Transcribe, on Shift+F11) lists,
after this session's phrases:

* words **not written** last time -- held while paused, or a phrase Windows
  stopped typing -- until they are inserted or discarded;
* the **review that did not finish** (D-2's own rescue file,
  ``dictation-review.json``, read where it is rather than copied);
* with **dictation history** on, the earlier phrases it kept, newest first.

Insert Again on a kept entry deletes it once it is written; Discard deletes it
unwritten; Clear History deletes the history. At start, one sentence says when
words from last time are waiting (:func:`kept_at_start`), and a history that was
turned off is deleted then too.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["KEEP_WHERE", "KeptWords", "SavedRow", "kept_at_start"]

#: Where the start-up sentence sends people: the same key in all three hosts.
KEEP_WHERE = "Recent Phrases, Shift+F11, brings them back."


@dataclass(frozen=True, slots=True)
class SavedRow:
    """One kept entry as Recent Phrases lists it."""

    label: str
    text: str
    kind: str
    discard: Callable[[], None]
    #: Written: nothing left to keep. History entries stay in the history.
    delivered: Callable[[], None]


class KeptWords:
    """One host's kept words: its store, its review file and its history length."""

    def __init__(self, keep: Any, review_path: Path | None, history_days: int) -> None:
        self.keep = keep
        self.review_path = review_path
        self.history_days = int(history_days or 0)

    def _review(self) -> SavedRow | None:
        if self.review_path is None:
            return None
        from quill.core.windows_dictation.rescue import KIND_LABELS
        from quill.core.windows_dictation.review_session import clear_rescue, load_rescue

        session = load_rescue(self.review_path)
        if session is None:
            return None
        text = " ".join(session.current.split())
        path = self.review_path
        return SavedRow(
            f"{KIND_LABELS['review']}: {text}",
            text,
            "review",
            lambda: clear_rescue(path),
            lambda: clear_rescue(path),
        )

    def rows(self) -> list[SavedRow]:
        """Not written (oldest first), the review, then the history (newest first).
        With the history off, any left from before is deleted here."""
        if not self.history_days:
            self.keep.clear_history()
        out: list[SavedRow] = []
        for entry in self.keep.kept():
            out.append(
                SavedRow(
                    entry.label,
                    entry.text,
                    entry.kind,
                    lambda entry_id=entry.entry_id: self.keep.drop(entry_id),
                    lambda entry_id=entry.entry_id: self.keep.drop(entry_id),
                )
            )
        review = self._review()
        if review is not None:
            out.append(review)
        for entry in self.keep.history(self.history_days):
            out.append(
                SavedRow(
                    entry.label,
                    entry.text,
                    "history",
                    lambda entry=entry: self.keep.forget(entry),
                    lambda: None,
                )
            )
        return out

    def clear_history(self) -> Callable[[], None] | None:
        """Clear History's action, offered while the history is on."""
        if not self.history_days:
            return None
        return lambda: bool(self.keep.clear_history())

    def waiting(self) -> int:
        """How many entries are not written: what the start-up sentence counts."""
        count = len(self.keep.kept())
        return count + (1 if self._review() is not None else 0)


def kept_at_start(kept: KeptWords, review_notice: str) -> str:
    """The one sentence said at start, or ``""``. A history that was turned off
    (here or in another copy of the settings) is deleted now."""
    from quill.core.windows_dictation.rescue import kept_notice

    if not kept.history_days:
        kept.keep.clear_history()
    if kept.keep.kept():
        return kept_notice(kept.waiting(), KEEP_WHERE)
    if kept._review() is not None:
        return review_notice
    return ""
