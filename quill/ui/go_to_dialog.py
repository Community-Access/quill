"""One Go To dialog, with a target kind -- Word's shape, and the family's.

``Ctrl+G`` has meant "go to line" in Notepad since Windows 3.1 and "go to
anything -- a line, a page, a bookmark, a heading" in Word for almost as long.
QuillLite had the Notepad half and reached bookmarks and headings through two
other commands on two other chords; QUILL had Go To Line and Go To Page as
separate commands and its bookmarks under a third. Three surfaces for one verb
is three places to look and three things to learn (bad.md 5.4, P1.6, P2.3).

Shared, so both editors open the same window. The host supplies the targets it
has -- QuillLite has no pagination, so it offers no Page kind, and the radio box
shows only the kinds it was given rather than a greyed row for a thing this
product does not do.

**A radio box rather than a drop-down**, and the reason is a listener's: a
``wx.Choice`` announces the kind you land on and nothing else, so finding out
what the alternatives are means opening it, and *changing* it means opening it
again. Arrow keys walk a radio box and every stop says its own name. The number
field and the list are both present the whole time and the irrelevant one is
disabled, which announces itself as unavailable -- a control that vanished would
leave somebody hunting a window that has changed shape underneath them (the same
rule the two tag pickers follow).
"""

from __future__ import annotations

from dataclasses import dataclass

import wx

from quill.ui.dialog_contract import (
    apply_modal_ids,
    set_accessible_name,
    show_modal_dialog,
)

__all__ = ["GoToResult", "GoToTarget", "ask_go_to"]

#: Uniform padding, matching the dialogs this one sits beside.
_PAD = 8


@dataclass(frozen=True, slots=True)
class GoToTarget:
    """One place the dialog can offer: a label to read, and where it is."""

    #: What the row says. Led by the thing that identifies it -- "3, Installing"
    #: rather than "Installing (bookmark 3)" -- so a listener can pick it out of
    #: a list by its first word (bad.md 5.2).
    label: str
    #: The character offset to land on.
    position: int


@dataclass(frozen=True, slots=True)
class GoToResult:
    """What the user asked for: a line number, or a position."""

    #: 1-based, when the Line kind was chosen. ``None`` otherwise.
    line: int | None = None
    #: A character offset, when a bookmark or a heading was chosen.
    position: int | None = None


def ask_go_to(
    parent: wx.Window,
    *,
    line: int,
    last_line: int,
    kinds: dict[str, list[GoToTarget]],
) -> GoToResult | None:
    """Ask where to go. Returns the answer, or ``None`` on Escape.

    *kinds* maps a kind's name -- "Bookmark", "Heading", "Page" -- to the
    targets under it. A kind with no targets is still offered and says so when
    chosen: "no headings in this document" is a fact worth hearing, and a radio
    box whose rows come and go with the document is one whose shape nobody can
    learn. Line is always first and always present.
    """
    dialog = wx.Dialog(parent, title="Go To", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)

    names = ["Line", *kinds]
    kind_box = wx.RadioBox(dialog, label="Go to a:", choices=names, majorDimension=1)
    kind_box.SetHelpText(
        "What to go to. Line asks for a number; the others offer a list of the "
        "places in this document. Arrow between them and the window below "
        "follows."
    )
    root.Add(kind_box, 0, wx.EXPAND | wx.ALL, _PAD)

    line_label = wx.StaticText(dialog, label=f"Line &number (1 to {last_line}):")
    line_field = wx.TextCtrl(dialog, value=str(line), style=wx.TE_PROCESS_ENTER)
    set_accessible_name(line_field, f"Line number, 1 to {last_line}")
    line_field.SetHelpText(
        "Type a line number and press Enter. Past the end of the document takes "
        "you to the last line rather than refusing."
    )
    root.Add(line_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    root.Add(line_field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    list_label = wx.StaticText(dialog, label="&Places:")
    places = wx.ListBox(dialog, choices=[], style=wx.LB_SINGLE)
    set_accessible_name(places, "Places")
    places.SetHelpText(
        "The bookmarks or headings in this document, in the order they appear. "
        "Choose one and press Enter to go there."
    )
    root.Add(list_label, 0, wx.LEFT | wx.RIGHT, _PAD)
    root.Add(places, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    root.Add(dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((480, 420))

    def _chosen_kind() -> str:
        return names[max(0, kind_box.GetSelection())]

    def _sync() -> None:
        """Show the control the chosen kind needs, and disable the other.

        Disabled rather than hidden: a control a reader can still reach and that
        announces itself as unavailable is a window whose shape stays the same,
        and one that vanished would leave somebody Tabbing through a layout that
        had moved under them.
        """
        kind = _chosen_kind()
        on_line = kind == "Line"
        line_field.Enable(on_line)
        places.Enable(not on_line)
        if on_line:
            places.Set([])
            line_field.SetFocus()
            line_field.SelectAll()
            return
        targets = kinds.get(kind, [])
        places.Set([target.label for target in targets])
        if targets:
            places.SetSelection(0)
            places.SetFocus()

    def _on_kind(_event: wx.CommandEvent) -> None:
        _sync()

    kind_box.Bind(wx.EVT_RADIOBOX, _on_kind)
    line_field.Bind(wx.EVT_TEXT_ENTER, lambda _e: dialog.EndModal(wx.ID_OK))
    places.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: dialog.EndModal(wx.ID_OK))

    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    _sync()
    kind_box.SetFocus()
    line_field.SetFocus()
    line_field.SelectAll()
    try:
        if show_modal_dialog(dialog, "Go To") != wx.ID_OK:
            return None
        kind = _chosen_kind()
        if kind == "Line":
            try:
                wanted = int(line_field.GetValue().strip())
            except ValueError:
                return None
            return GoToResult(line=max(1, min(last_line, wanted)))
        index = places.GetSelection()
        targets = kinds.get(kind, [])
        if index == wx.NOT_FOUND or not 0 <= index < len(targets):
            return None
        return GoToResult(position=targets[index].position)
    finally:
        dialog.Destroy()
