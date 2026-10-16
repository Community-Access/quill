"""The list of everything dictation understands, written from the table itself.

Two readers, one source. The "What can I say?" window (say it, or press the
Commands button in Dictation Settings) shows :func:`commands_reference` as plain
text, and ``scripts/build_dictation_commands.py`` writes the same content as
Markdown into both editors' documentation. Both come from
:mod:`~quill.core.windows_dictation.vocabulary`, so a phrase added there appears
in the window and the published reference the same day -- and
``tests/unit/scripts/test_dictation_commands_doc.py`` fails if the published
copy falls behind.

wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from quill.core.windows_dictation.command_mode import DEFAULT_COMMAND_PREFIX
from quill.core.windows_dictation.vocabulary import (
    COMMAND_HELP,
    DASH_STYLES,
    MARKS,
    PREFIX_HELP,
    SPELLING_ALPHABET,
    Mark,
)
from quill.core.windows_dictation.wake import DEFAULT_STOP_PHRASE, DEFAULT_WAKE_PHRASE

__all__ = ["commands_reference"]

_SHOWN = {
    "\n": "a line break",
    "\n\n": "a blank line (new paragraph)",
    "\t": "a tab",
    '"': 'the quotation mark "',
    "```" + chr(10): "a code fence (three backticks) on a line of its own",
}


def _shows(mark: Mark, dash: str) -> str:
    if mark.text == "{dash}":
        return "a dash, written as " + DASH_STYLES.get(dash, DASH_STYLES["em"])[0].lower()
    return _SHOWN.get(mark.text, mark.text)


def _grouped(marks: Iterable[Mark]) -> dict[str, list[Mark]]:
    groups: dict[str, list[Mark]] = {}
    for mark in marks:
        groups.setdefault(mark.group, []).append(mark)
    return groups


def _spanish_sections(heading: Any, row: Any, table_head: Any, lines: list[str], md: bool) -> None:
    """The Spanish punctuation words, and the drafted commands when switched on."""
    from quill.core.windows_dictation.speech_language import spanish_commands_enabled
    from quill.core.windows_dictation.vocabulary_es import (
        SPANISH_COMMAND_HELP,
        spanish_mark_rows,
    )

    heading("Spanish punctuation")
    note = (
        "With the dictation language set to Spanish, these words write punctuation only "
        "while automatic punctuation is off (or with Windows speech recognition): coma "
        "and punto are everyday words too. Commands are the English ones above."
    )
    lines.append(note)
    if md:
        lines.append("")  # a table needs a blank line before it
    table_head("Say", "Writes")
    for said, writes in spanish_mark_rows():
        writes = "a dash, in the style chosen for dash" if writes == "{dash}" else writes
        row(said, _SHOWN.get(writes, writes.replace("\n\n", " and a new paragraph")))
    if spanish_commands_enabled():
        heading("Spanish commands (draft, awaiting review)")
        table_head("Say, on its own", "What happens")
        for entry in SPANISH_COMMAND_HELP:
            row(" or ".join(f'"{phrase}"' for phrase in entry.phrases), entry.description)


def _command_word_section(
    heading: Any,
    row: Any,
    table_head: Any,
    lines: list[str],
    md: bool,
    prefix: str,
    required: bool,
) -> None:
    """The command word (D-1): how it works, strict mode, and its own commands."""
    from quill.core.windows_dictation.command_mode import COMMAND_MODE_HELP

    heading("The command word")
    word = prefix or "the command word"
    said = f'"{prefix}"' if prefix else "the command word"
    strict = (
        "Strict mode is on, so a command said on its own is written as words: say the "
        "command word first. The stop phrase always works on its own."
        if required
        else 'With "Commands only after the command word" switched on in More Dictation '
        "Settings (it is on in QUILL Transcribe), a command said on its own is written as "
        "words, except the stop phrase."
    )
    for sentence in (
        (
            f"Say {said} first to give a command instead of dictating: "
            f'"{word} scratch that". It counts only as the first word after a pause, '
            f'so "I told {word} about it" is written as words.'
            if prefix
            else "No command word is set, so give commands with the Speak a Command key."
        ),
        "Every command in this list works after the command word. If what follows it is "
        f'not a command, nothing is typed: you hear "Not a command", and "{word} type '
        'that" writes it after all.',
        f'Say "literal {word}" to write the word itself.',
        strict,
        "Speak a Command (F11 in QUILL and QUILL Lite, and in QUILL Transcribe the "
        "Command Key you choose) does the same without the word: the next thing you say "
        "is a command. Press it twice for command mode.",
    ):
        lines.append(("- " + sentence) if md else sentence)
    if md:
        lines.append("")
    table_head("Say, after the command word", "What happens")
    for entry in COMMAND_MODE_HELP:
        row(" or ".join(f'"{phrase}"' for phrase in entry.phrases), entry.description)


def _review_section(
    heading: Any, row: Any, table_head: Any, lines: list[str], md: bool, prefix: str
) -> None:
    """Review before inserting (D-2): what the review is, and its phrases."""
    from quill.core.windows_dictation.review_session import REVIEW_HELP

    heading("Review before inserting")
    word = prefix or "the command word"
    for sentence in (
        f'Say "{word} review that" to take the last phrase back out and hold it in '
        "Review Dictation (Shift+F4), where you can read it, edit it, ask the "
        "AI to change it and insert it once. Nothing is written until you insert it.",
        "While the review is open, what you say is written into it. Say the command word "
        "first to give an instruction instead, or turn on Talk About It in the window.",
        "Changing words with AI needs AI help switched on and your ChatGPT subscription "
        "or your own AI key. With AI off, the review still lets you edit and insert.",
    ):
        lines.append(("- " + sentence) if md else sentence)
    if md:
        lines.append("")
    table_head("Say, after the command word", "What happens")
    for entry in REVIEW_HELP:
        row(" or ".join(f'"{phrase}"' for phrase in entry.phrases), entry.description)


def commands_reference(
    *,
    markdown: bool = False,
    dash: str = "em",
    wake_phrase: str = "",
    stop_phrase: str = "",
    own_phrases: Iterable[tuple[str, str]] = (),
    language: str = "en",
    external: bool = False,
    command_prefix: str = DEFAULT_COMMAND_PREFIX,
    prefix_required: bool = False,
    review: bool = True,
) -> str:
    """Every phrase dictation acts on, grouped, with what each one does.

    *markdown* gives headings and tables for the published guide; otherwise the
    text is plain, one entry per line, for a read-only window a screen reader
    moves through with the arrow keys. *wake_phrase*, *stop_phrase* and
    *own_phrases* (the user's replacements) personalise the window; the
    published copy leaves them out. *language* ``"es"`` adds the Spanish
    punctuation words (and, in a development build that has them switched on,
    the drafted Spanish commands).

    *external* (D-7, 2026-10-13) is the list for dictating into another program
    -- QUILL Transcribe and Inkwell's Dictate Anywhere: only the commands that
    work there (:data:`~quill.core.windows_dictation.anywhere.EXTERNAL_COMMANDS`),
    no wake phrase, and the two limits of inserting into another program. The
    editors' list, the default, is unchanged. *review* False leaves out Review
    Dictation (D-2) for a host without it (Quill Inkwell).
    """
    from quill.core.windows_dictation.anywhere import EXTERNAL_COMMANDS

    def works(command: object) -> bool:
        return not external or command in EXTERNAL_COMMANDS

    lines: list[str] = []

    def heading(text: str, level: int = 2) -> None:
        if lines:
            lines.append("")
        lines.append(("#" * level + " " + text) if markdown else text.upper())
        lines.append("")

    def row(said: str, does: str) -> None:
        if markdown:
            lines.append(f"| {said} | {does} |")
        else:
            lines.append(f"{said}: {does}")

    def table_head(left: str, right: str) -> None:
        if markdown:
            lines.append(f"| {left} | {right} |")
            lines.append("|---|---|")

    if markdown:
        lines.append("# Dictation commands")
        lines.append("")
        lines.append(
            "Everything QUILL Lite and QUILL's Live Dictation understand, generated "
            "from the table the program itself reads -- so this list and the program "
            "cannot disagree. In either program, say **what can I say** while "
            "dictating to open the same list."
        )
    elif external:
        lines.append(
            "Everything that works while dictating into another program. Read with "
            "the arrow keys; Escape closes."
        )
    else:
        lines.append("Everything dictation understands. Read with the arrow keys; Escape closes.")

    heading("How the commands work")
    for sentence in (
        "Punctuation and layout words can go anywhere in a phrase: "
        '"dear Sam comma new paragraph thank you for the letter".',
        "Commands only work as a whole phrase, said on their own after a pause. "
        '"Delete that line of text" in a sentence is just words.',
        'With "Just write what I say" switched on in Dictation Settings, commands '
        "are written as words too; punctuation, layout and the stop phrase still work.",
        'Say "literal" before any of these to write the word instead: '
        '"literal comma" writes comma.',
        "Moonshine and Whisper add punctuation by themselves; saying it yourself "
        "always wins. With Windows speech recognition, say all of it.",
        (
            "Some commands take words after them: paste clip three, insert snippet "
            "sign off. They work only at the start of a phrase."
            if external
            else "Some commands take words after them: select the cat, paste clip three, "
            "insert snippet sign off. They work only at the start of a phrase."
        ),
        'The Markdown line marks -- "bullet", "numbered item", "block quote" and '
        '"heading one" to "heading six" -- count only at the start of a phrase, so '
        '"the heading two lines down" stays words.',
        "A snippet with blanks asks for each one by name: say the answer, or for a "
        "choice say one of the options or choose and its number. Say skip to leave "
        "one empty, scratch that to go back one, or cancel to type nothing. Then the "
        "whole snippet goes in as one phrase, and scratch that takes all of it back.",
        *(
            (
                "Nothing in the other program is read, so commands that select or find "
                "words are not listed: they work in QUILL's own documents.",
                "Correcting works on the words dictation typed there itself, and only "
                "while the focus has not moved and you have not typed or clicked since. "
                "In Word and Outlook, which change words as they are typed, the "
                "commands that retype words are refused; scratch that and the delete "
                "commands still work.",
                "Where a snippet or an abbreviation puts the cursor in the middle, the "
                "cursor stays at the end instead.",
            )
            if external
            else ()
        ),
    ):
        lines.append(("- " + sentence) if markdown else sentence)

    _command_word_section(
        heading, row, table_head, lines, markdown, command_prefix, prefix_required
    )
    if review:
        _review_section(heading, row, table_head, lines, markdown, command_prefix)

    for group, marks in _grouped(MARKS).items():
        heading(group)
        table_head("Say", "Writes")
        for mark in marks:
            shows = _shows(mark, dash)
            if markdown and shows == mark.text:
                # In a code span, so a backslash or a bracket is shown as itself
                # instead of being read as Markdown.
                fence = "``" if "`" in shows else "`"
                shows = f"{fence} {shows} {fence}" if fence == "``" else f"`{shows}`"
            row(" ".join(mark.phrase), shows)

    groups: dict[str, list[tuple[str, str]]] = {}
    for entry in COMMAND_HELP:
        if not works(entry.command):
            continue
        said = " or ".join(f'"{phrase}"' for phrase in entry.phrases)
        groups.setdefault(entry.group, []).append((said, entry.description))
    for group, entries in groups.items():
        heading("Commands: " + group.lower())
        table_head("Say, on its own", "What happens")
        for said, does in entries:
            row(said, does)

    prefix_groups: dict[str, list[tuple[str, str]]] = {}
    for prefix in PREFIX_HELP:
        if not works(prefix.command):
            continue
        said = " or ".join(f'"{opening} ..."' for opening in prefix.prefixes)
        prefix_groups.setdefault(prefix.group, []).append((
            f"{said} ({prefix.argument})",
            prefix.description,
        ))
    for group, entries in prefix_groups.items():
        heading("Commands with words after them: " + group.lower())
        table_head("Say, at the start of a phrase", "What happens")
        for said, does in entries:
            row(said, does)

    heading("Spelling")
    for sentence in (
        'Say "start spelling", then letters. Everything you say is written as '
        'letters until you say "stop spelling".',
        'Say "capital" before a letter for a capital, and "space" for a space. '
        'Say "all caps" for capitals until "no caps" or the end of the phrase.',
        'Punctuation works while spelling, with no spaces: "jay dot smith at sign '
        'example dot com". "Dot" is a full stop only here.',
        (
            'Say "spell" and the letters to spell one word without starting spelling mode.'
            if external
            else 'Say "spell" and the letters to spell one word without starting spelling '
            'mode, and "spell that" to spell the last phrase over again.'
        ),
        'Letter names work ("bee", "see"), and the phonetic alphabet is '
        "clearer: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, india, "
        "juliet, kilo, lima, mike, november, oscar, papa, quebec, romeo, sierra, "
        "tango, uniform, victor, whiskey, x-ray, yankee, zulu.",
        "Numbers are written as digits: "
        + ", ".join(k for k, v in SPELLING_ALPHABET.items() if v.isdigit())
        + ".",
    ):
        lines.append(("- " + sentence) if markdown else sentence)

    heading("Starting and stopping by voice")
    phrase = wake_phrase or DEFAULT_WAKE_PHRASE
    stop = stop_phrase or DEFAULT_STOP_PHRASE
    voice = (
        (
            f'Say "{stop}" on its own, after a pause, to stop dictation. '
            '"Stop dictation" always works too.',
        )
        if external
        else (
            f'With the wake phrase switched on in Dictation Settings, say "{phrase}" '
            "to start dictation without touching the keyboard. Anything you say after "
            "it in the same breath is written.",
            f'Say "{stop}" on its own, after a pause, to stop dictation. '
            '"Stop dictation" always works too. With the wake phrase on, stopping goes '
            "back to waiting for the wake phrase.",
            "You choose both phrases in Dictation Settings; each needs at least two words.",
        )
    )
    for sentence in voice:
        lines.append(("- " + sentence) if markdown else sentence)

    if language == "es":
        _spanish_sections(heading, row, table_head, lines, markdown)

    own = list(own_phrases)
    if own:
        heading("Your own words and phrases")
        table_head("Say", "Writes")
        for said, writes in own:
            row(said, writes.replace("\n", " (new line) ").replace("\t", " (tab) "))

    return "\n".join(lines).rstrip() + "\n"
