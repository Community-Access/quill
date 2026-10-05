"""The dictation state machine, and every sound and sentence it makes.

::

    OFF --start--> STARTING --> LISTENING <-> RECOGNIZING -> PROCESSING -> LISTENING
     ^                             |  ^
     |                        stop |  | wake phrase heard
     +-------- STOPPING <----------+  |
                   |                  |
                   +--> STANDBY ------+   (only while a wake phrase is set)

Any failure lands in OFF. The recogniser is stopped on every path out of a
session, because the one thing that must never happen is a microphone left open
while QUILL believes dictation is off. STANDBY is the one state where the
microphone is open and nothing is written: it is only reached when the user has
switched the wake phrase on, the menu says so, and every phrase heard there is
checked for the wake phrase and then dropped.

wx-free. The three things it drives are ports the editor supplies -- the
recogniser, the document and the feedback channels -- so the whole machine runs
in a unit test against fakes, and the two editors cannot disagree about what
happens when because neither of them decides it.

**What is said, and when.** Three separate choices, because they are three
separate moments and people want different things from each:

* **On and off** -- a rising and a falling pair of tones (``cue_sounds``) and
  the words "Dictation on" / "Dictation off" (``announce``). Either can go;
  the menu's check mark still says which it is.
* **Each phrase** -- ``phrase_feedback``, the shared
  :class:`~quill.core.action_feedback.ActionFeedback` choice: a short tone, the
  inserted text **read back**, both, or neither. The read-back is the point of
  the option: a tone says *something* went in, and only the words say whether
  it was what you said.
* **Failure and commands** -- always spoken, whatever the settings say, with the
  error tone when tones are on. "It did not work" is not a cue, and a command
  answers a question.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from quill.core.action_feedback import resolve
from quill.core.error_codes import CodedError
from quill.core.windows_dictation.composer import compose, spoken_form
from quill.core.windows_dictation.editing import EditingMixin
from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.live import LiveMixin
from quill.core.windows_dictation.options import clean_phrase, flow_on
from quill.core.windows_dictation.parser import (
    ParsedPhrase,
    Piece,
    RecognizedPhrase,
    parse,
    words_from_text,
)
from quill.core.windows_dictation.ports import (
    DictationState,
    DocumentPort,
    FeedbackPort,
    Moment,
    RecognizerPort,
)
from quill.core.windows_dictation.preferences import (
    DEFAULT_PHRASE_FEEDBACK,
    DictationPreferences,
)
from quill.core.windows_dictation.readback import spoken_marks
from quill.core.windows_dictation.resilience import ResilienceMixin, engine_failure_message
from quill.core.windows_dictation.transcript import TranscriptMixin
from quill.core.windows_dictation.vocabulary import Command
from quill.core.windows_dictation.voice_commands import VoiceCommandsMixin
from quill.core.windows_dictation.wake import is_stop_phrase, match_wake, wake_words

__all__ = [
    "DEFAULT_PHRASE_FEEDBACK",
    "DictationController",
    "DictationPreferences",
    "DictationStartError",
    "DictationState",
    "DocumentPort",
    "FeedbackPort",
    "Moment",
    "RecognizerPort",
]


class DictationStartError(CodedError):
    """The recogniser could not start: no microphone, no recogniser, no access."""

    code = "QUILL-DICTATION-WINDOWS-START"
    user_hint = (
        "Check that a microphone is connected, that Windows Settings, Privacy "
        "and security, Microphone lets desktop apps use it, and choose the "
        "microphone in Dictation Settings."
    )


#: The states in which dictation writes what it hears.
_LIVE = frozenset({
    DictationState.LISTENING,
    DictationState.RECOGNIZING,
    DictationState.PROCESSING,
})


class DictationController(
    ResilienceMixin, EditingMixin, LiveMixin, VoiceCommandsMixin, TranscriptMixin
):
    """One app's dictation session: one microphone, one document at a time."""

    def __init__(
        self,
        *,
        recognizer: Callable[[DictationController, DictationPreferences], RecognizerPort],
        document: DocumentPort,
        feedback: FeedbackPort,
        preferences: Callable[[], DictationPreferences],
    ) -> None:
        self._make_recognizer = recognizer
        self._document = document
        self._feedback = feedback
        self._preferences = preferences
        self._recognizer: RecognizerPort | None = None
        self._state = DictationState.OFF
        self.spelling = False
        self.history = PhraseHistory()
        #: What was dictated this app session, newest first, for Recent Phrases.
        self.recent: deque[str] = deque(maxlen=20)
        self._ignore_until_speech = False  # Escape threw the phrase being heard away
        self._restarted = False  # the one silent engine restart, spent
        self._last_spoken = ""
        self._init_live()  # live.py: preview, anchor, finishing, muting
        self._init_voice_commands()  # voice_commands.py: modes, targets, the library
        self._init_transcript()  # transcript.py: live transcripts
        #: Called when the wake phrase is heard, before dictation starts: the
        #: host points the controller at whichever document is in front now.
        self.on_wake: Callable[[], None] | None = None

    # -- state ------------------------------------------------------------ #

    @property
    def state(self) -> DictationState:
        return self._state

    @property
    def active(self) -> bool:
        """Whether dictation is writing -- the Dictation On check mark."""
        on_hold = (DictationState.STARTING, DictationState.PAUSED)
        return self._state in _LIVE or self._state in on_hold

    @property
    def standing_by(self) -> bool:
        """Whether the microphone is open for the wake phrase only."""
        return self._state is DictationState.STANDBY

    @property
    def microphone_open(self) -> bool:
        return self._recognizer is not None

    @property
    def preferences(self) -> DictationPreferences:
        """The settings as they are now, read afresh."""
        return self._preferences()

    def _set_state(self, state: DictationState) -> None:
        if state is self._state:
            return
        self._state = state
        try:
            self._feedback.state_changed(state)
        except Exception:  # noqa: BLE001 - a menu refresh is never worth a session
            pass

    def retarget(self, document: DocumentPort, feedback: FeedbackPort) -> None:
        """Write into a different document from now on -- the one in front when
        the wake phrase was heard, which need not be the one that armed it."""
        if document is not self._document:
            self.history.clear()
        self._document = document
        self._feedback = feedback

    # -- commands --------------------------------------------------------- #

    def toggle(self) -> None:
        if self.active:
            self.finish()  # keeps the phrase being spoken (live.py)
        else:
            self.start()

    def start(self, message: str = "Dictation on.") -> None:
        """Start dictating now -- from off, or from waiting for the wake phrase."""
        if self.active:
            return
        preferences = self._preferences()
        reason = self._document.unavailable_reason(writing=False)
        if reason:
            self._fail(reason, preferences)
            return
        if self._recognizer is None and not self._open(preferences):
            return
        self.history.clear()
        self.spelling = False
        self._restarted = False
        self._set_state(DictationState.LISTENING)
        self._announce_edge(Moment.ON, message, preferences)

    def arm(self) -> None:
        """Wait for the wake phrase: microphone open, nothing written."""
        preferences = self._preferences()
        if self.active or self.standing_by or not preferences.wake_enabled:
            return
        if self._recognizer is None and not self._open(preferences, quiet=True):
            return
        self._set_state(DictationState.STANDBY)

    def disarm(self) -> None:
        """Stop waiting for the wake phrase and close the microphone."""
        if self.standing_by:
            self._close_recognizer()
            self._set_state(DictationState.OFF)

    def stop(self, message: str = "Dictation off.") -> None:
        """Stop writing. With the wake phrase on, go back to waiting for it."""
        if not self.active:
            return
        message = self._transcript_stopping(message)  # transcript.py: how much it wrote
        preferences = self._preferences()
        self._set_state(DictationState.STOPPING)
        self.history.clear()
        self.spelling = False
        self._end_live()
        self._end_voice_modes()
        if preferences.wake_enabled and self._recognizer is not None:
            self._set_state(DictationState.STANDBY)
            self._announce_edge(
                Moment.OFF,
                f"{message[:-1]}. Say {preferences.wake_phrase} to start again.",
                preferences,
            )
            return
        self._close_recognizer()
        self._set_state(DictationState.OFF)
        self._announce_edge(Moment.OFF, message, preferences)

    def shut_down(self) -> None:
        """Close everything, silently: the window or the app is going away."""
        self._close_recognizer()
        self.history.clear()
        self._set_state(DictationState.OFF)

    def _open(
        self, preferences: DictationPreferences, *, quiet: bool = False, report: bool = True
    ) -> bool:
        self._set_state(DictationState.STARTING)
        try:
            recognizer = self._make_recognizer(self, preferences)
            recognizer.start(preferences.microphone)
        except DictationStartError as error:
            self._set_state(DictationState.OFF)
            if not report:
                return False
            if not quiet:
                self._fail(str(error.args[0]) if error.args else str(error), preferences)
            else:
                self._fail(
                    f"The wake phrase is not being listened for. {error.args[0]}", preferences
                )
            return False
        except Exception as error:  # noqa: BLE001 - never crash the editor
            self._set_state(DictationState.OFF)
            self._fail(f"Dictation could not start: {error}", preferences)
            return False
        self._recognizer = recognizer
        # A downloaded model that gave way to the built-in engine: never silently.
        notice = str(getattr(recognizer, "fallback_notice", "") or "")
        if notice:
            self._say(notice)
        return True

    # -- recogniser events ------------------------------------------------ #

    def on_speech_started(self) -> None:
        self._ignore_until_speech = False
        if self._state is DictationState.LISTENING:
            self._set_state(DictationState.RECOGNIZING)
            self._capture_anchor()

    def on_phrase(self, phrase: RecognizedPhrase) -> None:
        """A finalised phrase. Applied, then straight back to listening."""
        if not self._receive(phrase):
            return  # the microphone is muted while the AI's reply is read
        preferences = self._preferences()
        phrase = clean_phrase(
            phrase,
            remove_fillers=preferences.remove_fillers,
            strip_punctuation=preferences.strips_punctuation,
            language=preferences.filler_language,
        )
        phrase = self._rewrite(phrase, preferences)
        if self._ignore_until_speech:
            return  # the phrase Escape threw away, arriving late
        if self._state is DictationState.STANDBY:
            self._on_standby_phrase(phrase, preferences)
            return
        if self._state not in _LIVE:
            return
        heard = wake_words(" ".join(word.display for word in phrase.words))
        if is_stop_phrase(heard, preferences.stop_phrase):
            self.stop()
            return
        self._revise_mark()
        self._set_state(DictationState.PROCESSING)
        try:
            self._apply(self._parse(phrase, preferences), preferences)
        except Exception:  # noqa: BLE001 - a failed edit ends the session, never the app
            self._abandon("Dictation stopped: the phrase could not be written into the document.")
            return
        if self._state is DictationState.PROCESSING:
            self._set_state(DictationState.LISTENING)

    def _parse(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> ParsedPhrase:
        """What *phrase* means -- which, when writing straight through, is only words."""
        if preferences.profile == "transcript":
            return self._transcript_parse(phrase, preferences)
        if not preferences.continuous:
            return parse(phrase, spelling=self.spelling, vocabulary=preferences.vocabulary)
        phrase = flow_on(phrase, strip_period=preferences.engine_punctuates)
        parsed = parse(phrase, spelling=self.spelling, vocabulary=preferences.vocabulary)
        if parsed.command is None or parsed.command is Command.STOP:
            return parsed
        return ParsedPhrase(pieces=tuple(Piece(w.display) for w in phrase.words if w.display))

    def on_failure(self, message: str) -> None:
        """The recogniser stopped on its own. Once, the engine is restarted silently
        (resilience.restart_once); the second time it is reported by name."""
        if not (self.active or self.standing_by):
            return
        if self.restart_once():
            return
        if "microphone" not in message.lower():
            message = engine_failure_message(self._preferences().engine)
        self._abandon(message)

    def _rewrite(
        self, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> RecognizedPhrase:
        """The user's replacements and vocabulary, applied to what was heard."""
        if preferences.rewrite is None:
            return phrase
        text = phrase.text or " ".join(word.display for word in phrase.words)
        try:
            changed = preferences.rewrite(text)
        except Exception:  # noqa: BLE001 - a broken profile must never stop dictation
            return phrase
        if changed == text:
            return phrase
        # A replacement may write line breaks and tabs (a signature on two
        # lines). Splitting into words would lose them, so they become the
        # spoken marks that write them, and go through the same spacing rules
        # as everything else.
        spoken = (
            changed
            .replace("\r", "")
            .replace("\n\n", " new paragraph ")
            .replace("\n", " new line ")
            .replace("\t", " tab key ")
        )
        return RecognizedPhrase(words_from_text(spoken), text=changed, confidence=phrase.confidence)

    def _on_standby_phrase(
        self, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> None:
        heard_words = [word.display for word in phrase.words]
        heard = wake_words(" ".join(heard_words))
        used = match_wake(heard, preferences.wake_phrase)
        if used is None:
            return  # not for us: dropped, never written, never kept
        if self.on_wake is not None:
            self.on_wake()
        self.start()
        if not self.active:
            return
        # The rest of the phrase is dictation: skip the words the wake phrase used.
        remainder: list[str] = []
        counted = 0
        for word in heard_words:
            if counted < used and wake_words(word):
                counted += 1
                continue
            remainder.append(word)
        if remainder:
            text = " ".join(remainder)
            self.on_phrase(RecognizedPhrase(words_from_text(text), text=text))

    # -- applying a phrase ------------------------------------------------ #

    def _apply(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        command = parsed.command
        if command is Command.STOP:
            self.stop()
            return
        if command is Command.HELP:
            self._feedback.show_commands()
            return
        if command is Command.READ_BACK:
            self._say(self._last_spoken or "Nothing has been dictated yet.")
            return
        if command is Command.SPELL_ON:
            self.spelling = True
            self._say("Spelling. Say letters, or stop spelling.")
            return
        if command is Command.SPELL_OFF:
            self.spelling = False
            self._say("Spelling off.")
            return
        if self._mode_command(parsed, preferences):
            return  # caps, no space, the language: nothing written (voice_commands.py)
        reason = self._writing_reason()
        if reason:
            self._abandon(reason)
            return
        if self._live_command(command) or self._voice_command(parsed, preferences):
            return
        if command is not None:
            self._edit(command)
            return
        if not parsed.pieces:
            return
        if preferences.profile == "transcript":
            self._write_transcript(parsed, preferences)
            return
        self._go_to_anchor()
        pieces = self._in_mode(parsed.pieces)
        continued = self._continue_sentence(pieces)
        if continued is not None:
            pieces = continued
        before, after = self._document.context()
        text = compose(
            pieces,
            before=before,
            after=after,
            dash=preferences.dash,
            close_paragraphs=preferences.engine_punctuates and not self._one_line(),
            join_words=self.no_space,
        )
        if not text:
            return
        start, end = self._document.insert(text)
        self.history.push(DictatedPhrase(text, start, end, auto_period=parsed.auto_period))
        self._after_insert(text)
        self.recent.appendleft(" ".join(text.split()))
        spoken = spoken_form(pieces, text)
        heard = spoken_marks(text, preferences.speech_language)
        if not preferences.readback_marks or not any(c.isalnum() for c in text):
            heard = spoken  # a line break alone already says its name
        self._last_spoken = heard
        self._after_phrase()  # "spell that" lasts one phrase (voice_commands.py)
        play, speak = resolve(
            preferences.phrase_feedback,
            has_sound=self._feedback.has_cue(Moment.PHRASE),
        )
        if preferences.continuous:  # a pause does nothing, not even a tone
            play = speak = False
        # The tone first, and only now: it means "this went into the
        # document", so it cannot be played before the insert has happened.
        if play:
            self._feedback.cue(Moment.PHRASE)
        if speak and heard:
            self._feedback.read_back(heard)
        self._feedback.show(f"Dictated: {spoken}" if spoken else "Dictated.")

    def _one_line(self) -> bool:
        """A one-line box (Find, a question): no paragraph to close with a full stop."""
        single = getattr(self._document, "single_line", None)
        return bool(single()) if callable(single) else False

    # -- endings and feedback --------------------------------------------- #

    def _close_recognizer(self) -> None:
        recognizer, self._recognizer = self._recognizer, None
        if recognizer is None:
            return
        try:
            recognizer.stop()
        except Exception:  # noqa: BLE001 - it is being thrown away either way
            pass

    def _abandon(self, message: str) -> None:
        """End the session because something went wrong, and say what."""
        self._close_recognizer()
        self.history.clear()
        self.spelling = False
        self._set_state(DictationState.OFF)
        self._fail(message, self._preferences())

    def _fail(self, message: str, preferences: DictationPreferences) -> None:
        if preferences.cue_sounds and self._feedback.has_cue(Moment.ERROR):
            self._feedback.cue(Moment.ERROR)
        self._feedback.say(message)
        self._feedback.show(message)

    def _announce_edge(
        self, moment: Moment, message: str, preferences: DictationPreferences
    ) -> None:
        played = False
        if preferences.cue_sounds and self._feedback.has_cue(moment):
            self._feedback.cue(moment)
            played = True
        # With the tones off and the words off, the menu mark is the record.
        # With the tones on but none in the pack, the words step in: a setting
        # chooses between kinds of feedback, never down to none by accident.
        if preferences.announce or (preferences.cue_sounds and not played):
            self._feedback.say(message)
        self._feedback.show(message)

    def _say(self, message: str) -> None:
        """A spoken command's outcome. Always words: it answers a question."""
        self._feedback.say(message)
        self._feedback.show(message)
