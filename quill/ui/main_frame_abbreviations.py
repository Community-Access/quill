"""AbbreviationsMixin — bare-word TextExpander expansion for MainFrame.

Extracted into a mixin so the abbreviation subsystem stays within GATE-11
module-size budgets. Every method on this mixin resolves through the MRO;
it assumes ``self.editor``, ``self.frame``, ``self.settings``, ``self.document``,
``self._announce``, ``self._set_status``, ``self._show_modal_dialog``, and
``self._refresh_statusbar`` are provided by MainFrame.
"""

from __future__ import annotations


class AbbreviationsMixin:
    def _init_abbreviations(self) -> None:
        from quill.core.abbreviations import load_abbreviation_library

        self._abbreviation_library = load_abbreviation_library()
        self._abbreviation_expansion_guard = False
        # (post_expansion_text, caret_after, token_start, original_abbr) or None
        self._pending_undo: tuple[str, int, int, str] | None = None

    # -- automatic expansion hook (called from _on_text_changed) --

    def _expand_abbreviation_if_match(self) -> bool:
        """Try to expand an abbreviation at the current cursor position.

        Returns True if an expansion was applied (caller skips _sync_editor_change).
        Also intercepts a backspace immediately after an expansion.
        """
        if self._pending_undo is not None and self._try_undo_expansion():
            return True
        if self.editor.GetSelection()[0] != self.editor.GetSelection()[1]:
            return False
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        clipboard_text = self._get_clipboard_text_for_abbreviation()
        from quill.core.abbreviations import try_expand

        match = try_expand(text, caret, self._abbreviation_library, clipboard_text)
        if match is None:
            return False
        before = text[: match.token_start]
        after = text[match.token_end :]  # includes the trigger char
        new_text = before + match.resolved_text + after
        new_caret = match.token_start + match.cursor_offset
        if not match.has_cursor:
            new_caret += 1  # step past the trigger char
        new_caret = max(0, min(new_caret, len(new_text)))
        self._abbreviation_expansion_guard = True
        try:
            self.editor.ChangeValue(new_text)
            self.editor.SetInsertionPoint(new_caret)
            self.editor.SetSelection(new_caret, new_caret)
        finally:
            self._abbreviation_expansion_guard = False
        self.document.set_text(new_text)
        original_abbr = text[match.token_start : match.token_end]
        self._pending_undo = (new_text, new_caret, match.token_start, original_abbr)
        self._play_abbreviation_sound()
        preview = match.resolved_text[:40] + ("..." if len(match.resolved_text) > 40 else "")
        self._announce(f"Expanded: {preview}")
        return True

    def _try_undo_expansion(self) -> bool:
        """Detect and handle a single backspace pressed right after an expansion.

        Returns True (and consumes the change) if the backspace-after-expansion
        logic fires; False if the pending state is stale and should be cleared.
        """
        stored_text, stored_caret, token_start, original_abbr = self._pending_undo  # type: ignore[misc]
        self._pending_undo = None
        current_text = self.editor.GetValue()
        current_caret = self.editor.GetInsertionPoint()
        # Single backspace: caret retreated by 1, that char was deleted.
        if current_caret != stored_caret - 1:
            return False
        expected = stored_text[: stored_caret - 1] + stored_text[stored_caret:]
        if current_text != expected:
            return False
        # Confirmed backspace immediately after expansion.
        behavior = str(getattr(self.settings, "abbreviation_backspace_behavior", "delete"))
        before = current_text[:token_start]
        after = current_text[current_caret:]
        if behavior == "revert":
            new_text = before + original_abbr + after
            new_caret = token_start + len(original_abbr)
            label = f"Reverted to: {original_abbr}"
        else:
            new_text = before + after
            new_caret = token_start
            label = "Expansion deleted"
        self._abbreviation_expansion_guard = True
        try:
            self.editor.ChangeValue(new_text)
            self.editor.SetInsertionPoint(new_caret)
            self.editor.SetSelection(new_caret, new_caret)
        finally:
            self._abbreviation_expansion_guard = False
        self.document.set_text(new_text)
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        post_sound(SoundEvent.ABBREVIATION_DELETED)
        self._announce(label)
        return True

    def _get_clipboard_text_for_abbreviation(self) -> str:
        try:
            import wx

            if wx.TheClipboard.Open():
                obj = wx.TextDataObject()
                got = wx.TheClipboard.GetData(obj)
                wx.TheClipboard.Close()
                return obj.GetText() if got else ""
        except Exception:  # noqa: BLE001
            pass
        return ""

    def _play_abbreviation_sound(self) -> None:
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import is_active, post_sound

        if is_active():
            post_sound(SoundEvent.ABBREVIATION_EXPANDED)
            return
        # Legacy per-event winsound path for users without a QSP configured.
        if not getattr(self.settings, "abbreviation_expansion_sound", False):
            return
        sound_path = getattr(self.settings, "abbreviation_expansion_sound_file", "")
        try:
            import winsound

            if sound_path:
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.MessageBeep(winsound.MB_OK)
        except Exception:  # noqa: BLE001
            pass

    # -- manual expand command --

    def expand_abbreviation_at_cursor(self) -> None:
        """Expand the word immediately before the cursor without needing a trigger char."""
        if not getattr(self.settings, "abbreviation_expansion", True):
            self._announce("Abbreviation expansion is disabled")
            return
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        if caret == 0:
            self._announce("No word before cursor")
            return
        padded = text[:caret] + " " + text[caret:]
        from quill.core.abbreviations import try_expand

        match = try_expand(padded, caret + 1, self._abbreviation_library)
        if match is None:
            self._announce("No abbreviation match")
            return
        before = text[: match.token_start]
        after = text[caret:]
        new_text = before + match.resolved_text + after
        new_caret = match.token_start + match.cursor_offset
        new_caret = max(0, min(new_caret, len(new_text)))
        self._abbreviation_expansion_guard = True
        try:
            self.editor.ChangeValue(new_text)
            self.editor.SetInsertionPoint(new_caret)
            self.editor.SetSelection(new_caret, new_caret)
        finally:
            self._abbreviation_expansion_guard = False
        self.document.set_text(new_text)
        self._play_abbreviation_sound()
        preview = match.resolved_text[:40] + ("..." if len(match.resolved_text) > 40 else "")
        self._announce(f"Expanded to: {preview}")

    # -- manager dialog --

    def open_abbreviation_manager(self) -> None:
        from quill.core.abbreviations import load_abbreviation_library
        from quill.ui.abbreviation_manager_dialog import AbbreviationManagerDialog

        dlg = AbbreviationManagerDialog(self.frame, self._abbreviation_library)
        self._show_modal_dialog(dlg.dialog, "Manage Abbreviations")
        self._abbreviation_library = load_abbreviation_library()
        dlg.close()
        self._set_status("Abbreviations updated")

    # -- toggle command (status bar + menu) --

    def toggle_abbreviation_expansion(self, enabled: bool | None = None) -> None:
        from quill.core.settings import save_settings

        current = getattr(self.settings, "abbreviation_expansion", True)
        if enabled is None:
            enabled = not current
        self.settings.abbreviation_expansion = enabled
        save_settings(self.settings)
        state = "on" if enabled else "off"
        self._announce(f"Abbreviation expansion {state}")
        self._set_status(f"Abbreviations {state}")
        self._refresh_statusbar()
