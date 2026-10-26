"""Real RTF tables in a rich document; pipe rows wherever QUILL passes tables on.

In a rich document a table is RichEdit's own -- a grid on screen, a table to a
screen reader, to Word and to WordPad (:mod:`quill.ui.richedit_tables`). Outside
the editor QUILL hands tables around as Markdown pipe rows: a Word document's
tables arrive as them, Save as Word reads them, and so do the switches to
Markdown and plain text. This module is the bridge, in both directions:

* :func:`pipe_rows_to_rtf_tables` -- every run of pipe rows becomes a real
  ``\\trowd`` ... ``\\row`` table, its ``| --- |`` separator the header mark
  (``\\trhdr``). Used on what the editor is about to load
  (:func:`pipe_rows_as_tables`) and to build what Insert Table puts at the caret.
* :func:`rtf_tables_to_pipe_rows` -- every real table becomes pipe rows, its
  first row the header. Used on what the editor hands out
  (:func:`tables_to_pipe_rows_bytes`).
* :func:`mark_header_rows_in_file` -- RichEdit drops ``\\trhdr`` when it saves,
  so the saved file gets it back on each table's first row: that is how Word and
  a screen reader know the column headers.

Everything works on the RTF text, paragraph by paragraph, so the formatting
inside a cell -- bold, italic, a font -- crosses in both directions untouched.

Pure and wx-free.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from quill.core.table_nav import is_separator_row, is_table_row

__all__ = [
    "mark_header_rows",
    "mark_header_rows_in_file",
    "pipe_rows_as_tables",
    "pipe_rows_to_rtf_tables",
    "pipe_rows_to_tables_bytes",
    "rtf_tables_to_pipe_rows",
    "tables_to_pipe_rows_bytes",
]


def pipe_rows_to_tables_bytes(data: bytes) -> bytes:
    """:func:`pipe_rows_to_rtf_tables` over RTF bytes.

    RTF is seven-bit text with ``\\'xx`` escapes, so Latin-1 maps every byte to
    one character and back unchanged -- nothing outside the tables is touched.
    """
    return pipe_rows_to_rtf_tables(data.decode("latin-1")).encode("latin-1")


def tables_to_pipe_rows_bytes(data: bytes) -> bytes:
    """:func:`rtf_tables_to_pipe_rows` over RTF bytes."""
    if b"\\trowd" not in data:
        return data
    return rtf_tables_to_pipe_rows(data.decode("latin-1")).encode("latin-1")


_TROWD = re.compile(r"\\trowd(?![a-z])")
_ROW_END = re.compile(r"\\row(?![a-z])")


def mark_header_rows(rtf: str) -> str:
    """*rtf* with ``\\trhdr`` on the first row of every table that lacks it.

    A row starts a table unless the row before it ends right where it begins:
    a paragraph, or any text, between two rows makes them two tables.
    """
    out: list[str] = []
    last = 0
    previous_end: int | None = None
    for match in _TROWD.finditer(rtf):
        if previous_end is None:
            first = True
        else:
            gap = rtf[previous_end : match.start()]
            first = "\\par" in gap or bool(_visible_text(gap).strip())
        row_end = _ROW_END.search(rtf, match.end())
        stop = row_end.start() if row_end else len(rtf)
        out.append(rtf[last : match.end()])
        if first and "\\trhdr" not in rtf[match.end() : stop]:
            out.append("\\trhdr")
        last = match.end()
        previous_end = row_end.end() if row_end else len(rtf)
    out.append(rtf[last:])
    return "".join(out)


def mark_header_rows_in_file(path: str) -> None:
    """:func:`mark_header_rows` on the RTF file at *path*, in place.

    For a file the editor just saved: nothing else reads it until this returns.
    A file with no table is left alone. Raises ``OSError``.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if b"\\trowd" not in data:
        return
    marked = mark_header_rows(data.decode("latin-1")).encode("latin-1")
    if marked != data:
        with open(path, "wb") as handle:
            handle.write(marked)


@contextmanager
def pipe_rows_as_tables(path: str) -> Iterator[str]:
    """*path* itself, or a copy of it with its pipe rows as real tables.

    The copy lives in a temporary folder for the length of the ``with`` block,
    which is how long the control takes to read it.
    """
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        yield path  # the reader reports an unreadable file in its own words
        return
    converted = pipe_rows_to_tables_bytes(data) if b"|" in data else data
    if converted == data:
        yield path
        return
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "quill-tables.rtf")
        with open(copy, "wb") as handle:
            handle.write(converted)
        yield copy


#: Total table width in twips (6.5 inches: a Letter page inside 1-inch margins).
_TABLE_WIDTH = 9360

#: One control word, with its optional numeric parameter and one delimiting space.
_CONTROL = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?")


