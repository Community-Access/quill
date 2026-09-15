"""What to say as the caret moves through a document's structure.

A screen reader announces what it can see, and a Windows edit control shows it
almost nothing: font name, point size, weight. There is no paragraph style in
``RICHEDIT50W`` and none in ``wx.TextCtrl``, so there is nothing for JAWS or NVDA
to read when the caret lands on a heading. Word announces "heading level 2"
because Word ships a UIA provider that exposes ``StyleId_Heading2``; hosting a
stock control buys the control's own provider and no way to extend it.

So the editor says it itself. That is not a workaround anybody should feel bad
about -- it is what every screen-reader-first word processor on Windows does,
and it is squarely inside GATE-13: the reader cannot know a paragraph is a
heading, so this is ours to say.

The discipline is the whole design. Two things are announced and nothing else:

* **Entering a heading paragraph** -- "Heading 2", and only the level. The
  reader is already reading the line's text as the caret lands on it, so
  repeating the text here would speak every heading twice.
* **Crossing a table boundary** by ordinary line movement -- "Table, 4 rows, 3
  columns" on the way in and "Out of table" on the way out. Cell-by-cell
  navigation speaks for itself (:mod:`quill.core.table_nav`); this is the cue
  for the user who arrowed into a grid without meaning to and would otherwise
  hear a line of pipes with no explanation.

The table half is **QUILL only** and QuillLite passes ``include_tables=False``.
That is a deliberate product line, not an oversight: accessible table navigation
is a full-QUILL feature, and a boundary cue for a grid the small editor cannot
then navigate would announce a capability that is not there. It does not offend
the QuillLite rule in CLAUDE.md, which forbids Lite being *ahead* of QUILL --
never the other way about. Headings go to both editors.

Everything else stays silent, and the :class:`StructureAnnouncer` latch is what
keeps it that way: moving the caret *within* a heading says nothing, because you
have already been told. Leasey reaches the same conclusion from the other end
with its last-announced-page latch -- the cue is about the crossing, never about
the position.

Pure and wx-free. The UI layer reads the caret, builds a :class:`StructurePoint`
for wherever it is, and speaks whatever comes back.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.table_nav import TableGrid, find_table_at

__all__ = [
    "StructureAnnouncer",
    "StructurePoint",
    "point_from_text",
]


@dataclass(frozen=True, slots=True)
class StructurePoint:
    """Where the caret is, structurally, reduced to the parts worth speaking.

    ``paragraph_key`` identifies the paragraph the caret sits in -- a line index
    in markup mode, a paragraph start offset in rich mode. Its only job is to be
    *different* when the caret has moved to a different paragraph, which is what
    separates "arrived at a heading" from "still in the heading".

    ``table_key`` identifies the table the caret is inside (its start offset), or
    ``None`` outside one. ``table_shape`` carries ``(rows, columns)`` so entering
    a table can say how big it is.
    """

    paragraph_key: object
    heading_level: int = 0
    table_key: object | None = None
    table_shape: tuple[int, int] | None = None


def point_from_text(
    text: str,
    offset: int,
    *,
    heading_level: int,
    paragraph_key: object | None = None,
    include_tables: bool = True,
) -> StructurePoint:
    """Build a :class:`StructurePoint` for ``offset`` in ``text``.

    ``heading_level`` comes from the caller because the two editor modes know it
    two different ways: markup mode reads the Markdown hashes off the line, rich
    mode asks the control's Text Object Model for the font. The table half is the
    same in both, because both present a table as pipe rows in the buffer.

    ``paragraph_key`` defaults to the caret's line index, which is the right
    identity in markup mode and a serviceable one anywhere the buffer mirrors the
    visible text.

    ``include_tables=False`` skips table detection entirely -- QuillLite's
    setting, because table navigation is a full-QUILL feature and a boundary cue
    for a grid you cannot navigate is worse than silence. It also skips the scan,
    which is the whole per-keystroke cost of this module.
    """
    clamped = max(0, min(int(offset), len(text)))
    if paragraph_key is None:
        paragraph_key = text.count("\n", 0, clamped)
    grid: TableGrid | None = (
        find_table_at(text, clamped) if include_tables and _line_has_pipe(text, clamped) else None
    )
    if grid is None:
        return StructurePoint(paragraph_key=paragraph_key, heading_level=int(heading_level))
    return StructurePoint(
        paragraph_key=paragraph_key,
        heading_level=int(heading_level),
        table_key=grid.span_start,
        table_shape=(grid.row_count, grid.col_count),
    )


def _line_has_pipe(text: str, offset: int) -> bool:
    """Cheap veto before parsing the document for tables.

    Every row of a pipe table contains a pipe, so a caret line without one
    cannot be inside a table. This runs on every keystroke; ``find_table_at``
    scans outward from the caret and must not. QUILL had this guard inline
    before the announcer was shared -- it belongs with the scan it protects.
    """
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    return "|" in text[line_start : line_end if line_end != -1 else len(text)]


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


class StructureAnnouncer:
    """Turns a stream of caret positions into the few sentences worth saying.

    Feed it a :class:`StructurePoint` after every caret move; it answers with
    what to speak, or ``None`` for the overwhelmingly common case of "nothing the
    reader is not already saying". It is a latch, so it must be fed *every* move
    -- skipping the quiet ones would let a re-entry go unannounced.
    """

    def __init__(self) -> None:
        self._last: StructurePoint | None = None

    def reset(self) -> None:
        """Forget where the caret was: a new document, or a mode switch.

        The next update then announces whatever it lands on, which is right --
        after loading a file the caret's surroundings are news again.
        """
        self._last = None

    def sync(self, point: StructurePoint) -> None:
        """Move the latch without speaking.

        For the moment a command has *already* said it: applying Heading 2
        announces "Heading 2" itself, and the caret-move hook that fires
        immediately afterwards must not say it a second time.
        """
        self._last = point

    def update(self, point: StructurePoint) -> str | None:
        """What to say now that the caret is at ``point`` (or ``None``)."""
        previous = self._last
        self._last = point
        if previous is None:
            # First position in a document. Announce a table, because arriving
            # inside a grid is genuinely disorienting, but not a heading: the
            # reader reads the line the caret starts on, and a document that
            # opens on its own title would greet every user with "Heading 1".
            return self._table_phrase(point) if point.table_key is not None else None

        if point.table_key != previous.table_key:
            phrase = self._table_phrase(point)
            if phrase is not None:
                return phrase
            return "Out of table"

        if point.paragraph_key == previous.paragraph_key:
            # Same paragraph: the caret moved by a character or a word. Nothing
            # has changed structurally and the reader is already speaking.
            return None

        if point.heading_level > 0:
            return f"Heading {point.heading_level}"
        return None

    @staticmethod
    def _table_phrase(point: StructurePoint) -> str | None:
        if point.table_key is None:
            return None
        rows, columns = point.table_shape or (0, 0)
        return f"Table, {_plural(rows, 'row')}, {_plural(columns, 'column')}"
