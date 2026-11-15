"""The Field and Condition dialogs of QUILL's Gravity Forms editor (WP-C).

- :func:`ask_field`: one field's type (when adding), label, description,
  required, placeholder, default value, admin label, CSS class, and, by type,
  its choices (one a line), its HTML content or its consent text. Only the
  boxes that mean something for the type are shown, so Tab never stops on one
  that does nothing.
- :func:`ask_condition`: show or hide the field when another field is, or is
  not, a value; or always show it.

Both are ordinary dialogs of standard controls, run through the caller's
``show_modal``, with their help inline and OK and Cancel without access keys
(GATE-14). Neither touches the network. The core is
:mod:`quill.core.wordpress.gravity_build`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import wx

from quill.core.wordpress.gravity_build import (
    CHOICE_TYPES,
    DISPLAY_TYPES,
    FIELD_TYPES,
    Condition,
    choices_to_text,
    field_name,
)
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import ShowModal, _buttons, labelled_row

__all__ = ["ConditionDialog", "FieldAnswer", "FieldDialog", "ask_condition", "ask_field"]

_KINDS = list(FIELD_TYPES)


@dataclass(frozen=True)
class FieldAnswer:
    kind: str
    values: dict[str, Any]


class FieldDialog(wx.Dialog):
    """Add or edit one Gravity Forms field."""

    def __init__(self, parent: wx.Window, *, title: str, field: Mapping[str, Any] | None) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(
            "One field of the form. Only the settings that mean something for its type are shown."
        )
        old: Mapping[str, Any] = field or {}
        kind = str(old.get("type") or "text")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.kind = wx.Choice(self, choices=[f"{FIELD_TYPES[k]}" for k in _KINDS])
        self.kind.SetSelection(_KINDS.index(kind) if kind in _KINDS else 0)
        self.kind.Enable(field is None)
        self.kind.SetHelpText(
            "What kind of field this is. Chosen when the field is added; Change a Field Type "
            "on the form changes it later."
        )
        self.kind.Bind(wx.EVT_CHOICE, lambda _e: self._show_for_kind())
        labelled_row(sizer, self, "&Type:", self.kind)
        self.label = self._text(
            sizer,
            "&Label:",
            old.get("label"),
            "What the question asks. Every question needs one; a screen reader says it first.",
        )
        self.description = self._text(
            sizer,
            "&Description:",
            old.get("description"),
            "Help shown with the field, such as the format expected.",
            multiline=True,
        )
        self.required = wx.CheckBox(self, label="&Required")
        self.required.SetValue(bool(old.get("isRequired")))
        self.required.SetHelpText(
            "The form is not sent until this is answered, and a screen reader says required."
        )
        sizer.Add(self.required, 0, wx.ALL, 8)
        self.placeholder = self._text(
            sizer,
            "&Placeholder:",
            old.get("placeholder"),
            "Example text inside the empty box. It is not a label: it disappears on typing.",
        )
        self.default = self._text(
            sizer, "Default &value:", old.get("defaultValue"), "What the field holds at first."
        )
        self.admin_label = self._text(
            sizer,
            "&Admin label:",
            old.get("adminLabel"),
            "A shorter name for the entries list and notifications. Visitors never see it.",
        )
        self.css = self._text(
            sizer,
            "CSS &class:",
            old.get("cssClass"),
            "Class names for the theme's styles, separated by spaces.",
        )
        self.choices = self._text(
            sizer,
            "C&hoices:",
            choices_to_text(old.get("choices")),
            "One choice a line. To store a different value, write the text, space, equals, "
            "space, then the value. Start a line with an asterisk to have it chosen at first.",
            multiline=True,
        )
        self.content = self._text(
            sizer,
            "C&ontent:",
            old.get("content"),
            "The HTML this block shows. It asks nothing, so it needs no label.",
            multiline=True,
        )
        self.consent = self._text(
            sizer,
            "Check box te&xt:",
            old.get("checkboxLabel"),
            "The words beside the consent check box, such as I agree to the privacy policy.",
        )
        sizer.Add(_buttons(self), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)
        self._show_for_kind()
        apply_modal_ids(self)

    def _text(
        self, sizer: wx.Sizer, label: str, value: Any, help_text: str, *, multiline: bool = False
    ) -> wx.TextCtrl:
        control = wx.TextCtrl(
            self, value=str(value or ""), style=wx.TE_MULTILINE if multiline else 0
        )
        control.SetHelpText(help_text)
        if multiline:
            control.SetMinSize(dip_size(self, 380, 80))
        labelled_row(sizer, self, label, control)
        return control

    def kind_value(self) -> str:
        return _KINDS[max(0, self.kind.GetSelection())]

    def _show_for_kind(self) -> None:
        kind = self.kind_value()
        asks = kind not in DISPLAY_TYPES
        for control, shown in (
            (self.required, asks),
            (
                self.placeholder,
                kind
                in (
                    "text",
                    "textarea",
                    "email",
                    "phone",
                    "number",
                    "website",
                    "date",
                    "select",
                    "multiselect",
                ),
            ),
            (self.default, asks and kind not in ("name", "address", "consent", "time")),
            (self.choices, kind in CHOICE_TYPES),
            (self.content, kind == "html"),
            (self.consent, kind == "consent"),
        ):
            control.Show(shown)
            label = control.GetPrevSibling()
            if isinstance(label, wx.StaticText):
                label.Show(shown)
        self.Layout()
        self.Fit()

    def answer(self) -> FieldAnswer:
        kind = self.kind_value()
        values: dict[str, Any] = {
            "label": self.label.GetValue().strip(),
            "description": self.description.GetValue(),
            "adminLabel": self.admin_label.GetValue().strip(),
            "cssClass": self.css.GetValue().strip(),
        }
        if kind not in DISPLAY_TYPES:
            values["isRequired"] = self.required.GetValue()
        if self.placeholder.IsShown():
            values["placeholder"] = self.placeholder.GetValue()
        if self.default.IsShown():
            values["defaultValue"] = self.default.GetValue()
        if kind in CHOICE_TYPES:
            values["choices"] = self.choices.GetValue()
        if kind == "html":
            values["content"] = self.content.GetValue()
        if kind == "consent":
            values["checkboxLabel"] = self.consent.GetValue().strip()
        return FieldAnswer(kind, values)


def ask_field(
    parent: wx.Window, show_modal: ShowModal, *, title: str, field: Mapping[str, Any] | None
) -> FieldAnswer | None:
    """The field's type and settings when OK is pressed; None on Cancel."""
    dialog = FieldDialog(parent, title=title, field=field)
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.answer()
    finally:
        dialog.Destroy()


