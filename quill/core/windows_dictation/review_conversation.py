"""What each review command says and does: the review window's half of D-2.

:class:`ReviewConversation` runs one review: the words, the AI requests, and
every sentence the person hears. It is wx-free; the window
(``quill/ui/dictation_review_frame.py``) is a view over it, and the host --
an editor or QUILL Transcribe -- supplies a :class:`ReviewPort` (where the
text is shown, how a sentence is said, how the words are finally put in) and a
:class:`ReviewAi` (the AI route), so a unit test drives all of it with fakes.

**Spoken outcomes, and only those (GATE-13).** A revision is announced as the
diff summary -- two sentences at most -- never the whole text: the text is in a
real text control the screen reader reads by line, word and character, and a
braille display shows it. "Read it" speaks the whole text through the screen
reader on request. While a summary or the text is being read the microphone is
muted (``mute``) so the reader is not heard as the next instruction.

**One request per instruction.** "Working." once, and the status line says
so; no repeated speech. Escape while waiting cancels it. A failure is said with
"Nothing was changed."

**Privacy.** Before the first request on a route the person is asked, once,
with No as the default (:func:`~quill.core.windows_dictation.review_session.consent_question`).
Declining sends nothing. AI off -- the area switched off, no direct route, Safe
Mode -- means no request at all; the window still lets the words be edited and
inserted.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from quill.core.windows_dictation.review_session import (
    POLISH_INSTRUCTION,
    POLISH_LABEL,
    POLISH_OFF,
    ReviewSession,
    clear_rescue,
    consent_question,
    review_request,
    save_rescue,
)

__all__ = ["ReviewAi", "ReviewConversation", "ReviewPort"]


class ReviewAi(Protocol):
    """The AI route for reviews. Answers on the UI thread."""

    def reason(self) -> str:
        """Why no request can be made now (AI off), or ``""``."""
        ...

    def provider(self) -> str:
        """Who receives the words, as said: "OpenAI, on your ChatGPT subscription"."""
        ...

    def consented(self) -> bool: ...

    def agree(self) -> None: ...

    def ask(
        self, prompt: str, on_done: Callable[[str], None], on_error: Callable[[str], None]
    ) -> Any: ...

    def cancel(self, request: Any) -> None: ...


class ReviewPort(Protocol):
    """What the window and the host do for a review."""

    def say(self, text: str) -> None: ...

    def status(self, text: str) -> None: ...

    def show_text(self, text: str) -> None: ...

    def show_changes(self, text: str) -> None: ...

    def mute(self, text: str) -> None:
        """The microphone ignores what it hears while *text* is read aloud."""
        ...

    def ask_yes_no(self, question: str, title: str) -> bool: ...

    def insert(self, text: str, original: str) -> None:
        """Put *text* where the words were going, and close the review."""
        ...

    def close(self) -> None: ...


class ReviewConversation:
    """One review: the session, the requests, and what is said."""

    def __init__(
        self,
        session: ReviewSession,
        port: ReviewPort,
        *,
        ai: ReviewAi | None,
        rescue: Path | None = None,
        my_instructions: Callable[[], str] = lambda: "",
        context: Callable[[], str] = lambda: "",
        polish_on: Callable[[], bool] = lambda: False,
    ) -> None:
        self.session = session
        self._polish_on = polish_on
        self._port = port
        self._ai = ai
        self._rescue = rescue
        self._my_instructions = my_instructions
        self._context = context
        self._request: Any = None
        self._finished = False
        self._keep()

    # -- what the window asks ------------------------------------------------ #

    @property
    def working(self) -> bool:
        """A request is on its way."""
        return self._request is not None

    @property
    def finished(self) -> bool:
        """Inserted or discarded: nothing to keep."""
        return self._finished

    def ai_reason(self) -> str:
        """Why the AI cannot be asked here (``""`` when it can)."""
        if self._ai is None:
            return "AI is off, so this window cannot change your words. Edit them, then insert."
        return str(self._ai.reason())

    def opening_status(self) -> str:
        """The status line when the window opens: the cost, or why there is none."""
        reason = self.ai_reason()
        if reason:
            return reason
        assert self._ai is not None
        return f"Each change you ask for is one request to {self._ai.provider()}."

    def edited(self, text: str) -> None:
        """The person typed or dictated into the text."""
        self.session.edited(text)
        self._keep()

    # -- the commands -------------------------------------------------------- #

    def polish(self) -> None:
        """ "Polish my dictation" (P3): one fixed request, only when allowed.

        Opt-in (``windows_dictation_polish``, off by default) and never
        automatic; the consent question is the review's own, asked before the
        first request, so nothing is sent without a yes.
        """
        try:
            allowed = bool(self._polish_on())
        except Exception:  # noqa: BLE001 - unknown is off
            allowed = False
        if not allowed:
            self._port.say(POLISH_OFF)
            return
        self.instruct(POLISH_INSTRUCTION, label=POLISH_LABEL)

    def instruct(self, instruction: str, *, label: str = "") -> None:
        """Ask the AI to change the words: "make it shorter".

        *label* is what the status line and the revision call the request when
        the instruction itself is long (Polish's fixed wording)."""
        instruction = " ".join(instruction.split())
        if not instruction:
            self._port.say("Say or type what to change first, like make it shorter.")
            return
        if self.working:
            self._port.say("Still working on the last change. Press Escape to stop it.")
            return
        reason = self.ai_reason()
        if reason:
            self._port.say(reason)
            return
        text = self.session.current
        if not text.strip():
            self._port.say("There are no words to change yet.")
            return
        ai = self._ai
        assert ai is not None
        if not ai.consented():
            if not self._port.ask_yes_no(consent_question(ai.provider()), "Review with AI"):
                self._port.say("Nothing was sent.")
                return
            ai.agree()
        try:
            context = str(self._context() or "")
        except Exception:  # noqa: BLE001 - no context is the default anyway
            context = ""
        try:
            mine = str(self._my_instructions() or "")
        except Exception:  # noqa: BLE001 - instructions are a preference
            mine = ""
        prompt = review_request(text, instruction, my_instructions=mine, context=context)
        named = label or instruction
        self._port.status(f"Working: {named}. Escape stops it.")
        self._port.say("Polishing." if label == POLISH_LABEL else "Working.")
        self._request = ai.ask(
            prompt,
            lambda reply: self._replied(named, text, reply),
            self._failed,
        )

    def cancel(self) -> bool:
        """Escape while waiting: the request is dropped. ``False`` when none was."""
        request, self._request = self._request, None
        if request is None:
            return False
        if self._ai is not None:
            self._ai.cancel(request)
        self._port.status("Stopped. Nothing was changed.")
        self._port.say("Stopped. Nothing was changed.")
        return True

    def what_changed(self) -> None:
        self._say_and_mute(self.session.what_changed())

    def read_it(self) -> None:
        text = self.session.current.strip()
        self._say_and_mute(text or "There are no words yet.")

    def undo_change(self) -> None:
        summary = self.session.undo_revision()
        if not summary:
            self._port.say("There is no change to undo.")
            return
        self._port.show_text(self.session.current)
        self._port.show_changes(summary)
        self._keep()
        self._port.say(
            "Change undone."
        )  # what it undid is in What Changed, and "what changed" says it

    def restore(self) -> None:
        if not self.session.restore_original():
            self._port.say("These are already the words you said.")
            return
        self._port.show_text(self.session.current)
        self._port.show_changes(self.session.last_summary)
        self._keep()
        self._port.say("Back to what you said.")

    def insert(self) -> None:
        """Write the words where they were going. The only way anything is written."""
        if self.working:
            self.cancel()
        text = self.session.current
        if not text.strip():
            self._port.say("There are no words to insert. Discard closes the window.")
            return
        self._finished = True
        self._forget()
        self._port.insert(text, self.session.original)

    def discard(self, *, ask: bool = True) -> None:
        """Throw the words away. Asks first when the AI has changed them."""
        if (
            ask
            and self.session.changed
            and not self._port.ask_yes_no(
                "Discard these words and every change to them? Nothing is written.",
                "Discard These Words",
            )
        ):
            return
        if self.working:
            self.cancel()
        self._finished = True
        self._forget()
        self._port.close()
        self._port.say("Discarded. Nothing was written.")

    def closing(self) -> str:
        """The window is closing without Insert or Discard: the words are kept
        for next time. Returns what to say, or ``""``."""
        if self.working:
            request, self._request = self._request, None
            if self._ai is not None:
                self._ai.cancel(request)
        if self._finished or not self.session.current.strip():
            self._forget()
            return ""
        self._keep()
        return "Your words are kept. Review Dictation brings them back."

    # -- the reply ------------------------------------------------------------ #

    def _replied(self, instruction: str, sent: str, reply: str) -> None:
        if self._request is None or self._finished:
            return  # cancelled, or the window has gone
        self._request = None
        reply = reply.strip()
        if not reply:
            self._failed("The AI sent back nothing.")
            return
        if self.session.current != sent:
            said = (
                "Your words changed while the AI was working, so its reply was not used. Ask again."
            )
            self._port.status(said)
            self._port.say(said)
            return
        summary = self.session.revise(instruction, reply)
        self._port.show_text(self.session.current)
        self._port.show_changes(summary)
        self._port.status(f"Changed: {instruction}.")
        self._keep()
        self._say_and_mute(summary)

    def apply(self, label: str, text: str) -> str:
        """Replace the words with *text* as one change Undo Change takes back.

        For a change the person already reviewed elsewhere (an agent task's
        preview), so nothing is said here; returns the change in words.
        """
        if self._finished:
            return ""
        summary = self.session.revise(label, text)
        self._port.show_text(self.session.current)
        self._port.show_changes(summary)
        self._port.status(f"Changed: {label}.")
        self._keep()
        return summary

    def _failed(self, message: str) -> None:
        if self._request is None:
            return  # cancelled, or the window has gone
        self._request = None
        sentence = f"{message.rstrip('.')}. Nothing was changed."
        self._port.status(sentence)
        self._port.say(sentence)

    # -- plumbing --------------------------------------------------------------- #

    def _say_and_mute(self, text: str) -> None:
        self._port.mute(text)
        self._port.say(text)

    def _keep(self) -> None:
        if self._rescue is not None and not self._finished:
            if self.session.current.strip() or self.session.original.strip():
                save_rescue(self._rescue, self.session)

    def _forget(self) -> None:
        if self._rescue is not None:
            clear_rescue(self._rescue)
