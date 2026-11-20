"""Two small building blocks for the workflow, Dependabot and CODEOWNERS sheets (PRD 22.1).

- :class:`FieldsDialog` is a linear form: one labelled control per field, in
  order (a text box, a multi-line box, a choice or a check box), with OK and
  Cancel. Each field's label gets its own access key, chosen so no two in the
  window share one (GATE-14). The workflow editor's step, trigger, input and
  permissions forms, the Dependabot entry and the CODEOWNERS rule are all
  this one window with different fields.
- :class:`RowList` is a list with its buttons under it (Add, Edit, Remove,
  Move Up, Move Down): the list is the table, Enter edits the selected row.

Nothing here talks to GitHub; each form's :attr:`FieldsDialog.values` is
read by the window that opened it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["Field", "FieldsDialog", "ItemsDialog", "RowList", "ask_fields", "mnemonic"]


@dataclass(frozen=True)
class Field:
    """One control of a form.

    ``kind`` is "text", "multiline", "choice", "check", or "checks" (a list of
    check boxes whose value is the checked choices).
    """

    key: str
    label: str
    value: Any = ""
    help: str = ""
    kind: str = "text"
    choices: tuple[str, ...] = ()


def mnemonic(label: str, used: set[str]) -> str:
    """*label* with ``&`` before its first letter no other control has taken."""
    for index, char in enumerate(label):
        lowered = char.casefold()
        if char.isalnum() and lowered not in used:
            used.add(lowered)
            return label[:index] + "&" + label[index:]
    return label


class FieldsDialog:
    """A form of :class:`Field` rows; :attr:`values` is set when OK is pressed."""

    def __init__(
        self,
        parent: object,
        title: str,
        fields: Sequence[Field],
        *,
        check: Callable[[dict[str, Any]], str] | None = None,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self.title = title
        self.fields = list(fields)
        self._check = check
        self._announce = announce or (lambda _text: None)
        self.values: dict[str, Any] | None = None
        self.controls: dict[str, Any] = {}
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 520, 360))
        root = wx.BoxSizer(wx.VERTICAL)
        used: set[str] = set()
        for field in self.fields:
            self.controls[field.key] = self._control(root, field, used)
        self.problem = wx.StaticText(self.dialog, label="")
        self.problem.SetName("Form problem")
        root.Add(self.problem, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self.dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Keep what is in this form.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close the form without changing anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _control(self, root: Any, field: Field, used: set[str]) -> Any:
        wx = self._wx
        label = mnemonic(field.label, used)
        name = field.label.rstrip(":")
        if field.kind == "check":
            control = wx.CheckBox(self.dialog, label=label)
            control.SetValue(bool(field.value))
            control.SetHelpText(field.help or name)
            root.Add(control, 0, wx.ALL, 8)
            return control
        if field.kind == "checks":
            root.Add(wx.StaticText(self.dialog, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            # One real check box per choice (A11Y-SR-1): a check list's state
            # is not said as the reader moves through it.
            panel = wx.ScrolledWindow(self.dialog)
            panel.SetScrollRate(0, 10)
            column = wx.BoxSizer(wx.VERTICAL)
            chosen = set(field.value or ())
            boxes = []
            for choice in field.choices:
                box = wx.CheckBox(panel, label=choice)
                box.SetValue(choice in chosen)
                box.SetHelpText(field.help or name)
                column.Add(box, 0, wx.ALL, 2)
                boxes.append(box)
            if not boxes:
                none = wx.StaticText(panel, label="None to choose from.")
                column.Add(none, 0, wx.ALL, 2)
            panel.SetSizer(column)
            root.Add(panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
            return boxes
        # Each caption is built just before its control: wxMSW's accessible name.
        style = wx.TE_MULTILINE | wx.TE_DONTWRAP if field.kind == "multiline" else 0
        if field.kind == "choice":
            caption = wx.StaticText(self.dialog, label=label)
            control = wx.Choice(self.dialog, choices=list(field.choices))
            value = str(field.value)
            control.SetSelection(field.choices.index(value) if value in field.choices else 0)
        else:
            caption = wx.StaticText(self.dialog, label=label)
            control = wx.TextCtrl(self.dialog, value=str(field.value), style=style)
        control.SetName(name)
        control.SetHelpText(field.help or name)
        root.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(control, 1 if field.kind == "multiline" else 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        return control

    def read(self) -> dict[str, Any]:
        found: dict[str, Any] = {}
        for field in self.fields:
            control = self.controls[field.key]
            if field.kind == "check":
                found[field.key] = bool(control.GetValue())
            elif field.kind == "checks":
                found[field.key] = [
                    choice
                    for choice, box in zip(field.choices, control, strict=True)
                    if box.GetValue()
                ]
            elif field.kind == "choice":
                index = control.GetSelection()
                found[field.key] = field.choices[index] if index >= 0 else ""
            else:
                found[field.key] = str(control.GetValue())
        return found

    def _on_ok(self, event: Any) -> None:
        found = self.read()
        problem = self._check(found) if self._check is not None else ""
        if problem:
            self.problem.SetLabel(problem)
            self._announce(problem)
            return
        self.values = found
        event.Skip()

    def show(self) -> dict[str, Any] | None:
        try:
            if show_modal_dialog(self.dialog, self.title) != self._wx.ID_OK:
                return None
            return self.values
        finally:
            self.dialog.Destroy()


def ask_fields(
    parent: object,
    title: str,
    fields: Sequence[Field],
    *,
    check: Callable[[dict[str, Any]], str] | None = None,
    announce: Callable[[str], None] | None = None,
) -> dict[str, Any] | None:
    """Show a :class:`FieldsDialog`; its values, or None when cancelled."""
    return FieldsDialog(parent, title, fields, check=check, announce=announce).show()


class RowList:
    """A labelled list and a row of buttons under it, in *window*'s *sizer*.

    *buttons* are ``(label, help, handler)``; the first one whose label
    starts with "Edit" (or "&Edit") also answers Enter and double-click.
    """

    def __init__(
        self,
        window: Any,
        sizer: Any,
        label: str,
        help_text: str,
        buttons: Sequence[tuple[str, str, Callable[[], None]]],
    ) -> None:
        import wx

        sizer.Add(wx.StaticText(window, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.box = wx.ListBox(window, choices=[])
        self.box.SetName(label.replace("&", "").rstrip(":"))
        self.box.SetHelpText(help_text)
        sizer.Add(self.box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for text, help_line, handler in buttons:
            button = wx.Button(window, label=text)
            button.SetHelpText(help_line)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=handler: run())
            row.Add(button, 0, wx.RIGHT, 4)
            if text.replace("&", "").startswith("Edit") and not hasattr(self, "_edit"):
                self._edit = handler
                apply_listbox_activation(self.box, lambda _e, run=handler: run())
        sizer.Add(row, 0, wx.ALL, 8)

    def set_rows(self, rows: Sequence[str], select: int = -1) -> None:
        self.box.Set(list(rows))
        if rows and select >= 0:
            self.box.SetSelection(min(select, len(rows) - 1))

    def selection(self) -> int:
        return int(self.box.GetSelection())


class ItemsDialog:
    """A list of items to add to, edit, remove and reorder; :attr:`items` when OK.

    *summary(item, number)* is a row's text; *edit(item or None)* returns the
    new or changed item, or None when that form was cancelled.
    """

    def __init__(
        self,
        parent: object,
        title: str,
        noun: str,
        items: Sequence[Any],
        summary: Callable[[Any, int], str],
        edit: Callable[[Any], Any],
        *,
        help_text: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self.title = title
        self.items = list(items)
        self._summary = summary
        self._edit = edit
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 520, 360))
        root = wx.BoxSizer(wx.VERTICAL)
        self.rows = RowList(
            self.dialog,
            root,
            f"&{noun.title()}s:",
            help_text or f"Each {noun}, in order. Enter edits the selected one.",
            (
                (f"&Add {noun.title()}...", f"Add a {noun} at the end.", self.add),
                (f"&Edit {noun.title()}...", f"Change the selected {noun}.", self.edit),
                (f"&Remove {noun.title()}", f"Remove the selected {noun}.", self.remove),
                ("Move &Up", f"Move the selected {noun} earlier.", lambda: self.move(-1)),
                ("Move Do&wn", f"Move the selected {noun} later.", lambda: self.move(1)),
            ),
        )
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self.dialog, wx.ID_OK, "OK")
        ok.SetHelpText(f"Keep these {noun}s.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.refresh(0)

    def refresh(self, select: int = -1) -> None:
        self.rows.set_rows(
            [self._summary(item, number) for number, item in enumerate(self.items, 1)], select
        )

    def add(self) -> None:
        made = self._edit(None)
        if made is not None:
            self.items.append(made)
            self.refresh(len(self.items) - 1)

    def edit(self) -> None:
        index = self.rows.selection()
        if index < 0:
            return
        made = self._edit(self.items[index])
        if made is not None:
            self.items[index] = made
            self.refresh(index)

    def remove(self) -> None:
        index = self.rows.selection()
        if index >= 0:
            del self.items[index]
            self.refresh(index)

    def move(self, delta: int) -> None:
        index = self.rows.selection()
        target = index + delta
        if index < 0 or not 0 <= target < len(self.items):
            return
        self.items[index], self.items[target] = self.items[target], self.items[index]
        self.refresh(target)

    def show(self) -> list[Any] | None:
        try:
            if show_modal_dialog(self.dialog, self.title) != self._wx.ID_OK:
                return None
            return self.items
        finally:
            self.dialog.Destroy()
