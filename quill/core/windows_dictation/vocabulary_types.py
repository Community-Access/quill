"""The shapes dictation's tables are made of: marks, commands and their help.

Split out of :mod:`~quill.core.windows_dictation.vocabulary` (GATE-11) when the
2026-10-05 gap plan added the Markdown marks, the modes, and the commands that
take words after them ("select the cat", "paste clip three"). The types live
here so the tables -- :mod:`~quill.core.windows_dictation.vocabulary` for the
marks and :mod:`~quill.core.windows_dictation.vocabulary_commands` for the
commands -- can each import them without importing each other.
``vocabulary`` re-exports every name, so nothing that imported them from there
changes.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["Command", "CommandHelp", "Glue", "Mark", "PrefixHelp", "make_mark"]


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
    #: Starts a line: takes a new line first when the cursor is not at the
    #: start of one, then hugs the next word. ``- `` for a bullet, ``## `` for a
    #: heading. Counted only at the start of a phrase (dict.md question 4).
    LINE_START = "line_start"
    #: Opens or closes, by how many came before it on the line: a backtick.
    TOGGLE = "toggle"


class Command(StrEnum):
    """What a command does. Most are a whole phrase; some take words after them."""

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
    CORRECT = "correct"
    CHOOSE_1 = "choose_1"
    CHOOSE_2 = "choose_2"
    CHOOSE_3 = "choose_3"
    # 2026-10-05, the gap plan: modes, units, clips and snippets, languages.
    COPY_ALL = "copy_all"
    COPY_THAT = "copy_that"
    SHOW_CLIPS = "show_clips"
    SHOW_SNIPPETS = "show_snippets"
    CAPS_ON = "caps_on"
    CAPS_OFF = "caps_off"
    ALL_CAPS_ON = "all_caps_on"
    ALL_CAPS_OFF = "all_caps_off"
    NO_SPACE_ON = "no_space_on"
    NO_SPACE_OFF = "no_space_off"
    SPELL_THAT = "spell_that"
    SELECT_NEXT = "select_next"
    SELECT_PREVIOUS = "select_previous"
    PARAGRAPH_START = "paragraph_start"
    PARAGRAPH_END = "paragraph_end"
    SELECT_PARAGRAPH = "select_paragraph"
    SELECT_SENTENCE = "select_sentence"
    SELECT_LINE = "select_line"
    SWITCH_SPANISH = "switch_spanish"
    SWITCH_ENGLISH = "switch_english"
    # Commands that take words after them (PrefixHelp).
    PASTE_SLOT = "paste_slot"
    INSERT_SNIPPET = "insert_snippet"
    EXPAND = "expand"
    SELECT_WORDS = "select_words"
    GO_TO_WORDS = "go_to_words"
    GO_AFTER_WORDS = "go_after_words"
    CORRECT_WORDS = "correct_words"
    SPELL_WORDS = "spell_words"
    USE_CONTEXT = "use_context"


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


def make_mark(
    phrase: str,
    text: str,
    glue: Glue,
    *,
    ends: bool = False,
    spoken: str = "",
    group: str = "Punctuation",
) -> Mark:
    return Mark(tuple(phrase.split()), text, glue, ends, spoken, group)


@dataclass(frozen=True, slots=True)
class CommandHelp:
    """One whole-phrase command as the reference describes it."""

    command: Command
    phrases: tuple[str, ...]
    description: str
    group: str


@dataclass(frozen=True, slots=True)
class PrefixHelp:
    """A command said with words after it: "select the cat", "paste clip three".

    Still a whole phrase -- the command words must open it, and everything after
    them is the *argument*. A whole-phrase command always wins over a prefix
    ("select that" is the last phrase, not a search for "that").
    """

    command: Command
    #: The opening words, as said: "select", "paste clip".
    prefixes: tuple[str, ...]
    #: What the words after it are, for the reference: "words in the document".
    argument: str
    description: str
    group: str
