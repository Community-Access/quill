"""A Python-side mirror of a text control's buffer, and the answers it caches.

The problem this exists for is cheap to describe and expensive to have. Reading
``wx.TextCtrl.GetValue()`` on a multiline control copies the whole buffer across
the wx/native boundary, so every reader of "what does the document say" costs a
pass over the text. Display code has a *lot* of readers -- a status bar with a
word count, a heading cue, a list cue, a live spell check, an autoformat rule
that wants the character before the caret -- and each of them reading the
control directly turned one coalesced refresh of QUILL Lite's status bar into
three full scans plus two marshals, and one arrow key in a large file into
another (bad.md V2, V3, S8, T1).

QUILL solved this in #1346 by giving display code the document's own Python
string and memoising the statistics against a revision counter. It had somewhere
to put them: a :class:`~quill.core.document.Document` that every edit already
flows through. QUILL Lite has no such object -- its document *is* the control --
so this is that seam, built to be used by both, and **both use it** since
2026-09-18: QUILL's hand-rolled stats cache is gone, and the two editors now
answer "what does the document say" through one object (bad.md P0.6c, V4).

The two arrive at "the document changed" differently, and both are supported.
QUILL Lite has a text hook and calls :meth:`invalidate`; QUILL has a revision
counter on its Document and calls :meth:`sync_to`, which invalidates only when
the number has actually moved. Handing QUILL ``invalidate`` instead would have
meant finding every edit path in a 19,000-line module and remembering to call
it -- the kind of completeness nobody can verify -- while the revision it
already maintains is exactly the fact needed.

**Lazy rather than eager, and that is the whole design.** The obvious shape is
to copy the text into Python on every text event, which moves the cost from the
readers to the typist: a full ``GetValue()`` per keystroke is worse than what it
replaces. So an edit only marks the mirror stale, which is O(1); the next
*reader* pays for one read, and every reader after it until the following edit
pays nothing. A status bar that refreshes after a pause in typing therefore
costs one marshal rather than three, and a burst of typing costs none at all.

**Display-only, by contract.** Anything that edits or saves must read the
control itself. The mirror is exactly as current as the last invalidation, which
is the right answer for a word count and the wrong answer for a write to disk.

wx-free and directly tested.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.metrics import DocumentStats, compute_document_stats

__all__ = ["DocumentText", "EditRecord"]


@dataclass(frozen=True, slots=True)
class EditRecord:
    """One edit, in the terms a person would ask about it.

    Sizes rather than the text itself, deliberately: a journal holding copies
    of what was typed is a journal holding the password somebody pasted into
    the wrong window. What a spoken undo needs is *what changed and by how
    much*, and that is what this is.
    """

    #: What did it -- a command title, in the words the menu uses.
    action: str
    #: Where the change began, or -1 when the whole document changed.
    position: int
    characters_before: int
    characters_after: int
    lines_before: int
    lines_after: int

    @property
    def characters_delta(self) -> int:
        return self.characters_after - self.characters_before

    @property
    def lines_delta(self) -> int:
        return self.lines_after - self.lines_before


class DocumentText:
    """The text of one document, read once per edit and asked many times.

    *read* is what fetches the current text -- ``control.GetValue`` in the app,
    a lambda in a test. It is called at most once per revision, and only when
    something actually asks.
    """

    __slots__ = (
        "_journal",
        "_journal_limit",
        "_line_starts",
        "_read",
        "_revision",
        "_stats",
        "_synced_to",
        "_text",
    )

    def __init__(self, read: Callable[[], str], *, journal_limit: int = 50) -> None:
        self._read = read
        self._text: str | None = None
        self._revision = 0
        self._stats: tuple[int, DocumentStats] | None = None
        self._line_starts: tuple[int, list[int]] | None = None
        self._synced_to: object | None = None
        self._journal: list[EditRecord] = []
        self._journal_limit = max(0, int(journal_limit))

    # -- keeping up with the document ----------------------------------- #

    def invalidate(self) -> None:
        """The document changed: forget everything, read nothing.

        Called from the window's text hook. Deliberately does no work: the hook
        runs on every keystroke, and a hook that read the buffer would be the
        cost this class exists to remove.
        """
        self._text = None
        self._stats = None
        self._line_starts = None
        self._revision += 1

    def sync_to(self, revision: object) -> bool:
        """Follow a document's own revision counter. ``True`` when it had moved.

        For QUILL, whose :class:`~quill.core.document.Document` counts its own
        edits: asking "has the number changed?" is O(1) and needs no hook, so
        display code can call this before every read without having to trust
        that some edit path remembered to invalidate. ``None`` (a bare test stub
        with no counter) is treated as "cannot tell", and the mirror is dropped
        so the next read is honest rather than stale.
        """
        if revision is None:
            self.invalidate()
            self._synced_to = None
            return True
        if self._synced_to == revision:
            return False
        self._synced_to = revision
        self.invalidate()
        return True

    @property
    def revision(self) -> int:
        """How many times the document has changed. A cache key, not a version."""
        return self._revision

    # -- reading --------------------------------------------------------- #

    @property
    def text(self) -> str:
        """The document's text, read from the control at most once per edit."""
        if self._text is None:
            self._text = str(self._read())
        return self._text

    def stats(self) -> DocumentStats:
        """Characters, words and lines. Computed once per edit."""
        if self._stats is not None and self._stats[0] == self._revision:
            return self._stats[1]
        stats = compute_document_stats(self.text)
        self._stats = (self._revision, stats)
        return stats

    def line_starts(self) -> list[int]:
        """The offset each line begins at. Built once per edit.

        The reason it is worth caching rather than computing: Extend Selection
        Mode and the status bar both want line arithmetic on every keystroke,
        and rebuilding this table per press is an O(N) scan in the middle of
        somebody holding the Down arrow (bad.md P1.2a).
        """
        if self._line_starts is not None and self._line_starts[0] == self._revision:
            return self._line_starts[1]
        text = self.text
        starts = [0]
        index = text.find("\n")
        while index != -1:
            starts.append(index + 1)
            index = text.find("\n", index + 1)
        self._line_starts = (self._revision, starts)
        return starts

    def line_column(self, position: int) -> tuple[int, int]:
        """1-based line and column for *position*, off the cached line table."""
        starts = self.line_starts()
        capped = max(0, min(int(position), len(self.text)))
        low, high = 0, len(starts) - 1
        while low < high:
            middle = (low + high + 1) // 2
            if starts[middle] <= capped:
                low = middle
            else:
                high = middle - 1
        return low + 1, capped - starts[low] + 1

    def char_before(self, position: int) -> str:
        """The one character before *position*, or "".

        Its own method because the alternative is what QUILL Lite's autoformat
        did: ``GetValue()[position - 1]``, which reads the entire document to
        look at one character, on the hottest path in the app (bad.md T1).
        """
        index = int(position) - 1
        if index < 0:
            return ""
        text = self.text
        return text[index] if index < len(text) else ""

    # -- the journal ------------------------------------------------------ #

    def record(self, action: str, before: str, after: str, *, position: int = -1) -> EditRecord:
        """Remember that *action* turned *before* into *after*, and describe it.

        The journal exists for a question nobody could answer before: **what did
        that just do?** A screen reader says nothing when an application rewrites
        text on its own behalf, so a command that sorts forty lines, or an undo
        that takes it back, is silent -- and "press Ctrl+Z and listen" is not a
        way to find out what changed, because Ctrl+Z is silent too.

        Kept here rather than in the frame because both editors need it and
        neither owns the other, and bounded because a journal that grows with
        the session is a memory leak wearing a feature's clothes. The oldest
        entry falls off; nobody asks what changed forty edits ago.
        """
        record = EditRecord(
            action=action,
            position=int(position),
            characters_before=len(before),
            characters_after=len(after),
            lines_before=before.count("\n") + 1 if before else 0,
            lines_after=after.count("\n") + 1 if after else 0,
        )
        if self._journal_limit:
            self._journal.append(record)
            if len(self._journal) > self._journal_limit:
                del self._journal[0]
        return record

    @property
    def last_edit(self) -> EditRecord | None:
        """The most recent recorded edit, or ``None`` when nothing is recorded."""
        return self._journal[-1] if self._journal else None

    def journal(self) -> tuple[EditRecord, ...]:
        """Every recorded edit, oldest first."""
        return tuple(self._journal)
