"""Report Fields: choose extra Open-Meteo fields for the Weather Now report,
and the order they are read in.

No checkboxes in a list (they read poorly and toggle by accident): a chooser of
fields not yet added with an Add button, and a plain list of the chosen ones
with Move Up, Move Down and Remove -- the house pattern for an ordered choice.
The field catalogue and its help sentences live in
``quill.core.weather.nowcast.FIELD_CATALOG``.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.weather.nowcast import FIELD_CATALOG
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.dpi import dip, dip_size


class ReportFieldsDialog:
    def __init__(
        self,
        parent: object,
        *,
        chosen: list[str],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self.chosen = [key for key in chosen if key in FIELD_CATALOG]
        self.dialog = wx.Dialog(
            parent, title="Report Fields", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        dlg = self.dialog
        gap = dip(dlg, 12)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dlg,
                label="Extra fields from Open-Meteo to add to the Weather Now report, "
                "read in this order.",
            ),
            0,
            wx.ALL,
            gap,
        )
        add_row = wx.BoxSizer(wx.HORIZONTAL)
        add_row.Add(wx.StaticText(dlg, label="&Field to add:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._available = wx.Choice(dlg)
        self._available.SetHelpText(
            "Fields you have not added yet. Choose one, then press Add. The meaning "
            "of the chosen field is shown under the list."
        )
        add_row.Add(self._available, 1, wx.LEFT | wx.RIGHT, dip(dlg, 6))
        self._add = wx.Button(dlg, wx.ID_ANY, "&Add")
        self._add.SetHelpText("Add the chosen field to the end of the report's list.")
        add_row.Add(self._add)
        root.Add(add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)

        root.Add(
            wx.StaticText(dlg, label="Fields in the &report:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, gap
        )
        self._list = wx.ListBox(dlg, size=dip_size(dlg, 420, 200))
        set_accessible_name(self._list, "Fields in the report")
        self._list.SetHelpText(
            "The extra fields the report reads, in order. Move Up, Move Down and "
            "Remove act on the selected one."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)
        self._meaning = wx.StaticText(dlg, label="")
        root.Add(self._meaning, 0, wx.EXPAND | wx.ALL, gap)

        moves = wx.BoxSizer(wx.HORIZONTAL)
        self._up = wx.Button(dlg, wx.ID_ANY, "Move &Up")
        self._up.SetHelpText("Read the selected field one place earlier.")
        self._down = wx.Button(dlg, wx.ID_ANY, "Move &Down")
        self._down.SetHelpText("Read the selected field one place later.")
        self._remove = wx.Button(dlg, wx.ID_ANY, "Re&move")
        self._remove.SetHelpText("Take the selected field out of the report.")
        for button in (self._up, self._down, self._remove):
            moves.Add(button, 0, wx.RIGHT, dip(dlg, 6))
        root.Add(moves, 0, wx.LEFT | wx.RIGHT, gap)

        bottom = wx.StdDialogButtonSizer()
        ok = wx.Button(dlg, wx.ID_OK, "OK")
        ok.SetHelpText("Save these fields. The report uses them from its next refresh.")
        cancel = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing the report's fields.")
        ok.SetDefault()
        bottom.AddButton(ok)
        bottom.AddButton(cancel)
        bottom.Realize()
        root.Add(bottom, 0, wx.EXPAND | wx.ALL, gap)
        dlg.SetSizer(root)
        root.Fit(dlg)
        bind_close_button(dlg, cancel, modeless=False)

        self._add.Bind(wx.EVT_BUTTON, lambda _e: self.add())
        self._up.Bind(wx.EVT_BUTTON, lambda _e: self.move(-1))
        self._down.Bind(wx.EVT_BUTTON, lambda _e: self.move(1))
        self._remove.Bind(wx.EVT_BUTTON, lambda _e: self.remove())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync(source="list"))
        self._available.Bind(wx.EVT_CHOICE, lambda _e: self._sync(source="available"))
        self._refresh(select=0)

    # -- state -------------------------------------------------------------------

    def _unchosen(self) -> list[str]:
        return [key for key in FIELD_CATALOG if key not in self.chosen]

    def _refresh(self, *, select: int) -> None:
        self._available.Set([FIELD_CATALOG[k].label for k in self._unchosen()])
        if self._available.GetCount():
            self._available.SetSelection(0)
        self._list.Set([FIELD_CATALOG[k].label for k in self.chosen])
        if self.chosen:
            self._list.SetSelection(max(0, min(select, len(self.chosen) - 1)))
        self._sync()

    def _sync(self, *, source: str = "list") -> None:
        """Enable the buttons, and show the meaning of whichever control changed:
        the chooser's field when the chooser moved, else the list's."""
        at = self._list.GetSelection()
        has = at != self._wx.NOT_FOUND
        self._up.Enable(has and at > 0)
        self._down.Enable(has and at < len(self.chosen) - 1)
        self._remove.Enable(has)
        self._add.Enable(self._available.GetCount() > 0)
        pick = self._available.GetSelection()
        unchosen = self._unchosen()
        if source == "list" and has:
            meaning = FIELD_CATALOG[self.chosen[at]].help
        elif 0 <= pick < len(unchosen):
            meaning = FIELD_CATALOG[unchosen[pick]].help
        else:
            meaning = ""
        self._meaning.SetLabel(meaning)
        self._meaning.Wrap(dip(self.dialog, 420))
        self.dialog.Layout()

    def add(self) -> None:
        unchosen = self._unchosen()
        pick = self._available.GetSelection()
        if not 0 <= pick < len(unchosen):
            return
        key = unchosen[pick]
        self.chosen.append(key)
        self._refresh(select=len(self.chosen) - 1)
        if not self._available.GetCount():
            self._list.SetFocus()  # Add has just been disabled under focus
        self._announce(f"Added {FIELD_CATALOG[key].label}.")

    def move(self, step: int) -> None:
        at = self._list.GetSelection()
        to = at + step
        if at == self._wx.NOT_FOUND or not 0 <= to < len(self.chosen):
            return
        self.chosen[at], self.chosen[to] = self.chosen[to], self.chosen[at]
        self._refresh(select=to)
        button = self._up if step < 0 else self._down
        if not button.IsEnabled():
            self._list.SetFocus()  # at the top or bottom: the button went dim
        label = FIELD_CATALOG[self.chosen[to]].label
        self._announce(f"Moved {label} to {to + 1} of {len(self.chosen)}.")

    def remove(self) -> None:
        at = self._list.GetSelection()
        if at == self._wx.NOT_FOUND:
            return
        key = self.chosen.pop(at)
        self._refresh(select=at)
        if not self.chosen:
            self._available.SetFocus()  # Remove has just been disabled under focus
        self._announce(f"Removed {FIELD_CATALOG[key].label}.")

    def show(self) -> list[str] | None:
        """The chosen fields on OK, None on Cancel."""
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="OK",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        try:
            result = show_modal_dialog(self.dialog, "Report Fields", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return list(self.chosen) if result == wx.ID_OK else None
