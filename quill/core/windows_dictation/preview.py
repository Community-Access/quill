"""The live preview: the words heard so far, shown while you are still speaking.

A streaming engine (Nemotron, and OpenAI's live transcription) knows the words
of a phrase before the phrase is finished. They are **provisional** -- the
engine may still change them -- so they never go into the document or the
undo history. They go to the status bar's Dictation cell and a braille display
as "Hearing: ..." (``preview = "show"``, the default), which is where a
listener can glance at them without anything talking over the person who is
talking. Dictation Settings can also have them spoken (``"speak"``) -- calmly:
only the words that are new, never the same words twice, and no more often
than every :data:`SPEAK_SECONDS` -- or switched off.

When the phrase ends, the final words replace the preview and go through
everything a phrase always goes through (the normaliser and the commands), so
a preview can never run a command.

Learned from VS Code's interim transcript (grey text, replaced by the final
segment); QUILL's own words and code, credited in the design note.

Also here: :func:`close_sentence`, the full stop -- or question mark -- a
phrase gets at a pause when the engine left its end open.

Pure and wx-free.
"""

from __future__ import annotations

__all__ = [
    "PREVIEW_CHOICES",
    "SHOW_SECONDS",
    "SPEAK_SECONDS",
    "PreviewThrottle",
    "close_sentence",
    "coerce_preview",
]

#: (value, label) for Dictation Settings' chooser.
PREVIEW_CHOICES: tuple[tuple[str, str], ...] = (
    ("show", "Show it in the status bar and on a braille display"),
    ("speak", "Show it, and say new words quietly"),
    ("off", "Do not show it"),
)

#: The status bar and braille are updated at most this often.
SHOW_SECONDS = 0.3
#: New words are spoken at most this often in the "speak" choice.
SPEAK_SECONDS = 2.0

#: How an English question opens, for a phrase whose end the engine left open
#: (an engine's own mark always wins). Deliberately narrow, because a wrong
#: question mark is worse than a full stop: an inverted auxiliary ("Is it",
#: "Could you"), or a question word followed by one ("Where did", "What is").
#: Not "do", "have" or "will" on their own -- "Do the dishes" and "Have a good
#: day" are not questions -- and not a bare "when" or "which", which open
#: ordinary clauses ("When I get home").
_INVERTED = frozenset(
    "is are am was were does did can could would should shall isn't aren't wasn't "
    "weren't doesn't didn't can't couldn't won't wouldn't shouldn't".split()
)
_QUESTION_WORDS = frozenset("who what when where why how which whose whom".split())
_AUXILIARIES = _INVERTED | frozenset("do don't have has had will may might must".split())


def coerce_preview(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in {value for value, _label in PREVIEW_CHOICES} else "show"


def close_sentence(text: str, language: str = "en") -> str:
    """*text* closed with a mark when it ends in a word.

    A question mark when an English phrase opens like a question ("Can you",
    "Where did") or a Spanish one opens with the inverted mark; a full stop
    otherwise. An engine that punctuates closes a phrase at a pause, and the
    composer and "scratch that" expect it; a streaming engine that has not yet
    heard what follows leaves the end open, and :mod:`live` corrects the mark
    when the next phrase shows what it should have been.
    """
    text = text.strip()
    if not text or not text[-1].isalnum():
        return text
    if language == "es":
        return f"{text}?" if text.startswith(chr(0xBF)) else f"{text}."
    words = [word.strip(",").lower().replace(chr(0x2019), "'") for word in text.split()[:2]]
    first, second = (words + [""])[:2]
    asks = first in _INVERTED or (first in _QUESTION_WORDS and second in _AUXILIARIES)
    return f"{text}?" if asks else f"{text}."


class PreviewThrottle:
    """Decides what of a stream of provisional words to show and to say."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """A phrase finished or was thrown away: the next preview starts afresh."""
        self._shown = ""
        self._shown_at = -1e9
        self._spoken = ""
        self._spoken_at = -1e9

    def to_show(self, text: str, now: float) -> str | None:
        """*text* when it should replace what the status bar shows, else ``None``."""
        text = " ".join(text.split())
        if not text or text == self._shown or now - self._shown_at < SHOW_SECONDS:
            return None
        self._shown, self._shown_at = text, now
        return text

    def to_speak(self, text: str, now: float) -> str | None:
        """The words not yet spoken, when it is time to say them, else ``None``."""
        words = text.split()
        # Where the engine changed its mind, say again from there; otherwise
        # only what is new since the last time.
        common = 0
        for old, new in zip(self._spoken.split(), words, strict=False):
            if old.lower() != new.lower():
                break
            common += 1
        fresh = words[common:]
        if now - self._spoken_at < SPEAK_SECONDS or not fresh:
            return None
        self._spoken, self._spoken_at = " ".join(words), now
        return " ".join(fresh)
