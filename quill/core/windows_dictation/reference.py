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

from quill.core.windows_dictation.vocabulary import (
    COMMAND_HELP,
    DASH_STYLES,
    MARKS,
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


def commands_reference(
    *,
    markdown: bool = False,
    dash: str = "em",
    wake_phrase: str = "",
    stop_phrase: str = "",
    own_phrases: Iterable[tuple[str, str]] = (),
) -> str:
    """Every phrase dictation acts on, grouped, with what each one does.

    *markdown* gives headings and tables for the published guide; otherwise the
    text is plain, one entry per line, for a read-only window a screen reader
    moves through with the arrow keys. *wake_phrase*, *stop_phrase* and
    *own_phrases* (the user's replacements) personalise the window; the
    published copy leaves them out.
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
                shows = f"`{shows}`"
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

    heading("Spelling")
    for sentence in (
        'Say "start spelling", then letters. Everything you say is written as '
        'letters until you say "stop spelling".',
        'Say "capital" before a letter for a capital, and "space" for a space.',
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

    own = list(own_phrases)
    if own:
        heading("Your own words and phrases")
        table_head("Say", "Writes")
        for said, writes in own:
            row(said, writes.replace("\n", " (new line) ").replace("\t", " (tab) "))

    return "\n".join(lines).rstrip() + "\n"
