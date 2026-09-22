r"""Turning the editor's heading ladder into structure other programs can read.

A heading in the editor is a **point size and bold**, because that is the only
way the Text Object Model can be told to make one: there is no "apply Heading 2"
on a RichEdit control. Saving asks that control for its RTF and writes what
comes back, which is faithful and structurally empty -- no stylesheet, no
``\\sN``, no ``\\outlinelevelN``.

The editor reopens such a file and finds every heading again, because it
recognises its own ladder. **Word opens it and shows bold paragraphs whose style
box says Normal**, with an empty navigation pane and nothing in a generated
table of contents, and so does every other tool that reads structure -- a
converter, an accessibility checker, another word processor. A user reported
exactly that: "I added three headings, saved it, opened it in Word and the text
does not have headings."

So the ladder is translated on the way out, here, once, for both editors. The
Markdown writer (:mod:`quill.io.rtf`) has emitted the stylesheet since headings
first gained sizes, which is why this survived so long: one of the two writers
was already right.

Pure and wx-free, and it only ever **adds**. The text, the sizes, the fonts, the
colours and any paragraph formatting the user applied come through untouched, so
a document that passes through here is the same document with more structure in
it.
"""

from __future__ import annotations

from quill.core.heading_ladder import heading_level_for_font
from quill.io.rtf_styles import heading_stylesheet

__all__ = ["promote_heading_styles", "promote_heading_styles_in_file"]


#: Header groups whose contents are tables or metadata rather than document
#: text. A heading scan must not read a font name as a paragraph.
_SKIPPED_DESTINATIONS = (
    "fonttbl",
    "colortbl",
    "stylesheet",
    "info",
    "listtable",
    "listoverridetable",
    "generator",
    "pntext",
    "pn",
)


def _control_word(rtf: str, index: int) -> tuple[str, int | None, int]:
    r"""The control word at ``rtf[index] == '\'``: ``(name, number, next index)``.

    ``next index`` is past the word *and* past its delimiting space, which RTF
    says belongs to the control word and not to the text.
    """
    cursor = index + 1
    if cursor >= len(rtf):
        return "", None, cursor
    if not rtf[cursor].isalpha():
        # A control symbol (\*, \', \{ ...): one character, no number.
        return rtf[cursor], None, cursor + 1
    start = cursor
    while cursor < len(rtf) and rtf[cursor].isalpha():
        cursor += 1
    name = rtf[start:cursor]
    digits_start = cursor
    if cursor < len(rtf) and rtf[cursor] == "-":
        cursor += 1
    while cursor < len(rtf) and rtf[cursor].isdigit():
        cursor += 1
    number = int(rtf[digits_start:cursor]) if cursor > digits_start else None
    if cursor < len(rtf) and rtf[cursor] == " ":
        cursor += 1
    return name, number, cursor


def _skip_group(rtf: str, index: int) -> int:
    r"""The index just past the group whose ``{`` is at *index*."""
    depth = 0
    cursor = index
    while cursor < len(rtf):
        char = rtf[cursor]
        if char == "\\":
            cursor += 2  # a control symbol can be an escaped brace
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    return cursor


