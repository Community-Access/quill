"""The thesaurus and the dictionary, shared by QUILL and QUILL Lite.

A base of :class:`quill.ui.hosted_ai_commands.HostedAiMixin`, the way the
ChatGPT commands are: both editors get every command here the moment they get
the rest, and neither writes a line of its own.

Two things, with one word under the cursor between them:

**The thesaurus** is offline and free: the MyThes data file every copy ships
(:mod:`quill.core.thesaurus`), reached through :mod:`quill.core.word_lookup` so
that the word you are *on* is found -- "running" finds "run", "happier" finds
"happy" -- and every replacement comes back in the form the sentence needs.
``Shift+F7`` opens the two-pane picker; the context menu on a word carries a
**Thesaurus** submenu with the best replacements one keystroke away, the other
senses as submenus of their own, and the opposites.

**The dictionary** is the AI word tools (:mod:`quill.core.ai.word_tools`):
define this word *as used here*, synonyms that fit, a plainer or more formal or
more vivid word, opposites, is this the right word, use it in a sentence, where
it comes from, how to say it, rhymes, the Word Explorer that does all of it at
once, and the reverse dictionary (describe a meaning, get the word). They send
the word and the sentence it sits in, never the rest of the document, and run
**only on a direct route** -- the listener's own OpenAI key or ChatGPT
subscription -- for the reason written in ``word_tools.py``: the free service
is metered per person and a dictionary is asked a hundred times a day. With
neither, every row says so and opens the account window.

Both reach the same word the same way (:func:`quill.core.word_lookup.find_word`:
the selection when it is one word, else the word at the caret), so a listener
learns one habit: be on the word, press the key or open the menu.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core import thesaurus as thesaurus_engine
from quill.core import word_lookup
from quill.core.ai import word_tools
from quill.core.ai.word_tools import WordTool
from quill.core.word_lookup import WordSpan
from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["WordToolsMixin", "NEEDS_DIRECT_ROUTE"]

#: Said when a dictionary command runs with no key and no plan.
NEEDS_DIRECT_ROUTE = (
    "The dictionary uses your ChatGPT subscription or your own AI key. Sign in "
    "with Use My ChatGPT Subscription, or save a key with Use My Own AI Key, and "
    "try again."
)

#: Replacements the context menu puts in the first level of the Thesaurus
#: submenu: enough to choose from by ear, few enough to arrow through.
_MENU_TOP_TERMS = 8


def _escape(text: str) -> str:
    """Menu text: a literal ampersand is doubled or wx eats it as a mnemonic."""
    return text.replace("&", "&&")


class WordToolsMixin:
    """Thesaurus (offline) and dictionary (AI word tools) commands and menus."""

    # ------------------------------------------------------------------ #
    # Hooks: the one thing the two editors answer differently
    # ------------------------------------------------------------------ #

    def _dictionary_enabled(self) -> bool:
        """Whether the dictionary and thesaurus exist in this copy. QUILL Lite
        answers with its feature area; QUILL with its dictionary feature."""
        host = self._ai_host()  # type: ignore[attr-defined]
        asked = getattr(host, "feature_enabled", None)
        if callable(asked):
            try:
                return bool(asked("dictionary"))
            except Exception:  # noqa: BLE001 - a host that cannot say has it on
                return True
        return True

    def _online_lookups_allowed(self) -> bool:
        """The remembered consent for Look Up's online sources. Off until said."""
        settings = getattr(self._ai_host(), "settings", None)  # type: ignore[attr-defined]
        return bool(getattr(settings, "dictionary_online_lookups", False))

    def _set_online_lookups(self, allowed: bool) -> None:
        host = self._ai_host()  # type: ignore[attr-defined]
        settings = getattr(host, "settings", None)
        if settings is None:
            return
        try:
            settings.dictionary_online_lookups = bool(allowed)
        except Exception:  # noqa: BLE001 - a frozen settings object keeps the session value only
            return
        saver = getattr(host, "save_settings", None)
        if callable(saver):
            try:
                saver()
            except Exception:  # noqa: BLE001 - a read-only profile keeps the choice for the session
                pass

    def _lexical_service(self) -> Any:
        """One ``LexicalService`` per window, built on first use (the online
        providers' request stack stays off the start-up path)."""
        getter = getattr(self, "_get_lexical_service", None)  # QUILL caches its own
        if callable(getter):
            return getter()
        service = getattr(self, "_word_lexical_service", None)
        if service is None:
            from quill.core.lexical import default_service

            service = default_service(include_online=True)
            self._word_lexical_service = service
        return service

    def _teach_word(self, word: str) -> str:
        """Add *word* to the personal spelling dictionary; the sentence to say."""
        quill_way = getattr(self, "_add_word_to_dictionary_scope", None)
        if callable(quill_way):
            quill_way(word, 0)
            return f'Added "{word}" to your personal dictionary.'
        from quill.core.lite import spelling as spelling_mod

        app = self._ai_host()  # type: ignore[attr-defined]
        written = spelling_mod.add_word(
            word, app.settings, app.data_dir, getattr(self, "path", None)
        )
        forget = getattr(self, "_forget_spell_dictionary", None)
        if callable(forget):
            forget()
        if not written:
            return f'Could not save "{word}" to the dictionary.'
        shared = bool(getattr(app.settings, "share_quill_dictionary", False))
        where = "QUILL's shared dictionary" if shared else "your QUILL Lite dictionary"
        return f'Added "{word}" to {where}.'

    # ------------------------------------------------------------------ #
    # The word
    # ------------------------------------------------------------------ #

    def _word_context(self) -> tuple[str, int, tuple[int, int]]:
        control = self._ai_control()  # type: ignore[attr-defined]
        text = str(control.GetValue())
        caret = int(control.GetInsertionPoint())
        start, end = control.GetSelection()
        return text, caret, (int(start), int(end))

    def _current_word(self) -> tuple[str, WordSpan | None]:
        text, caret, selection = self._word_context()
        return text, word_lookup.find_word(
            text, caret, selection if selection[0] != selection[1] else None
        )

    def _word_still_there(self, text_then: str, span: WordSpan) -> bool:
        """Is the word this answer was about still exactly where it was?"""
        try:
            current = str(self._ai_control().GetValue())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a closed control is "changed"
            return False
        return (
            0 <= span.start <= span.end <= len(current)
            and current[span.start : span.end] == span.word
        )

    def _replace_word(self, span: WordSpan, replacement: str) -> None:
        """Write *replacement* over the word as one undoable edit, caret after it.

        The selection is collapsed afterwards: a selected word is destroyed by
        the next keystroke, and the reader announces a selection on focus
        return, which is an utterance nobody asked for.
        """
        control = self._ai_control()  # type: ignore[attr-defined]
        replace_as_one_undo(control, span.start, span.end, replacement)
        control.SetInsertionPoint(span.start + len(replacement))

    def _insert_at_caret(self, text: str) -> None:
        control = self._ai_control()  # type: ignore[attr-defined]
        start, end = control.GetSelection()
        if end <= start:
            start = end = int(control.GetInsertionPoint())
        replace_as_one_undo(control, int(start), int(end), text)
        control.SetInsertionPoint(int(start) + len(text))

    # ------------------------------------------------------------------ #
    # The thesaurus (offline)
    # ------------------------------------------------------------------ #

    def cmd_thesaurus(self) -> None:
        """Shift+F7: the two-pane picker for the word you are on, or one you type."""
        if not self._dictionary_enabled():
            self._announce("The thesaurus is switched off in Customize Features.")  # type: ignore[attr-defined]
            return
        if not thesaurus_engine.is_available():
            self._announce(  # type: ignore[attr-defined]
                "The thesaurus data file is not installed. Expected at "
                f"{thesaurus_engine.data_path()}."
            )
            return
        text, span = self._current_word()
        word = span.word if span is not None else ""
        if not word:
            parent = self._ai_parent()  # type: ignore[attr-defined]
            dialog = wx.TextEntryDialog(parent, "Look up word in thesaurus:", "Thesaurus", value="")
            try:
                if self._show_word_dialog(dialog, "Thesaurus") != wx.ID_OK:
                    return
                word = dialog.GetValue().strip()
            finally:
                dialog.Destroy()
            if not word:
                self._announce("No word entered.")  # type: ignore[attr-defined]
                return
            span = None
        self._open_thesaurus_picker(word, span)

    def _open_thesaurus_picker(self, word: str, span: WordSpan | None) -> None:
        from quill.ui.thesaurus_dialog import ThesaurusDialog

        headword, _how, senses = word_lookup.picker_senses(word)
        if not senses:
            self._announce(f'No thesaurus entry for "{word}".')  # type: ignore[attr-defined]
            return
        picker = ThesaurusDialog(
            self._ai_parent(),  # type: ignore[attr-defined]
            word if headword == word.lower() else f"{word} (as {headword})",
            senses,
            allow_replace=span is not None,
            show_modal_dialog=self._show_word_dialog,
            on_copy=self._copy_word,
            announce=self._announce,  # type: ignore[attr-defined]
        )
        try:
            chosen = picker.show_modal()
        finally:
            picker.Destroy()
        if not chosen or span is None:
            return
        self._replace_word(span, chosen)
        self._announce(f'Replaced "{span.word}" with "{chosen}".')  # type: ignore[attr-defined]

    def cmd_look_up(self) -> None:
        """Alt+F10: the dictionary without AI, for the word you are on or one you type."""
        if not self._dictionary_enabled():
            self._announce("The dictionary is switched off in Customize Features.")  # type: ignore[attr-defined]
            return
        _text, span = self._current_word()
        word = span.word if span is not None else ""
        if not word:
            dialog = wx.TextEntryDialog(
                self._ai_parent(),  # type: ignore[attr-defined]
                "Look up which word?",
                "Look Up",
                value="",
            )
            try:
                if self._show_word_dialog(dialog, "Look Up") != wx.ID_OK:
                    return
                word = dialog.GetValue().strip()
            finally:
                dialog.Destroy()
            if not word:
                self._announce("No word entered.")  # type: ignore[attr-defined]
                return
            span = None
        self._look_up_word(word, span)

    def _look_up_word(self, word: str, span: WordSpan | None) -> None:
        from quill.ui.lookup_window import show_lookup

        show_lookup(
            self._ai_parent(),  # type: ignore[attr-defined]
            word,
            service=self._lexical_service(),
            online=self._online_lookups_allowed(),
            set_online=self._set_online_lookups,
            replace=(lambda chosen: self._replace_word(span, chosen)) if span is not None else None,
            teach=self._teach_word,
            announce=self._announce,  # type: ignore[attr-defined]
            show_modal=self._show_word_dialog,
        )

    def cmd_word_summary(self) -> None:
        """Say what the thesaurus knows about the word you are on, without opening anything."""
        if not self._dictionary_enabled():
            self._announce("The thesaurus is switched off in Customize Features.")  # type: ignore[attr-defined]
            return
        _text, span = self._current_word()
        if span is None:
            self._announce("Put the cursor in a word, or select one, first.")  # type: ignore[attr-defined]
            return
        self._announce(word_lookup.word_summary(span.word))  # type: ignore[attr-defined]

    def _show_word_dialog(self, dialog: Any, title: str) -> int:
        """QUILL's hardened modal gate when the host has one; the shared one otherwise."""
        shower = getattr(self, "_show_modal_dialog", None)
        if callable(shower):
            return int(shower(dialog, title))
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title, announce=getattr(self, "_announce", None)))

    def _copy_word(self, text: str) -> bool:
        if not wx.TheClipboard.Open():
            return False
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            try:
                wx.TheClipboard.Flush()
            except Exception:  # noqa: BLE001 - flushing is a courtesy
                pass
            return True
        finally:
            wx.TheClipboard.Close()

    # ------------------------------------------------------------------ #
    # The dictionary (AI word tools)
    # ------------------------------------------------------------------ #

    def cmd_word_define(self) -> None:
        """Define the word as it is used in this sentence."""
        self._run_word_tool(word_tools.TOOLS_BY_ID["define"])

    def cmd_word_synonyms(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["synonyms"])

    def cmd_word_simpler(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["simpler"])

    def cmd_word_formal(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["formal"])

    def cmd_word_vivid(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["vivid"])

    def cmd_word_opposites(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["opposites"])

    def cmd_word_right(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["right_word"])

    def cmd_word_examples(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["examples"])

    def cmd_word_origin(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["origin"])

    def cmd_word_pronounce(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["pronounce"])

    def cmd_word_rhymes(self) -> None:
        self._run_word_tool(word_tools.TOOLS_BY_ID["rhymes"])

    def cmd_word_explorer(self) -> None:
        """Everything about the word at once."""
        self._run_word_tool(word_tools.EXPLORE)

    def cmd_find_word(self) -> None:
        """The reverse dictionary: describe the meaning, get the word, at the cursor."""
        if not self._dictionary_ready():
            return
        text, caret, _selection = self._word_context()
        sentence = word_lookup.sentence_around(text, caret, caret)
        parent = self._ai_parent()  # type: ignore[attr-defined]
        dialog = wx.TextEntryDialog(
            parent,
            "Describe the word you are looking for (its meaning, or what it is like):",
            "Find the Word For",
            value="",
        )
        try:
            if self._show_word_dialog(dialog, "Find the Word For") != wx.ID_OK:
                return
            description = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not description:
            self._announce("No description entered.")  # type: ignore[attr-defined]
            return
        self._announce("Working.")  # type: ignore[attr-defined]
        self._ai_service().ask(  # type: ignore[attr-defined]
            word_tools.FEATURE,
            word_tools.find_word_prompt(description, sentence),
            None,
            on_done=lambda answer, _quota: self._show_word_answer(
                word_tools.FIND_WORD, "", answer, on_use=self._insert_at_caret
            ),
            on_error=self._announce,  # type: ignore[attr-defined]
        )

    # -- plumbing --------------------------------------------------------- #

    def _dictionary_ready(self) -> bool:
        """The AI area is on and the route is direct; otherwise say so and open
        the account window, which is the one place the route gets fixed."""
        if not self._ai_switched_on():  # type: ignore[attr-defined]
            return False
        if self._ai_direct():  # type: ignore[attr-defined]
            return True
        self._announce(NEEDS_DIRECT_ROUTE)  # type: ignore[attr-defined]
        self.cmd_ai_chatgpt()  # type: ignore[attr-defined]
        return False

    def _run_word_tool(self, tool: WordTool) -> None:
        if not self._dictionary_ready():
            return
        text, span = self._current_word()
        if span is None:
            self._announce("Put the cursor in a word, or select one, first.")  # type: ignore[attr-defined]
            return
        sentence = word_lookup.sentence_around(text, span.start, span.end)
        self._announce("Working.")  # type: ignore[attr-defined]

        def done(answer: str, _quota: Any) -> None:
            on_use: Callable[[str], None] | None = None
            if tool.offers_choices and self._word_still_there(text, span):
                on_use = lambda chosen: self._replace_word(span, chosen)  # noqa: E731
            self._show_word_answer(tool, span.word, answer, on_use=on_use)

        self._ai_service().ask(  # type: ignore[attr-defined]
            word_tools.FEATURE,
            word_tools.word_prompt(tool, span.word, sentence),
            None,
            on_done=done,
            on_error=self._announce,  # type: ignore[attr-defined]
        )

    def _show_word_answer(
        self,
        tool: WordTool,
        word: str,
        raw: str,
        *,
        on_use: Callable[[str], None] | None,
    ) -> None:
        from quill.ui.word_tools_window import WordAnswerFrame

        parsed = word_tools.parse_answer(raw)
        choices = parsed.choices if tool.offers_choices else ()
        frame = WordAnswerFrame(
            self._ai_parent(),  # type: ignore[attr-defined]
            tool_label=tool.label,
            word=word,
            answer=parsed.answer,
            choices=choices,
            action=tool.action,
            on_use=on_use if choices else None,
            announce=self._announce,  # type: ignore[attr-defined]
            on_ask_again=(lambda: self._open_word_menu_at_caret()) if word else None,
        )
        self._show_ai_window(frame)  # type: ignore[attr-defined]

    def _open_word_menu_at_caret(self) -> None:
        """Ask Something Else: the context menu, which has the Dictionary submenu."""
        opener = getattr(self, "open_context_menu_at_caret", None)
        if callable(opener):
            opener()
        else:
            self._announce("Press the Applications key on the word for the Dictionary menu.")  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # The context menu: two submenus on the word
    # ------------------------------------------------------------------ #

    def append_word_submenus(
        self, menu: Any, text: str, caret: int, selection: tuple[int, int] | None
    ) -> bool:
        """Add *Thesaurus for "word"* and *Dictionary for "word"* to *menu*.

        Rows bind on *menu* -- the popup -- rather than on the submenus, because
        wxMSW routes a popup's commands through the menu handed to ``PopupMenu``
        and a handler bound on a submenu is one nothing ever reaches. Each
        submenu is built complete before it is appended, which is the other
        wxMSW rule (rows added after ``AppendSubMenu`` do not appear).

        Returns whether anything was added, so the caller can place a separator.
        """
        if selection is not None and selection[0] == selection[1]:
            selection = None
        span = word_lookup.find_word(text, caret, selection)
        if span is None:
            return False
        added = False
        dictionary_on = self._dictionary_enabled()
        if dictionary_on and thesaurus_engine.is_available():
            self._append_thesaurus_submenu(menu, span)
            added = True
        ai_on = bool(self._ai_host().feature_enabled("hosted_ai"))  # type: ignore[attr-defined]
        if dictionary_on or ai_on:
            self._append_dictionary_submenu(menu, span, look_up=dictionary_on, ai=ai_on)
            added = True
        return added

    def _append_thesaurus_submenu(self, menu: Any, span: WordSpan) -> None:
        shown = _escape(span.word)
        sub = wx.Menu()
        choices = word_lookup.thesaurus_choices(span.word)
        if choices is None:
            empty = sub.Append(wx.ID_ANY, f'No thesaurus entry for "{shown}"')
            empty.Enable(False)
        else:
            first, *rest = choices.senses
            for term in first.replacements[:_MENU_TOP_TERMS]:
                self._bind_replacement(menu, sub, span, term)
            if rest or choices.opposites:
                sub.AppendSeparator()
            for sense in rest:
                sense_menu = wx.Menu()
                for term in sense.replacements[:_MENU_TOP_TERMS]:
                    self._bind_replacement(menu, sense_menu, span, term)
                sub.AppendSubMenu(sense_menu, _escape(sense.label))
            if choices.opposites:
                opposites = wx.Menu()
                for term in choices.opposites[:_MENU_TOP_TERMS]:
                    self._bind_replacement(menu, opposites, span, term)
                sub.AppendSubMenu(opposites, "&Opposites")
            sub.AppendSeparator()
        summary = sub.Append(
            wx.ID_ANY, self._word_row_label("&Say Word Summary", "cmd_word_summary")
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_word_summary(), summary)
        more = sub.Append(wx.ID_ANY, self._word_row_label("&More in Thesaurus...", "cmd_thesaurus"))
        menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_thesaurus(), more)
        menu.AppendSubMenu(sub, f'&Thesaurus for "{shown}"')

    def _bind_replacement(self, popup: Any, into: Any, span: WordSpan, term: str) -> None:
        item = into.Append(wx.ID_ANY, _escape(term))

        def replace(_event: Any, chosen: str = term) -> None:
            if not self._word_still_there("", span):
                self._announce("The word has changed; nothing replaced.")  # type: ignore[attr-defined]
                return
            self._replace_word(span, chosen)
            self._announce(f'Replaced "{span.word}" with "{chosen}".')  # type: ignore[attr-defined]

        popup.Bind(wx.EVT_MENU, replace, item)

    def _append_dictionary_submenu(
        self, menu: Any, span: WordSpan, *, look_up: bool = True, ai: bool = True
    ) -> None:
        shown = _escape(span.word)
        sub = wx.Menu()
        if look_up:
            look = sub.Append(
                wx.ID_ANY, self._word_row_label(f'&Look Up "{shown}"...', "cmd_look_up")
            )
            menu.Bind(wx.EVT_MENU, lambda _e, w=span: self._look_up_word(w.word, w), look)
            if ai:
                sub.AppendSeparator()
        if not ai:
            pass
        elif not self._ai_direct():  # type: ignore[attr-defined]
            setup = sub.Append(wx.ID_ANY, "&Set Up the Dictionary (your own key or ChatGPT)...")
            menu.Bind(wx.EVT_MENU, lambda _e: self._dictionary_ready(), setup)
        else:
            handlers = {
                "define": self.cmd_word_define,
                "synonyms": self.cmd_word_synonyms,
                "simpler": self.cmd_word_simpler,
                "formal": self.cmd_word_formal,
                "vivid": self.cmd_word_vivid,
                "opposites": self.cmd_word_opposites,
                "right_word": self.cmd_word_right,
                "examples": self.cmd_word_examples,
                "origin": self.cmd_word_origin,
                "pronounce": self.cmd_word_pronounce,
                "rhymes": self.cmd_word_rhymes,
            }
            for tool in word_tools.TOOLS:
                item = sub.Append(
                    wx.ID_ANY, self._word_row_label(tool.label, f"cmd_word_{tool.id}")
                )
                menu.Bind(wx.EVT_MENU, lambda _e, run=handlers[tool.id]: run(), item)
            sub.AppendSeparator()
            explorer = sub.Append(
                wx.ID_ANY, self._word_row_label(word_tools.EXPLORE.label, "cmd_word_explorer")
            )
            menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_word_explorer(), explorer)
            find = sub.Append(
                wx.ID_ANY, self._word_row_label(word_tools.FIND_WORD.label, "cmd_find_word")
            )
            menu.Bind(wx.EVT_MENU, lambda _e: self.cmd_find_word(), find)
        menu.AppendSubMenu(sub, f'&Dictionary for "{shown}"')

    def _word_row_label(self, label: str, handler: str) -> str:
        """*label* with the key the command is actually bound to, when the host can say."""
        labeller = getattr(self, "_context_label", None)
        if callable(labeller):
            try:
                return str(labeller(label, handler))
            except Exception:  # noqa: BLE001 - a label without its key still works
                return label
        return label
