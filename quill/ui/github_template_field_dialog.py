"""One form field's settings, for the GitHub template builder (GitHub PRD 21.3).

Split from :mod:`quill.ui.github_template_builder_dialog` (GATE-11), which
re-exports :class:`FieldDialog`: Add Field... and Edit Field... open it, and
OK hands back the new body element.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from quill.core.github.template_builder import (
    FIELD_KIND_NAMES,
    make_id,
    new_field,
    update_field,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["FieldDialog"]


class FieldDialog:
    """One field's settings; :attr:`result` is the new body element after OK."""

    def __init__(
        self,
        parent: object,
        kind: str,
        raw: dict[str, Any] | None = None,
        *,
        taken: Iterable[str] = (),
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _text: None)
        self.kind = kind
        self._raw = dict(raw or {})
        self._taken = set(taken)
        self.result: dict[str, Any] | None = None
        attrs = dict(self._raw.get("attributes") or {})
        rules = self._raw.get("validations") or {}
        title = f"Form Field: {'Edit' if raw else 'Add'} {FIELD_KIND_NAMES[kind]}"
        self._title = title
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 480, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        answers = kind != "markdown"
        choices = kind in ("dropdown", "checkboxes")

        # The helper makes the caption and then the box, so the label precedes
        # its field in tab order (A11Y-Z-ORDER); value and help are keywords.
        def text(label: str, *, value: object, help_text: str, multiline: bool = False) -> Any:
            caption = wx.StaticText(self.dialog, label=label)
            root.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            control = wx.TextCtrl(
                self.dialog, value=str(value or ""), style=wx.TE_MULTILINE if multiline else 0
            )
            control.SetName(label.replace("&", "").rstrip(":"))
            control.SetHelpText(help_text)
            root.Add(control, 1 if multiline else 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
            return control

        self.label = text(
            "&Label:",
            value=attrs.get("label"),
            help_text="What the person filling it in reads.",
        )
        self.ident = text(
            "&Id:",
            value=self._raw.get("id"),
            help_text="Letters, numbers, - and _. Left empty, it is made from the label.",
        )
        self.description = text(
            "&Description:",
            value=attrs.get("description"),
            help_text="A short line under the label.",
        )
        self.placeholder = text(
            "&Placeholder:",
            value=attrs.get("placeholder"),
            help_text="Shown in an empty box; it vanishes once typed.",
        )
        value_label = "&Value or instructions text:" if kind == "markdown" else "&Value:"
        self.value = text(
            value_label,
            value=attrs.get("value"),
            help_text=(
                "For instructions, the Markdown to show; otherwise the text the box starts with."
            ),
            multiline=kind in ("markdown", "textarea"),
        )
        self.render = text(
            "Render as &code in language:",
            value=attrs.get("render"),
            help_text="For long text only: shell, yaml and so on. The answer is fenced as code.",
        )
        options = attrs.get("options") or []
        lines = []
        for option in options if isinstance(options, list) else []:
            if isinstance(option, dict):
                must = "* " if option.get("required") else ""
                lines.append(f"{must}{option.get('label', '')}")
            else:
                lines.append(str(option))
        self.options = text(
            "&Options, one per line:",
            value="\n".join(lines),
            help_text=(
                "One option per line. For check boxes, start a line with * to require that one."
            ),
            multiline=True,
        )
        self.default = text(
            "Default op&tion number:",
            value=(attrs["default"] + 1) if isinstance(attrs.get("default"), int) else "",
            help_text=(
                "For a drop-down: which option starts chosen, counting from 1. Empty for none."
            ),
        )
        self.multiple = wx.CheckBox(self.dialog, label="&Multiple choice")
        self.multiple.SetValue(bool(attrs.get("multiple")))
        self.multiple.SetHelpText("For a drop-down: let people choose more than one.")
        root.Add(self.multiple, 0, wx.ALL, 8)
        self.required = wx.CheckBox(self.dialog, label="&Required")
        self.required.SetValue(bool(isinstance(rules, dict) and rules.get("required")))
        self.required.SetHelpText("The form cannot be sent until this is answered.")
        root.Add(self.required, 0, wx.LEFT | wx.RIGHT, 8)
        for control, applies in (
            (self.label, answers),
            (self.ident, answers),
            (self.description, answers),
            (self.placeholder, kind in ("input", "textarea")),
            (self.render, kind == "textarea"),
            (self.options, choices),
            (self.default, kind == "dropdown"),
            (self.multiple, kind == "dropdown"),
            (self.required, answers and kind != "checkboxes"),
        ):
            control.Enable(applies)
        self.problem = wx.StaticText(self.dialog, label="")
        self.problem.SetName("Field problem")
        root.Add(self.problem, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self.dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Keep these settings for the field.")
        ok.SetDefault()
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing the field.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def build(self) -> tuple[dict[str, Any] | None, str]:
        """The element these controls describe, or ``(None, why not)``."""
        kind = self.kind
        if kind == "markdown":
            value = self.value.GetValue()
            if not value.strip():
                return None, "Instructions need some text."
            return update_field(self._raw, new_field("markdown", value=value)), ""
        label = self.label.GetValue().strip()
        if not label:
            return None, "Every field needs a label."
        ident = self.ident.GetValue().strip() or make_id(label, self._taken)
        if ident in self._taken:
            return None, f"Another field already has the id {ident}."
        lines = [line.strip() for line in self.options.GetValue().splitlines() if line.strip()]
        musts = [line.startswith("*") for line in lines]
        names = [line.lstrip("*").strip() for line in lines]
        default = -1
        typed = self.default.GetValue().strip()
        if kind == "dropdown" and typed:
            if not typed.isdigit() or not 1 <= int(typed) <= len(names):
                return None, f"The default option must be a number from 1 to {len(names)}."
            default = int(typed) - 1
        made = new_field(
            kind,
            label,
            ident=ident,
            required=self.required.GetValue(),
            description=self.description.GetValue().strip(),
            placeholder=self.placeholder.GetValue(),
            value=self.value.GetValue(),
            render=self.render.GetValue().strip(),
            options=names,
            required_options=musts,
            multiple=self.multiple.GetValue(),
            default=default,
        )
        return update_field(self._raw, made), ""

    def _on_ok(self, event: Any) -> None:
        made, problem = self.build()
        if made is None:
            self.problem.SetLabel(problem)
            self._announce(problem)
            return
        self.result = made
        event.Skip()

    def show(self) -> dict[str, Any] | None:
        try:
            if show_modal_dialog(self.dialog, self._title) != self._wx.ID_OK:
                return None
            return self.result
        finally:
            self.dialog.Destroy()
