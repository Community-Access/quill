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


def commands_reference(
    *,
    markdown: bool = False,
    dash: str = "em",
    wake_phrase: str = "",
    stop_phrase: str = "",
    own_phrases: Iterable[tuple[str, str]] = (),
    language: str = "en",
) -> str:
    """Every phrase dictation acts on, grouped, with what each one does.

    *markdown* gives headings and tables for the published guide; otherwise the
    text is plain, one entry per line, for a read-only window a screen reader
    moves through with the arrow keys. *wake_phrase*, *stop_phrase* and
    *own_phrases* (the user's replacements) personalise the window; the
    published copy leaves them out. *language* ``"es"`` adds the Spanish
    punctuation words (and, in a development build that has them switched on,
    the drafted Spanish commands).
    """
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
        "Some commands take words after them: select the cat, paste clip three, "
        "insert snippet sign off. They work only at the start of a phrase.",
        'The Markdown line marks -- "bullet", "numbered item", "block quote" and '
        '"heading one" to "heading six" -- count only at the start of a phrase, so '
        '"the heading two lines down" stays words.',
    ):
        lines.append(("- " + sentence) if markdown else sentence)

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
        said = " or ".join(f'"{phrase}"' for phrase in entry.phrases)
        groups.setdefault(entry.group, []).append((said, entry.description))
    for group, entries in groups.items():
        heading("Commands: " + group.lower())
        table_head("Say, on its own", "What happens")
        for said, does in entries:
            row(said, does)

    prefix_groups: dict[str, list[tuple[str, str]]] = {}
    for prefix in PREFIX_HELP:
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
        'Say "spell" and the letters to spell one word without starting spelling '
        'mode, and "spell that" to spell the last phrase over again.',
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
    for sentence in (
        f'With the wake phrase switched on in Dictation Settings, say "{phrase}" '
        "to start dictation without touching the keyboard. Anything you say after "
        "it in the same breath is written.",
        f'Say "{stop}" on its own, after a pause, to stop dictation. '
        '"Stop dictation" always works too. With the wake phrase on, stopping goes '
        "back to waiting for the wake phrase.",
        "You choose both phrases in Dictation Settings; each needs at least two words.",
    ):
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
