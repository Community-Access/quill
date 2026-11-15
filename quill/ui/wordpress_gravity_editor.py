"""QUILL's Gravity Forms editor: the form's settings and its fields (WP-C).

One dialog of standard controls. The top holds what the form says about
itself -- title, description, button text, label placement, the default
confirmation message and the Admin Notification's To and subject -- and the
bottom is the list of fields in order, one row each ("2. Email, Email,
required"), with buttons to add, edit, move, remove and condition them:

- Insert, or Add Field, adds a field after the selected one.
- Enter, or Edit Field, edits the selected field.
- Ctrl+Up and Ctrl+Down, or Move Up and Move Down, move it.
- Delete, or Remove Field, takes it out (and any logic that named it).
- Condition sets when it shows.

The editor never touches the network: it changes a copy of the form and
returns it, and the Workbench command previews, checks and saves it. A field
of a family QUILL does not build (a product, an upload) is in the list, can be
moved or removed, and says it is kept as it is. Moves and removals are said
aloud, since they change the list without moving focus (GATE-13 allows an
action's outcome).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from copy import deepcopy
from typing import Any

import wx

from quill.core.wordpress import gravity_build as gb
from quill.ui import wordpress_gravity_field_dialogs as fdlg
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import ShowModal, _buttons, labelled_row

__all__ = ["GravityFormEditor", "ask_form"]

_PLACEMENTS = list(gb.LABEL_PLACEMENTS)


class GravityFormEditor(wx.Dialog):
    """Edit a copy of a Gravity Forms form; :attr:`form` is the result."""

    def __init__(
        self,
        parent: wx.Window,
        show_modal: ShowModal,
        *,
        title: str,
        form: dict[str, Any],
        ever: Sequence[int] = (),
        announce: Callable[[str], None] = lambda _t: None,
        focus_field: str | None = None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(
            "A Gravity Forms form: its settings, then its fields in order. Nothing is sent "
            "until Review and Save shows the changes and you agree. Entries are never touched."
        )
        self.show_modal = show_modal
        self.announce = announce
        self.form = deepcopy(form)
        self.ever = list(ever)
        settings = gb.settings_of(self.form)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.title_box = self._text(sizer, "&Title:", settings.title, "The form's name.")
        self.description = self._text(
            sizer,
            "&Description:",
            settings.description,
            "Shown above the fields, when the theme shows form descriptions.",
            multiline=True,
        )
        self.button = self._text(
            sizer, "Button te&xt:", settings.button, "The words on the submit button."
        )
        self.placement = wx.Choice(self, choices=list(gb.LABEL_PLACEMENTS.values()))
        self.placement.SetSelection(
            _PLACEMENTS.index(settings.label_placement)
            if settings.label_placement in _PLACEMENTS
            else 0
        )
        self.placement.SetHelpText(
            "Where labels sit beside their fields. Top aligned reads best on a phone and zoomed in."
        )
        labelled_row(sizer, self, "Label &placement:", self.placement)
        self.confirmation = self._text(
            sizer,
            "Confirmation &message:",
            settings.confirmation,
            "What people read after sending the form: the default confirmation's message."
            if settings.confirmation_editable
            else "The default confirmation sends people to a page or address, which is changed "
            "in Gravity Forms; QUILL leaves it.",
            multiline=True,
        )
        self.confirmation.Enable(settings.confirmation_editable)
        self.notify_to = self._text(
            sizer,
            "Notification t&o:",
            settings.notify_to,
            "Who gets the Admin Notification email. {admin_email} is the site's admin address."
            if settings.notify_to_editable
            else "The Admin Notification goes to a field's answer or by routing, which is "
            "changed in Gravity Forms; QUILL leaves it.",
        )
        self.notify_to.Enable(settings.has_notification and settings.notify_to_editable)
        self.subject = self._text(
            sizer,
            "Notification &subject:",
            settings.notify_subject,
            "The Admin Notification's subject line.",
        )
        self.subject.Enable(settings.has_notification)
        self.fields = wx.ListBox(self, choices=[], style=wx.LB_SINGLE)
        self.fields.SetHelpText(
            "The form's fields in order. Insert adds, Enter edits, Ctrl+Up and Ctrl+Down move, "
            "Delete removes."
        )
        self.fields.SetMinSize(dip_size(self, 460, 200))
        self.fields.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.fields.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.edit_selected())
        labelled_row(sizer, self, "&Fields:", self.fields)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler, help_text in (
            ("&Add Field...", self.add_after_selected, "Add a field after the selected one."),
            ("&Edit Field...", self.edit_selected, "Change the selected field's settings."),
            ("Move &Up", lambda: self.move_selected(-1), "Move the selected field up one."),
            ("Move Do&wn", lambda: self.move_selected(1), "Move the selected field down one."),
            ("&Remove Field", self.remove_selected, "Take the selected field out of the form."),
            ("Co&ndition...", self.condition_selected, "When the selected field shows."),
        ):
            button = wx.Button(self, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=handler: run())
            row.Add(button, 0, wx.RIGHT, 4)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(_buttons(self, "Review and Save..."), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.refill()
        if focus_field is not None:
            ids = [str(f.get("id")) for f in gb.fields_of(self.form)]
            if focus_field in ids:
                self.fields.SetSelection(ids.index(focus_field))
                self.fields.SetFocus()
        apply_modal_ids(self)

    def _text(
        self, sizer: wx.Sizer, label: str, value: str, help_text: str, *, multiline: bool = False
    ) -> wx.TextCtrl:
        control = wx.TextCtrl(self, value=value, style=wx.TE_MULTILINE if multiline else 0)
        control.SetHelpText(help_text)
        if multiline:
            control.SetMinSize(dip_size(self, 460, 60))
        labelled_row(sizer, self, label, control)
        return control

    # -- the list ------------------------------------------------------------

    def _fields(self) -> list[dict[str, Any]]:
        found = self.form.setdefault("fields", [])
        return found if isinstance(found, list) else []

    def refill(self, select: int | None = None) -> None:
        rows = [gb.field_line(f, n) for n, f in enumerate(gb.fields_of(self.form), 1)]
        self.fields.Set(rows or ["No fields yet. Insert or Add Field adds one."])
        if rows:
            index = self.fields.GetSelection() if select is None else select
            self.fields.SetSelection(max(0, min(len(rows) - 1, index)))

    def selected(self) -> int:
        index = self.fields.GetSelection()
        return index if 0 <= index < len(gb.fields_of(self.form)) else -1

    def _on_key(self, event: wx.KeyEvent) -> None:
        key, ctrl = event.GetKeyCode(), event.ControlDown()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not ctrl:
            self.edit_selected()
        elif key in (wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT):
            self.add_after_selected()
        elif key in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.remove_selected()
        elif ctrl and key == wx.WXK_UP:
            self.move_selected(-1)
        elif ctrl and key == wx.WXK_DOWN:
            self.move_selected(1)
        else:
            event.Skip()

    # -- the commands ----------------------------------------------------------

    def add_after_selected(self) -> None:
        answer = fdlg.ask_field(self, self.show_modal, title="Add Field", field=None)
        if answer is None:
            return
        at = self.selected() + 1 if self.selected() >= 0 else None
        made = gb.add_field(self.form, answer.kind, answer.values, at=at, ever=self.ever)
        index = next(i for i, f in enumerate(self._fields()) if f is made)
        self.refill(index)
        self.fields.SetFocus()

    def edit_selected(self) -> None:
        index = self.selected()
        if index < 0:
            return
        field = self._fields()[index]
        if not gb.is_editable(field):
            self.announce(
                f"{gb.field_name(field)} is a {field.get('type')} field. QUILL keeps it as it is; "
                "change it in Gravity Forms, or move or remove it here."
            )
            return
        answer = fdlg.ask_field(
            self, self.show_modal, title=f"Edit Field - {gb.field_name(field)}", field=field
        )
        if answer is None:
            return
        gb.edit_field(field, answer.values)
        self.refill(index)
        self.fields.SetFocus()

    def move_selected(self, step: int) -> None:
        index = self.selected()
        if index < 0:
            return
        moved = gb.move_field(self.form, index, step)
        name = gb.field_name(self._fields()[moved])
        self.refill(moved)
        if moved == index:
            self.announce(f"{name} is already {'first' if step < 0 else 'last'}.")
        else:
            self.announce(f"{name} moved to {moved + 1} of {len(self._fields())}.")

    def remove_selected(self) -> None:
        index = self.selected()
        if index < 0:
            return
        gone = gb.remove_field(self.form, index)
        self.refill(index)
        if gone is not None:
            self.announce(
                f"Removed {gb.field_name(gone)}. Answers already given to it stay in the entries."
            )

    def condition_selected(self) -> None:
        index = self.selected()
        if index < 0:
            return
        field = self._fields()[index]
        current = gb.condition_of(field)
        if current == "complex":
            self.announce(
                f"{gb.field_name(field)} has conditional logic with more than one rule. QUILL "
                "keeps it as it is; change it in Gravity Forms."
            )
            return
        others = [f for f in self._fields()[:index] if f.get("type") not in gb.DISPLAY_TYPES]
        if not others:
            self.announce("A condition depends on a question before this one, and there is none.")
            return
        ok, condition = fdlg.ask_condition(
            self,
            self.show_modal,
            title=f"Condition - {gb.field_name(field)}",
            others=others,
            current=current if isinstance(current, gb.Condition) else None,
        )
        if not ok:
            return
        gb.set_condition(field, condition)
        self.refill(index)

    # -- the answer --------------------------------------------------------------

    def result(self) -> dict[str, Any]:
        """The edited form, with the settings boxes written in."""
        old = gb.settings_of(self.form)
        index = self.placement.GetSelection()
        gb.apply_settings(
            self.form,
            gb.Settings(
                title=self.title_box.GetValue().strip(),
                description=self.description.GetValue(),
                button=self.button.GetValue().strip(),
                label_placement=_PLACEMENTS[index]
                if 0 <= index < len(_PLACEMENTS)
                else "top_label",
                confirmation=self.confirmation.GetValue(),
                confirmation_editable=old.confirmation_editable,
                notify_to=self.notify_to.GetValue().strip(),
                notify_to_editable=old.notify_to_editable,
                notify_subject=self.subject.GetValue(),
                has_notification=old.has_notification,
            ),
        )
        return self.form


def ask_form(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    form: dict[str, Any],
    ever: Sequence[int] = (),
    announce: Callable[[str], None] = lambda _t: None,
    focus_field: str | None = None,
) -> dict[str, Any] | None:
    """The edited copy of *form* on Review and Save; None on Cancel."""
    dialog = GravityFormEditor(
        parent,
        show_modal,
        title=title,
        form=form,
        ever=ever,
        announce=announce,
        focus_field=focus_field,
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.result()
    finally:
        dialog.Destroy()
