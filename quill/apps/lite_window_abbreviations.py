"""Abbreviations in a QUILL Lite document: expansion as you type, the gallery, the manager.

Split out of :mod:`quill.apps.lite_window_typing` (GATE-11) when that module
gained AutoCorrect and Enter-in-a-list and reached its line cap. The cut is a
real seam: everything here is about the abbreviation *library* -- matching a
trigger, picking a snippet, editing the list -- while the typing module is
about what a keystroke does. :class:`~quill.apps.lite_window_typing.DocumentTypingMixin`
inherits this, so every window and every test stub that had the one still has
both.

**Abbreviations** (:mod:`quill.core.abbreviations`, QUILL's own engine and
QUILL's own manager dialog). Type ``addr`` and a space and get your address.
The library is QUILL Lite's own by default, in QUILL Lite's own data folder,
unless Preferences says share QUILL's. Entries in the AutoCorrect category are
misspelling corrections rather than abbreviations, and never expand here
(:mod:`quill.core.autocorrect` uses them instead).
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.abbreviations import is_trigger_char, try_expand
from quill.core.sound_events import SoundEvent
from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["DocumentAbbreviationsMixin"]


class DocumentAbbreviationsMixin:
    """Abbreviation expansion, the snippet gallery and the abbreviation manager."""

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
            caret = self.control.GetInsertionPoint()
            # An abbreviation is recognised by the character that follows it, so
            # a keystroke that is not a trigger cannot possibly expand anything.
            # Asked first, and asked of one character, because the answer is no
            # for every letter anybody types and the alternative was reading the
            # whole document to find that out (bad.md T1).
            if caret < 2 or not is_trigger_char(self.control.GetRange(caret - 1, caret)):
                return
            text = self.control.GetValue()
            match = try_expand(text, caret, library, clipboard_provider=self._clipboard_text)
        except Exception:  # noqa: BLE001 - expansion must never break typing
            return
        if match is None:
            return
        # An expansion is the app typing several words on your behalf, which is
        # the largest thing that happens in this editor without anybody pressing
        # a key for it -- and a screen reader says nothing at all, because no
        # focus moved and no control was named.
        self._cue(SoundEvent.ABBREVIATION_EXPANDED)
        replace_as_one_undo(self.control, match.token_start, match.token_end, match.resolved_text)
        landing = match.token_start + (
            match.cursor_offset if match.has_cursor else len(match.resolved_text)
        )
        if match.trailing_space:
            self.control.WriteText(" ")
        self.control.SetInsertionPoint(min(landing, self.control.GetLastPosition()))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Expanded to {match.resolved_text.strip()[:60]}")

    def cmd_toggle_abbreviations(self) -> None:
        """Alt+Shift+A: expansion on or off, without opening a dialog.

        The same switch Customize Features carries, on a key, because this is
        the one feature that acts *while you type*: the moment you want it off
        is the moment it has just expanded something you meant to keep, and
        three keystrokes of dialog in that moment is three too many.

        Everything the area owns follows -- the library is loaded or dropped and
        the menus are rebuilt -- so turning it off here really does stop the
        expansion rather than only stopping the menu item.
        """
        features = self.app.features
        if features is None:  # pragma: no cover - only before the app has loaded
            return
        enabled = self.app.feature_enabled("abbreviations")
        features.set_enabled("abbreviations", not enabled)
        self.app.save_features()
        self.app.reload_abbreviations()
        # After this event, not during it: the menu bar being rebuilt is the one
        # this command was just chosen from, and wxMSW does not survive having
        # a menu deleted while it is still dispatching that menu's event.
        wx.CallAfter(self.app.rebuild_all_menus)
        self._announce("Abbreviations off" if enabled else "Abbreviations on")

    def cmd_snippet_gallery(self) -> None:
        """Ctrl+Alt+Shift+Home: pick a snippet from a list and put it in.

        The half QUILL Lite did not have. Abbreviations expand when you *type the
        trigger*, which is perfect for the six you use daily and useless for the
        fortieth one, whose trigger you cannot remember -- and a manager is for
        editing them, not for reaching them. QUILL has had a gallery since its
        snippets shipped; this is the same surface at QUILL Lite's scale
        (bad.md 4.2 Tier 3, P3.6).

        "Snippet" rather than "abbreviation" in the title, because it is the
        name the bigger product uses for the same idea and a person moving
        between the two should not have to learn that they are the same thing.
        The store, the triggers and the manager are unchanged and still say
        abbreviation -- renaming those would move every key, every menu row and
        every line of documentation for a wording preference.

        Ordered by :func:`quill.core.abbreviations.quick_insert_order`, so the
        ones actually used rise to the top of the list rather than sitting in
        whatever order they were added.
        """
        from quill.apps.lite_dialogs import choose_from_rows
        from quill.core.abbreviations import quick_insert_order, resolve_expansion

        library = self.app.abbreviations
        if library is None:
            self._announce("Abbreviations are switched off. Alt+Shift+A turns them back on")
            return
        entries = quick_insert_order(library)
        if not entries:
            self._announce("There are no snippets yet. Manage Abbreviations adds one")
            return
        rows = []
        for entry in entries:
            # The trigger *and* a preview of what it writes: the trigger alone
            # is the thing somebody came here because they could not remember.
            preview = " ".join(entry.expansion.split())[:60]
            rows.append((entry.id, f"{entry.abbreviation}: {preview}"))
        chosen = choose_from_rows(
            self,
            title="Snippets",
            label="Snippets, most used first:",
            help_text=(
                "Choose one and press Enter to put it in at the cursor. These are "
                "the same abbreviations that expand as you type; this is the way "
                "in when you cannot remember the trigger."
            ),
            rows=rows,
        )
        self.control.SetFocus()
        if not isinstance(chosen, str):
            return
        entry = next((one for one in entries if one.id == chosen), None)
        if entry is None:
            return
        # ``_clipboard_text`` is DocumentClipboardMixin's -- the same reader the
        # typed expansion uses, so a clipboard snippet inserts the same thing
        # whichever route reached it.
        text, back, _used_clipboard = resolve_expansion(entry.expansion, self._clipboard_text())
        self.control.WriteText(text)
        if back:
            # The cursor placeholder, honoured the same way the typed expansion
            # honours it -- a snippet that puts the caret in the wrong place
            # through one route and the right place through the other is two
            # features wearing one name.
            self.control.SetInsertionPoint(max(0, self.control.GetInsertionPoint() - back))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Inserted {entry.abbreviation}")

    def cmd_manage_abbreviations(self) -> None:
        """QUILL's own abbreviation manager, over whichever library is in use."""
        from quill.ui.abbreviation_manager_dialog import AbbreviationManagerDialog

        library = self.app.abbreviations
        if library is None:
            self._announce("Abbreviations are switched off. Alt+Shift+A turns them back on")
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
