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
from quill.core.autoformat import autoformat_allows, is_dash_merge, smart_quote_for
from quill.core.sound_events import SoundEvent
from quill.ui.richedit_editing import RICH

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
        #: True: Tab types a tab character. False: Tab runs the smart line
        #: indent. Neither is the default any more -- the document kind decides
        #: through the shared quill.core.tab_behaviour rule QUILL reads too
        #: (bad.md T3, P1.21) -- and this holds the answer only once somebody
        #: has used the toggle, which is what _tab_mode_chosen records.
        self._tab_inserts_literal = True
        self._tab_mode_chosen = False

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
        # Escape also leaves Extend Selection Mode, which is a different state
        # from a waiting F8 marker: the marker is a place, the mode is a
        # sticky Shift. Both are invisible, so both answer Escape and both say
        # they did.
        if code == wx.WXK_ESCAPE and self.cancel_extend_selection_mode():
            return
        # Extend Selection Mode owns the navigation keys while it is on, and
        # must see them BEFORE the control does -- on wxMSW an arrow pressed
        # with text selected collapses the selection and stops, which is what
        # broke QuillLite's own attempt at this (bad.md P2.13, 5.3a).
        if self.handle_extend_selection_key(event):
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
        if self._swallow_native_formatting_key(event):
            return
        event.Skip()

    def _swallow_native_formatting_key(self, event: wx.KeyEvent) -> bool:
        """Stop the control formatting a document that has no formatting.

        QuillLite builds plain and Markdown documents on the same Rich Edit
        control QUILL does, and for the same reason -- it is what gives braille
        and the reader a text surface worth reading. The control brings its own
        chords: every native key QuillLite does not bind (``Ctrl+Shift+=`` for
        superscript and its friends) applies a formatting run to a document
        that cannot hold one, so the window and the file it will write disagree
        and nothing says so (bad.md R9).

        Said once per document, from the same shared sentence QUILL uses, so
        the two products cannot explain one dead key two ways. A chord
        QuillLite binds never reaches here: the menu accelerator runs first.
        """
        from quill.core.native_richedit_keys import (
            native_formatting_effect,
            native_formatting_notice,
            notice_kind_label,
        )

        if getattr(self.editor, "mode", None) == RICH:
            return False
        # getattr, not a direct call: a key event reaches this handler from
        # several places, and the guard must never be the reason a keystroke
        # raises. No key code means nothing to swallow.
        unicode_key = getattr(event, "GetUnicodeKey", None)
        key_code = getattr(event, "GetKeyCode", None)
        try:
            raw = (unicode_key() if callable(unicode_key) else 0) or (
                key_code() if callable(key_code) else 0
            )
            key = chr(int(raw))
        except (ValueError, OverflowError, TypeError):
            return False

        def held(name: str) -> bool:
            probe = getattr(event, name, None)
            return bool(probe()) if callable(probe) else False

        effect = native_formatting_effect(
            ctrl=held("ControlDown"),
            shift=held("ShiftDown"),
            alt=held("AltDown"),
            key=key,
        )
        if effect is None:
            return False
        seen = getattr(self, "_native_key_notices", None)
        if seen is None:
            seen = set()
            self._native_key_notices = seen
        if effect not in seen:
            seen.add(effect)
            # Through the shared table, not .lower(): lower-casing this
            # window's own "HTML" said "a html document" where QUILL said
            # "an HTML document", for the same key in the same file.
            self._announce(
                native_formatting_notice(effect, notice_kind_label(self.document_kind_label()))
            )
        return True

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
        elif self._tab_types_a_tab():
            return False
        else:
            self.cmd_indent(announce=False)
        self._announce(self.describe_indent_at_cursor())
        return True

    def _tab_types_a_tab(self) -> bool:
        """Whether Tab types a tab character right now (bad.md T3, P1.21).

        The toggle wins once it has been used; otherwise the document kind
        decides, through the rule QUILL reads too. QuillLite typed a tab in
        every kind and QUILL indented in every kind, and each was wrong in the
        other's documents -- a tab in a Markdown list item breaks the list.
        """
        from quill.core.tab_behaviour import tab_inserts_a_tab

        if self._tab_mode_chosen:
            return self._tab_inserts_literal
        return tab_inserts_a_tab(self.markup_surface())

    def cmd_toggle_tab_mode(self) -> None:
        """Switch the Tab key between typing a tab and indenting the line."""
        self._tab_inserts_literal = not self._tab_types_a_tab()
        self._tab_mode_chosen = True
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
        """Replace the keystroke where a rule applies. ``True`` when it did.

        Three gates, and they answer different questions. The Customize Features
        area is "do I want this at all"; the two settings are "which of the two
        rules" (QUILL's granularity, taken on 2026-09-17 -- curly quotes and em
        dashes are different opinions, bad.md T5); and the document kind is the
        one the app answers for itself, because a curly quote in a ``.json`` is
        a syntax error nobody asked for and no setting can express "except in
        code" (bad.md T4).
        """
        if not autoformat_allows(self.document_language()):
            return False
        settings = self.app.settings
        position = self.control.GetInsertionPoint()
        if position and self.control.GetSelection()[0] != self.control.GetSelection()[1]:
            return False  # a selection is a replacement, not a typed character
        # One character, not the whole document. This runs on *every
        # keystroke*, and reading the buffer out of the control to look at the
        # character behind the caret was the single hottest O(N) in the app --
        # QUILL has read it this way since #1346 (bad.md T1).
        preceding = self.control.GetRange(position - 1, position) if position else ""
        if typed in _QUOTES:
            if not bool(getattr(settings, "autoformat_smart_quotes", False)):
                return False
            self._insert_replacing(smart_quote_for(preceding, typed), back=0)
            return True
        if (
            typed == "-"
            and bool(getattr(settings, "autoformat_dashes", False))
            and is_dash_merge(preceding)
        ):
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

    def cmd_snippet_gallery(self) -> None:
        """Ctrl+Shift+Insert: pick a snippet from a list and put it in.

        The half QuillLite did not have. Abbreviations expand when you *type the
        trigger*, which is perfect for the six you use daily and useless for the
        fortieth one, whose trigger you cannot remember -- and a manager is for
        editing them, not for reaching them. QUILL has had a gallery since its
        snippets shipped; this is the same surface at QuillLite's scale
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
