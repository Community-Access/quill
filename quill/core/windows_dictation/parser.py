"""Recognised words into the pieces a phrase inserts.

The recogniser hands over each word twice: its **lexical** form, which is what
was said ("period", "new-paragraph"), and its **display** form, which is what a
formatter would print (".", "Microsoft"). The parser matches commands on the
lexical form and takes ordinary words from the display form, so a proper noun
keeps the capital the recogniser gave it and a command is recognised whatever
the recogniser chose to print for it.

Nothing here edits anything. The output is a :class:`ParsedPhrase`: either one
whole-phrase :class:`~quill.core.windows_dictation.vocabulary.Command`, or a
sequence of words and marks for :func:`~quill.core.windows_dictation.composer.compose`
to turn into text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.windows_dictation.vocabulary import (
    COMMANDS,
    LITERAL,
    SPELLING_ALPHABET,
    Command,
    Mark,
    longest_phrase,
    mark_for,
)

__all__ = [
    "ParsedPhrase",
    "Piece",
    "RecognizedPhrase",
    "RecognizedWord",
    "parse",
    "words_from_text",
]

_SPLIT = re.compile(r"[\s\-]+")
_WORD_CHARS = re.compile(r"[^a-z0-9']+")


@dataclass(frozen=True, slots=True)
class RecognizedWord:
    """One word as the recogniser reported it."""

    lexical: str
    display: str


@dataclass(frozen=True, slots=True)
class RecognizedPhrase:
    """One finalised result: the words, and the recogniser's own rendering.

    ``text`` is kept for diagnostics and for engines that report nothing finer;
    it is never logged, because it is what the user said.
    """

    words: tuple[RecognizedWord, ...]
    text: str = ""
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class Piece:
    """A word (``mark is None``) or a mark, in the order they were spoken."""

    text: str
    mark: Mark | None = None
    #: Written exactly as it is: no capital added at a sentence start. Spelled
    #: letters, where "iPhone" must stay "iPhone".
    verbatim: bool = False


@dataclass(frozen=True, slots=True)
class ParsedPhrase:
    """What one phrase means: a command, or pieces to insert (maybe none)."""

    pieces: tuple[Piece, ...] = field(default_factory=tuple)
    command: Command | None = None
    #: The recogniser ended the phrase with a full stop nobody said. Engines
    #: that punctuate end every phrase as a sentence, including one that was
    #: only a pause in the middle of one; the controller takes this full stop
    #: back when the next phrase plainly continues the sentence.
    auto_period: bool = False


@dataclass(frozen=True, slots=True)
class _Token:
    lexical: str
    display: str
    #: Which recognised word this token came from. A joined word becomes
    #: several tokens, and its display text must be written once, not once
    #: per token.
    source: int


def words_from_text(text: str) -> tuple[RecognizedWord, ...]:
    """Words for an engine, or a test, that reports only a flat string."""
    return tuple(RecognizedWord(word.lower(), word) for word in text.split())


def _normalise(lexical: str) -> list[str]:
    parts = [_WORD_CHARS.sub("", part.lower()) for part in _SPLIT.split(lexical)]
    return [part for part in parts if part]


def _tokens(words: tuple[RecognizedWord, ...]) -> list[_Token]:
    tokens: list[_Token] = []
    for index, word in enumerate(words):
        parts = _normalise(word.lexical)
        if not parts:
            # Punctuation the recogniser reported with no lexical form of its
            # own: keep it as display text so nothing said is lost.
            if word.display.strip():
                tokens.append(_Token("", word.display, index))
            continue
        # A word the recogniser joined or rendered ("new-paragraph", "period"
        # -> ".") is several tokens for matching, and one piece of text if no
        # phrase claims it: "well-known" stays hyphenated.
        for position, part in enumerate(parts):
            tokens.append(_Token(part, word.display if position == 0 else "", index))
    return tokens


def parse(phrase: RecognizedPhrase, *, spelling: bool = False) -> ParsedPhrase:
    """Turn one recognised phrase into a command or the pieces it inserts.

    With *spelling*, words are letters (see :func:`_spell`) -- but a whole-phrase
    command still works, which is how "stop spelling" gets out.
    """
    tokens = _tokens(phrase.words)
    lexical = [token.lexical for token in tokens]
    spoken = tuple(word for word in lexical if word)
    if spoken in COMMANDS:
        return ParsedPhrase(command=COMMANDS[spoken])
    if spelling:
        letters = _spell(spoken)
        return ParsedPhrase(pieces=(Piece(letters, verbatim=True),) if letters else ())

    pieces: list[Piece] = []
    written: set[int] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.lexical == LITERAL:
            escaped = longest_phrase(lexical, index + 1)
            if escaped is not None:
                # The words themselves, as said. The display form would be the
                # very punctuation the user asked not to have.
                pieces.extend(Piece(word) for word in escaped)
                for consumed in tokens[index : index + 1 + len(escaped)]:
                    written.add(consumed.source)
                index += 1 + len(escaped)
                continue
        found = longest_phrase(lexical, index)
        if found is not None:
            mark = mark_for(found)
            if mark is not None:
                pieces.append(Piece(mark.text, mark))
                for consumed in tokens[index : index + len(found)]:
                    written.add(consumed.source)
                index += len(found)
                continue
            # A command phrase inside a longer phrase is text, not a command.
        if token.source not in written and token.display:
            pieces.append(Piece(token.display))
        written.add(token.source)
        index += 1
    last = pieces[-1] if pieces else None
    auto_period = (
        last is not None
        and last.mark is None
        and last.text.endswith(".")
        and not last.text.endswith("..")
    )
    return ParsedPhrase(pieces=tuple(pieces), auto_period=auto_period)


#: What a recogniser writes when somebody says a letter's name.
_LETTER_SOUNDS: dict[str, str] = {
    "ay": "a",
    "bee": "b",
    "be": "b",
    "see": "c",
    "sea": "c",
    "dee": "d",
    "ee": "e",
    "ef": "f",
    "eff": "f",
    "gee": "g",
    "aitch": "h",
    "eye": "i",
    "jay": "j",
    "kay": "k",
    "el": "l",
    "em": "m",
    "en": "n",
    "oh": "o",
    "pee": "p",
    "pea": "p",
    "queue": "q",
    "cue": "q",
    "are": "r",
    "ess": "s",
    "tee": "t",
    "tea": "t",
    "you": "u",
    "vee": "v",
    "ex": "x",
    "why": "y",
    "zed": "z",
    "zee": "z",
}
_CAPITAL = {"capital", "cap", "uppercase", "upper"}


def _spell(words: tuple[str, ...]) -> str:
    """Spelling mode: letter names, the phonetic alphabet and digits, as letters.

    "capital" (or "cap") before a letter makes it a capital; "space" is a
    space; "double you" is w. Anything else is not a letter and is
    left out rather than guessed at -- the read-back says what was written, so
    a gap is heard at once.
    """
    out: list[str] = []
    capital = False
    index = 0
    while index < len(words):
        word = words[index]
        index += 1
        if word in _CAPITAL:
            capital = True
            continue
        if word == "double" and index < len(words) and words[index] == "you":
            index += 1
            letter = "w"
        elif word == "x" and index < len(words) and words[index] == "ray":
            index += 1  # "x-ray" arrives as two words once its hyphen is split
            letter = "x"
        elif word == "space":
            out.append(" ")
            capital = False
            continue
        elif word in SPELLING_ALPHABET:
            letter = SPELLING_ALPHABET[word]
        elif word in _LETTER_SOUNDS:
            letter = _LETTER_SOUNDS[word]
        elif word.isdigit() or (word.isalpha() and len(word) == 1):
            letter = word
        else:
            capital = False
            continue
        out.append(letter.upper() if capital else letter)
        capital = False
    return "".join(out)
