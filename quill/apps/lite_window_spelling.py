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

**A misspelling is said in the one way speech can convey it: by its letters.**
"receive" and "recieve" are the same sound, so telling a listener the word tells
them nothing -- the letters are the answer. Landing on one with Ctrl+F7 spells
it out after a pause, and the pause is the mechanism: press the next key and the
pending spelling is cancelled unheard, so a fast reader pays nothing for a
feature a careful one needs. The engine, the timings and the three ways of
saying a letter are shared with QUILL
(:mod:`quill.core.spelling.voicing`).

**While you type, it is a sound and never a voice.** Speech there would
interrupt the sentence it is commenting on. The earcon is short, quiet and
distinct, it can be silenced, and its repeat interval is tunable so one stubborn
proper noun does not become a drum.

**Ignoring is honoured everywhere, and nowhere on disk.** The context menu
(:mod:`quill.apps.lite_window_context_menu`) can say "not this one" and "not
this word, not in this document", and the answer has to hold for every route
into the checker or it is not an answer at all: the live check, Ctrl+F7 and
Shift+F7 all consult the same in-memory
:class:`~quill.core.spelling.context_menu.IgnoreList`, and it dies with the
window. An ignore that outlived the session would be a dictionary entry nobody
chose and nobody could find to remove -- teaching a word is the durable answer
and it has its own menu item.

