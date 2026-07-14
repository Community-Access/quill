"""Cursor-aware line operations for the first-party editor commands.

Migration note: ``duplicate_line``, ``delete_line``, ``move_line_up``,
``move_line_down``, ``join_paragraph``, and ``join_with_next_line`` are now also
vendored into ``quill/quillins_bundled/line-tools/line_ops.py`` for the
sandboxed Quillin counterparts (``ext.lines.*``). The first-party
``power.lines.*`` commands still use this module. When those commands are retired
(migration plan Wave N), the overlapping functions here can be removed.
"""

from __future__ import annotations


def duplicate_line(text: str, cursor: int) -> tuple[str, int]:
    lines = _lines(text)
    index = _line_index(text, cursor)
    lines.insert(index + 1, lines[index])
    updated = "\n".join(lines)
    return updated, _line_start(updated, index + 1)


def delete_line(text: str, cursor: int) -> tuple[str, int]:
    lines = _lines(text)
    index = _line_index(text, cursor)
    if len(lines) == 1:
        return "", 0
    del lines[index]
    if index >= len(lines):
        index = len(lines) - 1
    updated = "\n".join(lines)
    return updated, _line_start(updated, index)


def move_line_up(text: str, cursor: int) -> tuple[str, int]:
    lines = _lines(text)
    index = _line_index(text, cursor)
    if index == 0:
        return text, cursor
    lines[index - 1], lines[index] = lines[index], lines[index - 1]
    updated = "\n".join(lines)
    return updated, _line_start(updated, index - 1)


def move_line_down(text: str, cursor: int) -> tuple[str, int]:
    lines = _lines(text)
    index = _line_index(text, cursor)
    if index >= len(lines) - 1:
        return text, cursor
    lines[index], lines[index + 1] = lines[index + 1], lines[index]
    updated = "\n".join(lines)
    return updated, _line_start(updated, index + 1)


def join_with_next_line(text: str, cursor: int) -> tuple[str, int]:
    lines = _lines(text)
    index = _line_index(text, cursor)
    if index >= len(lines) - 1:
        return text, cursor
    lines[index] = f"{lines[index].rstrip()} {lines[index + 1].lstrip()}".rstrip()
    del lines[index + 1]
    updated = "\n".join(lines)
    return updated, _line_start(updated, index)


def move_lines_up(text: str, start: int, end: int) -> tuple[str, int, int]:
    """Move the whole block of lines spanned by ``[start, end]`` up one line.

    Selection-aware companion to :func:`move_line_up` (issue #133): a multi-line
    selection moves as one block instead of only its first line. With no
    selection (``start == end``) this moves just the caret's line. Returns the
    updated text and the new selection bounds covering the moved block.
    """
    lines = _lines(text)
    first, last = _selected_line_bounds(text, start, end)
    if first == 0:
        return text, start, end
    block = lines[first : last + 1]
    del lines[first : last + 1]
    lines[first - 1 : first - 1] = block
    updated = "\n".join(lines)
    new_start = _line_start(updated, first - 1)
    new_end = _line_end_offset(updated, last - 1)
    return updated, new_start, new_end


def move_lines_down(text: str, start: int, end: int) -> tuple[str, int, int]:
    """Move the whole block of lines spanned by ``[start, end]`` down one line.

    Selection-aware companion to :func:`move_line_down` (issue #133).
    """
    lines = _lines(text)
    first, last = _selected_line_bounds(text, start, end)
    if last >= len(lines) - 1:
        return text, start, end
    block = lines[first : last + 1]
    del lines[first : last + 1]
    lines[first + 1 : first + 1] = block
    updated = "\n".join(lines)
    new_start = _line_start(updated, first + 1)
    new_end = _line_end_offset(updated, last + 1)
    return updated, new_start, new_end


