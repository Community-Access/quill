"""An editable Properties sheet: OK, Cancel and Apply over the shared sheet model.

GitHub PRD section 15, provider-neutral (WordPress PRD section 8), beside the
read-only :mod:`quill.ui.workbench_properties_dialog`, which it does not
change. The sheet is a :class:`~quill.core.workbench.properties.SheetSpec`;
every field is a focusable, labelled control:

- text, numbers, dates and lists are text boxes (a list is comma-separated);
- a choice is a choice box and a flag a check box;
- a read-only field, or one the person's role cannot change (*locked*, with
  the reason as the field's F1 help), is a read-only text box, never bare
  static text, so Tab reaches it and a braille display can pan through it.

Several objects at once (batch, 9): a field that differs shows "Mixed", a
three-state check box shows its third state, and a field left Mixed is never
sent (:func:`quill.core.workbench.properties.changes`).

*on_save* is given the sheet's :class:`SheetState`; the provider sends it
off the UI thread and says the result. OK saves and closes; Apply saves and
keeps the sheet open on what was sent. Nothing here talks to a network, and
opening says nothing: the reader says the title and the first field (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from quill.core.workbench.properties import (
    MIXED,
    FieldKind,
    FieldSpec,
    SheetSpec,
    SheetState,
    Value,
    as_text,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name
from quill.ui.workbench_properties_dialog import field_text

__all__ = ["MIXED_WORD", "WorkbenchSheetEditor"]

MIXED_WORD = "Mixed"
_UNCHANGED = "(Mixed: leave as it is)"


class WorkbenchSheetEditor:
    """The editable sheet, parented to the Workbench so it never blocks the editor."""

    def __init__(
        self,
        parent: Any,
        sheet: SheetSpec,
        values: Mapping[str, object],
        *,
        title: str,
        copy_text: Callable[[str], None],
        on_save: Callable[[SheetState], None] | None = None,
        locked: Mapping[str, str] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self.sheet = sheet
        self.title = title
        self._copy_text = copy_text
        self._on_save = on_save
        self._locked = dict(locked or {})
        self.state = SheetState(sheet, loaded=dict(values))  # type: ignore[arg-type]
        self.controls: dict[str, Any] = {}
        self._shown: dict[str, object] = {}
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 600, 520))
        self.dialog.SetHelpText(
            "Everything about it on one sheet. Ctrl+Tab moves between pages; OK saves "
            "and closes, Apply saves and stays."
        )
        root = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.dialog)
        self.notebook.SetHelpText("The sheet's pages. Ctrl+Tab moves to the next page.")
        for page in sheet.pages:
            panel = wx.Panel(self.notebook)
            grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
            grid.AddGrowableCol(1, 1)
            for spec in page.fields:
                label = wx.StaticText(panel, label=f"{spec.label}:")
                control = self._control(panel, spec, self.state.loaded.get(spec.key))
                grid.Add(label, 0, wx.ALIGN_TOP | wx.TOP, 3)
                grid.Add(control, 1, wx.EXPAND)
                self.controls[spec.key] = control
                if self.editable(spec):
                    self._shown[spec.key] = self.value_of(spec)
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
            panel.SetSizer(outer)
            self.notebook.AddPage(panel, page.title)
        root.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_button = wx.Button(self.dialog, label="Copy as &Text")
        copy_button.SetHelpText("Copy every page of this sheet as plain text.")
        copy_button.Bind(wx.EVT_BUTTON, lambda _e: self._copy_text(self.text()))
        buttons.Add(copy_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer()
        if on_save is not None:
            ok = wx.Button(self.dialog, wx.ID_OK, "OK")
            ok.SetHelpText("Save what you changed and close the sheet.")
            ok.Bind(wx.EVT_BUTTON, lambda _e: self._save(close=True))
            apply = wx.Button(self.dialog, wx.ID_APPLY, "&Apply")
            apply.SetHelpText("Save what you changed and keep the sheet open.")
            apply.Bind(wx.EVT_BUTTON, lambda _e: self._save(close=False))
            buttons.Add(ok, 0, wx.RIGHT, 8)
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel" if on_save else "Close")
        cancel.SetHelpText("Close the sheet without saving. Escape does the same.")
        bind_close_button(self.dialog, cancel, modeless=False)
        buttons.Add(cancel, 0, wx.RIGHT, 8)
        if on_save is not None:
            buttons.Add(apply)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog)
        self.dialog.SetEscapeId(wx.ID_CANCEL)

    # -- building -----------------------------------------------------------------

    def _help(self, spec: FieldSpec) -> str:
        reason = self._locked.get(spec.key, "")
        if reason:
            return f"{spec.help or spec.label} Read only for you: {reason}"
        if spec.readonly or self._on_save is None:
            return spec.help or f"{spec.label}, read only."
        return spec.help or f"{spec.label}."

    def editable(self, spec: FieldSpec) -> bool:
        return self._on_save is not None and not spec.readonly and spec.key not in self._locked

    def _control(self, panel: Any, spec: FieldSpec, value: object) -> Any:
        wx = self._wx
        mixed = value is MIXED
        if self.editable(spec) and spec.kind is FieldKind.CHECK:
            style = wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER if mixed else 0
            control = wx.CheckBox(panel, label=spec.label, style=style)
            if mixed:
                control.Set3StateValue(wx.CHK_UNDETERMINED)
            else:
                control.SetValue(bool(value))
        elif self.editable(spec) and spec.kind is FieldKind.CHOICE:
            choices = list(spec.choices)
            if not mixed and value not in (None, "") and str(value) not in choices:
                choices.insert(0, str(value))
            if mixed:
                choices.insert(0, _UNCHANGED)
            control = wx.Choice(panel, choices=choices)
            current = _UNCHANGED if mixed else str(value or "")
            control.SetSelection(choices.index(current) if current in choices else 0)
        else:
            style = 0 if self.editable(spec) else wx.TE_READONLY
            if spec.kind is FieldKind.MULTILINE:
                style |= wx.TE_MULTILINE | wx.TE_WORDWRAP
            text = MIXED_WORD if mixed else self._text(spec, value)
            control = wx.TextCtrl(panel, value=text, style=style)
            if spec.kind is FieldKind.MULTILINE:
                control.SetMinSize(dip_size(panel, 380, 150))
        set_spoken_name(control, spec.label)
        control.SetHelpText(self._help(spec))
        return control

    def _text(self, spec: FieldSpec, value: object) -> str:
        if self.editable(spec):
            if isinstance(value, tuple):
                return ", ".join(str(v) for v in value)
            return "" if value is None else str(value)
        return field_text(value)

    # -- reading back -------------------------------------------------------------

    def value_of(self, spec: FieldSpec) -> Value | object:
        """What the control holds now, as the sheet's value (:data:`MIXED` if left Mixed)."""
        wx = self._wx
        control = self.controls[spec.key]
        if spec.kind is FieldKind.CHECK:
            if control.Is3State() and control.Get3StateValue() == wx.CHK_UNDETERMINED:
                return MIXED
            return bool(control.GetValue())
        if spec.kind is FieldKind.CHOICE:
            text = control.GetStringSelection()
            return MIXED if text == _UNCHANGED else text
        text = control.GetValue()
        if text == MIXED_WORD and self.state.loaded.get(spec.key) is MIXED:
            return MIXED
        if spec.kind is FieldKind.LIST:
            return tuple(part.strip() for part in text.split(",") if part.strip())
        return text

    def collect(self) -> SheetState:
        # Only what the person changed: a control that still shows what it was
        # given is left alone, so a field the site never sent is never "changed"
        # to empty by the act of showing it.
        for spec in self.sheet.fields():
            if not self.editable(spec):
                continue
            value = self.value_of(spec)
            if value != self._shown.get(spec.key):
                self.state.edited[spec.key] = value  # type: ignore[assignment]
            else:
                self.state.edited.pop(spec.key, None)
        return self.state

    def _save(self, *, close: bool) -> None:
        if self._on_save is None:
            return
        state = self.collect()
        if not state.pending():
            if close:
                self.dialog.EndModal(self._wx.ID_OK)
            return
        self._on_save(state)
        if close:
            self.dialog.EndModal(self._wx.ID_OK)
            return
        state.loaded.update(state.edited)
        state.edited.clear()
        self._shown = {s.key: self.value_of(s) for s in self.sheet.fields() if self.editable(s)}

    def text(self) -> str:
        values = {spec.key: self.state.loaded.get(spec.key) for spec in self.sheet.fields()}
        return as_text(self.sheet, values, title=self.title)

    def show(self) -> int:
        try:
            return int(show_modal_dialog(self.dialog, self.title))
        finally:
            self.dialog.Destroy()
