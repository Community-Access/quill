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
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "COMMANDS",
    "COMMAND_HELP",
    "DASH_STYLES",
    "LITERAL",
    "MARKS",
    "SPELLING_ALPHABET",
    "Command",
    "CommandHelp",
    "Glue",
    "Mark",
    "dash_text",
    "longest_phrase",
    "mark_for",
]


class Glue(StrEnum):
    """How a mark sits against the text on either side of it."""

    #: Hugs the word before it; a space follows before the next word. ``. , ? !``
    LEFT = "left"
    #: Takes a space before it and hugs the word after it. ``( [`` and an
    #: opening quotation mark.
    OPEN = "open"
    #: Hugs both sides. A hyphen, a slash, an apostrophe.
    JOIN = "join"
    #: Ends the line or indents it. No space on either side, and never a space
    #: at the start of the line that follows.
    BREAK = "break"
    #: Stands alone like a word: a space either side. ``& + =``
    WORD = "word"


class Command(StrEnum):
    """What a whole-phrase command does."""

    SCRATCH = "scratch"
    UNDO = "undo"
    STOP = "stop"
    SELECT = "select"
    CAPITALIZE = "capitalize"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    READ_BACK = "read_back"
    DELETE_WORD = "delete_word"
    DELETE_SENTENCE = "delete_sentence"
    LINE_START = "line_start"
    LINE_END = "line_end"
    DOCUMENT_START = "document_start"
    DOCUMENT_END = "document_end"
    SPELL_ON = "spell_on"
    SPELL_OFF = "spell_off"
    HELP = "help"


@dataclass(frozen=True, slots=True)
class Mark:
    """A spoken phrase that becomes a character or two in the document."""

    phrase: tuple[str, ...]
    text: str
    glue: Glue
    #: A sentence ends here, so the next word takes a capital.
    ends_sentence: bool = False
    #: What the read-back says when this is *all* a phrase inserted -- a blank
    #: line speaks as nothing at all, which is indistinguishable from failure.
    spoken: str = ""
    #: Which heading the command reference lists it under.
    group: str = "Punctuation"


def _mark(
    phrase: str,
    text: str,
    glue: Glue,
    *,
    ends: bool = False,
    spoken: str = "",
    group: str = "Punctuation",
) -> Mark:
    return Mark(tuple(phrase.split()), text, glue, ends, spoken, group)


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


#: Every mark, in the order the command reference lists them.
MARKS: tuple[Mark, ...] = (
    _mark("period", ".", Glue.LEFT, ends=True),
    _mark("full stop", ".", Glue.LEFT, ends=True),
    _mark("comma", ",", Glue.LEFT),
    _mark("question mark", "?", Glue.LEFT, ends=True),
    _mark("exclamation point", "!", Glue.LEFT, ends=True),
    _mark("exclamation mark", "!", Glue.LEFT, ends=True),
    _mark("colon", ":", Glue.LEFT),
    _mark("semicolon", ";", Glue.LEFT),
    _mark("ellipsis", "...", Glue.LEFT),
    _mark("open quote", '"', Glue.OPEN),
    _mark("begin quote", '"', Glue.OPEN),
    _mark("close quote", '"', Glue.LEFT),
    _mark("end quote", '"', Glue.LEFT),
    _mark("open single quote", "'", Glue.OPEN),
    _mark("close single quote", "'", Glue.LEFT),
    _mark("apostrophe", "'", Glue.JOIN),
    _mark("open parenthesis", "(", Glue.OPEN, group="Brackets"),
    _mark("open paren", "(", Glue.OPEN, group="Brackets"),
    _mark("left parenthesis", "(", Glue.OPEN, group="Brackets"),
    _mark("close parenthesis", ")", Glue.LEFT, group="Brackets"),
    _mark("close paren", ")", Glue.LEFT, group="Brackets"),
    _mark("right parenthesis", ")", Glue.LEFT, group="Brackets"),
    _mark("open bracket", "[", Glue.OPEN, group="Brackets"),
    _mark("left bracket", "[", Glue.OPEN, group="Brackets"),
    _mark("close bracket", "]", Glue.LEFT, group="Brackets"),
    _mark("right bracket", "]", Glue.LEFT, group="Brackets"),
    _mark("open brace", "{", Glue.OPEN, group="Brackets"),
    _mark("close brace", "}", Glue.LEFT, group="Brackets"),
    _mark("open angle bracket", "<", Glue.OPEN, group="Brackets"),
    _mark("close angle bracket", ">", Glue.LEFT, group="Brackets"),
    _mark("hyphen", "-", Glue.JOIN, group="Dashes and joining"),
    _mark("dash", DASH_PLACEHOLDER, Glue.JOIN, group="Dashes and joining"),
    _mark("slash", "/", Glue.JOIN, group="Dashes and joining"),
    _mark("forward slash", "/", Glue.JOIN, group="Dashes and joining"),
    _mark("backslash", "\\", Glue.JOIN, group="Dashes and joining"),
    _mark("underscore", "_", Glue.JOIN, group="Dashes and joining"),
    _mark("at sign", "@", Glue.JOIN, group="Symbols"),
    _mark("hash sign", "#", Glue.OPEN, group="Symbols"),
    _mark("number sign", "#", Glue.OPEN, group="Symbols"),
    _mark("dollar sign", "$", Glue.OPEN, group="Symbols"),
    _mark("percent sign", "%", Glue.LEFT, group="Symbols"),
    _mark("ampersand", "&", Glue.WORD, group="Symbols"),
    _mark("asterisk", "*", Glue.JOIN, group="Symbols"),
    _mark("plus sign", "+", Glue.WORD, group="Symbols"),
    _mark("minus sign", "-", Glue.WORD, group="Symbols"),
    _mark("equals sign", "=", Glue.WORD, group="Symbols"),
    _mark("new line", "\n", Glue.BREAK, ends=True, spoken="New line", group="Lines and layout"),
    _mark("newline", "\n", Glue.BREAK, ends=True, spoken="New line", group="Lines and layout"),
    _mark(
        "new paragraph",
        "\n\n",
        Glue.BREAK,
        ends=True,
        spoken="New paragraph",
        group="Lines and layout",
    ),
    _mark("tab key", "\t", Glue.BREAK, spoken="Tab", group="Lines and layout"),
    _mark("press tab", "\t", Glue.BREAK, spoken="Tab", group="Lines and layout"),
    _mark("tab", "\t", Glue.BREAK, spoken="Tab", group="Lines and layout"),
)


