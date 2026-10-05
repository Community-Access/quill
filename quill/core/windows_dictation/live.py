"""What dictation does *while* you speak, and the moments around a phrase.

The 2026-10-05 pass (VS Code's dictation studied, dict.md 2.4, 3.2, 4.4 and 6),
kept out of :mod:`~quill.core.windows_dictation.controller` because that module
is at its size ceiling, and because each of these is about the edges of a
phrase rather than the phrase pipeline itself:

* **The live preview** (:meth:`LiveMixin.on_partial`): a streaming engine's
  provisional words go to the status bar and braille as "Hearing: ...", never
  into the document or the undo history; the final words replace them.
  :mod:`~quill.core.windows_dictation.preview` decides how often.
* **Words go where you started speaking** (dict.md 2.4): the caret is
  remembered when a phrase starts. If it moves, or the focus goes to another
  window, before the phrase is written, the words still go where you were
  speaking, the caret is put back where you moved it, and you hear "Written
  where you started, in ...". If that spot no longer exists, the words go at
  the caret and you are told.
* **A streaming engine's late punctuation** (``previous_mark``): Nemotron
  writes the mark that ends a sentence when it hears the next one, so the last
  phrase's full stop becomes the question mark it should have been.
* **Finishing, not cutting off** (:meth:`LiveMixin.finish`): stopping while a
  phrase is being heard -- letting go of the dictation key, or pressing it --
  waits for that phrase and writes it, as VS Code's stop does.
* **Muting the microphone** (:meth:`LiveMixin.mute_for`) while the AI's reply
  is read aloud (Talk to the AI, dict.md 3.2), so the reply is not heard back
  as the next message.
* **"Correct that"** (dict.md 6): the other things the engine thought you said,
  where it offers them (Windows speech recognition does; the others answer one
  guess), and "choose 2" to swap.
* The keep-up watchdog's and OpenAI's notices.

wx-free; mixed into the controller, which supplies ``_state``, ``_document``,
``_feedback``, ``_recognizer``, ``history``, ``_preferences``, ``_say``,
``stop`` and ``_abandon``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.preview import PreviewThrottle
from quill.core.windows_dictation.vocabulary import Command

if TYPE_CHECKING:
    from quill.core.windows_dictation.controller import DictationState
    from quill.core.windows_dictation.parser import RecognizedPhrase
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["LiveMixin"]

_CLOSING = ".?!"
_CHOICES = {Command.CHOOSE_1: 0, Command.CHOOSE_2: 1, Command.CHOOSE_3: 2}
#: How long finishing the last phrase may take before dictation stops anyway.
FINISH_SECONDS = 4.0


class LiveMixin:
    """The live preview, the anchor, finishing, muting and "correct that"."""

    _state: DictationState
    _document: Any
    _feedback: Any
    _recognizer: Any
    _ignore_until_speech: bool
    history: PhraseHistory
    _preferences: Callable[[], DictationPreferences]

    def _say(self, message: str) -> None:  # provided by the controller
        raise NotImplementedError

    def stop(self, message: str = "Dictation off.") -> None:  # provided by the controller
        raise NotImplementedError

    def _abandon(self, message: str) -> None:  # provided by the controller
        raise NotImplementedError

    def _init_live(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._throttle = PreviewThrottle()
        self._anchor: Any = None
        self._anchor_note = ""
        self._incoming_mark = ""
        self._incoming_alternatives: tuple[str, ...] = ()
        self._alternatives: tuple[str, ...] = ()
        self._finishing: str | None = None
        self._finish_started = 0.0
        self._muted_until = 0.0

    # -- the preview -------------------------------------------------------- #

    def on_partial(self, text: str) -> None:
        """A streaming engine's provisional words for the phrase being heard."""
        from quill.core.windows_dictation.controller import _LIVE

        if self._state not in _LIVE or self._ignore_until_speech or self._muted():
            return
        preference = self._preferences().preview
        if preference == "off":
            return
        now = self._clock()
        shown = self._throttle.to_show(text, now)
        preview = getattr(self._feedback, "preview", None)
        if shown and callable(preview):
            preview(shown)
        if preference == "speak":
            fresh = self._throttle.to_speak(text, now)
            quietly = getattr(self._feedback, "say_quietly", None)
            if fresh and callable(quietly):
                quietly(fresh)

    def _clear_preview(self) -> None:
        self._throttle.reset()
        preview = getattr(self._feedback, "preview", None)
        if callable(preview):
            preview("")

    # -- receiving a phrase ------------------------------------------------- #

    def _receive(self, phrase: RecognizedPhrase) -> bool:
        """``False`` when the phrase is to be dropped (the microphone is muted)."""
        self._clear_preview()
        if self._muted():
            return False
        self._incoming_mark = phrase.previous_mark
        self._incoming_alternatives = tuple(phrase.alternatives)
        return True

    def _revise_mark(self) -> None:
        """Correct the last phrase's ending to the mark the engine has now heard."""
        mark, self._incoming_mark = self._incoming_mark, ""
        last = self.history.peek()
        if not mark or last is None or self._preferences().strips_punctuation:
            return
        body = last.inserted.rstrip()
        if not body or body[-1] not in _CLOSING:
            return
        if body[-1] == mark:
            # The engine itself confirms the full stop: not a pause's guess, so
            # a next phrase opening with "where" or "and" does not undo it.
            self.history.replace_last(
                DictatedPhrase(last.inserted, last.start, last.end, auto_period=False)
            )
            return
        position = last.start + len(body) - 1
        if self._document.text_between(position, position + 1) != body[-1]:
            return  # typed over since: leave it alone
        selection = self._document.selection()
        self._document.replace(position, position + 1, mark)
        self._document.select(*selection)
        inserted = body[:-1] + mark + last.inserted[len(body) :]
        self.history.replace_last(DictatedPhrase(inserted, last.start, last.end))

    # -- where the words go -------------------------------------------------- #

    def _capture_anchor(self) -> None:
        """Speech started: remember where it should be written."""
        anchor = getattr(self._document, "anchor", None)
        self._anchor = None
        if callable(anchor):
            try:
                self._anchor = anchor()
            except Exception:  # noqa: BLE001 - without an anchor, the caret is used
                self._anchor = None

    def _writing_reason(self) -> str:
        """Why a phrase cannot be written now, allowing for where it started."""
        reason = str(self._document.unavailable_reason(writing=True))
        relaxed = getattr(self._document, "anchored_reason", None)
        if reason and self._anchor is not None and callable(relaxed):
            return str(relaxed(self._anchor))
        return reason

    def _go_to_anchor(self) -> None:
        anchor, self._anchor = self._anchor, None
        place = getattr(self._document, "place_at_anchor", None)
        self._anchor_note = str(place(anchor)) if anchor is not None and callable(place) else ""
        self._placed = anchor if self._anchor_note else None

    def _after_insert(self, text: str) -> None:
        """The phrase is in: put the caret back, say where it went, tell the host."""
        self._alternatives = self._incoming_alternatives
        note, self._anchor_note = self._anchor_note, ""
        placed, self._placed = getattr(self, "_placed", None), None
        release = getattr(self._document, "release_anchor", None)
        if placed is not None and callable(release):
            release(placed)
        if note:
            self._say(note)
        written = getattr(self._feedback, "phrase_written", None)
        if callable(written):
            written(text)

    # -- finishing ------------------------------------------------------------ #

    def finish(self, message: str = "Dictation off.") -> None:
        """Stop, but write the phrase being spoken first (VS Code's stop)."""
        from quill.core.windows_dictation.controller import DictationState

        finish = getattr(self._recognizer, "finish", None)
        if self._state is not DictationState.RECOGNIZING or not callable(finish):
            self.stop(message)
            return
        if self._finishing is not None:
            return
        self._finishing = message
        self._finish_started = self._clock()
        try:
            finish()
        except Exception:  # noqa: BLE001 - nothing to finish: stop now
            self._finishing = None
            self.stop(message)
            return
        self._feedback.show("Dictation: writing the last phrase")

    @property
    def finishing(self) -> bool:
        return self._finishing is not None

    def on_finished(self) -> None:
        """The recogniser wrote what was left: now stop."""
        message, self._finishing = self._finishing, None
        if message is not None:
            self.stop(message)

    def finish_overdue(self) -> None:
        """The host's timer: the last phrase is taking too long; stop anyway."""
        if self._finishing is not None and self._clock() - self._finish_started >= FINISH_SECONDS:
            self.on_finished()

    def _end_live(self) -> None:
        """Dictation stopped: nothing provisional, nothing remembered."""
        self._clear_preview()
        self._anchor = None
        self._alternatives = ()
        self._finishing = None
        self._muted_until = 0.0

    # -- muting ----------------------------------------------------------------- #

    def mute_for(self, seconds: float) -> None:
        """Drop what the microphone hears for *seconds* (the AI's reply is being read)."""
        self._muted_until = self._clock() + max(0.0, seconds)
        discard = getattr(self._recognizer, "discard", None)
        if callable(discard):
            try:
                discard()
            except Exception:  # noqa: BLE001 - the guard in _receive still drops it
                pass

    def unmute(self) -> None:
        self._muted_until = 0.0

    @property
    def muted(self) -> bool:
        """Whether the microphone is being ignored while a reply is read."""
        return self._muted()

    def _muted(self) -> bool:
        return self._clock() < self._muted_until

    # -- notices from the recogniser ------------------------------------------- #

    def on_engine_notice(self, message: str) -> None:
        """Something the person should know, that did not stop dictation."""
        self._say(message)

    def on_engine_problem(self, message: str, fatal: bool = False) -> None:
        """OpenAI said no. Fatal problems stop dictation; never a silent switch."""
        if fatal:
            self._abandon(message)
        else:
            self._say(message)

    # -- "correct that" ---------------------------------------------------------- #

    def _live_command(self, command: Command | None) -> bool:
        """``True`` when *command* was "correct that" or "choose N", now handled."""
        if command is Command.CORRECT:
            self._offer_alternatives()
            return True
        if command in _CHOICES:
            self._choose(_CHOICES[command])
            return True
        return False

    def _offer_alternatives(self) -> None:
        options = self._alternatives[:3]
        if not options:
            if self._preferences().engine == "windows":
                said = "Windows speech recognition offered no other guesses for that phrase."
            else:
                said = (
                    "This speech engine gives one answer, not a list of guesses; only "
                    "Windows speech recognition offers other guesses."
                )
            self._say(
                f"{said} Say scratch that and say it again, or add a correction in My "
                "Words and Phrases."
            )
            return
        listed = " ".join(f"{number}: {text}." for number, text in enumerate(options, 1))
        self._say(f"{listed} Say choose and the number.")

    def _choose(self, index: int) -> None:
        options = self._alternatives
        last = self.history.peek()
        if index >= len(options) or last is None:
            self._say("There is no such choice. Say correct that to hear them again.")
            return
        from quill.core.windows_dictation.editing import same_text

        if not same_text(self._document.text_between(last.start, last.end), last.inserted):
            self._say("That phrase has changed since it was dictated, so it was left alone.")
            return
        lead = last.inserted[: len(last.inserted) - len(last.inserted.lstrip())]
        chosen = lead + options[index].strip()
        start, end = self._document.replace(last.start, last.end, chosen)
        self.history.replace_last(DictatedPhrase(chosen, start, end))
        self._alternatives = ()
        self._say(f"Changed to: {options[index].strip()}")
