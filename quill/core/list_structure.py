"""Where the caret is inside a list, in Markdown or in HTML.

A screen reader tells you about a list because the *browser* tells the reader:
an ``<ul>`` reaches the accessibility tree as a list with a known item count, and
NVDA says "list with 5 items" going in, "level 2" going down a rung, and "out of
list" coming back out. That is one of the most useful things a reader says, and
inside an editor it is gone -- the list is not a widget, it is characters in an
edit control, and the control exposes none of it. So a listener writing a nested
bullet list in Markdown hears "dash space item" over and over with no way to
tell the second level from the third except by counting spaces by ear.

This module is the missing half. It reduces a caret position to a
:class:`ListContext` -- what kind of list, how deep, how many items -- and
:mod:`quill.core.structure_announce` turns a *change* in that context into the
one sentence worth saying. Both editors use it, over both markups.

Three kinds, because all three carry different meaning and a reader names all
three:

* **bullet** -- Markdown ``-``/``*``/``+``, HTML ``<ul>``. Order is not meaning.
* **numbered** -- Markdown ``1.``/``1)``, HTML ``<ol>``. Order *is* meaning, so
  losing your place in one costs more.
* **definition** -- HTML ``<dl>`` and the Pandoc / PHP-Markdown-Extra ``Term`` /
  ``: definition`` shape. It alternates between two roles, and which one you are
  standing in is invisible: a definition list where you think you are typing a
  term and are actually typing a definition comes out inside out.

Counting rules, both chosen because the alternative is a lie told confidently:

* **Items are counted at the caret's own level, within its own parent.** A
  three-item list whose second item has four sub-items is "3 items" at level 1
  and "4 items" at level 2 -- never "7". That is what a reader says and what the
  writer means.
* **A fenced code block is not a list.** A ``- ...`` line inside a fence is a
  sample, and announcing a list every time the caret crossed one would make the
  cue noise in exactly the documents that have the most of them.

Pure, wx-free and directly tested (``tests/unit/core/test_list_structure.py``).
The HTML side is a scanner rather than a parser on purpose: an editor buffer is
usually a *fragment*, often mid-edit and rarely well-formed, and an
``html.parser`` that raised or resynchronised on an unclosed tag would take the
cue out at exactly the moment somebody is halfway through typing one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "BULLET",
    "DEFINITION",
    "ITEM_NOUNS",
    "KIND_LABELS",
    "NUMBERED",
    "ListContext",
    "list_context_at",
    "supports_lists",
]

#: The three kinds, as they are stored and as they are spoken.
BULLET = "bullet"
NUMBERED = "numbered"
DEFINITION = "definition"

#: Human wording for each kind. Kept here rather than in the announcer so the
#: two products, the status bar and the tests all name a list the same thing.
KIND_LABELS: dict[str, str] = {
    BULLET: "Bulleted list",
    NUMBERED: "Numbered list",
    DEFINITION: "Definition list",
}
#: What one entry of each kind is called. A definition list holds terms.
ITEM_NOUNS: dict[str, str] = {BULLET: "item", NUMBERED: "item", DEFINITION: "term"}

#: The markups that can express a list at all. ``plain`` cannot, so the caret
#: cue is silent in a plain document rather than guessing from punctuation -- a
#: hyphen at the start of a line in a letter is a dash, not a bullet.
_LIST_MARKUPS = frozenset({"markdown", "html"})

_FENCE = re.compile(r"^(?P<indent>[ ]{0,3})(?P<fence>`{3,}|~{3,})[ \t]*")
_BULLET_ITEM = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>[-*+])(?P<space>[ \t]+)(?P<rest>.*)$")
_NUMBERED_ITEM = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>\d{1,9}[.)])(?P<space>[ \t]+)(?P<rest>.*)$"
)
#: Pandoc / PHP-Markdown-Extra definition: a ``:`` or ``~`` under a term line.
_DEFINITION_ITEM = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>[:~])(?P<space>[ \t]+)(?P<rest>.*)$")

#: One HTML tag, open or close. Deliberately loose: it has to survive the
#: half-typed ``<ul`` that is on screen for as long as somebody's fingers take.
_TAG = re.compile(r"<\s*(?P<close>/?)\s*(?P<name>[A-Za-z][A-Za-z0-9-]*)(?P<rest>[^>]*)>")
#: Regions whose angle brackets are not markup. A ``<li>`` written *about*
#: inside a comment is prose, and one inside ``<script>`` is a string.
_OPAQUE = re.compile(r"<!--.*?-->|<script\b.*?</script\s*>|<style\b.*?</style\s*>", re.S | re.I)

_HTML_LIST_TAGS = {"ul": BULLET, "ol": NUMBERED, "dl": DEFINITION, "menu": BULLET}
_HTML_ITEM_TAGS = {"li": "item", "dt": "term", "dd": "definition"}


def supports_lists(markup_kind: str | None) -> bool:
    """Whether *markup_kind* can express a list that this module can read."""
    return str(markup_kind or "") in _LIST_MARKUPS


@dataclass(frozen=True, slots=True)
class ListContext:
    """The list the caret is standing in, reduced to what is worth saying.

    ``key`` identifies the innermost list itself, so re-entering the same list
    after a trip outside is a crossing and moving between its items is not. It
    is the offset that list starts at, which is stable under everything except
    an edit above it -- and the announcer re-latches silently after an edit.

    ``root_key`` identifies the *outermost* list of the same nest. The two keys
    answer two different questions and the announcer needs both: ``root_key``
    says whether you have walked into or out of a list structure at all, and
    ``key`` says whether the rung you are standing on has changed. Without the
    outer one, stepping from level one to level two reads as leaving one list
    and entering another, which is not what happened and not what it feels like.

    ``size`` counts the items **at the caret's level, within its own parent**;
    ``index`` is the caret's 1-based place among them. ``role`` is ``"item"``
    everywhere except a definition list, where it is ``"term"`` or
    ``"definition"`` -- the one distinction inside a list that changes what the
    text *means* and that nothing else in the stack will say.
    """

    kind: str
    depth: int
    key: object
    root_key: object = None
    size: int = 0
    index: int = 0
    role: str = "item"

    def __post_init__(self) -> None:
        if self.root_key is None:
            object.__setattr__(self, "root_key", self.key)

    @property
    def label(self) -> str:
        """``"Numbered list"`` -- how this kind of list is named aloud."""
        return KIND_LABELS.get(self.kind, "List")

    @property
    def item_noun(self) -> str:
        """``"item"`` or ``"term"`` -- what one of its entries is called."""
        return ITEM_NOUNS.get(self.kind, "item")


def list_context_at(text: str, offset: int, *, markup_kind: str) -> ListContext | None:
    """The list the caret sits in at *offset*, or ``None`` when it is not in one.

    ``markup_kind`` is the document's language, not a guess from the text: a
    ``.txt`` letter full of hyphens is not a bulleted list, and deciding
    otherwise from punctuation is how a helpful cue becomes a superstition.
    """
    if not supports_lists(markup_kind):
        return None
    clamped = max(0, min(int(offset), len(text)))
    if markup_kind == "html":
        return _html_context(text, clamped)
    return _markdown_context(text, clamped)


# -- Markdown ---------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _Line:
    """One parsed line: where it starts, how deep it is indented, what it is."""

    start: int
    end: int
    indent: int
    kind: str | None  # BULLET / NUMBERED / DEFINITION on an item line
    content_indent: int  # the column an item's own text begins at
    blank: bool
    fenced: bool
    #: ``"item"``, or ``"term"`` / ``"definition"`` in a definition list.
    role: str = "item"


def _expand_indent(raw: str) -> int:
    """Indent width in columns, with a tab counting as four.

    Four rather than eight because four is what every Markdown editor in use
    inserts for a nested bullet, this one included. The number only has to be
    consistent -- it is compared against other lines of the same document, never
    against an absolute.
    """
    width = 0
    for char in raw:
        width += 4 - (width % 4) if char == "\t" else 1
    return width


def _scan_markdown(text: str) -> list[_Line]:
    """Every line of *text*, classified, with fenced code blocks marked."""
    lines: list[_Line] = []
    open_fence: str | None = None
    position = 0
    for raw in text.split("\n"):
        start = position
        end = start + len(raw)
        position = end + 1
        leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
        indent = _expand_indent(leading)
        blank = not raw.strip()
        if open_fence is not None:
            lines.append(_Line(start, end, indent, None, indent, blank, True))
            if _closes_fence(raw, open_fence):
                open_fence = None
            continue
        fence = _FENCE.match(raw) if indent <= 3 else None
        if fence is not None:
            open_fence = fence.group("fence")
            lines.append(_Line(start, end, indent, None, indent, False, True))
            continue
        kind: str | None = None
        content_indent = indent
        for pattern, item_kind in (
            (_BULLET_ITEM, BULLET),
            (_NUMBERED_ITEM, NUMBERED),
            (_DEFINITION_ITEM, DEFINITION),
        ):
            match = pattern.match(raw)
            if match is None:
                continue
            # ``---`` is a thematic break and ``***`` is one too. Neither is a
            # one-item list, and treating them as one would put a "Bulleted
            # list" between every two sections of a well-formatted document.
            if item_kind == BULLET and _is_thematic_break(raw):
                break
            kind = item_kind
            content_indent = _expand_indent(leading + match.group("marker")) + len(
                match.group("space")
            )
            break
        role = "definition" if kind == DEFINITION else "item"
        lines.append(_Line(start, end, indent, kind, content_indent, blank, False, role))
    return _mark_definition_terms(lines)


def _mark_definition_terms(lines: list[_Line]) -> list[_Line]:
    """Promote the plain line above a ``: definition`` to that list's term.

    A Pandoc definition list is the one list shape whose *first* line carries no
    marker at all -- the term is ordinary text, and only the ``:`` under it says
    what it was. Nothing can see that on the term's own line, so it is resolved
    here in a second pass and the term becomes a real item like any other. Terms
    are what a definition list is counted in, matching ``<dt>`` on the HTML side.
    """
    for index, line in enumerate(lines):
        if line.kind is not None or line.blank or line.fenced:
            continue
        following = _next_non_blank(lines, index + 1)
        if following is None:
            continue
        candidate = lines[following]
        if candidate.kind == DEFINITION and candidate.indent >= line.indent:
            lines[index] = _Line(
                line.start,
                line.end,
                line.indent,
                DEFINITION,
                line.content_indent,
                False,
                False,
                "term",
            )
    return lines


def _closes_fence(line: str, open_fence: str) -> bool:
    stripped = line.strip()
    char = open_fence[0]
    if not stripped.startswith(char):
        return False
    count = len(stripped) - len(stripped.lstrip(char))
    return count >= len(open_fence) and not stripped[count:].strip()


def _is_thematic_break(line: str) -> bool:
    """``---``, ``***`` or ``___`` alone on a line: a rule, not a bullet."""
    body = line.strip().replace(" ", "").replace("\t", "")
    return len(body) >= 3 and len(set(body)) == 1 and body[0] in "-*_"


def _line_index_for(lines: list[_Line], offset: int) -> int:
    for index, line in enumerate(lines):
        if offset <= line.end:
            return index
    return max(0, len(lines) - 1)


def _next_non_blank(lines: list[_Line], start: int) -> int | None:
    for index in range(start, len(lines)):
        if not lines[index].blank:
            return index
    return None


def _owning_item(lines: list[_Line], index: int) -> int | None:
    """The item line the caret's line belongs to, following continuations.

    A wrapped bullet, a paragraph indented under one, and the blank line between
    an item and its own second paragraph are all still *inside* that item. The
    rule is CommonMark's: a line indented to at least the item's content column
    continues it. A blank line continues the item only when what follows does
    too, which is what stops the gap between two separate lists reading as one.
    """
    if index < 0 or index >= len(lines):
        return None
    line = lines[index]
    if line.kind is not None and not line.fenced:
        return index
    if line.blank:
        following = _next_non_blank(lines, index + 1)
        if following is None:
            return None
        if lines[following].kind is None and lines[following].indent <= line.indent:
            return None
    cursor = index - 1
    while cursor >= 0:
        candidate = lines[cursor]
        if candidate.blank:
            cursor -= 1
            continue
        if candidate.kind is not None and line.indent >= candidate.content_indent:
            return cursor
        if candidate.kind is None and candidate.indent < max(1, line.indent):
            return None
        cursor -= 1
    return None


def _markdown_context(text: str, offset: int) -> ListContext | None:
    lines = _scan_markdown(text)
    if not lines:
        return None
    item_index = _owning_item(lines, _line_index_for(lines, offset))
    if item_index is None:
        return None
    item = lines[item_index]
    ancestors = _markdown_ancestors(lines, item_index)
    siblings = _markdown_siblings(lines, item_index, ancestors[-1] if ancestors else None)
    key = siblings[0].start if siblings else item.start
    position = next((n for n, line in enumerate(siblings, 1) if line.start == item.start), 0)
    return ListContext(
        kind=item.kind or BULLET,
        depth=len(ancestors) + 1,
        key=key,
        root_key=ancestors[0].start if ancestors else key,
        size=len(siblings),
        index=position,
        role=item.role,
    )


def _markdown_ancestors(lines: list[_Line], index: int) -> list[_Line]:
    """The item lines this one is nested inside, outermost first."""
    ancestors: list[_Line] = []
    indent = lines[index].indent
    cursor = index - 1
    while cursor >= 0 and indent > 0:
        candidate = lines[cursor]
        if candidate.blank:
            cursor -= 1
            continue
        if candidate.kind is not None and candidate.indent < indent:
            ancestors.append(candidate)
            indent = candidate.indent
        elif candidate.kind is None and candidate.indent == 0:
            break
        cursor -= 1
    ancestors.reverse()
    return ancestors


def _markdown_siblings(lines: list[_Line], index: int, parent: _Line | None) -> list[_Line]:
    """The item lines sharing this one's level *and* its parent, in order.

    Bounded by the parent rather than by indentation alone, so two sub-lists
    under two different bullets are two lists of two rather than one list of
    four -- which is the count somebody restructuring an outline is listening
    for.
    """
    item = lines[index]
    lower, upper = _sibling_bounds(lines, index, parent)
    # A definition list is counted in *terms*, matching ``<dt>`` on the HTML
    # side: "3 terms" is the shape of the list, and counting the bodies as well
    # would double it for no gain -- every term has one.
    wanted = "term" if item.kind == DEFINITION else None
    return [
        line
        for line in lines[lower : upper + 1]
        if line.kind is not None
        and line.indent == item.indent
        and (wanted is None or line.role == wanted)
    ]


def _sibling_bounds(lines: list[_Line], index: int, parent: _Line | None) -> tuple[int, int]:
    """The inclusive run of lines that can hold this item's siblings."""
    item = lines[index]
    floor = item.indent if parent is None else parent.content_indent
    lower = index
    while lower > 0:
        candidate = lines[lower - 1]
        if candidate.blank:
            # One blank line is a loose list; a gap with un-indented text on the
            # far side of it is the end of this list.
            preceding = _previous_non_blank(lines, lower - 1)
            if preceding is None or _ends_run(lines[preceding], item, floor, parent):
                break
            lower -= 1
            continue
        if _ends_run(candidate, item, floor, parent):
            break
        lower -= 1
    upper = index
    while upper + 1 < len(lines):
        candidate = lines[upper + 1]
        if candidate.blank:
            following = _next_non_blank(lines, upper + 1)
            if following is None or _ends_run(lines[following], item, floor, parent):
                break
            upper += 1
            continue
        if _ends_run(candidate, item, floor, parent):
            break
        upper += 1
    return lower, upper


