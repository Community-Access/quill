"""The editor's context menu: what the Applications key offers, and when.

A ``wx.TextCtrl`` on Windows already has a context menu -- Undo, Cut, Copy,
Paste, Delete, Select All -- and it is the native one, so it is announced
properly and nobody had to write it. What it cannot do is know anything about
the word under the caret, and that is the one thing this menu is worth building
for: **when the caret is in a misspelled word, the corrections come first.**

Why that matters more here than in most editors: a sighted user finds a
misspelling by looking for a red squiggle and right-clicks it. There is no
squiggle in a screen reader. QuillLite says "possible misspelling" in the status
bar once and then stays out of the way (GATE-13 -- speaking it would interrupt
the typing it is commenting on), so until now acting on it meant remembering
Shift+F7 or walking Tools > Spelling. The Applications key is the affordance
everybody already has, on the word they are already in, and pressing it now
lands the first Down arrow on the correction itself.

The shape, and the reasons:

* **Suggestions at the top level, named, one press down.** Not in a "Spelling
  Suggestions" submenu -- that is a Right arrow and a pause before anything is
  said, which is most of what the menu saves. QUILL's own editor menu had them
  nested and now does not, for the same reason.
* **The word is in every spelling label.** "Add "Bhattacharya" to My
  Dictionary", not "Add to Dictionary". A context menu is read out of context by
  a listener who arrived by keyboard, and a label that names the word is one
  they can act on without going back to check what it was about.
* **Ignore Once and Ignore in This Document, and neither touches disk.** Both
  live in an in-memory :class:`~quill.core.spelling.context_menu.IgnoreList` for
  the life of the window. Teaching a word is the durable answer and it has its
  own two rows, which say *which* dictionary they wrote to, because there are
  two and "added to dictionary" does not say.
* **A clean word gets no spelling section at all**, not a disabled one. A row
  saying "no misspelling here" is a row every right-click in a correct document
  makes somebody arrow past.
* **The keys are in the labels**, resolved through the user's own keymap like
  every other menu in the app, so the menu teaches the key rather than replacing
  it.
* **The mouse and the keyboard act on different words, correctly.** A right
  click is about the word under the pointer; the Applications key is about the
  word at the caret. Both are worked out here before the menu is built, and a
  mouse click moves the caret first so that whatever the menu does lands where
  the user was pointing.

The spelling half is switched off with the ``spelling`` area, like everything
else in the feature; the editing half is always there, because it is the native
menu's contents and losing them would be a regression.
"""

from __future__ import annotations

import wx

from quill.core.spelling.context_menu import IgnoreList, SpellingContext, spelling_context

__all__ = ["DocumentContextMenuMixin"]

#: The most suggestions on the menu itself. The rest are one press further on,
#: in the Suggestions window, which is built for arrowing through a list; a
#: menu is not, and a menu of twelve near-identical words is a menu somebody
#: loses their place in.
_MENU_SUGGESTIONS = 6


