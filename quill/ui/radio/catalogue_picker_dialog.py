"""Choose from a catalogue: two lists, descriptions, and an order you keep.

Asked for on 2026-08-25 for ACB Media's podcasts: *"allow them to see a
listing of them, select the ones they want ... along with the descriptions of
each one ... Use two lists ... allow them to move them up and down so they can
organize the folder in the order they wish"*.

**Two lists, not checkboxes.** Checkboxes inside a wx list control are awkward
to build and unreliable with a screen reader, and the house pattern is settled:
choose from one list, Add, and curate a second with Move Up / Move Down /
Remove. The same shape the audiobook chapter editor uses.

**Source-agnostic on purpose.** The window is handed a title, a catalogue and
some words; it knows nothing about ACB, podcasts or streams. That is what lets
Community Picks (docs/design/community-picks.md) be a second menu item rather
than a second dialog -- and it means the accessibility work here is done once
for every catalogue that ever ships.

The ordering rule -- alphabetical until you move something, then exactly as you
left it -- is pure and lives in
:mod:`quill.core.podcasts.pick_list`, so it is tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.podcasts.pick_list import MANUAL, PickList
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, set_accessible_name


@dataclass(frozen=True, slots=True)
class PickableItem:
    """One row a catalogue offers. Whatever it stands for is the caller's."""

    #: Stable identity. Two items with the same key are the same pick, so a
    #: catalogue that renames a show does not offer it to you twice.
    key: str
    title: str
    description: str = ""
    #: A short parenthetical after the title -- "podcast", "station". Read out,
    #: so it earns its place only when a catalogue mixes kinds.
    kind: str = ""
    #: Already in the library. Shown, and refused, rather than hidden: "why is
    #: that one missing?" is a worse question than "you already have this".
    already_have: bool = False
    #: Anything the caller needs back. Never read here.
    payload: Any = None

    @property
    def label(self) -> str:
        parts = [self.title]
        if self.kind:
            parts.append(f"({self.kind})")
        if self.already_have:
            parts.append("-- already in your library")
        return " ".join(parts)


def choose_from_catalogue(
    host: Any,
    *,
    title: str,
    heading: str,
    items: list[PickableItem],
    chosen_label: str = "What you are adding",
) -> list[PickableItem] | None:
    """Show the picker. Returns the chosen items in order, or None on Cancel.

    An empty *items* is the caller's to explain before calling: a window that
    opens on nothing is a window that made somebody press a key to be told no.
    """
    import wx

    window = _CataloguePicker(host, wx, title, heading, items, chosen_label)
    return window.show()


