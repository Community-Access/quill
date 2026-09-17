"""The editor's context menu: what the Applications key offers, and when.

A ``wx.TextCtrl`` on Windows already has a context menu -- Undo, Cut, Copy,
Paste, Delete, Select All -- and it is the native one, so it is announced
properly and nobody had to write it. What it cannot do is know anything about
the word under the caret, and that is the one thing this menu is worth building
for: **when the caret is in a misspelled word, the menu grows a Spelling
submenu whose first row is a correction.**

Why that matters more here than in most editors: a sighted user finds a
misspelling by looking for a red squiggle and right-clicks it. There is no
squiggle in a screen reader. QuillLite says "possible misspelling" in the status
bar once and then stays out of the way (GATE-13 -- speaking it would interrupt
the typing it is commenting on), so until now acting on it meant remembering
Shift+F7 or walking Tools > Spelling. The Applications key is the affordance
everybody already has, on the word they are already in, and it now opens onto
the corrections for that word.

The shape, and the reasons:

* **The corrections are at the top level; everything else about the word is
  one row below them**, and that shape is the settled answer to the one
  genuinely contested question in this area (bad.md S11, resolved 2026-09-17).

  Two good arguments pulled opposite ways. QUILL's: the Applications key *is*
  the squiggle a listener does not have, so the first Down arrow has to land on
  the correction itself -- a submenu costs a Right arrow and a pause before
  anything is said, which is most of what the menu was saving. QuillLite's,
  asked for directly on 2026-09-13: a menu whose length changes depending on
  where the caret is, with Undo and Cut a dozen unpredictable rows further down
  whenever the word happens to be misspelled, is a menu nobody can learn.

  Both are right, and they are not actually in conflict, because the variable
  part is at the **front**. The corrections come first, then a separator, then
  **the same rows in the same order every single time** -- Spelling Actions,
  then the edit verbs. So the first Down arrow is a correction when there is
  one, and everything below the corrections is where it always is. What a
  person learns is not a row number, it is "after the suggestions, the menu is
  the menu".

  The rest of the spelling verbs -- ignore, teach, more suggestions, next and
  previous -- keep a submenu of their own, because they are the part nobody
  needs in a hurry and the part that would otherwise make the tail long.
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

from quill.core.links import find_link_at_cursor
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
        self._show_context_menu(position, event)

    def open_context_menu_at_caret(self) -> None:
        """The same menu, from the key that asked for it.

        Called by the Shift+F10 / Applications-key path in
        :class:`~quill.apps.lite_window_typing.DocumentTypingMixin`, which does
        not wait to find out whether wxMSW turns the keystroke into an
        ``EVT_CONTEXT_MENU`` on a subclassed native RichEdit. The caret is
        already where the user put it, so there is nothing to hit-test.
        """
        self._show_context_menu(int(self.control.GetInsertionPoint()), None)

    @staticmethod
    def _new_menu() -> wx.Menu:
        """A fresh, empty menu.

        A seam and nothing more. ``wx.Menu()`` needs a live ``wx.App``, and the
        menu tests build the whole thing against a stand-in so they can assert
        on rows and labels without a display; the submenu has to come from
        somewhere they can substitute.
        """
        return wx.Menu()

    def _show_context_menu(self, position: int, event: wx.ContextMenuEvent | None) -> None:
        """Build the menu for *position* and pop it. One body, two entry points."""
        menu = wx.Menu()
        context = self._context_spelling(position)
        if context is not None:
            self._append_spelling_section(menu, context)
        self._append_link_section(menu, position)
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
        """Corrections at the top, then one "Spelling Actions" row (bad.md S11).

        Built complete and only then attached, which is a wxMSW rule rather
        than a style: rows added to a ``wx.Menu`` *after* ``AppendSubMenu`` has
        taken it do not appear, silently. The same trap is written up in
        :mod:`quill.apps.lite_window_menus`, which builds the menu bar.

        Its rows bind on the **parent popup**, even though they live in the
        submenu, and that is not an oversight. wxMSW routes a popup menu's
        WM_COMMAND through ``wxCurrentPopupMenu`` -- the menu that was handed to
        ``PopupMenu`` -- so a handler bound on a submenu is a handler nothing
        ever reaches. ``Bind`` matches on the item's id, so binding on the
        parent works for a row at either level.

        Mnemonics inside a submenu are their own namespace, so these no longer
        have to dodge the edit rows below (U, R, T, C, P, L, A) -- only each
        other, and "&Spelling" has to miss them, which S does. That is GATE-14's
        rule; the gate scans controls rather than menus, so this one is kept by
        hand and by the test that walks the built menu.
        """
        word = context.word
        # The corrections, on the menu itself. This is the half of S11 that came
        # back from the submenu: the first Down arrow has to land on the answer.
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

        spelling = self._new_menu()
        ignore_once = spelling.Append(wx.ID_ANY, "&Ignore Once")
        menu.Bind(
            wx.EVT_MENU, lambda _e, ctx=context: self._ignore_once_from_context(ctx), ignore_once
        )
        ignore_all = spelling.Append(wx.ID_ANY, "I&gnore in This Document")
        menu.Bind(
            wx.EVT_MENU, lambda _e, ctx=context: self._ignore_word_from_context(ctx), ignore_all
        )

        add_personal = spelling.Append(
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
        add_document = spelling.Append(wx.ID_ANY, "Add to This Document &Only")
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, ctx=context: self._teach_from_context(ctx, "document"),
            add_document,
        )
        spelling.AppendSeparator()

        more = spelling.Append(
            wx.ID_ANY, self._context_label("&More Suggestions...", "cmd_spell_word_at_cursor")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_spell_word_at_cursor(), more)
        review = spelling.Append(
            wx.ID_ANY, self._context_label("Chec&k Document...", "cmd_spell_review")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_spell_review(), review)
        nxt = spelling.Append(
            wx.ID_ANY, self._context_label("&Next Misspelling", "cmd_next_misspelling")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_next_misspelling(), nxt)
        previous = spelling.Append(
            wx.ID_ANY, self._context_label("Pre&vious Misspelling", "cmd_previous_misspelling")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_previous_misspelling(), previous)

        # The word is in the title too. A submenu is read as one row on the way
        # past, and "Spelling" alone does not say which word it is about --
        # which is the same reason every row inside it names the word. What is
        # in here is everything that is *not* a correction: the corrections
        # themselves are above, where the first Down arrow reaches them.
        menu.AppendSubMenu(spelling, f'&Spelling Actions for "{self._escape_menu_text(word)}"')
        menu.AppendSeparator()

    def _append_link_section(self, menu: wx.Menu, position: int) -> None:
        """Two rows, and only when the caret is actually on a link.

        A web address in a text file is the commonest actionable thing in one,
        and QuillLite's context menu had spelling, the clipboard verbs and
        nothing else -- so the only way to follow a link was to select it by
        hand, copy it, and paste it into a browser. QUILL offers both of these
        when the caret is on one; the finder
        (:func:`~quill.core.links.find_link_at_cursor`) is shared and understands
        a Markdown link, an ``href=`` and a bare URL (bad.md 4.2, Tier 2).

        Absent rather than greyed, unlike the edit rows: those three are always
        *about* something and their state answers "why can I not copy?", while a
        permanent "Open Link" on every right-click in a document with no links
        in it is a row to walk past forever.
        """
        url = find_link_at_cursor(self.doc_text.text, int(position))
        if not url:
            return
        shown = url if len(url) <= 60 else url[:59] + "\u2026"
        open_item = menu.Append(wx.ID_ANY, f"&Open {self._escape_menu_text(shown)}")
        copy_item = menu.Append(wx.ID_ANY, "Cop&y Link Address")
        menu.Bind(wx.EVT_MENU, lambda _e, target=url: self._open_link(target), open_item)
        menu.Bind(wx.EVT_MENU, lambda _e, target=url: self._copy_link(target), copy_item)
        menu.AppendSeparator()

    def _open_link(self, url: str) -> None:
        """Hand *url* to whatever the system opens it with. Never raises.

        A failure is announced rather than thrown: no browser configured, or a
        URL the shell refuses, must not take the editor down with it -- and the
        address is still on offer through Copy Link Address.
        """
        try:
            opened = bool(wx.LaunchDefaultBrowser(url))
        except Exception:  # noqa: BLE001 - opening a link is never worth a crash
            opened = False
        self.control.SetFocus()
        self._announce(f"Opened {url}" if opened else f"That link could not be opened: {url}")

    def _copy_link(self, url: str) -> None:
        self.control.SetFocus()
        if self._set_clipboard_text(url):
            self._announce(f"Copied {url}")
            return
        self._announce("That could not be copied")

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

    def _popup_at(self, menu: wx.Menu, event: wx.ContextMenuEvent | None) -> None:
        """Pop *menu* where the event asked, or at the caret for the keyboard."""
        if event is None:
            self.control.PopupMenu(menu)
            return
        point = event.GetPosition()
        if point == wx.DefaultPosition or (point.x == -1 and point.y == -1):
            self.control.PopupMenu(menu)
            return
        self.control.PopupMenu(menu, self.control.ScreenToClient(point))
