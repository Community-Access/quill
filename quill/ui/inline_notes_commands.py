"""Inline notes, shared by QUILL and QUILL Lite.

Six commands on the same chords in both editors (family rule 2: the command
both products have keeps the chord):

* **Add Inline Note** ``Alt+Shift+I`` -- on the selection, or the caret's line.
* **Next / Previous Inline Note** ``Alt+Shift+J`` / ``Alt+Shift+K`` -- wrap.
* **Speak Inline Note** ``Alt+Shift+H`` -- pressed twice quickly, it edits.
* **Delete Inline Note** ``Alt+Shift+Delete`` -- after a Yes/No naming it.
* **List Inline Notes** ``Alt+Shift+Enter`` -- every note in one window
  (:mod:`quill.ui.inline_notes_list_dialog`).

A note is one of two kinds. A **private** note lives in a sidecar
(``inline_notes.json`` in the app's data folder) anchored to its text by quote
and context (:mod:`quill.core.inline_notes`), and works in every format. A note
**in the file**, for Markdown and HTML, is a ``<!-- quill-note: ... -->``
comment after the text it is about (:mod:`quill.core.inline_notes_file`), so a
colleague or an AI assistant reading the file sees it; adding, editing and
deleting one is an ordinary edit, so Ctrl+Z takes it back. Every command treats
both kinds the same, through one list (:mod:`quill.core.inline_notes_list`).

The ideas this module adds -- the list, the "Note on" line, notes in the file,
Delete -- are PlanCake's (Andre of Oire Software). The editor-specific parts
are the hooks in :class:`~quill.ui.editor_host.EditorHostMixin`; QUILL keeps its
tab bookkeeping in :mod:`quill.ui.main_frame_inline_notes`.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from quill.core.inline_notes import (
    INLINE_NOTES_FILENAME,
    InlineNote,
    InlineNoteVault,
    line_bounds,
    make_inline_note,
)
from quill.core.inline_notes_file import (
    IN_FILE_KINDS,
    insert_file_note,
    parse_file_notes,
    removal_span,
    remove_all_file_notes,
    replace_file_note,
)
from quill.core.inline_notes_list import (
    ORPHANED,
    NoteRow,
    collect_rows,
    first_sentence,
    row_at,
    rows_as_json,
    rows_as_markdown,
    rows_as_text,
)
from quill.core.storage import write_text_atomic
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.editor_host import EditorHostMixin

__all__ = ["NO_NOTES", "InlineNotesCommandsMixin"]

#: Two presses of the speak key within this window open the note for editing.
_DOUBLE_PRESS_SECONDS = 0.6

#: Said by every command when there is nothing to act on.
NO_NOTES = "No inline notes in this document"


class InlineNotesCommandsMixin(EditorHostMixin):
    """The inline-note commands. Mixed into both editors' document windows."""

    # ------------------------------------------------------------------ #
    # Storage: the private sidecar (QUILL overrides these for its tabs)
    # ------------------------------------------------------------------ #

    def _inline_vault(self) -> InlineNoteVault:
        vault = getattr(self, "_inline_note_vault", None)
        if vault is None:
            try:
                vault = InlineNoteVault.load(self._host_data_dir() / INLINE_NOTES_FILENAME)
            except Exception:  # noqa: BLE001 - best-effort persistence
                vault = InlineNoteVault(path=self._host_data_dir() / INLINE_NOTES_FILENAME)
            self._inline_note_vault = vault
        return vault

    def _sidecar_notes(self) -> list[InlineNote]:
        notes = getattr(self, "_inline_notes", None)
        if notes is None:
            key = InlineNoteVault.key_for(self._host_path())
            try:
                notes = self._inline_vault().notes_for(key)
            except Exception:  # noqa: BLE001
                notes = []
            self._inline_notes = notes
        return notes

    def _save_inline_notes(self) -> None:
        key = InlineNoteVault.key_for(self._host_path())
        if key:
            try:
                self._inline_vault().set_notes(key, list(self._sidecar_notes()))
            except Exception:  # noqa: BLE001 - persistence is best-effort
                pass

    def _set_sidecar_notes(self, notes: list[InlineNote]) -> None:
        self._inline_notes = list(notes)
        self._save_inline_notes()

    # ------------------------------------------------------------------ #
    # Where a new note goes
    # ------------------------------------------------------------------ #

    def _host_doc_key(self) -> int:
        """Identifies the document for the per-document "in the file" choice."""
        return id(self)

    def _notes_in_file_default(self, text: str, kind: str) -> bool:
        """This document's last choice, else yes if it already has notes in it,
        else the setting (off unless changed)."""
        remembered = getattr(self, "_notes_in_file_choices", {}).get(self._host_doc_key())
        if remembered is not None:
            return bool(remembered)
        if kind in IN_FILE_KINDS and parse_file_notes(text, kind):
            return True
        return bool(getattr(self._host_settings(), "inline_notes_in_file", False))

    def _remember_notes_in_file(self, choice: bool) -> None:
        choices = getattr(self, "_notes_in_file_choices", None)
        if choices is None:
            choices = {}
            self._notes_in_file_choices = choices
        choices[self._host_doc_key()] = bool(choice)

    # ------------------------------------------------------------------ #
    # The list every command reads
    # ------------------------------------------------------------------ #

    def _note_rows(self) -> list[NoteRow]:
        text = self._host_control().GetValue()
        return collect_rows(text, list(self._sidecar_notes()), self._host_kind())

    def _apply_document_edit(self, start: int, end: int, replacement: str) -> None:
        replace_as_one_undo(self._host_control(), start, end, replacement)
        self._host_after_edit()

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #

    def cmd_add_inline_note(self) -> None:
        """Alt+Shift+I: a note on the selection, or on the caret's line."""
        from quill.ui.inline_note_dialog import show_inline_note_dialog

        control = self._host_control()
        text = control.GetValue()
        start, end = (int(v) for v in control.GetSelection())
        if start > end:
            start, end = end, start
        a_start, a_end = (start, end) if start != end else line_bounds(text, start)
        kind = self._host_kind()
        available = kind in IN_FILE_KINDS and not self._host_read_only()
        import wx

        action, body, in_file = show_inline_note_dialog(
            wx,
            self._host_parent(),
            self._host_show_modal,
            title="Add Inline Note",
            note_on=first_sentence(text[a_start:a_end]) or "a blank line",
            in_file=self._notes_in_file_default(text, kind),
            in_file_available=available,
        )
        if action != "save" or not body.strip():
            self._host_say("Add inline note cancelled")
            return
        if available:
            self._remember_notes_in_file(in_file)
        if in_file and available:
            offset, insertion = insert_file_note(text, end, body, kind)
            self._apply_document_edit(offset, offset, insertion)
            shift = len(insertion) if offset <= start else 0
            control.SetSelection(start + shift, end + shift)
            self._host_say("Inline note written into the file.")
            return
        notes = list(self._sidecar_notes())
        notes.append(make_inline_note(body, text, start, end))
        self._set_sidecar_notes(notes)
        self._host_say("Inline note added.")

    def cmd_next_inline_note(self) -> None:
        """Alt+Shift+J: the next note's text, wrapping at the end."""
        self._go_to_inline_note(forward=True)

    def cmd_previous_inline_note(self) -> None:
        """Alt+Shift+K: the previous note's text, wrapping at the start."""
        self._go_to_inline_note(forward=False)

    def _go_to_inline_note(self, *, forward: bool) -> None:
        located = [row for row in self._note_rows() if row.position is not None]
        if not located:
            self._host_say(NO_NOTES)
            return
        caret = int(self._host_control().GetInsertionPoint())
        order = located if forward else list(reversed(located))
        chosen = next(
            (
                row
                for row in order
                if (forward and (row.position or 0) > caret)
                or (not forward and (row.position or 0) < caret)
            ),
            order[0],  # wrap around
        )
        index = located.index(chosen)
        self._move_to_row(chosen)
        self._host_say(f"Inline note {index + 1} of {len(located)}: {chosen.summary()}")

    def _move_to_row(self, row: NoteRow) -> None:
        control = self._host_control()
        position = int(row.position or 0)
        control.SetInsertionPoint(position)
        show = getattr(control, "ShowPosition", None)
        if callable(show):
            show(position)

    def cmd_speak_inline_note(self) -> None:
        """Alt+Shift+H: say the note at the caret; twice quickly to edit it."""
        rows = self._note_rows()
        row = row_at(rows, int(self._host_control().GetInsertionPoint()))
        if row is None:
            self._host_say(NO_NOTES)
            return
        now = time.monotonic()
        last = getattr(self, "_inline_note_speak_last", None)
        if last is not None and last[0] == row.note_id and (now - last[1]) < _DOUBLE_PRESS_SECONDS:
            self._inline_note_speak_last = None
            self._edit_note_row(row)
            return
        self._inline_note_speak_last = (row.note_id, now)
        self._host_say(f"Inline note: {row.text}")

    def cmd_delete_inline_note(self) -> None:
        """Alt+Shift+Delete: delete the note at the caret, after asking."""
        row = row_at(self._note_rows(), int(self._host_control().GetInsertionPoint()))
        if row is None:
            self._host_say(NO_NOTES)
            return
        if self._confirm_and_delete(row):
            self._host_say("Inline note deleted.")

    def cmd_list_inline_notes(self) -> None:
        """Alt+Shift+Enter: every note in one window."""
        import wx

        from quill.ui.inline_notes_list_dialog import NotesListHost, show_inline_notes_list

        if not self._note_rows():
            self._host_say(NO_NOTES)
            return
        host = NotesListHost(
            rows=self._note_rows,
            edit=self._edit_note_row,
            delete=self._delete_from_list,
            remove_all=self._remove_all_notes,
            copy_all=self._copy_all_notes,
            export=self._export_notes,
        )
        row = show_inline_notes_list(wx, self._host_parent(), self._host_show_modal, host)
        if row is None:
            return
        if row.orphaned:
            self._host_say(f"Nothing to go to: {ORPHANED}.")
            return
        self._move_to_row(row)

    # ------------------------------------------------------------------ #
    # Edit, delete, remove all, copy, export
    # ------------------------------------------------------------------ #

    def _current_file_note(self, row: NoteRow) -> Any:
        """*row*'s comment as it is in the text now, or ``None`` if it has gone."""
        if row.file_note is None:
            return None
        text = self._host_control().GetValue()
        for note in parse_file_notes(text, self._host_kind()):
            if note.start == row.file_note.start and note.text == row.file_note.text:
                return note
        return None

    def _edit_note_row(self, row: NoteRow) -> None:
        import wx

        from quill.ui.inline_note_dialog import show_inline_note_dialog

        action, body, _in_file = show_inline_note_dialog(
            wx,
            self._host_parent(),
            self._host_show_modal,
            title="Edit Inline Note",
            initial=row.text,
            allow_delete=True,
            note_on=row.on_label(),
        )
        if action == "cancel":
            return
        if action == "delete":
            if self._delete_row(row):
                self._host_say("Inline note deleted.")
            return
        if not body.strip():
            self._host_say("A note cannot be empty. Use Delete to remove it.")
            return
        if row.sidecar is not None:
            self._set_sidecar_notes([
                replace(n, text=body) if n.note_id == row.note_id else n
                for n in self._sidecar_notes()
            ])
        else:
            note = self._current_file_note(row)
            if note is None:
                self._host_say("That note is no longer in the document.")
                return
            start, end, replacement = replace_file_note(self._host_control().GetValue(), note, body)
            self._apply_document_edit(start, end, replacement)
        self._host_say("Inline note updated.")

    def _delete_row(self, row: NoteRow) -> bool:
        if row.sidecar is not None:
            self._set_sidecar_notes([n for n in self._sidecar_notes() if n.note_id != row.note_id])
            return True
        note = self._current_file_note(row)
        if note is None:
            return False
        start, end = removal_span(self._host_control().GetValue(), note)
        self._apply_document_edit(start, end, "")
        return True

    def _confirm_and_delete(self, row: NoteRow) -> bool:
        if not self._host_ask_yes_no(
            f'Delete the note "{row.summary()}"? The text it is on is not changed.',
            "Delete Inline Note",
        ):
            return False
        return self._delete_row(row)

    def _delete_from_list(self, row: NoteRow) -> bool:
        deleted = self._confirm_and_delete(row)
        if deleted:
            self._host_say("Inline note deleted.")
        return deleted

    def _remove_all_notes(self) -> int:
        rows = self._note_rows()
        count = len(rows)
        if not count:
            return 0
        noun = "note" if count == 1 else "notes"
        if not self._host_ask_yes_no(
            f"Remove all {count} {noun} from this document? The text they are on is not changed.",
            "Remove All Inline Notes",
        ):
            return 0
        self._set_sidecar_notes([])
        kind = self._host_kind()
        if kind in IN_FILE_KINDS:
            from quill.core.selection import changed_span

            text = self._host_control().GetValue()
            cleared, removed = remove_all_file_notes(text, kind)
            if removed:
                start, end, replacement = changed_span(text, cleared)
                self._apply_document_edit(start, end, replacement)
        self._host_say(f"{count} {noun} removed")
        return count

    def _host_copy_text(self, text: str) -> bool:
        setter = getattr(self, "_set_clipboard_text", None)
        if callable(setter):
            return bool(setter(text))
        import wx

        if not wx.TheClipboard.Open():
            return False
        try:
            return bool(wx.TheClipboard.SetData(wx.TextDataObject(text)))
        finally:
            wx.TheClipboard.Close()

    def _copy_all_notes(self, rows: list[NoteRow]) -> None:
        if self._host_copy_text(rows_as_text(rows)):
            self._host_say("Notes copied")
        else:
            self._host_say("Could not open the clipboard")

    def _export_notes(self, rows: list[NoteRow]) -> None:
        import wx

        title = self._host_title()
        path = self._host_path()
        with wx.FileDialog(
            self._host_parent(),
            "Export Inline Notes",
            defaultDir=str(path.parent) if path is not None else "",
            defaultFile=f"{title} notes.md",
            wildcard="Markdown (*.md)|*.md|JSON (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._host_show_modal(dialog, "Export Inline Notes") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
            as_json = dialog.GetFilterIndex() == 1 or target.suffix.lower() == ".json"
        if as_json:
            target = target.with_suffix(".json")
            body = rows_as_json(rows, str(path) if path is not None else title)
        else:
            if not target.suffix:
                target = target.with_suffix(".md")
            body = rows_as_markdown(rows, title)
        try:
            write_text_atomic(target, body)
        except OSError as error:
            self._host_say(f"Could not export the notes: {error.strerror or error}")
            return
        noun = "note" if len(rows) == 1 else "notes"
        self._host_say(f"Exported {len(rows)} {noun} to {target.name}")
