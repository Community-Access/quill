"""Fill a GitHub issue form (YAML) natively: one labelled control per field.

The schema and the body are :mod:`quill.core.github.issue_forms`'s; this is
only the form. Each field is a label created before its control (so a screen
reader reads the right name), its description as the control's F1 help, and
"(required)" in the label when GitHub requires it. A markdown element is read
only text in its place. OK validates; a missing answer is said once and focus
goes to that field. Nothing is sent from here: :attr:`result` holds the title
and body for the Workbench to send.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.issue_forms import (
    FormField,
    IssueForm,
    answer_key,
    render_body,
    validate,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["IssueFormDialog"]


class IssueFormDialog:
    """One issue form; :attr:`result` is ``(title, body)`` after Create Issue."""

    def __init__(
        self,
        parent: object,
        form: IssueForm,
        *,
        repository: str,
        announce: Callable[[str], None] | None = None,
        noun: str = "issue",
        action_label: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._form = form
        self._announce = announce or (lambda _text: None)
        self.result: tuple[str, str] | None = None
        self._controls: dict[str, Any] = {}
        # The same form fills a discussion category's form, and previews one
        # in the template builder ("preview" sends nothing anywhere).
        self._noun = noun
        action = action_label or f"Create {noun.title()}"
        self._title_text = (
            "Preview Form" if noun == "preview" else f"New {noun.title()} from a Form"
        )
        self.dialog = wx.Dialog(
            parent, title=self._title_text, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 600, 520))
        self.dialog.SetSize(dip_size(self.dialog, 760, 720))
        outer_panel = wx.ScrolledWindow(self.dialog, style=wx.VSCROLL)
        outer_panel.SetScrollRate(0, 20)
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            outer_panel,
            label=(
                f"{form.name}: {form.description or 'a form'} -- for {repository}. "
                + (
                    "This is a preview: nothing is sent anywhere."
                    if noun == "preview"
                    else f"{action} is the only action here that sends anything to GitHub."
                )
            ),
        )
        intro.Wrap(680)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        title_noun = "Issue" if noun == "preview" else noun.title()
        title_label = wx.StaticText(outer_panel, label=f"{title_noun} title (required):")
        root.Add(title_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._issue_title = wx.TextCtrl(outer_panel, value=form.title)
        self._issue_title.SetName(f"{title_noun} title (required)")
        self._issue_title.SetHelpText("What it is about, in a line.")
        root.Add(self._issue_title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        for index, item in enumerate(form.fields):
            self._add_field(outer_panel, root, item, index)

        self._status = wx.StaticText(outer_panel, label="")
        self._status.SetName("What is still missing")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 10)
        buttons = wx.StdDialogButtonSizer()
        create = wx.Button(outer_panel, wx.ID_OK, label=action)
        create.SetHelpText(
            "Show the body these answers would write."
            if noun == "preview"
            else "Send it to GitHub with these answers."
        )
        create.SetDefault()
        cancel = wx.Button(outer_panel, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Close without sending anything.")
        buttons.AddButton(create)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        outer_panel.SetSizer(root)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(outer_panel, 1, wx.EXPAND)
        self.dialog.SetSizer(sizer)
        create.Bind(wx.EVT_BUTTON, self._on_create)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _add_field(self, panel: Any, root: Any, item: FormField, index: int) -> None:
        wx = self._wx
        key = answer_key(item, index)
        if item.kind == "markdown":
            note = wx.StaticText(panel, label="From the form's authors:")
            root.Add(note, 0, wx.LEFT | wx.RIGHT, 10)
            text = wx.TextCtrl(
                panel, value=item.value, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
            )
            text.SetName("From the form's authors")
            text.SetHelpText("Text from the form's authors; read it, nothing to fill in.")
            root.Add(text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            return
        name = f"{item.label} (required)" if item.required else item.label
        help_text = item.description or ("Required." if item.required else "Optional.")
        # Check boxes, and a drop-down that allows several: one check box per
        # option in a labelled group (a check list box does not announce its
        # checked state as you move, A11Y-SR-1).
        if item.kind == "checkboxes" or (item.kind == "dropdown" and item.multiple):
            box = wx.StaticBox(panel, label=name)
            group = wx.StaticBoxSizer(box, wx.VERTICAL)
            checks = []
            musts = item.required_options or (False,) * len(item.options)
            for option, must in zip(item.options, musts, strict=False):
                check = wx.CheckBox(box, label=f"{option} (required)" if must else option)
                check.SetHelpText(item.description or "Check it if it applies.")
                group.Add(check, 0, wx.ALL, 4)
                checks.append(check)
            self._controls[key] = checks
            root.Add(group, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            return
        # Each control's label is the static text made just before it: that,
        # not SetName, is what a screen reader reads on Windows.
        control: Any
        if item.kind == "dropdown":
            choices = list(item.options) if item.required else ["(none)", *item.options]
            label = wx.StaticText(panel, label=f"{name}:")
            control = wx.Choice(panel, choices=choices)
            start = item.default if item.default >= 0 else -1
            control.SetSelection(start if item.required else start + 1)
        else:
            style = wx.TE_MULTILINE | wx.TE_WORDWRAP if item.kind == "textarea" else 0
            label = wx.StaticText(panel, label=f"{name}:")
            control = wx.TextCtrl(panel, value=item.value, style=style)
            if item.placeholder:
                control.SetHint(item.placeholder)
        root.Add(label, 0, wx.LEFT | wx.RIGHT, 10)
        control.SetName(name)
        control.SetHelpText(help_text or name)
        proportion = 1 if item.kind == "textarea" else 0
        root.Add(control, proportion, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._controls[key] = control

    def answers(self) -> dict[str, object]:
        """Every answer, keyed the way :mod:`issue_forms` reads them."""
        wx = self._wx
        found: dict[str, object] = {}
        for index, item in enumerate(self._form.fields):
            key = answer_key(item, index)
            control = self._controls.get(key)
            if control is None:
                continue
            if item.kind == "checkboxes":
                found[key] = [bool(check.GetValue()) for check in control]
            elif isinstance(control, list):
                found[key] = [
                    o for o, c in zip(item.options, control, strict=False) if c.GetValue()
                ]
            elif isinstance(control, wx.Choice):
                choice = control.GetStringSelection()
                found[key] = "" if choice == "(none)" else choice
            else:
                found[key] = control.GetValue()
        return found

    def _on_create(self, event: Any) -> None:
        answers = self.answers()
        missing = validate(self._form, answers)
        title = self._issue_title.GetValue().strip()
        if not title:
            missing.insert(0, "The title is required.")
        if missing:
            self._status.SetLabel(" ".join(missing))
            self._announce(missing[0])
            self._focus_missing(missing[0])
            return
        self.result = (title, render_body(self._form, answers))
        event.Skip()

    def _focus_missing(self, sentence: str) -> None:
        if sentence.startswith("The title"):
            self._issue_title.SetFocus()
            return
        for index, item in enumerate(self._form.fields):
            if item.answers and sentence.startswith(item.label):
                control = self._controls.get(answer_key(item, index))
                target = control[0] if isinstance(control, list) and control else control
                if target is not None:
                    target.SetFocus()
                return

    def show(self) -> bool:
        try:
            return (
                show_modal_dialog(self.dialog, self._title_text) == self._wx.ID_OK
                and self.result is not None
            )
        finally:
            self.dialog.Destroy()
