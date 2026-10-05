"""QUILL's half of inline notes: registration, menu rows and tab bookkeeping.

The commands themselves are shared with QUILL Lite
(:mod:`quill.ui.inline_notes_commands`); this mixin registers them under
QUILL's command ids, puts their rows on **Tools > Writing and Language**, and
keeps each tab's private notes. Default keys (all remappable in the Keymap
Editor), the same in both editors:

- ``notes.add_inline_note`` (Alt+Shift+I): note the current line or selection.
- ``notes.next_inline_note`` / ``notes.previous_inline_note`` (Alt+Shift+J /
  Alt+Shift+K): move to the next/previous note's text and say it.
- ``notes.speak_inline_note`` (Alt+Shift+H): say the note at the caret; press
  it again quickly (double-press) to edit or delete it.
- ``notes.delete_inline_note`` (Alt+Shift+Delete): delete the note at the caret.
- ``notes.list_inline_notes`` (Alt+Shift+Enter): every note in one window.

Private notes are persisted per document in an :class:`InlineNoteVault` so they
return when the file is reopened. The active document's notes live on its tab
(``tab.inline_notes``) and are aliased to ``self._inline_notes`` while it is
current. Notes written into the file need no bookkeeping: they are the text.
"""

from __future__ import annotations

from typing import Any

from quill.core.inline_notes import InlineNoteVault
from quill.ui.inline_notes_commands import InlineNotesCommandsMixin
from quill.ui.main_frame_editor_host import QuillEditorHostMixin

#: Command id, menu label, handler name -- in menu order. Delete and List carry
#: no access key: every letter in their names is taken in this menu, and a
#: duplicate would advertise a key that may not work (GATE-14).
_NOTE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("notes.add_inline_note", "&Add Inline Note...", "cmd_add_inline_note"),
    ("notes.next_inline_note", "Next Inline &Note", "cmd_next_inline_note"),
    ("notes.previous_inline_note", "Previous Inline No&te", "cmd_previous_inline_note"),
    ("notes.speak_inline_note", "Speak Inline Note (double to &edit)", "cmd_speak_inline_note"),
    ("notes.delete_inline_note", "Delete Inline Note...", "cmd_delete_inline_note"),
    ("notes.list_inline_notes", "List Inline Notes...", "cmd_list_inline_notes"),
)

_COMMAND_NAMES = {
    "notes.add_inline_note": "Add Inline Note",
    "notes.next_inline_note": "Next Inline Note",
    "notes.previous_inline_note": "Previous Inline Note",
    "notes.speak_inline_note": "Speak Inline Note (double-press to edit)",
    "notes.delete_inline_note": "Delete Inline Note",
    "notes.list_inline_notes": "List Inline Notes",
}


class InlineNotesMixin(QuillEditorHostMixin, InlineNotesCommandsMixin):
    _wx: Any
    frame: Any
    editor: Any
    document: Any

    def register_inline_note_commands(self) -> None:
        for command_id, _label, handler_name in _NOTE_ROWS:
            self.commands.register(
                command_id,
                _COMMAND_NAMES[command_id],
                getattr(self, handler_name),
                self._binding_for(command_id),
            )
        self.register_review_commands()  # main_frame_review: Toggle Task Done, Export HTML

    def _inline_note_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_inline_note_ids", None)
        if ids is None:
            import wx

            ids = {command_id: wx.NewIdRef() for command_id, _l, _h in _NOTE_ROWS}
            self._inline_note_ids = ids
        return ids

    def _append_inline_note_rows(self, menu: Any) -> None:
        """The six note rows, bound once (Tools > Writing and Language)."""
        import wx

        from quill.core.i18n import _

        ids = self._inline_note_menu_ids()
        for command_id, label, _handler in _NOTE_ROWS:
            menu.Append(ids[command_id], self._menu_label(_(label), command_id))
        if not getattr(self, "_inline_note_rows_wired", False):
            self._inline_note_rows_wired = True
            for command_id, _label, handler_name in _NOTE_ROWS:
                handler = getattr(self, handler_name)
                self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id])

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping.update(self._inline_note_menu_ids())
        return mapping

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

    # -- browse mode: N / Shift+N ----------------------------------------- #
    def _browse_inline_note(self, *, reverse: bool) -> None:
        """Browse mode's N and Shift+N: the next or previous note (QUILL only)."""
        self._go_to_inline_note(forward=not reverse)
