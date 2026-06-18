"""Prompt Library dialog — browse, run, manage, and share AI prompts.

Layout: searchable prompt list on the left; prompt text preview on the right.
Buttons: Run with AI, New, Edit, Disable/Enable, Delete, Import .pqp, Export .pqp.

Running a prompt sends the selected document text (passed in by the caller) to
the configured AI provider and opens :class:`~quill.ui.ai_chat_dialog.AIResponseDialog`
with the response.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

import wx

from quill.core.prompt_library import CATEGORIES, Prompt, PromptLibrary
from quill.ui.dialog_contract import show_message_box

if TYPE_CHECKING:
    from quill.core.settings import Settings


class PromptLibraryDialog:
    """Browse, run, and manage prompts in the AI Prompt Library."""

    def __init__(
        self,
        parent: object,
        library: PromptLibrary,
        settings: Settings,
        selection: str = "",
        document: str = "",
        title: str = "",
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._lib = library
        self._settings = settings
        self._selection = selection
        self._document = document
        self._doc_title = title
        self._running = False
        self._announce = announce_cb or (lambda _: None)

        self.dialog = wx.Dialog(
            parent,
            title="Prompt Library",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(700, 480))

        root = wx.BoxSizer(wx.VERTICAL)
        body = wx.BoxSizer(wx.HORIZONTAL)

        # -- Left: search + list --
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self.dialog, label="&Search:"), 0, wx.BOTTOM, 2)
        self._search = wx.TextCtrl(self.dialog)
        self._search.SetName("Search prompts")
        left.Add(self._search, 0, wx.EXPAND | wx.BOTTOM, 4)
        left.Add(wx.StaticText(self.dialog, label="&Prompts:"), 0, wx.BOTTOM, 2)
        self._listbox = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._listbox.SetName("Prompt list")
        left.Add(self._listbox, 1, wx.EXPAND)
        body.Add(left, 2, wx.EXPAND | wx.RIGHT, 8)

        # -- Right: prompt text preview --
        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self.dialog, label="Prompt &text:"), 0, wx.BOTTOM, 2)
        self._preview = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self._preview.SetName("Prompt text preview")
        right.Add(self._preview, 1, wx.EXPAND)
        right.Add(
            wx.StaticText(self.dialog, label="&Input text (replaces {selection}):"),
            0,
            wx.TOP | wx.BOTTOM,
            4,
        )
        self._input = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._input.SetName("Input text for prompt")
        self._input.SetValue(selection)
        right.Add(self._input, 1, wx.EXPAND)
        body.Add(right, 3, wx.EXPAND)

        root.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Prompt status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # -- Buttons --
        btn_sz = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_run = wx.Button(self.dialog, wx.ID_ANY, label="&Run with AI")
        self._btn_new = wx.Button(self.dialog, wx.ID_ANY, label="&New Prompt")
        self._btn_edit = wx.Button(self.dialog, wx.ID_ANY, label="&Edit")
        self._btn_toggle = wx.Button(self.dialog, wx.ID_ANY, label="Disa&ble")
        self._btn_delete = wx.Button(self.dialog, wx.ID_ANY, label="&Delete")
        self._btn_import = wx.Button(self.dialog, wx.ID_ANY, label="&Import .pqp")
        self._btn_export = wx.Button(self.dialog, wx.ID_ANY, label="E&xport .pqp")
        btn_close = wx.Button(self.dialog, wx.ID_CANCEL, label="C&lose")

        for b in (
            self._btn_run,
            self._btn_new,
            self._btn_edit,
            self._btn_toggle,
            self._btn_delete,
            self._btn_import,
            self._btn_export,
        ):
            btn_sz.Add(b, 0, wx.RIGHT, 4)
        btn_sz.AddStretchSpacer(1)
        btn_sz.Add(btn_close, 0)
        root.Add(btn_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )

        self._search.Bind(wx.EVT_TEXT, self._on_search_changed)
        self._listbox.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        self._listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_run)
        self._btn_run.Bind(wx.EVT_BUTTON, self._on_run)
        self._btn_new.Bind(wx.EVT_BUTTON, self._on_new)
        self._btn_edit.Bind(wx.EVT_BUTTON, self._on_edit)
        self._btn_toggle.Bind(wx.EVT_BUTTON, self._on_toggle)
        self._btn_delete.Bind(wx.EVT_BUTTON, self._on_delete)
        self._btn_import.Bind(wx.EVT_BUTTON, self._on_import)
        self._btn_export.Bind(wx.EVT_BUTTON, self._on_export)

        self._prompts: list[Prompt] = []
        self._rebuild_list()
        self._search.SetFocus()
        self._check_ai_configured()

    def _set_status(self, msg: str) -> None:
        self._status.SetLabel(msg)
        if msg:
            self._announce(msg)

    def _check_ai_configured(self) -> None:
        model_id = (
            getattr(self._settings, "ai_prompt_default_model", "")
            or self._settings.ai_chat_default_model
            or ""
        )
        if not model_id:
            self._set_status(
                "No AI model configured. Open Preferences > AI to set a provider and model."
            )

    # -- public API -----------------------------------------------------------

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    # -- list management ------------------------------------------------------

    def _rebuild_list(self, keep_index: int = 0) -> None:
        query = self._search.GetValue().lower().strip()
        self._prompts = [
            p
            for p in self._lib.all()
            if not query or query in p.name.lower() or query in p.category.lower()
        ]
        self._listbox.Clear()
        for p in self._prompts:
            disabled_tag = " [disabled]" if not p.enabled else ""
            src_tag = f" [{p.source}]" if p.source not in ("user", "builtin") else ""
            self._listbox.Append(f"{p.category} — {p.name}{src_tag}{disabled_tag}")
        count = self._listbox.GetCount()
        if count > 0:
            self._listbox.SetSelection(max(0, min(keep_index, count - 1)))
        self._refresh_preview()
        self._update_buttons()

    def _current_prompt(self) -> Prompt | None:
        idx = self._listbox.GetSelection()
        if idx < 0 or idx >= len(self._prompts):
            return None
        return self._prompts[idx]

    def _refresh_preview(self) -> None:
        p = self._current_prompt()
        self._preview.SetValue(p.text if p else "")

    def _update_buttons(self) -> None:
        p = self._current_prompt()
        has = p is not None
        self._btn_run.Enable(has and not self._running)
        self._btn_edit.Enable(has)
        self._btn_toggle.Enable(has)
        if p is not None:
            self._btn_toggle.SetLabel("Ena&ble" if not p.enabled else "Disa&ble")
        self._btn_delete.Enable(has and p is not None and not p.is_builtin)
        self._btn_export.Enable(bool(self._prompts))

    # -- event handlers -------------------------------------------------------

    def _on_search_changed(self, _event: object) -> None:
        self._rebuild_list()

    def _on_selection_changed(self, _event: object) -> None:
        self._refresh_preview()
        self._update_buttons()

    def _on_run(self, _event: object) -> None:
        p = self._current_prompt()
        if p is None or self._running:
            return
        input_text = self._input.GetValue()
        if not input_text.strip():
            show_message_box(
                "Enter text to process in the Input text field before running a prompt.",
                "No Input Text",
                wx.OK | wx.ICON_INFORMATION,
                self.dialog,
                announce=self._announce,
            )
            self._input.SetFocus()
            return
        provider_id = self._settings.ai_chat_default_provider
        model_id = self._settings.ai_prompt_default_model or self._settings.ai_chat_default_model
        if not model_id:
            show_message_box(
                "No AI model configured. Set a default model in Preferences > AI.",
                "No Model",
                wx.OK | wx.ICON_INFORMATION,
                self.dialog,
                announce=self._announce,
            )
            return
        prompt_text = (
            p.text
            .replace("{selection}", input_text)
            .replace("{document}", self._document or input_text)
            .replace("{title}", self._doc_title)
        )
        self._running = True
        self._update_buttons()
        self._set_status(f"Sending to {model_id}...")
        self.dialog.Layout()

        def run() -> None:
            try:
                from quill.core.ai_chat import send_prompt
                from quill.platform.windows.credential_store import load_secret

                api_key = load_secret(f"quill-{provider_id}-api-key")
                result = send_prompt(provider_id, model_id, prompt_text, api_key=api_key)
                wx.CallAfter(self._on_result, result, model_id, provider_id)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(self._on_run_error, str(exc))

        threading.Thread(  # GATE-40-OK: prompt library send worker.
            target=run, daemon=True
        ).start()

    def _on_result(self, result: str, model_id: str, provider_id: str) -> None:
        self._running = False
        self._set_status("")
        self._update_buttons()
        from quill.ui.ai_chat_dialog import AIResponseDialog

        dlg = AIResponseDialog(self.dialog, result, model_id, provider_id)
        dlg.show()
        dlg.close()

    def _on_run_error(self, message: str) -> None:
        self._running = False
        self._set_status("")
        self._update_buttons()
        show_message_box(
            f"AI request failed: {message}",
            "Prompt Run Failed",
            wx.OK | wx.ICON_ERROR,
            self.dialog,
            announce=self._announce,
        )

    def _on_new(self, _event: object) -> None:
        dlg = _PromptEditDialog(self.dialog)
        if dlg.show() == wx.ID_OK:
            name, text, category = dlg.get_values()
            if name and text:
                self._lib.add(name, text, category)
                self._rebuild_list()
                self._listbox.SetName(f"Prompt list — {name} added")
        dlg.close()

    def _on_edit(self, _event: object) -> None:
        p = self._current_prompt()
        if p is None:
            return
        dlg = _PromptEditDialog(self.dialog, p)
        if dlg.show() == wx.ID_OK:
            name, text, category = dlg.get_values()
            if name and text:
                self._lib.update(p.id, name=name, text=text, category=category)
                idx = self._listbox.GetSelection()
                self._rebuild_list(keep_index=idx)
        dlg.close()

    def _on_toggle(self, _event: object) -> None:
        p = self._current_prompt()
        if p is None:
            return
        idx = self._listbox.GetSelection()
        if p.enabled:
            self._lib.disable(p.id)
        else:
            self._lib.enable(p.id)
        self._rebuild_list(keep_index=idx)

    def _on_delete(self, _event: object) -> None:
        p = self._current_prompt()
        if p is None or p.is_builtin:
            return
        confirm = wx.MessageDialog(
            self.dialog,
            f"Delete the prompt '{p.name}'? This cannot be undone.",
            "Delete Prompt",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(confirm, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)  # noqa: dialog_button_contract
        try:
            ok = confirm.ShowModal() == wx.ID_YES
        finally:
            confirm.Destroy()
        if ok:
            self._lib.remove(p.id)
            self._rebuild_list()

    def _on_import(self, _event: object) -> None:
        with wx.FileDialog(
            self.dialog,
            "Import Prompt Pack",
            wildcard="QUILL Prompt Pack (*.pqp)|*.pqp",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fdlg:
            if fdlg.ShowModal() != wx.ID_OK:
                return
            path_str = fdlg.GetPath()
        from pathlib import Path

        try:
            added = self._lib.import_pqp(Path(path_str))
        except Exception as exc:  # noqa: BLE001
            show_message_box(
                f"Import failed: {exc}",
                "Import Error",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
                announce=self._announce,
            )
            return
        self._rebuild_list()
        msg = f"Imported {len(added)} prompt(s)." if added else "No new prompts to import."
        self._listbox.SetName(f"Prompt list — {msg}")
        show_message_box(
            msg,
            "Import Complete",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
            announce=self._announce,
        )

    def _on_export(self, _event: object) -> None:
        with wx.FileDialog(
            self.dialog,
            "Export Prompt Pack",
            defaultFile="my-prompts.pqp",
            wildcard="QUILL Prompt Pack (*.pqp)|*.pqp",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fdlg:
            if fdlg.ShowModal() != wx.ID_OK:
                return
            path_str = fdlg.GetPath()
        from pathlib import Path

        try:
            count = self._lib.export_pqp(Path(path_str))
        except Exception as exc:  # noqa: BLE001
            show_message_box(
                f"Export failed: {exc}",
                "Export Error",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
                announce=self._announce,
            )
            return
        show_message_box(
            f"Exported {count} prompt(s) to {path_str}",
            "Export Complete",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
            announce=self._announce,
        )


class _PromptEditDialog:
    """Inline edit / new prompt dialog."""

    def __init__(self, parent: object, prompt: Prompt | None = None) -> None:
        self._prompt = prompt
        is_new = prompt is None
        self.dialog = wx.Dialog(
            parent,
            title="New Prompt" if is_new else f"Edit — {prompt.name}",
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
        root.Add(self._text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, label="&Save")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="Ca&ncel")
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)

        from quill.ui.dialog_contract import apply_modal_ids

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
