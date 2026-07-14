"""MainFrame mixin for inline notes — sticky, content-anchored annotations.

Commands (default keys; all remappable in the Keymap Editor):
- ``notes.add_inline_note`` (Alt+Shift+I): note the current line or selection.
- ``notes.next_inline_note`` / ``notes.previous_inline_note`` (Alt+Shift+J / G):
  move the caret to the next/previous note's anchored text and announce it.
- ``notes.speak_inline_note`` (Alt+Shift+H): speak the note at the caret; press it
  again quickly (double-press) to open the note to view/edit/delete.

Notes are anchored to content (quote + context, see ``core.inline_notes``) so they
follow edits, and are persisted per document in an :class:`InlineNoteVault` so they
return when the file is reopened. The active document's notes live on its tab
(``tab.inline_notes``) and are aliased to ``self._inline_notes`` while it is current.
"""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

from quill.core.inline_notes import (
    InlineNoteVault,
    make_inline_note,
    note_at,
    resolved_notes,
)

# Two presses of the speak key within this window opens the note for editing.
_DOUBLE_PRESS_SECONDS = 0.6


class InlineNotesMixin:
    _wx: Any
    frame: Any
    editor: Any
    document: Any

    def register_inline_note_commands(self) -> None:
        specs: tuple[tuple[str, str, object], ...] = (
            ("notes.add_inline_note", "Add Inline Note", self.add_inline_note),
            ("notes.next_inline_note", "Next Inline Note", self.next_inline_note),
            ("notes.previous_inline_note", "Previous Inline Note", self.previous_inline_note),
            (
                "notes.speak_inline_note",
                "Speak Inline Note (double-press to edit)",
                self.speak_inline_note,
            ),
        )
        for command_id, label, handler in specs:
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    # -- persistence / lifecycle ------------------------------------------- #
    def _inline_vault(self) -> InlineNoteVault:
        vault = getattr(self, "_inline_note_vault", None)
        if vault is None:
            try:
                vault = InlineNoteVault.load()
            except Exception:  # noqa: BLE001 - best-effort persistence
                vault = InlineNoteVault()
            self._inline_note_vault = vault
        return vault

    def _load_inline_notes_for(self, tab: object) -> None:
        """Load a document's saved inline notes into its tab (called on open)."""
        key = InlineNoteVault.key_for(getattr(tab.document, "path", None))
        try:
            tab.inline_notes = self._inline_vault().notes_for(key)
        except Exception:  # noqa: BLE001
            tab.inline_notes = []

    def _save_inline_notes(self) -> None:
        """Persist the active document's notes to its tab and (if saved) to disk."""
        tab = self._active_tab()
        if tab is not None:
            tab.inline_notes = list(self._inline_notes)
        key = InlineNoteVault.key_for(getattr(getattr(self, "document", None), "path", None))
        if key:
            try:
                self._inline_vault().set_notes(key, self._inline_notes)
            except Exception:  # noqa: BLE001
                pass

    # -- commands ---------------------------------------------------------- #
    def add_inline_note(self) -> None:
        from quill.ui.inline_note_dialog import show_inline_note_dialog

        editor = getattr(self, "editor", None)
        if editor is None:
            return
        try:
            start, end = editor.GetSelection()
            doc_text = editor.GetValue()
        except Exception:  # noqa: BLE001
            return
        action, body = show_inline_note_dialog(
            self._wx, self.frame, self._show_modal_dialog, title="Add Inline Note"
        )
        if action != "save" or not body.strip():
            self._set_status("Add inline note cancelled")
            return
        note = make_inline_note(body, doc_text, int(start), int(end))
        self._inline_notes.append(note)
        self._save_inline_notes()
        anchor = note.quote.strip().splitlines()[0] if note.quote.strip() else "this line"
        if len(anchor) > 40:
            anchor = anchor[:39] + "…"
        self._set_status_quiet(f'Inline note added on "{anchor}"')
        self._announce("Inline note added.")

    def next_inline_note(self) -> None:
        self._go_to_inline_note(forward=True)

    def previous_inline_note(self) -> None:
        self._go_to_inline_note(forward=False)

    def _go_to_inline_note(self, *, forward: bool) -> None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        doc_text = editor.GetValue()
        located = resolved_notes(doc_text, self._inline_notes)
        if not located:
            self._set_status("No inline notes in this document")
            return
        caret = editor.GetInsertionPoint()
        order = located if forward else list(reversed(located))
        chosen = None
        for note, start, _end in order:
            if (forward and start > caret) or (not forward and start < caret):
                chosen = (note, start)
                break
        if chosen is None:  # wrap around
            note, start, _end = order[0]
            chosen = (note, start)
        note, start = chosen
        index = next(i for i, (n, _s, _e) in enumerate(located) if n.note_id == note.note_id)
        editor.SetInsertionPoint(start)
        show = getattr(editor, "ShowPosition", None)
        if callable(show):
            show(start)
        editor.SetFocus()
        # _set_status already speaks; identical _announce would double-speak (#728).
        self._set_status(f"Inline note {index + 1} of {len(located)}: {note.summary()}")

    def speak_inline_note(self) -> None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        note = note_at(editor.GetValue(), self._inline_notes, editor.GetInsertionPoint())
        if note is None:
            self._set_status("No inline notes in this document")
            return
        now = time.monotonic()
        last = getattr(self, "_inline_note_speak_last", None)
        if last is not None and last[0] == note.note_id and (now - last[1]) < _DOUBLE_PRESS_SECONDS:
            self._inline_note_speak_last = None
            self._edit_inline_note(note)
            return
        self._inline_note_speak_last = (note.note_id, now)
        # Quiet status (summary) + spoken full text, so the note is read aloud
        # without the status line double-speaking it (#728).
        self._set_status_quiet(f"Inline note: {note.summary()}")
        self._announce(f"Inline note: {note.text}")

    def _edit_inline_note(self, note: object) -> None:
        from quill.ui.inline_note_dialog import show_inline_note_dialog

        action, body = show_inline_note_dialog(
            self._wx,
            self.frame,
            self._show_modal_dialog,
            title="Edit Inline Note",
            initial=note.text,
            allow_delete=True,
        )
        if action == "cancel":
            return
        if action == "delete":
            self._inline_notes = [n for n in self._inline_notes if n.note_id != note.note_id]
            self._save_inline_notes()
            self._set_status("Inline note deleted")  # _set_status speaks (#728)
            return
        self._inline_notes = [
            replace(n, text=body) if n.note_id == note.note_id else n for n in self._inline_notes
        ]
        self._save_inline_notes()
        self._set_status("Inline note updated")  # _set_status speaks (#728)
