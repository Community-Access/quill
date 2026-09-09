"""What happens while you type: abbreviations, autocorrect, and the spell check.

Two features that watch the keystroke rather than the menu, and the only two
places in QuillLite where the app changes text the user did not ask it to
change. Both are therefore switchable areas, and one of them starts off.

**Abbreviations** (:mod:`quill.core.abbreviations`, QUILL's own engine and
QUILL's own manager dialog). Type ``addr`` and a space and get your address.
Expansion is a real accessibility feature rather than a typing convenience: it
turns a long, error-prone, character-by-character insertion into four
keystrokes, and the errors it removes are the ones that cost most to find again
by ear.

The library is **QuillLite's own** by default, in QuillLite's own data folder.
Preferences has a switch -- off by default -- that points it at QUILL's shared
``abbreviations.json`` instead, which is the one Inkwell and QUILL both use. That
is deliberately opt-in and not the default: Inkwell shares the library because
one library is its entire value, while QuillLite is offered as an alternative to
QUILL, and a machine that has never had QUILL installed must not grow a Quill
data folder because somebody opened a text file.

**Autocorrect** (:mod:`quill.core.autoformat`, QUILL's rules). Curly quotes, em
dashes from a double hyphen, a capital at the start of a sentence. It ships
**off** (:data:`quill.core.lite.features.DEFAULT_OFF`), because every one of
those is welcome in prose and actively wrong in a configuration file, a code
snippet or a CSV -- and QuillLite is used for all four. Turning it on is one
checkbox in View > Customize Features.

Neither runs in plain text mode by accident: both are keyed off ``EVT_CHAR``
after the character has landed, and both leave the text alone when their area is
off.

**Spell check** is the third thing watching the keystroke, and the only one that
never changes the text -- it schedules
:meth:`~quill.apps.lite_window_spelling.DocumentSpellingMixin.schedule_live_spell_check`
and nothing more. It is here rather than on ``EVT_TEXT`` so that a paste, which
is not typing, does not trigger a check of a word the user never typed.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.abbreviations import try_expand
from quill.core.autoformat import is_dash_merge, smart_quote_for

__all__ = ["DocumentTypingMixin"]

#: The characters autocorrect reacts to. Everything else is passed straight
#: through, so the common case costs one set membership test per keystroke.
_QUOTES = {'"', "'"}


class DocumentTypingMixin:
    """Abbreviation expansion and autocorrect, on the way through EVT_CHAR."""

    def _on_char(self, event: wx.KeyEvent) -> None:
        """Watch the keystroke. Almost always: let it through untouched.

        Bound to ``EVT_CHAR`` rather than ``EVT_TEXT`` because both features
        need to know *which* character arrived and to be able to refuse it --
        a smart quote replaces the straight one the user pressed, so the plain
        one must never be inserted in the first place.
        """
        code = event.GetUnicodeKey()
        typed = chr(code) if code else ""
        if typed and self.app.feature_enabled("autoformat") and self._autoformat(typed):
            return  # handled: the replacement went in instead of the keystroke
        event.Skip()
        # After the keystroke, on a timer: the check has to see the finished
        # word, and judging one the user is still typing would report every
        # word as wrong on its way to being right.
        self.schedule_live_spell_check()
        if typed and self.app.feature_enabled("abbreviations"):
            # After the character lands, not before: an abbreviation is
            # recognised by the trigger that follows it, so the trigger has to
            # be in the buffer for try_expand to see it.
            wx.CallAfter(self._maybe_expand)

    # ------------------------------------------------------------------ #
    # Autocorrect
    # ------------------------------------------------------------------ #

    def _autoformat(self, typed: str) -> bool:
        """Replace the keystroke where a rule applies. ``True`` when it did."""
        position = self.control.GetInsertionPoint()
        if position and self.control.GetSelection()[0] != self.control.GetSelection()[1]:
            return False  # a selection is a replacement, not a typed character
        text = self.control.GetValue()
        preceding = text[position - 1] if position else ""
        if typed in _QUOTES:
            self._insert_replacing(smart_quote_for(preceding, typed), back=0)
            return True
        if typed == "-" and is_dash_merge(preceding):
            # The second hyphen of "--" becomes an em dash, eating the first.
            self._insert_replacing("—", back=1)
            return True
        return False

    def _insert_replacing(self, text: str, *, back: int) -> None:
        """Put *text* in, having first removed *back* characters behind the caret."""
        position = self.control.GetInsertionPoint()
        if back:
            self.control.Remove(max(0, position - back), position)
        self.control.WriteText(text)
        self._set_modified(True)
        self._touch_status()

    # ------------------------------------------------------------------ #
    # Abbreviations
    # ------------------------------------------------------------------ #

    def _maybe_expand(self) -> None:
        """Expand the word before the caret if it is an abbreviation.

        Guarded end to end: an expansion that raises must not be able to eat a
        keystroke, and the clipboard provider is passed rather than the
        clipboard text so ``${clipboard}`` costs a clipboard open only on the
        rare expansion that actually uses it -- not once per keystroke.
        """
        library: Any = self.app.abbreviations
        if library is None:
            return
        try:
            text = self.control.GetValue()
            caret = self.control.GetInsertionPoint()
            match = try_expand(text, caret, library, clipboard_provider=self._clipboard_text)
        except Exception:  # noqa: BLE001 - expansion must never break typing
            return
        if match is None:
            return
        self.control.Replace(match.token_start, match.token_end, match.resolved_text)
        landing = match.token_start + (
            match.cursor_offset if match.has_cursor else len(match.resolved_text)
        )
        if match.trailing_space:
            self.control.WriteText(" ")
        self.control.SetInsertionPoint(min(landing, self.control.GetLastPosition()))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Expanded to {match.resolved_text.strip()[:60]}")

    def cmd_manage_abbreviations(self) -> None:
        """QUILL's own abbreviation manager, over whichever library is in use."""
        from quill.ui.abbreviation_manager_dialog import AbbreviationManagerDialog

        library = self.app.abbreviations
        if library is None:
            self._announce("Abbreviations are switched off in Customize Features")
            return
        from quill.ui.dialog_contract import show_modal_dialog

        dialog = AbbreviationManagerDialog(self, library)
        try:
            show_modal_dialog(dialog.dialog, "Manage Abbreviations")
        finally:
            dialog.close()
        # The dialog edits the library object in place; the write back is ours,
        # and the reload is what makes a second window see the same list.
        self.app.save_abbreviations()
        self.app.reload_abbreviations()
        self.control.SetFocus()
