"""Deletion ring: a small kill-ring of recently deleted text.

Distinct from undo (which reverts the last edit in place) and from the Copy
Tray (which captures *copies*): the deletion ring captures text removed by
QUILL's structured delete commands so it can be re-inserted at the *current*
cursor position later. This mirrors the WordPerfect Editor "Cancel" buffer,
which remembered the last three deletions and let you restore any of them.

The ring is pure data — no ``wx`` — so it is fully unit-testable. The UI layer
(:mod:`quill.ui.main_frame_power_tools`) records into it from
``_apply_line_operation`` and reads from it for ``edit.restore_deletion``.
"""

from __future__ import annotations

from collections import deque

DEFAULT_MAX_ENTRIES = 3


def removed_span(before: str, after: str) -> str:
    """Return the contiguous run of text present in *before* but not *after*.

    Assumes a single contiguous deletion (true for every delete command that
    feeds the ring). Returns ``""`` when *after* is not a pure deletion of
    *before* (e.g. equal strings, or an insertion). Computed by stripping the
    common prefix and the common suffix.
    """
    if len(after) >= len(before):
        return ""
    prefix = 0
    limit = len(after)
    while prefix < limit and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    max_suffix = min(len(after) - prefix, len(before) - prefix)
    while suffix < max_suffix and before[-1 - suffix] == after[-1 - suffix]:
        suffix += 1
    return before[prefix : len(before) - suffix]


class DeletionRing:
    """Holds up to ``max_entries`` recent deletions, newest first."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._max_entries = max(1, int(max_entries))
        self._entries: deque[str] = deque(maxlen=self._max_entries)

    def record(self, text: str) -> None:
        """Push *text* as the newest deletion.

        Empty strings are ignored. A deletion identical to the current newest
        entry is collapsed so repeated identical deletes do not flood the ring.
        """
        if not text:
            return
        if self._entries and self._entries[0] == text:
            return
        self._entries.appendleft(text)

    def is_empty(self) -> bool:
        return not self._entries

    def most_recent(self) -> str | None:
        return self._entries[0] if self._entries else None

    def entries(self) -> list[str]:
        """Return the deletions newest-first (a copy; safe to mutate)."""
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
