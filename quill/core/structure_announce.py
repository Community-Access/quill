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
* **Crossing a list boundary, or changing level inside one** -- "Bulleted list,
  5 items" on the way in, "Level 2, 3 items" a rung down, "Out of list" on the
  way out. This is the one cue in the set a screen reader *does* give you
  elsewhere: in a browser an ``<ul>`` reaches the accessibility tree as a list
  with a count, and NVDA says very nearly this sentence. In an editor the list
  is characters rather than a widget, so the reader has nothing to go on and the
  editor owes it. :mod:`quill.core.list_structure` does the reading; this
  decides what of it is worth saying.

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

from quill.core.list_structure import DEFINITION, ListContext, list_context_at
from quill.core.table_nav import TableGrid, find_table_at

__all__ = [
    "HEADING_POSITIONS",
    "HEADING_POSITION_LABELS",
    "StructureAnnouncer",
    "StructurePoint",
    "describe_heading_arrival",
    "point_from_text",
    "heading_first_from",
]


def describe_heading_arrival(
    level: int,
    title: str,
    *,
    ordinal: int | None = None,
    total: int | None = None,
) -> str:
    """What both editors say on arriving at a heading (bad.md R15).

    QUILL said "Moved to next heading, H2, 3 of 12: Installing" and QuillLite
    said "Heading 2: Installing". Two products, one key, two sentences -- and
    each half-right.

    **"Moved to next heading" goes.** You pressed the next-heading key; that you
    moved to the next heading is the one thing you already knew, and GATE-13 is
    the rule that says the app speaks only what the reader cannot. It is also
    what every screen reader says navigating headings on a web page: the level,
    then the text. QuillLite's shape wins on that count.

    **"3 of 12" stays**, which is QUILL's and is the half worth keeping: it is
    the only thing in the sentence that tells you where you are in the document
    rather than what is under the caret, and there is no other way to find out
    without counting.

    **"Heading 2" rather than "H2"**, because "H2" read aloud is "aitch two" and
    a person has to translate it every time.
    """
    named = title.strip() or "untitled"
    where = ""
    if ordinal is not None and total is not None and total > 0:
        where = f", {ordinal} of {total}"
    return f"Heading {level}{where}: {named}"


#: Where the level goes relative to the heading's own text.
HEADING_POSITIONS: tuple[str, ...] = ("before", "after")

#: How each is named on screen, in both editors' Preferences. One table, so the
#: two products cannot describe the same choice in different words.
HEADING_POSITION_LABELS: dict[str, str] = {
    "before": 'Before the text ("Heading 2, Installing")',
    "after": 'After the text ("Installing... Heading 2")',
}


