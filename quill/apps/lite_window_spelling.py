"""Spelling in QuillLite: F7 to review, and a quiet check while you type.

None of the checking is written here. The wordlist, the suggestions and the
guided review are QUILL's (:mod:`quill.core.spellcheck`,
:mod:`quill.core.spelling`, and
:class:`~quill.ui.spelling_review_dialog.SpellingReviewDialog`), reached through
the same helper the Mastodon compose box uses. What this mixin owns is the six
commands and the one decision QUILL does not have to make: **when to stay
quiet.**

That decision is the whole reason this feature is worth shipping rather than
merely having. WordPad never had a spell checker at all; Notepad gained one in
2024 and immediately had to add the exception, because a live checker in
``settings.json`` flags every key and a live checker in ``main.py`` flags every
identifier. For a sighted user those are underlines to ignore. For the person
this editor is built for they are a status line each, and a feature that
interrupts fifty times a minute is not a feature that can be left on. So the
default follows the extension (:mod:`quill.core.spellcheck_filetypes`), decided
once per document.

Three things follow from that, and each is deliberate:

* **The state is per document, not per app.** Open a letter and a config file
  side by side and the letter is checked while the config file is not. Turning
  it on in the config file keeps it on there, and does not turn it on
  everywhere.
* **The state is announced when it is not the obvious one.** A checker that is
  silently off is indistinguishable from a checker that is broken, so opening a
  file the rule skips says so once, and Check While Typing carries a check mark
  that reads the true state.
* **F7 is never gated.** A default answers what to do when nobody has said
  anything; pressing F7 is saying something. Somebody who runs the review on a
  Python file meant to.

Announcements follow GATE-13: the outcome of what the user did, and never a
control's own name, role or text -- those are the reader's to say.
"""

from __future__ import annotations

import wx

from quill.core.lite import spelling as spelling_mod

__all__ = ["DocumentSpellingMixin"]

#: How long typing has to stop before the live check looks at the word. A check
#: on every keystroke would judge a word the user is still in the middle of, and
#: announce a misspelling that is merely unfinished.
_LIVE_DELAY_MS = 700

#: The most suggestions offered for one word. Past this the list stops being one
#: somebody arrows through and starts being one they get lost in.
_MAX_SUGGESTIONS = 12


