"""QuickInsertMixin -- pick an abbreviation by name, and save one from the clipboard.

Two commands that belong with abbreviations but not inside the expansion hot
path, so they live here rather than growing ``main_frame_abbreviations.py``
(GATE-11). Both are the editor's half of what Quill Inkwell offers system-wide,
over the same shared library.

Requires ``self.editor``, ``self.frame``, ``self.document``,
``self._abbreviation_library``, ``self._announce``, ``self._show_modal_dialog``,
``self._record_abbreviation_use``, and
``self._get_clipboard_text_for_abbreviation`` from the host frame.
"""

from __future__ import annotations


class QuickInsertMixin:
    def open_quick_insert(self) -> None:
        """Pick an abbreviation by name and insert its expansion at the caret.

        The way to use an abbreviation you have not memorised, and the only way
        to reach one whose trigger mode is "manual". The same picker Quill
        Inkwell opens, over the same library.
        """
        import wx

        from quill.core.abbreviations import resolve_expansion
        from quill.ui.quick_insert_dialog import QuickInsertDialog

        dlg = QuickInsertDialog(self.frame, self._abbreviation_library)
        result = self._show_modal_dialog(dlg.dialog, "Quick Insert")
        chosen = dlg.chosen
        dlg.close()
        if result != wx.ID_OK or chosen is None:
            return
        from quill.ui.fill_in_dialog import prompt_for_fields

        filled = prompt_for_fields(
            self.frame, chosen.expansion, self._show_modal_dialog, title=chosen.abbreviation
        )
        if filled is None:
            return
        text, cursor_offset, has_cursor = resolve_expansion(
            filled, self._get_clipboard_text_for_abbreviation()
        )
        caret = self.editor.GetInsertionPoint()
        document_text = self.editor.GetValue()
        new_text = document_text[:caret] + text + document_text[caret:]
        new_caret = caret + (cursor_offset if has_cursor else len(text))
        self._abbreviation_expansion_guard = True
        try:
            self.editor.ChangeValue(new_text)
            self.editor.SetInsertionPoint(new_caret)
            self.editor.SetSelection(new_caret, new_caret)
        finally:
            self._abbreviation_expansion_guard = False
        self.document.set_text(new_text)
        self._record_abbreviation_use(chosen.id)
        self._announce(f"Inserted {chosen.abbreviation}")

    def new_abbreviation_from_clipboard(self) -> None:
        """Save whatever is on the clipboard as a new abbreviation."""
        import uuid

        import wx

        from quill.core.abbreviations import Abbreviation, save_abbreviation_library
        from quill.ui.abbreviation_manager_dialog import _AbbreviationEditDialog

        text = self._get_clipboard_text_for_abbreviation()
        if not text.strip():
            self._announce("The clipboard has no text to save.")
            return
        entry = Abbreviation(id=str(uuid.uuid4()), abbreviation="", expansion=text)
        library = self._abbreviation_library
        dlg = _AbbreviationEditDialog(
            self.frame,
            entry,
            categories=sorted({a.category for a in library.abbreviations if a.category}),
        )
        if self._show_modal_dialog(dlg.dialog, "New Abbreviation") == wx.ID_OK and dlg.trigger_text:
            dlg.apply_to(entry)
            library.abbreviations.append(entry)
            library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
            save_abbreviation_library(library)
            self._announce(f"Saved {entry.abbreviation}")
        dlg.close()
