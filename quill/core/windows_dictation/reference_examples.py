"""Worked examples and limits for the dictation command reference (todo D.2).

Kept beside :mod:`~quill.core.windows_dictation.reference` rather than in it,
so the generated list stays the table and this stays the teaching. Every
example here is one the acceptance tests run, in QUILL and QUILL Lite both
(``tests/unit/apps/test_dictation_acceptance.py``): if an example stops being
true, a test fails before a reader finds out. Design record section 35.

Nothing here claims how accurately or how quickly any engine hears: that waits
on the benchmarks, and the guide says so.

wx-free.
"""

from __future__ import annotations

from typing import Any

__all__ = ["examples_section"]

#: ``(what you have, what you say, what you get)``, in the order a person meets them.
_EXAMPLES: tuple[tuple[str, str, str], ...] = (
    (
        "Meet me on Friday.",
        '"go to Friday", then "next"',
        "Meet me on next Friday. The cursor goes in front of the words, and what "
        "you say next is written there.",
    ),
    (
        "Meet me on Friday.",
        '"go after meet me", then "at noon"',
        "Meet me at noon on Friday.",
    ),
    (
        "The cat sat. The cat ran. The cat slept. (cursor at the end)",
        '"select the cat", then "select previous" twice, then "select again"',
        "The third The cat is selected first, because the nearest match before the "
        "cursor wins; then the second, then the first; then the second again. At the "
        'ends you hear "None before that." or "No more."',
    ),
    (
        "Dear Sam, the meeting moved to Tuesday at ten.",
        '"select the meeting through Tuesday"',
        "the meeting moved to Tuesday is selected. The next phrase you say replaces it.",
    ),
    (
        "I met Ann today.",
        '"correct Ann", then "Anne"',
        "I met Anne today.",
    ),
    (
        "Any document",
        '"copy all"',
        "The whole document is on the clipboard. Nothing is selected and the cursor "
        "does not move, so the next word you say cannot replace everything.",
    ),
    (
        "Kept. (typed by you)",
        '"first phrase period", "second phrase period", then "scratch that" twice',
        "Kept. Each scratch that takes out one dictated phrase, newest first. Your "
        "own typing is never taken; a phrase you have typed into since is left alone.",
    ),
    (
        "Copy Tray slots 1 to 12 filled",
        '"paste clip one" up to "paste clip twelve", or "paste slot 12"',
        "That slot's text goes in as one phrase, so scratch that takes all of it back. "
        'An empty slot is said ("Slot 4 is empty."); "paste clip thirteen" asks for '
        "a slot number.",
    ),
    (
        "A snippet named sign off",
        '"insert snippet sign off"',
        "The snippet's text. A name said as separate words finds a joined name too "
        '("sig off" finds sigoff). When two names match, you hear how many and '
        "nothing is typed.",
    ),
    (
        "An abbreviation named home address",
        '"insert abbreviation home address"',
        "What the abbreviation expands to.",
    ),
    (
        "Anywhere",
        '"caps on", "the old man and the sea", "caps off"',
        "The Old Man And The Sea. All caps on and all caps off work the same way "
        "for capitals throughout. Every mode ends when dictation stops.",
    ),
    (
        "meeting notes (just dictated)",
        '"capitalize that", then "all caps that", then "no caps that"',
        "Meeting Notes, then MEETING NOTES, then meeting notes.",
    ),
    (
        "Write to",
        '"start spelling", "jay dot sierra mike india tango hotel", "at sign echo '
        'x-ray dot charlie oscar", "stop spelling"',
        "Write to `j.smith@ex.co`. While spelling, each phrase joins the letters before "
        'it with no space, so you can pause as often as you like; say "space" for a '
        "space. A whole word such as smith is not a letter and is left out.",
    ),
    (
        "An empty line",
        '"heading one shopping", "bullet milk", "numbered item call the bank", '
        '"block quote be kind"',
        "`# Shopping`, then `- Milk`, `1. Call the bank` and `> Be kind`, each on its own line.",
    ),
    (
        "See",
        '"open bracket the guide close bracket", then "open paren page close paren"',
        "`See [the guide](page)`: a Markdown link, with no space between the bracket "
        "and the parenthesis.",
    ),
)

#: What is not done, or not known yet.
_LIMITS: tuple[str, ...] = (
    "How accurately and how quickly each engine hears you has not been measured "
    "yet. Those numbers wait on the dictation benchmarks; nothing in this guide is "
    "a claim about them.",
    "Commands that take words after them (select, go to, go after, correct, paste "
    "clip, insert snippet) work only at the start of a phrase.",
    "Words you ask for are looked for in the document's text. When they are not "
    'there, what you said is written as words and you hear "Not found, written as '
    'text." Scratch that takes it out.',
    "An asterisk and an underscore join the words either side of them (`two*three`, "
    '`snake_case`). For Markdown bold, use "bold that" with the Markdown profile.',
    "In another program (QUILL Transcribe, and Quill Inkwell's Dictate Anywhere) "
    "dictation can only type: dictating, punctuation, scratch that, the modes, "
    "spelling, paste clip, insert snippet and insert abbreviation work. Anything "
    "that has to read or select that program's text is refused with the same "
    "sentence: select, go to, go after, select again, select sentence, line or "
    "paragraph, copy all, copy that, show clips, show snippets, spell that, and "
    "read last sentence or read selection.",
    "In another program, a snippet or abbreviation that puts the cursor in the "
    "middle leaves it at the end instead, because moving it back would mean "
    "reading that program's text.",
)


def examples_section(heading: Any, lines: list[str], md: bool) -> None:
    """The worked examples -- a table in the guide, three lines each in the
    in-app list -- and then the limits."""
    heading("Worked examples")
    lines.append(
        "Each of these works the same in QUILL and QUILL Lite. What you get is what "
        "the automated acceptance tests check."
    )
    if md:
        lines.extend(("", "| You have | You say | You get |", "|---|---|---|"))
    for have, say, get in _EXAMPLES:
        if md:
            lines.append(f"| {have} | {say} | {get} |")
        else:  # the in-app list is plain text: no code marks
            get = get.replace("`", "")
            lines.extend((f"You have: {have}", f"You say: {say}", f"You get: {get}"))
    heading("Limits")
    for sentence in _LIMITS:
        lines.append(("- " + sentence) if md else sentence.replace("`", ""))
