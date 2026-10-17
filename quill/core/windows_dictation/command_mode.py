"""The command word: "QUILL scratch that" is for QUILL, and is never typed.

D-1 of the 2026-10-13 dictation gap plan (the owner's request). Bare
whole-phrase commands ("scratch that") work for short fixed phrases, but in
another program a misheard one is typed into somebody's email. Saying the
command word first marks one utterance as meant for QUILL:

* **The command word** is ``QUILL`` unless the person chooses another
  (``windows_dictation_command_prefix``). It is matched only as the **first
  word of an utterance after a pause** -- the voice detector's phrase boundary,
  which every engine already gives -- with the wake phrase's forgiveness
  (:func:`~quill.core.windows_dictation.wake.match_wake`: the same word, the
  same Soundex, or one edit), because a recogniser that was never told "Quill"
  writes "quil" or "Quill,". "I told Quill about it" is dictated.
* **What follows it** is matched against the one command table
  (:mod:`~quill.core.windows_dictation.vocabulary_commands`) and the few
  commands that only make sense after the command word
  (:data:`COMMAND_MODE_HELP`: type that, command mode, dictation mode). Later
  grammar (D-10's "replace X with Y", D-19, D-2's review commands, D-23's
  formats) joins one of those tables and works after the command word with no
  change here.
* **Not a command: nothing is typed.** The error cue and one sentence
  (:func:`not_a_command`); "QUILL type that" writes the refused words, once.
* **"literal QUILL" writes the word** (:func:`escape_literal_prefix`), as
  "literal comma" writes *comma*.
* **A one-word command word is fine** -- the wake phrase's two-word rule does
  not apply, because nothing happens unless a command follows -- but
  :func:`command_prefix_problem` refuses common English words and the
  person's own My Words vocabulary.

The state (one command, command mode, the timeout) is the controller's:
:mod:`~quill.core.windows_dictation.command_mode_mixin`.

Pure and wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from quill.core.windows_dictation.parser import RecognizedPhrase, RecognizedWord
from quill.core.windows_dictation.vocabulary import COMMANDS, LITERAL, MARKS, PREFIXES
from quill.core.windows_dictation.vocabulary_types import Command, CommandHelp, PrefixHelp
from quill.core.windows_dictation.wake import match_wake, wake_words

__all__ = [
    "COMMAND_MODE_HELP",
    "COMMAND_MODE_PREFIX_HELP",
    "COMMAND_MODE_SAID",
    "DEFAULT_COMMAND_PREFIX",
    "DEFAULT_COMMAND_TIMEOUT",
    "DICTATION_MODE_SAID",
    "MAX_COMMAND_TIMEOUT",
    "MIN_COMMAND_TIMEOUT",
    "SAY_A_COMMAND",
    "coerce_prefix",
    "coerce_timeout",
    "command_only",
    "command_prefix_problem",
    "escape_literal_prefix",
    "not_a_command",
    "split_phrase",
    "split_prefix",
]

DEFAULT_COMMAND_PREFIX = "QUILL"
#: Seconds command mode (and one armed command) waits for a command.
DEFAULT_COMMAND_TIMEOUT = 8
MIN_COMMAND_TIMEOUT = 5
MAX_COMMAND_TIMEOUT = 30

#: Said once on entering command mode; and when "dictation mode" leaves it.
COMMAND_MODE_SAID = "Command mode."
DICTATION_MODE_SAID = "Dictation mode."
#: Said when the Command Key arms one command and there is no tone to play.
SAY_A_COMMAND = "Say a command."

#: Whole-phrase commands that only count after the command word (or with the
#: Command Key, or in command mode). In the reference, "The command word".
COMMAND_MODE_HELP: tuple[CommandHelp, ...] = (
    CommandHelp(
        Command.TYPE_THAT,
        ("type that", "write that"),
        "Writes the words that were just refused as not a command, once.",
        "The command word",
    ),
    CommandHelp(
        Command.COMMAND_MODE,
        ("command mode",),
        "Everything you say is a command, with no command word, until you say "
        "dictation mode or stop giving commands for a few seconds. You hear a "
        "falling tone when it ends.",
        "The command word",
    ),
    CommandHelp(
        Command.DICTATION_MODE,
        ("dictation mode",),
        "Leaves command mode at once: what you say is written again.",
        "The command word",
    ),
)

#: Commands with words after them that only count after the command word. Empty:
#: D-10 and D-19's "replace X with Y" and "change that to Y" joined the one
#: table instead (vocabulary_commands.PREFIX_HELP), so they work after the
#: command word and, with strict mode off, on their own.
COMMAND_MODE_PREFIX_HELP: tuple[PrefixHelp, ...] = ()

_ONLY_AFTER_THE_WORD: dict[tuple[str, ...], Command] = {
    tuple(phrase.split()): entry.command for entry in COMMAND_MODE_HELP for phrase in entry.phrases
}

#: Words heard all day, which would make every other sentence a command.
_COMMON = frozenset(
    """
    a about after again all also am an and any are as at back be because been
    before being but by can come could day did do does done down each even
    every first for from get give go going good got had has have he her here
    him his how i if in into is it its just know last like look make man many
    me more most much my new no not now of off oh ok okay on one only or other
    our out over people right said say see she should so some still such take
    than thank thanks that the their them then there these they thing think
    this those through time to too two up us very want was way we well were
    what when where which while who why will with work would yeah year yes yet
    you your hello hi hey please sorry sure maybe never always today tomorrow
    yesterday morning night dear regards best love sir madam mr mrs ms dr
    computer
    """.split()
)


def _command_words() -> frozenset[str]:
    """Every word of every command and mark: a command word that is one of
    them would be both."""
    phrases = [*COMMANDS, *PREFIXES, *(mark.phrase for mark in MARKS), *_ONLY_AFTER_THE_WORD]
    return frozenset(word for phrase in phrases for word in phrase) | {LITERAL}


def coerce_prefix(value: object) -> str:
    """The saved command word, tidied: spaces collapsed. ``""`` means none."""
    return " ".join(str(value or "").split())


def coerce_timeout(value: object) -> int:
    """Seconds, held between :data:`MIN_COMMAND_TIMEOUT` and the maximum."""
    try:
        seconds = int(float(str(value)))
    except (TypeError, ValueError):
        return DEFAULT_COMMAND_TIMEOUT
    return max(MIN_COMMAND_TIMEOUT, min(MAX_COMMAND_TIMEOUT, seconds))


def command_prefix_problem(prefix: str, my_words: Iterable[str] = ()) -> str:
    """Why *prefix* would make a poor command word, or ``""`` when it is fine.

    Empty is fine: no spoken command word, so only the Command Key gives
    commands. *my_words* is the person's My Words and Phrases vocabulary: a
    word they dictate on purpose must not become a command.
    """
    words = wake_words(prefix)
    if not prefix.strip():
        return ""
    if not words or len(words) > 2:
        return "Use one word for the command word, or two at most."
    if sum(len(word) for word in words) < 4:
        return "Use a longer command word: short words are easily heard by mistake."
    common = [word for word in words if word in _COMMON or word in _command_words()]
    if len(common) == len(words):
        return (
            f"{prefix} is a word said in ordinary sentences or a dictation command, so "
            "it would turn what you say into commands by accident. Choose a name, "
            "like QUILL."
        )
    mine = {" ".join(wake_words(word)) for word in my_words}
    if " ".join(words) in mine:
        return (
            f"{prefix} is in your words in My Words and Phrases, so you dictate it on "
            "purpose. Choose another command word."
        )
    return ""


def split_prefix(lexical_words: Sequence[str], prefix: str) -> tuple[bool, tuple[str, ...]]:
    """``(True, the words after it)`` when *lexical_words* open with *prefix*.

    Only at the start: the first word of the utterance (or the first two, for a
    two-word command word), matched forgivingly. ``(False, the words)`` otherwise,
    and always when *prefix* is empty.
    """
    heard = wake_words(" ".join(lexical_words))
    if not wake_words(prefix):
        return False, tuple(heard)
    used = match_wake(heard, prefix)
    if used is None:
        return False, tuple(heard)
    return True, tuple(heard[used:])


def split_phrase(phrase: RecognizedPhrase, prefix: str) -> RecognizedPhrase | None:
    """The words after the command word, as recognised, or ``None`` when the
    phrase does not open with it."""
    opened, _rest = split_prefix([word.lexical for word in phrase.words], prefix)
    if not opened:
        return None
    used = len(wake_words(prefix))
    counted = 0
    rest: list[RecognizedWord] = []
    for word in phrase.words:
        if counted < used and wake_words(word.lexical):
            counted += len(wake_words(word.lexical))
            continue
        rest.append(word)
    text = " ".join(word.display for word in rest)
    return RecognizedPhrase(tuple(rest), text=text, confidence=phrase.confidence)


def command_only(words: Sequence[str]) -> Command | None:
    """The command-word-only command *words* say (folded), if any."""
    return _ONLY_AFTER_THE_WORD.get(tuple(words))


def escape_literal_prefix(phrase: RecognizedPhrase, prefix: str) -> RecognizedPhrase:
    """ "literal QUILL" writes the command word itself, spelled as it is set.

    The parser's ``literal`` escapes a mark or a command phrase; this extends it
    to the command word, which is not in the table. The escaped word keeps a
    lexical form no table matches, so it is written and nothing else happens.
    """
    if not wake_words(prefix):
        return phrase
    words = list(phrase.words)
    out: list[RecognizedWord] = []
    index = 0
    changed = False
    while index < len(words):
        word = words[index]
        following = words[index + 1] if index + 1 < len(words) else None
        if (
            following is not None
            and wake_words(word.lexical) == [LITERAL]
            and match_wake(wake_words(following.lexical), prefix) is not None
        ):
            out.append(RecognizedWord(prefix.lower(), prefix))
            index += 2
            changed = True
            continue
        out.append(word)
        index += 1
    if not changed:
        return phrase
    return RecognizedPhrase(
        tuple(out),
        text=" ".join(word.display for word in out),
        confidence=phrase.confidence,
        previous_mark=phrase.previous_mark,
        alternatives=phrase.alternatives,
    )


def not_a_command(prefix: str) -> str:
    """Said, with the error cue, when what followed the command word is not a
    command. Nothing was typed."""
    if wake_words(prefix):
        return f"Not a command. Say it again, or say {prefix} type that to write it."
    return "Not a command. Say it again, or press the Command Key and say type that to write it."
