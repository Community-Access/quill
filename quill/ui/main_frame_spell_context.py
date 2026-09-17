"""The spelling half of the editor's context menu, and the session ignore list.

Its own module rather than more lines in ``main_frame.py`` or
``main_frame_spellcheck.py``: both are at their GATE-11 ceiling, and this is a
self-contained subject with one entry point (:meth:`_append_spelling_corrections`)
and two commands the rest of the app can call.

**Corrections first, then a fixed tail** -- the settled answer to the one
genuinely contested question in this area (bad.md S11, resolved 2026-09-17).

A sighted user finds a misspelling by looking for a red squiggle and right-
clicks it. There is no squiggle in a screen reader, so the Applications key *is*
the squiggle, and the first Down arrow has to land on the correction itself --
not on Undo, and not on a "Spelling Suggestions" submenu that costs a Right
arrow and a pause before anything is said. QUILL had them nested until
2026-09-10 and that was the fix.

QuillLite, asked directly on 2026-09-13, went the other way and had a reason
just as good: a menu whose *length* changes with where the caret is, with Undo
and Cut a dozen unpredictable rows further down whenever the word happens to be
misspelled, is a menu nobody can learn.

Both are right, and they do not actually conflict, because the variable part is
at the **front**. Corrections, a separator, then **one row** -- Spelling Actions
for the word -- and then the edit verbs, in that order, every single time. The
first Down arrow is a correction when there is one; everything below the
corrections is where it always is. What a person learns is not a row number, it
is "after the suggestions, the menu is the menu". Both editors build it this way
now.

**Why ignoring lives in memory and nowhere else.** "Ignore this" is a statement
about the document in front of you, this afternoon. An ignore that survived the
session would be a dictionary entry nobody chose and nobody could find to
remove; the durable answer is the dictionary, which is on the same menu and says
which of its three scopes it wrote to. The list is per document, so a surname
ignored in a letter does not go quiet in the report in the next tab.

QuillLite's editor answers the same key with the same shape
(:mod:`quill.apps.lite_window_context_menu`) over the same wx-free model
(:mod:`quill.core.spelling.context_menu`), so neither editor can drift ahead of
the other.
"""

from __future__ import annotations

from quill.core.spelling.context_menu import IgnoreList

__all__ = ["SpellContextMenuMixin"]


