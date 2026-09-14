"""Hard line breaks in Markdown: writing them, spotting them, saying them (#1488).

A blind novelist reported this, and the report is worth reading twice. His
scene breaks are lines that follow one another with no gap -- "United States,"
then "Illinois," then "Chicago," -- which in Word is a **hard return**
(Shift+Enter) inside one paragraph, not four paragraphs. Converted to Markdown
and opened in QUILL they came back with blank lines between them, and nothing he
tried removed them. His words: *"The editor should not be showing me blank lines
where blank lines will later just magically disappear."* He spent two days on it.

Three things were wrong, and only the first is the one he could see:

1. **QUILL's Markdown renderer implemented no hard break at all.** Not two
   trailing spaces, not a backslash, not a literal ``<br>``. Every line of a
   paragraph was joined with a space, so there was no way to write one -- which
   is why his workaround had to be an HTML tag, and why he was right to expect
   it to break.
2. **The Word reader merged every paragraph into one**, joining them with a
   single newline, which Markdown reads as a soft wrap. So a whole chapter
   arrived as one paragraph.
3. **A Word hard return was indistinguishable from a soft wrap** once it got
   here, so even a fixed renderer could not have put it back.

What this module fixes is the vocabulary the other two need.

**Both spellings are read; one is written.** CommonMark has two: a line ending
in two or more spaces, and a line ending in a single backslash. QUILL accepts
either from anybody's file -- being strict about input would fail documents that
are correct. What it *writes* is a setting, because the two are not equally
usable: **two trailing spaces are invisible and inaudible.** A screen reader
says nothing for them, no editor shows them, and most tools strip trailing
whitespace on save, silently destroying the break. A backslash can be heard, can
be found with Find, and survives every editor that has ever existed. For an app
written for people who cannot see the screen, that is not a close call, so
backslash is the default -- with two-space available for anyone who needs to
match a tool that only understands the older spelling.
"""

from __future__ import annotations

__all__ = [
    "HARD_BREAK_LABELS",
    "HARD_BREAK_STYLES",
    "add_hard_break",
    "hard_break_suffix",
    "line_ends_with_hard_break",
    "normalise_hard_break_style",
    "strip_hard_break",
]

#: The two spellings QUILL can write, best first.
HARD_BREAK_STYLES: tuple[str, ...] = ("backslash", "spaces")

#: What a chooser shows for each. Written once so Preferences, the settings
#: documentation and anything that speaks the current value cannot disagree.
HARD_BREAK_LABELS: dict[str, str] = {
    "backslash": "Backslash at the end of the line (you can hear it)",
    "spaces": "Two spaces at the end of the line (invisible, older style)",
}

_SUFFIXES: dict[str, str] = {"backslash": "\\", "spaces": "  "}


def normalise_hard_break_style(value: object) -> str:
    """*value* as one of :data:`HARD_BREAK_STYLES`, defaulting to backslash."""
    text = str(value or "").strip().lower()
    return text if text in _SUFFIXES else HARD_BREAK_STYLES[0]


def hard_break_suffix(style: object) -> str:
    """What to put at the end of a line to break it in *style*."""
    return _SUFFIXES[normalise_hard_break_style(style)]


def line_ends_with_hard_break(line: str) -> bool:
    """Whether *line* ends in a hard break, in either spelling.

    Liberal on purpose: a document written elsewhere is not wrong for using the
    other spelling, and a reader that only understood QUILL's own choice would
    render somebody else's correct file incorrectly.

    A line of nothing but spaces is not a break -- it is an empty line, and
    treating it as one would put a stray ``<br>`` into every document that has
    trailing whitespace on a blank line, which is most of them.
    """
    if not line.strip():
        return False
    if line.endswith("  "):
        return True
    # One backslash, not two: "ends with \\\\" is an escaped backslash that the
    # author wanted printed, which is the opposite of a line break.
    stripped = line.rstrip()
    return stripped.endswith("\\") and not stripped.endswith("\\\\")


def strip_hard_break(line: str) -> str:
    """*line* without its hard-break marker, ready to render or re-wrap."""
    if not line.strip():
        return line
    if line.endswith("  "):
        return line.rstrip()
    stripped = line.rstrip()
    if stripped.endswith("\\") and not stripped.endswith("\\\\"):
        return stripped[:-1]
    return line


def add_hard_break(line: str, style: object) -> str:
    """*line* ending in a hard break, whatever it ended in before.

    Idempotent, and it converts: running it over a file written in the other
    spelling rewrites the breaks rather than doubling them, which is what makes
    changing the setting a safe thing to do to a document.
    """
    return strip_hard_break(line).rstrip() + hard_break_suffix(style)
