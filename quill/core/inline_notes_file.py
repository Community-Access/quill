"""Notes kept *inside* the file, as HTML comments (wx-free).

QUILL's inline notes live in a private sidecar (``inline_notes.json``) by
default, which works in every format and never touches the document. The cost
is that nobody else can read them: a colleague, or the AI assistant that wrote
the plan you are reviewing, never sees a sidecar. PlanCake (Andre of Oire
Software) showed the other way round -- the note lives in the file, right after
the text it is about -- and this module is QUILL's version of that idea for the
two formats where it can be done without breaking the file:

    Back up the uploads folder.
    <!-- quill-note: And the database dump. -->

An HTML comment is valid Markdown and valid HTML, so the file stays correct,
renderers (GitHub, Pandoc, every browser) hide it, and a plain-text reader or
an AI assistant still sees it. The form is fixed and QUILL's own -- only
``quill-note:`` comments are read, never another tool's markers.

**Escaping.** A comment may not contain ``--``, so note text is written with
``&`` as ``&amp;`` and every second hyphen of a pair as ``&#45;``; reading
reverses both in one pass, so any text round-trips, ``-->`` included.

**Anchoring.** A note is about the block just before it: the paragraph, list
item, heading or line it follows. It is written after the *end* of that block
(after the closing fence for a code block), indented to a list item's text so
the list stays one list, and after any notes already there so their order
holds. In HTML, where blank lines mean nothing, the block is the line.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

__all__ = [
    "IN_FILE_KINDS",
    "NOTE_LINE_MARK",
    "FileNote",
    "escape_note_text",
    "format_note_comment",
    "insert_file_note",
    "mark_notes_for_render",
    "note_aside_html",
    "parse_file_notes",
    "remove_all_file_notes",
    "removal_span",
    "remove_file_note",
    "replace_file_note",
    "unescape_note_text",
]

#: Document kinds a note may be written into. Anything else keeps the sidecar.
IN_FILE_KINDS = frozenset({"markdown", "html"})

_PREFIX = "<!-- quill-note: "
_SUFFIX = " -->"
_COMMENT_RE = re.compile(r"<!--[ \t]*quill-note:[ \t]?(.*?)[ \t]*-->", re.DOTALL)
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_ITEM_RE = re.compile(r"^(\s*)(?:[-*+]|\d{1,9}[.)])[ \t]+")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}(?:\s|$)")
_UNESCAPE_RE = re.compile(r"&(amp|#45);")

#: Starts a line the Markdown renderer emits verbatim: a note's ``aside``,
#: put there by :func:`mark_notes_for_render`. A control character no typed
#: document starts a line with, the same trick the renderer uses for breaks.
NOTE_LINE_MARK = chr(2)


@dataclass(frozen=True, slots=True)
class FileNote:
    """One ``quill-note`` comment and the text it is about.

    ``start``/``end`` cover the comment's whole line(s), newline included, so
    deleting that span removes the note and leaves the document as it was.
    ``anchor_start``/``anchor_end`` are the block it follows; ``anchor`` is
    that block's text, empty when there is none (an orphaned note).
    """

    text: str
    start: int
    end: int
    anchor_start: int
    anchor_end: int
    anchor: str

    @property
    def note_id(self) -> str:
        return f"file:{self.start}"


def escape_note_text(text: str) -> str:
    """*text* made safe inside an HTML comment (no ``--`` anywhere)."""
    escaped = text.replace("&", "&amp;")
    while "--" in escaped:
        escaped = escaped.replace("--", "-&#45;")
    if escaped.endswith("-"):
        escaped = escaped[:-1] + "&#45;"
    return escaped


def unescape_note_text(text: str) -> str:
    """Reverse :func:`escape_note_text`, in one pass so nothing is decoded twice."""
    return _UNESCAPE_RE.sub(lambda m: "&" if m.group(1) == "amp" else "-", text)


def format_note_comment(text: str, indent: str = "") -> str:
    """The comment for *text*, continuation lines indented like the first."""
    body = escape_note_text(text.strip())
    body = body.replace("\r\n", "\n").replace("\n", "\n" + indent)
    return f"{indent}{_PREFIX}{body}{_SUFFIX}"


def _lines(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    offset = 0
    for line in text.split("\n"):
        out.append((offset, line))
        offset += len(line) + 1
    return out


def _fenced(lines: list[tuple[int, str]]) -> list[int]:
    """For each line, the number of the fenced code block it is in, or -1."""
    inside = [-1] * len(lines)
    fence = ""
    block = -1
    for number, (_offset, line) in enumerate(lines):
        match = _FENCE_RE.match(line)
        if fence:
            inside[number] = block
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = ""
        elif match:
            block += 1
            inside[number] = block
            fence = match.group(1)
    return inside


def _is_note_line(line: str) -> bool:
    return line.lstrip().startswith("<!--") and "quill-note:" in line


def parse_file_notes(text: str, kind: str = "markdown") -> list[FileNote]:
    """Every ``quill-note`` comment in *text*, in document order.

    Only a comment that starts its own line counts, and never one inside a
    fenced code block, so a document that shows the form as an example -- in a
    code span or a fence -- is left alone.
    """
    lines = _lines(text)
    fenced = _fenced(lines) if kind != "html" else [-1] * len(lines)
    notes: list[FileNote] = []
    number = 0
    while number < len(lines):
        offset, line = lines[number]
        stripped = line.lstrip()
        if fenced[number] >= 0 or not stripped.startswith("<!--"):
            number += 1
            continue
        start = offset + (len(line) - len(stripped))
        match = _COMMENT_RE.match(text, start)
        if match is None:
            number += 1
            continue
        last = number
        while last + 1 < len(lines) and lines[last + 1][0] <= match.end() - 1:
            last += 1
        end_line_offset, end_line = lines[last]
        span_end = end_line_offset + len(end_line)
        if text[match.end() : span_end].strip():
            number += 1  # something follows the comment on its line: not ours
            continue
        if span_end < len(text):
            span_end += 1  # the newline
        indent = line[: len(line) - len(stripped)]
        body = "\n".join(
            part[len(indent) :] if part.startswith(indent) else part.lstrip()
            for part in match.group(1).split("\n")
        )
        a_start, a_end = _anchor_before(lines, number, fenced, kind)
        notes.append(
            FileNote(
                text=unescape_note_text(body).strip(),
                start=offset,
                end=span_end,
                anchor_start=a_start,
                anchor_end=a_end,
                anchor=text[a_start:a_end],
            )
        )
        number = last + 1
    return notes


def _anchor_before(
    lines: list[tuple[int, str]], number: int, fenced: list[int], kind: str
) -> tuple[int, int]:
    """The block a note on line *number* is about: the one just above it."""
    probe = number - 1
    while probe >= 0 and (not lines[probe][1].strip() or _is_note_line(lines[probe][1])):
        probe -= 1
    if probe < 0:
        start = lines[number][0]
        return (start, start)
    first = _block_start(lines, probe, fenced, kind)
    return (lines[first][0], lines[probe][0] + len(lines[probe][1]))


def _block_start(lines: list[tuple[int, str]], last: int, fenced: list[int], kind: str) -> int:
    """The first line of the block whose last line is *last*."""
    first = last
    if fenced[last] >= 0:
        while first > 0 and fenced[first - 1] == fenced[last]:
            first -= 1
        return first
    if kind == "html":
        return first
    while first > 0:
        line = lines[first][1]
        if _ITEM_RE.match(line) or _HEADING_RE.match(line):
            break
        above = lines[first - 1][1]
        if (
            not above.strip()
            or _is_note_line(above)
            or fenced[first - 1] >= 0
            or _HEADING_RE.match(above)
        ):
            break
        first -= 1
    return first


def insert_file_note(
    text: str, position: int, note: str, kind: str = "markdown"
) -> tuple[int, str]:
    """Where to write a note about the text at *position*, and what to write.

    Returns ``(offset, insertion)``: insert *insertion* at *offset* and the
    note sits on its own line after the block *position* is in. Apply it as
    an ordinary edit so undo takes it back.
    """
    lines = _lines(text)
    fenced = _fenced(lines) if kind != "html" else [-1] * len(lines)
    number = 0
    for index, (offset, line) in enumerate(lines):
        if offset <= position <= offset + len(line):
            number = index
            break
    # On a blank line (or a note), the note is about the block above.
    while number > 0 and (not lines[number][1].strip() or _is_note_line(lines[number][1])):
        number -= 1
    if fenced[number] >= 0:
        while number + 1 < len(lines) and fenced[number + 1] == fenced[number]:
            number += 1
    elif kind != "html" and not _HEADING_RE.match(lines[number][1]):
        while number + 1 < len(lines):
            nxt = lines[number + 1][1]
            if (
                not nxt.strip()
                or _ITEM_RE.match(nxt)
                or _HEADING_RE.match(nxt)
                or _FENCE_RE.match(nxt)
                or _is_note_line(nxt)
            ):
                break
            number += 1
    first = _block_start(lines, number, fenced, kind)
    indent = "" if fenced[number] >= 0 else _indent_for(lines[first][1])
    # After any notes already on this block, so their order holds.
    while number + 1 < len(lines) and _is_note_line(lines[number + 1][1]):
        number += 1
    offset, line = lines[number]
    return (offset + len(line), "\n" + format_note_comment(note, indent))


def _indent_for(line: str) -> str:
    item = _ITEM_RE.match(line)
    if item:
        return " " * len(item.group(0))
    lead = line[: len(line) - len(line.lstrip())]
    return lead if len(lead.expandtabs(4)) < 4 else ""


def removal_span(text: str, note: FileNote) -> tuple[int, int]:
    """The ``[start, end)`` to delete so *note* goes and its line with it."""
    start, end = note.start, note.end
    if end == len(text) and start > 0 and text[start - 1] == "\n":
        start -= 1  # the last line: take the newline before it instead
    return (start, end)


def remove_file_note(text: str, note: FileNote) -> str:
    """*text* without *note*'s comment line."""
    start, end = removal_span(text, note)
    return text[:start] + text[end:]