def _paragraphs(body: str) -> list[str]:
    """Split RTF *body* into top-level pieces, each ending just after a ``\\par``.

    Only a ``\\par`` at the document's own level ends a piece; one inside a group
    (a footnote, a field) belongs to that group. The last piece is whatever
    follows the final ``\\par`` -- usually the closing brace.
    """
    pieces: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(body):
        char = body[i]
        if char == "\\":
            match = _CONTROL.match(body, i)
            if match is None:
                i += 2  # an escaped symbol: \\ \{ \} \'xx's backslash
                continue
            if match.group(1) == "par" and depth == 1:
                end = match.end()
                while end < len(body) and body[end] in "\r\n":
                    end += 1
                pieces.append(body[start:end])
                start = end
                i = end
                continue
            i = match.end()
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        i += 1
    pieces.append(body[start:])
    return pieces


def _visible_text(raw: str) -> str:
    """The text a paragraph shows, control words and groups stripped."""
    out: list[str] = []
    depth = 0
    skip_depth: int | None = None
    i = 0
    while i < len(raw):
        char = raw[i]
        if char == "\\":
            if raw.startswith("\\\\", i) or raw.startswith("\\{", i) or raw.startswith("\\}", i):
                if skip_depth is None:
                    out.append(raw[i + 1])
                i += 2
                continue
            if raw.startswith("\\'", i):
                if skip_depth is None:
                    out.append(chr(int(raw[i + 2 : i + 4], 16)))
                i += 4
                continue
            if raw.startswith("\\*", i):
                skip_depth = depth if skip_depth is None else skip_depth
                i += 2
                continue
            match = _CONTROL.match(raw, i)
            i = match.end() if match else i + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            if skip_depth is not None and depth == skip_depth:
                skip_depth = None
            depth -= 1
        elif char not in "\r\n" and skip_depth is None:
            out.append(char)
        i += 1
    return "".join(out)


def _split_raw_cells(raw: str) -> tuple[str, list[str]]:
    """``(prefix, cells)``: a pipe row's raw RTF, cut at its top-level pipes.

    *prefix* is everything before the first pipe (paragraph and font controls the
    control writes at the start of a line). An escaped pipe -- ``\\|`` in the
    text, ``\\\\|`` in RTF -- is cell text, not a divider.
    """
    found: list[tuple[int, int]] = []  # (position, group depth) of every pipe
    depth = 0
    i = 0
    while i < len(raw):
        char = raw[i]
        if char == "\\":
            if raw.startswith("\\\\|", i):
                i += 3
                continue
            match = _CONTROL.match(raw, i)
            i = match.end() if match else i + 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == "|":
            found.append((i, depth))
        i += 1
    if not found:
        return raw, []
    # The row's own pipes are the shallowest ones: a piece can begin inside the
    # document's opening brace, and a pipe inside a cell's group is one deeper.
    level = min(d for _i, d in found)
    bars = [position for position, d in found if d == level]
    prefix = raw[: bars[0]]
    tail = raw[bars[-1] + 1 :]
    cells = [raw[a + 1 : b] for a, b in zip(bars, bars[1:], strict=False)]
    # Text after the last pipe is a final cell only if it is not just the \par.
    rest = _CONTROL.sub("", tail.replace("\\par", "")).strip()
    if rest:
        cells.append(tail.split("\\par")[0])
    return prefix, cells


def _unwrap(cell: str) -> str:
    """*cell* without the one group around all of it, if there is exactly one.

    Each cell is written inside a group of its own, in both directions; without
    this every save and open would add another pair of braces.
    """
    cell = cell.strip()
    if not (cell.startswith("{") and cell.endswith("}")):
        return cell
    depth = 0
    for index, char in enumerate(cell):
        if char == "{" and (index == 0 or cell[index - 1] != "\\"):
            depth += 1
        elif char == "}" and cell[index - 1] != "\\":
            depth -= 1
            if depth == 0 and index != len(cell) - 1:
                return cell  # the first group closes early: not one group
    return cell[1:-1]


def _cell_rtf(raw: str) -> str:
    """One cell's content for a table row: trimmed, its escaped pipes made plain."""
    return _unwrap(raw).replace("\\\\|", "|")


def _table_rtf(rows: list[str], header: bool) -> str:
    """The ``\\trowd`` ... ``\\row`` block for *rows* (raw paragraph RTF each)."""
    parsed = [_split_raw_cells(row) for row in rows]
    columns = max((len(cells) for _prefix, cells in parsed), default=1) or 1
    width = _TABLE_WIDTH // columns
    definition = "".join(f"\\cellx{width * (index + 1)}" for index in range(columns))
    lines: list[str] = []
    for index, (_prefix, cells) in enumerate(parsed):
        padded = cells + [""] * (columns - len(cells))
        trhdr = "\\trhdr" if header and index == 0 else ""
        body = "".join(f"{{{_cell_rtf(cell)}}}\\cell " for cell in padded)
        lines.append(f"\\trowd\\trgaph108{trhdr}{definition}\r\n\\pard\\intbl {body}\\row\r\n")
    return "".join(lines)