class _CataloguePicker:
    def __init__(
        self,
        host: Any,
        wx: Any,
        title: str,
        heading: str,
        items: list[PickableItem],
        chosen_label: str,
    ) -> None:
        self._host = host
        self._wx = wx
        self._title = title
        self._heading = heading
        self._available = list(items)
        self._chosen_label = chosen_label
        self._picks = PickList(key=lambda item: item.key)
        self._result: list[PickableItem] | None = None

    # -- building ---------------------------------------------------------------

    def show(self) -> list[PickableItem] | None:
        """Build and show through the hardened modal path.

        One method because the dialog-hardening gate reads the scope that
        *constructs* the dialog for its accessible show path.
        """
        wx = self._wx
        self.dialog = wx.Dialog(
            self._host.frame, title=self._title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(wx.Size(900, 620))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(self.dialog, label=self._heading)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 8)

        columns = wx.BoxSizer(wx.HORIZONTAL)
        columns.Add(self._available_column(), 1, wx.EXPAND | wx.RIGHT, 8)
        columns.Add(self._transfer_column(), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        columns.Add(self._chosen_column(), 1, wx.EXPAND)
        root.Add(columns, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(self._buttons(), 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        # In show(), not in _buttons(): the dialog-hardening gate reads the
        # scope that CONSTRUCTS the dialog, and a contract wired one call away
        # is a contract it cannot see.
        apply_modal_ids(self.dialog, affirmative_id=self._ok_btn.GetId(), escape_id=self._cancel_id)

        self._fill_available()
        self._sync()
        self._wx.CallAfter(self._available_list.SetFocus)
        try:
            return self._host._show_modal_dialog(self.dialog, self._title) and self._result
        finally:
            self.dialog.Destroy()

    def _available_column(self) -> Any:
        wx = self._wx
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(self.dialog, label="&Available:"), 0, wx.BOTTOM, 4)
        self._available_list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        _help = (
            "Everything this catalogue offers, in alphabetical order. Arrow "
            "through it and the box below reads the description. Enter, or the "
            "Add button, moves the highlighted one into your list on the right."
        )
        self._available_list.SetName(_help)
        self._available_list.SetHelpText(_help)
        box.Add(self._available_list, 1, wx.EXPAND)

        box.Add(wx.StaticText(self.dialog, label="&Description:"), 0, wx.TOP | wx.BOTTOM, 4)
        # Read-only edit field, not static text: a description is the whole
        # reason somebody can choose, and static text cannot be tabbed to,
        # arrowed through, or re-read a word at a time (the same reason the ACB
        # schedule's summary line is a field).
        char_w, char_h = self.dialog.GetTextExtent("M")
        self._description = wx.TextCtrl(
            self.dialog,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_WORDWRAP,
            size=(char_w * 40, char_h * 5),
        )
        _desc_help = (
            "What the highlighted item is, in the publisher's own words. It is "
            "read-only -- you can tab to it and arrow through it a word at a "
            "time, but not change it."
        )
        self._description.SetName(_desc_help)
        self._description.SetHelpText(_desc_help)
        box.Add(self._description, 0, wx.EXPAND)
        return box

    def _transfer_column(self) -> Any:
        wx = self._wx
        box = wx.BoxSizer(wx.VERTICAL)
        self._add_btn = wx.Button(self.dialog, label="A&dd")
        self._add_btn.SetHelpText("Moves the highlighted item into your list on the right.")
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._add_selected())
        box.Add(self._add_btn, 0, wx.EXPAND | wx.BOTTOM, 6)

        self._add_all_btn = wx.Button(self.dialog, label="Add A&ll")
        self._add_all_btn.SetHelpText(
            "Adds everything on the left that you do not already have, and says how many."
        )
        self._add_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._add_all())
        box.Add(self._add_all_btn, 0, wx.EXPAND)
        return box

    def _chosen_column(self) -> Any:
        wx = self._wx
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(self.dialog, label=f"&{self._chosen_label}:"), 0, wx.BOTTOM, 4)
        self._chosen_list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        _help = (
            "What you are about to add, in the order it will be saved. It stays "
            "in alphabetical order however you add to it -- until you move "
            "something, and from then on it stays exactly as you arrange it. "
            "Enter, or Remove, takes the highlighted one back out."
        )
        self._chosen_list.SetName(_help)
        self._chosen_list.SetHelpText(_help)
        box.Add(self._chosen_list, 1, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler, help_text in (
            ("Move &Up", lambda: self._move(-1), "Moves the highlighted one one place earlier."),
            ("Move Dow&n", lambda: self._move(1), "Moves the highlighted one one place later."),
            ("&Remove", self._remove, "Takes the highlighted one back out of your list."),
            (
                "Sort A to &Z",
                self._resort,
                "Puts your list back into alphabetical order, discarding the "
                "arrangement you made. Only offered once you have moved something.",
            ),
        ):
            button = self._wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(self._wx.EVT_BUTTON, lambda _e, h=handler: h())
            row.Add(button, 0, wx.RIGHT | wx.TOP, 4)
            self._chosen_buttons = getattr(self, "_chosen_buttons", {})
            self._chosen_buttons[label] = button
        box.Add(row, 0)
        return box

    def _buttons(self) -> Any:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._summary = wx.StaticText(self.dialog, label="")
        row.Add(self._summary, 1, wx.ALIGN_CENTER_VERTICAL)
        self._ok_btn = wx.Button(self.dialog, wx.ID_OK, "&Add These")
        self._ok_btn.SetHelpText(
            "Adds everything in your list, in the order shown, and closes this window."
        )
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cl&ose")
        cancel.SetHelpText("Closes without adding anything.")
        row.Add(self._ok_btn, 0, wx.RIGHT, 6)
        row.Add(cancel, 0)
        self._ok_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept())
        self._cancel_id = cancel.GetId()
        apply_listbox_activation(self._available_list, lambda _e=None: self._add_selected())
        apply_listbox_activation(self._chosen_list, lambda _e=None: self._remove())
        self._available_list.Bind(self._wx.EVT_LISTBOX, lambda _e: self._sync())
        self._chosen_list.Bind(self._wx.EVT_LISTBOX, lambda _e: self._sync())
        return row

    # -- state ------------------------------------------------------------------

    def _fill_available(self) -> None:
        self._available_list.Set([item.label for item in self._available])
        if self._available:
            self._available_list.SetSelection(0)

    def _selected_available(self) -> PickableItem | None:
        index = self._available_list.GetSelection()
        if index == self._wx.NOT_FOUND or index >= len(self._available):
            return None
        return self._available[index]

    def _add_selected(self) -> None:
        item = self._selected_available()
        if item is None:
            return
        if item.already_have:
            self._host._announce(f"{item.title} is already in your library.")
            return
        if not self._picks.add(item):
            self._host._announce(f"{item.title} is already in your list.")
            return
        self._refill_chosen()
        self._host._announce(f"Added {item.title}. {self._count_sentence().capitalize()}.")

    def _add_all(self) -> None:
        addable = [item for item in self._available if not item.already_have]
        added = self._picks.add_all(addable)
        self._refill_chosen()
        if not added:
            self._host._announce("Nothing to add -- your list already has all of them.")
            return
        # A verb that touches many rows says how many (GATE-BULK-COUNT).
        noun = "item" if added == 1 else "items"
        self._host._announce(f"Added {added} {noun}. {self._count_sentence().capitalize()}.")

    def _remove(self) -> None:
        index = self._chosen_list.GetSelection()
        removed = self._picks.remove_at(index) if index != self._wx.NOT_FOUND else None
        if removed is None:
            return
        self._refill_chosen(select=min(index, len(self._picks) - 1))
        self._host._announce(f"Removed {removed.title}. {self._count_sentence().capitalize()}.")

    def _move(self, delta: int) -> None:
        index = self._chosen_list.GetSelection()
        if index == self._wx.NOT_FOUND:
            return
        landed = self._picks.move(index, delta)
        # The cursor follows the row, or the next press moves the wrong one.
        self._refill_chosen(select=landed)
        item = self._picks.items[landed]
        self._host._announce(f"{item.title}, {landed + 1} of {len(self._picks)}.")

    def _resort(self) -> None:
        self._picks.resort()
        self._refill_chosen()
        self._host._announce("Back in alphabetical order.")

    def _refill_chosen(self, *, select: int | None = None) -> None:
        self._chosen_list.Set([item.label for item in self._picks.items])
        if len(self._picks):
            self._chosen_list.SetSelection(max(0, min(select or 0, len(self._picks) - 1)))
        self._sync()

    def _count_sentence(self) -> str:
        total = len(self._picks)
        if not total:
            return "your list is empty"
        return f"{total} in your list"

    def _sync(self) -> None:
        item = self._selected_available()
        text = item.description if item is not None else ""
        if item is not None and not text:
            text = "No description is published for this one."
        if self._description.GetValue() != text:
            self._description.ChangeValue(text)
        addable = item is not None and not item.already_have
        self._add_btn.Enable(addable)
        chosen = len(self._picks)
        has_selection = self._chosen_list.GetSelection() != self._wx.NOT_FOUND
        buttons = getattr(self, "_chosen_buttons", {})
        for label in ("Move &Up", "Move Dow&n", "&Remove"):
            if label in buttons:
                buttons[label].Enable(has_selection)
        if "Sort A to &Z" in buttons:
            # Only meaningful once an arrangement exists to discard.
            buttons["Sort A to &Z"].Enable(self._picks.order == MANUAL and chosen > 1)
        self._ok_btn.Enable(chosen > 0)
        self._summary.SetLabel(self._count_sentence().capitalize() + ".")
        set_accessible_name(self._summary, self._count_sentence().capitalize() + ".")

    def _accept(self) -> None:
        self._result = list(self._picks.items)
        self.dialog.EndModal(self._wx.ID_OK)


__all__ = ["PickableItem", "choose_from_catalogue"]
