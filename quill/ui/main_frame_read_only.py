"""The Read-Only Guard in QUILL (EDS-8), mixed into :class:`MainFrame`.

Moved out of ``main_frame_power_tools.py`` on 2026-10-16, when the guard grew a
key (Ctrl+Alt+Backspace, shared with QUILL Lite under rule 2), a shared memory
(:mod:`quill.core.read_only_guards`) and a refusal on the text-changing paths.

What the guard does and does not stop:

* **Stops** typing (the control is made read-only) and every command that
  changes text through :meth:`MainFrame._replace_document_text` or
  :meth:`MainFrame._apply_insertion_result` -- snippets, line tools, case
  changes, Copy Tray pastes and the rest. Those raise
  :class:`~quill.core.read_only_guards.DocumentReadOnlyError` before the text
  changes, and the command runner says "Document is read-only" instead of the
  command's own success sentence.
* **Leaves alone** the caret, the selection, reading, Find, bookmarks (they are
  stored beside the document, not in it), and document notes, which are kept
  beside the file while the guard is on rather than written into it.

The guard is remembered per file. A file that cannot be written at all (a
read-only share, the read-only attribute) is treated as guarded too, so it says
so at open instead of refusing at Ctrl+S twenty minutes later.
"""

from __future__ import annotations

from quill.core.paths import app_data_dir
from quill.core.read_only_guards import (
    GUARD_FILENAME,
    DocumentReadOnlyError,
    ReadOnlyGuards,
    toggle_sentence,
)

__all__ = ["ReadOnlyGuardMixin"]


class ReadOnlyGuardMixin:
    """Toggle, remember and enforce the Read-Only Guard."""

    def _read_only_guards(self) -> ReadOnlyGuards:
        """The remembered guards, loaded once per window.

        Keys are normalised the way bookmarks and notes are, so a file opened
        from File Explorer finds the guard set on it from Open Recent.
        """
        guards = getattr(self, "_power_tools_read_only_guards", None)
        if guards is None:
            guards = ReadOnlyGuards(app_data_dir() / GUARD_FILENAME)
            self._power_tools_read_only_guards = guards
        return guards

    def _document_is_read_only(self) -> bool:
        flag = self.document.source_metadata.get("read_only_guard")
        if flag is not None:
            return bool(flag)
        if self.document.path is not None:
            if self._read_only_guards().is_guarded(self.document.path):
                return True
            # The file itself, not just the guard somebody switched on: a file
            # from a read-only share could be typed into for twenty minutes
            # and refuse at Ctrl+S, which is the worst moment to find out
            # (bad.md P2.12).
            from quill.core.file_access import is_read_only

            return is_read_only(self.document.path)
        return False

    def _refuse_edit_if_read_only(self) -> None:
        """Raise before a text-changing path touches a guarded document.

        Raising rather than returning is the point: the caller has not said
        anything yet, and an exception is the only way to stop it saying
        "Inserted snippet" about a snippet that was not inserted. The command
        registry (``CommandRegistry.set_read_only_refusal``) turns it into one sentence.
        """
        if getattr(self, "document", None) is None:
            return
        try:
            guarded = self._document_is_read_only()
        except AttributeError:  # a partial document stand-in has no guard to honour
            return
        if guarded:
            raise DocumentReadOnlyError()

    def announce_read_only_at_open(self) -> bool:
        """Say it once, at open, when the file cannot be saved back.

        True when it said something. Named rather than inlined so the open path
        reads as what it is, and so the sentence has one home in each editor.
        """
        from quill.core.file_access import READ_ONLY_NOTICE, is_read_only

        if not is_read_only(getattr(self.document, "path", None)):
            return False
        self._set_status(READ_ONLY_NOTICE)
        return True

    def _refresh_read_only_state(self) -> None:
        """Re-apply the persisted read-only guard to the active editor."""
        read_only = self._document_is_read_only()
        self.document.source_metadata["read_only_guard"] = read_only
        self._guarded_browse_text = None
        getattr(self.editor, "SetEditable", lambda _v: None)(not read_only)

    def toggle_read_only_guard(self) -> None:
        """Ctrl+Alt+Backspace: lock this document against edits, or unlock it.

        The caret, the selection, bookmarks and document notes are untouched:
        only typing and the commands that change text stop. The lock is
        remembered per file; when it cannot be written, the sentence says so
        rather than promising it will be there next time.
        """
        read_only = not self._document_is_read_only()
        self.document.source_metadata["read_only_guard"] = read_only
        self._guarded_browse_text = None
        set_editable = getattr(self.editor, "SetEditable", None)
        if callable(set_editable):
            set_editable(not read_only)
        reason = ""
        if self.document.path is not None:
            reason = self._read_only_guards().set(self.document.path, read_only)
        elif read_only:
            reason = "it has no file name yet"
        self._announce(toggle_sentence(read_only, saved=not reason, reason=reason))
