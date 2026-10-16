"""Command mode in the controller: the command word, one command, command mode.

D-1 (the rules are :mod:`~quill.core.windows_dictation.command_mode`'s). Kept
out of :mod:`~quill.core.windows_dictation.controller` because that module is at
its GATE-11 ceiling; the controller asks one question of this mixin for every
phrase it writes, :meth:`CommandModeMixin._dictate`, **before**
:func:`~quill.core.windows_dictation.composer.compose` runs, and one for every
phrase heard while paused for its field, :meth:`CommandModeMixin._paused_parse`.

**Never typed.** An utterance classified as a command -- after the command
word, after the Command Key, or in command mode -- goes to the command path and
nowhere else. If it is not a command, nothing is written: the error cue and
:func:`~quill.core.windows_dictation.command_mode.not_a_command`, and "type
that" writes it if the person meant it. A command that finds nothing to act on
("select the cat" with no cat) says "Not found." instead of writing the words,
as it does without the command word (:meth:`_write_instead`). The one thing a
command ever puts into the document is what it is for: a snippet, a clip.

**Three ways in.**

* The **command word**: one command, said in the same breath. A rising tone,
  no words; what the command does is what gets spoken. The word on its own,
  then a pause, arms one command, as the Command Key does.
* The **Command Key** (:meth:`command_key`): the next utterance is a command,
  with or without the word. Pressed again before one is said, **command mode**;
  pressed in command mode, back to dictation.
* **Command mode** ("QUILL command mode"): a tone and "Command mode." once;
  every utterance is a command until "dictation mode" (at once) or the timeout
  (``windows_dictation_command_timeout``, 8 seconds, 5 to 30) with no command,
  which plays a falling tone and says nothing. The next utterance is dictated.
  The status cell and QUILL Transcribe's state line say "Command mode"
  (:attr:`command_mode_text`), which a braille display shows; it is not spoken
  again (GATE-13).

**Strict mode** (``windows_dictation_command_prefix_required``, on in QUILL
Transcribe, off in the editors): a bare command is written as words, except the
stop phrase and "stop dictation", which always work, and "stop spelling" while
spelling, which is the way out of it.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.command_mode import (
    COMMAND_MODE_SAID,
    DICTATION_MODE_SAID,
    SAY_A_COMMAND,
    command_only,
    escape_literal_prefix,
    not_a_command,
    split_phrase,
)
from quill.core.windows_dictation.parser import ParsedPhrase, Piece, RecognizedPhrase, parse
from quill.core.windows_dictation.ports import Moment
from quill.core.windows_dictation.vocabulary import Command
from quill.core.windows_dictation.voice_commands import VoiceCommandsMixin
from quill.core.windows_dictation.wake import wake_words

if TYPE_CHECKING:
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["PAUSED_REFUSAL", "CommandModeMixin"]

#: A command word said while dictation is paused for its field.
PAUSED_REFUSAL = "Dictation is paused. Resume it first."


def _as_words(parsed: ParsedPhrase, phrase: RecognizedPhrase) -> ParsedPhrase:
    """*parsed* written as words: a command said where commands do not count."""
    if parsed.pieces:
        return ParsedPhrase(pieces=parsed.pieces)
    return ParsedPhrase(pieces=tuple(Piece(word.display) for word in phrase.words if word.display))


class CommandModeMixin(VoiceCommandsMixin):
    """The command word, the Command Key and command mode, on the controller."""

    _clock: Callable[[], float]
    _state: Any

    #: The next utterance is a command (the Command Key, or the word alone).
    _command_once = False
    #: Command mode: every utterance is a command until it times out.
    _command_sticky = False
    #: When the armed command or command mode lapses, by ``_clock``.
    _command_until = 0.0
    #: Which arming a scheduled timeout belongs to, and its handle.
    _command_round = 0
    _command_handle: Any = None
    #: A command is running: a search that finds nothing writes nothing.
    _commanding = False
    #: The last utterance refused as not a command, for "type that".
    _command_refused: RecognizedPhrase | None = None

    @property
    def active(self) -> bool:  # provided by the controller
        raise NotImplementedError

    def _parse(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> ParsedPhrase:
        raise NotImplementedError  # provided by the controller

    def _fail(self, message: str, preferences: DictationPreferences) -> None:
        raise NotImplementedError  # provided by the controller

    # -- what the host shows -------------------------------------------------- #

    @property
    def command_mode_text(self) -> str:
        """For the status cell and the tray: "Command mode", "Waiting for a
        command", or ``""``."""
        if self._command_sticky:
            return "Command mode"
        if self._command_once:
            return "Waiting for a command"
        return ""

    @property
    def command_mode(self) -> bool:
        return self._command_sticky

    # -- the Command Key ------------------------------------------------------- #

    def command_key(self) -> None:
        """One command; pressed again before it, command mode; in command mode,
        back to dictation. The host starts dictation first when it is off."""
        if not self.active:
            return
        preferences = self._preferences()
        if self._command_sticky:
            self._command_leave(preferences, said=DICTATION_MODE_SAID)
        elif self._command_once:
            self._command_enter(preferences)
        else:
            self._command_arm(preferences)

    # -- the controller's hooks ------------------------------------------------ #

    def _command_reset(self) -> None:
        """A session starts or ends: no command armed, no command mode."""
        self._command_stop_timer()
        self._command_once = False
        self._command_sticky = False
        self._command_refused = None

    def _end_voice_modes(self) -> None:
        super()._end_voice_modes()
        self._command_reset()

    def _dictate(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> None:
        """One phrase, before anything is composed: a command, or dictation."""
        if preferences.profile != "transcript":
            rest = self._command_split(phrase, preferences)
            if rest is not None:
                self._command_utterance(rest, preferences)
                return
            phrase = escape_literal_prefix(phrase, preferences.command_prefix)
        self._apply(
            self._strict(self._parse(phrase, preferences), phrase, preferences), preferences
        )

    def _paused_parse(
        self, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> ParsedPhrase | None:
        """What a phrase heard while paused for its field means. ``None`` when it
        was meant for QUILL and is not something a paused session does: it is
        answered here, and never held to be typed later."""
        rest = self._command_split(phrase, preferences)
        if rest is None:
            phrase = escape_literal_prefix(phrase, preferences.command_prefix)
            return self._strict(self._parse(phrase, preferences), phrase, preferences)
        parsed = parse(rest, vocabulary=preferences.vocabulary)
        if parsed.command is None:
            self._say(PAUSED_REFUSAL)
            return None
        return parsed

    def _write_instead(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        """A command found nothing: written as text, unless it was meant for
        QUILL, when nothing is written."""
        if self._commanding:
            self._say("Not found.")
            return
        super()._write_instead(parsed, preferences)

    # -- telling commands from dictation ----------------------------------------- #

    def _strict(
        self, parsed: ParsedPhrase, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> ParsedPhrase:
        """Strict mode: a bare command is words, but stopping always works."""
        if not preferences.command_prefix_required or parsed.command is None:
            return parsed
        if parsed.command is Command.STOP or self.spelling:
            return parsed
        return _as_words(parsed, phrase)

    def _command_split(
        self, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> RecognizedPhrase | None:
        """The command in *phrase*, or ``None`` when it is dictation."""
        if self._command_once or self._command_sticky:
            if self._clock() >= self._command_until:
                self._command_lapsed(preferences)  # late: this one is dictation
        rest = split_phrase(phrase, preferences.command_prefix)
        if self._command_sticky:
            self._command_schedule(preferences)  # a command keeps the mode open
            return rest if rest is not None else phrase
        if self._command_once:
            self._command_once = False
            self._command_stop_timer()
            self._command_changed()
            return rest if rest is not None else phrase
        return rest

    def _command_utterance(self, rest: RecognizedPhrase, preferences: DictationPreferences) -> None:
        """Run the command *rest* says, or refuse it. Nothing here is typed."""
        words = wake_words(" ".join(word.lexical for word in rest.words))
        if not words:
            if not self._command_sticky:
                self._command_arm(preferences)  # the command word alone, then a pause
            return
        only = command_only(words)
        if only is Command.TYPE_THAT:
            self._type_refused(preferences)
            return
        if only is Command.COMMAND_MODE:
            self._command_enter(preferences)
            return
        if only is Command.DICTATION_MODE:
            if self._command_sticky:
                self._command_leave(preferences, said=DICTATION_MODE_SAID)
            else:
                self._say(DICTATION_MODE_SAID)
            return
        parsed = parse(rest, vocabulary=preferences.vocabulary)
        if parsed.command is None:
            self._command_refused = rest
            self._fail(not_a_command(preferences.command_prefix), preferences)
            return
        if not self._command_sticky:
            self._command_cue(Moment.COMMAND_ON, preferences)  # the result is what is said
        self._commanding = True
        try:
            self._apply(parsed, preferences)
        finally:
            self._commanding = False

    def _type_refused(self, preferences: DictationPreferences) -> None:
        """ "QUILL type that": the refused words, written once, as words."""
        phrase, self._command_refused = self._command_refused, None
        if phrase is None:
            self._say("Nothing to type. Say it again first.")
            return
        parsed = self._parse(phrase, preferences)
        self._apply(_as_words(parsed, phrase) if parsed.command else parsed, preferences)

    # -- arming, entering, leaving ----------------------------------------------- #

    def _command_arm(self, preferences: DictationPreferences) -> None:
        self._command_once = True
        self._command_schedule(preferences)
        self._command_cue(Moment.COMMAND_ON, preferences, SAY_A_COMMAND)
        self._feedback.show(SAY_A_COMMAND)
        self._command_changed()

    def _command_enter(self, preferences: DictationPreferences) -> None:
        self._command_once = False
        self._command_sticky = True
        self._command_schedule(preferences)
        self._command_cue(Moment.COMMAND_ON, preferences)
        self._say(COMMAND_MODE_SAID)  # once, on entry
        self._command_changed()

    def _command_leave(self, preferences: DictationPreferences, *, said: str = "") -> None:
        self._command_stop_timer()
        self._command_once = False
        self._command_sticky = False
        self._command_cue(Moment.COMMAND_OFF, preferences, "" if said else DICTATION_MODE_SAID)
        if said:
            self._say(said)
        self._command_changed()

    def _command_lapsed(self, preferences: DictationPreferences) -> None:
        """No command in time: a falling tone, no words (unless there is no tone)."""
        self._command_leave(preferences)

    def _command_cue(
        self, moment: Moment, preferences: DictationPreferences, words: str = ""
    ) -> None:
        """The tone; *words* instead when there is none to play and the person
        has not turned both tones and words off."""
        if preferences.cue_sounds and self._feedback.has_cue(moment):
            self._feedback.cue(moment)
        elif words and (preferences.announce or preferences.cue_sounds):
            self._feedback.say(words)

    def _command_changed(self) -> None:
        """The status cell and the tray state line follow command mode."""
        try:
            self._feedback.state_changed(self._state)
        except Exception:  # noqa: BLE001 - a mirror is never worth a session
            pass

    # -- the timeout ------------------------------------------------------------ #

    def _command_schedule(self, preferences: DictationPreferences) -> None:
        self._command_stop_timer()
        seconds = float(preferences.command_timeout)
        self._command_until = self._clock() + seconds
        later = getattr(self._feedback, "call_later", None)
        if not callable(later):
            return  # checked when the next phrase arrives instead
        token = self._command_round
        try:
            self._command_handle = later(seconds, lambda: self._command_timed_out(token))
        except Exception:  # noqa: BLE001 - no event loop: the next phrase checks
            self._command_handle = None

    def _command_stop_timer(self) -> None:
        self._command_round += 1
        handle, self._command_handle = self._command_handle, None
        stop = getattr(handle, "Stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:  # noqa: BLE001 - a timer that already fired is fine
                pass

    def _command_timed_out(self, token: int) -> None:
        if token != self._command_round or not (self._command_once or self._command_sticky):
            return  # a late callback for an arming that is over
        self._command_handle = None
        if not self.active:
            self._command_reset()
            return
        self._command_lapsed(self._preferences())
