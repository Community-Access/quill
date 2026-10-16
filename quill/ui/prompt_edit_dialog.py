"""New Prompt and Edit Prompt: the one window that writes a library prompt.

Extracted from :mod:`quill.ui.prompt_library_dialog` (GATE-11) on 2026-10-15,
when the Prompt Library became reachable from both editors' free AI as well as
from QUILL's own AI provider. The library window kept the list and the running;
this keeps the writing. Every control carries its F1 sentence at construction
(GATE-<APP>-HELP), because QUILL Lite's help audit now scans it too.
"""

from __future__ import annotations

import wx

from quill.core.prompt_library import CATEGORIES, Prompt
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["PromptEditDialog"]


class PromptEditDialog:
    """Write a new prompt, or change one: a name, a category and the text."""

    def __init__(self, parent: object, prompt: Prompt | None = None) -> None:
        self._prompt = prompt
        is_new = prompt is None
        self.dialog = wx.Dialog(
            parent,
            title="New Prompt" if is_new else "Edit Prompt",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 420))

        root = wx.BoxSizer(wx.VERTICAL)

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(
            wx.StaticText(self.dialog, label="&Name:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self._name = wx.TextCtrl(self.dialog)
        self._name.SetName("Prompt name")
        self._name.SetHelpText(
            "What the prompt is called in the list. Type a short name you will "
            "recognise, such as Make It Friendlier."
        )
        name_row.Add(self._name, 1)
        root.Add(name_row, 0, wx.EXPAND | wx.ALL, 8)

        cat_row = wx.BoxSizer(wx.HORIZONTAL)
        cat_row.Add(
            wx.StaticText(self.dialog, label="&Category:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._category = wx.Choice(self.dialog, choices=list(CATEGORIES))
        self._category.SetName("Prompt category")
        self._category.SetHelpText(
            "Which group the prompt is listed under. The list shows the category "
            "before each prompt's name."
        )
        cat_row.Add(self._category)
        root.Add(cat_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(
            wx.StaticText(
                self.dialog, label="Prompt &text — use {selection}, {document}, {title}:"
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            2,
        )
        self._text = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._text.SetName("Prompt text")
        self._text.SetHelpText(
            "The instruction the AI is given. Type {selection} where the text you "
            "run it on should go, {document} for the whole document, and {title} "
            "for the document's title."
        )
        root.Add(self._text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, label="&Save")
        ok_btn.SetHelpText("Saves the prompt in the library and closes this window.")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        cancel_btn.SetHelpText("Closes this window without saving anything.")
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
        )

        if prompt:
            self._name.SetValue(prompt.name)
            cat_idx = (
                list(CATEGORIES).index(prompt.category) if prompt.category in CATEGORIES else 4
            )
            self._category.SetSelection(cat_idx)
            self._text.SetValue(prompt.text)
        else:
            self._category.SetSelection(0)

        self._name.SetFocus()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    def get_values(self) -> tuple[str, str, str]:
        name = self._name.GetValue().strip()
        text = self._text.GetValue().strip()
        cat_idx = self._category.GetSelection()
        category = CATEGORIES[cat_idx] if 0 <= cat_idx < len(CATEGORIES) else "Custom"
        return name, text, category