Announcements follow GATE-13: the outcome of what the user did, and never a
control's own name, role or text -- those are the reader's to say.
"""

from __future__ import annotations

import wx

from quill.apps.lite_window_spelling_navigation import DocumentSpellingNavigationMixin
from quill.core.lite import spelling as spelling_mod
from quill.core.spelling.voicing import LiveAlertPolicy, SpellAloudPolicy, SpellAloudVoice

__all__ = ["DocumentSpellingMixin"]

#: How long typing has to stop before the live check looks at the word. A check
#: on every keystroke would judge a word the user is still in the middle of, and
#: announce a misspelling that is merely unfinished.
_LIVE_DELAY_MS = 700

#: The most suggestions offered for one word. Past this the list stops being one
#: somebody arrows through and starts being one they get lost in.
_MAX_SUGGESTIONS = 12


class DocumentSpellingMixin(DocumentSpellingNavigationMixin):
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
        #: What the personal dictionary looked like when the cache was
        #: filled, so a word taught in the other editor is noticed
        #: without a restart (bad.md S10).
        self._spell_dictionary_revision: tuple[int, int] = (0, 0)
        self._last_live_word = None
        #: When the last live alert was made, so the repeat throttle has
        #: something to measure against. Monotonic, because a clock that can go
        #: backwards would silence the alert until it caught up again.
        self._last_live_alert_at = 0.0
        #: The one pending "and here is how it is spelled". Rebuilt whenever the
        #: settings change, so a listener who shortens the pause hears the new
        #: one on the next word rather than after a restart.
        self._spell_voice = SpellAloudVoice(
            self._announce, SpellAloudPolicy.from_settings(self.app.settings), wx.CallLater
        )

    def refresh_spelling_voice(self) -> None:
        """Re-read the voicing preferences. Called after Preferences is saved."""
        self._spell_voice.policy = SpellAloudPolicy.from_settings(self.app.settings)

    def _live_alert_policy(self) -> LiveAlertPolicy:
        """What the as-you-type alert should do. Read fresh, never cached: it is
        consulted once per pause in typing, and a stale copy would ignore a
        switch the user has just flipped."""
        return LiveAlertPolicy.from_settings(self.app.settings)

    def _spelling_enabled(self) -> bool:
        """Is the whole area switched on in Customize Features?"""
        return bool(self.app.feature_enabled("spelling"))

    def _spell_dictionary(self) -> set[str]:
        """The taught words for this document, cached but not stale.

        Cached because it is consulted on every live check: going to disk each
        time somebody stops typing would put a file read in the typing path.

        Keyed on the personal dictionary's **revision** since 2026-09-17, which
        is what makes ``share_quill_dictionary`` mean what it says. With sharing
        on, both editors read and write one ``personal.json`` -- and a word
        taught in QUILL stayed underlined here until QuillLite was restarted,
        which makes a shared dictionary look broken rather than shared
        (bad.md S10). The check is one ``stat``; the re-read only happens when
        the file actually moved.
        """
        from quill.core.spellcheck import personal_dictionary_revision

        revision = personal_dictionary_revision(
            spelling_mod.dictionary_dir(self.app.settings, self.app.data_dir)
        )
        if self._spell_dictionary_cache is None or self._spell_dictionary_revision != revision:
            self._spell_dictionary_cache = spelling_mod.load_dictionary(
                self.app.settings, self.app.data_dir, self.path
            )
            self._spell_dictionary_revision = revision
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
        """Look at the word you have just finished, and report it if it is wrong.

        ``misspelling_behind``, not ``misspelling_at``. The latter matches only a
        word *beginning exactly at the caret*, which typing left to right never
        produces -- the caret is always at or past the end of the word just
        finished -- so this whole feature was unreachable until 2026-09-10:
        settings, earcon, status line and all, and never once fired. The new
        helper asks the question the surface has, and requires a terminator, so
        it never judges a word somebody is still in the middle of typing.

        Bounded either way: it walks left over a handful of characters and
        matches one word. Nothing here scans the document.
        """

        from quill.core.spellcheck import misspelling_behind
        from quill.core.spellcheck_live import live_alert_suppressed

        text = self.doc_text.text
        caret = self.control.GetInsertionPoint()
        item = misspelling_behind(text, caret, self._spell_dictionary())
        if item is None or self.spell_ignores.skips(text, item):
            self._last_live_word = None
            return
        # URLs, code spans and fenced blocks are wall-to-wall false positives
        # even inside prose -- QUILL's own rule, applied here for the same
        # reason: every one of them costs a spoken interruption.
        if live_alert_suppressed(text, item.start, item.end):
            self._last_live_word = None
            return
        self._report_misspelling(text, item)

    def _report_misspelling(self, _text: str, item: object) -> None:
        """Say a misspelling once: status bar, earcon, and speech if asked.

        One implementation for both paths -- the as-you-type check and the
        caret-move check (:meth:`check_spelling_at_caret`) -- because the two
        differ only in *which* word they found. Sharing the throttle state is
        the point: typing a word and then arrowing back onto it is one word, and
        a listener should hear about it once.
        """
        import time

        word = str(getattr(item, "word", ""))
        start = int(getattr(item, "start", 0))
        policy = self._live_alert_policy()
        key = (word.lower(), start)
        now = time.monotonic()
        if key == self._last_live_word and (
            policy.repeat_ms <= 0 or (now - self._last_live_alert_at) * 1000 < policy.repeat_ms
        ):
            return  # already said, and not long enough ago to say again
        self._last_live_word = key
        self._last_live_alert_at = now
        # The status bar, not the voice -- unless the user has asked otherwise.
        # A misspelling is not the outcome of what they just did (they were
        # typing, or moving), so speaking it interrupts the very thing it is
        # commenting on. The Message cell holds it, F6 reads it, the Spelling
        # menu acts on it, and the earcon is what makes it noticeable without a
        # word being said.
        message = f'Possible misspelling: "{word}"'
        self._set_status_message(message)
        # A tone asked for and not available falls through to the words, never to
        # silence: the setting chooses between two kinds of feedback, and the
        # house rule (CLAUDE.md, action_feedback) is that it may never choose
        # down to none. This one went quiet on a machine with no sound pack, so
        # a listener who had asked for a tone and got nothing had no way to tell
        # the alert apart from a clean document (bad.md S12).
        from quill.core.sound_events import SoundEvent

        has_clip = self._has_sound_for(SoundEvent.SPELLING_ALERT)
        if policy.sound and has_clip:
            self._play_spelling_alert()
        if policy.speech or (policy.sound and not has_clip):
            self._announce(message)

    #: The keys that move the caret without changing the text. A caret that
    #: arrived on one of these is *navigating*, and the word it landed on is the
    #: one to report; a caret that arrived any other way is typing, and the word
    #: behind it is. 0 is the mouse (EVT_LEFT_UP carries no key code), which is
    #: navigation by any reading.
    _NAVIGATION_KEYS = frozenset({
        0,
        wx.WXK_LEFT,
        wx.WXK_RIGHT,
        wx.WXK_UP,
        wx.WXK_DOWN,
        wx.WXK_HOME,
        wx.WXK_END,
        wx.WXK_PAGEUP,
        wx.WXK_PAGEDOWN,
        wx.WXK_NUMPAD_LEFT,
        wx.WXK_NUMPAD_RIGHT,
        wx.WXK_NUMPAD_UP,
        wx.WXK_NUMPAD_DOWN,
        wx.WXK_NUMPAD_HOME,
        wx.WXK_NUMPAD_END,
        wx.WXK_NUMPAD_PAGEUP,
        wx.WXK_NUMPAD_PAGEDOWN,
    })

    def check_spelling_at_caret(self, key_code: int = 0) -> None:
        """Report the misspelling the caret just landed **on**.

        Reported 2026-09-12: "if I arrow to the word it does not make a sound
        either by moving with the arrow keys or moving by word", while moving to
        the *line* did make one. Both halves of that were this function's
        absence. The only spelling check QuillLite ran was the as-you-type one,
        which asks ``misspelling_behind`` -- the word you have just *finished* --
        and every key including an arrow restarted it. Arrow down onto a line and
        the word behind the caret is often the misspelled one, so it fired;
        arrow right into that same word and there is no finished word behind the
        caret at all, so it did not. The word the caret is standing in was never
        the question being asked.

        It is now, on a caret move: ``misspelling_at_position``, the "which word
        am I on" helper. Navigation keys only -- during typing this would judge
        every word on its way to being right, which is exactly what
        ``misspelling_behind`` exists to avoid.

        The alert itself is shared with the typing path, including its repeat
        throttle, so arrowing back and forth over one word does not drum and
        typing a word then arrowing onto it does not say it twice.
        """
        if key_code not in self._NAVIGATION_KEYS:
            return
        if not (self._spelling_enabled() and self._live_spelling):
            return
        try:
            from quill.core.spellcheck import misspelling_at_position

            # The mirror, not the control: this runs on every navigation key-up,
            # and marshalling the whole buffer out of the RichEdit to look at
            # one word was O(N) per arrow press (bad.md S8, V3).
            text = self.doc_text.text
            item = misspelling_at_position(
                text, int(self.control.GetInsertionPoint()), self._spell_dictionary()
            )
            if item is None:
                return
            self._report_misspelling(text, item)
        except Exception:  # noqa: BLE001 - a spell check must never break the caret
            pass

    def _play_spelling_alert(self) -> None:
        """The earcon. Never a bell fallback, and never silence either.

        QUILL falls back to ``wx.Bell`` when no pack is loaded, and that is
        wrong here even though QUILL always has a sound stack: the system bell
        is a loud, undismissable, wrong-sounding noise to attach to something
        this frequent. But *silence* was the other wrong answer, and it is the
        one this had -- a listener who asked for a tone and got nothing could
        not tell the alert from a clean document. The caller falls through to
        the words instead, which is the house rule for every feedback mode
        (bad.md S12).
        """
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import post_cue

        post_cue(SoundEvent.SPELLING_ALERT)

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
            # QuillLite's own folder, or QUILL's when the listener has asked to
            # share it. Without this the review wrote into QUILL's regardless,
            # so a word taught through F7 was flagged again next session and a
            # Quill folder appeared on a machine that had never had QUILL
            # (bad.md S1). The other two add routes always passed it.
            personal_dir=spelling_mod.dictionary_dir(self.app.settings, self.app.data_dir),
            # The session ignores, which F7 did not honour: the docstring on
            # this module claimed "every route" and this was the route that
            # was not (bad.md S6).
            ignores=self.spell_ignores,
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
        from quill.core.spellcheck import misspelling_at_position, suggest_words

        if not self._require_spelling():
            return
        text = self.control.GetValue()
        # The word the caret is *in*, not one starting exactly under it.
        # ``misspelling_at`` is the as-you-type helper and answers only for a
        # word beginning at the caret, so Shift+F7 in the middle of a misspelled
        # word used to say there was no misspelling at the cursor -- which is
        # every press that was not made in the instant after typing the space.
        # QUILL has always used the walk-left form here; this is QuillLite
        # catching up rather than a new idea.
        item = misspelling_at_position(
            text, self.control.GetInsertionPoint(), self._spell_dictionary()
        )
        if item is None or self.spell_ignores.skips(text, item):
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
                "document. Escape leaves the word as it is. Each suggestion is "
                "spelled out after a short pause; arrow on to skip it."
            ),
            rows=[(word, word) for word in suggestions],
            # Eight near-identical spellings is the exact place a listener
            # cannot tell one row from the next: the reader says "receive" for
            # the right one and "recieve" for the wrong one, and those are the
            # same sound. So each row spells itself out after a pause, and
            # arrowing on cancels it -- a fast pass down the list stays silent.
            on_highlight=self._spell_suggestion,
        )
        self._spell_voice.cancel()
        if not isinstance(chosen, str):
            self.control.SetFocus()
            return
        self.control.Replace(item.start, item.end, chosen)
        self.control.SetInsertionPoint(item.start + len(chosen))
        self._set_modified(True)
        self._touch_status()
        self._announce("Replaced with " + chosen)
        self.control.SetFocus()

    def _spell_suggestion(self, suggestion: object) -> None:
        """Queue the letters of the suggestion the user has arrowed onto."""
        policy = self._spell_voice.policy
        if not policy.suggestions:
            return
        self._spell_voice.spell_later(str(suggestion), delay_ms=policy.suggestion_delay_ms)

    def _spell_after_landing(self, word: str) -> None:
        """Queue the letters of *word*, if the listener has asked for them."""
        policy = self._spell_voice.policy
        if not policy.navigation:
            self._spell_voice.cancel()
            return
        self._spell_voice.spell_later(word, delay_ms=policy.navigation_delay_ms)

    def cmd_add_word_to_dictionary(self) -> None:
        """Alt+F7: teach the word at the caret, for good.

        Written to QuillLite's own dictionary unless Preferences says to share
        QUILL's -- and it says which, because "added to dictionary" does not
        tell you where it went when there are two of them.
        """
        from quill.core.spellcheck import misspelling_at_position

        if not self._require_spelling():
            return
        text = self.control.GetValue()
        # The walk-left form, for the reason spelled out in
        # cmd_spell_word_at_cursor: Alt+F7 has to teach the word the caret is
        # in, not only one that happens to start under it.
        item = misspelling_at_position(
            text, self.control.GetInsertionPoint(), self._spell_dictionary()
        )
        if item is None or self.spell_ignores.skips(text, item):
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

    def cmd_spelling_voice_settings(self) -> None:
        """Ctrl+Alt+Shift+F7: how a misspelling is said, in one window.

        Not gated behind :meth:`_require_spelling`, and that is deliberate: the
        settings survive the area being switched off, and somebody who has just
        turned spelling back on should be able to reach the window that decides
        how loud it is going to be. Every other command here acts on a document
        and is rightly refused; this one is a preference.
        """
        from quill.apps.lite_spelling_voice_dialog import edit_spelling_voice

        changed = edit_spelling_voice(self, self.app.settings, announce=self._announce)
        self.control.SetFocus()
        if not changed:
            return
        self.app.save_settings()
        # Every open document, not just this one: the voicing is a statement
        # about how you want to be spoken to, and a pause that is 600 ms in
        # document 2 and 900 ms in document 3 is a pause you cannot learn.
        for frame in self.app.frames:
            refresh = getattr(frame, "refresh_spelling_voice", None)
            if callable(refresh):
                refresh()
        self._announce("Spelling announcements saved")

    # ------------------------------------------------------------------ #
    # Shared guard
    # ------------------------------------------------------------------ #

    def _require_spelling(self) -> bool:
        """True when the area is on; says why not when it is off."""
        if self._spelling_enabled():
            return True
        self._announce("Spell check is switched off in Customize Features")
        return False