def replace_file_note(text: str, note: FileNote, new_text: str) -> tuple[int, int, str]:
    """The edit that rewrites *note* to say *new_text*: ``(start, end, replacement)``."""
    line_end = text.find("\n", note.start)
    first_line = text[note.start : len(text) if line_end == -1 else line_end]
    indent = first_line[: len(first_line) - len(first_line.lstrip())]
    end = (
        note.end - 1
        if note.end > note.start and text[note.end - 1 : note.end] == "\n"
        else note.end
    )
    return (note.start, end, format_note_comment(new_text, indent))


def remove_all_file_notes(text: str, kind: str = "markdown") -> tuple[str, int]:
    """*text* with every ``quill-note`` comment removed, and how many went."""
    notes = parse_file_notes(text, kind)
    for note in reversed(notes):
        text = remove_file_note(text, note)
    return text, len(notes)


def note_aside_html(text: str) -> str:
    """A note as a page shows it: a marked ``aside`` named "Note".

    The word "Note:" is in the text as well as the accessible name, so the
    marking does not depend on colour or on a screen reader announcing the
    landmark (PlanCake names its note regions "User note" for the same reason).
    """
    body = "<br>".join(html.escape(line) for line in text.strip().split("\n"))
    return (
        f'<aside class="quill-note" aria-label="Note"><p><strong>Note:</strong> {body}</p></aside>'
    )


def mark_notes_for_render(text: str, kind: str, include: bool) -> str:
    """*text* ready to render: notes left out, or turned into ``aside`` lines.

    Left out is the default everywhere a page leaves QUILL -- export, copy,
    publish -- because a forgotten note must never appear in a published page.
    The preview includes them: it is the writer's own view of their document.
    """
    notes = parse_file_notes(text, kind)
    for note in reversed(notes):
        if include:
            line = note_aside_html(note.text)
            if kind == "markdown":
                line = NOTE_LINE_MARK + line
            tail = "\n" if text[note.end - 1 : note.end] == "\n" else ""
            text = text[: note.start] + line + tail + text[note.end :]
        else:
            text = remove_file_note(text, note)
    return text
