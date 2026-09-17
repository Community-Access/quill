"""Line surgery, and getting deleted text back.

Reordering two lines in an editor that cannot do it costs a select, a cut, a
move and a paste -- four operations, each of which moves the caret somewhere the
last one did not leave it. For somebody reading by ear that is not merely slower
than pressing one key; it is four chances to lose your place in a document you
cannot glance at. That is the whole argument for this module, and it is why
these commands are here rather than filed under "power tools".

Every operation is QUILL's own :mod:`quill.core.line_ops`, not a second
implementation. QuillLite must never be ahead of QUILL, and it is not here
either: QUILL registered all five line commands long before this file existed
and bound none of them to a key, so they were reachable from a menu and from no
keystroke at all. Adding them here is what surfaced that, and the same chords
now appear in ``DEFAULT_KEYMAP`` on both sides.

**Restore Deleted Text** is the one that is not a convenience. Undo puts text
back where it was; the deletion ring puts it back *where the caret is now*,
which turns a delete into a move and is the only thing here that undo cannot
do. Deletions are recorded by the structured-delete commands, so the ring holds
what a person deliberately removed rather than every character they backspaced
over.

Two rules the whole module keeps:

* **One undoable step.** Changes go in through the control's own ``Replace``,
  so Ctrl+Z takes back the whole move rather than an insertion and a deletion
  that have to be undone separately.
* **Say what happened.** A line move produces no sound of its own and the
  reader announces nothing for a caret that lands where it already was, so each
  command announces its own outcome -- including the refusals, because "nothing
  happened" and "you are on the first line" are different facts.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.apps.lite_dialogs import choose_from_rows
from quill.core import line_ops
from quill.core.deletion_ring import DeletionRing, removed_span
from quill.core.format_ops import toggle_line_comment
from quill.ui.richedit_editing import RICH

#: ``(text, cursor) -> (text, cursor)`` -- the shape every whole-document line
#: operation in :mod:`quill.core.line_ops` already has.
_LineOp = Callable[[str, int], tuple[str, int]]


class DocumentLineMixin:
    """Move, delete and join lines, and put deleted text back."""

    # ------------------------------------------------------------------ #
    # The one path every command here goes through
    # ------------------------------------------------------------------ #

    def _apply_line_op(self, op: _LineOp, *, refusal: str, done: str) -> None:
        """Run *op* over the whole document, announcing the outcome either way.

        The whole document rather than the selection: every operation here is
        defined relative to the caret's line, and ``line_ops`` already works in
        those terms. Passing a slice would make "the line above" mean "the line
        above within the selection", which is not what anybody means by it.
        """
        text = self.control.GetValue()
        cursor = self.control.GetInsertionPoint()
        changed, new_cursor = op(text, cursor)
        if changed == text:
            self._announce(refusal)
            return
        removed = self._record_removal(text, changed)
        # Replace the whole value in one go so the control keeps it as a single
        # undo step. SetValue would clear the undo history entirely.
        self.control.Replace(0, self.control.GetLastPosition(), changed)
        self.control.SetInsertionPoint(min(new_cursor, self.control.GetLastPosition()))
        self._set_modified(True)
        self._touch_status()
        self._announce(done if not removed else f"{done}: {self._preview(removed)}")

    def _record_removal(self, before: str, after: str) -> str:
        """Remember what a delete took, so Restore Deleted Text can offer it."""
        if len(after) >= len(before):
            return ""
        removed = removed_span(before, after)
        if removed:
            self._deletion_ring().record(removed)
        return removed

    def _deletion_ring(self) -> DeletionRing:
        """This window's ring, created on first use.

        Per window, not per app: a deletion is a fact about the document you
        took it out of, and offering document 2's deleted paragraph while you
        stand in document 5 would be a way to corrupt two files at once.
        """
        ring = getattr(self, "_lite_deletion_ring", None)
        if ring is None:
            ring = DeletionRing()
            self._lite_deletion_ring = ring
        return ring

    @staticmethod
    def _preview(text: str, limit: int = 40) -> str:
        """A short, speakable rendering of *text* for an announcement."""
        flat = " ".join(text.split())
        if not flat:
            return "blank line"
        return flat if len(flat) <= limit else f"{flat[:limit]}..."

    # ------------------------------------------------------------------ #
    # Moving and duplicating
    # ------------------------------------------------------------------ #

    def cmd_move_line_up(self) -> None:
        self._apply_line_op(
            line_ops.move_line_up,
            refusal="Already the first line",
            done="Moved line up",
        )

    def cmd_move_line_down(self) -> None:
        self._apply_line_op(
            line_ops.move_line_down,
            refusal="Already the last line",
            done="Moved line down",
        )

    def cmd_duplicate_line(self) -> None:
        self._apply_line_op(
            line_ops.duplicate_line,
            refusal="Nothing to duplicate",
            done="Duplicated line",
        )

    def cmd_join_lines(self) -> None:
        self._apply_line_op(
            line_ops.join_with_next_line,
            refusal="No line below to join",
            done="Joined lines",
        )

    # ------------------------------------------------------------------ #
    # Deleting, and undeleting
    # ------------------------------------------------------------------ #

    def cmd_delete_line(self) -> None:
        self._apply_line_op(
            line_ops.delete_line,
            refusal="Nothing to delete",
            done="Deleted line",
        )

    def cmd_delete_to_line_start(self) -> None:
        self._apply_line_op(
            line_ops.delete_to_line_start,
            refusal="Already at the start of the line",
            done="Deleted to start of line",
        )

    def cmd_delete_to_line_end(self) -> None:
        self._apply_line_op(
            line_ops.delete_to_line_end,
            refusal="Already at the end of the line",
            done="Deleted to end of line",
        )

    def cmd_delete_paragraph(self) -> None:
        self._apply_line_op(
            line_ops.delete_paragraph,
            refusal="Nothing to delete",
            done="Deleted paragraph",
        )

    def cmd_restore_deletion(self) -> None:
        """Put a recent structured deletion back, at the caret.

        Deliberately *at the caret* rather than where it came from: that is what
        distinguishes this from undo, and it is the whole reason to have it.

        **All three, not just the newest.** The ring has held three deletions
        all along and this command offered one of them, so two were unreachable
        from the only surface that reads the ring -- and the one you want is
        rarely the last thing you deleted, because the last thing you deleted
        you probably meant to (bad.md C9). One of them goes straight in; more
        than one asks which, with a preview of each.
        """
        ring = self._deletion_ring()
        entries = ring.entries()
        if not entries:
            self._announce("Nothing deleted yet in this document")
            return
        if len(entries) == 1:
            self._restore_deleted(entries[0])
            return
        rows = [
            (index, f"{len(text):,} characters: {self._preview(text)}")
            for index, text in enumerate(entries)
        ]
        chosen = choose_from_rows(
            self,
            title="Restore Deleted Text",
            label="&Recently deleted, newest first:",
            help_text=(
                "The last few things a line command deleted. Choosing one puts it "
                "back where the cursor is now, which is what makes this different "
                "from undo."
            ),
            rows=rows,
        )
        self.control.SetFocus()
        if chosen is None:
            return
        self._restore_deleted(entries[int(chosen)])

    def _restore_deleted(self, restored: str) -> None:
        at = self.control.GetInsertionPoint()
        self.control.Replace(at, at, restored)
        self.control.SetInsertionPoint(at + len(restored))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Restored {len(restored)} characters: {self._preview(restored)}")

    # ------------------------------------------------------------------ #
    # Comments
    # ------------------------------------------------------------------ #

    def cmd_toggle_line_comment(self) -> None:
        """Ctrl+/: comment the selected lines out, or bring them back.

        QuillLite's PRD accepts that people edit ``.py``, ``.json`` and
        ``.conf`` here -- it already silences the spell checker in them for
        exactly that reason -- and a comment toggle is the second half of that
        concession (bad.md 4.2, Tier 1). It is the same shared
        :func:`~quill.core.format_ops.toggle_line_comment` QUILL uses, so the
        prefix a file gets is the one QUILL would give it: ``# `` for Python and
        the configuration formats, ``-- `` for SQL, ``<!-- -->`` for HTML and
        Markdown, ``// `` for everything else.

        The file name decides, which is why an unsaved document gets ``// ``:
        there is nothing else to go on, and guessing from the contents would be
        a guess a person then has to undo.
        """
        if self.editor.mode == RICH:
            self._announce("Commenting out lines works in plain text documents")
            return
        text = self.control.GetValue()
        start, end = self.control.GetSelection()
        updated, span_start, span_end = toggle_line_comment(text, start, end, self.path)
        if updated == text:
            self._announce("Nothing to comment")
            return
        # Counted by comparing the lines, not by counting the newlines in the
        # span: the span ends at a line break, so a newline count is one too
        # many, and whether a blank line inside a selection takes a marker
        # depends on the comment style. A count that is sometimes wrong is
        # worse than no count at all (the same rule as the collector's, C7).
        before_lines = text[span_start:span_end].split("\n")
        after_lines = updated[span_start:span_end].split("\n")
        count = sum(
            1 for pair in zip(before_lines, after_lines, strict=False) if pair[0] != pair[1]
        )
        self.control.Replace(0, self.control.GetLastPosition(), updated)
        self.control.SetSelection(span_start, span_end)
        self._set_modified(True)
        self._touch_status()
        commented = len(updated) > len(text)
        self._announce(
            f"{'Commented' if commented else 'Uncommented'} {count} line{'s' if count != 1 else ''}"
        )
