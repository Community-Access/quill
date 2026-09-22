"""Which document kinds each formatting command means anything in.

Reported while testing: "if in plain text mode, shouldn't the Format menu go
away?" Sixteen of the twenty-one formatting commands could only refuse in a
plain text document, and every one of their rows was enabled and advertising a
key. For somebody reading the menu with a screen reader that is twenty rows to
arrow past, each of which promises a shortcut, and pressing any of them answers
"this document has no formatting".

Dimmed rather than removed, for three reasons. The menu bar's *shape* is what a
listener navigates by, and a menu that appears and disappears between documents
is re-learned every time. Windows dims what does not apply, QuillLite already
dims two rows this way, and the project's menu rule exempts disabled items from
having to advertise a key -- so dimming is the sanctioned answer rather than a
special case. And the Format menu of a plain document still has to hold
**Switch Document Mode** and **Document Language**: they are the way to make
everything else live, and removing the menu would remove the only signpost to
them.

The table is the risk, so it is gated. A row dimmed when the command would have
worked is a feature taken away, and a row live when the command can only refuse
is the bug this fixes coming back -- so
``tests/unit/apps/test_lite_format_gating.py`` runs every command in every kind
and asserts the table agrees with what actually happens. The table is a claim;
the test is what makes it true.

``RICH`` is the *mode* and the other three are markup *languages*, which is a
distinction the editor keeps everywhere: a Markdown document and a plain text
one are both plain to the control, and only one of them has headings.
"""

from __future__ import annotations

__all__ = ["ALL_KINDS", "FORMAT_COMMAND_KINDS", "applies_to"]

#: Rich text, where formatting is real, plus the three markup languages.
ALL_KINDS: frozenset[str] = frozenset({"plain", "markdown", "html", "rich"})

#: Everything a markup document can express, which is emphasis and headings.
#: Not alignment, not spacing, not a font size -- Markdown has no way to say
#: any of those, so offering them would be offering nothing.
_MARKUP = frozenset({"markdown", "html", "rich"})

#: Rich text only: these are real character and paragraph properties, and there
#: is no markup spelling of them to fall back to.
_RICH = frozenset({"rich"})

FORMAT_COMMAND_KINDS: dict[str, frozenset[str]] = {
    # Emphasis: asterisks, a <strong>, or real bold.
    "cmd_bold": _MARKUP,
    "cmd_italic": _MARKUP,
    "cmd_underline": _MARKUP,
    # Headings: hashes, an <h2>, or the point-size ladder.
    "cmd_heading_0": _MARKUP,
    "cmd_heading_1": _MARKUP,
    "cmd_heading_2": _MARKUP,
    "cmd_heading_3": _MARKUP,
    "cmd_heading_4": _MARKUP,
    "cmd_heading_5": _MARKUP,
    "cmd_heading_6": _MARKUP,
    "cmd_normal_text": _MARKUP,
    # Structure, which is headings by another name: a document with no headings
    # has no sections to promote, demote or move.
    "cmd_promote_heading": _MARKUP,
    "cmd_demote_heading": _MARKUP,
    "cmd_move_section_up": _MARKUP,
    "cmd_move_section_down": _MARKUP,
    # Rich text too, since 2026-09-22. It used to refuse there and the report
    # was one sentence long -- "it should work there" -- and correct: a rich
    # document has headings, ``all_headings`` already lists them, and the only
    # thing missing was a way to move a *formatted* range rather than a line
    # (:mod:`quill.ui.heading_organizer_rich`).
    "cmd_heading_organizer": _MARKUP,
    # Lists: a bullet is a character in Markdown and a paragraph property in
    # rich text. HTML is deliberately absent -- the cycle has no HTML spelling,
    # which is measured rather than assumed (see the gating test).
    "cmd_cycle_list_style": frozenset({"markdown", "rich"}),
    # Real character and paragraph properties, rich text only.
    "cmd_grow_font": _RICH,
    "cmd_shrink_font": _RICH,
    "cmd_selection_font": _RICH,
    "cmd_align_left": _RICH,
    "cmd_align_center": _RICH,
    "cmd_align_right": _RICH,
    "cmd_align_justify": _RICH,
    "cmd_spacing_single": _RICH,
    "cmd_spacing_one_half": _RICH,
    "cmd_spacing_double": _RICH,
    # Always live, and the last two are why the menu stays: Editor Font is the
    # *editor's* face rather than the document's, Describe Formatting answers
    # for whatever is there including nothing, and these two are how a plain
    # document becomes one of the others.
    "cmd_editor_font": ALL_KINDS,
    "cmd_describe": ALL_KINDS,
    "cmd_switch_document_kind": ALL_KINDS,
    "cmd_set_language": ALL_KINDS,
}


def applies_to(handler: str, kind: str) -> bool:
    """Whether *handler* does anything in a document of *kind*.

    An unlisted handler applies everywhere: the table names what is *limited*,
    so a command nobody has classified stays reachable rather than silently
    disappearing from a menu.
    """
    return kind in FORMAT_COMMAND_KINDS.get(handler, ALL_KINDS)