@dataclass(frozen=True, slots=True)
class CommandHelp:
    """One command as the reference describes it."""

    command: Command
    phrases: tuple[str, ...]
    description: str
    group: str


#: Every whole-phrase command, with what it does, in reference order.
COMMAND_HELP: tuple[CommandHelp, ...] = (
    CommandHelp(
        Command.SCRATCH,
        ("scratch that", "delete that"),
        "Removes the phrase you dictated last. Say it again to remove the one "
        "before. A phrase you have typed into since is left alone.",
        "Correcting",
    ),
    CommandHelp(
        Command.UNDO,
        ("undo that", "undo", "undo last"),
        "The same as pressing Ctrl+Z.",
        "Correcting",
    ),
    CommandHelp(
        Command.SELECT,
        ("select that",),
        "Selects the phrase you dictated last, so you can change or format it "
        "with the keyboard. The next phrase you say replaces it.",
        "Correcting",
    ),
    CommandHelp(
        Command.CAPITALIZE,
        ("capitalize that", "cap that"),
        "Gives every word of the last phrase a capital: meeting notes becomes Meeting Notes.",
        "Correcting",
    ),
    CommandHelp(
        Command.UPPERCASE,
        ("all caps that", "uppercase that"),
        "Puts the last phrase in capitals.",
        "Correcting",
    ),
    CommandHelp(
        Command.LOWERCASE,
        ("no caps that", "lowercase that"),
        "Puts the last phrase in small letters.",
        "Correcting",
    ),
    CommandHelp(
        Command.DELETE_WORD,
        ("delete word", "delete last word"),
        "Deletes the word just before the cursor.",
        "Correcting",
    ),
    CommandHelp(
        Command.DELETE_SENTENCE,
        ("delete sentence", "delete last sentence"),
        "Deletes from the start of the sentence the cursor is in up to the cursor.",
        "Correcting",
    ),
    CommandHelp(
        Command.READ_BACK,
        ("read that", "repeat that"),
        "Reads the last phrase aloud again.",
        "Correcting",
    ),
    CommandHelp(
        Command.LINE_START,
        ("go to beginning of line", "go to start of line"),
        "Moves the cursor to the start of the line.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.LINE_END,
        ("go to end of line",),
        "Moves the cursor to the end of the line.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.DOCUMENT_START,
        ("go to top", "go to start of document", "go to beginning of document"),
        "Moves the cursor to the start of the document.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.DOCUMENT_END,
        ("go to bottom", "go to end of document"),
        "Moves the cursor to the end of the document.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.SPELL_ON,
        ("start spelling", "spell mode", "spelling mode"),
        "Starts spelling mode: every phrase is read as letters until you say "
        "stop spelling. See Spelling below.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.SPELL_OFF,
        ("stop spelling", "end spelling", "spelling off"),
        "Leaves spelling mode.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.HELP,
        ("what can i say", "show commands", "dictation commands"),
        "Opens this list.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.STOP,
        ("stop dictation", "stop dictating", "stop listening"),
        "Stops dictation. With a wake phrase set, dictation goes back to waiting for it.",
        "Dictation itself",
    ),
)

#: Whole-phrase commands, by the words that say them.
COMMANDS: dict[tuple[str, ...], Command] = {
    tuple(phrase.split()): entry.command for entry in COMMAND_HELP for phrase in entry.phrases
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
