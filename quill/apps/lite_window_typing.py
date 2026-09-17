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
checkbox in Tools > Customize Features.

Neither runs in plain text mode by accident: both are keyed off ``EVT_CHAR``
after the character has landed, and both leave the text alone when their area is
off.

**Overtype** is the fourth. The native control implements insert-versus-overwrite
itself and toggles it on VK_INSERT, and it will not report which mode it is in --
so QuillLite mirrors the mode, and every route that changes it comes through
:meth:`~quill.ui.richedit_editing.RichEditDocument.toggle_overtype` (which is
also what QUILL's own command calls). The Insert key is watched rather than
bound: it is NVDA's and JAWS's modifier and must never be claimed, but the
control answers it regardless, so the mirror has to see it go past or the Typing
Mode cell would start lying the first time somebody pressed it.

**Tab mode** is the fifth, and the only one that changes what an ordinary key
*means*. QuillLite is a Notepad replacement, so its Tab types a tab character --
that is the default, and it is the opposite of QUILL's, where Tab runs the smart
line indent. The divergence is deliberate and is the only one on this page:
QUILL is a document editor whose Tab is almost always about structure, while a
file opened in QuillLite is as likely to be a configuration file where a tab is
data. Both products ship the same toggle so either default can be left behind,
and in both Shift+Tab outdents whatever the mode, so a stray indent can be
undone without first switching back.

**Spell check** is the third thing watching the keystroke, and the only one that
never changes the text -- it schedules
:meth:`~quill.apps.lite_window_spelling.DocumentSpellingMixin.schedule_live_spell_check`
and nothing more. It is here rather than on ``EVT_TEXT`` so that a paste, which
is not typing, does not trigger a check of a word the user never typed.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.abbreviations import is_trigger_char, try_expand
from quill.core.autoformat import is_dash_merge, smart_quote_for
from quill.core.sound_events import SoundEvent

__all__ = ["DocumentTypingMixin"]

#: The characters autocorrect reacts to. Everything else is passed straight
#: through, so the common case costs one set membership test per keystroke.
_QUOTES = {'"', "'"}


class DocumentTypingMixin:
    """Abbreviation expansion and autocorrect, on the way through EVT_CHAR."""

    # -- overtype ------------------------------------------------------------ #

    def _init_overwrite(self) -> None:
        """Start in insert mode, which is where a freshly built control starts."""
        #: Mirrors the control, which keeps the mode and will not report it.
        self._overwrite_mode = False
        #: Up only while :meth:`cmd_toggle_overwrite` is handing the control a
        #: synthesised Insert; the watcher must not read that as the user.
        self._synthetic_insert_key = False
        #: True: Tab types a tab character (Notepad, and QuillLite's default).
        #: False: Tab runs the smart line indent (QUILL's default). See the
        #: module docstring for why the two products start on opposite sides.
        self._tab_inserts_literal = True

    def _on_key_down(self, event: wx.KeyEvent) -> None:
        """Watch the Insert key go past, and keep the mirror true.

        Never bound, only watched: Insert is the screen reader's modifier, and
        ``Skip`` is what lets the control do the overtype it was always going
        to do. All this adds is that the status cell knows.
        """
        code = event.GetKeyCode()
        if code == wx.WXK_INSERT and not self._synthetic_insert_key:
            self._overwrite_mode = not self._overwrite_mode
            self._touch_status()
            self._sync_check_items()
            event.Skip()
            return
        if code == wx.WXK_TAB and self._handle_tab(event):
            return
        # Escape drops a waiting F8 marker. It could not be cancelled at all
        # before 2026-09-16: cancel_extend_selection existed and nothing called
        # it, so once F8 was pressed the marker waited forever and pressing F8
        # again silently moved it somewhere else. The state is invisible, so
        # the only way out was to complete a selection you did not want
        # (bad.md L4). Escape is what a listener reaches for, and it is free
        # here -- the control does nothing with it in a plain edit.
        if code == wx.WXK_ESCAPE and self.cancel_extend_selection():
            return
        # Shift+F10 and the Applications key, opened here rather than left to
        # wx. Reported 2026-09-12: "I misspelled a word and arrow to it and
        # pressed shift+f10 and got no spelling information." The menu is built
        # by EVT_CONTEXT_MENU, which wxMSW raises from WM_CONTEXTMENU -- and the
        # editor is a native RichEdit that wx subclasses, so whether the
        # keyboard form of that message ever arrives is not ours to rely on. A
        # right-click always worked, which is exactly the shape of bug that
        # looks like "the feature is missing" to somebody who never uses a
        # mouse. Opening it from the key that was pressed needs no such luck.
        if self._is_context_menu_key(event):
            self.open_context_menu_at_caret()
            return
        event.Skip()

    @staticmethod
    def _is_context_menu_key(event: wx.KeyEvent) -> bool:
        """Shift+F10 or the Applications key, and nothing else.

        Plain F10 is the menu bar and must be left alone; Ctrl+Shift+F10 is not
        this either, so the modifiers are checked rather than assumed.
        """
        code = event.GetKeyCode()
        if code == wx.WXK_WINDOWS_MENU:
            return not (event.ControlDown() or event.AltDown())
        return (
            code == wx.WXK_F10
            and event.ShiftDown()
            and not (event.ControlDown() or event.AltDown())
        )

    def _handle_tab(self, event: wx.KeyEvent) -> bool:
        """Indent or outdent instead of typing a tab. ``True`` if it was handled.

        Shift+Tab outdents in *either* mode, so a stray indent can be undone
        without first leaving literal-tab mode. Plain Tab is only intercepted
        when the smart mode is on; otherwise it is left alone and the control --
        built with ``TE_PROCESS_TAB`` -- types the character itself, which is
        what a Notepad replacement is expected to do.

        The outcome is spoken as the new depth ("4 spaces", "1 tab") rather than
        "Indented 1 line", because leading whitespace is precisely what a screen
        reader does not read back: the count is the only way to hear what the
        keystroke actually did.
        """
        if event.ShiftDown():
            self.cmd_outdent(announce=False)
        elif self._tab_inserts_literal:
            return False
        else:
            self.cmd_indent(announce=False)
        self._announce(self.describe_indent_at_cursor())
        return True

    def cmd_toggle_tab_mode(self) -> None:
        """Switch the Tab key between typing a tab and indenting the line."""
        self._tab_inserts_literal = not self._tab_inserts_literal
        self._touch_status()
        self._sync_check_items()
        self._announce(
            "Tab key types a tab character"
            if self._tab_inserts_literal
            else "Tab key indents the line"
        )

    def cmd_toggle_overwrite(self) -> None:
        """Switch between inserting and overwriting, in the control as well.

        Refuses rather than lies when there is no native control to tell: a
        status cell that misreports what typing is about to do, to somebody who
        cannot check by looking, is the one failure this bar exists to prevent.
        """
        toggle = getattr(self.editor, "toggle_overtype", None)
        self._synthetic_insert_key = True
        try:
            moved = bool(toggle()) if callable(toggle) else False
        except Exception:  # noqa: BLE001 - the mirror stays honest either way
            moved = False
        finally:
            self._synthetic_insert_key = False
        if not moved:
            self._announce("Overwrite mode is not available on this editing surface")
            return
        self._overwrite_mode = not self._overwrite_mode
        self._sync_check_items()
        self._announce("Overwrite mode on" if self._overwrite_mode else "Insert mode on")

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
        # One character, not the whole document. This runs on *every
        # keystroke*, and reading the buffer out of the control to look at the
        # character behind the caret was the single hottest O(N) in the app --
        # QUILL has read it this way since #1346 (bad.md T1).
        preceding = self.control.GetRange(position - 1, position) if position else ""
        if typed in _QUOTES:
            self._insert_replacing(smart_quote_for(preceding, typed), back=0)
            return True
        if typed == "-" and is_dash_merge(preceding):
            # The second hyphen of "--" becomes an em dash, eating the first.
            self._insert_replacing("—", back=1)
            self._cue(SoundEvent.WORD_CORRECTED)
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
