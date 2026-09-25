"""How QUILL says a misspelling: the alert while you type, and the letters.

Its own module for two reasons. ``main_frame_spellcheck.py`` is at its GATE-11
ceiling, and -- the better reason -- "how is a misspelling *voiced*" is one
subject with one set of rules, and it was previously split between a live-alert
method, a hard-coded throttle and nothing at all on the navigation keys.

**A misspelling is the one thing in an editor that speech cannot convey.**
"receive" and "recieve" are the same sound. A sighted user gets a red squiggle
under the wrong letters; a listener told "not in dictionary, recieve" has been
handed a word they cannot tell from the correct one. The letters are the answer,
and this module is about delivering them without becoming a nuisance.

**While you type, the alert is a sound and not a voice.** Speech there
interrupts the very sentence it is commenting on, and somebody composing a
paragraph is the person least able to afford it. The earcon is short and quiet,
it can be silenced, its repeat interval is a setting, and speaking it as well is
available for anyone who wants that.

**When you land on one, the word comes from the screen reader and the letters
come from here**, after a pause -- a separate utterance, because a single one
cannot be interrupted and somebody who recognised the word from its first
syllable would have to sit through eleven more letters. Press the next key and
the pending spelling is cancelled unheard, which is what makes the feature free
for a fast reader and complete for a careful one.

Every timing and every choice is shared with QUILL Lite through
:mod:`quill.core.spelling.voicing`, which owns the policies and the one-pending-
utterance scheduler and knows nothing about wx.
"""

from __future__ import annotations

import time

from quill.core.spelling.voicing import LiveAlertPolicy, SpellAloudPolicy, SpellAloudVoice

__all__ = ["SpellVoiceMixin"]


def _call_later(frame: object) -> object | None:
    """``wx.CallLater``, or None where there is no wx to ask.

    The frame's own ``_wx`` first, because a test double supplies a stand-in
    there and the real frame caches the module. None when neither is available:
    a missing timer means the *delayed* half of a spell-aloud is skipped, which
    is exactly what :class:`SpellAloudVoice` is built to cope with, and is far
    better than an AttributeError raised in the middle of a keystroke.
    """
    wx_module = getattr(frame, "_wx", None)
    if wx_module is None:
        try:
            import wx as wx_module  # type: ignore[no-redef]
        except Exception:  # noqa: BLE001 - headless is a normal place to be
            return None
    return getattr(wx_module, "CallLater", None)