def _ends_run(candidate: _Line, item: _Line, floor: int, parent: _Line | None) -> bool:
    """Whether *candidate* falls outside the run this item's siblings live in.

    The parent *is* a boundary, and that is the line that matters: a sub-list
    under the second bullet must stop at the second bullet, or it walks on up
    into the first bullet's sub-list and reports one list of four where there
    are two lists of two.
    """
    if parent is not None and candidate.start == parent.start:
        return True
    if candidate.kind is not None and candidate.indent == item.indent:
        return False
    if candidate.indent > item.indent:
        return False  # a nested line, still inside the run
    return candidate.indent < floor or candidate.kind is None


def _previous_non_blank(lines: list[_Line], start: int) -> int | None:
    for index in range(start - 1, -1, -1):
        if not lines[index].blank:
            return index
    return None


# -- HTML -------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _OpenList:
    """A list element open above the caret."""

    tag: str
    kind: str
    start: int
    body_start: int


def _blank_opaque(text: str) -> str:
    """*text* with comments, scripts and styles blanked to same-length runs.

    Blanked rather than removed so every offset in the result still means what
    it meant in the original -- the caret's position is the whole question here.
    """

    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return _OPAQUE.sub(blank, text)


def _is_self_closing(rest: str) -> bool:
    return rest.rstrip().endswith("/")


