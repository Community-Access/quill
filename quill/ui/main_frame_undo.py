"""Persistent undo: the history that survives closing the file.

Extracted from ``main_frame.py`` under GATE-11 (x.md item 12). The gate's rule
is "extract, do not raise the budget", and it is the right rule here: this is a
self-contained cluster -- load, record, flush, step -- that only ever touches
its own three attributes, so it was sitting in the largest module in the tree
for no reason beyond having been written there.

The size budget it grew to need is the interesting part. The history held up to
a hundred *full document copies* and was rewritten in its entirety every few
seconds while you type, because the whole thing is one JSON file. A hundred
snapshots of a shopping list is nothing; a hundred snapshots of a 1 MB
manuscript is 100 MB, in memory and on disk, so the cost of every keystroke grew
with the length of the piece you were writing. ``bound_history`` caps the total
as well as the count, and ``save_and_reanchor`` keeps the in-memory copy and the
undo cursor in step with what actually survived -- without which the cap would
bound the file and not the memory, and the cursor would quietly point at the
wrong snapshot.

(x.md proposed a length-then-hash equality check instead. Measured, that is a
pessimization: Python's ``==`` already compares length first and returns in
~0 us when they differ, which is what a keystroke produces, while sha256 of a
1 MB document costs ~243 us against memcmp's ~34 us. The comparison was never
the expensive part; the retained copies were.)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from quill.core.undo_store import bound_history, load_undo_history, save_and_reanchor


class PersistentUndoMixin:
    """Undo history that outlives the editing session."""

    # Provided by MainFrame.
    settings: Any
    document: Any
    editor: Any
    _persistent_undo_history: list[str]
    _persistent_undo_index: int
    _suspend_persistent_undo: bool

    def _load_persistent_undo_state(self, path: Path, text: str) -> None:
        history = load_undo_history(path)
        if not history:
            history = [text]
        elif history[-1] != text:
            history.append(text)
        self._persistent_undo_history = bound_history(history)
        self._persistent_undo_index = len(self._persistent_undo_history) - 1
        if self.settings.persistent_undo:
            self._flush_persistent_undo_to(path)

    def _record_persistent_undo_state(self, text: str) -> None:
        if not self.settings.persistent_undo or self.document.path is None:
            return
        if (
            self._persistent_undo_history
            and self._persistent_undo_history[self._persistent_undo_index] == text
        ):
            return
        if self._persistent_undo_index < len(self._persistent_undo_history) - 1:
            self._persistent_undo_history = self._persistent_undo_history[
                : self._persistent_undo_index + 1
            ]
        self._persistent_undo_history.append(text)
        # Bounded by total size as well as count -- see MAX_HISTORY_CHARS.
        self._persistent_undo_history = bound_history(self._persistent_undo_history)
        self._persistent_undo_index = len(self._persistent_undo_history) - 1
        # Persisting the full history JSON on every keystroke is wasteful (and
        # can write many MB per second on large documents). Throttle disk
        # writes; flush_persistent_undo() forces a write on save/close.
        self._persistent_undo_dirty = True
        self._maybe_flush_persistent_undo()

    def _maybe_flush_persistent_undo(self, force: bool = False) -> None:
        if not getattr(self, "_persistent_undo_dirty", False):
            return
        if self.document.path is None:
            return
        now = datetime.now(UTC)
        last = getattr(self, "_last_persistent_undo_write_at", None)
        interval = timedelta(seconds=3)
        if not force and last is not None and now - last < interval:
            return
        self._flush_persistent_undo_to(self.document.path)
        self._last_persistent_undo_write_at = now
        self._persistent_undo_dirty = False

    def _flush_persistent_undo_to(self, path: Path) -> None:
        """Write, and keep the in-memory copy in step with what survived."""
        self._persistent_undo_history, self._persistent_undo_index = save_and_reanchor(
            path, self._persistent_undo_history, self._persistent_undo_index
        )

    def flush_persistent_undo(self) -> None:
        self._maybe_flush_persistent_undo(force=True)

    def _step_persistent_undo(self, direction: int) -> None:
        if not self._persistent_undo_history:
            self._set_status("Nothing to undo")
            return
        target = self._persistent_undo_index + direction
        if target < 0 or target >= len(self._persistent_undo_history):
            self._set_status("Nothing to redo" if direction > 0 else "Nothing to undo")
            return
        text = self._persistent_undo_history[target]
        self._persistent_undo_index = target
        self._suspend_persistent_undo = True
        try:
            self.editor.ChangeValue(text)
        finally:
            self._suspend_persistent_undo = False
        self.document.set_text(text)
        self._refresh_title()
        self._set_status("Redo" if direction > 0 else "Undo")