class SpellContextMenuMixin:
    """Ignoring, and the corrections block at the top of the editor menu."""

    def spell_ignores(self) -> IgnoreList:
        """The words this document is not to complain about, for this session.

        Per document, because "ignore this" is a statement about the thing in
        front of you: a colleague's surname ignored in a letter must not go
        quiet in the report open in the next tab. Kept on the frame and keyed by
        the document rather than written into ``Document`` itself, so nothing
        about an in-memory, session-only convenience reaches the file model --
        or the file.

        Nothing here is ever persisted. The durable answer to "this is a word"
        is the dictionary, which has its own rows on the same menu and says
        which scope it wrote to.
        """
        store = getattr(self, "_spell_ignores_by_document", None)
        if store is None:
            store = {}
            self._spell_ignores_by_document = store
        key = id(self.document)
        found = store.get(key)
        if found is None:
            found = IgnoreList()
            store[key] = found
        return found

    def _first_unignored(
        self, text: str, cursor: int, dictionary: set[str], *, forward: bool
    ) -> object:
        """The next (or previous) misspelling that has not been ignored, or None.

        Stepped rather than filtered: an ignored word is not a stop, so the
        search resumes past it instead of announcing "no more misspellings" at
        the first word somebody chose to skip. Each hop starts beyond the last
        hit, so a document of nothing but ignored words ends rather than loops.
        """
        from quill.core.spellcheck import next_misspelling, previous_misspelling

        finder = next_misspelling if forward else previous_misspelling
        ignores = self.spell_ignores()
        item = finder(text, cursor, dictionary)
        while item is not None and ignores.skips(text, item):
            cursor = item.end if forward else item.start
            item = finder(text, cursor, dictionary)
        return item

    def ignore_misspelling_once(self, item: object) -> None:
        """Stop reporting this one occurrence, at this one place, this session."""
        self.spell_ignores().ignore_once(item)  # type: ignore[arg-type]
        self._last_live_misspelling_feedback = None
        self._set_status(f'Ignoring "{item.word}" here')  # type: ignore[attr-defined]

    def ignore_misspelling_everywhere(self, word: str) -> None:
        """Stop reporting *word* in this document until it is closed."""
        self.spell_ignores().ignore_word(word)
        self._last_live_misspelling_feedback = None
        # Says how long, because that is the fact that decides whether to teach
        # the word instead, and it is discoverable nowhere else.
        self._set_status(
            f'Ignoring "{word}" in this document for this session. '
            "Add it to a dictionary to keep it."
        )

    def _append_spelling_corrections(self, menu: object, context: object) -> None:
        """The corrections for the word at the caret, at the top of the menu.

        Every row names the word. A context menu reached by the Applications key
        is read out of context -- there is no pointer sitting on the thing it is
        about -- so "Add to dictionary" is a row somebody has to go back and
        check the meaning of, while 'Add "Bhattacharya" to the personal
        dictionary' is one they can act on where they stand.

        Ignore Once and Ignore in This Document are both offered, and neither
        touches disk: they last until the document is closed. Teaching a word is
        the durable answer, it is in the same submenu, and it says which of the
        three dictionaries it wrote to -- because there are three, and "added to
        dictionary" does not say which.

        Everything that is not a correction is behind one **Spelling Actions**
        row, which is what makes the tail fixed (see the module docstring). Three
        of QuillLite's scopes are two, because QuillLite opens files rather than
        projects and has nothing to call a project root; that divergence is
        real and is the only one here.
        """
        wx = self._wx
        word = context.word

        def _escape(value: str) -> str:
            # A suggestion is data, so its ampersands are literal. Without this
            # a suggestion containing "&" swallows the next character and claims
            # an access key the menu has already given to something else.
            return value.replace("&", "&&")

        if context.suggestions:
            for suggestion in context.suggestions:
                item_id = wx.NewIdRef()
                menu.Append(item_id, _escape(suggestion))

                def _apply_replacement(
                    _event,
                    replacement: str = suggestion,
                    start: int = context.start,
                    end: int = context.end,
                    original: str = word,
                ) -> None:
                    if self.editor.GetRange(start, end) != original:
                        # The offsets were worked out when the menu was built and
                        # a menu stays open as long as the user leaves it open.
                        # Replacing on a stale offset would quietly corrupt a
                        # word somewhere else, which is the worst outcome here.
                        self._set_status("That word has changed. Nothing was replaced.")
                        return
                    self.editor.Replace(start, end, replacement)
                    self.document.set_text(self.editor.GetValue())
                    self.editor.SetInsertionPoint(start + len(replacement))
                    self._set_status(f'Replaced "{original}" with "{replacement}"')

                menu.Bind(wx.EVT_MENU, _apply_replacement, id=item_id)
        else:
            # Present and disabled, and this is the one place that is right: the
            # user asked about *this word*, and "there is nothing I can suggest"
            # is the answer to their question. The rows below still act on it.
            empty_id = wx.NewIdRef()
            empty = menu.Append(empty_id, f'No suggestions for "{_escape(word)}"')
            empty.Enable(False)
        menu.AppendSeparator()

        # One row, built complete and attached last -- rows added to a wx.Menu
        # after AppendSubMenu has taken it do not appear, silently. Its items
        # bind on the PARENT popup, because wxMSW routes a popup's WM_COMMAND
        # through the menu handed to PopupMenu, so a handler bound on a submenu
        # is a handler nothing reaches. Bind matches on id, so binding on the
        # parent works for a row at either level.
        actions = wx.Menu()

        once_id = wx.NewIdRef()
        actions.Append(once_id, "&Ignore Once")
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, item=context.item: self.ignore_misspelling_once(item),
            id=once_id,
        )
        all_id = wx.NewIdRef()
        actions.Append(all_id, "I&gnore in This Document")
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, value=word: self.ignore_misspelling_everywhere(value),
            id=all_id,
        )
        actions.AppendSeparator()

        for label, scope_index in (
            (f'Add "{_escape(word)}" to My &Dictionary', 0),
            ("Add to This &Document Only", 1),
            ("Add to This P&roject", 2),
        ):
            scope_id = wx.NewIdRef()
            actions.Append(scope_id, label)
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, value=word, index=scope_index: self._add_word_to_dictionary_scope(
                    value, index
                ),
                id=scope_id,
            )
        actions.AppendSeparator()

        next_id = wx.NewIdRef()
        actions.Append(next_id, "&Next Misspelling")
        menu.Bind(wx.EVT_MENU, lambda _e: self.next_misspelling(), id=next_id)
        prev_id = wx.NewIdRef()
        actions.Append(prev_id, "Pre&vious Misspelling")
        menu.Bind(wx.EVT_MENU, lambda _e: self.previous_misspelling(), id=prev_id)

        menu.AppendSubMenu(actions, f'&Spelling Actions for "{_escape(word)}"')
        menu.AppendSeparator()
