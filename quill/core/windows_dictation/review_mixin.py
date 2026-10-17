"""Review before inserting, in the controller: the voice half of D-2.

The review itself -- the words, the AI, what is said -- is the host's review
desk (``quill/ui/dictation_review_frame.py``), reached through the feedback
port's optional ``review()``, as the library is through ``library()``. A host
without one (Quill Inkwell) answers "Review is not available here."

What the controller decides, before anything is composed
(:mod:`~quill.core.windows_dictation.command_mode_mixin` asks):

* **"QUILL review that"** takes the words held while paused for the field, or
  else the last phrase -- taken back out of the document, the way "scratch
  that" does, so in another program it is backspaced away -- and opens them in
  the review. With AI off it says
  :data:`~quill.core.windows_dictation.review_session.AI_OFF` and leaves the
  phrase where it was written.
* **While reviewing**, what follows the command word is a review command
  ("insert it", "what changed") or, when it is not a dictation command at all,
  an instruction for the AI ("make it shorter"). With **Talk About It** on,
  every utterance is one of those, with or without the word.
* **"QUILL polish that"** (P3, "Polish my dictation"): with the opt-in
  setting on, the last phrase is opened in the review the same way and one
  fixed request -- punctuation, capitals and small slips, the words kept -- is
  made there, after the review's consent. Never automatic, never inserted
  until Insert, and Undo Change takes it back.
* **Send dictation to review first** (``windows_dictation_review_first``):
  the first phrase of dictation opens an empty review, and that phrase and the
  rest are written into it. The host points the controller at the review's text
  while it is open (``retarget``), so dictation there goes through a document
  port, never through keystrokes, and nothing reaches the target before Insert.

wx-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.parser import RecognizedPhrase
from quill.core.windows_dictation.review_session import (
    AI_OFF,
    NOTHING_TO_REVIEW,
    REVIEW_COMMANDS,
    not_reviewing,
)
from quill.core.windows_dictation.snippet_fill import SnippetFillMixin
from quill.core.windows_dictation.vocabulary import Command
from quill.core.windows_dictation.wake import wake_words

if TYPE_CHECKING:
    from quill.core.windows_dictation.parser import ParsedPhrase
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["NOT_HERE", "ReviewMixin"]

#: A host with no review window (Quill Inkwell).
NOT_HERE = "Review is not available here."


def _said(phrase: RecognizedPhrase) -> str:
    return phrase.text or " ".join(word.display for word in phrase.words)


class ReviewMixin(SnippetFillMixin):  # and VoiceCommandsMixin under that
    """ "review that", the review commands, Talk About It and review first."""

    _held: list[ParsedPhrase]

    @property
    def active(self) -> bool:  # provided by the controller
        raise NotImplementedError

    def _parse(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> ParsedPhrase:
        raise NotImplementedError  # provided by the controller

    if TYPE_CHECKING:  # target_hold.py, later in the controller's bases than this

        def _drop_held(self) -> None: ...

        def _rescue_held_done(self) -> None: ...

    # -- the host's review desk ------------------------------------------------- #

    def _review_desk(self) -> Any:
        provider = getattr(self._feedback, "review", None)
        try:
            return provider() if callable(provider) else None
        except Exception:  # noqa: BLE001 - no review is an answer
            return None

    @property
    def reviewing(self) -> bool:
        """Whether a review is open for this session's host."""
        desk = self._review_desk()
        return bool(desk is not None and desk.is_open())

    # -- the hooks command_mode_mixin.py calls --------------------------------- #

    def _review_command(self, words: tuple[str, ...] | list[str], preferences: Any) -> bool:
        """A review command after the command word: handled here, ``True``."""
        command = REVIEW_COMMANDS.get(tuple(words))
        if command is None:
            return False
        desk = self._review_desk()
        if command is Command.REVIEW_THAT:
            self.review_last(voice=True)
            return True
        if command is Command.REVIEW_POLISH and desk is not None and not desk.is_open():
            self._polish_last(preferences)
            return True
        if desk is None:
            self._say(NOT_HERE)
        elif not desk.is_open():
            self._say(not_reviewing(preferences.command_prefix))
        else:
            desk.command(command)
        return True

    def _review_instruction(self, rest: RecognizedPhrase) -> bool:
        """Not a dictation command, while reviewing: an instruction for the AI."""
        desk = self._review_desk()
        if desk is None or not desk.is_open():
            return False
        desk.instruct(_said(rest))
        return True

    def _review_dictation(
        self, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> bool:
        """A phrase with no command word. ``True`` when the review took it:
        Talk About It is on. Sending to review first opens the review here and
        returns ``False``, so the phrase is written into it."""
        desk = self._review_desk()
        if desk is None:
            return False
        if desk.is_open():
            if not desk.talking():
                return False
            command = REVIEW_COMMANDS.get(tuple(wake_words(_said(phrase))))
            if command is Command.REVIEW_THAT:
                self._say("Already reviewing.")
            elif command is not None:
                desk.command(command)
            else:
                desk.instruct(_said(phrase))
            return True
        if preferences.review_first and preferences.profile != "transcript":
            parsed = self._parse(phrase, preferences)
            if parsed.command is None and parsed.pieces:
                desk.open("")  # the host points this controller at the review's text
        return False

    # -- what a host does while a review is open --------------------------------- #

    @property
    def document(self) -> Any:
        """The document this session writes into now."""
        return self._document

    def retarget(self, document: Any, feedback: Any) -> None:  # provided by the controller
        raise NotImplementedError

    def review_retarget(self, document: Any) -> Any:
        """Write into *document* (the review's text) from now on, with the same
        feedback; returns the document written into until now."""
        previous = self._document
        self.retarget(document, self._feedback)
        return previous

    def insert_reviewed(self, text: str) -> str:
        """Write reviewed words into this session's document as one phrase --
        in another program, typed with the same checks as a dictated phrase,
        and "scratch that" takes it back. ``""``, or why it was not written."""
        reason = str(self._document.unavailable_reason(writing=True))
        if reason:
            return reason
        try:
            self._insert_text(text, 0, " ".join(text.split()), self._preferences())
        except Exception as error:  # noqa: BLE001 - said, never raised
            return str(error) or "The words could not be written."
        return ""

    # -- "polish that" (P3) ---------------------------------------------------------- #

    def _polish_last(self, preferences: Any) -> None:
        """ "QUILL polish that" with no review open: the last phrase goes into
        the review, then the one polish request is made there -- after the
        review's own consent question. Off unless the person allowed it."""
        from quill.core.windows_dictation.review_session import POLISH_OFF

        if not getattr(preferences, "polish", False):
            self._say(POLISH_OFF)
            return
        self.review_last(voice=True)
        desk = self._review_desk()
        if desk is not None and desk.is_open():
            desk.command(Command.REVIEW_POLISH)

    # -- "review that" ------------------------------------------------------------ #

    def review_last(self, *, voice: bool = False) -> None:
        """Open the held words, or the last phrase, in the review.

        *voice* is "QUILL review that": with AI off the phrase stays written.
        The Review Dictation key opens the review either way, empty when there
        is nothing to take, because editing before inserting needs no AI.
        """
        desk = self._review_desk()
        if desk is None:
            self._say(NOT_HERE)
            return
        if desk.is_open():
            desk.focus()
            if voice:
                self._say("Already reviewing.")
            return
        if voice and desk.ai_reason():
            self._say(AI_OFF)
            return
        text = self._take_for_review()
        if text is None and voice:
            self._say(NOTHING_TO_REVIEW)
            return
        desk.open(text or "")

    def _take_for_review(self) -> str | None:
        """The held words, or the last phrase taken back out; ``None`` if neither."""
        held = list(getattr(self, "_held", []) or [])
        if held:
            from quill.core.windows_dictation.ports import DictationState
            from quill.core.windows_dictation.rescue_mixin import held_text

            text = held_text(held)  # one after another, as they would have been written
            self._rescue_held_done()  # the review keeps them now (its own rescue file)
            self._drop_held()
            if self.active:
                self._set_state(DictationState.LISTENING)
            return text
        phrase = self.history.peek()
        if phrase is None:
            return None
        if self._document.text_between(phrase.start, phrase.end) != phrase.inserted:
            self.history.clear()
            return None
        self.history.pop()
        try:
            self._document.remove(phrase.start, phrase.end)
        except Exception:  # noqa: BLE001 - it stays written; the review still gets a copy
            self._say("The phrase could not be taken back out, so it is still written.")
        return " ".join(phrase.inserted.split())