# --------------------------------------------------------------------------- #
# conditional logic

_WHEN = ("Always show this field", "Show this field when", "Hide this field when")


class ConditionDialog(wx.Dialog):
    """Show or hide one field on another field's answer."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        others: Sequence[Mapping[str, Any]],
        current: Condition | None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(
            "Show or hide this field depending on another field's answer. Only fields before "
            "this one are offered, so the form never changes behind the person filling it in."
        )
        self.others = list(others)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.when = wx.Choice(self, choices=list(_WHEN))
        self.when.SetHelpText("Always shows it; or shows or hides it on the answer below.")
        labelled_row(sizer, self, "&When:", self.when)
        self.field = wx.Choice(self, choices=[field_name(f) for f in self.others])
        self.field.SetHelpText("The earlier field whose answer decides.")
        self.field.Bind(wx.EVT_CHOICE, lambda _e: self._fill_values())
        labelled_row(sizer, self, "&Field:", self.field)
        self.test = wx.Choice(self, choices=["is", "is not"])
        self.test.SetHelpText("Whether the answer must be, or must not be, the value.")
        labelled_row(sizer, self, "&Test:", self.test)
        self.value = wx.ComboBox(self, choices=[])
        self.value.SetHelpText("The answer to compare with. A choice field offers its values.")
        labelled_row(sizer, self, "&Value:", self.value)
        sizer.Add(_buttons(self), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        ids = [str(f.get("id")) for f in self.others]
        if current is not None and current.field_id in ids:
            self.when.SetSelection(1 if current.action == "show" else 2)
            self.field.SetSelection(ids.index(current.field_id))
            self.test.SetSelection(0 if current.operator == "is" else 1)
            self._fill_values()
            self.value.SetValue(current.value)
        else:
            self.when.SetSelection(0)
            self.field.SetSelection(0 if self.others else wx.NOT_FOUND)
            self.test.SetSelection(0)
            self._fill_values()
        apply_modal_ids(self)

    def _fill_values(self) -> None:
        index = self.field.GetSelection()
        chosen = self.others[index] if 0 <= index < len(self.others) else {}
        values = [
            str(c.get("value", c.get("text", "")))
            for c in chosen.get("choices") or []
            if isinstance(c, dict)
        ]
        self.value.Set(values)
        if values:
            self.value.SetValue(values[0])

    def answer(self) -> Condition | None:
        when = self.when.GetSelection()
        index = self.field.GetSelection()
        if when <= 0 or not 0 <= index < len(self.others):
            return None
        return Condition(
            "show" if when == 1 else "hide",
            str(self.others[index].get("id")),
            "is" if self.test.GetSelection() <= 0 else "isnot",
            self.value.GetValue(),
        )


def ask_condition(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    others: Sequence[Mapping[str, Any]],
    current: Condition | None,
) -> tuple[bool, Condition | None]:
    """(True, the condition or None for always) on OK; (False, None) on Cancel."""
    dialog = ConditionDialog(parent, title=title, others=others, current=current)
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return False, None
        return True, dialog.answer()
    finally:
        dialog.Destroy()