def heading_first_from(settings: object) -> bool:
    """Whether *settings* asks for the level in front of the heading's text.

    Reached for defensively and defaulting to ``True``, which is the setting's
    own default: a settings object that predates the field -- a file written by
    an older build, or a test stub -- gets the behaviour that works on every
    kind of caret move rather than the one that is lossy on half of them.
    """
    return str(getattr(settings, "heading_announce_position", "before") or "before") != "after"


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

    ``list_context`` is the list the caret is standing in, or ``None``. It is
    built by the caller and may be ``None`` simply because the user has switched
    list cues off -- which is deliberate, and is what makes switching them back
    on announce the list you are already in on your very next keypress, rather
    than staying silent until you happen to leave it and return.
    """

    paragraph_key: object
    heading_level: int = 0
    #: The heading's own words, so the cue can lead with the level and carry the
    #: text with it. Empty when the caller has not supplied it, in which case the
    #: cue falls back to the level alone.
    heading_text: str = ""
    table_key: object | None = None
    table_shape: tuple[int, int] | None = None
    list_context: ListContext | None = None


def point_from_text(
    text: str,
    offset: int,
    *,
    heading_level: int,
    heading_text: str = "",
    paragraph_key: object | None = None,
    include_tables: bool = True,
    list_markup: str | None = None,
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

    ``list_markup`` is the document's language (``"markdown"`` or ``"html"``)
    when list cues are wanted, and ``None`` when they are not -- either because
    the document has no markup that could hold a list or because the user has
    switched the cue off. ``None`` skips the scan as well as the announcement.
    """
    clamped = max(0, min(int(offset), len(text)))
    if paragraph_key is None:
        paragraph_key = text.count("\n", 0, clamped)
    grid: TableGrid | None = (
        find_table_at(text, clamped) if include_tables and _line_has_pipe(text, clamped) else None
    )
    listing = list_context_at(text, clamped, markup_kind=list_markup) if list_markup else None
    return StructurePoint(
        paragraph_key=paragraph_key,
        heading_level=int(heading_level),
        heading_text=str(heading_text or ""),
        table_key=grid.span_start if grid is not None else None,
        table_shape=(grid.row_count, grid.col_count) if grid is not None else None,
        list_context=listing,
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


def _list_entry_phrase(context: ListContext) -> str:
    """Name a list on arrival: its kind, its size, and its level if it has one.

    The level comes last and only when it is worth saying. Landing on level one
    of a list does not need "level 1" after it; landing straight inside a nested
    one -- which is what Ctrl+End, a search hit and a bookmark all do -- very
    much does, because the indentation that would have shown a sighted reader
    how deep this is went past without a sound.
    """
    phrase = f"{context.label}, {_plural(context.size, context.item_noun)}"
    return phrase if context.depth <= 1 else f"{phrase}, level {context.depth}"


class StructureAnnouncer:
    """Turns a stream of caret positions into the few sentences worth saying.

    Feed it a :class:`StructurePoint` after every caret move; it answers with
    what to speak, or ``None`` for the overwhelmingly common case of "nothing the
    reader is not already saying". It is a latch, so it must be fed *every* move
    -- skipping the quiet ones would let a re-entry go unannounced.
    """

    def __init__(self) -> None:
        self._last: StructurePoint | None = None
        #: Whether the phrase just returned already contains the line's own
        #: text, and must therefore *replace* the screen reader's reading of it
        #: rather than follow it. The one piece of state a caller needs that is
        #: not the words themselves: it decides whether to interrupt.
        self.replaces_reader = False

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

    def update(self, point: StructurePoint, *, heading_first: bool = False) -> str | None:
        """What to say now that the caret is at ``point`` (or ``None``).

        ``heading_first=True`` puts the level **in front of** the heading's own
        text -- "Heading 2, Installing" -- as one utterance the editor owns, and
        sets :attr:`replaces_reader` so the caller interrupts rather than queues.

        That is not a matter of taste. A cue queued *behind* the reader is at the
        reader's mercy: on a large caret jump -- Ctrl+Home, a search hit, a
        bookmark -- NVDA and JAWS cancel what is pending and start again on the
        new line, and the "Heading 1" waiting its turn is never heard at all. It
        is also the order a browser gives you, where a reader says "heading level
        two" before reading the heading.
        """
        previous = self._last
        self._last = point
        self.replaces_reader = False
        if previous is None:
            # First position in a document. Announce a *container* -- a table
            # or a list -- because arriving inside one is genuinely disorienting
            # and completely invisible. Not a heading: the reader reads the line
            # the caret starts on, and a document that opens on its own title
            # would greet every user with "Heading 1" across the top of it.
            if point.table_key is not None:
                return self._table_phrase(point)
            if point.list_context is not None:
                return _list_entry_phrase(point.list_context)
            return None

        if point.table_key != previous.table_key:
            phrase = self._table_phrase(point)
            if phrase is not None:
                return phrase
            return "Out of table"

        list_phrase = self._list_phrase(previous.list_context, point.list_context)
        if list_phrase is not None:
            # Ahead of the paragraph check on purpose: a definition term and its
            # body can land on one paragraph key in a buffer that wraps them, and
            # the role change is the one thing worth saying about that move.
            return list_phrase

        if point.paragraph_key == previous.paragraph_key:
            # Same paragraph: the caret moved by a character or a word. Nothing
            # has changed structurally and the reader is already speaking.
            return None

        if point.heading_level > 0:
            if heading_first and point.heading_text:
                # One utterance, ours, level first. ``replaces_reader`` tells the
                # caller to interrupt -- which is safe precisely because the text
                # the reader was about to say is inside this sentence.
                self.replaces_reader = True
                return f"Heading {point.heading_level}, {point.heading_text}"
            return f"Heading {point.heading_level}"
        return None

    @staticmethod
    def _list_phrase(before: ListContext | None, now: ListContext | None) -> str | None:
        """What a move from *before* to *now* changed about the list, if anything.

        Four events and nothing else, which is the whole discipline:

        * **Out.** ``now`` is ``None`` where ``before`` was not.
        * **In.** A different list structure (``root_key``), or the first one.
          Named in full, because arriving is the moment you need to know what it
          is you have arrived in.
        * **A rung.** Same structure, different depth -- or a different sub-list
          at the same depth, which is a different list however it feels. "Level
          2, 3 items", and the kind as well when that changed, since a bulleted
          list nested inside a numbered one is a real difference and a silent one.
        * **Term or definition.** Only in a definition list, only on a change.
          This is the one alternation inside a list where the role decides what
          the text *means*, and nothing else in the stack will ever say it.

        Everything else -- above all moving from one item to the next, which is
        what the caret does nearly all the time in a list -- is silent. The
        reader is already speaking the item.
        """
        if now is None:
            return "Out of list" if before is not None else None
        if before is None or before.root_key != now.root_key:
            return _list_entry_phrase(now)
        if before.depth != now.depth or before.key != now.key:
            if before.kind != now.kind:
                return _list_entry_phrase(now)
            return f"Level {now.depth}, {_plural(now.size, now.item_noun)}"
        if now.kind == DEFINITION and before.role != now.role:
            return now.role.capitalize()
        return None

    @staticmethod
    def _table_phrase(point: StructurePoint) -> str | None:
        if point.table_key is None:
            return None
        rows, columns = point.table_shape or (0, 0)
        return f"Table, {_plural(rows, 'row')}, {_plural(columns, 'column')}"
