"""The Heading Organizer: every heading in one list, reordered with arrow keys.

Promote, demote, move a whole section up or down, rename, and check the result
against the accessibility rules for heading order -- in one window, where the
alternative is four separate commands and no way to see what you have done.

For somebody who listens, that difference is not cosmetic. Restructuring a
document with four commands means holding the shape of the document in your head
while you work on it, because nothing reads it back; here the list *is* the
shape, and every change re-reads it.

**Extracted from ``main_frame.py`` on 2026-09-17 so QuillLite can have it**
(bad.md P2.13, Tier 2). QuillLite already lists headings and already moves
sections; the organizer is those two combined, and the rule is that a
capability which is editor-core, already shared, worth a listener's time and
switchable off belongs in both (bad.md 4.2). Sharing it also took 260 lines out
of the largest module in the tree.

The host supplies what it alone knows -- the markup kind, the text, how to open
a modal, how to say something -- and gets back the new text or ``None``. It owns
neither the dialog nor the rules.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import wx

from quill.core.markdown_sections import (
    HeadingBlock,
    apply_heading_organizer_edits,
    parse_heading_blocks,
    validate_heading_sequence,
)
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_message_box, show_modal_dialog

__all__ = ["ORGANIZER_KINDS", "organize_headings", "organize_rich_headings"]

#: The document kinds that have a heading *syntax* to rewrite. Rich text is
#: excluded deliberately: its headings are point sizes on runs, and reordering
#: them means moving formatted ranges rather than lines -- a different job, and
#: one the outline already answers well enough to not need this.
ORGANIZER_KINDS = frozenset({"markdown", "html"})


def organize_headings(
    parent: Any,
    *,
    markup_kind: str,
    text: str,
    say: Callable[[str], None],
    show_modal: Callable[[Any, str], int] = show_modal_dialog,
    warn_duplicate_h1: bool = False,
) -> str | None:
    """Open the organizer over *text*. Returns the new text, or ``None``.

    ``None`` covers every case where nothing should change: the wrong kind of
    document, no headings, a cancelled dialog, and a dialog closed without
    having altered anything. Each says which, because a window that opens and
    closes with no sentence is indistinguishable from one that failed.
    """
    if markup_kind not in ORGANIZER_KINDS:
        say("Heading Organizer is only available for Markdown or HTML documents")
        return None
    headings = parse_heading_blocks(text, markup_kind)
    if not headings:
        say("No headings found for Heading Organizer")
        return None
    updated = _show_dialog(
        parent,
        headings=headings,
        source_text=text,
        show_modal=show_modal,
        say=say,
        warn_duplicate_h1=warn_duplicate_h1,
    )
    if updated is None:
        say("Heading Organizer cancelled")
        return None
    transformed = apply_heading_organizer_edits(text, markup_kind, updated)
    if transformed == text:
        say("Heading Organizer closed without changes")
        return None
    return transformed


def organize_rich_headings(
    parent: Any,
    *,
    wrapper: Any,
    text: str,
    say: Callable[[str], None],
    show_modal: Callable[[Any, str], int] = show_modal_dialog,
    warn_duplicate_h1: bool = False,
) -> bool:
    """The organizer over a rich text document. ``True`` if the document changed.

    The same window as :func:`organize_headings`, over the same blocks, with the
    same promote, demote, reorder and rename -- only the two ends differ. The
    headings come from the control's own point-size ladder rather than from
    parsing markers out of a string, and the edits go back through formatted
    range moves rather than a rewritten string, so a section keeps its sizes and
    weights on the way (:mod:`quill.ui.heading_organizer_rich`).

    Sharing the dialog is the point. A rich-text organizer written separately
    would be a second set of keys to learn and a second place for the
    duplicate-Heading-1 rule to drift.
    """
    from quill.ui.heading_organizer_rich import (
        apply_rich_organizer_edits,
        rich_heading_blocks,
        unchanged,
    )

    headings = wrapper.all_headings()
    if not headings:
        say("No headings found for Heading Organizer")
        return False
    blocks = rich_heading_blocks(text, headings)
    updated = _show_dialog(
        parent,
        headings=blocks,
        source_text=text,
        show_modal=show_modal,
        say=say,
        warn_duplicate_h1=warn_duplicate_h1,
    )
    if updated is None:
        say("Heading Organizer cancelled")
        return False
    if unchanged(blocks, updated):
        say("Heading Organizer closed without changes")
        return False
    return bool(apply_rich_organizer_edits(wrapper, blocks, updated))


def _show_dialog(
    parent: Any,
    *,
    headings: list[HeadingBlock],
    source_text: str,
    show_modal: Callable[[Any, str], int] = show_modal_dialog,
    say: Callable[[str], None],
    warn_duplicate_h1: bool,
) -> list[HeadingBlock] | None:
    """Build the window and run it. The default *show_modal* is the shared one.

    A parameter rather than a hard call because QUILL passes ``MainFrame``'s own
    ``_show_modal_dialog``, which adds the z-order and region handling a frame
    with a status bar and a notebook needs. QuillLite has no such wrapper and
    wants exactly the default, which is why it is the default rather than
    something every caller has to remember to pass.
    """
    dialog = wx.Dialog(
        parent,
        title="Heading Organizer",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        size=(920, 620),
    )
    working = [replace(heading) for heading in headings]
    originals = {heading.source_index: heading for heading in headings}
    selected_index = 0

    list_box = wx.ListBox(dialog)
    set_accessible_name(list_box, "Headings")
    list_box.SetHelpText(
        "Every heading in the document, in the order it appears. Arrow through "
        "them; Tab demotes the one you are on and Shift+Tab promotes it."
    )
    preview = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
    set_accessible_name(preview, "Heading preview")
    preview.SetHelpText(
        "The section under the heading you are on, so you can tell two "
        "similarly named headings apart before moving either."
    )
    instructions = wx.StaticText(
        dialog,
        label=(
            "Arrow through headings. Tab demotes, Shift+Tab promotes. "
            "Use Move Up/Down to reorder sections and Rename to edit heading text."
        ),
    )
    promote_button = wx.Button(dialog, label="&Promote")
    promote_button.SetHelpText(
        "Make this heading one level shallower: Heading 3 becomes Heading 2."
    )
    demote_button = wx.Button(dialog, label="&Demote")
    demote_button.SetHelpText("Make this heading one level deeper: Heading 2 becomes Heading 3.")
    move_up_button = wx.Button(dialog, label="Move &Up")
    move_up_button.SetHelpText("Move this heading and everything under it above the one before it.")
    move_down_button = wx.Button(dialog, label="Move Do&wn")
    move_down_button.SetHelpText("Move this heading and everything under it below the next one.")
    rename_button = wx.Button(dialog, label="&Rename...")
    rename_button.SetHelpText("Change the wording of this heading without moving it.")
    validate_button = wx.Button(dialog, label="&Validate")
    validate_button.SetHelpText(
        "Check the heading order against the accessibility rules: it must start "
        "at Heading 1 and must not skip a level on the way down."
    )
    apply_button = wx.Button(dialog, id=wx.ID_OK, label="Apply")
    cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")

    def labels() -> list[str]:
        return [f"Heading {entry.level}: {entry.title or '(empty heading)'}" for entry in working]

    def refresh() -> None:
        nonlocal selected_index
        list_box.Set(labels())
        if not working:
            preview.ChangeValue("No headings found.")
            return
        selected_index = max(0, min(selected_index, len(working) - 1))
        list_box.SetSelection(selected_index)
        update_preview()

    def selected() -> HeadingBlock | None:
        if not working:
            return None
        current = list_box.GetSelection()
        if current == wx.NOT_FOUND:
            return None
        return working[current]

    def set_selected(entry: HeadingBlock) -> None:
        nonlocal selected_index
        current = list_box.GetSelection()
        if current == wx.NOT_FOUND:
            return
        working[current] = entry
        selected_index = current
        refresh()

    def update_preview() -> None:
        entry = selected()
        if entry is None:
            preview.ChangeValue("No heading selected.")
            return
        origin = originals.get(entry.source_index)
        if origin is None:
            preview.ChangeValue(entry.title)
            return
        section = source_text[origin.section_start : origin.section_end].strip()
        preview.ChangeValue(section or entry.title)

    def promote() -> None:
        entry = selected()
        if entry is None:
            return
        if entry.level <= 1:
            say("Heading already at level 1")
            return
        set_selected(replace(entry, level=entry.level - 1))
        say(f"{entry.title or '(empty heading)'} is now Heading {entry.level - 1}")

    def demote() -> None:
        entry = selected()
        if entry is None:
            return
        if entry.level >= 6:
            say("Heading already at level 6")
            return
        set_selected(replace(entry, level=entry.level + 1))
        say(f"{entry.title or '(empty heading)'} is now Heading {entry.level + 1}")

    def move(delta: int) -> None:
        nonlocal selected_index
        current = list_box.GetSelection()
        if current == wx.NOT_FOUND:
            return
        target = current + delta
        if target < 0 or target >= len(working):
            say("Already at the end" if delta > 0 else "Already at the start")
            return
        working[current], working[target] = working[target], working[current]
        selected_index = target
        refresh()
        entry = working[target]
        say(f"Moved {entry.title or '(empty heading)'} to position {target + 1} of {len(working)}")

    def rename() -> None:
        entry = selected()
        if entry is None:
            return
        with wx.TextEntryDialog(
            dialog,
            "Enter heading text:",
            "Rename Heading",
            value=entry.title,
        ) as rename_dialog:
            if show_modal(rename_dialog, "Rename Heading") != wx.ID_OK:
                return
            new_title = rename_dialog.GetValue().strip()
        set_selected(replace(entry, title=new_title))
        say(f"Renamed to {new_title or '(empty heading)'}")

    def validate(show_success: bool = False) -> bool:
        # #303: the duplicate-H1 warning is opt-in. The default keeps the
        # historical behaviour -- only "must start at H1" and "skipped level"
        # fire -- so somebody who deliberately writes a multi-H1 work is not
        # interrupted by a rule they do not hold themselves to.
        issues = validate_heading_sequence(working, require_single_h1=warn_duplicate_h1)
        if not issues:
            if show_success:
                show_message_box(
                    "Heading order passed accessibility checks.",
                    "Heading Organizer",
                    wx.OK | wx.ICON_INFORMATION,
                    dialog,
                )
            return True
        show_message_box(
            "Fix these heading issues before applying:\n\n"
            + "\n".join(f"- {issue}" for issue in issues),
            "Heading Organizer",
            wx.OK | wx.ICON_WARNING,
            dialog,
        )
        return False

    def on_key(event: Any) -> None:
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_TAB:
            if event.ShiftDown():
                promote()
            else:
                demote()
            return
        if key_code in (wx.WXK_ADD, wx.WXK_NUMPAD_ADD):
            demote()
            return
        if key_code in (wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT):
            promote()
            return
        event.Skip()

    body = wx.BoxSizer(wx.HORIZONTAL)
    main = wx.BoxSizer(wx.VERTICAL)
    main.Add(instructions, 0, wx.ALL | wx.EXPAND, 8)
    main.Add(list_box, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
    main.Add(
        wx.StaticText(dialog, label="Preview of selected heading section:"),
        0,
        wx.LEFT | wx.RIGHT,
        8,
    )
    main.Add(preview, 1, wx.ALL | wx.EXPAND, 8)
    actions = wx.BoxSizer(wx.VERTICAL)
    actions.Add(promote_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.Add(demote_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.Add(move_up_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.Add(move_down_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.Add(rename_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.Add(validate_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.AddStretchSpacer(1)
    actions.Add(apply_button, 0, wx.EXPAND | wx.BOTTOM, 6)
    actions.Add(cancel_button, 0, wx.EXPAND)
    body.Add(main, 1, wx.EXPAND)
    body.Add(actions, 0, wx.ALL | wx.EXPAND, 8)
    dialog.SetSizer(body)

    list_box.Bind(wx.EVT_LISTBOX, lambda _e: update_preview())
    list_box.Bind(wx.EVT_CHAR_HOOK, on_key)
    promote_button.Bind(wx.EVT_BUTTON, lambda _e: promote())
    demote_button.Bind(wx.EVT_BUTTON, lambda _e: demote())
    move_up_button.Bind(wx.EVT_BUTTON, lambda _e: move(-1))
    move_down_button.Bind(wx.EVT_BUTTON, lambda _e: move(1))
    rename_button.Bind(wx.EVT_BUTTON, lambda _e: rename())
    validate_button.Bind(wx.EVT_BUTTON, lambda _e: validate(show_success=True))
    apply_button.Bind(
        wx.EVT_BUTTON,
        lambda _e: dialog.EndModal(wx.ID_OK) if validate() else None,
    )
    cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

    refresh()
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    try:
        if show_modal(dialog, "Heading Organizer") != wx.ID_OK:
            return None
        return working
    finally:
        # Destroyed here rather than left to the garbage collector. Inside
        # main_frame.py this dialog was never destroyed at all -- the cost of a
        # leak in a window opened a few times a session is invisible, which is
        # exactly why it had gone unnoticed, and the gate catches it now that
        # the surface is a module of its own (A11Y-4).
        dialog.Destroy()
