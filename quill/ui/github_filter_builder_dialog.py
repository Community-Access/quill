"""The Filter Builder (Ctrl+Alt+F): conditions written as GitHub's syntax (PRD 17.2, C7).

Choose an attribute, an operator that fits it and a value picked from the
repository (or typed), and Add (Insert) puts the condition in the list; Delete
removes the focused one. The query the conditions make is shown as it grows,
so people learn GitHub's syntax by watching it appear. OK (Ctrl+Enter) writes
it into the filter box; Save as Search (Ctrl+S) also keeps it under Saved
Searches. Groups joined by Or are numbered: a condition in group 2 is or'ed
with group 1.

The arithmetic is :mod:`quill.core.github.filter_builder`. Opening says
nothing (GATE-13).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.github.filter_builder import (
    ATTRIBUTES,
    OPERATORS,
    SORTS,
    BuilderRow,
    describe_row,
    render_query,
    rows_from_query,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

__all__ = ["FilterBuilderDialog"]

TITLE = "Filter Builder"


class FilterBuilderDialog:
    """Build a filter; :attr:`query` and :attr:`save` are the answer after OK."""

    def __init__(
        self, parent: Any, *, values: Mapping[str, Sequence[str]], initial: str = ""
    ) -> None:
        import wx

        self._wx = wx
        self._values = {key: list(found) for key, found in values.items()}
        self.rows: list[BuilderRow] = rows_from_query(initial)
        self.query = ""
        self.save = False
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 640, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        def labelled(text: str, control: Any) -> None:
            grid.Add(wx.StaticText(self.dialog, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)

        self.attribute = wx.Choice(self.dialog, choices=[a.label for a in ATTRIBUTES])
        self.attribute.SetHelpText(
            "What to filter on: every attribute GitHub search knows for issues and pull "
            "requests. Has conflicts is checked over the loaded rows."
        )
        labelled("A&ttribute:", self.attribute)
        self.operator = wx.Choice(self.dialog, choices=[])
        self.operator.SetHelpText(
            "How to compare: is, is not, any of, none of, has none, has any; dates before, "
            "after, between or in the last n days; numbers more than, less than, between."
        )
        labelled("O&perator:", self.operator)
        self.value = wx.ComboBox(self.dialog, choices=[], style=wx.CB_DROPDOWN)
        self.value.SetHelpText(
            "The value: choose one from the repository, or type it. Me means you. For any "
            "of and none of, separate several with commas; a date is year-month-day."
        )
        labelled("&Value:", self.value)
        self.second = wx.TextCtrl(self.dialog)
        self.second.SetHelpText("For between: the second value, the end of the range.")
        labelled("Up to (for &between):", self.second)
        self.group = wx.SpinCtrl(self.dialog, min=1, max=5, initial=1)
        self.group.SetHelpText(
            "Or groups: conditions in the same group must all match; a different group is "
            "joined with Or, which GitHub's issue search allows."
        )
        labelled("Or &group:", self.group)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        add_row = wx.BoxSizer(wx.HORIZONTAL)
        add = wx.Button(self.dialog, label="A&dd Condition")
        add.SetHelpText("Add this condition to the list. Insert does it too.")
        add.Bind(wx.EVT_BUTTON, lambda _e: self.add())
        remove = wx.Button(self.dialog, label="&Remove Condition")
        remove.SetHelpText("Remove the selected condition. Delete does it too.")
        remove.Bind(wx.EVT_BUTTON, lambda _e: self.remove())
        add_row.Add(add, 0, wx.RIGHT, 6)
        add_row.Add(remove)
        root.Add(add_row, 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(wx.StaticText(self.dialog, label="&Conditions:"), 0, wx.LEFT | wx.TOP, 8)
        self.conditions = wx.ListBox(self.dialog, choices=[])
        set_spoken_name(self.conditions, "Conditions")
        self.conditions.SetHelpText("The conditions so far, in words. Delete removes one.")
        root.Add(self.conditions, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sort_row = wx.BoxSizer(wx.HORIZONTAL)
        sort_row.Add(wx.StaticText(self.dialog, label="S&ort:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.sort = wx.Choice(self.dialog, choices=["As GitHub sorts", *(w for w, _q in SORTS)])
        self.sort.SetHelpText(
            "Sort and order: created, updated, comments, reactions, interactions."
        )
        self.sort.SetSelection(0)
        sort_row.Add(self.sort, 1, wx.LEFT, 6)
        root.Add(sort_row, 0, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(self.dialog, label="&Query:"), 0, wx.LEFT, 8)
        self.preview = wx.TextCtrl(self.dialog, style=wx.TE_READONLY)
        set_spoken_name(self.preview, "Query")
        self.preview.SetHelpText("The query the conditions make, in GitHub's own syntax.")
        root.Add(self.preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save = wx.Button(self.dialog, label="&Save as Search")
        save.SetHelpText("Use this filter and keep it under Saved Searches. Ctrl+S.")
        save.Bind(wx.EVT_BUTTON, lambda _e: self.finish(save=True))
        buttons.Add(save)
        buttons.AddStretchSpacer()
        ok = wx.Button(self.dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Write this filter into the filter box and apply it. Ctrl+Enter.")
        ok.Bind(wx.EVT_BUTTON, lambda _e: self.finish(save=False))
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Change nothing.")
        bind_close_button(self.dialog, cancel, modeless=False)
        buttons.Add(ok, 0, wx.RIGHT, 6)
        buttons.Add(cancel)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog)
        self.dialog.SetEscapeId(wx.ID_CANCEL)
        self.attribute.Bind(wx.EVT_CHOICE, lambda _e: self._attribute_changed())
        self.sort.Bind(wx.EVT_CHOICE, lambda _e: self._refresh())
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self.attribute.SetSelection(0)
        self._attribute_changed()
        self._refresh()

    def _attribute_changed(self) -> None:
        spec = ATTRIBUTES[max(self.attribute.GetSelection(), 0)]
        self.operator.Set(list(OPERATORS[spec.kind]))
        self.operator.SetSelection(0)
        choices = list(spec.choices) or list(self._values.get(spec.source, ()))
        if spec.kind == "person":
            choices = ["Me", *choices]
        self.value.Set(choices)

    def add(self) -> None:
        spec = ATTRIBUTES[max(self.attribute.GetSelection(), 0)]
        operator = self.operator.GetStringSelection()
        text = self.value.GetValue().strip()
        values = tuple(v.strip() for v in text.split(",") if v.strip())
        if operator == "between" and self.second.GetValue().strip():
            values = (*values[:1], self.second.GetValue().strip())
        if not values and operator not in ("has none", "has any"):
            self.value.SetFocus()
            return
        self.rows.append(BuilderRow(spec.key, operator, values, self.group.GetValue() - 1))
        self.value.SetValue("")
        self.second.SetValue("")
        self._refresh()

    def remove(self) -> None:
        index = self.conditions.GetSelection()
        if 0 <= index < len(self.rows):
            del self.rows[index]
            self._refresh()

    def text(self) -> str:
        index = self.sort.GetSelection()
        sort = SORTS[index - 1][1] if index > 0 else ""
        return render_query(self.rows, sort)

    def _refresh(self) -> None:
        self.conditions.Set([describe_row(row) for row in self.rows] or ["(No conditions yet.)"])
        self.preview.ChangeValue(self.text())

    def finish(self, *, save: bool) -> None:
        self.query = self.text()
        self.save = save
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_key(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        focused = wx.Window.FindFocus()
        if code == wx.WXK_INSERT and not event.HasAnyModifiers():
            self.add()
            return
        if code == wx.WXK_DELETE and focused is self.conditions:
            self.remove()
            return
        if event.ControlDown() and code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.finish(save=False)
            return
        if event.ControlDown() and code in (ord("S"), ord("s")):
            self.finish(save=True)
            return
        event.Skip()

    def show(self) -> bool:
        try:
            return bool(show_modal_dialog(self.dialog, TITLE) == self._wx.ID_OK)
        finally:
            self.dialog.Destroy()