class SpellVoiceMixin:
    """The as-you-type alert, and the letters that follow a landing."""

    # ------------------------------------------------------------------ #
    # Spelling a word out
    # ------------------------------------------------------------------ #

    def spell_voice(self) -> SpellAloudVoice:
        """The one pending "and here is how it is spelled", for this frame.

        Built once and re-policied on every call, so a listener who shortens the
        pause in Preferences hears the new one on the next word rather than
        after a restart. One instance, because scheduling a second spelling has
        to cancel the first: travelling through a document with Ctrl+F7 should
        be quiet, not a queue of spellings for words already left behind.
        """
        policy = SpellAloudPolicy.from_settings(self.settings)
        voice = getattr(self, "_spell_aloud_voice", None)
        if voice is None:
            voice = SpellAloudVoice(self._announce_result, policy, _call_later(self))
            self._spell_aloud_voice = voice
        else:
            voice.policy = policy
        return voice

    def _spell_after_landing(self, word: str) -> None:
        """Spell the word you have just landed on, after a pause.

        The reader has already said it, because the word is selected -- and for
        a misspelling that is the one piece of information that does not help.
        """
        voice = self.spell_voice()
        if not voice.policy.navigation:
            voice.cancel()
            return
        voice.spell_later(word, delay_ms=voice.policy.navigation_delay_ms)

    def _announce_spellcheck_hint(self, text: str | None = None) -> None:
        """The as-you-type alert: a sound, a status line, and silence."""
        from quill.core.spellcheck_filetypes import is_code_filename
        from quill.core.spellcheck_live import live_alert_suppressed

        if not getattr(self.settings, "announce_spelling", True):
            self._last_live_misspelling_feedback = None
            return
        dictionary = self._spell_dictionary()
        cursor = self.editor.GetInsertionPoint()
        if text is None:  # #1346: reuse the typing path's single buffer read.
            text = self.editor.GetValue()
        # Bounded, for the reason #1346 round 3 gave: the unbounded
        # next_misspelling scanned a clean document from the caret to its end on
        # every pause in typing, for an answer this caller then discarded.
        #
        # Bounded to the *right* word only since 2026-09-10, though. This asked
        # ``misspelling_at``, which matches a word beginning **exactly at the
        # caret** -- and typing left to right the caret is always at or past the
        # *end* of the word just finished, so the condition was never true. The
        # earcon, the status line and the settings all existed and none of them
        # had ever fired. ``misspelling_behind`` asks what this surface actually
        # wants to know: what word did you just finish, and is it a word?
        from quill.core.spellcheck import misspelling_behind

        item = misspelling_behind(text, cursor, dictionary)
        if item is None or self.spell_ignores().skips(text, item):
            self._last_live_misspelling_feedback = None
            return
        if live_alert_suppressed(text, item.start, item.end):
            self._last_live_misspelling_feedback = None
            return
        # Quiet in code, by the file's name. live_alert_suppressed above rules
        # out a *region* -- a URL, a code span, a fence -- which is the right
        # answer inside prose. It cannot help in main.py, where the whole file
        # is the region: every identifier is a word no dictionary has, and each
        # one costs a screen-reader user an earcon and a status line. The
        # explicit F7 review is deliberately not gated here; that one was asked
        # for, and somebody who runs it on a source file means it.
        if getattr(self.settings, "spellcheck_skip_code_files", True) and is_code_filename(
            self.document.path
        ):
            self._last_live_misspelling_feedback = None
            return
        key = (item.word.lower(), item.start, item.end)
        now = time.monotonic()
        # The repeat throttle is a setting now rather than a literal 0.75: that
        # number was right for whoever wrote it and is a drum or a silence for
        # somebody else. Zero means alert every time, because a throttle that
        # cannot be switched off eventually hides something.
        policy = LiveAlertPolicy.from_settings(self.settings)
        if (
            self._last_live_misspelling_feedback == key
            and policy.repeat_ms > 0
            and (now - self._last_live_misspelling_feedback_at) * 1000 < policy.repeat_ms
        ):
            return
        self._last_live_misspelling_feedback = key
        self._last_live_misspelling_feedback_at = now
        if policy.sound:
            self._play_spelling_alert()
        # Written, not spoken. `_set_status` always announces, so until
        # 2026-09-16 this line was read aloud whether or not
        # `spelling_alert_speech` was on -- and TWICE when it was on, once here
        # and once below. The setting therefore meant nothing in QUILL and the
        # opposite of nothing in QUILL Lite, whose status write is silent
        # (bad.md S2). The quiet write keeps the status bar honest for anybody
        # reviewing it, which is GATE-12's requirement, without speaking.
        self._set_status_quiet(f'Possible misspelling: "{item.word}"')
        # Off by default, and deliberately: speech here interrupts the sentence
        # it is commenting on. Available for anyone who wants it anyway.
        if policy.speech:
            self._announce_result(f'Possible misspelling: "{item.word}"')

    def _play_spelling_alert(self) -> None:
        # Prefer the pack earcon; fall back to the system bell only when the
        # sound system is off or the active pack has no spelling_alert sound,
        # so the alert is never silently lost.
        from quill.core.sound_events import SoundEvent
        from quill.ui import sound_manager

        if sound_manager.is_active() and str(SoundEvent.SPELLING_ALERT) in (
            sound_manager.get_loaded_events()
        ):
            sound_manager.post_sound(SoundEvent.SPELLING_ALERT)
            return
        bell = getattr(self._wx, "Bell", None)
        if callable(bell):
            bell()
