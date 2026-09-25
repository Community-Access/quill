"""Move Section To: a destination, not forty keystrokes.

Alt+Shift+Up moves a section one step. That is the right tool for tidying two
adjacent sections and the wrong one for moving a section across a long
document: forty presses is forty announcements, and by ear you have to count
them, because there is no page to glance at to see how far you have got. Every
press also commits: overshoot and you press the other key and hope the document
came back the way it was.

So this is a **destination picker** instead of a faster key. Two questions, both
answered from a filtered list:

1. **Which heading?** Every heading in the document, each row saying where it
   sits -- ``"2 of 6, level 2 - Bread"`` -- so a name shared by two headings is
   still two distinguishable rows.
2. **Before, after, or inside it?** Three rows, because "next to that heading"
   is genuinely ambiguous and guessing is worse than asking.

One edit, one undo step, one sentence. This is the operation cut-and-paste is
worst at -- selecting from a heading to exactly the start of the next one is an
invisible boundary found by trial -- and the one a picker is best at. Word has
no equivalent.

**Only "Inside" changes a level**, and it says so before and after. Everything
else preserves the moved section's level exactly, for the same reason
:func:`~quill.core.markdown_sections.move_section` does: a key that says "move"
and also renumbers your headings has edited more than it said. Promote and
Demote are on Alt+Shift+Left/Right for when that is what you meant.

Everything here is pure. :func:`run_move_section_to` runs the two-question flow
with the choosers passed in, so QUILL and QUILL Lite share the flow, the rules
and the wording and differ only in which dialog they draw.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from quill.core.section_tree import (
    HTML_HEADING_PATTERN,
    parse_heading_blocks,
    section_for_caret,
    sibling_position,
    subtree_end,
)

__all__ = [
    "PLACEMENTS",
    "MoveToOutcome",
    "MoveToStatus",
    "MoveTarget",
    "move_section_to",
    "move_targets",
    "placement_choices",
    "run_move_section_to",
]

#: The three answers to "where, relative to that heading?", in the order they
#: are offered. ``before`` and ``after`` keep the moved section's level;
#: ``inside`` is the only one that changes it, and the only one that can be
#: refused for depth.
PLACEMENTS: tuple[str, ...] = ("before", "after", "inside")

_MAX_LEVEL = 6


@dataclass(frozen=True, slots=True)
class MoveTarget:
    """One heading a section could be moved to, as the row a person reads.

    ``label`` is the whole row and the only thing the dialog shows, because a
    listener gets one pass at it. It leads with the position rather than the
    title so that two sections called "Notes" are two different rows instead of
    a coin toss, and it names the level because "before Bread" means something
    different depending on whether Bread is a chapter or a paragraph heading.
    """

    #: Index into :func:`~quill.core.section_tree.parse_heading_blocks`.
    index: int
    level: int
    title: str
    #: 1-based position among *all* headings in the document, and their count.
    ordinal: int
    total: int
    #: True for the section the caret is in, and for anything inside it --
    #: the rows that will be refused. Kept as a row rather than filtered out
    #: so that searching for a heading you can see finds it and explains
    #: itself, instead of returning nothing and looking broken.
    blocked: bool = False

    @property
    def label(self) -> str:
        name = (self.title or "").strip() or "(untitled)"
        row = f"{self.ordinal} of {self.total}, level {self.level} - {name}"
        return f"{row} (the section you are moving)" if self.blocked else row


class MoveToStatus(StrEnum):
    OK = "ok"
    #: The caret is not in a section, so there is nothing to move.
    NO_SECTION = "no_section"
    #: One heading in the whole document: nowhere to move it to.
    ONLY_SECTION = "only_section"
    #: Somebody backed out of one of the two questions.
    CANCELLED = "cancelled"
    #: The chosen heading is the moving section itself, or inside it.
    INSIDE_SELF = "inside_self"
    #: "Inside" would push a heading past level 6, which Markdown cannot write.
    TOO_DEEP = "too_deep"


@dataclass(frozen=True, slots=True)
class MoveToOutcome:
    """The new document, or the unchanged one and the reason why."""

    text: str
    caret: int
    status: MoveToStatus
    announce: str

    @property
    def moved(self) -> bool:
        return self.status is MoveToStatus.OK


def placement_choices() -> list[tuple[str, str]]:
    """``(value, label)`` for the second question, in offer order.

    Each label says what will happen to the document, not what the word means.
    "After" is the one people get wrong -- it puts the section past everything
    under the chosen heading, not between that heading and its first child --
    and "Inside" is the one that costs a level, so both say so on the row
    rather than in a help string nobody will open mid-operation.
    """
    return [
        ("before", "Before it - just above that heading"),
        ("after", "After it - below that heading and everything under it"),
        ("inside", "Inside it - the last section under that heading (changes the level)"),
    ]


def move_targets(text: str, caret: int, *, markup_kind: str = "markdown") -> list[MoveTarget]:
    """Every heading in the document, as rows for the first question.

    Including the ones that cannot be used. A row that is present and explains
    why it is refused is findable by search and teaches the rule; a row that has
    been filtered out is a heading somebody can see in their document, cannot
    find in the list, and has no way to ask about.
    """
    if markup_kind not in {"markdown", "html"}:
        return []
    blocks = parse_heading_blocks(text, markup_kind)
    if len(blocks) < 2:
        return []
    found = section_for_caret(blocks, caret)
    if found is None:
        return []
    source_index = found[0]
    source_end = subtree_end(blocks, source_index, len(text))
    total = len(blocks)
    targets: list[MoveTarget] = []
    for index, block in enumerate(blocks):
        blocked = index == source_index or (
            index > source_index and block.section_start < source_end
        )
        targets.append(
            MoveTarget(
                index=index,
                level=block.level,
                title=block.title,
                ordinal=index + 1,
                total=total,
                blocked=blocked,
            )
        )
    return targets


def move_section_to(
    text: str,
    caret: int,
    target_index: int,
    placement: str,
    *,
    markup_kind: str = "markdown",
) -> MoveToOutcome:
    """Move the section at ``caret`` to ``placement`` of ``blocks[target_index]``.

    The moved span is the heading plus everything under it -- exactly what
    :func:`~quill.core.markdown_sections.move_section` moves, so the two
    commands cannot disagree about what a section is.
    """
    if markup_kind not in {"markdown", "html"}:
        return MoveToOutcome(text, caret, MoveToStatus.NO_SECTION, _NOT_HERE)
    blocks = parse_heading_blocks(text, markup_kind)
    if not blocks:
        return MoveToOutcome(text, caret, MoveToStatus.NO_SECTION, _NOT_HERE)
    if len(blocks) < 2:
        return MoveToOutcome(
            text,
            caret,
            MoveToStatus.ONLY_SECTION,
            "This document has only one section, so there is nowhere to move it to.",
        )
    found = section_for_caret(blocks, caret)
    if found is None:
        return MoveToOutcome(text, caret, MoveToStatus.NO_SECTION, _NOT_HERE)
    source_index, source_level, source_start, _own_end = found
    source_end = subtree_end(blocks, source_index, len(text))
    if not 0 <= target_index < len(blocks):
        return MoveToOutcome(text, caret, MoveToStatus.NO_SECTION, _NOT_HERE)

    anchor = blocks[target_index]
    source_name = _name(blocks[source_index].title)
    anchor_name = _name(anchor.title)
    if target_index == source_index:
        return MoveToOutcome(
            text,
            caret,
            MoveToStatus.INSIDE_SELF,
            f"{anchor_name} is the section you are moving, so it cannot be its own destination.",
        )
    if target_index > source_index and anchor.section_start < source_end:
        return MoveToOutcome(
            text,
            caret,
            MoveToStatus.INSIDE_SELF,
            f"{anchor_name} is inside {source_name}, so {source_name} cannot move into it. "
            f"Promote {anchor_name} first if you want them side by side.",
        )

    placement = placement if placement in PLACEMENTS else "after"
    if placement == "inside":
        new_level = anchor.level + 1
        delta = new_level - source_level
        deepest = max(
            block.level
            for block in blocks
            if block.section_start >= source_start and block.section_start < source_end
        )
        if deepest + delta > _MAX_LEVEL:
            return MoveToOutcome(
                text,
                caret,
                MoveToStatus.TOO_DEEP,
                f"Putting {source_name} inside {anchor_name} would need a heading "
                f"below level {_MAX_LEVEL}, which Markdown cannot write. "
                f"Promote {source_name} first, or choose After instead.",
            )
    else:
        delta = 0

    destination = (
        anchor.section_start
        if placement == "before"
        else subtree_end(blocks, target_index, len(text))
    )
    body = text[source_start:source_end].rstrip("\n")
    if delta:
        body = _shift_levels(body, delta, markup_kind)

    new_text, insert_at = _relocate(text, source_start, source_end, destination, body)
    column = min(max(0, caret - source_start), _first_line_length(body))
    new_caret = insert_at + column
    return MoveToOutcome(
        new_text,
        new_caret,
        MoveToStatus.OK,
        _announce_move(
            new_text, new_caret, markup_kind, source_name, anchor_name, placement, delta
        ),
    )


def run_move_section_to(
    text: str,
    caret: int,
    *,
    markup_kind: str = "markdown",
    choose_heading: Callable[[list[MoveTarget]], MoveTarget | None],
    choose_placement: Callable[[list[tuple[str, str]]], str | None],
) -> MoveToOutcome:
    """Ask the two questions and apply the answer. The flow, shared by both editors.

    The choosers are injected rather than imported because they are the only
    part that differs: QUILL draws its searchable picker, QUILL Lite draws
    QUILL Lite's, and both are already built, already keyboard-tested and already
    in the dialog inventory. Everything that decides what the rows say, what is
    refused, what the edit is and what gets announced happens here, once.

    Either chooser may answer ``None`` for "never mind", and a cancel says
    nothing: nothing changed, and the reader announces the caret arriving back
    in the document. That is GATE-13 -- speaking after Escape is announcing our
    own housekeeping at somebody.
    """
    targets = move_targets(text, caret, markup_kind=markup_kind)
    if not targets:
        known = markup_kind in {"markdown", "html"}
        blocks = parse_heading_blocks(text, markup_kind) if known else []
        if len(blocks) == 1:
            return MoveToOutcome(
                text,
                caret,
                MoveToStatus.ONLY_SECTION,
                "This document has only one section, so there is nowhere to move it to.",
            )
        return MoveToOutcome(text, caret, MoveToStatus.NO_SECTION, _NOT_HERE)
    chosen = choose_heading(targets)
    if chosen is None:
        return MoveToOutcome(text, caret, MoveToStatus.CANCELLED, "")
    placement = choose_placement(placement_choices())
    if placement is None:
        return MoveToOutcome(text, caret, MoveToStatus.CANCELLED, "")
    return move_section_to(text, caret, chosen.index, placement, markup_kind=markup_kind)


# --------------------------------------------------------------------------- #
# The edit
# --------------------------------------------------------------------------- #


def _relocate(text: str, start: int, end: int, destination: int, body: str) -> tuple[str, int]:
    """Cut ``[start, end)`` out of ``text`` and put ``body`` in at ``destination``.

    Returns the new document and where ``body`` actually landed, so the caller
    can put the caret on the moved heading without searching for it -- searching
    would find the wrong one in a document with two headings of the same name.

    **Blank lines belong to the slot, not to the section**, the same rule
    :func:`~quill.core.section_tree.swap_sections` follows and for the same
    reason. Sections do not all end the same way: the last one in a file
    typically ends with a single newline and every earlier one with a blank
    line. Carrying a terminator along with the text jams two headings onto
    consecutive lines at one end of the move and leaves a stray blank line at
    the other, so each seam is closed to exactly one blank line and the end of
    the file keeps the ending it had.
    """
    tail = text[end:]
    remainder = text[:start] + tail
    if not tail:
        # The moved section was last, so the document now ends with whatever
        # separated it from the one before. Restore the ending the file had.
        ending = text[len(text.rstrip("\n")) :]
        remainder = remainder.rstrip("\n") + ending
        if destination > start:
            destination = len(remainder)
    if destination >= end:
        destination -= end - start
    destination = max(0, min(destination, len(remainder)))

    before = remainder[:destination]
    after = remainder[destination:]
    if not after:
        ending = remainder[len(remainder.rstrip("\n")) :] or "\n"
        head = before.rstrip("\n")
        joiner = "\n\n" if head else ""
        return head + joiner + body + ending, len(head) + len(joiner)
    head = before.rstrip("\n")
    joiner = "\n\n" if head else ""
    return head + joiner + body + "\n\n" + after, len(head) + len(joiner)


def _shift_levels(body: str, delta: int, markup_kind: str) -> str:
    """Renumber every heading in ``body`` by ``delta``, deepest-safe.

    Back to front, so that rewriting one heading cannot move the offsets of the
    ones still to be rewritten. The caller has already checked that no heading
    ends up past level 6, so the clamp here is belt and braces rather than
    policy -- a silent clamp would flatten two levels into one and change the
    shape of the outline without saying so.
    """
    blocks = parse_heading_blocks(body, markup_kind)
    out = body
    for block in reversed(blocks):
        level = max(1, min(_MAX_LEVEL, block.level + delta))
        if level == block.level:
            continue
        span = out[block.start : block.end]
        if markup_kind == "markdown":
            replacement = "#" * level + span[block.level :]
        else:
            replacement = HTML_HEADING_PATTERN.sub(_html_relevel(level), span, count=1)
        out = out[: block.start] + replacement + out[block.end :]
    return out


def _html_relevel(level: int) -> Callable[[re.Match[str]], str]:
    """A substitution that rewrites one ``<hN>...</hN>`` pair to *level*.

    A named factory rather than a lambda with a default argument: the default
    was the only way to capture the loop variable, and it also made the
    callable's signature a lie to anything reading it.
    """

    def rewrite(match: re.Match[str]) -> str:
        return f"<h{level}{match.group('attrs')}>{match.group('body')}</h{level}>"

    return rewrite


def _first_line_length(body: str) -> int:
    newline = body.find("\n")
    return len(body) if newline == -1 else newline


# --------------------------------------------------------------------------- #
# The sentence
# --------------------------------------------------------------------------- #

_NOT_HERE = "Put the cursor in a section to move it"


def _name(title: str) -> str:
    return (title or "").strip() or "this section"


def _announce_move(
    new_text: str,
    new_caret: int,
    markup_kind: str,
    source_name: str,
    anchor_name: str,
    placement: str,
    delta: int,
) -> str:
    """One sentence: what moved, where it went, what it is now, and where it sits.

    The last clause is the half a listener cannot get any other way. The reader
    says the text changed; it never says that this section is now the second of
    three at its level, which is exactly what a sighted person reads off the
    page -- and what you need before deciding whether you are finished.

    The level clause only appears when the level actually changed, because
    "still Heading 2" is a sentence about our implementation. When it did
    change, saying so is not optional: Inside is the one placement that edits
    more than the order, and an unannounced renumbering is a silent edit.
    """
    blocks = parse_heading_blocks(new_text, markup_kind)
    found = section_for_caret(blocks, new_caret) if blocks else None
    sentence = f"Moved {source_name} {placement} {anchor_name}"
    if delta and found is not None:
        sentence = f"{sentence}, now Heading {blocks[found[0]].level}"
    if found is None:
        return sentence
    ordinal, total = sibling_position(blocks, found[0])
    if total <= 1:
        return sentence
    return f"{sentence}. Now {ordinal} of {total} at this level"
