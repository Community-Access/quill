"""QUILL Transcribe's Practice window and recognition test: the words (D-25).

The window (:mod:`quill.apps.transcribe_practice`) has a field of its own that
dictation types into directly, so a first dictation never goes into a real
program. Its recognition test, **Read This Sentence**, shows one of
:data:`SENTENCES`, the person reads it aloud, and :func:`score` compares what
was written with what was shown, word for word, with the benchmark's own
scorer (:func:`quill.core.windows_dictation.word_errors.word_errors`).

The sentences are ordinary English a first-time user can read without
stumbling, with a name, a number and a question among them, because those are
what a speech model gets wrong first. Punctuation and capitals do not count:
the test is about the words.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.windows_dictation.word_errors import score_words, word_errors

__all__ = ["SENTENCES", "Score", "next_sentence", "score"]

SENTENCES: tuple[str, ...] = (
    "The quick brown fox jumps over the lazy dog.",
    "Please send the report to Maria before Friday afternoon.",
    "I would like two tickets for the concert on Saturday night.",
    "Can you call me back when you have a moment?",
    "The library opens at nine and closes at six.",
    "My favourite season is autumn, when the leaves change colour.",
    "Thank you for your help with the move last weekend.",
    "We need milk, bread, eggs and a bag of apples.",
)


@dataclass(frozen=True, slots=True)
class Score:
    """How what was written compares with the sentence."""

    words: int
    errors: int
    #: The sentence's words that were not written as said, in order.
    missed: tuple[str, ...] = ()

    @property
    def percent(self) -> int:
        """Words right, as a whole percentage; never below zero."""
        if not self.words:
            return 0
        return max(0, round(100 * (self.words - self.errors) / self.words))

    def sentence(self) -> str:
        """The outcome, said once and shown in the result field."""
        if not self.words:
            return "There was no sentence to compare with."
        if self.errors == 0:
            return f"All {self.words} words right. Recognition is working well."
        word = "difference" if self.errors == 1 else "differences"
        said = f"{self.percent} percent right: {self.errors} {word} in {self.words} words."
        if self.missed:
            said += " Not heard as said: " + ", ".join(self.missed) + "."
        if self.percent < 80:
            said += (
                " Try speaking a little slower, moving closer to the microphone, or "
                "a larger model in Choose Model."
            )
        return said


def score(reference: str, heard: str) -> Score:
    """Compare what was written (*heard*) with the sentence (*reference*)."""
    said = score_words(reference)
    got = score_words(heard)
    remaining = list(got)
    missed: list[str] = []
    for word in said:
        if word in remaining:
            remaining.remove(word)
        else:
            missed.append(word)
    return Score(len(said), word_errors(said, got), tuple(missed))


def next_sentence(current: str) -> str:
    """The sentence after *current*, round to the first again."""
    try:
        index = SENTENCES.index(current)
    except ValueError:
        return SENTENCES[0]
    return SENTENCES[(index + 1) % len(SENTENCES)]
