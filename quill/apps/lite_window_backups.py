r"""Earlier Versions: reading back one of the dated copies kept on every save.

Split out of :mod:`quill.apps.lite_window_tools` under GATE-11, and the line is
clean: that module reshapes the text in front of you, and this one goes and
fetches an older copy of it.

QuillLite has written these since backups shipped and offered no way to read
one: the files were correct, correctly named, and reachable only by knowing that
``%LOCALAPPDATA%\QuillLite\backups`` exists and which of the hashed folders was
yours. A safety net nobody can reach is not a safety net.
"""

from __future__ import annotations

from quill.apps.lite_dialogs import choose_from_rows
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentBackupsMixin"]


class DocumentBackupsMixin:
    """Earlier Versions, and the two things it can do with one."""

    # ------------------------------------------------------------------ #
    # Earlier versions of this file
    # ------------------------------------------------------------------ #

    def cmd_browse_backups(self) -> None:
        """List the dated copies kept on every save, and put one back.

        QuillLite has written these since backups shipped and offered no way to
        read one: the files were correct, correctly named, and reachable only by
        knowing that ``%LOCALAPPDATA%\\QuillLite\\backups`` exists and which of
        the hashed folders was yours. A safety net nobody can reach is not a
        safety net, and this is the half that was missing.

        Two verbs, because restoring in place and looking first are different
        needs and only one of them is safe when you are not sure:

        * **Restore** replaces this document's text. It is undoable with Ctrl+Z,
          and it does not save -- so the file on disk is untouched until you
          decide, which means a restore chosen by mistake costs one keystroke.
        * **Open a Copy** puts the old version in a new untitled window and
          leaves this one alone. That is the one to use when the question is
          "what did this say yesterday" rather than "put yesterday back".

        The rows are the shared phrasing
        (:func:`quill.core.version_history.version_label`), so a version reads
        the same here as in QUILL's own Restore Previous Version.
        """
        if not self.app.feature_enabled("backups"):
            self._announce(
                "Backups are switched off. Turn them on in Tools, Customize Features, "
                "and QuillLite will keep a dated copy of this file on every save."
            )
            return
        if self.path is None:
            self._announce("Save this document once and its earlier versions are kept from then on")
            return
        from quill.core.lite.backups import backup_saved_at, list_backups, read_backup
        from quill.core.metrics import compute_document_stats
        from quill.core.version_history import version_label

        rows: list[tuple[object, str]] = []
        for backup in list_backups(self.path):
            saved = backup_saved_at(backup)
            text = read_backup(backup)
            if saved is None or text is None:
                continue  # not one of ours, or gone since the list was built
            words = compute_document_stats(text).words
            rows.append((backup, version_label(saved, words=words)))
        if not rows:
            self._announce(f"No earlier versions of {self.path.name} yet")
            return
        chosen = choose_from_rows(
            self,
            title="Earlier Versions",
            label=f"&Earlier versions of {self.path.name}, newest first:",
            help_text=(
                "Dated copies of this file, one for each time you saved it. Restore "
                "replaces the text in this window, which you can undo and which does "
                "not write to the file until you save. Open a Copy puts the old "
                "version in a new window and leaves this one alone."
            )
            + (
                # Said, because it is a loss and it is not obvious. A backup
                # stores GetValue(), which is the text and none of the runs, so
                # restoring one into a rich document replaces formatted text
                # with flat text. The dialog offered the rows and said nothing
                # (bad.md F7); the honest answer is to warn rather than to stop
                # -- the text is still the thing somebody came back for.
                " These are copies of the text only: restoring one into this "
                "rich text document keeps the words and loses the formatting."
                if self.editor.mode == RICH
                else ""
            ),
            rows=rows,
            extra_button="Open a &Copy",
        )
        if chosen is None:
            self.control.SetFocus()
            return
        backup, action = chosen
        text = read_backup(backup)
        if text is None:
            self._announce("That version could not be read; it may have been removed")
            self.control.SetFocus()
            return
        if action == "copy":
            self._open_backup_copy(text)
            return
        self._restore_backup(text)

    def _open_backup_copy(self, text: str) -> None:
        """Put an old version in a new untitled window; this document is untouched."""
        window = self.app.new_window(self.editor.mode)
        window.control.SetValue(text)
        window._set_modified(True)
        window._touch_status()
        window._announce("Opened that version as a new untitled document")

    def _restore_backup(self, text: str) -> None:
        """Replace this document's text with an old version, undoably.

        ``Replace`` over the whole range rather than ``SetValue`` on purpose:
        it goes on the control's undo stack, so Ctrl+Z takes the restore back.
        Nothing is written to disk, and the announcement says so -- somebody who
        has just replaced their document needs to hear that they can still
        change their mind.
        """
        replace_as_one_undo(self.control, 0, self.control.GetLastPosition(), text)
        self.control.SetInsertionPoint(0)
        self._set_modified(True)
        self._touch_status()
        self._announce(
            "Restored that version. Nothing is written until you save, and Control Z undoes it."
        )