def promote_heading_styles(rtf: str) -> str:
    r"""Give the headings in *rtf* the style references Word reads.

    The editor applies a heading through the Text Object Model as **point size
    plus bold** -- there is no other way to say "heading" to a RichEdit control
    -- and saving asks that control for its RTF. What comes back is exactly what
    it knows: ``\b\fs40 This is a test.\par``, with no stylesheet, no ``\sN``
    and no ``\outlinelevel``. The editor reopens that file and finds every
    heading again, because it recognises its own ladder; **Word opens it and
    shows three bold paragraphs called Normal**, with an empty navigation pane
    and nothing in a generated table of contents. A user reported precisely
    that: "I added three headings, saved it, opened it in Word and the text does
    not have headings."

    So the ladder is translated on the way out. Each paragraph whose first run
    is bold at one of the six heading sizes gains ``\sN``, ``\outlinelevelN``
    and ``\keepn``, and the document gains the stylesheet those references
    point at -- the same :func:`heading_stylesheet` the Markdown writer has
    emitted since headings got sizes, which is why this went unnoticed for so
    long: the *other* writer was already right.

    Only additions are made. The text, the sizes, the fonts, the colours and any
    paragraph formatting the user applied are left exactly as the control wrote
    them, so a file that round-trips through here is the same document with more
    structure in it. A document that already carries a stylesheet is left with
    the one it has.
    """
    if "\\rtf" not in rtf[:16]:
        return rtf
    inserts: list[tuple[int, str]] = []
    # Character state, scoped to groups the way RTF scopes it: '{' saves, '}'
    # restores. \pard resets the *paragraph*, never the font.
    size_half_points: int | None = None
    bold = False
    stack: list[tuple[int | None, bool]] = []
    paragraph_open = False  # whether this paragraph's first text is still ahead
    cursor = 0
    length = len(rtf)
    while cursor < length:
        char = rtf[cursor]
        if char == "{":
            name, _number, after = (
                _control_word(rtf, cursor + 1)
                if (cursor + 1 < length and rtf[cursor + 1] == "\\")
                else ("", None, cursor + 1)
            )
            if name == "*" or name in _SKIPPED_DESTINATIONS:
                cursor = _skip_group(rtf, cursor)
                continue
            stack.append((size_half_points, bold))
            cursor += 1
            continue
        if char == "}":
            if stack:
                size_half_points, bold = stack.pop()
            cursor += 1
            continue
        if char == "\\":
            name, number, after = _control_word(rtf, cursor)
            if name == "fs" and number is not None:
                size_half_points = number
            elif name == "b":
                bold = number != 0
            elif name == "plain":
                size_half_points, bold = None, False
            elif name == "par":
                paragraph_open = False
            cursor = after
            continue
        if char in "\r\n":
            cursor += 1
            continue
        # Text. The first of a paragraph decides what that paragraph is.
        if not paragraph_open:
            paragraph_open = True
            level = (
                heading_level_for_font(size_half_points / 2, bold=bold)
                if size_half_points is not None
                else None
            )
            if level is not None:
                inserts.append((cursor, f"\\s{level}\\outlinelevel{level - 1}\\keepn "))
        cursor += 1
    if not inserts:
        return rtf
    out = rtf
    for at, text in reversed(inserts):
        out = out[:at] + text + out[at:]
    return _with_stylesheet(out)


def _with_stylesheet(rtf: str) -> str:
    r"""*rtf* with :func:`heading_stylesheet` in its header, if it has none.

    After the colour table when there is one and the font table otherwise, which
    is where the RTF specification puts it and where Word looks for it.
    """
    if "\\stylesheet" in rtf:
        return rtf
    for table in ("{\\colortbl", "{\\fonttbl"):
        start = rtf.find(table)
        if start != -1:
            end = _skip_group(rtf, start)
            return rtf[:end] + heading_stylesheet() + rtf[end:]
    # No tables at all: straight after the \rtf1 header controls.
    first_group = rtf.find("{", 1)
    at = first_group if first_group != -1 else len(rtf) - 1
    return rtf[:at] + heading_stylesheet() + rtf[at:]


def promote_heading_styles_in_file(path: str) -> None:
    """Add the heading stylesheet to the RTF just written at *path*.

    The control has no way to say "this paragraph is Heading 2" -- a heading in
    RichEdit is a point size and bold, which is what this surface applies and
    what ``ITextDocument::Save`` writes out. Word reads that as three bold
    paragraphs called Normal, so a file saved here had headings the editor could
    find and Word could not. :func:`~quill.io.rtf_styles.promote_heading_styles`
    translates the ladder into the ``\\sN`` / ``\\outlinelevelN`` references Word
    looks for, adding nothing else.

    Read and written as latin-1, which maps every byte to a character and back:
    RTF escapes its own non-ASCII, and a codec that guessed could not.

    Never raises. The document on disk is already correct and complete before
    this runs; losing the styles is worth reporting nowhere and losing the save
    is worth reporting everywhere.
    """
    try:
        with open(path, encoding="latin-1") as handle:
            original = handle.read()
        promoted = promote_heading_styles(original)
        if promoted == original:
            return
        with open(path, "w", encoding="latin-1") as handle:
            handle.write(promoted)
    except (OSError, ValueError, UnicodeError):
        return