class DocumentSpellingMixin:
    """The Spelling menu, and the quiet check behind it."""

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #

    def _init_spelling(self) -> None:
        """Set the live-check state for this document. Called once, on open.

        Two gates, and both have to be open: the app-wide setting (a
        preference) and the file-type rule (a fact about this document). A
        document whose extension says "code" starts unchecked even when the
        setting says check, which is the entire point of the rule.
        """
        self._live_spelling = bool(
            getattr(self.app.settings, "spell_check_while_typing", True)
        ) and spelling_mod.initial_live_check(self.path)
        self._spell_timer = None
        self._spell_dictionary_cache = None
        self._last_live_word = None

    def _spelling_enabled(self) -> bool:
        """Is the whole area switched on in Customize Features?"""
        return bool(self.app.feature_enabled("spelling"))

    def _spell_dictionary(self) -> set[str]:
        """The taught words for this document, read once and kept.

        Cached because it is consulted on every live check: going to disk each
        time somebody stops typing would put a file read in the typing path.
        """
        if self._spell_dictionary_cache is None:
            self._spell_dictionary_cache = spelling_mod.load_dictionary(
                self.app.settings, self.app.data_dir, self.path
            )
        return self._spell_dictionary_cache

    def _forget_spell_dictionary(self) -> None:
        """Drop the cache, after a word is taught or the file is saved as another."""
        self._spell_dictionary_cache = None

    def announce_spelling_state_if_skipped(self) -> None:
        """Say once, on open, that this file type is not checked.

        The one announcement this feature makes on its own. Without it the
        difference between "off for this file type" and "broken" is invisible,
        and nobody can act on a silence they cannot explain.
        """
        if not self._spelling_enabled() or self._live_spelling:
            return
        if spelling_mod.skipped_as_code(self.path):
            self._announce(
                "Spell check while typing is off for this file type. "
                "Control Alt F7 turns it on, F7 reviews the document."
            )

    # ------------------------------------------------------------------ #
    # The live check
    # ------------------------------------------------------------------ #

    def schedule_live_spell_check(self) -> None:
        """Restart the pause timer. Called from the typing path, per keystroke.

        Cheap on purpose: everything expensive happens in
        :meth:`_run_live_spell_check`, once typing has actually stopped.
        """
        if not (self._spelling_enabled() and self._live_spelling):
            return
        if self._spell_timer is None:
            self._spell_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_spell_timer, self._spell_timer)
        self._spell_timer.Start(_LIVE_DELAY_MS, oneShot=True)

    def _on_spell_timer(self, _event: wx.TimerEvent) -> None:
        try:
            self._run_live_spell_check()
        except Exception:  # noqa: BLE001 - a spell check must never break typing
            pass

    def _run_live_spell_check(self) -> None:
        """Look at the word behind the caret, and say so if it is not a word.

        Bounded to the word the caret is in rather than scanning forward: an
        unbounded search would walk a clean document to its end on every pause
        in typing, for an answer this caller would then discard.
        """
        from quill.core.spellcheck import misspelling_at
        from quill.core.spellcheck_live import live_alert_suppressed

        text = self.control.GetValue()
        caret = self.control.GetInsertionPoint()
        item = misspelling_at(text, caret, self._spell_dictionary())
        if item is None:
            self._last_live_word = None
            return
        # URLs, code spans and fenced blocks are wall-to-wall false positives
        # even inside prose -- QUILL's own rule, applied here for the same
        # reason: every one of them costs a spoken interruption.
        if live_alert_suppressed(text, item.start, item.end):
            self._last_live_word = None
            return
        key = (item.word.lower(), item.start)
        if key == self._last_live_word:
            return  # already said; do not repeat it on every pause
        self._last_live_word = key
        # The status bar, not the voice. A misspelling is not the outcome of
        # what the user just did -- they were typing -- so speaking it would
        # interrupt the very thing it is commenting on. The Message cell holds
        # it, F6 reads it, and the Spelling menu acts on it.
        self._set_status_message(f'Possible misspelling: "{item.word}"')

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #

    def cmd_toggle_live_spelling(self) -> None:
        """Turn the as-you-type check on or off, for this document only."""
        if not self._require_spelling():
            return
        self._live_spelling = not self._live_spelling
        self._last_live_word = None
        if not self._live_spelling and self._spell_timer is not None:
            self._spell_timer.Stop()
        self._announce(
            "Spell check while typing on" if self._live_spelling else "Spell check while typing off"
        )
        self._sync_check_items()

    def cmd_spell_review(self) -> None:
        """F7: the guided review over the whole document.

        Deliberately never gated by the file-type rule. That rule decides what
        happens when nobody has said anything, and this is somebody saying
        something.
        """
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.spell_review import review_textctrl

        if not self._require_spelling():
            return
        review_textctrl(
            wx,
            self,
            self.control,
            dictionary=self._spell_dictionary(),
            announce_fn=self._announce,
            settings=self.app.settings,
            show_modal=show_modal_dialog,
            scope_label="document",
            document_path=self.path,
        )
        self._forget_spell_dictionary()  # the review can teach words
        self._touch_status()
        self.control.SetFocus()

    def cmd_spell_word_at_cursor(self) -> None:
        """Shift+F7: suggestions for the word the caret is in.

        The narrow, common case the full review is too heavy for -- one word
        somebody already knows is wrong. A list rather than a cycle, because a
        list can be arrowed through and reconsidered.
        """
        from quill.apps.lite_dialogs import choose_from_rows
        from quill.core.spellcheck import misspelling_at, suggest_words

        if not self._require_spelling():
            return
        text = self.control.GetValue()
        item = misspelling_at(text, self.control.GetInsertionPoint(), self._spell_dictionary())
        if item is None:
            self._announce("No misspelling at the cursor")
            return
        suggestions = suggest_words(item.word, self._spell_dictionary(), limit=_MAX_SUGGESTIONS)
        if not suggestions:
            self._announce("No suggestions for " + item.word)
            return
        chosen = choose_from_rows(
            self,
            title="Spelling Suggestions",
            label="Suggestions for " + item.word + ":",
            help_text=(
                "Choose a spelling and press Enter to replace the word in the "
                "document. Escape leaves the word as it is."
            ),
            rows=[(word, word) for word in suggestions],
        )
        if not isinstance(chosen, str):
            self.control.SetFocus()
            return
        self.control.Replace(item.start, item.end, chosen)
        self.control.SetInsertionPoint(item.start + len(chosen))
        self._set_modified(True)
        self._touch_status()
        self._announce("Replaced with " + chosen)
        self.control.SetFocus()

    def cmd_next_misspelling(self) -> None:
        """Ctrl+F7: move to the next word that is not in the dictionary."""
        self._go_to_misspelling(forward=True)

    def cmd_previous_misspelling(self) -> None:
        """Ctrl+Shift+F7: move to the previous one."""
        self._go_to_misspelling(forward=False)

    def _go_to_misspelling(self, *, forward: bool) -> None:
        from quill.core.spellcheck import next_misspelling, previous_misspelling

        if not self._require_spelling():
            return
        text = self.control.GetValue()
        caret = self.control.GetInsertionPoint()
        finder = next_misspelling if forward else previous_misspelling
        item = finder(text, caret, self._spell_dictionary())
        if item is None:
            self._announce("No further misspellings" if forward else "No earlier misspellings")
            return
        # Selected rather than merely arrived at: the word is then what Shift+F7
        # acts on, and what the reader reads on arrival.
        self.control.SetSelection(item.start, item.end)
        self._touch_status()
        self._announce("Misspelling: " + item.word)

    def cmd_add_word_to_dictionary(self) -> None:
        """Alt+F7: teach the word at the caret, for good.

        Written to QuillLite's own dictionary unless Preferences says to share
        QUILL's -- and it says which, because "added to dictionary" does not
        tell you where it went when there are two of them.
        """
        from quill.core.spellcheck import misspelling_at

        if not self._require_spelling():
            return
        text = self.control.GetValue()
        item = misspelling_at(text, self.control.GetInsertionPoint(), self._spell_dictionary())
        if item is None:
            self._announce("No misspelling at the cursor")
            return
        written = spelling_mod.add_word(item.word, self.app.settings, self.app.data_dir, self.path)
        if not written:
            self._announce("Could not save " + item.word + " to the dictionary")
            return
        self._forget_spell_dictionary()
        self._last_live_word = None
        shared = bool(getattr(self.app.settings, "share_quill_dictionary", False))
        where = "QUILL's shared dictionary" if shared else "your QuillLite dictionary"
        self._announce("Added " + item.word + " to " + where)

    # ------------------------------------------------------------------ #
    # Shared guard
    # ------------------------------------------------------------------ #

    def _require_spelling(self) -> bool:
        """True when the area is on; says why not when it is off."""
        if self._spelling_enabled():
            return True
        self._announce("Spell check is switched off in Customize Features")
        return False
