"""What the two editors *say* about a section, composed exactly once.

The other half of the :mod:`quill.core.markdown_sections` extraction (GATE-11).
:mod:`quill.core.section_tree` works out the shape of the document; this module
turns that shape into the one sentence a screen reader reads out, and it is the
only place either editor is allowed to compose one.

That rule is not tidiness. QUILL and QuillLite each used to derive their own
wording for the same key, and the shorter of the two said less: "Soup" where
the other said "Section moved below Soup", and "No sibling to swap with" -- a
sentence about the implementation -- where the document plainly continued below.
Two wordings for one action is two things to keep true.

Everything here is a pure function from data to a finished sentence. Nothing
reads a setting, a keymap or a widget; the chord in a piece of advice is passed
in by the caller, which read it from that editor's own keymap, so rebinding the
key keeps the advice honest.
"""

from __future__ import annotations

from quill.core.section_tree import (
    MoveResult,
    SectionSelection,
    parse_heading_blocks,
    section_for_caret,
    sibling_position,
)

__all__ = [
    "announce_edge",
    "describe_move",
    "describe_section_selection",
]


def describe_section_selection(selection: SectionSelection) -> str:
    """What to say after selecting a section. One wording, both editors.

    Counts, because the screen reader will not give them: it announces that a
    selection changed, not how much of the document is now in it, and "did that
    take the sub-headings with it?" is the whole question at this moment. The
    title is here for the same reason -- the caret may have been in the body
    when the key was pressed, several screens below the heading it acted on.
    """
    name = (selection.title or "").strip() or "this section"
    lines = f"{selection.lines} line" if selection.lines == 1 else f"{selection.lines} lines"
    if selection.sections <= 1:
        return f"Selected {name}, {lines}"
    under = selection.sections - 1
    nested = f"{under} section under it" if under == 1 else f"{under} sections under it"
    return f"Selected {name} and {nested}, {lines}"


def announce_edge(
    result: MoveResult,
    sibling_title: str = "",
    parent_title: str = "",
    *,
    contained: str = "",
    promote_key: str = "",
) -> str:
    # The one refusal that earns a longer sentence: this section contains
    # everything below it, so no move is possible in that direction and saying
    # only "Bottom of X" leaves somebody pressing a key that can never work.
    # The chord is passed in rather than written here, because each editor
    # reads its own keymap and a refusal that names a key which does something
    # else is the same defect as no refusal at all.
    if result == MoveResult.BOTTOM and contained:
        edge = f"Bottom of {parent_title}." if parent_title else "Bottom!"
        advice = (
            f" {promote_key} promotes {contained} to make it a sibling."
            if promote_key
            else f" Promote {contained} to make it a sibling."
        )
        return f"{edge} Everything below is inside this section.{advice}"
    # "Top!" / "Bottom!" mean "this section is already first (or last) where it
    # sits".  Naming the parent is what makes that hearable: a sub-heading that
    # is the last child of its parent is at the bottom of *that parent*, not of
    # a document that plainly continues below it.
    if result == MoveResult.TOP:
        return f"Top of {parent_title}" if parent_title else "Top!"
    if result == MoveResult.BOTTOM:
        return f"Bottom of {parent_title}" if parent_title else "Bottom!"
    if result == MoveResult.NO_SECTION:
        return "No section to move"
    if sibling_title:
        return sibling_title
    return ""


def describe_move(new_text: str, new_caret: int, markup_kind: str, where: str, jumped: str) -> str:
    """The whole sentence for a move that happened, composed once for both
    editors: what it did, what it passed, and where it has landed.

    The last part is the half a listener cannot get any other way. The reader
    announces that the text changed; it never says that this section is now the
    second of three at its level, which is the thing a sighted person reads off
    the page and the thing you need before pressing the key again.
    """
    name = (jumped or "").strip()
    sentence = f"Section moved {where} {name}" if name else f"Section moved {where}"
    blocks = parse_heading_blocks(new_text, markup_kind)
    found = section_for_caret(blocks, new_caret) if blocks else None
    if found is None:
        return sentence
    ordinal, total = sibling_position(blocks, found[0])
    if total <= 1:
        return sentence
    return f"{sentence}. Now {ordinal} of {total} at this level"
