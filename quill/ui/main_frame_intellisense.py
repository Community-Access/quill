"""Intellisense / word-prediction popup behaviour for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``IntellisensePopupMixin`` and every method resolves identically through the
MRO; the methods reference instance state and sibling methods via ``self``
exactly as before.
"""

from __future__ import annotations

from quill.core.intellisense import build_intellisense_suggestions, collect_document_words
from quill.platform.sr_announce import announce


class IntellisensePopupMixin:
    def _show_intellisense_popup(self, *, manual: bool) -> bool:
        popup = getattr(self, "_intellisense_popup", None)
        if popup is None:
            return False
        if not manual and not getattr(self.settings, "intellisense_as_you_type", False):
            if popup.is_visible():
                self._hide_intellisense_popup()
            return False
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        dictionary = self._spell_dictionary() | collect_document_words(text)
        context, suggestions = build_intellisense_suggestions(
            text,
            cursor,
            dictionary,
            limit=8,
        )
        if not suggestions:
            if popup.is_visible():
                self._hide_intellisense_popup()
            self._intellisense_context = context
            self._intellisense_fragment_text = context.fragment if context is not None else ""
            self._intellisense_suggestions = []
            return False
        if not manual and context is not None and len(context.fragment.strip()) < 2:
            if self._intellisense_popup.is_visible():
                self._hide_intellisense_popup()
            return False
        self._intellisense_context = context
        self._intellisense_fragment_text = context.fragment if context is not None else ""
        self._intellisense_suggestions = suggestions
        status = f"{len(suggestions)} prediction(s). {suggestions[0].label}"
        was_visible = popup.is_visible()
        popup.update(suggestions, status)
        if not was_visible:
            editor_pos = self.editor.GetScreenPosition()
            popup.show((editor_pos.x + 20, editor_pos.y + 40))
            announce(status)
        return True

    def _refresh_intellisense_popup(self) -> None:
        if self._intellisense_guard:
            return
        popup = getattr(self, "_intellisense_popup", None)
        popup_visible = popup is not None and popup.is_visible()
        if not popup_visible and not getattr(self.settings, "intellisense_as_you_type", False):
            return
        self._show_intellisense_popup(manual=popup_visible)

    def _hide_intellisense_popup(self) -> None:
        popup = getattr(self, "_intellisense_popup", None)
        if popup is not None:
            popup.hide()
        self._intellisense_context = None
        self._intellisense_fragment_text = ""
        self._intellisense_suggestions = []

    def _dismiss_intellisense_popup(self) -> None:
        """Cancel the prediction popup and return focus to the editor.

        Used when the listbox itself has focus (Escape), so the user is never
        stranded in the floating window."""
        self._hide_intellisense_popup()
        if self.editor is not None:
            self.editor.SetFocus()
        self._set_status("Word prediction dismissed")

    def _apply_intellisense_selection(self) -> bool:
        popup = getattr(self, "_intellisense_popup", None)
        context = getattr(self, "_intellisense_context", None)
        if popup is None or context is None:
            return False
        suggestion = popup.selected_suggestion()
        if suggestion is None:
            return False
        self._intellisense_guard = True
        try:
            self.editor.Replace(
                context.replacement_start,
                context.replacement_end,
                suggestion.inserted_text,
            )
            caret = context.replacement_start + suggestion.caret_offset
            caret = max(0, min(caret, len(self.editor.GetValue())))
            self.editor.SetInsertionPoint(caret)
            self.editor.SetSelection(caret, caret)
        finally:
            self._intellisense_guard = False
        self._hide_intellisense_popup()
        # Return focus to the editor in case the listbox itself held focus
        # (e.g. the user Tabbed or clicked into the floating window).
        if self.editor is not None:
            self.editor.SetFocus()
        self._set_status(f'Inserted prediction "{suggestion.label}".')
        return True

    def _handle_intellisense_key_down(self, event: object) -> bool:
        wx = self._wx
        # The manual word-prediction trigger is the edit.word_prediction command
        # (Ctrl+. by default) via show_word_prediction(). Ctrl+Space is left free
        # for edit.select_chunk per keymap §4.22, so it is intentionally not
        # intercepted here.
        popup = getattr(self, "_intellisense_popup", None)
        if popup is None or not popup.is_visible():
            return False
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            self._hide_intellisense_popup()
            return True
        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            if self._apply_intellisense_selection():
                return True
            return False
        if key_code == wx.WXK_UP:
            popup.set_selection(popup.selection_index() - 1)
            selection = popup.selected_suggestion()
            if selection is not None:
                announce(selection.label)
            return True
        if key_code == wx.WXK_DOWN:
            popup.set_selection(popup.selection_index() + 1)
            selection = popup.selected_suggestion()
            if selection is not None:
                announce(selection.label)
            return True
        return False
