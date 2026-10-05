"""Everything dictation understands, in one table.

Three kinds, because they behave differently:

**Marks** go *into* the text -- punctuation, a line break, a tab, a symbol. They
can appear anywhere in a phrase ("hello comma world period") and each has a
:class:`Glue` that says how it sits against its neighbours, which is the whole
of the spacing rule: a comma hugs the word before it, an opening bracket hugs
the word after it, a new line hugs neither.

**Commands** act on the *document* or on dictation itself -- scratch that,
select that, go to end of line, stop dictation. They count only when they are
the **whole** phrase. "Delete that line of text" is somebody dictating a
sentence, and a recogniser that heard it correctly must not be punished by
having the last phrase deleted. Saying the command on its own, after a pause, is
the unambiguous version, and it is how every dictation product teaches these.

**Spelling mode** turns letters into letters: "start spelling", then "capital
bravo alpha delta" writes *Bad*. See :data:`SPELLING_ALPHABET`.

The table is the only place a phrase is spelled, and it carries a description
of each entry: the in-app "What can I say?" list and the published command
reference (``scripts/build_dictation_commands.py``) are both generated from it,
so the list somebody reads is the list that works. The parser matches the
longest phrase first ("exclamation point" before "exclamation"), and
``literal`` before any phrase makes it words instead: "literal new line" types
*new line*.

**One table per language.** The tables above are English. :func:`vocabulary_for`
puts together what a phrase is matched against for the dictation language: the
English table as it is, or -- for Spanish -- the English commands and marks
plus the Spanish punctuation words of
:mod:`~quill.core.windows_dictation.vocabulary_es` when the engine is not
punctuating, matched without accents (dict.md 9.4).
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from quill.core.windows_dictation.vocabulary_commands import COMMAND_HELP, PREFIX_HELP
from quill.core.windows_dictation.vocabulary_types import (
    Command,
    CommandHelp,
    Glue,
    Mark,
    PrefixHelp,
    make_mark,
)

__all__ = [
    "COMMANDS",
    "COMMAND_HELP",
    "DASH_STYLES",
    "LITERAL",
    "MARKS",
    "PREFIXES",
    "PREFIX_HELP",
    "SPELLING_ALPHABET",
    "SPELLING_MARKS",
    "Command",
    "CommandHelp",
    "Glue",
    "Mark",
    "PrefixHelp",
    "Vocabulary",
    "dash_text",
    "longest_phrase",
    "mark_for",
    "vocabulary_for",
]


#: The dash is a mark whose text is a preference: ``{dash}`` is replaced by
#: :func:`dash_text` when the phrase is written.
DASH_PLACEHOLDER = "{dash}"

#: ``style -> (label, text)``. An em dash hugging both words is how most style
#: guides set it and what Word's AutoFormat makes of two hyphens; a spaced en
#: dash is the British habit; two hyphens are what plain text files have always
#: used and what every screen reader reads the same way.
DASH_STYLES: dict[str, tuple[str, str]] = {
    "em": ("Em dash, no spaces (word" + chr(0x2014) + "word)", chr(0x2014)),
    "en": ("En dash with spaces (word " + chr(0x2013) + " word)", " " + chr(0x2013) + " "),
    "hyphens": ("Two hyphens with spaces (word -- word)", " -- "),
}


def dash_text(style: str) -> str:
    return DASH_STYLES.get(style, DASH_STYLES["em"])[1]


_CODE = "Markdown and code"
_LINES = "Starting a line (say these first)"

#: Every mark, in the order the command reference lists them.
MARKS: tuple[Mark, ...] = (
    make_mark("period", ".", Glue.LEFT, ends=True),
    make_mark("full stop", ".", Glue.LEFT, ends=True),
    make_mark("comma", ",", Glue.LEFT),
    make_mark("question mark", "?", Glue.LEFT, ends=True),
    make_mark("exclamation point", "!", Glue.LEFT, ends=True),
    make_mark("exclamation mark", "!", Glue.LEFT, ends=True),
    make_mark("colon", ":", Glue.LEFT),
    make_mark("semicolon", ";", Glue.LEFT),
    make_mark("ellipsis", "...", Glue.LEFT),
    make_mark("open quote", '"', Glue.OPEN),
    make_mark("begin quote", '"', Glue.OPEN),
    make_mark("close quote", '"', Glue.LEFT),
    make_mark("end quote", '"', Glue.LEFT),
    make_mark("open single quote", "'", Glue.OPEN),
    make_mark("close single quote", "'", Glue.LEFT),
    make_mark("apostrophe", "'", Glue.JOIN),
    make_mark("open parenthesis", "(", Glue.OPEN, group="Brackets"),
    make_mark("open paren", "(", Glue.OPEN, group="Brackets"),
    make_mark("left parenthesis", "(", Glue.OPEN, group="Brackets"),
    make_mark("close parenthesis", ")", Glue.LEFT, group="Brackets"),
    make_mark("close paren", ")", Glue.LEFT, group="Brackets"),
    make_mark("right parenthesis", ")", Glue.LEFT, group="Brackets"),
    make_mark("open bracket", "[", Glue.OPEN, group="Brackets"),
    make_mark("left bracket", "[", Glue.OPEN, group="Brackets"),
    make_mark("close bracket", "]", Glue.LEFT, group="Brackets"),
    make_mark("right bracket", "]", Glue.LEFT, group="Brackets"),
    make_mark("open brace", "{", Glue.OPEN, group="Brackets"),
    make_mark("close brace", "}", Glue.LEFT, group="Brackets"),
    make_mark("open angle bracket", "<", Glue.OPEN, group="Brackets"),
    make_mark("close angle bracket", ">", Glue.LEFT, group="Brackets"),
    make_mark("hyphen", "-", Glue.JOIN, group="Dashes and joining"),
    make_mark("dash", DASH_PLACEHOLDER, Glue.JOIN, group="Dashes and joining"),
    make_mark("slash", "/", Glue.JOIN, group="Dashes and joining"),
    make_mark("forward slash", "/", Glue.JOIN, group="Dashes and joining"),
    make_mark("backslash", "\\", Glue.JOIN, group="Dashes and joining"),
    make_mark("underscore", "_", Glue.JOIN, group="Dashes and joining"),
    make_mark("at sign", "@", Glue.JOIN, group="Symbols"),
    make_mark("hash sign", "#", Glue.OPEN, group="Symbols"),
    make_mark("number sign", "#", Glue.OPEN, group="Symbols"),
    make_mark("dollar sign", "$", Glue.OPEN, group="Symbols"),
    make_mark("percent sign", "%", Glue.LEFT, group="Symbols"),
    make_mark("ampersand", "&", Glue.WORD, group="Symbols"),
    make_mark("asterisk", "*", Glue.JOIN, group="Symbols"),
    make_mark("plus sign", "+", Glue.WORD, group="Symbols"),
    make_mark("minus sign", "-", Glue.WORD, group="Symbols"),
    make_mark("equals sign", "=", Glue.WORD, group="Symbols"),
    make_mark("new line", "\n", Glue.BREAK, ends=True, spoken="New line", group="Lines and layout"),
    make_mark("newline", "\n", Glue.BREAK, ends=True, spoken="New line", group="Lines and layout"),
    make_mark(
        "new paragraph",
        "\n\n",
        Glue.BREAK,
        ends=True,
        spoken="New paragraph",
        group="Lines and layout",
    ),
    make_mark("tab key", "\t", Glue.BREAK, spoken="Tab", group="Lines and layout"),
    make_mark("press tab", "\t", Glue.BREAK, spoken="Tab", group="Lines and layout"),
    make_mark("tab", "\t", Glue.BREAK, spoken="Tab", group="Lines and layout"),
    # 2026-10-05 (dict.md 3.3): Markdown and code. A backtick opens or closes by
    # how many came before it on the line; the fence takes a line of its own.
    make_mark("backtick", "`", Glue.TOGGLE, group=_CODE),
    make_mark("back quote", "`", Glue.TOGGLE, group=_CODE),
    make_mark("triple backtick", "```\n", Glue.LINE_START, spoken="Code fence", group=_CODE),
    make_mark("code fence", "```\n", Glue.LINE_START, spoken="Code fence", group=_CODE),
    make_mark("tilde", "~", Glue.JOIN, group=_CODE),
    make_mark("vertical bar", "|", Glue.WORD, group=_CODE),
    make_mark("pipe symbol", "|", Glue.WORD, group=_CODE),
    make_mark("caret", "^", Glue.JOIN, group=_CODE),
    make_mark("greater than sign", ">", Glue.WORD, group=_CODE),
    make_mark("less than sign", "<", Glue.WORD, group=_CODE),
    # Only at the start of a phrase: "the heading two lines down" is English.
    make_mark("bullet", "- ", Glue.LINE_START, spoken="Bullet", group=_LINES),
    make_mark("list item", "- ", Glue.LINE_START, spoken="Bullet", group=_LINES),
    make_mark("numbered item", "1. ", Glue.LINE_START, spoken="Numbered item", group=_LINES),
    make_mark("block quote", "> ", Glue.LINE_START, spoken="Block quote", group=_LINES),
    *(
        make_mark(
            f"heading {said}",
            "#" * level + " ",
            Glue.LINE_START,
            spoken=f"Heading {name}",
            group=_LINES,
        )
        for level, name in enumerate(("one", "two", "three", "four", "five", "six"), 1)
        for said in (name, str(level))
    ),
)


#: Whole-phrase commands, by the words that say them.
COMMANDS: dict[tuple[str, ...], Command] = {
    tuple(phrase.split()): entry.command for entry in COMMAND_HELP for phrase in entry.phrases
}

#: Commands said with words after them ("select the cat"), by their opening words.
PREFIXES: dict[tuple[str, ...], Command] = {
    tuple(prefix.split()): entry.command for entry in PREFIX_HELP for prefix in entry.prefixes
}

#: The escape word. "literal comma" types *comma*.
LITERAL = "literal"

#: Spelling mode's letters. A recogniser mishears single letters all the time --
#: "bee", "be" and "B" are one sound -- so the phonetic alphabet is accepted as
#: well, and it is the one to use when a letter matters.
SPELLING_ALPHABET: dict[str, str] = {
    "alpha": "a",
    "alfa": "a",
    "bravo": "b",
    "charlie": "c",
    "delta": "d",
    "echo": "e",
    "foxtrot": "f",
    "golf": "g",
    "hotel": "h",
    "india": "i",
    "juliet": "j",
    "juliett": "j",
    "kilo": "k",
    "lima": "l",
    "mike": "m",
    "november": "n",
    "oscar": "o",
    "papa": "p",
    "quebec": "q",
    "romeo": "r",
    "sierra": "s",
    "tango": "t",
    "uniform": "u",
    "victor": "v",
    "whiskey": "w",
    "whisky": "w",
    "x-ray": "x",
    "xray": "x",
    "yankee": "y",
    "zulu": "z",
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

#: Marks that count only while spelling, where "dot" in "bravo dot com" is a
#: full stop with no space and nowhere near the end of a sentence.
SPELLING_MARKS: dict[str, str] = {"dot": ".", "point": ".", "dash": "-"}

_BY_FIRST_WORD: dict[str, list[tuple[str, ...]]] = {}
for _phrase in [mark.phrase for mark in MARKS] + list(COMMANDS):
    _BY_FIRST_WORD.setdefault(_phrase[0], []).append(_phrase)
for _candidates in _BY_FIRST_WORD.values():
    _candidates.sort(key=len, reverse=True)

_MARK_BY_PHRASE: dict[tuple[str, ...], Mark] = {mark.phrase: mark for mark in MARKS}


def longest_phrase(words: list[str], start: int) -> tuple[str, ...] | None:
    """The longest mark or command phrase beginning at *words[start]*, if any."""
    if start >= len(words):
        return None
    for phrase in _BY_FIRST_WORD.get(words[start], ()):
        if tuple(words[start : start + len(phrase)]) == phrase:
            return phrase
    return None


def mark_for(phrase: tuple[str, ...]) -> Mark | None:
    """The mark *phrase* names, or ``None`` when it is a command or nothing."""
    return _MARK_BY_PHRASE.get(phrase)


class Vocabulary:
    """Everything one dictation language matches a phrase against.

    *marks* maps a phrase to the marks it writes -- usually one, two for
    Spanish "punto y aparte". *folds* says the phrase's words are compared
    without accents (the table's own phrases are stored that way already).
    """

    def __init__(
        self,
        marks: dict[tuple[str, ...], tuple[Mark, ...]],
        commands: dict[tuple[str, ...], Command],
        *,
        folds: bool = False,
        capital_words: Iterable[str] = (),
        space_words: Iterable[str] = (),
        prefixes: dict[tuple[str, ...], Command] | None = None,
    ) -> None:
        self.marks = marks
        self.commands = commands
        #: Opening words of a command that takes words after it, longest first.
        self.prefixes = sorted((prefixes or {}).items(), key=lambda item: -len(item[0]))
        self.folds = folds
        self.capital_words = frozenset(capital_words)
        self.space_words = frozenset(space_words)
        by_first: dict[str, list[tuple[str, ...]]] = {}
        for phrase in list(marks) + list(commands):
            by_first.setdefault(phrase[0], []).append(phrase)
        for candidates in by_first.values():
            candidates.sort(key=len, reverse=True)
        self._by_first = by_first

    def prefix(self, words: tuple[str, ...]) -> tuple[Command, tuple[str, ...]] | None:
        """The command *words* open with, and the words after it -- only when
        there are some: "select" on its own is not a search for nothing."""
        for opening, command in self.prefixes:
            if len(words) > len(opening) and words[: len(opening)] == opening:
                return command, words[len(opening) :]
        return None

    def longest(self, words: list[str], start: int) -> tuple[str, ...] | None:
        """The longest mark or command phrase beginning at *words[start]*."""
        if start >= len(words):
            return None
        for phrase in self._by_first.get(words[start], ()):
            if tuple(words[start : start + len(phrase)]) == phrase:
                return phrase
        return None


#: English, as dictation has always matched it.
ENGLISH = Vocabulary({mark.phrase: (mark,) for mark in MARKS}, COMMANDS, prefixes=PREFIXES)

#: English mark words that are everyday Spanish words too ("colon", "Colón"),
#: left out of the Spanish vocabulary so Spanish text keeps them.
_SPANISH_COLLISIONS = frozenset({("colon",)})


@lru_cache(maxsize=8)
def _spanish(spoken_marks: bool, commands: bool) -> Vocabulary:
    from quill.core.windows_dictation.speech_language import fold
    from quill.core.windows_dictation.vocabulary_es import (
        SPANISH_CAPITAL_WORDS,
        SPANISH_COMMAND_HELP,
        SPANISH_MARKS,
        SPANISH_PREFIX_HELP,
        SPANISH_SPACE_WORDS,
        SPANISH_SWITCH_HELP,
    )

    marks = {
        phrase: written
        for phrase, written in ENGLISH.marks.items()
        if phrase not in _SPANISH_COLLISIONS
    }
    if spoken_marks:
        marks.update({
            tuple(fold(said).split()): written for said, written in SPANISH_MARKS.items()
        })
    table = dict(COMMANDS)
    # The way back to English works whether or not the drafted commands are on:
    # somebody who switched by voice must be able to switch back by voice.
    for entry in SPANISH_SWITCH_HELP:
        table.update({tuple(fold(said).split()): entry.command for said in entry.phrases})
    prefixes = dict(PREFIXES)
    if commands:
        for prefix in SPANISH_PREFIX_HELP:
            prefixes.update({tuple(fold(said).split()): prefix.command for said in prefix.prefixes})
        for entry in SPANISH_COMMAND_HELP:
            table.update({tuple(fold(said).split()): entry.command for said in entry.phrases})
    return Vocabulary(
        marks,
        table,
        folds=True,
        capital_words=SPANISH_CAPITAL_WORDS,
        space_words=SPANISH_SPACE_WORDS,
        prefixes=prefixes,
    )


def vocabulary_for(language: str = "en", *, spoken_marks: bool = True) -> Vocabulary:
    """What a phrase in *language* is matched against.

    *spoken_marks* is whether the Spanish punctuation words count -- the
    controller passes ``True`` only while the engine is not punctuating by
    itself (dict.md 9.4 C, option 1). English ignores it: its mark words are
    rarely ordinary words, and they have always worked alongside automatic
    punctuation. The Spanish commands join only when
    :func:`~quill.core.windows_dictation.speech_language.spanish_commands_enabled`.
    """
    from quill.core.windows_dictation.speech_language import (
        coerce_speech_language,
        spanish_commands_enabled,
    )

    if coerce_speech_language(language) == "en":
        return ENGLISH
    return _spanish(spoken_marks, spanish_commands_enabled())