def _html_context(text: str, offset: int) -> ListContext | None:
    scrubbed = _blank_opaque(text)
    stack: list[_OpenList] = []
    roles: dict[int, str] = {}
    for match in _TAG.finditer(scrubbed, 0, offset):
        name = match.group("name").lower()
        closing = bool(match.group("close"))
        if name in _HTML_LIST_TAGS:
            if closing:
                _pop_to(stack, name)
                roles.pop(len(stack) + 1, None)
            elif not _is_self_closing(match.group("rest")):
                stack.append(_OpenList(name, _HTML_LIST_TAGS[name], match.start(), match.end()))
            continue
        if name in _HTML_ITEM_TAGS and stack:
            roles[len(stack)] = "" if closing else _HTML_ITEM_TAGS[name]
    if not stack:
        return None
    innermost = stack[-1]
    # An empty role means the caret is between ``</li>`` and the next ``<li>``:
    # outside every item and still inside the list, which is the fact the cue is
    # about, so it reads as a plain item rather than as having left.
    role = roles.get(len(stack)) or "item"
    size, index = _html_item_counts(scrubbed, innermost, offset)
    return ListContext(
        kind=innermost.kind,
        depth=len(stack),
        key=innermost.start,
        root_key=stack[0].start,
        size=size,
        index=index,
        role=role,
    )


def _pop_to(stack: list[_OpenList], tag: str) -> None:
    """Close the nearest *tag*, discarding whatever was left open inside it."""
    for position in range(len(stack) - 1, -1, -1):
        if stack[position].tag == tag:
            del stack[position:]
            return


def _html_item_counts(text: str, owner: _OpenList, offset: int) -> tuple[int, int]:
    """How many items *owner* holds directly, and which one holds *offset*.

    Direct children only: an ``<li>`` belonging to a nested ``<ul>`` is that
    list's item, not this one's. Counting those too is what would turn "3 items"
    into "7" in the one document shape -- an outline -- where the count matters
    most.
    """
    counted = "dt" if owner.kind == DEFINITION else "li"
    nested = 0
    size = 0
    index = 0
    for match in _TAG.finditer(text, owner.body_start):
        name = match.group("name").lower()
        closing = bool(match.group("close"))
        if name in _HTML_LIST_TAGS:
            if closing:
                if nested == 0:
                    break  # the owner's own close tag: the list ends here
                nested -= 1
            elif not _is_self_closing(match.group("rest")):
                nested += 1
            continue
        if nested or closing or name != counted:
            continue
        size += 1
        if match.start() <= offset:
            index = size
    return size, index