def pipe_rows_to_rtf_tables(rtf: str) -> str:
    """Rewrite every run of two or more pipe-row paragraphs as a real RTF table.

    A ``| --- |`` separator under the first row makes it the header row
    (``\\trhdr``) and is not written as a row. Everything that is not a table is
    returned byte for byte.
    """
    pieces = _paragraphs(rtf)
    texts = [_visible_text(piece) for piece in pieces]
    out: list[str] = []
    i = 0
    while i < len(pieces):
        if not is_table_row(texts[i]):
            out.append(pieces[i])
            i += 1
            continue
        end = i
        while end + 1 < len(pieces) and is_table_row(texts[end + 1]):
            end += 1
        if end == i:  # a single pipe line is not a table
            out.append(pieces[i])
            i += 1
            continue
        run = list(range(i, end + 1))
        header = len(run) > 1 and is_separator_row(texts[run[1]])
        rows = [pieces[j] for j in run if not is_separator_row(texts[j])]
        # Whatever stood before the first pipe stays, byte for byte: for a table
        # at the very start of a document it is the header -- the opening brace,
        # the font table -- and dropping any of it would break the file.
        prefix, _cells = _split_raw_cells(pieces[i])
        out.append(prefix + _table_rtf(rows, header))
        # Leave the table: the paragraph after it starts fresh.
        if end + 1 < len(pieces) and not pieces[end + 1].lstrip().startswith("\\pard"):
            pieces[end + 1] = "\\pard " + pieces[end + 1]
        i = end + 1
    return "".join(out)


#: A table row: from ``\trowd`` to its ``\row``.
_ROW = re.compile(r"\\trowd\b.*?\\row(?![a-z])\s*", re.DOTALL)
#: The row-definition controls in front of a row's first cell.
_ROW_DEFINITION = re.compile(
    r"\\(?:trowd|trgaph-?\d+|trleft-?\d+|trrh-?\d+|trq[lrc]|trhdr|trkeep|trautofit\d*|"
    r"trpadd[a-z]*-?\d*|trftsWidth\d*|trwWidth\d*|irow\d+|irowband-?\d+|ts\d+|"
    r"clvertal[tcb]|clbrdr[tblr]|brdr[a-z]+\d*|brdrw\d+|brdrcf\d+|clcbpat\d+|"
    r"clftsWidth\d*|clwWidth\d*|clpad[a-z]*\d*|cellx-?\d+|lastrow|trbrdr[tblrhv])(?![a-z]) ?"
)


def _cell_texts(row_rtf: str) -> list[str]:
    """The cells of one ``\\trowd`` ... ``\\row`` block, as inline RTF."""
    body = _ROW_DEFINITION.sub("", row_rtf)
    body = re.sub(r"\\row(?![a-z])\s*$", "", body.rstrip())
    parts = re.split(r"\\cell(?![a-z])\s?", body)
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    cells: list[str] = []
    for part in parts:
        part = re.sub(r"\\(?:pard|intbl|plain)(?![a-z]) ?", "", part).strip()
        cells.append(_unwrap(part).replace("|", "\\\\|"))
    return cells


def rtf_tables_to_pipe_rows(rtf: str) -> str:
    """Rewrite every real RTF table as pipe-row paragraphs the table keys read.

    Each table's first row is its header, with the ``| --- |`` separator under
    it: the editor treats every real table's first row as its header, so that
    is what the round trip keeps. A pipe inside a cell is escaped, so it stays
    cell text.
    """
    out: list[str] = []
    last = 0
    in_table = False
    for match in _ROW.finditer(rtf):
        between = rtf[last : match.start()]
        if between.strip() and _visible_text(between).strip():
            in_table = False
        out.append(between)
        cells = _cell_texts(match.group(0))
        # Each cell in a group of its own: formatting cannot leak into the next
        # cell, and a cell ending in a control word (\b0) cannot swallow the
        # space in front of the next pipe as its delimiter.
        row = "| " + " | ".join(f"{{{cell}}}" for cell in cells) + " |"
        lines = [f"\\pard {row}\\par\r\n"]
        if not in_table:
            divider = "| " + " | ".join("---" for _ in cells) + " |"
            lines.append(f"\\pard {divider}\\par\r\n")
        out.extend(lines)
        in_table = True
        last = match.end()
    out.append(rtf[last:])
    return "".join(out)