class DocumentContextMenuMixin:
    """The Applications-key menu over the editor."""

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #

    def _init_context_menu(self) -> None:
        """The per-document ignore list. One per window, gone when it closes."""
        self._spell_ignores = IgnoreList()

    @property
    def spell_ignores(self) -> IgnoreList:
        """The words this document has been told to stop reporting, this session."""
        if getattr(self, "_spell_ignores", None) is None:  # pragma: no cover - defensive
            self._init_context_menu()
        return self._spell_ignores

    # ------------------------------------------------------------------ #
    # Building it
    # ------------------------------------------------------------------ #

    def _on_editor_context_menu(self, event: wx.ContextMenuEvent) -> None:
        """Build and pop the menu, over the word the user actually meant.

        A right click is about the word under the pointer and the Applications
        key is about the word at the caret, and wx tells them apart by the
        position: a real screen position for the mouse, ``(-1, -1)`` for the
        keyboard. The mouse case moves the caret first, so that Replace, Ignore
        and Add all act on the word that was pointed at -- and so that the
        editor is left where the user was looking rather than where they had
        been before they reached for the mouse.
        """
        position = self._context_caret_position(event)
        menu = wx.Menu()
        context = self._context_spelling(position)
        if context is not None:
            self._append_spelling_section(menu, context)
        self._append_edit_section(menu)
        try:
            self._popup_at(menu, event)
        finally:
            menu.Destroy()

    def _context_caret_position(self, event: wx.ContextMenuEvent) -> int:
        """Where the menu is about: the pointer's character, or the caret.

        Never raises: ``HitTest`` is not implemented identically on every
        platform, and a context menu that throws is a context menu that does
        not appear at all -- so an unusable hit test falls back to the caret,
        which is always right for the keyboard and merely approximate for the
        mouse.
        """
        point = event.GetPosition()
        if point == wx.DefaultPosition or (point.x == -1 and point.y == -1):
            return int(self.control.GetInsertionPoint())
        try:
            _result, index = self.control.HitTestPos(self.control.ScreenToClient(point))
        except (AttributeError, TypeError, NotImplementedError):
            return int(self.control.GetInsertionPoint())
        if index < 0:
            return int(self.control.GetInsertionPoint())
        # The caret follows the pointer, so every action the menu offers lands
        # where the user pointed and the editor is left there afterwards.
        self.control.SetInsertionPoint(index)
        return int(index)

    def _context_spelling(self, position: int) -> SpellingContext | None:
        """The misspelling to build a section for, or None for none.

        None whenever the spelling area is switched off, whatever is under the
        caret: a feature somebody removed must own nothing, and a Customize
        Features checkbox that leaves half a menu behind is a checkbox that does
        not mean what it says.
        """
        if not self._spelling_enabled():
            return None
        try:
            return spelling_context(
                self.control.GetValue(),
                position,
                self._spell_dictionary(),
                self.spell_ignores,
                limit=_MENU_SUGGESTIONS,
            )
        except Exception:  # noqa: BLE001 - a spell check must never eat the menu
            return None

    def _append_spelling_section(self, menu: wx.Menu, context: SpellingContext) -> None:
        """The corrections, then the durable answers, then the way onward.

        Every mnemonic in this section is chosen to miss the edit rows below
        (U, R, T, C, P, L, A), because Windows *cycles* focus between two
        controls claiming one letter instead of pressing either -- so a letter
        used twice in one popup is a row that silently cannot be reached, and
        nothing announces the loss. That is GATE-14's rule; the gate scans
        controls rather than menus, so this one is kept by hand and by the test
        that walks the built menu.
        """
        word = context.word
        if context.suggestions:
            for suggestion in context.suggestions:
                item = menu.Append(wx.ID_ANY, self._escape_menu_text(suggestion))
                menu.Bind(
                    wx.EVT_MENU,
                    lambda _e, replacement=suggestion, ctx=context: self._replace_from_context(
                        ctx, replacement
                    ),
                    item,
                )
        else:
            # Present and disabled rather than absent, and this is the one place
            # that is right: the user asked about *this word* and "there is
            # nothing I can suggest" is the answer to their question. The rows
            # below still act on it.
            empty = menu.Append(wx.ID_ANY, f'No suggestions for "{self._escape_menu_text(word)}"')
            empty.Enable(False)
        menu.AppendSeparator()

        ignore_once = menu.Append(wx.ID_ANY, "&Ignore Once")
        menu.Bind(
            wx.EVT_MENU, lambda _e, ctx=context: self._ignore_once_from_context(ctx), ignore_once
        )
        ignore_all = menu.Append(wx.ID_ANY, "I&gnore in This Document")
        menu.Bind(
            wx.EVT_MENU, lambda _e, ctx=context: self._ignore_word_from_context(ctx), ignore_all
        )

        add_personal = menu.Append(
            wx.ID_ANY, f'Add "{self._escape_menu_text(word)}" to My &Dictionary'
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, ctx=context: self._teach_from_context(ctx, "personal"),
            add_personal,
        )
        # A second scope, because the two answers are genuinely different: a
        # surname belongs in the personal dictionary and a project's product
        # name belongs beside the file, where somebody else opening it gets it
        # too and nobody's personal list fills up with a job they left.
        add_document = menu.Append(wx.ID_ANY, "Add to This Document &Only")
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, ctx=context: self._teach_from_context(ctx, "document"),
            add_document,
        )
        menu.AppendSeparator()

        more = menu.Append(
            wx.ID_ANY, self._context_label("&More Suggestions...", "cmd_spell_word_at_cursor")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_spell_word_at_cursor(), more)
        review = menu.Append(
            wx.ID_ANY, self._context_label("Chec&k Document...", "cmd_spell_review")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_spell_review(), review)
        nxt = menu.Append(
            wx.ID_ANY, self._context_label("&Next Misspelling", "cmd_next_misspelling")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_next_misspelling(), nxt)
        previous = menu.Append(
            wx.ID_ANY, self._context_label("Pre&vious Misspelling", "cmd_previous_misspelling")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_previous_misspelling(), previous)
        menu.AppendSeparator()

    def _append_edit_section(self, menu: wx.Menu) -> None:
        """What the native menu had. Rebuilt because replacing it removed it.

        Not a smaller set: a context menu that lost Paste because somebody added
        a spell checker is a regression, and the native one is what a user's
        hands already know. The three that need a selection say so by being
        greyed rather than by being missing, which is how every Windows edit
        menu has answered "why can I not copy?" since 1995.
        """
        start, end = self.control.GetSelection()
        has_selection = end > start
        undo = menu.Append(wx.ID_UNDO, "&Undo\tCtrl+Z")
        undo.Enable(bool(self.control.CanUndo()))
        redo = menu.Append(wx.ID_REDO, "&Redo\tCtrl+Y")
        redo.Enable(bool(self.control.CanRedo()))
        menu.AppendSeparator()
        cut = menu.Append(wx.ID_CUT, "Cu&t\tCtrl+X")
        cut.Enable(has_selection)
        copy = menu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
        copy.Enable(has_selection)
        paste = menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V")
        paste.Enable(bool(self.control.CanPaste()))
        delete = menu.Append(wx.ID_DELETE, "De&lete\tDel")
        delete.Enable(has_selection)
        menu.AppendSeparator()
        menu.Append(wx.ID_SELECTALL, "Select &All\tCtrl+A")
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.Undo(), id=wx.ID_UNDO)
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.Redo(), id=wx.ID_REDO)
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.Cut(), id=wx.ID_CUT)
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.Copy(), id=wx.ID_COPY)
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.Paste(), id=wx.ID_PASTE)
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.Remove(start, end), id=wx.ID_DELETE)
        menu.Bind(wx.EVT_MENU, lambda _e: self.control.SelectAll(), id=wx.ID_SELECTALL)

    # ------------------------------------------------------------------ #
    # What the rows do
    # ------------------------------------------------------------------ #

    def _replace_from_context(self, context: SpellingContext, replacement: str) -> None:
        """Put *replacement* where the misspelling was, and say so.

        Re-checked against the document rather than trusted: the offsets were
        worked out when the menu was built, and a menu is modal for as long as
        the user leaves it open. Replacing on a stale offset would corrupt a
        word somewhere else, silently, which is the worst outcome available
        here -- so a document that has moved underneath gets an announcement
        and no edit.
        """
        if not self._context_still_valid(context):
            self._announce("That word has changed. Nothing was replaced.")
            return
        self.control.Replace(context.start, context.end, replacement)
        self.control.SetInsertionPoint(context.start + len(replacement))
        self._set_modified(True)
        self._touch_status()
        self._last_live_word = None
        self._announce(f'Replaced "{context.word}" with "{replacement}"')
        self.control.SetFocus()

    def _ignore_once_from_context(self, context: SpellingContext) -> None:
        self.spell_ignores.ignore_once(context.item)
        self._last_live_word = None
        self._touch_status()
        self._announce(f'Ignoring "{context.word}" here.')
        self.control.SetFocus()

    def _ignore_word_from_context(self, context: SpellingContext) -> None:
        self.spell_ignores.ignore_word(context.word)
        self._last_live_word = None
        self._touch_status()
        # "for now" and "until this window closes" are the two facts somebody
        # needs to decide whether to teach the word instead, and they are not
        # discoverable anywhere else.
        self._announce(
            f'Ignoring "{context.word}" in this document until you close the window. '
            "Add it to a dictionary to keep it."
        )
        self.control.SetFocus()

    def _teach_from_context(self, context: SpellingContext, scope: str) -> None:
        """Write the word to a dictionary, and name the one it went to."""
        from quill.core.lite import spelling as spelling_mod

        written = spelling_mod.add_word(
            context.word, self.app.settings, self.app.data_dir, self.path, scope
        )
        if not written:
            self._announce(f'Could not save "{context.word}" to the dictionary')
            self.control.SetFocus()
            return
        self._forget_spell_dictionary()
        self._last_live_word = None
        self._touch_status()
        self._announce(f'Added "{context.word}" to {self._dictionary_name(scope)}')
        self.control.SetFocus()

    def _dictionary_name(self, scope: str) -> str:
        """Which dictionary, in words. There are two, and possibly QUILL's."""
        if scope == "document":
            path = self.path
            where = path.name if path is not None else "this unsaved document"
            return f"the dictionary beside {where}"
        if getattr(self.app.settings, "share_quill_dictionary", False):
            return "QUILL's shared dictionary"
        return "your QuillLite dictionary"

    def _context_still_valid(self, context: SpellingContext) -> bool:
        """Does the document still say, at that offset, what the menu was about?"""
        text = self.control.GetValue()
        if context.end > len(text):
            return False
        return text[context.start : context.end] == context.word

    # ------------------------------------------------------------------ #
    # Labels
    # ------------------------------------------------------------------ #

    def _context_label(self, label: str, command: str) -> str:
        """*label* with the key that is actually bound to *command*, if any.

        The resolved key, never the literal in the command table: a menu that
        advertises a key the user has rebound is how a wrong key gets learned,
        and this menu exists partly to teach the keys that make it unnecessary.
        """
        key = self.app.binding_for(command)
        return f"{label}\t{key}" if key else label

    @staticmethod
    def _escape_menu_text(text: str) -> str:
        """A suggestion is data, so its ampersands are literal, not mnemonics.

        Without this, a suggestion containing "&" swallows the next character
        and claims an access key in a menu that has already assigned it.
        """
        return text.replace("&", "&&")

    def _popup_at(self, menu: wx.Menu, event: wx.ContextMenuEvent) -> None:
        """Pop *menu* where the event asked, or at the caret for the keyboard."""
        point = event.GetPosition()
        if point == wx.DefaultPosition or (point.x == -1 and point.y == -1):
            self.control.PopupMenu(menu)
            return
        self.control.PopupMenu(menu, self.control.ScreenToClient(point))