def selected_line_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Public: first and last line indices spanned by a selection (issue #133).

    Used by the UI to report how many lines a move affected ("Moved 3 lines up")
    and to detect a document-edge no-op, so the announcement matches what the
    block move in :func:`move_lines_up` / :func:`move_lines_down` actually did.
    """
    return _selected_line_bounds(text, start, end)


def join_selected_lines(text: str, start: int, end: int) -> tuple[str, int, int]:
    """Join every line in the selection, preserving blank-line paragraph breaks.

    Issue #135: "Join lines" previously merged only the first two lines. With a
    selection this now collapses each run of non-blank lines into one line
    (single spaces between words) while keeping blank lines as paragraph
    separators, so selecting a whole document reflows it paragraph by paragraph.
    With no selection it joins the caret's paragraph (see :func:`join_paragraph`).
    """
    if start == end:
        updated, cursor = join_paragraph(text, start)
        return updated, cursor, cursor
    lines = _lines(text)
    first, last = _selected_line_bounds(text, start, end)
    joined_segment = _join_paragraph_lines(lines[first : last + 1])
    new_lines = lines[:first] + joined_segment + lines[last + 1 :]
    updated = "\n".join(new_lines)
    new_start = _line_start(updated, first)
    new_end = _line_end_offset(updated, first + len(joined_segment) - 1)
    return updated, new_start, new_end


def join_paragraph(text: str, cursor: int) -> tuple[str, int]:
    """Join the caret's paragraph (consecutive non-blank lines) into one line.

    A paragraph runs from the caret's line until the next blank line, matching
    the "word wrap each paragraph until you see the double enter" behaviour
    requested in issue #135. A no-op on a blank line or a single-line paragraph.
    """
    lines = _lines(text)
    index = _line_index(text, cursor)
    if lines[index].strip() == "":
        return text, cursor
    first = index
    last = index
    while last < len(lines) - 1 and lines[last + 1].strip() != "":
        last += 1
    if first == last:
        return text, cursor
    joined = " ".join(part.strip() for part in lines[first : last + 1])
    new_lines = lines[:first] + [joined] + lines[last + 1 :]
    updated = "\n".join(new_lines)
    return updated, _line_start(updated, first)


def _join_paragraph_lines(segment: list[str]) -> list[str]:
    """Collapse runs of non-blank lines into single lines, keeping blank lines."""
    result: list[str] = []
    buffer: list[str] = []
    for line in segment:
        if line.strip() == "":
            if buffer:
                result.append(" ".join(part.strip() for part in buffer))
                buffer = []
            result.append(line)
        else:
            buffer.append(line)
    if buffer:
        result.append(" ".join(part.strip() for part in buffer))
    return result


def number_lines(text: str, start: int = 1, separator: str = ". ") -> str:
    """Prefix each non-blank line with a consecutive number (EDS-4).

    Numbering starts at ``start`` and increments only for non-blank lines; blank
    lines are passed through unchanged.
    """
    number = start
    out: list[str] = []
    for line in text.split("\n"):
        if line.strip() == "":
            out.append(line)
        else:
            out.append(f"{number}{separator}{line}")
            number += 1
    return "\n".join(out)


_ROMAN_VALUES: tuple[tuple[int, str], ...] = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def to_roman_numeral(number: int) -> str:
    """Render a positive integer as an uppercase Roman numeral."""
    if number <= 0:
        raise ValueError("Roman numerals only support positive integers")
    remaining = number
    parts: list[str] = []
    for value, symbol in _ROMAN_VALUES:
        count, remaining = divmod(remaining, value)
        if count:
            parts.append(symbol * count)
    return "".join(parts)


def number_lines_advanced(
    text: str,
    *,
    start: int = 1,
    increment: int = 1,
    style: str = "digits",
    pad_width: int = 0,
    suffix: str = ". ",
    align: str = "left",
) -> str:
    """Prefix non-blank lines with a running number (Text Monkey-style auto-number).

    ``style`` is ``"digits"`` or ``"roman"``. ``pad_width`` zero-pads digit
    numbering to a fixed width (ignored for Roman numerals). ``align`` controls
    whether the rendered number is left- or right-justified within the widest
    rendered number's column, independent of ``pad_width``.
    """
    lines = text.split("\n")
    numbers: list[int | None] = []
    current = start
    for line in lines:
        if line.strip() == "":
            numbers.append(None)
        else:
            numbers.append(current)
            current += increment

    def render(value: int) -> str:
        if style == "roman":
            return to_roman_numeral(value)
        rendered = str(value)
        if pad_width:
            rendered = rendered.zfill(pad_width)
        return rendered

    rendered_numbers = [render(value) if value is not None else None for value in numbers]
    width = max((len(value) for value in rendered_numbers if value is not None), default=0)

    out: list[str] = []
    for line, rendered in zip(lines, rendered_numbers, strict=True):
        if rendered is None:
            out.append(line)
            continue
        label = rendered.rjust(width) if align == "right" else rendered.ljust(width)
        out.append(f"{label}{suffix}{line}")
    return "\n".join(out)


def delete_to_line_start(text: str, cursor: int) -> tuple[str, int]:
    """Delete from the cursor back to the start of the line (EDS-9)."""
    start = text.rfind("\n", 0, cursor) + 1
    return text[:start] + text[cursor:], start


def delete_to_line_end(text: str, cursor: int) -> tuple[str, int]:
    """Delete from the cursor to the end of the line, keeping the newline (EDS-9)."""
    newline = text.find("\n", cursor)
    end = len(text) if newline == -1 else newline
    return text[:cursor] + text[end:], cursor


def delete_to_document_start(text: str, cursor: int) -> tuple[str, int]:
    """Delete from the cursor to the top of the document (EDS-9)."""
    return text[cursor:], 0


def delete_to_document_end(text: str, cursor: int) -> tuple[str, int]:
    """Delete from the cursor to the bottom of the document (EDS-9)."""
    return text[:cursor], cursor


def delete_paragraph(text: str, cursor: int) -> tuple[str, int]:
    """Delete the current paragraph and any blank lines after it (EDS-10)."""
    lines = _lines(text)
    index = _line_index(text, cursor)
    if lines[index].strip() == "":
        start = end = index
    else:
        start = index
        while start > 0 and lines[start - 1].strip() != "":
            start -= 1
        end = index
        while end < len(lines) - 1 and lines[end + 1].strip() != "":
            end += 1
    while end < len(lines) - 1 and lines[end + 1].strip() == "":
        end += 1
    del lines[start : end + 1]
    if not lines:
        lines = [""]
    new_index = min(start, len(lines) - 1)
    updated = "\n".join(lines)
    return updated, _line_start(updated, new_index)


def first_non_blank_position(text: str, cursor: int) -> int:
    """Return the offset of the first non-whitespace character on the line (EDS-16)."""
    line_start = text.rfind("\n", 0, cursor) + 1
    newline = text.find("\n", cursor)
    line_end = len(text) if newline == -1 else newline
    line = text[line_start:line_end]
    leading = len(line) - len(line.lstrip())
    if leading == len(line):
        return line_end
    return line_start + leading


def last_non_blank_position(text: str, cursor: int) -> int:
    """Return the offset just past the last non-whitespace character (EDS-16)."""
    line_start = text.rfind("\n", 0, cursor) + 1
    newline = text.find("\n", cursor)
    line_end = len(text) if newline == -1 else newline
    line = text[line_start:line_end]
    return line_start + len(line.rstrip())


def _lines(text: str) -> list[str]:
    if text == "":
        return [""]
    return text.split("\n")


def _line_index(text: str, cursor: int) -> int:
    if cursor <= 0:
        return 0
    return text[:cursor].count("\n")


def _line_start(text: str, index: int) -> int:
    if index <= 0:
        return 0
    position = 0
    current = 0
    while current < index and position < len(text):
        if text[position] == "\n":
            current += 1
        position += 1
    return position


def _line_end_offset(text: str, index: int) -> int:
    """Return the offset of the end of the line at ``index`` (before its newline)."""
    start = _line_start(text, index)
    newline = text.find("\n", start)
    return len(text) if newline == -1 else newline


def _selected_line_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Return the first and last line indices spanned by the selection.

    A selection that ends exactly at a line start does not pull in the following
    line, so the bounds cover only the lines the user visibly selected.
    """
    if end < start:
        start, end = end, start
    first = _line_index(text, start)
    last_pos = end - 1 if end > start else end
    last = _line_index(text, max(start, last_pos))
    return first, last


def chunk_span(text: str, cursor: int) -> tuple[int, int]:
    """Return the (start, end) character span of the word-chunk at cursor.

    A chunk is a maximal run of one character class:
    - word characters (alphanumeric + underscore)
    - whitespace characters
    - everything else (punctuation / symbols)

    When the cursor is at the end of the text the last character's chunk is
    returned. Returns (cursor, cursor) for empty text.
    """
    if not text:
        return cursor, cursor
    pos = max(0, min(cursor, len(text) - 1))
    ch = text[pos]
    if ch.isalnum() or ch == "_":

        def _same(c: str) -> bool:
            return c.isalnum() or c == "_"

    elif ch.isspace():

        def _same(c: str) -> bool:
            return c.isspace()

    else:

        def _same(c: str) -> bool:
            return not (c.isalnum() or c == "_" or c.isspace())

    start = pos
    while start > 0 and _same(text[start - 1]):
        start -= 1
    end = pos + 1
    while end < len(text) and _same(text[end]):
        end += 1
    return start, end
