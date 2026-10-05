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

What a phrase is matched against is a
:class:`~quill.core.windows_dictation.vocabulary.Vocabulary` -- English unless
the caller passes another (Spanish, from
:func:`~quill.core.windows_dictation.vocabulary.vocabulary_for`), which may also
ask for words to be compared without their accents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.windows_dictation.speech_language import fold
from quill.core.windows_dictation.vocabulary import (
    DASH_PLACEHOLDER,
    ENGLISH,
    LITERAL,
    SPELLING_ALPHABET,
    SPELLING_MARKS,
    Command,
    Glue,
    Mark,
    Vocabulary,
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
# Letters in any language survive: "linea" with its accent and "n" with its
# tilde must reach the command table intact.
_WORD_CHARS = re.compile(r"[^\w']+")


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
    #: The mark a streaming engine put at the end of the *previous* phrase once
    #: it heard this one ("?" after "Can you send it"): live.py revises it.
    previous_mark: str = ""
    #: Other things the engine thought was said, best first, for "correct that".
    alternatives: tuple[str, ...] = ()


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
    #: The words after a command that takes some ("select *the cat*"), as said.
    #: With such a command, ``pieces`` is the whole phrase as ordinary text --
    #: what is written when the command finds nothing to act on (dict.md
    #: question 3: nothing you said is lost).
    argument: tuple[str, ...] = ()


#: Whole-phrase commands that are also ordinary sentences ("Next one."): when
#: there is nothing for them to act on, the phrase is written instead.
_WRITTEN_WHEN_IDLE = frozenset({Command.SELECT_NEXT, Command.SELECT_PREVIOUS})


@dataclass(frozen=True, slots=True)
class _Token:
    lexical: str
    display: str
    #: Which recognised word this token came from. A joined word becomes
    #: several tokens, and its display text must be written once, not once
    #: per token.
    source: int
    #: The word as said, accents and all, when *lexical* had them folded away.
    said: str = ""


def words_from_text(text: str) -> tuple[RecognizedWord, ...]:
    """Words for an engine, or a test, that reports only a flat string."""
    return tuple(RecognizedWord(word.lower(), word) for word in text.split())


def _normalise(lexical: str) -> list[str]:
    parts = [_WORD_CHARS.sub("", part.lower()) for part in _SPLIT.split(lexical)]
    return [part for part in parts if part]


def _tokens(words: tuple[RecognizedWord, ...], folds: bool = False) -> list[_Token]:
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
            display = word.display if position == 0 else ""
            tokens.append(_Token(fold(part) if folds else part, display, index, part))
    return tokens


def parse(
    phrase: RecognizedPhrase, *, spelling: bool = False, vocabulary: Vocabulary | None = None
) -> ParsedPhrase:
    """Turn one recognised phrase into a command or the pieces it inserts.

    With *spelling*, words are letters (see :func:`_spell`) -- but a whole-phrase
    command still works, which is how "stop spelling" gets out. *vocabulary* is
    the language's table; English when not given.
    """
    table = vocabulary or ENGLISH
    tokens = _tokens(phrase.words, table.folds)
    lexical = [token.lexical for token in tokens]
    spoken = tuple(word for word in lexical if word)
    if spoken in table.commands:
        command = table.commands[spoken]
        if command in _WRITTEN_WHEN_IDLE:
            return ParsedPhrase(_pieces(tokens, lexical, table)[0], command=command)
        return ParsedPhrase(command=command)
    if spelling:
        letters = _spell(spoken, table)
        return ParsedPhrase(pieces=(Piece(letters, verbatim=True),) if letters else ())
    opened = table.prefix(spoken)
    if opened is not None:
        command, argument = opened
        if command is Command.SPELL_WORDS:
            # "spell bravo alpha delta": one word spelled, no mode to leave. A
            # sentence that only starts with "spell" is not letters, and is text.
            letters = _spell(argument, table, strict=True)
            if letters:
                return ParsedPhrase(pieces=(Piece(letters, verbatim=True),))
        else:
            pieces, _auto = _pieces(tokens, lexical, table)
            return ParsedPhrase(pieces, command=command, argument=argument)
    pieces, auto_period = _pieces(tokens, lexical, table)
    return ParsedPhrase(pieces=pieces, auto_period=auto_period)


def _pieces(
    tokens: list[_Token], lexical: list[str], table: Vocabulary
) -> tuple[tuple[Piece, ...], bool]:
    """The words and marks a phrase writes, and whether it ends on an engine's
    full stop."""
    pieces: list[Piece] = []
    written: set[int] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.lexical == LITERAL:
            escaped = table.longest(lexical, index + 1)
            if escaped is not None:
                # The words themselves, as said. The display form would be the
                # very punctuation the user asked not to have.
                said = tokens[index + 1 : index + 1 + len(escaped)]
                pieces.extend(Piece(token.said or token.lexical) for token in said)
                for consumed in tokens[index : index + 1 + len(escaped)]:
                    written.add(consumed.source)
                index += 1 + len(escaped)
                continue
        found = table.longest(lexical, index)
        if found is not None:
            marks = table.marks.get(found, ())
            if marks and marks[0].glue is Glue.LINE_START and index != 0:
                # "bullet" and "heading two" start a line only when they start
                # the phrase; anywhere else they are words (dict.md question 4).
                marks = ()
            if marks:
                pieces.extend(Piece(mark.text, mark) for mark in marks)
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
    return tuple(pieces), auto_period


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


def _spell(
    words: tuple[str, ...], vocabulary: Vocabulary = ENGLISH, *, strict: bool = False
) -> str:
    """Spelling mode: letter names, the phonetic alphabet and digits, as letters.

    "capital" (or "cap") before a letter makes it a capital, and "all caps"
    makes every letter one until "no caps"; "space" is a space; "double you" is
    w. Punctuation works too, with no spaces round it: "bravo dot com",
    "jay underscore smith", "at sign" (dict.md 3.3). Anything else is not a
    letter and is left out rather than guessed at -- the read-back says what was
    written, so a gap is heard at once. *strict* gives ``""`` instead when any
    word is not a letter: "spell" opening an ordinary sentence is text.
    """
    out: list[str] = []
    capital = False
    all_caps = False
    index = 0
    while index < len(words):
        word = words[index]
        index += 1
        following = words[index] if index < len(words) else ""
        if word in ("all", "no") and following == "caps":
            index += 1
            all_caps = word == "all"
            continue
        if word in _CAPITAL or word in vocabulary.capital_words:
            capital = True
            continue
        found = vocabulary.longest(list(words), index - 1)
        marks = vocabulary.marks.get(found, ()) if found is not None else ()
        if marks:
            index += len(found or ()) - 1
            for mark in marks:
                out.append("-" if mark.text == DASH_PLACEHOLDER else mark.text.strip(" ") or " ")
            capital = False
            continue
        if word == "double" and following == "you":
            index += 1
            letter = "w"
        elif word == "x" and following == "ray":
            index += 1  # "x-ray" arrives as two words once its hyphen is split
            letter = "x"
        elif word == "space" or word in vocabulary.space_words:
            out.append(" ")
            capital = False
            continue
        elif word in SPELLING_MARKS:
            out.append(SPELLING_MARKS[word])
            capital = False
            continue
        elif word in SPELLING_ALPHABET:
            letter = SPELLING_ALPHABET[word]
        elif word in _LETTER_SOUNDS:
            letter = _LETTER_SOUNDS[word]
        elif word.isdigit() or (word.isalpha() and len(word) == 1):
            letter = word
        else:
            if strict:
                return ""
            capital = False
            continue
        out.append(letter.upper() if capital or all_caps else letter)
        capital = False
    return "".join(out)
