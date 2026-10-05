"""Live transcripts: an hour of somebody else talking, written into a document.

dict.md 3.7 (gap 2). **Live Transcript** in Tools > Dictation opens a new,
untitled document -- never the one you are editing -- and dictates into it in a
profile made for a lecture or a meeting:

* No commands, except the stop phrase: whatever the speaker says is written,
  even "scratch that". Punctuation the engine adds stays.
* No tone and no read-back for each phrase; nothing is announced while it runs.
  The status bar (and so a braille display) says "Live transcript: 12 minutes,
  1,840 words", and Dictation Status says it on demand.
* A pause of four seconds or more starts a new paragraph, and with **Time stamps
  in live transcripts** on (off by default) each paragraph starts with the time,
  "[10:42]".
* The words always go at the end of the transcript, and into the transcript even
  while you are working in another document -- your own place in the transcript
  is kept if you move around in it.
* Never stops on silence, never listens for the wake phrase, fillers removed.
* Microphone only (dict.md question 7: the computer's own sound is a second
  step, once this one has been used for a while).

The profile itself is ``DictationPreferences.from_settings`` with
``profile="transcript"``; the host marks the transcript's text control
with it, exactly as the AI Conversation window marks its message box.

wx-free; mixed into the controller.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.parser import ParsedPhrase, Piece, RecognizedPhrase, parse
from quill.core.windows_dictation.vocabulary import Command, Glue, Mark

if TYPE_CHECKING:
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["PARAGRAPH_GAP_SECONDS", "TranscriptMixin", "transcript_status"]

#: A pause this long between phrases starts a new paragraph.
PARAGRAPH_GAP_SECONDS = 4.0
_NEW_PARAGRAPH = Mark(("new", "paragraph"), "\n\n", Glue.BREAK, True, "New paragraph")


def transcript_status(seconds: float, words: int) -> str:
    """ "Live transcript: 12 minutes, 1,840 words"."""
    minutes = int(max(0.0, seconds) // 60)
    return (
        f"Live transcript: {minutes} minute{'s' if minutes != 1 else ''}, "
        f"{words:,} word{'s' if words != 1 else ''}"
    )


def _clock_time() -> str:
    return time.strftime("%H:%M")


class TranscriptMixin:
    """The live transcript half of the controller."""

    _document: Any
    _feedback: Any
    history: PhraseHistory
    _preferences: Callable[[], DictationPreferences]
    _clock: Callable[[], float]
    _anchor: Any

    def _init_transcript(self, wall: Callable[[], str] = _clock_time) -> None:
        self._wall = wall
        self._transcript_started: float | None = None
        self._transcript_last: float | None = None
        self.transcript_words = 0

    @property
    def transcribing(self) -> bool:
        """Whether a live transcript is being written."""
        return self._transcript_started is not None

    def begin_transcript(self) -> None:
        """The host pointed dictation at a new transcript document: count from now."""
        self._transcript_started = self._clock()
        self._transcript_last = None
        self.transcript_words = 0

    def transcript_status(self) -> str:
        """What the status bar and Dictation Status say while it runs."""
        if self._transcript_started is None:
            return ""
        return transcript_status(self._clock() - self._transcript_started, self.transcript_words)

    def _transcript_stopping(self, message: str) -> str:
        """The sentence dictation stops with: a transcript says how much it wrote."""
        if self._transcript_started is None:
            return message
        words = self.transcript_words
        self._transcript_started = None
        self._transcript_last = None
        return f"Live transcript stopped, {words:,} word{'s' if words != 1 else ''}."

    def _transcript_parse(
        self, phrase: RecognizedPhrase, preferences: DictationPreferences
    ) -> ParsedPhrase:
        """Everything the speaker says is text; only the stop phrase is obeyed."""
        parsed = parse(phrase, vocabulary=preferences.vocabulary)
        if parsed.command is None or parsed.command is Command.STOP:
            return parsed
        if parsed.pieces:
            return ParsedPhrase(pieces=parsed.pieces)
        return ParsedPhrase(pieces=tuple(Piece(w.display) for w in phrase.words if w.display))

    def _write_transcript(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        """Add *parsed* at the end of the transcript, quietly, keeping your place."""
        from quill.core.windows_dictation.composer import compose

        self._anchor = None  # always the end, wherever the cursor is
        if self._transcript_started is None:
            self.begin_transcript()
        now = self._clock()
        document = self._document
        saved = document.selection()
        end = document.last_position()
        fresh = self._transcript_last is None
        gap = not fresh and now - (self._transcript_last or now) >= PARAGRAPH_GAP_SECONDS
        pieces: list[Piece] = []
        if gap and end > 0:
            pieces.append(Piece(_NEW_PARAGRAPH.text, _NEW_PARAGRAPH))
        if (gap or fresh) and preferences.transcript_timestamps:
            pieces.append(Piece(f"[{self._wall()}]", verbatim=True))
        pieces.extend(parsed.pieces)
        document.select(end, end)
        before, _after = document.context()
        text = compose(pieces, before=before, dash=preferences.dash, close_paragraphs=True)
        if not text:
            return
        start, stop = document.insert(text)
        self.history.push(DictatedPhrase(text, start, stop))
        counted = [word for word in text.split() if not word.startswith("[")]
        self.transcript_words += sum(1 for word in counted if any(c.isalnum() for c in word))
        self._transcript_last = now
        if saved != (end, end):
            document.select(*saved)  # your place in the transcript stays where it was
        self._feedback.show(self.transcript_status())
