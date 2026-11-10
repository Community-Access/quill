"""The Properties sheet, in full: one dialog that renders any sheet model (GitHub PRD 15, C6).

Provider-neutral, beside the simpler :mod:`quill.ui.workbench_sheet_editor`,
which it leaves alone. The sheet is a
:class:`~quill.core.workbench.properties.SheetSpec`; this window adds what
Phases 7 to 10 ask of it:

- **Every fact a focusable, labelled control**; a field the person may not
  change is a read-only text box whose F1 help, and the line under it, say
  why (*locked*: field key to reason).
- **Check lists** (labels, assignees, reviewers): one real check box per
  choice (:class:`quill.ui.workbench_check_group.CheckGroup`; the
  ``wx.CheckListBox`` is banned because readers do not say its state), three-
  state over several objects ("bug, on 3 of 5"), and only the boxes you
  change are sent, as a :class:`~quill.core.workbench.properties.ListDelta`.
- **New... beside a picker** (*on_create*): makes the thing and uses it at once.
- **Tables** (an Access page's people): a list box, with Add..., Change...
  and Remove when the provider gives *on_table* (Insert, F2 and Delete too).
- **OK, Cancel, Apply**: Enter is OK except in a multi-line box, Ctrl+Enter
  is OK from anywhere, Escape is Cancel, Ctrl+S is Apply; F5 reloads; Ctrl+1
  to Ctrl+9 jump to a page; Ctrl+Shift+C copies the sheet; Shift+Enter opens
  it on GitHub.
- **The last page used** for each kind of object is where it opens next time
  (*start_page*), section 16.3.

Saving is the provider's job (*on_apply* gets the pending changes and calls
:meth:`saved` when GitHub's re-read is in). Opening says nothing: the reader
says the title and the first field (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from quill.core.workbench.properties import (
    MIXED,
    FieldChange,
    FieldKind,
    FieldSpec,
    ListDelta,
    SheetSpec,
    SheetState,
    as_text,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name
from quill.ui.workbench_check_group import CheckGroup
from quill.ui.workbench_properties_dialog import field_text

__all__ = ["MIXED_CHOICE", "PropertiesSheet", "checklist_row"]

MIXED_CHOICE = "(Mixed: leave as it is)"


def checklist_row(name: str, count: int, total: int) -> str:
    """A check list row over several objects: "bug, on 3 of 5"; one object: "bug"."""
    if total <= 1 or count in (0, total):
        return name
    return f"{name}, on {count} of {total}"


class PropertiesSheet:
    """One object's sheet, or several objects' combined sheet."""

    def __init__(
        self,
        parent: Any,
        sheet: SheetSpec,
        values: Mapping[str, object],
        *,
        title: str,
        copy_text: Callable[[str], None],
        on_apply: Callable[[Sequence[FieldChange], bool], None] | None = None,
        locked: Mapping[str, str] | None = None,
        choices: Mapping[str, Sequence[str]] | None = None,
        counts: Mapping[str, Mapping[str, int]] | None = None,
        total: int = 1,
        on_create: Callable[[FieldSpec], str | None] | None = None,
        on_table: Callable[[FieldSpec, str, str], None] | None = None,
        on_reload: Callable[[], None] | None = None,
        open_web: Callable[[], None] | None = None,
        copy_link: Callable[[], None] | None = None,
        start_page: str = "",
        loaded_at: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self.sheet = sheet
        self.title = title
        self.total = total
        self._copy_text = copy_text
        self._on_apply = on_apply
        self._locked = dict(locked or {})
        self._choices = {key: list(items) for key, items in (choices or {}).items()}
        self._counts = {key: dict(found) for key, found in (counts or {}).items()}
        self._on_create = on_create
        self._on_table = on_table
        self._on_reload = on_reload
        self.state = SheetState(sheet, loaded=dict(values))  # type: ignore[arg-type]
        self.controls: dict[str, Any] = {}
        self._items: dict[str, list[str]] = {}
        self._initial: dict[str, object] = {}
        self.closed_with = 0
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 680, 560))
        self.dialog.SetHelpText(
            "Everything about it on one sheet. Ctrl+Tab moves between pages, Ctrl+1 to "
            "Ctrl+9 jump to one; OK saves and closes, Ctrl+S saves and stays, F5 reloads."
        )
        root = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.dialog)
        self.notebook.SetHelpText("The sheet's pages. Ctrl+Tab moves to the next page.")
        self._page_keys: list[str] = []
        for page in sheet.pages:
            panel = wx.ScrolledWindow(self.notebook, style=wx.VSCROLL)
            panel.SetScrollRate(0, 10)
            grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
            grid.AddGrowableCol(1, 1)
            for spec in page.fields:
                label = wx.StaticText(panel, label=f"{spec.label}:")
                cell = self._cell(panel, spec)
                grid.Add(label, 0, wx.ALIGN_TOP | wx.TOP, 3)
                grid.Add(cell, 1, wx.EXPAND)
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
            panel.SetSizer(outer)
            self.notebook.AddPage(panel, page.title)
            self._page_keys.append(page.key)
        root.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)
        self.status = wx.TextCtrl(self.dialog, value=loaded_at, style=wx.TE_READONLY)
        set_spoken_name(self.status, "Sheet status")
        self.status.SetHelpText(
            "When the sheet was loaded from GitHub, and what the last save did."
        )
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(self._buttons(copy_link, open_web), 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog)
        self.dialog.SetEscapeId(wx.ID_CANCEL)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        if start_page in self._page_keys:
            self.notebook.SetSelection(self._page_keys.index(start_page))

    # -- building -----------------------------------------------------------------

    def editable(self, spec: FieldSpec) -> bool:
        return self._on_apply is not None and not spec.readonly and spec.key not in self._locked

    def _help(self, spec: FieldSpec) -> str:
        reason = self._locked.get(spec.key, "")
        base = spec.help or f"{spec.label}."
        if reason:
            return f"{base} Read only: {reason}"
        if not self.editable(spec):
            return f"{base} Read only."
        return base

    def _cell(self, panel: Any, spec: FieldSpec) -> Any:
        wx = self._wx
        value = self.state.loaded.get(spec.key)
        column = wx.BoxSizer(wx.VERTICAL)
        control = self._control(panel, spec, value)
        window = control.panel if isinstance(control, CheckGroup) else control
        set_spoken_name(window, spec.label)
        control.SetHelpText(self._help(spec))
        self.controls[spec.key] = control
        if self.editable(spec) and spec.create and self._on_create is not None:
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(window, 1, wx.EXPAND)
            button = wx.Button(panel, label=spec.create)
            button.SetHelpText(f"Make a new one and use it here at once: {spec.create}")
            button.Bind(wx.EVT_BUTTON, lambda _e, s=spec: self._create(s))
            row.Add(button, 0, wx.LEFT, 6)
            column.Add(row, 1, wx.EXPAND)
        elif spec.kind is FieldKind.TABLE and self._on_table is not None:
            column.Add(window, 1, wx.EXPAND)
            row = wx.BoxSizer(wx.HORIZONTAL)
            for verb, text, what in (
                ("add", "Add...", "Add someone or something to this list. Insert does it too."),
                ("change", "Change...", "Change the selected row, such as its role. F2 too."),
                ("remove", "Remove", "Remove the selected row, after a preview. Delete too."),
            ):
                button = wx.Button(panel, label=text)
                button.SetHelpText(what)
                button.Bind(wx.EVT_BUTTON, lambda _e, s=spec, v=verb: self._table(s, v))
                row.Add(button, 0, wx.RIGHT, 6)
            column.Add(row, 0, wx.TOP, 4)
        else:
            column.Add(window, 1, wx.EXPAND)
        reason = self._locked.get(spec.key, "")
        if reason:
            column.Add(wx.StaticText(panel, label=f"Read only: {reason}"), 0, wx.TOP, 2)
        if self.editable(spec):
            self._initial[spec.key] = self.value_of(spec)
        return column

    def _control(self, panel: Any, spec: FieldSpec, value: object) -> Any:
        wx = self._wx
        mixed = value is MIXED
        if self.editable(spec) and spec.kind is FieldKind.CHECK:
            style = wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER if mixed else 0
            control = wx.CheckBox(panel, label=spec.label, style=style)
            control.SetHelpText(self._help(spec))
            if mixed:
                control.Set3StateValue(wx.CHK_UNDETERMINED)
            else:
                control.SetValue(bool(value))
            return control
        if self.editable(spec) and spec.kind is FieldKind.CHOICE:
            items = list(self._choices.get(spec.key, spec.choices))
            if not mixed and value not in (None, "") and str(value) not in items:
                items.insert(0, str(value))
            if "" not in items and not spec.choices:
                items.insert(0, "")
            if mixed:
                items.insert(0, MIXED_CHOICE)
            control = wx.Choice(panel, choices=[item or "(none)" for item in items])
            control.SetHelpText(self._help(spec))
            self._items[spec.key] = items
            current = MIXED_CHOICE if mixed else str(value or "")
            control.SetSelection(items.index(current) if current in items else 0)
            return control
        if self.editable(spec) and spec.kind is FieldKind.CHECKLIST:
            have = value if isinstance(value, tuple) else ()
            counts = self._counts.get(spec.key, {})
            items = list(self._choices.get(spec.key, spec.choices))
            items += [name for name in (*have, *counts) if name not in items]
            group = CheckGroup(
                panel,
                spec.label,
                items,
                have=have,
                counts=counts,
                total=self.total,
                help_text=self._help(spec),
            )
            return group
        if spec.kind is FieldKind.TABLE:
            rows = list(value) if isinstance(value, tuple) else []
            control = wx.ListBox(panel, choices=[str(r) for r in rows] or ["(none)"])
            control.SetHelpText(self._help(spec))
            control.SetMinSize(dip_size(panel, 300, 110))
            return control
        style = 0 if self.editable(spec) else wx.TE_READONLY
        if spec.kind is FieldKind.MULTILINE:
            style |= wx.TE_MULTILINE | wx.TE_WORDWRAP
        if mixed:
            text = "Mixed"
        elif self.editable(spec) and isinstance(value, tuple):
            text = ", ".join(str(v) for v in value)
        elif self.editable(spec):
            text = "" if value is None else str(value)
        else:
            text = field_text(value)
        control = wx.TextCtrl(panel, value=text, style=style)
        control.SetHelpText(self._help(spec))
        if spec.kind is FieldKind.MULTILINE:
            control.SetMinSize(dip_size(panel, 400, 150))
        return control

    def _buttons(self, copy_link: Callable[[], None] | None, open_web: Any) -> Any:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        extras: list[tuple[str, str, Callable[[], None]]] = [
            ("Copy as &Text", "Copy every page as plain text. Ctrl+Shift+C.", self.copy_as_text)
        ]
        if copy_link is not None:
            extras.append(("Copy &Link", "Copy its GitHub address.", copy_link))
        if open_web is not None:
            extras.append(("Open on &GitHub", "Open it in your browser. Shift+Enter.", open_web))
        if self._on_reload is not None:
            extras.append(("&Reload", "Load it again from GitHub. F5.", self._on_reload))
        for text, what, action in extras:
            button = wx.Button(self.dialog, label=text)
            button.SetHelpText(what)
            button.Bind(wx.EVT_BUTTON, lambda _e, a=action: a())
            row.Add(button, 0, wx.RIGHT, 6)
        row.AddStretchSpacer()
        if self._on_apply is not None:
            ok = wx.Button(self.dialog, wx.ID_OK, "OK")
            ok.SetHelpText("Save what you changed and close the sheet. Ctrl+Enter too.")
            ok.Bind(wx.EVT_BUTTON, lambda _e: self.apply(close=True))
            row.Add(ok, 0, wx.RIGHT, 6)
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel" if self._on_apply else "Close")
        cancel.SetHelpText("Close the sheet without saving. Escape does the same.")
        bind_close_button(self.dialog, cancel, modeless=False)
        row.Add(cancel, 0, wx.RIGHT, 6)
        if self._on_apply is not None:
            apply = wx.Button(self.dialog, wx.ID_APPLY, "&Apply")
            apply.SetHelpText("Save what you changed and keep the sheet open. Ctrl+S too.")
            apply.Bind(wx.EVT_BUTTON, lambda _e: self.apply(close=False))
            row.Add(apply)
        return row

    # -- reading back -------------------------------------------------------------

    def value_of(self, spec: FieldSpec) -> object:
        """What the control holds, as the sheet's value (:data:`MIXED` when left Mixed)."""
        wx = self._wx
        control = self.controls[spec.key]
        if spec.kind is FieldKind.CHECK and isinstance(control, wx.CheckBox):
            if control.Is3State() and control.Get3StateValue() == wx.CHK_UNDETERMINED:
                return MIXED
            return bool(control.GetValue())
        if spec.kind is FieldKind.CHOICE and isinstance(control, wx.Choice):
            items = self._items.get(spec.key, [])
            index = control.GetSelection()
            text = items[index] if 0 <= index < len(items) else ""
            return MIXED if text == MIXED_CHOICE else text
        if isinstance(control, CheckGroup):
            return control.checked()
        if isinstance(control, wx.ListBox):
            return self.state.loaded.get(spec.key)
        text = str(control.GetValue())
        if text == "Mixed" and self.state.loaded.get(spec.key) is MIXED:
            return MIXED
        if spec.kind is FieldKind.LIST:
            return tuple(part.strip() for part in text.split(",") if part.strip())
        return text

    def _delta(self, spec: FieldSpec) -> ListDelta:
        """For several objects: only the boxes changed from where they started."""
        control = self.controls[spec.key]
        return control.delta() if isinstance(control, CheckGroup) else ListDelta()

    def pending(self) -> list[FieldChange]:
        """The changed editable fields, as changes against what was loaded."""
        found: list[FieldChange] = []
        for spec in self.sheet.fields():
            if not self.editable(spec):
                continue
            if spec.kind is FieldKind.CHECKLIST and self.total > 1:
                delta = self._delta(spec)
                if delta:
                    found.append(FieldChange(spec.key, spec.label, MIXED, delta))
                continue
            value = self.value_of(spec)
            if value is MIXED or value == self._initial.get(spec.key):
                continue
            found.append(
                FieldChange(spec.key, spec.label, self.state.loaded.get(spec.key), value)  # type: ignore[arg-type]
            )
        return found

    # -- acting ---------------------------------------------------------------------

    def apply(self, *, close: bool) -> None:
        changes = self.pending()
        if not changes:
            if close:
                self.end(self._wx.ID_OK)
            else:
                self.status.SetValue("Nothing changed to save.")
            return
        if self._on_apply is not None:
            self._on_apply(changes, close)

    def saved(self, values: Mapping[str, object], said: str, *, close: bool) -> None:
        """The provider's answer after GitHub's re-read: show it, or close on OK."""
        if close:
            self.end(self._wx.ID_OK)
            return
        self.state.loaded.update(values)  # type: ignore[arg-type]
        for spec in self.sheet.fields():
            if self.editable(spec) and spec.key in values:
                self._set(spec, values[spec.key])
                self._initial[spec.key] = self.value_of(spec)
        self.status.SetValue(said)

    def reloaded(self, values: Mapping[str, object], loaded_at: str) -> None:
        self.state.loaded.update(values)  # type: ignore[arg-type]
        for spec in self.sheet.fields():
            if spec.key in values:
                self._set(spec, values[spec.key])
                if self.editable(spec):
                    self._initial[spec.key] = self.value_of(spec)
        self.status.SetValue(loaded_at)

    def _set(self, spec: FieldSpec, value: object) -> None:
        wx = self._wx
        control = self.controls[spec.key]
        if isinstance(control, wx.CheckBox):
            control.SetValue(bool(value))
        elif isinstance(control, wx.Choice):
            items = self._items.get(spec.key, [])
            text = str(value or "")
            if text not in items:
                items.append(text)
                control.Append(text or "(none)")
            control.SetSelection(items.index(text))
        elif isinstance(control, CheckGroup):
            control.reset(value if isinstance(value, tuple) else ())
        elif isinstance(control, wx.ListBox):
            rows = [str(r) for r in value] if isinstance(value, tuple) else []
            control.Set(rows or ["(none)"])
        elif isinstance(control, wx.TextCtrl):
            if isinstance(value, tuple) and self.editable(spec):
                control.SetValue(", ".join(str(v) for v in value))
            elif self.editable(spec):
                control.SetValue("" if value is None else str(value))
            else:
                control.SetValue(field_text(value))

    def _create(self, spec: FieldSpec) -> None:
        made = self._on_create(spec) if self._on_create is not None else None
        if not made:
            return
        wx = self._wx
        control = self.controls[spec.key]
        if isinstance(control, CheckGroup):
            control.add(made, on=True)
            control.panel.GetParent().Layout()
            control.boxes[made].SetFocus()
            return
        items = self._items.setdefault(spec.key, [])
        if made not in items:
            items.append(made)
            control.Append(made)
        if isinstance(control, wx.Choice):
            control.SetSelection(items.index(made))
        control.SetFocus()

    def _table(self, spec: FieldSpec, verb: str) -> None:
        if self._on_table is None:
            return
        control = self.controls[spec.key]
        index = control.GetSelection()
        rows = self.state.loaded.get(spec.key)
        row = str(rows[index]) if isinstance(rows, tuple) and 0 <= index < len(rows) else ""
        if verb != "add" and not row:
            self.status.SetValue("Select a row in the list first.")
            return
        self._on_table(spec, verb, row)

    def set_table(self, key: str, rows: tuple[str, ...]) -> None:
        self.state.loaded[key] = rows
        self._set(self.sheet.field(key), rows)

    def _on_key(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        ctrl = event.ControlDown()
        focused = wx.Window.FindFocus()
        if ctrl and not event.ShiftDown() and code in (ord("S"), ord("s")):
            self.apply(close=False)
            return
        if ctrl and code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.apply(close=True)
            return
        if code == wx.WXK_F5 and self._on_reload is not None:
            self._on_reload()
            return
        if ctrl and event.ShiftDown() and code in (ord("C"), ord("c")):
            self.copy_as_text()
            return
        if ctrl and not event.ShiftDown() and ord("1") <= code <= ord("9"):
            index = code - ord("1")
            if index < self.notebook.GetPageCount():
                self.notebook.SetSelection(index)
                self.notebook.SetFocus()
            return
        for spec in self.sheet.fields():
            if self.controls.get(spec.key) is focused and spec.kind is FieldKind.TABLE:
                verb = {wx.WXK_INSERT: "add", wx.WXK_F2: "change", wx.WXK_DELETE: "remove"}
                if code in verb and not ctrl:
                    self._table(spec, verb[code])
                    return
        event.Skip()

    def page_key(self) -> str:
        index = self.notebook.GetSelection()
        return self._page_keys[index] if 0 <= index < len(self._page_keys) else ""

    def text(self) -> str:
        values = {spec.key: self.state.loaded.get(spec.key) for spec in self.sheet.fields()}
        return as_text(self.sheet, values, title=self.title)

    def copy_as_text(self) -> None:
        self._copy_text(self.text())

    def end(self, code: int) -> None:
        self.closed_with = code
        if self.dialog.IsModal():
            self.dialog.EndModal(code)

    def show(self) -> int:
        try:
            return int(show_modal_dialog(self.dialog, self.title))
        finally:
            self.dialog.Destroy()
