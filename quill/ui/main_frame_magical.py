"""The three commands that answer what the screen reader cannot (bad.md P3.7).

A reader says what is under the cursor. It has no way to say what the
application just did on its own behalf, or what kind of document you have
arrived in, and those are the two things a sighted user gets for free from a
glance at the screen.

* **What Is This Document?** -- size, shape, and whether anything will stop you.
  The glance before you start reading.
* **What Changed?** -- what the last command did to the text. Sort Lines,
  Remove Duplicates and thirty others rewrite the buffer in silence.
* **Undo and Say What Changed** -- Ctrl+Z is the most-pressed key in an editor
  and the most silent: whether it did anything at all is a guess.

The fourth approved command, Repeat Last Announcement, shipped as #1304 and
lives in :mod:`quill.ui.announce_commands`.

The wording is all in the wx-free :mod:`quill.core.magical`, so QUILL Lite can
adopt these three without the two editors describing the same change two ways --
which is the whole point of rule 10, and the reason none of this phrasing is
written here.
"""

from __future__ import annotations

__all__ = ["MagicalTierMixin"]


class MagicalTierMixin:
    """What is this, what changed, and what did that undo take back."""

    def describe_this_document(self) -> None:
        """Say what kind of document this is, and how big and how shaped.

        Announced rather than put in the status bar: it is asked for, and an
        answer to a question you asked should arrive the way the question was
        put -- immediately, cutting across whatever is being read.
        """
        from quill.core.magical import arrival_summary

        stats = self._statusbar_document_stats()
        if stats is None:
            self._announce("No document is open.")
            return
        self._announce(
            arrival_summary(
                stats,
                kind=self._arrival_kind_label(),
                headings=self._arrival_heading_count(),
                list_items=self._arrival_list_item_count(),
                read_only=bool(self._document_is_read_only()),
            )
        )

    def describe_last_change(self) -> None:
        """Say what the last command did to the text.

        Reads the shared edit journal on :class:`~quill.core.document_text.DocumentText`,
        which every one of QUILL's own rewrites passes through
        (``_replace_document_text``). Before this the only way to find out what
        Sort Lines had done was to read the document again.
        """
        from quill.core.magical import describe_change

        self._announce(describe_change(self.doc_text.last_edit))

    def undo_and_say_what_changed(self) -> None:
        """Undo, then say what was taken back -- or that there was nothing.

        The distinction is the feature. An undo at the bottom of the stack and an
        undo that reversed a forty-line sort are both completely silent, and no
        amount of listening tells them apart; the only way to find out used to be
        to read the document and compare it with your memory of it.
        """
        from quill.core.magical import describe_undo

        record = self.doc_text.last_edit
        editor = getattr(self, "editor", None)
        can_undo = getattr(editor, "CanUndo", None)
        worked = bool(can_undo()) if callable(can_undo) else editor is not None
        if worked:
            undo = getattr(editor, "Undo", None)
            if callable(undo):
                undo()
            else:
                worked = False
        self._announce(describe_undo(record, worked=worked))

    # -- what the summary needs to know ----------------------------------- #

    def _arrival_kind_label(self) -> str:
        """ "Markdown", "HTML", "Rich Text" or "Plain text"."""
        mode = str(self._current_editor_mode() or "")
        if mode.startswith("rich"):
            return "Rich Text"
        kind = str(self._effective_markup_kind() or "").lower()
        if kind in {"markdown", "md"}:
            return "Markdown"
        if kind in {"html", "htm", "xhtml"}:
            return "HTML"
        return "Plain text"

    def _arrival_heading_count(self) -> int:
        """How many headings the document has, off the outline QUILL already builds."""
        entries = getattr(self, "_outline_entries", None)
        if not callable(entries):
            return 0
        try:
            return len(list(entries()))
        except Exception:  # noqa: BLE001 - a summary must never be the thing that fails
            return 0

    def _arrival_list_item_count(self) -> int:
        """How many list items, counted from the text rather than guessed."""
        from quill.core.list_structure import count_list_items

        try:
            return int(count_list_items(self.doc_text.text))
        except Exception:  # noqa: BLE001
            return 0
